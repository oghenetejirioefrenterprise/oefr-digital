#!/usr/bin/env python3
"""SEO publish cycle — DataStructured seo-operator.

Picks an uncovered (product, content_type) pair, drafts a 1000-1200-word
SEO blog post grounded in the product's real spec data, writes it to
state/blog/posts/{today}-{slug}.md with frontmatter matching the existing
posts, and routes a summary to the marketing_reports Telegram channel
(falling back to the founder DM if that channel is not yet configured).

Scheduled via trinity.toml [scheduler.cycles.seo_publish] — 08:00 ET Tue+Fri.

Usage:
    python scripts/seo_publish.py            # pick, draft, write, notify
    python scripts/seo_publish.py --dry-run  # draft + print, do not write or notify
    python scripts/seo_publish.py --product <slug> --content-type <type>

Content types (mirrors Phase 3 design doc 3.4):
    how_to          -> "How to use {dataset} for {use case}"
    vs_commercial   -> "{dataset} vs commercial alternatives"
    monthly_refresh -> "What's in the latest {dataset} refresh"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTS_DIR = REPO_ROOT / "state" / "products"
POSTS_DIR = REPO_ROOT / "state" / "blog" / "posts"
TRINITY_TOML = REPO_ROOT / "trinity.toml"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from lib.slug import slugify  # noqa: E402

# ── Config ────────────────────────────────────────────────────────
# Statuses that mean the product is live / sellable and therefore worth
# writing SEO content for. Drafts and blocked products are excluded.
SELLABLE_STATUSES = {
    "SHIPPED",
    "FULLY_SHIPPED",
    "SHIPPING",
    "READY_TO_SHIP",
    "APPROVED",
}

# Content-type priority: which angle to write first for a given product.
# vs_commercial converts best (high commercial intent), how_to builds
# top-of-funnel, monthly_refresh keeps the niche keyword fresh.
CONTENT_TYPES = ["vs_commercial", "how_to", "monthly_refresh"]

CONTENT_TYPE_BRIEF = {
    "vs_commercial": (
        "Angle: \"{name} vs commercial alternatives.\" Compare this public-data "
        "product against the expensive commercial platforms that repackage the "
        "same government source. Cover coverage/completeness, data freshness, "
        "source citation/verifiability, and total cost. Be specific and fair — "
        "name the trade-offs where the commercial tool genuinely wins (e.g. "
        "enrichment, UI, ongoing updates), then show where buying the raw "
        "public dataset at a one-time price wins."
    ),
    "how_to": (
        "Angle: \"How to use {name} for a concrete use case.\" Pick the single "
        "strongest use case implied by the audience, then walk the reader "
        "step-by-step: what columns matter, how to segment/filter the CSV, how "
        "to load it into a CRM or outreach tool, and how to turn rows into "
        "results. Practical and tactical — the reader should be able to act "
        "today."
    ),
    "monthly_refresh": (
        "Angle: \"What's in the latest {name} refresh.\" Announce the current "
        "data cut, break down the record counts and segments, explain what "
        "changed vs a prior refresh at a high level, and remind the reader who "
        "this dataset is for and why fresh public-source data matters for "
        "outbound."
    ),
}

# Telegram (mirrors scripts/cfo_digest.py conventions).
FOUNDER_DM_CHAT_ID = "1366707521"

# LLM
# Provider auto-selection: prefer NVIDIA NIM (free via existing access,
# OpenAI-compatible) when NVIDIA_API_KEY is present, else fall back to OpenAI.
# Override with SEO_LLM_PROVIDER (nvidia|openai) and SEO_LLM_MODEL.
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "meta/llama-3.3-70b-instruct"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


# ── Env ───────────────────────────────────────────────────────────
def ensure_env(*names: str) -> None:
    """Source ~/.profile into os.environ for any requested vars not already set."""
    missing = [n for n in names if not os.environ.get(n)]
    if not missing:
        return
    try:
        result = subprocess.run(
            ["bash", "-c", "source ~/.profile && env"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        for line in result.stdout.splitlines():
            k, _, v = line.partition("=")
            if k in missing and v:
                os.environ.setdefault(k, v)
    except Exception as exc:  # pragma: no cover - best-effort sourcing
        print(f"[WARN] could not source ~/.profile: {exc}", file=sys.stderr)


# ── trinity.toml channels ─────────────────────────────────────────
def load_channels() -> dict:
    """Return [telegram.channels] from trinity.toml (empty dict on failure)."""
    try:
        import tomllib

        with open(TRINITY_TOML, "rb") as fh:
            data = tomllib.load(fh)
        return data.get("telegram", {}).get("channels", {}) or {}
    except Exception as exc:
        print(f"[WARN] could not read telegram channels: {exc}", file=sys.stderr)
        return {}


def marketing_chat_id(channels: dict) -> str:
    """marketing_reports if configured, else founder_dm, else hardcoded founder DM."""
    target = (channels.get("marketing_reports") or "").strip()
    if target:
        return target
    fallback = (channels.get("founder_dm") or "").strip()
    return fallback or FOUNDER_DM_CHAT_ID


# ── Product discovery ─────────────────────────────────────────────
def discover_products() -> list[dict]:
    """Load sellable product specs that have a known record count."""
    products: list[dict] = []
    if not PRODUCTS_DIR.is_dir():
        return products
    for spec_path in sorted(PRODUCTS_DIR.glob("*/spec.json")):
        try:
            spec = json.loads(spec_path.read_text())
        except Exception as exc:
            print(f"[WARN] skipping unreadable spec {spec_path}: {exc}", file=sys.stderr)
            continue
        status = str(spec.get("status", "")).upper()
        if status not in SELLABLE_STATUSES:
            continue
        row_count = spec.get("row_count")
        if not isinstance(row_count, int) or row_count <= 0:
            # Cannot ground numbers without a real record count.
            continue
        if not spec.get("slug"):
            continue
        products.append(spec)
    return products


# ── Coverage ──────────────────────────────────────────────────────
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict:
    """Minimal YAML-ish frontmatter parser for `key: "value"` lines."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip().strip('"').strip("'")
        fm[key.strip()] = val
    return fm


