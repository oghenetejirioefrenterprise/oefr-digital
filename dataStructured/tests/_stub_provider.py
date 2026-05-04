"""Stub LLM provider for contract tests — no real API calls."""
from collections import deque
from typing import Any


class StubProvider:
    """Drop-in for trinity Provider — returns canned responses, records calls."""

    def __init__(self) -> None:
        self._responses: deque[str] = deque()
        self.calls: list[dict[str, Any]] = []

    def respond_with(self, text: str) -> None:
        """Queue a canned response for the next chat() call."""
        self._responses.append(text)

    def chat(self, messages, **kwargs) -> dict[str, Any]:
        """Return the next queued response."""
        if not self._responses:
            raise RuntimeError("StubProvider: no canned response queued")
        text = self._responses.popleft()
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return {"text": text, "stop_reason": "end_turn", "usage": {"input_tokens": 0, "output_tokens": 0}}

    def stream(self, messages, **kwargs):
        result = self.chat(messages, **kwargs)
        yield {"type": "text", "text": result["text"]}
        yield {"type": "end", "result": result}
