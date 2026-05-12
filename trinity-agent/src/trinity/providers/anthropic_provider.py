"""Anthropic provider — talks to Claude via the official Python SDK."""
from __future__ import annotations

import json
from typing import Any, Generator

from anthropic import Anthropic

from .base import (
    Message,
    Provider,
    Response,
    ToolCall,
    ToolDef,
    ToolResult,
    Usage,
)


class AnthropicProvider(Provider):
    """Provider backed by the Anthropic Messages API."""

    def __init__(self, api_key: str) -> None:
        self._client = Anthropic(api_key=api_key)

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _convert_tools(tools: list[ToolDef] | None) -> list[dict[str, Any]]:
        """Convert ToolDef list to Anthropic tool format."""
        if not tools:
            return []
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]

    @staticmethod
    def _convert_messages(messages: list[Message]) -> list[dict[str, Any]]:
        """Convert Message list to Anthropic message format.

        Handles plain strings, mixed content blocks, and ToolResult objects
        that must become ``tool_result`` content blocks inside a ``user``
        message.
        """
        result: list[dict[str, Any]] = []

        for msg in messages:
            # ── ToolResult list → user message with tool_result blocks ──
            if isinstance(msg.content, list) and msg.content and isinstance(msg.content[0], ToolResult):
                blocks = []
                for tr in msg.content:
                    block: dict[str, Any] = {
                        "type": "tool_result",
                        "tool_use_id": tr.tool_use_id,
                        "content": tr.content,
                    }
                    if tr.is_error:
                        block["is_error"] = True
                    blocks.append(block)
                result.append({"role": "user", "content": blocks})
                continue

            # ── plain string content ────────────────────────────────────
            if isinstance(msg.content, str):
                result.append({"role": msg.role, "content": msg.content})
                continue

            # ── list content (may contain ToolResult mixed with dicts) ──
            if isinstance(msg.content, list):
                blocks = []
                for item in msg.content:
                    if isinstance(item, ToolResult):
                        block = {
                            "type": "tool_result",
                            "tool_use_id": item.tool_use_id,
                            "content": item.content,
                        }
                        if item.is_error:
                            block["is_error"] = True
                        blocks.append(block)
                    elif isinstance(item, ToolCall):
                        blocks.append({
                            "type": "tool_use",
                            "id": item.id,
                            "name": item.name,
                            "input": item.input,
                        })
                    elif isinstance(item, dict):
                        blocks.append(item)
                    else:
                        # Fallback: treat as text
                        blocks.append({"type": "text", "text": str(item)})
                result.append({"role": msg.role, "content": blocks})
                continue

            # ── fallback ────────────────────────────────────────────────
            result.append({"role": msg.role, "content": str(msg.content)})

        return result

    @staticmethod
    def _parse_response(raw: Any) -> Response:
        """Extract a normalized Response from the Anthropic SDK response."""
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in raw.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        input=block.input,
                    )
                )

        # Map Anthropic stop reasons to our canonical names
        stop_reason_map = {
            "end_turn": "end_turn",
            "tool_use": "tool_use",
            "max_tokens": "max_tokens",
            "stop_sequence": "end_turn",
        }
        stop_reason = stop_reason_map.get(raw.stop_reason, raw.stop_reason or "")

        usage = Usage(
            input_tokens=raw.usage.input_tokens,
            output_tokens=raw.usage.output_tokens,
        )

        return Response(
            text="\n".join(text_parts) if text_parts else "",
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=usage,
            raw=raw,
        )

    # ── public API ───────────────────────────────────────────────────

    def chat(
        self,
        model: str,
        system: str,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 16384,
    ) -> Response:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": self._convert_messages(messages),
        }
        if system:
            kwargs["system"] = system

        converted_tools = self._convert_tools(tools)
        if converted_tools:
            kwargs["tools"] = converted_tools

        raw = self._client.messages.create(**kwargs)
        return self._parse_response(raw)

    def stream(
        self,
        model: str,
        system: str,
        messages: list[Message],
        tools: list[ToolDef] | None = None,
        max_tokens: int = 16384,
    ) -> Generator[str | ToolCall | Response, None, None]:
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": self._convert_messages(messages),
        }
        if system:
            kwargs["system"] = system

        converted_tools = self._convert_tools(tools)
        if converted_tools:
            kwargs["tools"] = converted_tools

        with self._client.messages.stream(**kwargs) as stream:
            # Yield text chunks as they arrive
            for text_chunk in stream.text_stream:
                yield text_chunk

            # After stream is done, get the final accumulated message
            final = stream.get_final_message()

        # Parse the final message into a Response
        response = self._parse_response(final)

        # Yield any tool calls from the final message
        for tc in response.tool_calls:
            yield tc

        # Final yield is always the complete Response
        yield response