def covered_pairs() -> set[tuple[str, str]]:
    """Set of (product_slug, content_type) pairs already published."""
    covered: set[tuple[str, str]] = set()
    if not POSTS_DIR.is_dir():
        return covered
    for post in POSTS_DIR.glob("*.md"):
        fm = parse_frontmatter(post.read_text())
        ps = fm.get("product_slug")
        ct = fm.get("content_type")
        if ps and ct:
            covered.add((ps, ct))
    return covered


def post_count_by_product() -> dict[str, int]:
    counts: dict[str, int] = {}
    if not POSTS_DIR.is_dir():
        return counts
    for post in POSTS_DIR.glob("*.md"):
        fm = parse_frontmatter(post.read_text())
        ps = fm.get("product_slug")
        if ps:
            counts[ps] = counts.get(ps, 0) + 1
    return counts


def pick_pair(products: list[dict]) -> tuple[dict, str] | None:
    """Pick an uncovered (product, content_type) pair.

    Strategy: spread coverage across the catalog first. Sort products by
    (existing post count, slug) so products with no posts are chosen before
    giving a second post to a product that already has one. Within a product,
    pick the first uncovered content type in priority order.
    """
    covered = covered_pairs()
    counts = post_count_by_product()
    ordered = sorted(products, key=lambda s: (counts.get(s["slug"], 0), s["slug"]))
    for spec in ordered:
        for ct in CONTENT_TYPES:
            if (spec["slug"], ct) not in covered:
                return spec, ct
    return None


# ── LLM drafting ──────────────────────────────────────────────────
def resolve_provider() -> str:
    """Return 'nvidia' or 'openai' based on env + available keys."""
    forced = (os.environ.get("SEO_LLM_PROVIDER") or "").strip().lower()
    if forced in ("nvidia", "openai"):
        return forced
    ensure_env("NVIDIA_API_KEY", "OPENAI_API_KEY")
    if os.environ.get("NVIDIA_API_KEY"):
        return "nvidia"
    return "openai"


