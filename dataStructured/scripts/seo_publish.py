"""SEO Operator publishing script.

Runs Tuesday + Friday at 08:00 ET via the trinity scheduler `seo_publish` cycle.

Algorithm:
1. Scan `state/products/*/{spec.json,launch-report.json}` for FULLY_SHIPPED /
   compliance-PASS products (mirrors site/lib/products.ts filter logic).
2. Scan `state/blog/posts/*.md` to know which (product_slug, content_type)
   pairs have already been covered.
3. Pick one uncovered (product, content_type) pair, prioritising high
   row_count + recently-launched.
4. Use claude_agent_sdk.query (CLI/OAuth — same pattern as
   scripts/distribution_draft.py) to draft a 1000-1200-word post.
5. Write `state/blog/posts/{YYYY-MM-DD}-{slug}.md` with frontmatter + body.
6. Notify `marketing_reports` Telegram channel with title + live URL.

Standalone usage:
    source ~/.profile && python scripts/seo_publish.py

Output (last line, stdout):
    wrote state/blog/posts/<date>-<slug>.md
"""
from __future__ import annotations

import anyio
import json
import re
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


# -- Paths -----------------------------------------------------------
STATE_DIR = _REPO_ROOT / "state"
PRODUCTS_DIR = STATE_DIR / "products"
POSTS_DIR = STATE_DIR / "blog" / "posts"

# -- Config ----------------------------------------------------------
CONTENT_TYPES = ["how_to_use", "vs_commercial", "monthly_refresh"]
TARGET_WORDS_MIN = 1000
TARGET_WORDS_MAX = 1200
SITE_BASE_URL = "https://data.oefrenterprise.com"

SHIPPED_STATUSES = {
    "FULLY_SHIPPED",
    "SHIPPED",
    "SHIPPED_STRIPE_ONLY",
    "STRIPE_ONLY",
}


# -- Helpers ---------------------------------------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    """Turn a string into a URL-safe lowercase slug."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = text.strip("-")
    return text[:80] if text else "post"


