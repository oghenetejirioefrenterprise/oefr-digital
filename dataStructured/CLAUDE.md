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

## Storefront (Phase 2 sub-project 1)

Public site at https://data.oefrenterprise.com — Next.js 14 App Router at `~/apps/dataStructured/site/`. Reads `state/products/*/spec.json` + `launch-report.json` at build time. Filters on `compliance_verdict === "PASS"` AND `status === "FULLY_SHIPPED"`. Engineer agent's shipping flow now includes a `git push` step to trigger Vercel auto-deploy of new product pages.

```bash
# Local dev
cd ~/apps/dataStructured/site
npm install
npm run dev  # → http://localhost:3501

# Tests
npm test

# Deploy (usually auto on git push; manual override available)
vercel --prod
```

## Multi-channel Telegram routing (Phase 3)

Specialized agents route their output to topic-specific groups instead of all DMing the founder:

| Channel | Used by |
|---|---|
| `founder_dm` | CEO daily DM (always populated; chat_id 1366707521) |
| `compliance_flags` | compliance-officer NEEDS_FOUNDER_REVIEW + REVOCATION events |
| `financial_alerts` | cfo daily digest + anomalies |
| `marketing_reports` | marketing-lead plans + partnerships-lead candidate briefs |

Channel chat_ids live in `trinity.toml` under `[telegram.channels]`. Empty string = unset → `scripts/telegram_dispatch.py` falls back to `founder_dm` so messages aren't lost.

**One-time founder setup:**
1. Create Telegram groups manually (one per non-DM channel).
2. Add `@Ralph_the_builder_oefr_bot` to each group as admin.
3. Get the group chat_id via `https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getUpdates` after sending one message in the group.
4. Set the chat_id strings in `trinity.toml`'s `[telegram.channels]` block.
5. Reload trinity daemon: `trinity stop && trinity start --daemon`.

Use from any agent or script:
```python
from scripts.telegram_dispatch import send_to_channel
send_to_channel("financial_alerts", "MRR snapshot: $29")
```

## Affiliate tracking (Phase 3 sub-project 6)

Generate an affiliate link for a partner:

```bash
python scripts/affiliate_link.py --partner <partner_handle> --product-slug <slug> [--commission-pct 30]
```

Outputs a Stripe Payment Link with `?client_reference_id=...` appended. The customer-success agent's 2-hourly sweep auto-reconciles charges with that reference back to the partner via `state/partnerships/sales-log.json`. Per-partner totals roll up to `state/partnerships/active.json`.

Founder reviews `active.json` monthly, pays partners manually (no auto-payouts), and edits `sales-log.json` entries to set `paid_to_partner: true` after each payout.

## Reference docs

- `docs/superpowers/specs/2026-05-04-datastructured-design.md` — v1 design spec
- `docs/PRD.md` — full vision + phase roadmap
- `docs/superpowers/plans/2026-05-04-datastructured-v1.md` — this implementation plan
