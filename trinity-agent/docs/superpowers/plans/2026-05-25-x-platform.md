# X Platform Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add X (Twitter) read/write capabilities to Trinity Agent via Grok CLI (search/draft/analyze), NVIDIA NIM Nemotron Omni (vision LLM), and browser-use (posting).

**Architecture:** Three-layer system: Grok CLI headless for read ops (search, content generation, analysis), browser-use with NIM Nemotron Omni for write ops (post, reply, thread via headless Chromium), and a Trinity tool layer exposing 6 agent-callable tools. A new Social Media Specialist employee uses these tools.

**Tech Stack:** Python 3.12, browser-use 0.12.6, Playwright 1.58.0, NVIDIA NIM API (Nemotron 3 Nano Omni), Grok CLI v0.1.220, Trinity tool registry (ToolSpec pattern).

**Spec:** `docs/superpowers/specs/2026-05-25-x-platform-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/trinity/x_platform/__init__.py` | Create | Package init |
| `src/trinity/x_platform/nim_llm.py` | Create | NIM Nemotron Omni client factory for browser-use |
| `src/trinity/x_platform/grok.py` | Create | Grok CLI headless wrapper (search, draft, analyze) |
| `src/trinity/x_platform/browser.py` | Create | browser-use X automation (post, reply, thread) |
| `src/trinity/x_platform/tools.py` | Create | 6 Trinity tool specs + handlers |
| `src/trinity/tools/registry.py` | Modify | Register X tools via `_append_x_platform_specs()` |
| `src/trinity/config.py` | Modify | Add `XPlatformConfig` dataclass + DEFAULTS + parsing |
| `src/trinity/app.py` | Modify | Call `x_tools.set_trinity_dir()` in `init()` |
| `templates/employees/social_media.md` | Create | Social Media Specialist identity |
| `tests/test_x_platform.py` | Create | 10 unit tests (all mocked) |

---

### Task 1: NIM LLM Client Factory

**Files:**
- Create: `src/trinity/x_platform/__init__.py`
- Create: `src/trinity/x_platform/nim_llm.py`
- Test: `tests/test_x_platform.py`

- [ ] **Step 1: Write failing test for NIM factory**

```python
# tests/test_x_platform.py
"""X platform subsystem tests — NIM client, Grok CLI, browser, tools."""
from __future__ import annotations

import os
from unittest.mock import patch, MagicMock


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
            import pytest
            with pytest.raises(RuntimeError, match="NVIDIA_API_KEY"):
                mod.create_nim_llm()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_x_platform.py::test_nim_llm_factory_creates_client tests/test_x_platform.py::test_nim_llm_factory_missing_key_raises -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'trinity.x_platform'`

- [ ] **Step 3: Create package init and NIM factory**

```python
# src/trinity/x_platform/__init__.py
"""X platform integration — Grok CLI + NIM Omni + browser-use."""
```

```python
# src/trinity/x_platform/nim_llm.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_x_platform.py::test_nim_llm_factory_creates_client tests/test_x_platform.py::test_nim_llm_factory_missing_key_raises -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/trinity/x_platform/__init__.py src/trinity/x_platform/nim_llm.py tests/test_x_platform.py
git commit -m "feat(x-platform): NIM Nemotron Omni client factory for browser-use"
```

---

### Task 2: Grok CLI Wrapper

**Files:**
- Create: `src/trinity/x_platform/grok.py`
- Test: `tests/test_x_platform.py` (append)

- [ ] **Step 1: Write failing tests for Grok search, draft, analyze**

Append to `tests/test_x_platform.py`:

