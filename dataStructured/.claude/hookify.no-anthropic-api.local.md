---
name: no-anthropic-api
enabled: false
---

RETIRED 2026-05-10: Original rule was based on a wrong premise.

OpenAI ChatGPT Plus ($20/mo) does NOT include API credits — it is a separate billing
system from the OpenAI API. The OPENAI_API_KEY in ~/.profile has zero API quota.

Correct cost policy:
- Browser-use (Twitter/Reddit distribution): uses ChatAnthropic claude-haiku-4-5
  via the existing $200/mo Anthropic plan (ANTHROPIC_API_KEY = ANTHROPIC_SETUP_TOKEN_cciephantom)
- Trinity-agent orchestration: uses claude_sdk (Claude Code OAuth, same plan)
- Codex CLI rescue/coding: uses OpenAI subscription via codex:rescue skill
- No direct OpenAI API calls — no credits available on the $20 ChatGPT Plus plan
