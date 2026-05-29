#!/usr/bin/env python3
"""Quick test of Nvidia NIM LLM wrapper for browser-use."""
import asyncio
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.nvidia_nim_llm import create_nvidia_nim_llm
from browser_use.llm.messages import UserMessage, SystemMessage


async def test_nvidia_nim():
    """Test basic LLM call to Nvidia NIM."""
    print("🧪 Testing Nvidia NIM LLM wrapper...")

    try:
        llm = create_nvidia_nim_llm(
            model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
            max_completion_tokens=512,
            temperature=0.2,
        )
        print(f"✓ LLM initialized: {llm.model}")

        messages = [
            SystemMessage(content="You are a helpful browser automation assistant. Be concise."),
            UserMessage(content="List 3 key steps to post on Reddit: login, navigate to subreddit, compose post. Just list them briefly."),
        ]

        print("\n🔄 Calling Nvidia NIM API...")
        response = await llm.ainvoke(messages)

        print("\n✅ Response received:")
        print(f"Completion: {response.completion}")
        print(f"Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}\n")

        print("🎉 Test passed! Nvidia NIM LLM is working.")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_nvidia_nim())
    sys.exit(0 if success else 1)
