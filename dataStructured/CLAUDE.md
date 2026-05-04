# CLAUDE.md — DataStructured

Project context for Claude Code. Auto-loaded when a session is opened in this folder.

## What this is

DataStructured is a standalone, autonomous, public-data-as-a-product company. Built on the BuiltWith / Nomad List model: harvest public data, package for a niche audience, sell as one-time / membership / SaaS.

**Folder-scoped:** everything lives inside `~/apps/dataStructured/`. Nothing here references projects outside this folder, the global `~/.claude/agents/`, or `~/.openclaw/`.

## Operating model

Built on **trinity-agent** (`~/apps/trinity-agent`). Six employees in `.trinity/employees/`:

| Employee | Role |
|---|---|
| `ceo` | Strategic orchestrator + sole comms layer (only employee that DMs the founder) |
| `opportunity-researcher` | Wide-scope demand discovery (daily 13:00 ET) |
| `data-engineer` | Public-data harvest via Google operators + AI |
| `data-steward` | Quality gate (clean / dedupe / validate) |
| `compliance-officer` | Hard ethics gate (PASS / FAIL / NEEDS FOUNDER REVIEW) |
| `engineer` | Stripe Payment Link + Gumroad listing shipper |

## Canonical workflow

```
research-lead → ceo (approve) → data-engineer → data-steward
   → compliance-officer (PASS) → ceo writes spec → engineer → distribution-queue
```

## Hard rules (every agent enforces)

1. **Public data only.** No auth-bypass, no scraping behind login, no purchased private datasets.
2. **No PII.** Personal email, phone, home address, financial accounts → automatic compliance FAIL.
3. **Source URL on every row.** Non-negotiable for shipping.
4. **Production code only.** No mocks, no placeholders, no half-built features in shipped products.
5. **Test before claiming done.** URL must load + buy flow must work.
6. **Folder-scoped.** No agent here references projects outside `~/apps/dataStructured/`.
7. **Bootstrap discipline.** No new paid SaaS, no premature engineering.
8. **Never discount.** Stack value (bonus content, tier upgrades) instead of cutting price.

## Common commands

```bash
cd ~/apps/dataStructured

# Start daemon (Telegram bot + scheduler)
trinity start --daemon

# One-shot task
trinity run "do today's work" -e ceo

# Workspace status
trinity status

# Run tests
pytest

# Stop daemon
trinity stop
```

## Reference docs

- `docs/superpowers/specs/2026-05-04-datastructured-design.md` — v1 design spec
- `docs/PRD.md` — full vision + phase roadmap
- `docs/superpowers/plans/2026-05-04-datastructured-v1.md` — this implementation plan