def _make_client(provider: str):
    """Return (OpenAI-compatible client, model, supports_json_response_format)."""
    from openai import OpenAI

    override_model = (os.environ.get("SEO_LLM_MODEL") or "").strip()
    if provider == "nvidia":
        ensure_env("NVIDIA_API_KEY")
        key = os.environ.get("NVIDIA_API_KEY")
        if not key:
            raise RuntimeError("NVIDIA_API_KEY not set — cannot draft post")
        client = OpenAI(api_key=key, base_url=NVIDIA_BASE_URL)
        return client, (override_model or DEFAULT_NVIDIA_MODEL), False
    # openai
    ensure_env("OPENAI_API_KEY")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set — cannot draft post")
    return OpenAI(), (override_model or DEFAULT_OPENAI_MODEL), True


def _extract_json(text: str) -> dict:
    """Parse a JSON object from an LLM response, tolerating prose/fences."""
    text = text.strip()
    # Strip markdown code fences if present.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the first balanced {...} block.
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found in LLM response")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unbalanced JSON object in LLM response")


def build_prompt(spec: dict, content_type: str) -> tuple[str, str]:
    """Return (system, user) prompts grounded in the product's real spec."""
    facts = {
        "name": spec.get("name", spec["slug"]),
        "slug": spec["slug"],
        "row_count": spec.get("row_count"),
        "column_count": spec.get("column_count"),
        "price_usd": spec.get("price_usd"),
        "source": spec.get("source", ""),
        "audience": spec.get("audience", ""),
        "summary": spec.get("summary", ""),
        "format": spec.get("format", "one_time"),
        "deliverable": spec.get("deliverable", "csv"),
    }
    brief = CONTENT_TYPE_BRIEF[content_type].format(name=facts["name"])

    system = (
        "You are an expert B2B SEO content writer for DataStructured, a company "
        "that packages official public/government datasets into affordable, "
        "instant-download CSV products. Your posts are accurate, specific, and "
        "non-hype. CRITICAL: only use the numeric facts provided to you (record "
        "counts, prices, column counts, source). Never invent statistics, "
        "competitor prices, or record counts you were not given. When you "
        "estimate or generalize, say so explicitly. Write in confident, "
        "practical American business English. Use markdown with ## section "
        "headings. Do NOT include a top-level # title or any frontmatter — the "
        "body only."
    )

    user = (
        f"Write a 1000-1200 word SEO blog post.\n\n"
        f"{brief}\n\n"
        f"=== GROUND-TRUTH FACTS (use only these for numbers) ===\n"
        f"Product name: {facts['name']}\n"
        f"Records: {facts['row_count']:,}\n"
        f"Columns/fields: {facts['column_count']}\n"
        f"Price: ${facts['price_usd']} ({facts['format']}, {facts['deliverable']})\n"
        f"Official source: {facts['source']}\n"
        f"Target audience: {facts['audience']}\n"
        f"Product summary: {facts['summary']}\n"
        f"=======================================================\n\n"
        "Output EXACTLY in the following delimited format and nothing else "
        "(no JSON, no code fences, no preamble):\n\n"
        "TITLE: <SEO title, <= 65 chars ideally, includes the primary keyword>\n"
        "DESCRIPTION: <meta description, 140-160 chars>\n"
        "KEYWORD: <the single primary target keyword phrase, lowercase>\n"
        "BODY:\n"
        "<the full markdown post body — 1000-1200 words, 4-7 ## section "
        "headings, no top-level # title>\n\n"
        "The body must open with a 2-3 sentence hook addressing the reader's "
        "buying intent and close with a short call to action pointing to the "
        "dataset. Be specific and cite the official source by name. IMPORTANT: "
        "the body MUST be at least 1000 words — write in full, substantive "
        "paragraphs and do not stop early."
    )
    return system, user


