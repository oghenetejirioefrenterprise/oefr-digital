# X Platform Integration — Design Spec

**Date:** 2026-05-25
**Status:** Approved
**Author:** Trinity

## Overview

Add X (Twitter) interaction capabilities to Trinity Agent via three layers:
Grok CLI for read operations (search, draft, analyze), NVIDIA NIM Nemotron
Omni for vision-based browser reasoning, and browser-use for automated posting.
A new Social Media Specialist employee uses these tools.

## Motivation

OEFR Digital needs autonomous X presence for product distribution and brand
building. The existing DataStructured project already proves the
browser-use + NIM Omni + cookie persistence stack works in production
(`scripts/post_twitter_browseruse.py`). This design brings that proven
pattern into Trinity's tool system so any employee can search X and the
Social Media Specialist can post autonomously via scheduler cycles.

## Architecture

Three layers, each with a clear role:

| Layer | Technology | Responsibility |
|-------|------------|----------------|
| Read  | Grok CLI headless (`grok -p`) | Search X, analyze trends, generate content |
| Vision | NIM Nemotron Omni via `browser-use` `ChatOpenAILike` | Drive browser through screenshots + reasoning |
| Write | `browser-use` `Agent` + headless Chromium | Login, post, reply, thread on x.com |

### Data flow — posting

```
Agent request -> x_draft (Grok generates content)
              -> x_post  (browser-use + NIM Omni logs in, types, clicks Post)
              -> result URL returned to agent
```

### Data flow — searching

```
Agent request -> x_search (grok -p "search X for ...")
              -> plain text parsed -> formatted results returned to agent
```

### Session management

Cookies stored at `<trinity_dir>/state/browser_cookies/twitter.json`.
Persisted after each browser-use session. Reused on next run to skip
login when session is still valid. Same pattern as DataStructured.

## Components

### `src/trinity/x_platform/__init__.py`

Package init. Empty.

### `src/trinity/x_platform/nim_llm.py`

NIM client factory for browser-use.

```python
def create_nim_llm(
    model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    max_completion_tokens=2048,
    temperature=0.2,
) -> ChatOpenAILike:
```

- Uses `NVIDIA_API_KEY` from environment (sourced from `~/.profile`)
- Returns `ChatOpenAILike` pointing at `https://integrate.api.nvidia.com/v1`
- Auto-sources `~/.profile` if key not in env
- Temperature 0.2 for deterministic browser actions

### `src/trinity/x_platform/browser.py`

browser-use X automation. All functions are async.

```python
async def post_tweet(
    trinity_dir: Path,
    text: str,
    reply_link: str = "",
    username: str = "",
    password: str = "",
) -> str:
    """Post hook tweet, optionally reply with link. Returns tweet URL."""

async def reply_to_tweet(
    trinity_dir: Path,
    tweet_url: str,
    text: str,
    username: str = "",
    password: str = "",
) -> str:
    """Reply to an existing tweet. Returns reply URL."""

async def post_thread(
    trinity_dir: Path,
    tweets: list[str],
    username: str = "",
    password: str = "",
) -> str:
    """Post a multi-tweet thread. Returns first tweet URL."""
```

Implementation details:
- browser-use `Agent` with `max_failures=3`, `max_steps=40`
- `BrowserProfile(headless=True, args=["--no-sandbox", ...])` with stored cookies
- Login handles X identity verification ("enter your phone or username")
- Hook+reply pattern: links in replies preserve algorithmic reach
- Credentials from `X_USERNAME` / `X_PASS` env vars (fall back to params)
- Cookie persistence after each session at `<trinity_dir>/state/browser_cookies/twitter.json`

### `src/trinity/x_platform/grok.py`

Grok CLI headless wrapper. All functions are sync (subprocess).

```python
def search(query: str, limit: int = 10) -> str:
    """Search X via Grok CLI. Returns formatted results."""

def draft(topic: str, context: str = "", tone: str = "professional") -> str:
    """Generate tweet/thread draft via Grok CLI."""

def analyze(query: str) -> str:
    """Analyze X sentiment/engagement via Grok CLI."""
```

Implementation details:
- All calls: `subprocess.run(["grok", "-p", prompt], capture_output=True, timeout=60)`
- Output format: `--output-format plain` (simpler parsing than streaming-json)
- Prompts include OEFR brand context for consistent voice
- Search prompt instructs Grok to use its built-in `search_x` tool
- Results returned as plain text (agent interprets)

### `src/trinity/x_platform/tools.py`

