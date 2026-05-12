"""Access control — decides whether the bot should respond to a given update."""
from __future__ import annotations

import logging

from trinity.config import TelegramConfig

log = logging.getLogger(__name__)


class AccessControl:
    """Enforces DM policy, group allow-list, and mention requirements.

    Initialised once at bot startup and called for every incoming update.
    """

    def __init__(self, config: TelegramConfig, bot_username: str):
        self.dm_policy = config.acl.dm_policy            # "open" | "allowlist"
        self.group_policy = config.acl.group_policy       # "open" | "allowlist"
        self.allowed_users: set[str] = {
            str(uid) for uid in config.acl.allowed_users
        }
        self.bot_username = bot_username.lower()

        # Build a lookup of configured group chat_ids for fast membership
        # checks.  Keys are the *chat_id strings* from each group config.
        # Values are the group config objects themselves.
        self._groups: dict[str, object] = {}
        for _name, gcfg in config.groups.items():
            if gcfg.chat_id:
                self._groups[gcfg.chat_id] = gcfg

    # ── Public API ──────────────────────────────────────────────────

    def should_respond(self, update: dict) -> bool:
        """Return ``True`` if the bot should process this update."""
        msg = update.get("message", {})
        chat = msg.get("chat", {})
        user = msg.get("from", {})
        chat_type = chat.get("type", "")
        chat_id = str(chat.get("id", ""))
        user_id = str(user.get("id", ""))
        text = msg.get("text", "")

        # Skip messages with no text content.
        if not text:
            return False

        # ── Direct messages ─────────────────────────────────────────
        if chat_type == "private":
            if self.dm_policy == "open":
                return True
            # "allowlist" (or any other value) — only configured users.
            return user_id in self.allowed_users

        # ── Group / supergroup messages ─────────────────────────────
        if chat_type in ("group", "supergroup"):
            # Must be a group we know about.
            gcfg = self._groups.get(chat_id)
            if gcfg is None:
                return False

            # Enforce user allow-list when group_policy is "allowlist".
            if self.group_policy == "allowlist" and user_id not in self.allowed_users:
                return False

            # Honour the per-group mention requirement.
            if getattr(gcfg, "require_mention", True):
                return self._is_mentioned(msg)

            return True

        return False

    # ── Internals ───────────────────────────────────────────────────

    def _is_mentioned(self, msg: dict) -> bool:
        """Return ``True`` if the bot's @username appears in the message."""
        text = (msg.get("text") or "").lower()
        target = f"@{self.bot_username}"

        # Simple substring check (covers plain-text mentions).
        if target in text:
            return True

        # Walk through Telegram entities to catch parsed @mention entities.
        for entity in msg.get("entities", []):
            if entity.get("type") == "mention":
                start = entity["offset"]
                end = start + entity["length"]
                mention = text[start:end].lower()
                if mention == target:
                    return True

        return False
