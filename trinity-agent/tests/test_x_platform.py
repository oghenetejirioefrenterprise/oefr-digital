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


def test_grok_search_uses_x_search():
    """search() calls the xAI Responses API with the x_search tool."""
    with patch("trinity.x_platform.grok._call") as mock_call:
        mock_call.return_value = "Found 5 posts about AI agents..."
        from trinity.x_platform.grok import search
        result = search("AI agents")
        mock_call.assert_called_once()
        prompt, kwargs = mock_call.call_args[0][0], mock_call.call_args
        assert "AI agents" in prompt
        assert kwargs.kwargs.get("x_search") is True
        assert "Found 5 posts" in result


def test_grok_search_http_error_returns_error_string():
    """search() returns an Error: string (not a crash) on an API HTTP error."""
    import urllib.error
    with patch("trinity.x_platform.grok._oauth_token", return_value="tok"), \
         patch("trinity.x_platform.grok.urllib.request.urlopen",
               side_effect=urllib.error.HTTPError("u", 429, "Too Many", {}, None)):
        from trinity.x_platform.grok import search
        result = search("anything")
        assert result.startswith("Error: xAI API returned HTTP 429")


def test_grok_no_token_returns_error():
    """With no OAuth token, calls degrade to an Error: string."""
    with patch("trinity.x_platform.grok._oauth_token", return_value=None):
        from trinity.x_platform.grok import search
        assert "OAuth token" in search("anything")


def test_grok_draft_no_x_search():
    """draft() is plain generation — must NOT request the x_search tool."""
    with patch("trinity.x_platform.grok._call") as mock_call:
        mock_call.return_value = "New FMCSA carrier data is live..."
        from trinity.x_platform.grok import draft
        result = draft("FMCSA carrier leads", context="B2B data product")
        assert mock_call.call_args.kwargs.get("x_search") is False
        assert len(result) > 0


def test_grok_analyze_uses_x_search():
    """analyze() runs over X data via x_search."""
    with patch("trinity.x_platform.grok._call") as mock_call:
        mock_call.return_value = "Sentiment: mostly positive."
        from trinity.x_platform.grok import analyze
        result = analyze("OEFR Digital")
        assert mock_call.call_args.kwargs.get("x_search") is True
        assert len(result) > 0


def test_grok_extract_text_parses_responses_payload():
    """_extract_text pulls output_text out of a /v1/responses payload."""
    from trinity.x_platform.grok import _extract_text
    payload = {"output": [{"type": "message", "content": [
        {"type": "output_text", "text": "hello from X"},
    ]}]}
    assert _extract_text(payload) == "hello from X"


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

    with patch("trinity.x_platform.grok._call", return_value="results"):
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


# ── grok OAuth proactive refresh ─────────────────────────────────────

def _auth_entry(expires_at):
    import json
    return json.dumps({"https://auth.x.ai::id": {
        "key": "OLD", "refresh_token": "R0", "oidc_client_id": "C",
        "oidc_issuer": "https://auth.x.ai", "expires_at": expires_at, "auth_mode": "oidc",
    }})


def _iso(delta_min):
    import datetime as dt
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=delta_min)).strftime(
        "%Y-%m-%dT%H:%M:%S.000000000Z")


def test_oauth_refreshes_when_near_expiry(tmp_path, monkeypatch):
    import json
    from trinity.x_platform import grok
    auth = tmp_path / "auth.json"
    auth.write_text(_auth_entry(_iso(-5)))  # expired 5 min ago
    auth.chmod(0o600)
    monkeypatch.setattr(grok, "_AUTH_PATH", auth)
    monkeypatch.setattr(grok, "_refresh",
                        lambda e: {"access_token": "NEW", "refresh_token": "R1", "expires_in": 3600})
    assert grok._oauth_token() == "NEW"
    saved = json.loads(auth.read_text())["https://auth.x.ai::id"]
    assert saved["key"] == "NEW"
    assert saved["refresh_token"] == "R1"            # rotated token persisted
    assert oct(auth.stat().st_mode)[-3:] == "600"    # perms preserved


def test_oauth_no_refresh_when_valid(tmp_path, monkeypatch):
    from trinity.x_platform import grok
    auth = tmp_path / "auth.json"
    auth.write_text(_auth_entry(_iso(120)))  # 2h left
    monkeypatch.setattr(grok, "_AUTH_PATH", auth)
    def _boom(e):
        raise AssertionError("must not refresh a valid token")
    monkeypatch.setattr(grok, "_refresh", _boom)
    assert grok._oauth_token() == "OLD"


def test_oauth_refresh_failure_falls_back_to_stale(tmp_path, monkeypatch):
    from trinity.x_platform import grok
    auth = tmp_path / "auth.json"
    auth.write_text(_auth_entry(_iso(-5)))
    monkeypatch.setattr(grok, "_AUTH_PATH", auth)
    monkeypatch.setattr(grok, "_refresh", lambda e: None)
    assert grok._oauth_token() == "OLD"  # graceful: stale token, no crash
