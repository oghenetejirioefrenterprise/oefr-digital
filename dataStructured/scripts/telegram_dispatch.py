"""Multi-channel Telegram dispatch helper.

Reads channel→chat_id mapping from trinity.toml's [telegram.channels] block.
Falls back to founder_dm if the requested channel is empty/unset, so messages
never get lost during the founder-setup gap.

Usage (CLI):
  python scripts/telegram_dispatch.py --channel compliance_flags --message "Halt: NPI dataset PII flag triggered"

Usage (import):
  from scripts.telegram_dispatch import send_to_channel
  send_to_channel("financial_alerts", "MRR snapshot: $29")
"""
import argparse
import os
import sys
import tomllib
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
CONFIG_PATH = WORKSPACE / "trinity.toml"


def _load_channels() -> dict:
    with open(CONFIG_PATH, "rb") as f:
        cfg = tomllib.load(f)
    channels = cfg.get("telegram", {}).get("channels", {})
    if not channels:
        raise RuntimeError(
            "No [telegram.channels] block in trinity.toml — run Phase 3 sub-project 5 setup first."
        )
    return channels


def _resolve_chat_id(channel: str) -> tuple[str, str]:
    """Returns (resolved_chat_id, route_used). Falls back to founder_dm if channel is empty."""
    channels = _load_channels()
    target = channels.get(channel, "")
    if target:
        return str(target), channel
    founder = channels.get("founder_dm", "")
    if not founder:
        raise RuntimeError(
            f"Channel {channel!r} unset and founder_dm fallback also unset in trinity.toml"
        )
    return str(founder), f"founder_dm (fallback for {channel})"


def send_to_channel(channel: str, message: str, *, prefix_channel_name: bool = True) -> dict:
    """Send `message` to the Telegram chat configured for `channel`.

    Returns the TelegramAPI response dict (includes `ok`, `result`).
    Raises on network / API failure.
    """
    chat_id, route = _resolve_chat_id(channel)
    body = f"[{channel}] {message}" if prefix_channel_name and route != channel else message

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

    try:
        from trinity.telegram.api import TelegramAPI
    except ImportError as exc:
        raise RuntimeError(f"trinity.telegram.api unavailable: {exc}") from exc

    api = TelegramAPI(token)
    result = api.send_message(int(chat_id), body)
    return {"ok": True, "route": route, "chat_id": chat_id, "telegram_result": result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Send to a configured Telegram channel")
    parser.add_argument("--channel", required=True, choices=["founder_dm", "compliance_flags", "financial_alerts", "marketing_reports"])
    parser.add_argument("--message", required=True)
    parser.add_argument("--no-prefix", action="store_true", help="Omit the [channel] prefix on fallback")
    args = parser.parse_args()

    try:
        res = send_to_channel(args.channel, args.message, prefix_channel_name=not args.no_prefix)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"sent to {res['route']} (chat_id={res['chat_id']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
