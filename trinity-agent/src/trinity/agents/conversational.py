"""Track 1 — Conversational agent (no tools, fast, streaming)."""
from __future__ import annotations

import logging
from typing import Callable

from trinity.config import TrinityConfig
from trinity.providers.base import Message, Provider

log = logging.getLogger(__name__)


def run(
    provider: Provider,
    config: TrinityConfig,
    system: str,
    chat_history: list[Message],
    new_message: str,
    model: str | None = None,
    on_text: Callable[[str], None] | None = None,
) -> str:
    """Run a conversational response — single API call, no tools.

    Args:
        provider: LLM provider
        config: Trinity config
        system: System prompt (compact identity + group context + memories)
        chat_history: Previous messages in this chat
        new_message: The new user message
        model: Model override (defaults to config.agent.default_model)
        on_text: Streaming callback for text chunks
    """
    model = model or config.agent.default_model
    messages = chat_history + [Message(role="user", content=new_message)]

    if on_text:
        final = ""
        for item in provider.stream(
            model=model,
            system=system,
            messages=messages,
            max_tokens=4096,
        ):
            if isinstance(item, str):
                on_text(item)
                final += item
            else:
                # Response object
                if hasattr(item, "text") and item.text:
                    final = item.text
        return final or "(no response)"

    response = provider.chat(
        model=model,
        system=system,
        messages=messages,
        max_tokens=4096,
    )
    return response.text or "(no response)"