DELIM_RE = re.compile(
    r"TITLE:\s*(?P<title>.+?)\s*\n+"
    r"DESCRIPTION:\s*(?P<description>.+?)\s*\n+"
    r"KEYWORD:\s*(?P<keyword>.+?)\s*\n+"
    r"(?:BODY:\s*\n+)?(?P<body>.*)$",
    re.DOTALL | re.IGNORECASE,
)


def parse_delimited(text: str) -> dict:
    """Parse the TITLE/DESCRIPTION/KEYWORD/BODY delimited LLM response."""
    text = text.strip()
    # Strip an outer code fence if the model wrapped everything.
    fence = re.match(r"^```[a-zA-Z]*\s*\n(.*)\n```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    m = DELIM_RE.search(text)
    if not m:
        raise ValueError("LLM response did not match expected delimited format")
    return {
        "title": m.group("title").strip().strip('"'),
        "description": m.group("description").strip().strip('"'),
        "keyword": m.group("keyword").strip().strip('"'),
        "body": m.group("body").strip(),
    }


def draft_post(spec: dict, content_type: str) -> dict:
    provider = resolve_provider()
    client, model, supports_json_fmt = _make_client(provider)
    print(f"[INFO] drafting via {provider} ({model})")
    system, user = build_prompt(spec, content_type)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
        max_tokens=4000,
    )
    raw = resp.choices[0].message.content
    data = parse_delimited(raw)
    for key in ("title", "description", "keyword", "body"):
        if not str(data.get(key, "")).strip():
            raise ValueError(f"LLM response missing required field: {key}")
    data["title"] = data["title"].strip()
    data["description"] = data["description"].strip()
    data["keyword"] = data["keyword"].strip().lower()
    data["body"] = data["body"].strip()

    # Length enforcement: one expansion pass if the body undershoots target.
    wc = word_count(data["body"])
    if wc < 1000:
        print(f"[INFO] body {wc} words (< 1000) — requesting expansion pass")
        expanded = expand_body(client, model, spec, content_type, data["body"], wc)
        if word_count(expanded) > wc:
            data["body"] = expanded
    return data


def expand_body(client, model, spec: dict, content_type: str, body: str, current_wc: int) -> str:
    """Ask the model to expand an under-length body to 1000-1200 words."""
    facts = (
        f"Records: {spec.get('row_count'):,} | Columns: {spec.get('column_count')} | "
        f"Price: ${spec.get('price_usd')} | Source: {spec.get('source', '')}"
    )
    prompt = (
        f"The markdown blog post below is only {current_wc} words. Expand it to "
        "between 1000 and 1200 words by adding depth, concrete detail, worked "
        "examples, and 1-2 additional ## sections where useful. Keep the "
        "existing structure and tone, keep it accurate, and ONLY use these "
        f"ground-truth numbers (never invent stats): {facts}.\n\n"
        "Return ONLY the full expanded markdown body — no title, no frontmatter, "
        "no commentary.\n\n"
        "=== CURRENT DRAFT ===\n" + body
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert B2B SEO content editor."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=4000,
    )
    out = resp.choices[0].message.content.strip()
    fence = re.match(r"^```[a-zA-Z]*\s*\n(.*)\n```$", out, re.DOTALL)
    if fence:
        out = fence.group(1).strip()
    return out


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


# ── Write + notify ────────────────────────────────────────────────
def build_markdown(spec: dict, content_type: str, draft: dict, published_at: str) -> tuple[str, str]:
    """Return (slug, full_markdown)."""
    slug = slugify(draft["title"])
    # Keep slugs reasonable in length.
    if len(slug) > 80:
        slug = slug[:80].rstrip("-")
    fm_lines = [
        "---",
        f'title: "{draft["title"].replace(chr(34), chr(39))}"',
        f'slug: "{slug}"',
        f'description: "{draft["description"].replace(chr(34), chr(39))}"',
        f'keyword: "{draft["keyword"].replace(chr(34), chr(39))}"',
        f'product_slug: "{spec["slug"]}"',
        f'published_at: "{published_at}"',
        f'content_type: "{content_type}"',
        "---",
        "",
    ]
    return slug, "\n".join(fm_lines) + draft["body"].rstrip() + "\n"


