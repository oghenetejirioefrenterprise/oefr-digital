"""Output-side scrubber that strips ``<active_memory>`` fences from agent text.

The pre-reply recall pipeline injects recalled memories into the system prompt
fenced in ``<active_memory>...</active_memory>``. The fenced content is meant
for the model only — if the model ever echoes the wrapper, the user sees raw
prompt scaffolding (and, more importantly, an attacker who poisoned a memory
entry could exfiltrate it).

This module provides a streaming-aware scrubber: text inside a fence is
discarded, the wrapping tags themselves are dropped, and partial tags
spanning chunk boundaries are held back until enough chunks arrive to
disambiguate. If the stream ends with an unclosed fence, the in-span tail
is discarded — leaking partial fence content is worse than truncating the
reply.
"""
from __future__ import annotations

import re

# Match an opening tag with or without attributes:
#   <active_memory>            <active_memory source="store">
_OPEN_TAG_RE = re.compile(r"<\s*active_memory\b[^>]*>", re.IGNORECASE)
_CLOSE_TAG_RE = re.compile(r"</\s*active_memory\s*>", re.IGNORECASE)


class MemoryFenceScrubber:
    """Stream-safe scrubber for ``<active_memory>`` fences.

    Usage:
        s = MemoryFenceScrubber()
        for chunk in stream:
            telegram_send(s.scrub_chunk(chunk))
        telegram_send(s.flush())
    """

    def __init__(self) -> None:
        self._buffer: str = ""
        self._in_fence: bool = False

    def scrub_chunk(self, chunk: str) -> str:
        """Return the safe-to-emit prefix of ``chunk`` plus any held-back text."""
        if not chunk:
            return ""
        self._buffer += chunk
        out: list[str] = []

        while True:
            if self._in_fence:
                m = _CLOSE_TAG_RE.search(self._buffer)
                if m is None:
                    # Still inside. Discard in-fence content but keep any
                    # trailing partial close-tag candidate so a tag
                    # straddling chunk boundaries isn't dropped on the floor.
                    last_lt = self._buffer.rfind("<")
                    if last_lt >= 0 and ">" not in self._buffer[last_lt:]:
                        self._buffer = self._buffer[last_lt:]
                    else:
                        self._buffer = ""
                    return "".join(out)
                # Close found — discard up to and including the close tag.
                self._buffer = self._buffer[m.end():]
                self._in_fence = False
                continue

            m = _OPEN_TAG_RE.search(self._buffer)
            if m is not None:
                out.append(self._buffer[: m.start()])
                self._buffer = self._buffer[m.end():]
                self._in_fence = True
                continue

            # No complete open tag. Keep any trailing partial-tag candidate
            # buffered so a tag straddling chunk boundaries can still be
            # recognised on the next call.
            last_lt = self._buffer.rfind("<")
            if last_lt >= 0 and ">" not in self._buffer[last_lt:]:
                out.append(self._buffer[:last_lt])
                self._buffer = self._buffer[last_lt:]
            else:
                out.append(self._buffer)
                self._buffer = ""
            return "".join(out)

    def flush(self) -> str:
        """Emit any remaining safe content. Drops in-fence content."""
        if self._in_fence:
            # Unclosed fence — drop the rest entirely.
            self._buffer = ""
            self._in_fence = False
            return ""
        out = self._buffer
        self._buffer = ""
        return out


def scrub(text: str) -> str:
    """One-shot scrub for non-streaming callers."""
    s = MemoryFenceScrubber()
    return s.scrub_chunk(text) + s.flush()
