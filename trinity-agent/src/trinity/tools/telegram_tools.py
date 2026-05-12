"""Telegram messaging — send messages to Telegram groups via the Bot API."""
from __future__ import annotations

import requests

TELEGRAM_API = "https://api.telegram.org"
SEND_TIMEOUT = 15


def send_telegram(
    message: str,
    group: str,
    bot_token: str,
    groups: dict[str, dict],
) -> str:
    """Send a message to a Telegram group.

    *group* is a logical group name (e.g. "blockers").  Its chat_id is looked
    up from *groups*, which maps group names to dicts containing ``chat_id``.
    *bot_token* is the Telegram Bot API token.
    """
    if not bot_token:
        return "Error: bot_token is empty — cannot send Telegram message"

    group_cfg = groups.get(group)
    if group_cfg is None:
        available = ", ".join(sorted(groups.keys())) if groups else "(none)"
        return f"Unknown group '{group}'. Available groups: {available}"

    chat_id = group_cfg.get("chat_id", "")
    if not chat_id:
        return f"Group '{group}' has no chat_id configured"

    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=SEND_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            return f"Message sent to {group} (chat_id={chat_id})"
        return f"Telegram API error: {data.get('description', 'unknown error')}"
    except requests.RequestException as e:
        return f"Failed to send Telegram message: {e}"
