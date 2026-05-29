"""Marketing Lead daily plan generator.

Runs daily at 11:00 ET via the trinity scheduler `marketing_plan` cycle.

Algorithm:
1. Load `state/distribution-queue.json` (items with status == "ready").
2. Load `state/distribution-log.json` to know (item_id, channel/subreddit) pairs
   already posted in the last 30 days.
3. Pick top 3 unposted items by `added_at` desc.
4. For each item, select the best channel:
   - Niche-keyword override (audience text scanned against NICHE_KEYWORDS_TO_CHANNEL)
   - Otherwise round-robin reddit / twitter / linkedin based on plan index
5. Generate the draft via `scripts.distribution_draft.generate_draft` (Claude SDK
   via the local OAuth CLI -- same fallback sub-project 5 used).
6. For Reddit plans, pick the first subreddit from the LLM's suggestions that
   has NOT been posted to with this slug in the last 30 days.
7. Write `state/marketing-plans/{YYYY-MM-DD}.json` atomically (.tmp + rename).
8. Send a one-message summary to `marketing_reports` Telegram channel
   (falls back to founder_dm).

Standalone usage:
    source ~/.profile && python scripts/marketing_plan.py

Output (last line, stdout):
    wrote state/marketing-plans/<date>.json with N plans
"""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make sibling modules importable when run directly.
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.distribution_draft import generate_draft  # noqa: E402
from scripts.telegram_dispatch import send_to_channel  # noqa: E402


# -- Paths ----------------------------------------------------------
STATE_DIR = _REPO_ROOT / "state"
QUEUE_FILE = STATE_DIR / "distribution-queue.json"
LOG_FILE = STATE_DIR / "distribution-log.json"
PLANS_DIR = STATE_DIR / "marketing-plans"

# -- Config ---------------------------------------------------------
TOP_N = 3
DEDUPE_WINDOW_DAYS = 30
ROUND_ROBIN = ["reddit", "twitter", "linkedin"]

# Niche keyword -> (channel, subreddit_or_handle). Subreddit None means
# generic for the channel (e.g. LinkedIn doesn't have subreddits).
NICHE_KEYWORDS_TO_CHANNEL: dict[str, tuple[str, str | None]] = {
    "trucking": ("reddit", "r/Truckers"),
    "carrier": ("reddit", "r/Truckers"),
    "freight": ("reddit", "r/Truckers"),
    "real estate": ("linkedin", None),
    "realtor": ("linkedin", None),
    "agent": ("linkedin", None),
    "contractor": ("reddit", "r/Construction"),
    "electrician": ("reddit", "r/electricians"),
    "hvac": ("reddit", "r/HVAC"),
    "medicare": ("linkedin", None),
    "investor": ("linkedin", None),
    "nonprofit": ("linkedin", None),
    "bank": ("twitter", None),
    "biz": ("twitter", None),
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def load_queue() -> list[dict]:
    """Return all queue items with status == 'ready' (preserves order)."""
    if not QUEUE_FILE.exists():
        return []
    data = json.loads(QUEUE_FILE.read_text())
    return [i for i in data.get("items", []) if i.get("status") == "ready"]


def load_log_entries() -> list[dict]:
    """Return all distribution-log entries (may be empty)."""
    if not LOG_FILE.exists():
        return []
    data = json.loads(LOG_FILE.read_text())
    return data.get("entries", [])


def _parse_iso(s: str) -> datetime | None:
    """Best-effort ISO-8601 parse; returns None on failure."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def recent_posted_keys(entries: list[dict]) -> set[tuple[str, str]]:
    """Return set of (slug, channel_key) posted in last DEDUPE_WINDOW_DAYS.

    channel_key for reddit entries is the full "reddit:r/Sub" string; for
    twitter/linkedin it's just the channel name. Any status counts as 'posted'
    for dedupe purposes -- if we tried it recently, don't retry the same target.
    """
    cutoff = now_utc() - timedelta(days=DEDUPE_WINDOW_DAYS)
    keys: set[tuple[str, str]] = set()
    for e in entries:
        slug = e.get("slug")
        channel = e.get("channel")
        if not slug or not channel:
            continue
        posted_at = _parse_iso(e.get("posted_at", ""))
        if posted_at is None or posted_at < cutoff:
            continue
        keys.add((slug, channel))
    return keys


def pick_top_items(items: list[dict], n: int) -> list[dict]:
    """Return top-N items by added_at desc (most recent first)."""
    def key(i: dict) -> datetime:
        return _parse_iso(i.get("added_at", "")) or datetime.min.replace(
            tzinfo=timezone.utc
        )
    return sorted(items, key=key, reverse=True)[:n]


def select_channel(item: dict, plan_index: int) -> tuple[str, str | None]:
    """Select (channel, subreddit_or_handle_hint) for an item.

    Niche-keyword override scans the audience text first; falls back to
    round-robin keyed on the plan index so a 3-item plan spreads across
    reddit / twitter / linkedin evenly.
    """
    audience = (item.get("audience") or "").lower()
    name = (item.get("name") or "").lower()
    haystack = f"{audience} {name}"
    for keyword, (channel, hint) in NICHE_KEYWORDS_TO_CHANNEL.items():
        if keyword in haystack:
            return channel, hint
    return ROUND_ROBIN[plan_index % len(ROUND_ROBIN)], None


def pick_subreddit(
    draft: dict, slug: str, posted_keys: set[tuple[str, str]], fallback: str | None
) -> tuple[str, bool]:
    """For a reddit draft, return (subreddit, requires_founder_review_flag).

    Walk LLM's `subreddit_suggestions` in order; take the first one not posted
    to with this slug in the last 30 days. If all are stale, fall back to the
    niche-override hint or the first suggestion (flag for founder review so
    distribution-agent or founder can decide whether to actually post).
    """
    suggestions = [s for s in (draft.get("subreddit_suggestions") or []) if s]
    for sub in suggestions:
        if (slug, f"reddit:{sub}") not in posted_keys:
            return sub, False
    if fallback and (slug, f"reddit:{fallback}") not in posted_keys:
        return fallback, False
    # All exhausted -- return best-effort with review flag.
    return (suggestions[0] if suggestions else (fallback or "r/Entrepreneur")), True


def build_plan(
    item: dict, plan_index: int, posted_keys: set[tuple[str, str]]
) -> dict | None:
    """Build one plan entry. Returns None if generation fails."""
    channel, hint = select_channel(item, plan_index)
    slug = item.get("slug", "")
    try:
        draft = generate_draft(item, channel)
    except Exception as exc:  # pylint: disable=broad-except
        print(
            f"WARN: generate_draft failed for {slug}/{channel}: {exc}",
            file=sys.stderr,
        )
        traceback.print_exc(file=sys.stderr)
        return None

    requires_review = False
    subreddit_or_handle: str | None = None
    rationale_bits: list[str] = []

    if channel == "reddit":
        subreddit_or_handle, requires_review = pick_subreddit(
            draft, slug, posted_keys, hint
        )
        rationale_bits.append(f"Reddit -> {subreddit_or_handle}")
        if hint:
            rationale_bits.append(f"niche-keyword match: {hint}")
        else:
            rationale_bits.append("round-robin assignment")
        if requires_review:
            rationale_bits.append(
                "all suggested subreddits used within 30d -- founder should "
                "review before posting"
            )
    elif channel == "twitter":
        subreddit_or_handle = hint  # may be None
        rationale_bits.append("Twitter thread (link in reply for reach)")
        if hint:
            rationale_bits.append(f"niche-keyword target: {hint}")
        else:
            rationale_bits.append("round-robin assignment")
    elif channel == "linkedin":
        subreddit_or_handle = hint
        rationale_bits.append("LinkedIn professional post")
        if hint:
            rationale_bits.append(f"niche-keyword match drove channel choice")
        else:
            rationale_bits.append("round-robin assignment")

    # Schedule to distribution-agent's 21:00 ET cycle today.
    sched = now_utc().replace(hour=21, minute=0, second=0, microsecond=0)
    if sched < now_utc():
        sched = sched + timedelta(days=1)

    return {
        "item_id": item.get("id"),
        "slug": slug,
        "channel": channel,
        "subreddit_or_handle": subreddit_or_handle,
        "draft": draft,
        "rationale": " | ".join(rationale_bits),
        "scheduled_for": iso(sched),
        "requires_founder_review": requires_review,
    }


def write_plan_atomic(plan: dict) -> Path:
    """Write today's plan atomically (.tmp + rename). Returns final path."""
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = plan["date"]
    final = PLANS_DIR / f"{date_str}.json"
    tmp = final.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(plan, f, indent=2, sort_keys=False)
        f.write("\n")
    tmp.replace(final)
    return final


def safe_notify(channel: str, message: str) -> None:
    """Send to channel; never raise on Telegram failures (just log to stderr)."""
    try:
        send_to_channel(channel, message)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"WARN: telegram dispatch failed: {exc}", file=sys.stderr)