def _parse_iso(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


# -- Product discovery -----------------------------------------------
def load_shippable_products() -> list[dict]:
    """Return list of {slug, spec, launch} for FULLY_SHIPPED + PASS products."""
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
        if not spec.get("name") or not spec.get("summary"):
            continue
        if not isinstance(spec.get("price_usd"), (int, float)):
            continue

        products.append({"slug": entry.name, "spec": spec, "launch": launch})

    return products


# -- Blog post discovery ---------------------------------------------
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_FM_FIELD_RE = re.compile(r"^([a-zA-Z_]+):\s*\"?(.*?)\"?\s*$")


def _parse_frontmatter(raw: str) -> dict[str, str]:
    """Very small YAML-frontmatter parser (key: value pairs only)."""
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fm = _FM_FIELD_RE.match(line)
        if fm:
            out[fm.group(1)] = fm.group(2)
    return out


def load_existing_posts() -> list[dict[str, str]]:
    """Return list of parsed frontmatter dicts from existing posts."""
    if not POSTS_DIR.exists():
        return []
    posts: list[dict[str, str]] = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        try:
            raw = path.read_text()
        except OSError:
            continue
        fm = _parse_frontmatter(raw)
        if fm:
            posts.append(fm)
    return posts


def covered_pairs(posts: list[dict[str, str]]) -> set[tuple[str, str]]:
    """Return set of (product_slug, content_type) pairs already published."""
    return {
        (p.get("product_slug", ""), p.get("content_type", ""))
        for p in posts
        if p.get("product_slug") and p.get("content_type")
    }


# -- Pair selection --------------------------------------------------
def pick_pair(
    products: list[dict], covered: set[tuple[str, str]]
) -> tuple[dict, str] | None:
    """Pick highest-priority (product, content_type) pair not yet covered.

    Priority order:
      1. Higher row_count first
      2. More recently-launched (launch.created) second
      3. Earlier CONTENT_TYPES index third (how_to_use beats vs_commercial)
    """
    if not products:
        return None

    def sort_key(p: dict) -> tuple:
        row_count = p["spec"].get("row_count") or 0
        created = _parse_iso(p["launch"].get("created", "")) or datetime.min.replace(
            tzinfo=timezone.utc
        )
        return (-row_count, -created.timestamp())

    for product in sorted(products, key=sort_key):
        for content_type in CONTENT_TYPES:
            if (product["slug"], content_type) not in covered:
                return product, content_type
    return None


# -- Claude SDK draft -----------------------------------------------
def _build_prompt(product: dict, content_type: str) -> str:
    spec = product["spec"]
    name = spec.get("name", "")
    summary = spec.get("summary", "")
    audience = spec.get("audience", "")
    source = spec.get("source", "")
    row_count = spec.get("row_count", "?")
    price = spec.get("price_usd", "?")
    bonus_stack = spec.get("bonus_stack", [])
    bonus_text = "\n".join(f"  - {b}" for b in bonus_stack) if bonus_stack else "  (none)"

    type_directive = {
        "how_to_use": (
            "Content type: HOW-TO USE GUIDE.\n"
            "Write a practical guide titled 'How to use {dataset} for {specific use case}'. "
            "Choose ONE concrete use case implied by the audience. Walk through what fields matter "
            "for that use case, how to load/filter the CSV, and what a first-week workflow looks like."
        ),
        "vs_commercial": (
            "Content type: HONEST COMPARISON.\n"
            "Write '{dataset} vs {one well-known commercial alternative}'. Pick a real, public "
            "commercial competitor. Use only real, public pricing — if you cannot recall the exact "
            "current price, describe the pricing model qualitatively (e.g. 'enterprise quote-based'). "
            "Compare: coverage, freshness, source citation, format, total cost. Be fair — note where "
            "the commercial tool genuinely wins (e.g. enrichment, intent signals)."
        ),
        "monthly_refresh": (
            "Content type: REFRESH NOTES.\n"
            "Write 'What's in the {month} {year} {dataset} refresh'. Cover: row count this cycle, "
            "what changed since the prior cut (state breakdowns, fleet-size distribution, top growth "
            "areas), and what buyers should do with this refresh."
        ),
    }[content_type]

    today = now_utc()
    month_year = today.strftime("%B %Y")

    return f"""You are the SEO Operator for DataStructured, an autonomous public-data-as-a-product company.

Write ONE blog post of {TARGET_WORDS_MIN}-{TARGET_WORDS_MAX} words for the product below.

PRODUCT:
  name: {name}
  slug: {spec.get("slug", "")}
  summary: {summary}
  audience: {audience}
  source: {source}
  row_count: {row_count}
  price_usd: {price}
  bonus_stack:
{bonus_text}

CONTEXT:
  today: {today.strftime("%Y-%m-%d")}
  month_year: {month_year}
  product_url: {SITE_BASE_URL}/products/{spec.get("slug", "")}

{type_directive}

HARD RULES (failure = rejected post):
  - No fabricated statistics. Cite the public source ({source}) when stating numbers about the dataset.
  - No discount language ("limited time", "X% off", "today only", "sale" — all banned).
  - No outbound links to commercial competitors' affiliate programs.
  - One clear CTA at the end pointing to {SITE_BASE_URL}/products/{spec.get("slug", "")}.
  - Plain markdown only. No HTML, no MDX, no JS, no script tags.
  - Use H2 (##) and H3 (###) for structure. The H1 is the post title (set in frontmatter; do NOT repeat as # in body).

OUTPUT FORMAT (return EXACTLY this — frontmatter + body — no code fences, no commentary):

---
title: "PUT TITLE HERE — make it a long-tail buyer-intent phrase"
slug: "put-url-safe-slug-here"
description: "Meta description, 140-155 characters, sentence case, ends with a period."
keyword: "primary keyword phrase, 2-5 words, lowercase"
product_slug: "{spec.get("slug", "")}"
published_at: "{today.strftime("%Y-%m-%dT08:00:00Z")}"
content_type: "{content_type}"
---

(Your {TARGET_WORDS_MIN}-{TARGET_WORDS_MAX}-word post body in plain markdown starts here. Use ## H2s. End with a clear CTA paragraph linking to {SITE_BASE_URL}/products/{spec.get("slug", "")}.)
"""


async def _query_claude_sdk(prompt: str) -> str:
    """Run a one-shot query via claude_agent_sdk (uses local Claude CLI / OAuth)."""
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
        system_prompt=(
            "You are a long-form SEO writer for a public-data products company. "
            "Return ONLY the requested markdown — frontmatter + body — with no preface, "
            "no code fences, no commentary outside the document."
        ),
    )

    chunks: list[str] = []
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    return "".join(chunks)


