"""Thin wrapper around the Telegram Bot HTTP API."""
from __future__ import annotations

import logging

import requests

log = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────────────────────────

def _chunk_text(text: str, max_len: int = 4096) -> list[str]:
    """Split *text* into chunks that each fit within Telegram's limit.

    Prefers splitting at newline boundaries so messages remain readable.
    """
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split at the last newline inside the window.
        split_at = text.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            # No good newline — hard-cut at the limit.
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


# ── TelegramAPI ─────────────────────────────────────────────────────

class TelegramAPI:
    """Stateless helper that talks to ``https://api.telegram.org/bot<token>``."""

    def __init__(self, token: str):
        self.token = token
        self.base = f"https://api.telegram.org/bot{token}"
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    def reset_session(self) -> None:
        """Close the current HTTP session and create a fresh one.

        Used by the poll loop to clear a potentially poisoned connection
        pool after repeated network failures.
        """
        try:
            self.session.close()
        except Exception:
            pass
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"

    # ── Read methods ────────────────────────────────────────────────

    def get_me(self) -> dict:
        """Return the bot's own user object (``getMe``)."""
        try:
            r = self.session.get(f"{self.base}/getMe")
            r.raise_for_status()
            return r.json()["result"]
        except Exception:
            log.exception("getMe failed")
            return {}

    def get_updates(self, offset: int = 0, timeout: int = 30) -> list[dict]:
        """Long-poll for new updates starting after *offset*.

        Returns a (possibly empty) list of update dicts on success or
        long-poll timeout. All other errors (HTTP, connection, DNS) are
        re-raised so the caller's retry handler can respond with proper
        backoff. Swallowing them here silently wedges the bot.
        """
        try:
            r = self.session.get(
                f"{self.base}/getUpdates",
                params={
                    "offset": offset,
                    "timeout": timeout,
                    "allowed_updates": '["message"]',
                },
                timeout=timeout + 10,
            )
            r.raise_for_status()
            return r.json().get("result", [])
        except requests.exceptions.Timeout:
            # Perfectly normal for long-poll — just return empty.
            return []

    # ── Write methods ───────────────────────────────────────────────

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_to: int | None = None,
        parse_mode: str | None = None,
    ) -> dict:
        """Send a text message, auto-chunking at 4096 chars.

        Returns the Telegram ``Message`` result dict for the *last* chunk
        sent, or ``{}`` if every chunk failed.
        """
        chunks = _chunk_text(text, 4096)
        result: dict = {}
        for i, chunk in enumerate(chunks):
            payload: dict = {"chat_id": chat_id, "text": chunk}
            if reply_to and i == 0:
                payload["reply_to_message_id"] = reply_to
            if parse_mode:
                payload["parse_mode"] = parse_mode
            try:
                r = self.session.post(f"{self.base}/sendMessage", json=payload)
                if r.status_code == 200:
                    result = r.json().get("result", {})
                else:
                    log.warning("sendMessage failed (%s): %s", r.status_code, r.text[:200])
                    # Retry without parse_mode — Markdown can fail on unescaped chars.
                    if parse_mode:
                        payload.pop("parse_mode", None)
                        r2 = self.session.post(f"{self.base}/sendMessage", json=payload)
                        if r2.status_code == 200:
                            result = r2.json().get("result", {})
            except Exception:
                log.exception("sendMessage error for chat %s", chat_id)
        return result

    def edit_message(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        parse_mode: str | None = None,
    ) -> dict:
        """Edit an existing message in-place.

        Text is silently truncated to 4096 chars.  Telegram API errors are
        logged but never raised — the bot must keep running.
        """
        payload: dict = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text[:4096],
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            r = self.session.post(f"{self.base}/editMessageText", json=payload)
            if r.status_code == 200:
                return r.json().get("result", {})
            log.warning("editMessageText failed (%s): %s", r.status_code, r.text[:200])
        except Exception:
            log.exception("editMessageText error for chat %s msg %s", chat_id, message_id)
        return {}

    def send_chat_action(self, chat_id: int | str, action: str = "typing") -> None:
        """Send a chat action (e.g. ``typing``) indicator.

        Best-effort — errors are swallowed.
        """
        try:
            self.session.post(
                f"{self.base}/sendChatAction",
                json={"chat_id": chat_id, "action": action},
            )
        except Exception:
            pass  # truly fire-and-forget

    def delete_webhook(self, drop_pending: bool = False) -> None:
        """Delete any active webhook and optionally drop pending updates.

        Also forces the server to release a lingering ``getUpdates``
        long-poll from a previous consumer.
        """
        try:
            self.session.post(
                f"{self.base}/deleteWebhook",
                json={"drop_pending_updates": drop_pending},
            )
        except Exception:
            log.exception("deleteWebhook failed")
