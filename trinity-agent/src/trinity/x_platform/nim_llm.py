"""NVIDIA NIM LLM wrapper for browser-use agent."""
from __future__ import annotations

import os
import subprocess

from browser_use.llm.openai.like import ChatOpenAILike


def create_nim_llm(
    model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    max_completion_tokens: int = 2048,
    temperature: float = 0.2,
) -> ChatOpenAILike:
    """Create a browser-use LLM client backed by NVIDIA NIM.

    Returns ChatOpenAILike pointing at integrate.api.nvidia.com/v1.
    Auto-sources ~/.profile if NVIDIA_API_KEY is not in env.
    """
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
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

    return ChatOpenAILike(
        model=model,
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        max_completion_tokens=max_completion_tokens,
        temperature=temperature,
    )