def generate_post(product: dict, content_type: str) -> str:
    """Generate full markdown post (frontmatter + body) via Claude SDK."""
    prompt = _build_prompt(product, content_type)
    raw = anyio.run(_query_claude_sdk, prompt)
    return _clean_post(raw)


def _clean_post(raw: str) -> str:
    """Strip code fences if the LLM wrapped its output despite instructions."""
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        # Drop first ``` line
        lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return raw + ("\n" if not raw.endswith("\n") else "")


# -- Frontmatter validation -----------------------------------------
REQUIRED_FRONTMATTER = {
    "title",
    "slug",
    "description",
    "keyword",
    "product_slug",
    "published_at",
    "content_type",
}


def validate_post(raw: str, expected_product_slug: str, expected_type: str) -> dict[str, str]:
    """Parse and validate the post's frontmatter. Returns parsed fm dict.

    Raises RuntimeError with a useful message on validation failure so the
    daemon log captures what went wrong without writing a broken file.
    """
    fm = _parse_frontmatter(raw)
    if not fm:
        raise RuntimeError("post is missing YAML frontmatter (--- ... ---)")
    missing = REQUIRED_FRONTMATTER - set(fm.keys())
    if missing:
        raise RuntimeError(f"frontmatter missing required keys: {sorted(missing)}")
    if fm.get("product_slug") != expected_product_slug:
        raise RuntimeError(
            f"frontmatter product_slug={fm.get('product_slug')!r} "
            f"does not match expected {expected_product_slug!r}"
        )
    if fm.get("content_type") != expected_type:
        raise RuntimeError(
            f"frontmatter content_type={fm.get('content_type')!r} "
            f"does not match expected {expected_type!r}"
        )
    if not fm.get("title"):
        raise RuntimeError("frontmatter title is empty")
    return fm


# -- File write + notify -------------------------------------------
def write_post_atomic(raw_md: str, fm: dict[str, str]) -> Path:
    """Write the post to state/blog/posts/{date}-{slug}.md atomically."""
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = now_utc().date().isoformat()
    safe_slug = slugify(fm.get("slug", "") or fm.get("title", "post"))
    filename = f"{date_str}-{safe_slug}.md"
    final = POSTS_DIR / filename
    tmp = final.with_suffix(".md.tmp")
    tmp.write_text(raw_md)
    tmp.replace(final)
    return final


def safe_notify(channel: str, message: str) -> None:
    try:
        send_to_channel(channel, message)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"WARN: telegram dispatch failed: {exc}", file=sys.stderr)


def build_summary(fm: dict[str, str], filepath: Path) -> str:
    title = fm.get("title", "(no title)")
    slug = fm.get("slug", "")
    product_slug = fm.get("product_slug", "")
    return (
        f"SEO post published\n"
        f"Title: {title}\n"
        f"URL: {SITE_BASE_URL}/blog/{slug}\n"
        f"Product: {product_slug}\n"
        f"File: {filepath.relative_to(_REPO_ROOT)}"
    )


# -- Entry point ----------------------------------------------------
def main() -> int:
    products = load_shippable_products()
    if not products:
        print("No shippable products found — nothing to publish.")
        return 0

    existing = load_existing_posts()
    covered = covered_pairs(existing)

    pick = pick_pair(products, covered)
    if pick is None:
        print(
            "All (product, content_type) pairs already covered "
            f"({len(products)} products x {len(CONTENT_TYPES)} types = "
            f"{len(products) * len(CONTENT_TYPES)} pairs, {len(covered)} covered)."
        )
        return 0

    product, content_type = pick
    print(
        f"Drafting post: product={product['slug']} "
        f"content_type={content_type}"
    )

    try:
        raw_md = generate_post(product, content_type)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"ERROR: generate_post failed: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    try:
        fm = validate_post(raw_md, product["slug"], content_type)
    except Exception as exc:  # pylint: disable=broad-except
        print(f"ERROR: validate_post failed: {exc}", file=sys.stderr)
        print("--- raw output (first 500 chars) ---", file=sys.stderr)
        print(raw_md[:500], file=sys.stderr)
        return 1

    path = write_post_atomic(raw_md, fm)
    print(f"wrote {path.relative_to(_REPO_ROOT)}")
    print(f"title: {fm.get('title')}")

    safe_notify("marketing_reports", build_summary(fm, path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
