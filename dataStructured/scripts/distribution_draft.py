"""CEO-driven manual distribution path: generate a draft post + optionally send to founder for review.

Sub-project 5 (Phase 2). Sits alongside the automated distribution-agent — does not replace it.
Invoke when an item warrants extra care (first post to a new community, sensitive niche, founder wants final say).

LLM access uses claude_agent_sdk (CLI/OAuth) — same as the rest of trinity-agent. This is required
because TJ's ~/.profile intentionally does not export ANTHROPIC_API_KEY (Claude CLI uses OAuth via
~/.claude.json under his Max subscription; the Anthropic SDK would reject the OAuth token via API key).
"""
import anyio
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
QUEUE_FILE = WORKSPACE / "state" / "distribution-queue.json"
DRAFTS_DIR = WORKSPACE / "state" / "distribution-drafts"

CHANNELS = {"reddit", "twitter", "linkedin"}


def load_queue_item(item_id: str) -> dict:
    queue = json.loads(QUEUE_FILE.read_text())
    for item in queue.get("items", []):
        if item.get("id") == item_id:
            return item
    raise SystemExit(f"item_id {item_id!r} not found in distribution-queue.json")


def _build_prompt(item: dict, channel: str) -> str:
    name = item["name"]
    audience = item.get("audience", "")
    stripe_url = item.get("stripe_payment_link_url", "")
    gumroad_url = item.get("gumroad_url") or item.get("gumroad_listing_url", "")
    price = item.get("price_usd", 0)

    if channel == "reddit":
        return (
            f"Draft a Reddit post for this product. Recommend 1-3 subreddits where it'd be welcome (avoid spammy subs; prefer niche-relevant). Then a non-promotional title and a body that gives genuine value while disclosing the product. No emoji. Plain text.\n\n"
            f"Product: {name}\nAudience: {audience}\nPrice: ${price}\nStripe link: {stripe_url}\nGumroad link: {gumroad_url}\n\n"
            f"Return ONLY a JSON object (no prose, no code fences) with shape: "
            f'{{"subreddit_suggestions": ["r/..."], "title": "...", "body": "..."}}'
        )
    if channel == "twitter":
        return (
            f"Draft a 3-5 tweet thread for this product. First tweet: the data point that makes the audience care. Middle tweets: the value. Last tweet: link + price. No emoji except 1 in tweet 1 if it really fits.\n\n"
            f"Product: {name}\nAudience: {audience}\nPrice: ${price}\nStripe link: {stripe_url}\n\n"
            f"Return ONLY a JSON object (no prose, no code fences) with shape: "
            f'{{"thread": ["tweet1", "tweet2"]}}'
        )
    if channel == "linkedin":
        return (
            f"Draft a LinkedIn post for this product (professional tone, 100-200 words). Lead with industry insight, not the product. Soft-mention the dataset at the end with the link. No hashtags spam (max 3).\n\n"
            f"Product: {name}\nAudience: {audience}\nPrice: ${price}\nStripe link: {stripe_url}\n\n"
            f"Return ONLY a JSON object (no prose, no code fences) with shape: "
            f'{{"text": "..."}}'
        )
    raise SystemExit(f"channel must be one of {CHANNELS}")


def _extract_json(raw: str) -> dict:
    """Pull a JSON object out of an LLM response that may include prose or fences."""
    raw = raw.strip()
    # Strip code fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines[1:])
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Last resort: grab the first {...} block
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


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
        allowed_tools=[],  # no tool use — pure text completion
        system_prompt="You generate concise marketing copy for public-data products. You return ONLY a JSON object — no prose, no code fences, no commentary.",
    )

    chunks: list[str] = []
    async for msg in query(prompt=prompt, options=opts):
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    chunks.append(block.text)
    return "".join(chunks)


def generate_draft(item: dict, channel: str) -> dict:
    """Generate channel-appropriate draft text via Claude (CLI/OAuth-backed).

    Returns dict with keys depending on channel:
      - reddit: {"subreddit_suggestions": [str], "title": str, "body": str}
      - twitter: {"thread": [str]}  # list of tweets in thread
      - linkedin: {"text": str}
    """
    prompt = _build_prompt(item, channel)
    raw = anyio.run(_query_claude_sdk, prompt)
    return _extract_json(raw)


def send_for_approval(item: dict, channel: str, draft: dict, draft_id: str) -> bool:
    """Send the draft to founder via Telegram DM. Returns True on success."""
    try:
        from trinity.telegram.api import TelegramAPI
    except ImportError:
        print("trinity.telegram.api not importable — skipping Telegram send", file=sys.stderr)
        return False

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN not set — skipping Telegram send", file=sys.stderr)
        return False

    founder_chat_id = 1366707521
    api = TelegramAPI(token)

    summary_body = (
        f"📝 Distribution draft for review\n\n"
        f"Item: {item['name']}\n"
        f"Channel: {channel}\n"
        f"Draft ID: {draft_id}\n\n"
        f"---\n"
        f"{json.dumps(draft, indent=2)}\n"
        f"---\n\n"
        f"Reply 'approve {draft_id}' or 'decline {draft_id}'."
    )
    api.send_message(founder_chat_id, summary_body)
    return True


def main():
    parser = argparse.ArgumentParser(description="CEO manual distribution draft")
    parser.add_argument("--item-id", required=True, help="ID from distribution-queue.json")
    parser.add_argument("--channel", required=True, choices=sorted(CHANNELS))
    parser.add_argument("--send-for-approval", action="store_true", help="Also send draft to founder Telegram DM")
    args = parser.parse_args()

    item = load_queue_item(args.item_id)
    draft = generate_draft(item, args.channel)

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    draft_id = f"{args.item_id}-{args.channel}-{ts}"
    draft_path = DRAFTS_DIR / f"{draft_id}.json"
    draft_path.write_text(json.dumps({
        "draft_id": draft_id,
        "item_id": args.item_id,
        "channel": args.channel,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_approval" if args.send_for_approval else "draft_only",
        "draft": draft,
    }, indent=2) + "\n")

    print(f"Draft saved: {draft_path}")
    print(json.dumps(draft, indent=2))

    if args.send_for_approval:
        ok = send_for_approval(item, args.channel, draft, draft_id)
        print(f"Telegram approval request sent: {ok}")


if __name__ == "__main__":
    main()