def build_summary(plan: dict) -> str:
    """One-message summary of the day's plan for Telegram."""
    lines = [f"Marketing plan {plan['date']} -- {len(plan['plans'])} drafts ready"]
    for p in plan["plans"]:
        slug = p.get("slug", "?")
        channel = p.get("channel", "?")
        target = p.get("subreddit_or_handle") or "-"
        flag = " [REVIEW]" if p.get("requires_founder_review") else ""
        lines.append(f"- {slug} -> {channel} ({target}){flag}")
    lines.append("Drafts in state/marketing-plans/. Distribution-agent posts at 21:00 ET.")
    return "\n".join(lines)


def main() -> int:
    """Entry point -- read queue/log, build plans, write file, notify."""
    items = load_queue()
    if not items:
        print("No ready items in distribution-queue.json -- nothing to plan.")
        return 0

    entries = load_log_entries()
    posted_keys = recent_posted_keys(entries)

    # Filter out items already saturated across ALL three channels in last 30d.
    def already_saturated(item: dict) -> bool:
        slug = item.get("slug", "")
        # Saturated if twitter, linkedin, AND at least one reddit subreddit posted.
        if (slug, "twitter") in posted_keys and (slug, "linkedin") in posted_keys:
            for key_slug, key_chan in posted_keys:
                if key_slug == slug and key_chan.startswith("reddit:"):
                    return True
        return False

    candidates = [i for i in items if not already_saturated(i)]
    top = pick_top_items(candidates, TOP_N)

    today_iso = now_utc().date().isoformat()
    plans: list[dict] = []
    for idx, item in enumerate(top):
        plan_entry = build_plan(item, idx, posted_keys)
        if plan_entry is not None:
            plans.append(plan_entry)

    plan_doc = {
        "version": 1,
        "date": today_iso,
        "generated_at": iso(now_utc()),
        "plans": plans,
    }
    path = write_plan_atomic(plan_doc)

    summary = build_summary(plan_doc)
    safe_notify("marketing_reports", summary)

    print(f"wrote {path.relative_to(_REPO_ROOT)} with {len(plans)} plans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
