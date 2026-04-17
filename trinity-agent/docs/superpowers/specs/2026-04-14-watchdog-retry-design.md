# Watchdog Retry System

**Date:** 2026-04-14
**Status:** Approved

## Problem

The Trinity agent errors out during work (most commonly `Command failed with exit code 1` from the Claude Agent SDK). When this happens, the error is caught and sent to the user as "Hit an error: ..." with no recovery attempt. The user must manually re-send their message.

## Solution

Wrap the agent execution in `handle_message()` with a retry loop. On failure, re-invoke the agent with the original message plus error context so it can adjust its approach. Cap retries at a configurable limit. Log exhausted failures to the knowledge base for persistent visibility.

## Config

New field in `[agent]` section of `trinity.toml`:

```toml
[agent]
max_retries = 3
```

- Default: `3` (meaning up to 4 total attempts: 1 original + 3 retries)
- Set to `0` to disable retries
- Added to `AgentConfig` dataclass in `config.py` and `DEFAULTS`

## Retry Logic

Location: `handle_message()` in `app.py`, wrapping the existing try/except block.

### Flow

1. **Attempt 1** — run normally with the original user message
2. **On exception** — increment retry counter, update the Telegram status message with `"Retrying (attempt N/M)..."`, re-run with modified input
3. **Modified input** — original message + `"\n\n[Previous attempt failed: {error}. Try a different approach.]"`
4. **On success** — deliver response normally, no indication of prior failures
5. **On exhaustion** — send last error to Telegram AND log an issue via `wiki.log_issue()`

### What gets retried

- Both `_run_conversational()` and `_run_action()` failures
- Each retry is a fresh call with modified input, not a resume
- The router classification runs once — retries use the same track

### What doesn't change

- Streaming/typing infrastructure stays as-is
- Memory extraction only runs on successful responses
- `StreamState` is reused across retries (activity log accumulates)

### Status message during retries

The existing `StreamState` status message is updated to show retry progress:
```
Retrying (attempt 2/4)...

[Previous error: Command failed with exit code 1]
```

### Failure logging

When all retries are exhausted:
1. Send to Telegram: `"Failed after {N} attempts: {last_error}"`
2. Log to knowledge base: `wiki.log_issue(trinity_dir, "agent", description, status="open")`

This surfaces the failure in the briefing so patterns become visible over time.

## Files to Modify

| File | Change |
|------|--------|
| `config.py` | Add `max_retries: int = 3` to `AgentConfig`, add to `DEFAULTS` |
| `app.py` | Retry loop in `handle_message()`, error-context re-invocation, failure logging |