6 Trinity tool specs + handler functions.

**Read tools (use grok.py):**

| Tool | Input schema | Description |
|------|-------------|-------------|
| `x_search` | `query: str`, `limit?: int` | Search X posts, hashtags, users, trends |
| `x_draft` | `topic: str`, `context?: str`, `tone?: str` | Generate tweet/thread draft with brand voice |
| `x_analyze` | `query: str` | Sentiment/engagement analysis |

**Write tools (use browser.py):**

| Tool | Input schema | Description |
|------|-------------|-------------|
| `x_post` | `text: str`, `reply_link?: str` | Post a tweet (link goes in reply) |
| `x_reply` | `tweet_url: str`, `text: str` | Reply to a specific tweet |
| `x_thread` | `tweets: list[str]` | Post a multi-tweet thread |

Tool registration:
- `X_TOOLS` list in tools.py, appended to registry in `tools/registry.py`
- `set_trinity_dir(path)` module-level setter (same pattern as kanban tools)
- Write tools run browser-use via `asyncio.run()` inside the sync handler

### `templates/employees/social_media.md`

Social Media Specialist identity template.

Key traits:
- Brand voice: OEFR tone (professional, data-driven, no discounts, value-add only)
- Hook+reply strategy: main tweet is the hook (no links), link goes in reply
- 280-char awareness, thread structure knowledge
- Product catalog awareness (datasets, digital products)
- Engagement patterns: respond to relevant conversations, not spam
- Access: `X_TOOLS` + `RESEARCHER_TOOLS`

### Integration wires

**`src/trinity/tools/registry.py`:**
- Import and register `X_TOOLS` alongside existing `BUILDER_TOOLS`, `RESEARCHER_TOOLS`
- Social Media employee gets `X_TOOLS + RESEARCHER_TOOLS`

**`src/trinity/app.py`:**
- Call `x_tools.set_trinity_dir(trinity_dir)` during `init()`

**`src/trinity/config.py`:**
- Add `x_platform` config section to `TrinityConfig`:
  - `x_username_env: str = "X_USERNAME"`
  - `x_password_env: str = "X_PASSWORD"`
  - `nim_api_key_env: str = "NVIDIA_API_KEY"`
  - `nim_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"`
  - `nim_base_url: str = "https://integrate.api.nvidia.com/v1"`
  - `headless: bool = True`
  - `max_steps: int = 40`
  - `max_failures: int = 3`

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Grok CLI timeout (>60s) | Return error string to agent, don't crash |
| Grok CLI not in PATH | Return "grok CLI not installed" error |
| browser-use fails all 3 attempts | Raise RuntimeError with last 200 chars of agent output |
| No tweet permalink in result | Raise RuntimeError (post likely failed) |
| Cookie save failure | Log warning, continue (next run re-authenticates) |
| Missing X credentials | Clear error: "X_USERNAME / X_PASS not set" |
| Missing NVIDIA_API_KEY | Auto-source ~/.profile, raise if still missing |
| Tweet > 280 chars | Truncate to 277 + "..." |

## Testing

All tests use mocks — no real API calls, no real browser sessions.

| Test | What it verifies |
|------|-----------------|
| `test_grok_search` | Subprocess called with correct prompt, result parsed |
| `test_grok_draft` | Subprocess called, text extracted from output |
| `test_grok_analyze` | Subprocess called with analysis prompt |
| `test_nim_llm_factory` | ChatOpenAILike created with correct base_url and model |
| `test_post_tweet` | browser-use Agent created with correct task prompt, credentials as sensitive_data |
| `test_reply_to_tweet` | Task prompt includes tweet URL |
| `test_post_thread` | Task prompt includes all tweets in sequence |
| `test_tool_registration` | All 6 tools in X_TOOLS with correct schemas |
| `test_tool_handlers_wired` | Each handler callable, returns string |
| `test_truncation` | Tweets > 280 chars truncated properly |

## Dependencies

All already installed:
- `browser-use` 0.12.6 (includes `ChatOpenAILike`)
- `playwright` 1.58.0
- `grok` CLI v0.1.220 at `~/.grok/bin/grok`
- `NVIDIA_API_KEY` in `~/.profile`
- `X_USERNAME` / `X_PASS` in `~/.profile`

No new dependencies required.

## Cost

- NIM API: free tier (40 RPM, unlimited credits)
- Grok CLI: existing subscription
- browser-use: local Chromium, no API cost (NIM handles the LLM calls)
- Total incremental cost: $0
