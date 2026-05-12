"""Live status updates pushed to Telegram while the agent is working.

The :class:`StreamState` object receives callbacks from the agent layer
(text chunks and tool-use events) and periodically edits a Telegram
"status message" so the user can see progress in real time.

A background thread continuously sends ``typing`` chat actions so the
header indicator stays active for the full duration of the agent's work.
"""
from __future__ import annotations

import logging
import threading
import time

from trinity.memory.scrubber import MemoryFenceScrubber, scrub as scrub_text
from trinity.telegram.api import TelegramAPI

log = logging.getLogger(__name__)

# Human-readable labels for tool names
_TOOL_LABELS: dict[str, str] = {
    "read_file": "\U0001f4c4 Reading",        # 📄
    "write_file": "\u270d\ufe0f Writing",      # ✍️
    "edit_file": "\u270d\ufe0f Editing",       # ✍️
    "list_directory": "\U0001f4c2 Browsing",   # 📂
    "search_files": "\U0001f50d Searching",    # 🔍
    "search_content": "\U0001f50d Searching",  # 🔍
    "run_command": "\u25b6\ufe0f Running",     # ▶️
    "git_status": "\U0001f500 Git status",     # 🔀
    "git_diff": "\U0001f500 Git diff",         # 🔀
    "git_commit": "\U0001f4be Committing",     # 💾
    "web_search": "\U0001f310 Web search",     # 🌐
    "web_fetch": "\U0001f310 Fetching",        # 🌐
    "send_telegram": "\u2709\ufe0f Sending",   # ✉️
    "memory_store": "\U0001f9e0 Remembering",  # 🧠
    "memory_search": "\U0001f9e0 Recalling",   # 🧠
    "memory_forget": "\U0001f9e0 Forgetting",  # 🧠
    "memory_recall": "\U0001f9e0 Recalling",   # 🧠
    "memory_update": "\U0001f9e0 Updating",    # 🧠
    "memory_promote": "\U0001f9e0 Promoting",  # 🧠
    "log_issue": "\U0001f4cb Logging issue",   # 📋
    "log_decision": "\U0001f4cb Logging",      # 📋
    "log_audit": "\U0001f4cb Auditing",        # 📋
    "log_lesson": "\U0001f4cb Logging",        # 📋
    # Claude Agent SDK built-in tools
    "Read": "\U0001f4c4 Reading",              # 📄
    "Write": "\u270d\ufe0f Writing",           # ✍️
    "Edit": "\u270d\ufe0f Editing",            # ✍️
    "Bash": "\u25b6\ufe0f Running",            # ▶️
    "Glob": "\U0001f50d Searching",            # 🔍
    "Grep": "\U0001f50d Searching",            # 🔍
    "WebSearch": "\U0001f310 Web search",      # 🌐
    "WebFetch": "\U0001f310 Fetching",         # 🌐
    "LS": "\U0001f4c2 Browsing",               # 📂
    "retry": "\U0001f504 Retrying",             # 🔄
}


def _tool_label(tool_name: str, summary: str) -> str:
    """Build a human-readable line for a tool call."""
    label = _TOOL_LABELS.get(tool_name, f"\u2699\ufe0f {tool_name}")  # ⚙️ fallback
    if summary:
        short = summary[:60] + ("..." if len(summary) > 60 else "")
        return f"{label} `{short}`"
    return label