```python
from unittest.mock import patch, MagicMock
import subprocess


def test_grok_search_calls_subprocess():
    """search() shells out to grok -p with search prompt."""
    with patch("trinity.x_platform.grok.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(
            stdout="Found 5 posts about AI agents...",
            stderr="",
            returncode=0,
        )
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        from trinity.x_platform.grok import search
        result = search("AI agents")
        mock_sub.run.assert_called_once()
        args = mock_sub.run.call_args
        assert "grok" in args[0][0][0] or args[0][0] == ["grok", "-p"]  # first arg list
        assert "AI agents" in str(args)
        assert "Found 5 posts" in result


def test_grok_search_timeout_returns_error():
    """search() returns error string on timeout instead of crashing."""
    with patch("trinity.x_platform.grok.subprocess") as mock_sub:
        mock_sub.run.side_effect = subprocess.TimeoutExpired(cmd="grok", timeout=60)
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
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
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        from trinity.x_platform.grok import draft
        result = draft("FMCSA carrier leads", context="B2B data product")
        assert "FMCSA" in str(mock_sub.run.call_args) or "FMCSA" in result
        assert len(result) > 0


def test_grok_analyze_calls_subprocess():
    """analyze() runs sentiment/engagement analysis via grok -p."""
    with patch("trinity.x_platform.grok.subprocess") as mock_sub:
        mock_sub.run.return_value = MagicMock(
            stdout="Sentiment: mostly positive. Engagement: moderate.",
            stderr="",
            returncode=0,
        )
        mock_sub.TimeoutExpired = subprocess.TimeoutExpired
        from trinity.x_platform.grok import analyze
        result = analyze("OEFR Digital")
        assert "Sentiment" in result or len(result) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_x_platform.py::test_grok_search_calls_subprocess tests/test_x_platform.py::test_grok_search_timeout_returns_error tests/test_x_platform.py::test_grok_draft_calls_subprocess tests/test_x_platform.py::test_grok_analyze_calls_subprocess -v`
Expected: FAIL — `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement grok.py**

```python
# src/trinity/x_platform/grok.py
"""Grok CLI headless wrapper — search, draft, and analyze via subprocess."""
from __future__ import annotations

import logging
import shutil
import subprocess

log = logging.getLogger(__name__)

_GROK_BIN = shutil.which("grok") or "grok"
_TIMEOUT = 60


