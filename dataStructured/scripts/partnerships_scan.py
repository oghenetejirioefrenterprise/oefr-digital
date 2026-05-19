"""Partnerships Lead weekly scan.

Runs Mondays at 10:00 ET via the trinity scheduler `partnerships_scan` cycle.

Algorithm:
1. Scan `state/products/*/{spec.json,launch-report.json}` for FULLY_SHIPPED /
   compliance-PASS products (mirrors seo_publish.py filter logic).
2. For each product (capped by --max-products), use claude_agent_sdk.query
   (CLI/OAuth — same pattern as scripts/distribution_draft.py + seo_publish.py)
   to research 3-5 real candidate outlets (newsletters, podcasts, YouTube
   channels, niche subreddits) whose audience overlaps with the product
   buyer profile.
3. For each returned candidate:
     - Score audience_match_score (1-10) (LLM supplies; we clamp).
     - Pre-generate the partner-scoped Stripe link by invoking
       `scripts/affiliate_link.py` as a subprocess; capture the affiliate URL
       from stdout and the corresponding entry from utm-links.json for the
       client_reference_id.
     - Build the personalized outreach DM text (LLM-drafted, contains the
       affiliate link).
4. Write per-product brief to `state/partnerships/candidates/{slug}.json`.
5. Send a digest summary to the `marketing_reports` Telegram channel.

Standalone usage:
    source ~/.profile && python scripts/partnerships_scan.py [--max-products N]

The --max-products flag (default 3) bounds LLM cost for smoke tests; the
scheduled cycle should pass `--max-products 99` or omit and rely on the
default depending on observed cost / latency in production.
"""
from __future__ import annotations

import anyio
import argparse
import json
import re
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Make sibling modules importable when run directly.
_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.telegram_dispatch import send_to_channel  # noqa: E402


# -- Paths ----------------------------------------------------------
STATE_DIR = _REPO_ROOT / "state"
PRODUCTS_DIR = STATE_DIR / "products"
CANDIDATES_DIR = STATE_DIR / "partnerships" / "candidates"
UTM_LINKS_FILE = STATE_DIR / "partnerships" / "utm-links.json"
AFFILIATE_SCRIPT = _REPO_ROOT / "scripts" / "affiliate_link.py"

# -- Config ---------------------------------------------------------
DEFAULT_MAX_PRODUCTS = 3
DEFAULT_COMMISSION_PCT = 30
MIN_CANDIDATES_PER_PRODUCT = 3
MAX_CANDIDATES_PER_PRODUCT = 5
PYTHON_BIN = sys.executable

SHIPPED_STATUSES = {
    "FULLY_SHIPPED",
    "SHIPPED",
    "SHIPPED_STRIPE_ONLY",
    "STRIPE_ONLY",
}


# -- Helpers --------------------------------------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


_HANDLE_RE = re.compile(r"[^a-z0-9_]+")


def sanitize_handle(raw: str) -> str:
    """Reduce an LLM-supplied handle to [a-z0-9_], lowercase, max 40 chars.

    affiliate_link.py uses the handle inside a client_reference_id; Stripe
    accepts most chars but URL-safety + short hashing both prefer this form.
    """
    if not raw:
        return ""
    cleaned = _HANDLE_RE.sub("_", raw.strip().lower()).strip("_")
    return cleaned[:40] if cleaned else ""


