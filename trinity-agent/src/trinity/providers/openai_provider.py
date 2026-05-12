"""OpenAI provider — talks to OpenAI via the official Python SDK."""
from __future__ import annotations

from .openrouter_provider import OpenRouterProvider


class OpenAIProvider(OpenRouterProvider):
    """Provider backed by the OpenAI API.

    Reuses the OpenRouter provider since both use the OpenAI SDK.
    The only difference is the base_url (official OpenAI endpoint).
    """

    def __init__(self, api_key: str) -> None:
        super().__init__(api_key=api_key, base_url="https://api.openai.com/v1")