class StreamState:
    """Pushes activity updates from the agent layer to Telegram.

    Two modes:

    - ``mode="append"`` (default): each tool-use event becomes its own
      Telegram message and the final response is also a new message.
      Nothing is ever edited or deleted, so the chat preserves the full
      session log scrollback.
    - ``mode="edit"``: a single status message is edited in place with
      throttled updates and replaced with the final response on
      ``finalize``.

    A background thread keeps re-sending the ``typing`` chat action in
    both modes so the header indicator stays visible while the agent is
    working.
    """

    def __init__(
        self,
        api: TelegramAPI,
        chat_id: int,
        status_msg_id: int | None,
        update_interval: int = 3,
        mode: str = "append",
    ):
        self.api = api
        self.chat_id = chat_id
        self.status_msg_id = status_msg_id
        self.update_interval = update_interval
        self.mode = mode if mode in ("append", "edit") else "append"

        # Text track
        self._text_buffer: list[str] = []

        # Streaming scrubber for <active_memory> fences. Even though the
        # model is told not to emit them, we belt-and-suspenders here.
        self._scrubber = MemoryFenceScrubber()

        # Tool track (only used in edit mode for the rolling status panel)
        self._activity: list[str] = []
        self._turn_count: int = 0

        # Throttle state
        self._last_update: float = 0.0

        # Typing indicator thread
        self._typing_active = True
        self._typing_thread = threading.Thread(
            target=self._typing_loop, daemon=True, name="typing-indicator",
        )
        self._typing_thread.start()

    # ── Public callbacks ────────────────────────────────────────────

    def on_text(self, chunk: str) -> None:
        """Track 1: accumulate a streamed text chunk.

        Chunks are passed through the memory fence scrubber before
        buffering. In append mode the buffered chunks are emitted as part
        of the final response — we don't spam partial-text messages.
        """
        clean = self._scrubber.scrub_chunk(chunk)
        if clean:
            self._text_buffer.append(clean)
        if self.mode == "edit":
            self._maybe_push()

    def on_tool(self, tool_name: str, tool_input_summary: str) -> None:
        """Track 2: surface a tool-use event."""
        entry = _tool_label(tool_name, tool_input_summary)
        self._turn_count += 1

        if self.mode == "append":
            try:
                self.api.send_message(self.chat_id, entry)
            except Exception:
                log.exception("on_tool: append send failed for chat %s", self.chat_id)
            return

        self._activity.append(entry)
        if len(self._activity) > 8:
            self._activity = self._activity[-8:]
        # Push respecting throttle to avoid Telegram 429 rate limits
        self._maybe_push()

    def finalize(self, response: str) -> None:
        """Deliver the agent's final response to the chat.

        Append mode: send as a new message, leaving any prior activity
        messages untouched.
        Edit mode: replace the original status message with the response
        and continue any overflow as additional new messages.

        The response is scrubbed of any leaked ``<active_memory>`` fences
        before being sent.
        """
        # Stop the typing indicator
        self._typing_active = False

        # One-shot scrub on the consolidated response — non-streaming
        # callers go through here directly. Streaming callers have
        # already scrubbed each chunk, but a final scrub is cheap.
        response = scrub_text(response or "")
        if not response:
            response = "(No response)"

        try:
            if self.mode == "append":
                first = response[:4096]
                self.api.send_message(self.chat_id, first)
                remaining = response[4096:]
                while remaining:
                    chunk = remaining[:4096]
                    self.api.send_message(self.chat_id, chunk)
                    remaining = remaining[4096:]
                return

            # edit mode
            if self.status_msg_id is None:
                # No status message to edit — fall back to send.
                self.api.send_message(self.chat_id, response[:4096])
                remaining = response[4096:]
                while remaining:
                    self.api.send_message(self.chat_id, remaining[:4096])
                    remaining = remaining[4096:]
                return

            if len(response) <= 4096:
                self.api.edit_message(self.chat_id, self.status_msg_id, response)
            else:
                self.api.edit_message(
                    self.chat_id, self.status_msg_id, response[:4096]
                )
                remaining = response[4096:]
                while remaining:
                    chunk = remaining[:4096]
                    self.api.send_message(self.chat_id, chunk)
                    remaining = remaining[4096:]
        except Exception:
            log.exception("finalize: failed to deliver response to chat %s", self.chat_id)

    # ── Internals ───────────────────────────────────────────────────

    def _typing_loop(self) -> None:
        """Background loop: re-send typing action every 5s until finalized."""
        while self._typing_active:
            try:
                self.api.send_chat_action(self.chat_id, "typing")
            except Exception:
                pass
            time.sleep(5)

    def _maybe_push(self) -> None:
        """Edit the Telegram status message if enough time has elapsed."""
        now = time.time()
        if now - self._last_update < self.update_interval:
            return
        self._push()
        self._last_update = now

    def _push(self) -> None:
        """Build the status text and edit the Telegram message (edit mode only)."""
        if self.mode != "edit" or self.status_msg_id is None:
            return

        parts: list[str] = []

        # Header
        if self._turn_count == 0:
            parts.append("\u2699\ufe0f Starting...")
        else:
            parts.append(f"\u2699\ufe0f Working (step {self._turn_count})...")

        # Tool activity log
        if self._activity:
            parts.append("")
            for line in self._activity:
                parts.append(line)

        # Accumulated text preview (last 200 chars)
        if self._text_buffer:
            preview = "".join(self._text_buffer)[-200:]
            parts.append("")
            parts.append(preview)

        text = "\n".join(parts)
        if len(text) > 4000:
            text = text[:4000]

        try:
            self.api.edit_message(self.chat_id, self.status_msg_id, text)
        except Exception:
            log.exception("_push: edit failed for chat %s", self.chat_id)
