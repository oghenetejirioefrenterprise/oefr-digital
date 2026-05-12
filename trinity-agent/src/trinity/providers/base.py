"""Provider ABC — unified interface for LLM backends."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generator


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: Any  # str or list of content blocks


@dataclass
class ToolDef:
    """Tool definition passed to the LLM."""
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool, sent back to the LLM."""
    tool_use_id: str
    content: str
    is_error: bool = False


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class Response:
    """Normalized response from any provider."""
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = ""  # "end_turn" | "tool_use" | "max_tokens"
    usage: Usage = field(default_factory=Usage)
    raw: Any = None  # Provider-specific raw response


class Provider(ABC):
    """Abstract LLM provider — all agents talk through this interface."""

    @abstractmethod
    def chat(
        self,
        model: str,
        system: str,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 16384,
    ) -> Response:
        """Send a chat completion request and return the full response."""
        ...

    @abstractmethod
    def stream(
        self,
        model: str,
        system: str,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 16384,
    ) -> Generator[str | ToolCall | Response, None, None]:
        """Stream a chat completion.

        Yields:
          - str: text chunks as they arrive
          - ToolCall: when the model requests a tool call
          - Response: final complete response (last item yielded)
        """
        ...
