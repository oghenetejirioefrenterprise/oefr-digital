"""OpenRouter provider — talks to OpenRouter (OpenAI-compatible) via the openai SDK."""
from __future__ import annotations

import json
from typing import Any, Generator

from openai import OpenAI

from .base import (
    Message,
    Provider,
    Response,
    ToolCall,
    ToolDef,
    ToolResult,
    Usage,
)


class OpenRouterProvider(Provider):
    """Provider backed by the OpenAI-compatible OpenRouter API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    # ── helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _convert_tools(tools: list[ToolDef] | None) -> list[dict[str, Any]] | None:
        """Convert ToolDef list to OpenAI function-calling format."""
        if not tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]

    @staticmethod
    def _convert_messages(
        system: str,
        messages: list[Message],
    ) -> list[dict[str, Any]]:
        """Convert system prompt + Message list to OpenAI chat format.

        The system prompt becomes the first message with role="system".
        ToolResult objects become tool-role messages.
        Assistant messages with ToolCall content blocks become assistant
        messages with tool_calls.
        """
        result: list[dict[str, Any]] = []

        if system:
            result.append({"role": "system", "content": system})

        for msg in messages:
            # ── ToolResult list → individual tool messages ──────────
            if isinstance(msg.content, list) and msg.content and isinstance(msg.content[0], ToolResult):
                for tr in msg.content:
                    result.append({
                        "role": "tool",
                        "tool_call_id": tr.tool_use_id,
                        "content": tr.content,
                    })
                continue

            # ── assistant message with mixed content (text + tool_use) ──
            if msg.role == "assistant" and isinstance(msg.content, list):
                text_parts: list[str] = []
                oai_tool_calls: list[dict[str, Any]] = []
                for item in msg.content:
                    if isinstance(item, ToolCall):
                        oai_tool_calls.append({
                            "id": item.id,
                            "type": "function",
                            "function": {
                                "name": item.name,
                                "arguments": json.dumps(item.input),
                            },
                        })
                    elif isinstance(item, dict):
                        if item.get("type") == "tool_use":
                            oai_tool_calls.append({
                                "id": item["id"],
                                "type": "function",
                                "function": {
                                    "name": item["name"],
                                    "arguments": json.dumps(item.get("input", {})),
                                },
                            })
                        elif item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        else:
                            text_parts.append(str(item))
                    elif isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, ToolResult):
                        # ToolResult in an assistant message is unusual but
                        # handle gracefully — will be appended as a tool msg
                        result.append({
                            "role": "tool",
                            "tool_call_id": item.tool_use_id,
                            "content": item.content,
                        })
                        continue
                    else:
                        text_parts.append(str(item))

                assistant_msg: dict[str, Any] = {"role": "assistant"}
                content_text = "\n".join(text_parts) if text_parts else None
                if content_text:
                    assistant_msg["content"] = content_text
                else:
                    assistant_msg["content"] = None
                if oai_tool_calls:
                    assistant_msg["tool_calls"] = oai_tool_calls
                result.append(assistant_msg)
                continue

            # ── user message with list of ToolResult (mixed) ────────
            if isinstance(msg.content, list):
                parts: list[str] = []
                for item in msg.content:
                    if isinstance(item, ToolResult):
                        result.append({
                            "role": "tool",
                            "tool_call_id": item.tool_use_id,
                            "content": item.content,
                        })
                    elif isinstance(item, dict) and item.get("type") == "text":
                        parts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        parts.append(item)
                    else:
                        parts.append(str(item))
                if parts:
                    result.append({"role": msg.role, "content": "\n".join(parts)})
                continue

            # ── plain string content ────────────────────────────────
            result.append({"role": msg.role, "content": str(msg.content)})

        return result

    @staticmethod
    def _parse_response(raw: Any) -> Response:
        """Extract a normalized Response from the OpenAI SDK response."""
        choice = raw.choices[0] if raw.choices else None
        if choice is None:
            return Response(text="", stop_reason="end_turn", raw=raw)

        text = choice.message.content or ""

        tool_calls: list[ToolCall] = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        input=args,
                    )
                )

        # Map OpenAI finish reasons to our canonical names
        finish_map = {
            "stop": "end_turn",
            "tool_calls": "tool_use",
            "length": "max_tokens",
            "content_filter": "end_turn",
        }
        stop_reason = finish_map.get(choice.finish_reason or "", choice.finish_reason or "end_turn")

        usage = Usage()
        if raw.usage:
            usage = Usage(
                input_tokens=raw.usage.prompt_tokens or 0,
                output_tokens=raw.usage.completion_tokens or 0,
            )

        return Response(
            text=text,
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
            "messages": self._convert_messages(system, messages),
        }

        converted_tools = self._convert_tools(tools)
        if converted_tools:
            kwargs["tools"] = converted_tools
            kwargs["tool_choice"] = "auto"

        raw = self._client.chat.completions.create(**kwargs)
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
            "messages": self._convert_messages(system, messages),
            "stream": True,
        }

        converted_tools = self._convert_tools(tools)
        if converted_tools:
            kwargs["tools"] = converted_tools
            kwargs["tool_choice"] = "auto"

        # Accumulators for the full response
        text_parts: list[str] = []
        # tool_call chunks indexed by position
        tool_call_chunks: dict[int, dict[str, Any]] = {}
        finish_reason: str | None = None
        usage_prompt: int = 0
        usage_completion: int = 0

        stream_response = self._client.chat.completions.create(**kwargs)

        for chunk in stream_response:
            # Track usage if provided in the final chunk
            if chunk.usage:
                usage_prompt = chunk.usage.prompt_tokens or 0
                usage_completion = chunk.usage.completion_tokens or 0

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            if chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

            # ── text delta ──────────────────────────────────────────
            if delta and delta.content:
                text_parts.append(delta.content)
                yield delta.content

            # ── tool call deltas ────────────────────────────────────
            if delta and delta.tool_calls:
                for tc_delta in delta.tool_calls:
                    idx = tc_delta.index
                    if idx not in tool_call_chunks:
                        tool_call_chunks[idx] = {
                            "id": "",
                            "name": "",
                            "arguments": "",
                        }
                    entry = tool_call_chunks[idx]
                    if tc_delta.id:
                        entry["id"] = tc_delta.id
                    if tc_delta.function:
                        if tc_delta.function.name:
                            entry["name"] = tc_delta.function.name
                        if tc_delta.function.arguments:
                            entry["arguments"] += tc_delta.function.arguments

        # ── assemble completed tool calls ───────────────────────────
        tool_calls: list[ToolCall] = []
        for idx in sorted(tool_call_chunks):
            entry = tool_call_chunks[idx]
            try:
                args = json.loads(entry["arguments"])
            except (json.JSONDecodeError, TypeError):
                args = {}
            tc = ToolCall(id=entry["id"], name=entry["name"], input=args)
            tool_calls.append(tc)
            yield tc

        # ── map finish reason ───────────────────────────────────────
        finish_map = {
            "stop": "end_turn",
            "tool_calls": "tool_use",
            "length": "max_tokens",
            "content_filter": "end_turn",
        }
        stop_reason = finish_map.get(finish_reason or "", finish_reason or "end_turn")

        # ── final Response yield ────────────────────────────────────
        yield Response(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=stop_reason,
            usage=Usage(input_tokens=usage_prompt, output_tokens=usage_completion),
            raw=None,
        )
