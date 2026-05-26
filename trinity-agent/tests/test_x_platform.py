"""X platform subsystem tests — NIM client, Grok CLI, browser, tools."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import subprocess as real_subprocess

import pytest


def test_nim_llm_factory_creates_client():
    """create_nim_llm returns a ChatOpenAILike with correct config."""
    with patch.dict(os.environ, {"NVIDIA_API_KEY": "nvapi-test-key"}):
        with patch("trinity.x_platform.nim_llm.ChatOpenAILike") as mock_cls:
            mock_cls.return_value = MagicMock()
            from trinity.x_platform.nim_llm import create_nim_llm
            client = create_nim_llm()
            mock_cls.assert_called_once_with(
                model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
                api_key="nvapi-test-key",
                base_url="https://integrate.api.nvidia.com/v1",
                max_completion_tokens=2048,
                temperature=0.2,
            )
            assert client is mock_cls.return_value


def test_nim_llm_factory_missing_key_raises():
    """create_nim_llm raises RuntimeError when NVIDIA_API_KEY is missing."""
    import importlib
    import trinity.x_platform.nim_llm as mod
    importlib.reload(mod)
    env = {k: v for k, v in os.environ.items() if k != "NVIDIA_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        with patch("trinity.x_platform.nim_llm.subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(stdout="")
            with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
                mod.create_nim_llm()


def test_grok_search_calls_subprocess():
    """search() shells out to grok -p with search prompt."""
    with patch("trinity.x_platform.grok.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(
            stdout="Found 5 posts about AI agents...",
            stderr="",
            returncode=0,
        )
        mock_sub.TimeoutExpired = real_subprocess.TimeoutExpired
        from trinity.x_platform.grok import search
        result = search("AI agents")
        mock_sub.run.assert_called_once()
        assert "AI agents" in str(mock_sub.run.call_args)
        assert "Found 5 posts" in result


def test_grok_search_timeout_returns_error():
    """search() returns error string on timeout instead of crashing."""
    with patch("trinity.x_platform.grok.subprocess") as mock_sub:
        mock_sub.run.side_effect = real_subprocess.TimeoutExpired(cmd="grok", timeout=60)
        mock_sub.TimeoutExpired = real_subprocess.TimeoutExpired
        from trinity.x_platform.grok import search
        result = search("anything")
        assert "timed out" in result.lower()


def test_grok_draft_calls_subprocess():
    """draft() generates tweet content via grok -p."""
    with patch("trinity.x_platform.grok.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(
            stdout="Here's a tweet draft:\n\nNew FMCSA carrier data is live...",
            stderr="",
            returncode=0,
        )
        mock_sub.TimeoutExpired = real_subprocess.TimeoutExpired
        from trinity.x_platform.grok import draft
        result = draft("FMCSA carrier leads", context="B2B data product")
        assert len(result) > 0


def test_grok_analyze_calls_subprocess():
    """analyze() runs sentiment/engagement analysis via grok -p."""
    with patch("trinity.x_platform.grok.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(
            stdout="Sentiment: mostly positive. Engagement: moderate.",
            stderr="",
            returncode=0,
        )
        mock_sub.TimeoutExpired = real_subprocess.TimeoutExpired
        from trinity.x_platform.grok import analyze
        result = analyze("OEFR Digital")
        assert len(result) > 0


def test_post_tweet_creates_agent(tmp_path):
    """post_tweet creates a browser-use Agent with correct task prompt."""
    trinity_dir = tmp_path / ".trinity"
    trinity_dir.mkdir()

    with patch.dict(os.environ, {"X_USERNAME": "testuser", "X_PASS": "testpass", "NVIDIA_API_KEY": "nvapi-test"}):
        with patch("trinity.x_platform.browser.Agent") as mock_agent_cls:
            with patch("trinity.x_platform.browser.create_nim_llm") as mock_llm:
                with patch("trinity.x_platform.browser.BrowserProfile"):
                    mock_agent = MagicMock()
                    mock_history = MagicMock()
                    mock_history.final_result.return_value = "https://x.com/testuser/status/123456"

                    async def fake_run(**kwargs):
                        return mock_history
                    mock_agent.run = fake_run
                    mock_agent_cls.return_value = mock_agent

                    from trinity.x_platform.browser import post_tweet
                    url = asyncio.run(post_tweet(trinity_dir, "Hello world"))

                    mock_agent_cls.assert_called_once()
                    call_kwargs = mock_agent_cls.call_args
                    task_text = call_kwargs.kwargs.get("task", "")
                    assert "Hello world" in task_text
                    assert url == "https://x.com/testuser/status/123456"


def test_post_tweet_with_reply_link(tmp_path):
    """post_tweet includes reply step when reply_link is provided."""
    trinity_dir = tmp_path / ".trinity"
    trinity_dir.mkdir()

    with patch.dict(os.environ, {"X_USERNAME": "testuser", "X_PASS": "testpass", "NVIDIA_API_KEY": "nvapi-test"}):
        with patch("trinity.x_platform.browser.Agent") as mock_agent_cls:
            with patch("trinity.x_platform.browser.create_nim_llm"):
                with patch("trinity.x_platform.browser.BrowserProfile"):
                    mock_agent = MagicMock()
                    mock_history = MagicMock()
                    mock_history.final_result.return_value = "https://x.com/testuser/status/789"

                    async def fake_run(**kwargs):
                        return mock_history
                    mock_agent.run = fake_run
                    mock_agent_cls.return_value = mock_agent

                    from trinity.x_platform.browser import post_tweet
                    asyncio.run(post_tweet(trinity_dir, "Hook tweet", reply_link="https://buy.stripe.com/xxx"))

                    task_text = mock_agent_cls.call_args.kwargs.get("task", "")
                    assert "Reply" in task_text or "reply" in task_text
                    assert "https://buy.stripe.com/xxx" in task_text


def test_post_tweet_no_permalink_raises(tmp_path):
    """post_tweet raises RuntimeError when no tweet URL is found."""
    trinity_dir = tmp_path / ".trinity"
    trinity_dir.mkdir()

    with patch.dict(os.environ, {"X_USERNAME": "testuser", "X_PASS": "testpass", "NVIDIA_API_KEY": "nvapi-test"}):
        with patch("trinity.x_platform.browser.Agent") as mock_agent_cls:
            with patch("trinity.x_platform.browser.create_nim_llm"):
                with patch("trinity.x_platform.browser.BrowserProfile"):
                    mock_agent = MagicMock()
                    mock_history = MagicMock()
                    mock_history.final_result.return_value = "Something went wrong"

                    async def fake_run(**kwargs):
                        return mock_history
                    mock_agent.run = fake_run
                    mock_agent_cls.return_value = mock_agent

                    from trinity.x_platform.browser import post_tweet
                    with pytest.raises(RuntimeError, match="no tweet permalink"):
                        asyncio.run(post_tweet(trinity_dir, "Test tweet"))


def test_all_specs_has_six_tools():
    """ALL_SPECS contains exactly 6 tool spec tuples."""
    from trinity.x_platform.tools import ALL_SPECS
    assert len(ALL_SPECS) == 6
    names = [schema["name"] for schema, _ in ALL_SPECS]
    assert "x_search" in names
    assert "x_draft" in names
    assert "x_analyze" in names
    assert "x_post" in names
    assert "x_reply" in names
    assert "x_thread" in names


def test_tool_handlers_return_strings(tmp_path):
    """Read tool handlers return strings when mocked."""
    trinity_dir = tmp_path / ".trinity"
    trinity_dir.mkdir()

    from trinity.x_platform import tools as x_tools
    x_tools.set_trinity_dir(trinity_dir)

    with patch("trinity.x_platform.grok.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(stdout="results", stderr="", returncode=0)
        mock_sub.TimeoutExpired = real_subprocess.TimeoutExpired
        result = x_tools.x_search_handler({"query": "test"}, tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0


def test_tweet_truncation(tmp_path):
    """Tweets longer than 280 chars are truncated to 277 + '...'."""
    long_text = "A" * 300
    trinity_dir = tmp_path / ".trinity"
    trinity_dir.mkdir()

    with patch.dict(os.environ, {"X_USERNAME": "u", "X_PASS": "p", "NVIDIA_API_KEY": "k"}):
        with patch("trinity.x_platform.browser.Agent") as mock_agent_cls:
            with patch("trinity.x_platform.browser.create_nim_llm"):
                with patch("trinity.x_platform.browser.BrowserProfile"):
                    mock_agent = MagicMock()
                    mock_history = MagicMock()
                    mock_history.final_result.return_value = "https://x.com/u/status/999"

                    async def fake_run(**kwargs):
                        return mock_history
                    mock_agent.run = fake_run
                    mock_agent_cls.return_value = mock_agent

                    from trinity.x_platform.browser import post_tweet
                    asyncio.run(post_tweet(trinity_dir, long_text))

                    task_text = mock_agent_cls.call_args.kwargs.get("task", "")
                    assert "A" * 300 not in task_text
                    assert "..." in task_text