def send_telegram(message: str, chat_id: str) -> bool:
    ensure_env("TELEGRAM_BOT_TOKEN")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("[WARN] TELEGRAM_BOT_TOKEN not set — skipping Telegram", file=sys.stderr)
        return False
    import requests

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=30,
        )
        if resp.status_code == 200:
            print(f"[OK] Telegram summary sent to {chat_id}")
            return True
        if chat_id != FOUNDER_DM_CHAT_ID:
            print(
                f"[WARN] Telegram send failed ({resp.status_code}), retrying founder DM",
                file=sys.stderr,
            )
            return send_telegram(message, FOUNDER_DM_CHAT_ID)
        print(f"[ERROR] Telegram send failed: {resp.status_code} — {resp.text}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"[ERROR] Telegram send error: {exc}", file=sys.stderr)
        return False


def format_summary(spec: dict, content_type: str, slug: str, draft: dict, wc: int, post_path: Path) -> str:
    rel = post_path.relative_to(REPO_ROOT)
    return (
        "*📝 SEO post published*\n\n"
        f"*{draft['title']}*\n"
        f"Product: `{spec['slug']}`\n"
        f"Angle: `{content_type}`  ·  {wc} words\n"
        f"Keyword: _{draft['keyword']}_\n"
        f"File: `{rel}`\n\n"
        f"{draft['description']}"
    )


# ── Main ──────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(description="Publish today's SEO post.")
    parser.add_argument("--dry-run", action="store_true", help="draft + print, do not write or notify")
    parser.add_argument("--product", help="force a specific product slug")
    parser.add_argument("--content-type", choices=CONTENT_TYPES, help="force a content type")
    args = parser.parse_args()

    today = dt.date.today().isoformat()
    published_at = f"{today}T08:00:00Z"

    products = discover_products()
    if not products:
        print("[ERROR] no sellable products found — nothing to write about", file=sys.stderr)
        return 1
    print(f"[INFO] {len(products)} sellable products in catalog")

    # Select the (product, content_type) pair.
    if args.product and args.content_type:
        spec = next((s for s in products if s["slug"] == args.product), None)
        if not spec:
            print(f"[ERROR] product '{args.product}' not found among sellable products", file=sys.stderr)
            return 1
        content_type = args.content_type
    else:
        picked = pick_pair(products)
        if not picked:
            print("[INFO] all (product, content_type) pairs are covered — nothing to publish today")
            return 0
        spec, content_type = picked

    print(f"[INFO] selected pair: {spec['slug']} / {content_type}")

    # Draft.
    draft = draft_post(spec, content_type)
    wc = word_count(draft["body"])
    print(f"[INFO] drafted '{draft['title']}' — {wc} words")
    if wc < 850:
        print(f"[WARN] draft is short ({wc} words); target is 1000-1200", file=sys.stderr)

    slug, markdown = build_markdown(spec, content_type, draft, published_at)
    post_path = POSTS_DIR / f"{today}-{slug}.md"

    if args.dry_run:
        print("\n===== DRY RUN — POST PREVIEW =====\n")
        print(markdown)
        print("===== END PREVIEW =====")
        print(f"[DRY-RUN] would write to {post_path}")
        return 0

    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    if post_path.exists():
        print(f"[ERROR] {post_path} already exists — aborting to avoid overwrite", file=sys.stderr)
        return 1
    post_path.write_text(markdown)
    print(f"[OK] wrote {post_path}")

    # Notify.
    channels = load_channels()
    chat_id = marketing_chat_id(channels)
    summary = format_summary(spec, content_type, slug, draft, wc, post_path)
    send_telegram(summary, chat_id)

    print("[DONE] SEO publish cycle complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
