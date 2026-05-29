#!/usr/bin/env python3
"""Nvidia NIM LLM wrapper for browser-use agent."""
import os
import subprocess
from browser_use.llm.openai.like import ChatOpenAILike


def create_nvidia_nim_llm(
    model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    max_completion_tokens: int = 2048,
    temperature: float = 0.2,
) -> ChatOpenAILike:
    """
    Create a browser-use LLM client for Nvidia NIM.

    Uses OpenAI-compatible API via browser-use's ChatOpenAILike wrapper.
    Optimized for nemotron-3-nano-omni-30b-a3b-reasoning (multimodal + reasoning).

    Args:
        model: Nvidia NIM model name
        max_completion_tokens: Max completion tokens
        temperature: Sampling temperature (lower = more deterministic)

    Returns:
        ChatOpenAILike: Browser-use compatible LLM client

    Raises:
        RuntimeError: If NVIDIA_API_KEY is not set
    """
    # Get API key from env
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        # Try auto-sourcing ~/.profile
        result = subprocess.run(
            ["bash", "-c", "source ~/.profile && env"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.split("\n"):
            if "=" in line:
                k, _, v = line.partition("=")
                if k == "NVIDIA_API_KEY":
                    os.environ.setdefault(k, v)
                    api_key = v
                    break

    if not api_key:
        raise RuntimeError(
            "NVIDIA_API_KEY not set — source ~/.profile or set env var"
        )

    # Return browser-use compatible LLM
    return ChatOpenAILike(
        model=model,
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
    )