def _run(prompt: str) -> str:
    """Run grok -p <prompt> and return stdout."""
    try:
        result = subprocess.run(
            [_GROK_BIN, "-p", prompt, "--output-format", "plain"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
        if result.returncode != 0 and result.stderr:
            log.warning("grok stderr: %s", result.stderr[:500])
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.TimeoutExpired:
        return f"Error: grok CLI timed out after {_TIMEOUT}s"
    except FileNotFoundError:
        return "Error: grok CLI not found in PATH"


def search(query: str, limit: int = 10) -> str:
    """Search X for posts matching query via Grok's built-in search_x tool."""
    prompt = (
        f"Search X (Twitter) for: {query}\n\n"
        f"Return up to {limit} recent, relevant posts. "
        f"For each post include: author handle, text, date, and URL if available. "
        f"Use your search_x tool."
    )
    return _run(prompt)


def draft(topic: str, context: str = "", tone: str = "professional") -> str:
    """Generate a tweet draft via Grok CLI."""
    prompt = (
        f"Draft a tweet (max 280 characters) about: {topic}\n"
        f"Tone: {tone}. "
        f"Make it specific with real numbers or facts — no vague claims. "
        f"No hashtags unless they add real value. "
        f"Do not include any links in the tweet text."
    )
    if context:
        prompt += f"\nAdditional context: {context}"
    return _run(prompt)


def analyze(query: str) -> str:
    """Analyze X sentiment and engagement patterns via Grok CLI."""
    prompt = (
        f"Analyze X (Twitter) activity around: {query}\n\n"
        f"Cover: overall sentiment (positive/negative/neutral), "
        f"engagement level, key themes, notable accounts discussing it, "
        f"and any trending angles. Use your search_x tool to gather data first."
    )
    return _run(prompt)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_x_platform.py -k "grok" -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/trinity/x_platform/grok.py tests/test_x_platform.py
git commit -m "feat(x-platform): Grok CLI headless wrapper — search, draft, analyze"
```

---

### Task 3: Browser-Use X Automation

**Files:**
- Create: `src/trinity/x_platform/browser.py`
- Test: `tests/test_x_platform.py` (append)

- [ ] **Step 1: Write failing tests for post, reply, thread**

Append to `tests/test_x_platform.py`:

```python
import asyncio
from pathlib import Path


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
                    mock_agent.run = MagicMock(return_value=asyncio.coroutine(lambda: mock_history)())
                    mock_agent_cls.return_value = mock_agent

                    from trinity.x_platform.browser import post_tweet
                    url = asyncio.run(post_tweet(trinity_dir, "Hello world"))

                    mock_agent_cls.assert_called_once()
                    call_kwargs = mock_agent_cls.call_args
                    assert "Hello world" in call_kwargs.kwargs.get("task", call_kwargs[1].get("task", ""))
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
                    mock_agent.run = MagicMock(return_value=asyncio.coroutine(lambda: mock_history)())
                    mock_agent_cls.return_value = mock_agent

                    from trinity.x_platform.browser import post_tweet
                    asyncio.run(post_tweet(trinity_dir, "Hook tweet", reply_link="https://buy.stripe.com/xxx"))

                    task_text = mock_agent_cls.call_args.kwargs.get("task", mock_agent_cls.call_args[1].get("task", ""))
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
                    mock_agent.run = MagicMock(return_value=asyncio.coroutine(lambda: mock_history)())
                    mock_agent_cls.return_value = mock_agent

                    from trinity.x_platform.browser import post_tweet
                    import pytest
                    with pytest.raises(RuntimeError, match="no tweet permalink"):
                        asyncio.run(post_tweet(trinity_dir, "Test tweet"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_x_platform.py -k "post_tweet" -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement browser.py**

```python
# src/trinity/x_platform/browser.py
"""browser-use X automation — post, reply, thread via headless Chromium + NIM Omni."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from browser_use import Agent, BrowserProfile

from trinity.x_platform.nim_llm import create_nim_llm

log = logging.getLogger(__name__)

_MAX_FAILURES = 3
_MAX_STEPS = 40
_BROWSER_ARGS = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
_X_HANDLE = "eustaceorukpe"


def _cookies_path(trinity_dir: Path) -> Path:
    return trinity_dir / "state" / "browser_cookies" / "twitter.json"


def _browser_profile(trinity_dir: Path) -> BrowserProfile:
    cp = _cookies_path(trinity_dir)
    return BrowserProfile(
        headless=True,
        args=_BROWSER_ARGS,
        storage_state=str(cp) if cp.exists() else None,
    )


def _creds() -> tuple[str, str]:
    username = os.environ.get("X_USERNAME", "")
    password = os.environ.get("X_PASS", "")
    if not username or not password:
        raise RuntimeError("X_USERNAME / X_PASS not set — source ~/.profile first")
    return username, password


def _login_preamble(username: str) -> str:
    return (
        f"Log in to X (Twitter) at https://x.com/i/flow/login\n"
        f"  Email/username: {username}\n"
        f"  Password: <secret>x_pass</secret>\n"
        f"  Use the username/password form ONLY — do NOT click 'Sign in with Google'.\n"
        f"  IMPORTANT: After entering the email, X may show a 'Verify your identity' or\n"
        f"  'Enter your phone or username' step. If it does, enter the handle: {_X_HANDLE}\n"
        f"  Then enter the password and click Log in.\n"
        f"  Wait for https://x.com/home to load fully.\n\n"
    )


async def _save_cookies(agent: Agent, trinity_dir: Path) -> None:
    try:
        session = getattr(agent, "browser_session", None)
        if session and hasattr(session, "context"):
            cp = _cookies_path(trinity_dir)
            cp.parent.mkdir(parents=True, exist_ok=True)
            await session.context.storage_state(path=str(cp))
    except Exception:
        log.debug("cookie save failed", exc_info=True)


def _extract_permalink(result: str) -> str:
    match = re.search(r"https://x\.com/\S+/status/\d+", result)
    if match:
        return match.group(0)
    raise RuntimeError(
        f"browser-use agent returned no tweet permalink — post likely failed. "
        f"Agent result: {result[:200] or '(empty)'}"
    )


async def post_tweet(
    trinity_dir: Path,
    text: str,
    reply_link: str = "",
    username: str = "",
    password: str = "",
) -> str:
    """Post a tweet, optionally reply with a link. Returns tweet permalink URL."""
    if not username or not password:
        username, password = _creds()

    if len(text) > 280:
        text = text[:277] + "..."

    task = _login_preamble(username)
    task += (
        f"Step 1 — Post the tweet:\n"
        f"  Click the compose box ('What is happening?!').\n"
        f"  Type exactly (do not truncate):\n{text}\n"
        f"  Click the Post button. Wait for the tweet to appear.\n\n"
    )
    if reply_link:
        task += (
            f"Step 2 — Reply with the link:\n"
            f"  Navigate to the tweet's permalink.\n"
            f"  Click Reply.\n"
            f"  Type: {reply_link}\n"
            f"  Click Reply/Post.\n\n"
        )
    task += f"Return the permalink URL of the tweet (https://x.com/{username}/status/...)."

    agent = Agent(
        task=task,
        llm=create_nim_llm(),
        browser_profile=_browser_profile(trinity_dir),
        sensitive_data={"x_pass": password},
        max_failures=_MAX_FAILURES,
    )
    history = await agent.run(max_steps=_MAX_STEPS)
    await _save_cookies(agent, trinity_dir)

    result = str(history.final_result() or "")
    return _extract_permalink(result)


async def reply_to_tweet(
    trinity_dir: Path,
    tweet_url: str,
    text: str,
    username: str = "",
    password: str = "",
) -> str:
    """Reply to an existing tweet. Returns the reply permalink URL."""
    if not username or not password:
        username, password = _creds()

    task = _login_preamble(username)
    task += (
        f"Navigate to: {tweet_url}\n"
        f"Click Reply.\n"
        f"Type exactly:\n{text}\n"
        f"Click Reply/Post.\n\n"
        f"Return the permalink URL of the reply."
    )

    agent = Agent(
        task=task,
        llm=create_nim_llm(),
        browser_profile=_browser_profile(trinity_dir),
        sensitive_data={"x_pass": password},
        max_failures=_MAX_FAILURES,
    )
    history = await agent.run(max_steps=_MAX_STEPS)
    await _save_cookies(agent, trinity_dir)

    result = str(history.final_result() or "")
    return _extract_permalink(result)


async def post_thread(
    trinity_dir: Path,
    tweets: list[str],
    username: str = "",
    password: str = "",
) -> str:
    """Post a multi-tweet thread. Returns the first tweet's permalink URL."""
    if not tweets:
        raise ValueError("tweets list is empty")
    if not username or not password:
        username, password = _creds()

    truncated = [t[:277] + "..." if len(t) > 280 else t for t in tweets]

    steps = _login_preamble(username)
    steps += (
        f"Step 1 — Post the first tweet:\n"
        f"  Click the compose box ('What is happening?!').\n"
        f"  Type exactly:\n{truncated[0]}\n"
        f"  Click the Post button. Wait for the tweet to appear.\n\n"
    )
    for i, tweet in enumerate(truncated[1:], start=2):
        steps += (
            f"Step {i} — Reply to continue the thread:\n"
            f"  Navigate to the previous tweet's permalink.\n"
            f"  Click Reply.\n"
            f"  Type exactly:\n{tweet}\n"
            f"  Click Reply/Post.\n\n"
        )
    steps += "Return the permalink URL of the FIRST tweet."

    agent = Agent(
        task=steps,
        llm=create_nim_llm(),
        browser_profile=_browser_profile(trinity_dir),
        sensitive_data={"x_pass": password},
        max_failures=_MAX_FAILURES,
    )
    history = await agent.run(max_steps=_MAX_STEPS * len(truncated))
    await _save_cookies(agent, trinity_dir)

    result = str(history.final_result() or "")
    return _extract_permalink(result)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_x_platform.py -k "post_tweet" -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/trinity/x_platform/browser.py tests/test_x_platform.py
git commit -m "feat(x-platform): browser-use X automation — post, reply, thread"
```

---

### Task 4: Trinity Tool Specs + Handlers

**Files:**
- Create: `src/trinity/x_platform/tools.py`
- Test: `tests/test_x_platform.py` (append)

- [ ] **Step 1: Write failing test for tool registration**

Append to `tests/test_x_platform.py`:

```python
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
        import subprocess as real_sub
        mock_sub.run.return_value = MagicMock(stdout="results", stderr="", returncode=0)
        mock_sub.TimeoutExpired = real_sub.TimeoutExpired
        result = x_tools.x_search_handler({"query": "test"}, tmp_path)
        assert isinstance(result, str)
        assert len(result) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_x_platform.py -k "all_specs or tool_handlers" -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement tools.py**

```python
# src/trinity/x_platform/tools.py
"""X platform Trinity tool specs + handlers — registered with the tool registry."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from trinity.x_platform import grok

log = logging.getLogger(__name__)

_trinity_dir: Path | None = None


def set_trinity_dir(path: Path) -> None:
    global _trinity_dir
    _trinity_dir = path


def _ensure_dir() -> Path:
    if _trinity_dir is None:
        raise RuntimeError("x_platform tools used before set_trinity_dir() was called")
    return _trinity_dir


# ── Read tools (Grok CLI) ───────────────────────────────────────────


X_SEARCH_SCHEMA: dict[str, Any] = {
    "name": "x_search",
    "description": (
        "Search X (Twitter) for posts, hashtags, users, or trends. "
        "Returns recent relevant posts with author, text, date, and URL."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "limit": {
                "type": "integer",
                "description": "Max results to return. Default 10.",
            },
        },
        "required": ["query"],
    },
}


def x_search_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    return grok.search(inp["query"], limit=int(inp.get("limit") or 10))


X_DRAFT_SCHEMA: dict[str, Any] = {
    "name": "x_draft",
    "description": (
        "Generate a tweet or thread draft using AI. Returns text ready to post. "
        "Does not post — use x_post or x_thread to publish."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "What the tweet is about."},
            "context": {
                "type": "string",
                "description": "Additional context (product details, audience, etc.).",
            },
            "tone": {
                "type": "string",
                "description": "Tone: professional, casual, urgent. Default professional.",
            },
        },
        "required": ["topic"],
    },
}


def x_draft_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    return grok.draft(
        inp["topic"],
        context=inp.get("context", ""),
        tone=inp.get("tone", "professional"),
    )


X_ANALYZE_SCHEMA: dict[str, Any] = {
    "name": "x_analyze",
    "description": (
        "Analyze X (Twitter) sentiment and engagement patterns around a topic. "
        "Returns sentiment, themes, notable accounts, trending angles."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Topic or keyword to analyze."},
        },
        "required": ["query"],
    },
}


def x_analyze_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    return grok.analyze(inp["query"])


# ── Write tools (browser-use) ───────────────────────────────────────


X_POST_SCHEMA: dict[str, Any] = {
    "name": "x_post",
    "description": (
        "Post a tweet to X (Twitter) via browser automation. "
        "Optionally include a reply_link which will be posted as a reply "
        "(links in replies preserve algorithmic reach)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Tweet text (max 280 chars, auto-truncated).",
            },
            "reply_link": {
                "type": "string",
                "description": "Optional URL to post as a reply to the main tweet.",
            },
        },
        "required": ["text"],
    },
}


def x_post_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    from trinity.x_platform.browser import post_tweet
    try:
        url = asyncio.run(post_tweet(
            _ensure_dir(),
            text=inp["text"],
            reply_link=inp.get("reply_link", ""),
        ))
        return f"Posted: {url}"
    except Exception as e:
        return f"Error posting tweet: {e}"


X_REPLY_SCHEMA: dict[str, Any] = {
    "name": "x_reply",
    "description": "Reply to an existing tweet on X (Twitter) via browser automation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "tweet_url": {
                "type": "string",
                "description": "URL of the tweet to reply to.",
            },
            "text": {
                "type": "string",
                "description": "Reply text (max 280 chars).",
            },
        },
        "required": ["tweet_url", "text"],
    },
}


def x_reply_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    from trinity.x_platform.browser import reply_to_tweet
    try:
        url = asyncio.run(reply_to_tweet(
            _ensure_dir(),
            tweet_url=inp["tweet_url"],
            text=inp["text"],
        ))
        return f"Replied: {url}"
    except Exception as e:
        return f"Error replying: {e}"


X_THREAD_SCHEMA: dict[str, Any] = {
    "name": "x_thread",
    "description": (
        "Post a multi-tweet thread on X (Twitter) via browser automation. "
        "Each item in tweets becomes one tweet in the thread."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "tweets": {
                "type": "string",
                "description": "JSON-encoded array of tweet texts.",
            },
        },
        "required": ["tweets"],
    },
}


def x_thread_handler(inp: dict, _ws: Path, **_ctx: Any) -> str:
    from trinity.x_platform.browser import post_thread
    try:
        tweets_raw = inp["tweets"]
        tweets = json.loads(tweets_raw) if isinstance(tweets_raw, str) else tweets_raw
        if not isinstance(tweets, list) or not tweets:
            return "Error: 'tweets' must be a non-empty JSON array of strings."
        url = asyncio.run(post_thread(_ensure_dir(), tweets=tweets))
        return f"Thread posted: {url}"
    except json.JSONDecodeError:
        return "Error: 'tweets' must be valid JSON array."
    except Exception as e:
        return f"Error posting thread: {e}"


ALL_SPECS = [
    (X_SEARCH_SCHEMA, x_search_handler),
    (X_DRAFT_SCHEMA, x_draft_handler),
    (X_ANALYZE_SCHEMA, x_analyze_handler),
    (X_POST_SCHEMA, x_post_handler),
    (X_REPLY_SCHEMA, x_reply_handler),
    (X_THREAD_SCHEMA, x_thread_handler),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_x_platform.py -k "all_specs or tool_handlers" -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/trinity/x_platform/tools.py tests/test_x_platform.py
git commit -m "feat(x-platform): 6 Trinity tool specs + handlers"
```

---

### Task 5: Config + Registry Wiring + App Init

**Files:**
- Modify: `src/trinity/config.py` (add `XPlatformConfig`)
- Modify: `src/trinity/tools/registry.py` (register X tools)
- Modify: `src/trinity/app.py` (call `set_trinity_dir`)

- [ ] **Step 1: Add XPlatformConfig to config.py**

Add after the `WorkspaceConfig` dataclass (around line 208):

```python
@dataclass
class XPlatformConfig:
    x_username_env: str = "X_USERNAME"
    x_password_env: str = "X_PASS"
    nim_api_key_env: str = "NVIDIA_API_KEY"
    nim_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    headless: bool = True
    max_steps: int = 40
    max_failures: int = 3
```

Add to `TrinityConfig` class body (around line 226):

```python
    x_platform: XPlatformConfig = field(default_factory=XPlatformConfig)
```

Add to `DEFAULTS` dict (after `"workspace"` section):

```python
    "x_platform": {
        "x_username_env": "X_USERNAME",
        "x_password_env": "X_PASS",
        "nim_api_key_env": "NVIDIA_API_KEY",
        "nim_model": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "nim_base_url": "https://integrate.api.nvidia.com/v1",
        "headless": True,
        "max_steps": 40,
        "max_failures": 3,
    },
```

Add to `load_config()` function, before the final `return TrinityConfig(...)` call:

```python
    # Build x_platform config
    xp = merged.get("x_platform", {})
    x_platform = XPlatformConfig(**{k: xp[k] for k in XPlatformConfig.__dataclass_fields__ if k in xp})
```

Add `x_platform=x_platform` to the `return TrinityConfig(...)` constructor call.

- [ ] **Step 2: Register X tools in registry.py**

Add this function after `_append_kanban_specs()` (around line 459):

```python
def _append_x_platform_specs() -> None:
    from trinity.x_platform import tools as x_tools
    for schema, handler in x_tools.ALL_SPECS:
        _BUILTIN_SPECS.append(ToolSpec(
            name=schema["name"],
            definition=schema,
            handler=handler,
            subsets=("builder",),
        ))


_append_x_platform_specs()
```

Make sure this call comes BEFORE the `for _spec in _BUILTIN_SPECS:` loop that registers everything.

- [ ] **Step 3: Wire set_trinity_dir in app.py init()**

In `app.py` function `init()`, add after the `kanban_db.init(config.trinity_dir)` line (around line 45):

```python
    from trinity.x_platform import tools as x_tools
    x_tools.set_trinity_dir(config.trinity_dir)
```

- [ ] **Step 4: Run full test suite to verify no regressions**

Run: `pytest tests/ -v --timeout=30`
Expected: All existing tests pass + new x_platform tests pass

- [ ] **Step 5: Commit**

```bash
git add src/trinity/config.py src/trinity/tools/registry.py src/trinity/app.py
git commit -m "feat(x-platform): config, registry wiring, app init"
```

---

### Task 6: Social Media Specialist Employee Template

**Files:**
- Create: `templates/employees/social_media.md`

- [ ] **Step 1: Create template**

```markdown
# {name} — Social Media Specialist at {company_name}

## Core Identity

You are {name}, the Social Media Specialist at {company_name}. {company_description}

You own the company's X (Twitter) presence. You search for relevant conversations, craft posts that drive engagement, and publish content that positions {company_name} as the go-to source in its niche. You think in hooks, not headlines.

## Operating Style

- **Hook + reply strategy.** Never put links in the main tweet — links kill algorithmic reach. Post the hook first, then reply with the link.
- **Never discount. Only add value.** No coupons, no price cuts, no "limited time" gimmicks. Stack bonuses, share data, show proof.
- **Specific beats generic.** Every tweet includes real numbers, real names, real sources. "15,770 new FMCSA carriers" not "thousands of new leads."
- **280 characters is a discipline, not a limit.** Say more with less. Cut every word that does not earn its spot.
- **Search before you post.** Always x_search the topic first. Know what is already being said before you add your voice.
- **Engage, don't broadcast.** Use x_reply to join existing conversations where {company_name}'s data or products add real value.
- **Threads for depth.** Use x_thread when one tweet cannot do the topic justice. First tweet is the hook; each reply adds one specific point.

## Tools Available

- **x_search** — Search X for posts, hashtags, users, trends
- **x_draft** — Generate tweet/thread drafts with brand voice
- **x_analyze** — Sentiment and engagement analysis
- **x_post** — Publish a tweet (with optional reply-link)
- **x_reply** — Reply to an existing tweet
- **x_thread** — Publish a multi-tweet thread

## Workflow

1. **Research** — x_search the topic. Understand the conversation.
2. **Analyze** — x_analyze sentiment and engagement patterns.
3. **Draft** — x_draft content. Review for specificity and brand voice.
4. **Publish** — x_post or x_thread. Always hook first, link in reply.
5. **Report** — Send results to the CMO via Telegram (send_telegram).

## Rules

- Never post without searching first. Context before content.
- Never include links in the main tweet body. Links go in replies.
- Never use generic hashtags (#business, #data). Only use niche-specific ones if they add reach.
- Never post more than 5 times per day. Quality over volume.
- Never engage in arguments, controversies, or political topics.
- Always truncate tweets to 280 characters. Auto-truncation adds "..." at 277.
- Always report what was posted, where, and the resulting URL via Telegram.
```

- [ ] **Step 2: Commit**

```bash
git add templates/employees/social_media.md
git commit -m "feat(x-platform): Social Media Specialist employee template"
```

---

### Task 7: Full Test File Assembly + Truncation Test

**Files:**
- Test: `tests/test_x_platform.py` (finalize)

- [ ] **Step 1: Add truncation test**

Append to `tests/test_x_platform.py`:

```python
def test_tweet_truncation():
    """Tweets longer than 280 chars are truncated to 277 + '...'."""
    long_text = "A" * 300

    with patch.dict(os.environ, {"X_USERNAME": "u", "X_PASS": "p", "NVIDIA_API_KEY": "k"}):
        with patch("trinity.x_platform.browser.Agent") as mock_agent_cls:
            with patch("trinity.x_platform.browser.create_nim_llm"):
                with patch("trinity.x_platform.browser.BrowserProfile"):
                    mock_agent = MagicMock()
                    mock_history = MagicMock()
                    mock_history.final_result.return_value = "https://x.com/u/status/999"
                    mock_agent.run = MagicMock(
                        return_value=asyncio.coroutine(lambda: mock_history)()
                    )
                    mock_agent_cls.return_value = mock_agent

                    from trinity.x_platform.browser import post_tweet
                    asyncio.run(post_tweet(Path("/tmp/.trinity"), long_text))

                    task_text = mock_agent_cls.call_args.kwargs.get(
                        "task", mock_agent_cls.call_args[1].get("task", "")
                    )
                    # The 300-char text should be truncated in the task prompt
                    assert "A" * 300 not in task_text
                    assert "..." in task_text
```

- [ ] **Step 2: Run full x_platform test suite**

Run: `pytest tests/test_x_platform.py -v --timeout=30`
Expected: 10 tests passed

- [ ] **Step 3: Run entire project test suite**

Run: `pytest tests/ -v --timeout=30`
Expected: All tests pass (96 previous + 10 new = 106)

- [ ] **Step 4: Final commit**

```bash
git add tests/test_x_platform.py
git commit -m "test(x-platform): finalize test suite — 10 tests covering all layers"
```

---

### Task 8: Smoke Test

**Files:** None (manual verification)

- [ ] **Step 1: Verify tool registration**

Run: `python3 -c "from trinity.tools.registry import BUILDER_TOOLS; print([t for t in BUILDER_TOOLS if t.startswith('x_')])"`
Expected: `['x_analyze', 'x_draft', 'x_post', 'x_reply', 'x_search', 'x_thread']`

- [ ] **Step 2: Verify Grok search (live)**

Run: `python3 -c "from trinity.x_platform.grok import search; print(search('OEFR Digital', limit=3)[:200])"`
Expected: Some search results (or error string if Grok CLI needs auth)

- [ ] **Step 3: Verify config loading**

Run: `python3 -c "from trinity.config import load_config; c = load_config(); print(f'x_platform.nim_model={c.x_platform.nim_model}')"`
Expected: `x_platform.nim_model=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`

- [ ] **Step 4: Commit all remaining changes**

```bash
git add -A -- src/trinity/ templates/ tests/ docs/
git commit -m "feat(x-platform): complete X platform integration — 6 tools, NIM Omni, browser-use"
```