# -- Product discovery ---------------------------------------------
def load_shippable_products() -> list[dict]:
    """Return list of {slug, spec, launch} for FULLY_SHIPPED + PASS products.

    Mirrors scripts/seo_publish.py:load_shippable_products() so both agents
    operate on the same product universe.
    """
    if not PRODUCTS_DIR.exists():
        return []

    products: list[dict] = []
    for entry in sorted(PRODUCTS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        spec_path = entry / "spec.json"
        launch_path = entry / "launch-report.json"
        if not (spec_path.exists() and launch_path.exists()):
            continue
        try:
            spec = json.loads(spec_path.read_text())
            launch = json.loads(launch_path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        if launch.get("status") not in SHIPPED_STATUSES:
            continue
        if spec.get("compliance_verdict") != "PASS":
            continue
        if not launch.get("stripe_payment_link_url"):
            continue
        if not spec.get("name"):
            continue

        products.append({"slug": entry.name, "spec": spec, "launch": launch})

    # Rank: higher row_count first, then more-recently-launched.
    def sort_key(p: dict) -> tuple:
        row_count = p["spec"].get("row_count") or 0
        created = _parse_iso(p["launch"].get("created", "")) or datetime.min.replace(
            tzinfo=timezone.utc
        )
        return (-row_count, -created.timestamp())

    products.sort(key=sort_key)
    return products


# -- Claude SDK candidate research --------------------------------
def _build_candidate_prompt(product: dict) -> str:
    spec = product["spec"]
    name = spec.get("name", "")
    summary = spec.get("summary", "")
    audience = spec.get("audience", "")
    source = spec.get("source", "")
    row_count = spec.get("row_count", "?")
    price = spec.get("price_usd", "?")

    return f"""You are the Partnerships Lead for DataStructured, an autonomous public-data-as-a-product company.

Your task: identify {MIN_CANDIDATES_PER_PRODUCT}-{MAX_CANDIDATES_PER_PRODUCT} affiliate candidates for the product below — newsletter writers, podcast hosts, YouTube creators, or niche-community publishers whose audience overlaps with the product's buyer profile. The founder will review every candidate before any outreach is sent, so surface your best knowledge of real outlets in this niche — better to propose plausible candidates the founder can verify than to return nothing.

PRODUCT:
  name: {name}
  summary: {summary}
  audience: {audience}
  source: {source}
  row_count: {row_count}
  price_usd: {price}

GUIDELINES:
  - Prefer real, well-known outlets you have actual knowledge of (Substacks, podcasts, YouTube channels, subreddits, X creators serving this niche).
  - If you are unsure of an exact URL, supply the most likely canonical form (substack.com/[name], youtube.com/@[name], reddit.com/r/[name]) — the founder verifies before sending.
  - Each candidate must include `specific_reference` describing the type of content they publish that justifies the audience fit (a recurring theme, a series they run, a known editorial focus). Don't invent specific post titles you can't recall.
  - Skip platforms where unsolicited affiliate-solicitation DMs violate ToS: Instagram, Threads. Acceptable platforms: Substack, beehiiv, independent podcasts, YouTube, niche subreddits, X/Twitter creators, LinkedIn (flag as email_outreach).
  - For LinkedIn / professional outlets where cold DMs are weak: set `requires_email_outreach` true.
  - Default commission 30%; only bump higher for unusually large or qualified audiences.

For each candidate, supply:
  - candidate_name: human-readable name of the outlet or creator
  - candidate_handle: lowercase, underscore-or-alnum-only; this becomes a UTM partner handle
  - candidate_url: primary URL (their newsletter, channel, or profile)
  - platform: one of "substack" | "beehiiv" | "podcast" | "youtube" | "subreddit" | "twitter" | "linkedin" | "other"
  - audience: short description including approximate size if known
  - audience_match_score: integer 1-10 (10 = bull's-eye buyer overlap)
  - specific_reference: a concrete editorial focus or recurring topic that justifies the match
  - commission_pct: integer (default 30; bump if audience warrants)
  - requires_email_outreach: boolean (true for LinkedIn / formal outlets; false for casual creator DMs)

Return ONLY a JSON object (no prose, no code fences) with shape:
{{"candidates": [{{...}}, ...]}}

Aim for {MIN_CANDIDATES_PER_PRODUCT}-{MAX_CANDIDATES_PER_PRODUCT} candidates. Empty list only if this niche genuinely has no creator economy you can identify.
"""


def _build_dm_prompt(product: dict, candidate: dict, affiliate_link: str) -> str:
    spec = product["spec"]
    name = spec.get("name", "")
    summary = spec.get("summary", "")
    source = spec.get("source", "")
    row_count = spec.get("row_count", "?")
    price = spec.get("price_usd", "?")
    commission_pct = candidate.get("commission_pct", DEFAULT_COMMISSION_PCT)
    style_hint = (
        "Write a short professional email (subject + body, 90-140 words). Open with a sincere reference to their work, then introduce the dataset, then the affiliate offer."
        if candidate.get("requires_email_outreach")
        else "Write a casual DM (80-130 words). First sentence references the candidate's specific recent work. Then the dataset value in 1-2 sentences. Then the affiliate offer with the link. No emoji, no hype words."
    )

    return f"""Draft a personalized outreach message to this potential affiliate partner.

PRODUCT:
  name: {name}
  summary: {summary}
  source: {source}
  row_count: {row_count}
  price_usd: {price}

CANDIDATE:
  name: {candidate.get("candidate_name", "")}
  platform: {candidate.get("platform", "")}
  audience: {candidate.get("audience", "")}
  specific_reference: {candidate.get("specific_reference", "")}

AFFILIATE LINK (already generated — include verbatim in the message): {affiliate_link}
COMMISSION: {commission_pct}%

{style_hint}

HARD RULES:
  - No discount language (no "limited time", "X% off", "sale").
  - Reference the candidate's specific_reference naturally; don't quote it verbatim.
  - Include the AFFILIATE LINK exactly as given.
  - State the commission rate plainly.
  - No emoji.
  - No hashtags.

Return ONLY a JSON object (no prose, no code fences) with shape:
{{"outreach_dm": "...full message text..."}}
For email-style messages, include the subject line as the first line prefixed with "Subject: ".
"""


def _extract_json(raw: str) -> dict:
    """Pull a JSON object out of an LLM response that may include prose or fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines[1:])
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


async def _query_claude_sdk(prompt: str, system_prompt: str) -> str:
    """Run a one-shot query via claude_agent_sdk (uses local Claude CLI / OAuth).

    Same pattern as scripts/distribution_draft.py and scripts/seo_publish.py —
    TJ's ~/.profile intentionally omits ANTHROPIC_API_KEY (OAuth via Max plan).
    """
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        TextBlock,
        query,
    )

    opts = ClaudeAgentOptions(
        model="claude-sonnet-4-5",
        max_turns=1,
        permission_mode="bypassPermissions",
        allowed_tools=[],
        system_prompt=system_prompt,
    )

    chunks: list[str] = []
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    return "".join(chunks)


def research_candidates(product: dict) -> list[dict]:
    """Ask the LLM to research 3-5 real candidates for this product.

    Returns a (possibly empty) list of raw candidate dicts. Caller is
    responsible for validation, handle-sanitization, and affiliate-link
    generation. We do minimal trimming here so the LLM's structure stays
    inspectable downstream.
    """
    prompt = _build_candidate_prompt(product)
    system_prompt = (
        "You are a partnerships researcher who surfaces real creators and outlets in niche industries. "
        "The founder verifies every candidate before any outreach, so propose your best-known candidates in the niche; "
        "you don't need to be 100% certain of exact URLs as long as you can name a real outlet and describe its editorial focus. "
        "You return ONLY a JSON object — no prose, no code fences, no commentary."
    )
    raw = anyio.run(_query_claude_sdk, prompt, system_prompt)
    try:
        obj = _extract_json(raw)
    except json.JSONDecodeError as exc:
        print(
            f"WARN: candidate JSON parse failed for {product['slug']}: {exc}",
            file=sys.stderr,
        )
        print(f"--- raw (first 400 chars) ---\n{raw[:400]}", file=sys.stderr)
        return []
    cands = obj.get("candidates", [])
    if not isinstance(cands, list):
        return []
    return cands[:MAX_CANDIDATES_PER_PRODUCT]


def draft_outreach_dm(product: dict, candidate: dict, affiliate_link: str) -> str:
    """Generate the personalized outreach DM / email text via the LLM."""
    prompt = _build_dm_prompt(product, candidate, affiliate_link)
    system_prompt = (
        "You write concise, respectful affiliate-outreach messages. "
        "You return ONLY a JSON object — no prose, no code fences, no commentary."
    )
    raw = anyio.run(_query_claude_sdk, prompt, system_prompt)
    try:
        obj = _extract_json(raw)
    except json.JSONDecodeError as exc:
        print(
            f"WARN: DM JSON parse failed for {candidate.get('candidate_handle', '?')}: {exc}",
            file=sys.stderr,
        )
        return ""
    dm = obj.get("outreach_dm", "")
    return dm if isinstance(dm, str) else ""


# -- Affiliate link generation ------------------------------------
def generate_affiliate_link(
    partner_handle: str, product_slug: str, commission_pct: int
) -> tuple[str | None, str | None]:
    """Invoke scripts/affiliate_link.py to mint the partner-scoped Stripe link.

    Returns (affiliate_url, client_reference_id) or (None, None) on failure.
    The client_reference_id is read back from utm-links.json after the
    subprocess writes it, so it stays in sync with whatever affiliate_link.py
    chose to encode.
    """
    if not partner_handle:
        return None, None
    try:
        proc = subprocess.run(
            [
                PYTHON_BIN,
                str(AFFILIATE_SCRIPT),
                "--partner",
                partner_handle,
                "--product-slug",
                product_slug,
                "--commission-pct",
                str(commission_pct),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        print(
            f"ERROR: affiliate_link.py timeout for {partner_handle}/{product_slug}",
            file=sys.stderr,
        )
        return None, None

    if proc.returncode != 0:
        print(
            f"ERROR: affiliate_link.py rc={proc.returncode} "
            f"for {partner_handle}/{product_slug}: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None, None

    affiliate_url = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if not affiliate_url.startswith("http"):
        print(
            f"ERROR: affiliate_link.py stdout not a URL: {affiliate_url!r}",
            file=sys.stderr,
        )
        return None, None

    # Recover the client_reference_id from utm-links.json for the schema.
    client_ref = None
    try:
        links = json.loads(UTM_LINKS_FILE.read_text()).get("links", [])
        for entry in links:
            if (
                entry.get("partner") == partner_handle
                and entry.get("product_slug") == product_slug
            ):
                client_ref = entry.get("client_reference_id")
                break
    except (OSError, json.JSONDecodeError):
        pass

    return affiliate_url, client_ref


# -- Candidate processing pipeline -------------------------------
def process_product(product: dict) -> dict | None:
    """Run the full pipeline for one product. Returns brief dict or None."""
    slug = product["slug"]
    print(f"\n=== {slug} ===")

    raw_cands = research_candidates(product)
    print(f"  LLM returned {len(raw_cands)} raw candidate(s)")

    briefs: list[dict] = []
    for raw in raw_cands:
        if not isinstance(raw, dict):
            continue
        candidate_name = (raw.get("candidate_name") or "").strip()
        handle = sanitize_handle(raw.get("candidate_handle") or candidate_name)
        url = (raw.get("candidate_url") or "").strip()
        if not (candidate_name and handle and url):
            print(f"  SKIP — missing required field: {raw!r}")
            continue

        try:
            score = int(raw.get("audience_match_score") or 0)
        except (TypeError, ValueError):
            score = 0
        score = max(1, min(10, score)) if score else 5

        commission_pct = raw.get("commission_pct")
        try:
            commission_pct = int(commission_pct)
        except (TypeError, ValueError):
            commission_pct = DEFAULT_COMMISSION_PCT
        commission_pct = max(1, min(75, commission_pct))

        affiliate_url, client_ref = generate_affiliate_link(handle, slug, commission_pct)
        if not affiliate_url:
            print(f"  SKIP {handle} — affiliate link generation failed")
            continue

        outreach_dm = draft_outreach_dm(product, raw, affiliate_url)
        if not outreach_dm:
            print(f"  SKIP {handle} — DM draft failed")
            continue

        briefs.append({
            "candidate_name": candidate_name,
            "candidate_handle": handle,
            "candidate_url": url,
            "platform": raw.get("platform", ""),
            "audience": raw.get("audience", ""),
            "audience_match_score": score,
            "specific_reference": raw.get("specific_reference", ""),
            "commission_pct": commission_pct,
            "requires_email_outreach": bool(raw.get("requires_email_outreach", False)),
            "outreach_dm": outreach_dm,
            "affiliate_link": affiliate_url,
            "client_reference_id": client_ref,
            "status": "drafted",
            "added_at": now_utc().isoformat(),
        })
        print(f"  + {handle} (score {score}, commission {commission_pct}%)")

    if not briefs:
        print(f"  no usable candidates produced for {slug}")
        return None

    brief = {
        "version": 1,
        "product_slug": slug,
        "product_name": product["spec"].get("name", ""),
        "generated_at": now_utc().isoformat(),
        "candidates": briefs,
    }
    return brief


def write_brief_atomic(brief: dict) -> Path:
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    final = CANDIDATES_DIR / f"{brief['product_slug']}.json"
    tmp = final.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(brief, indent=2) + "\n")
    tmp.replace(final)
    return final


def safe_notify(channel: str, message: str) -> None:
    try:
        send_to_channel(channel, message)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"WARN: telegram dispatch failed: {exc}", file=sys.stderr)


def build_summary(briefs: list[dict], skipped: list[str]) -> str:
    if not briefs:
        return (
            "Partnerships scan complete — 0 candidate briefs produced this cycle.\n"
            f"Products inspected but no usable candidates: {len(skipped)}"
        )
    lines = ["Partnerships scan complete — weekly candidate briefs:"]
    for b in briefs:
        lines.append(
            f"  - {b['product_slug']}: {len(b['candidates'])} candidate(s) "
            f"(top score {max(c['audience_match_score'] for c in b['candidates'])})"
        )
    lines.append("")
    lines.append(f"Review at state/partnerships/candidates/")
    if skipped:
        lines.append(f"Skipped (no candidates returned): {len(skipped)}")
    return "\n".join(lines)


# -- Entry point --------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Partnerships Lead weekly scan")
    parser.add_argument(
        "--max-products",
        type=int,
        default=DEFAULT_MAX_PRODUCTS,
        help=f"Cap on products processed this run (default {DEFAULT_MAX_PRODUCTS}; "
        "bounds LLM cost for smoke tests).",
    )
    args = parser.parse_args()

    products = load_shippable_products()
    if not products:
        print("No shippable products found — nothing to scan.")
        return 0

    selected = products[: max(1, args.max_products)]
    print(
        f"Scanning {len(selected)} of {len(products)} shippable products "
        f"(max-products={args.max_products})."
    )

    briefs_written: list[dict] = []
    skipped: list[str] = []
    for product in selected:
        try:
            brief = process_product(product)
        except Exception as exc:  # pylint: disable=broad-except
            print(f"ERROR: {product['slug']} failed: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            skipped.append(product["slug"])
            continue
        if brief is None:
            skipped.append(product["slug"])
            continue
        path = write_brief_atomic(brief)
        print(f"wrote {path.relative_to(_REPO_ROOT)} ({len(brief['candidates'])} candidates)")
        briefs_written.append(brief)

    summary = build_summary(briefs_written, skipped)
    print("\n" + summary)
    safe_notify("marketing_reports", summary)

    total_candidates = sum(len(b["candidates"]) for b in briefs_written)
    print(
        f"\nDone. Products processed: {len(selected)}, "
        f"briefs written: {len(briefs_written)}, "
        f"total candidates: {total_candidates}, "
        f"skipped: {len(skipped)}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
