# DataStructured

Autonomous public-data-as-a-product company. Built on the BuiltWith / Nomad List / Starter Story playbook: harvest public data, structure it for a paying audience, sell as one-time digital product, recurring membership, or SaaS.

## What's in this folder

| Path | Purpose |
|---|---|
| `trinity.toml` | trinity-agent config — auth, employees, scheduler cycles |
| `.env.example` | Secrets template (real `.env` is gitignored) |
| `CLAUDE.md` | Project context for Claude Code sessions |
| `docs/PRD.md` | Full vision + phase roadmap |
| `docs/superpowers/specs/` | Design specs (v1 + future phases) |
| `docs/superpowers/plans/` | Implementation plans |
| `.trinity/` | trinity-agent runtime state (gitignored) |
| `state/` | Domain artifacts (opportunities, datasets, ethics ledger, products, distribution queue) |
| `scripts/` | Stripe + Gumroad helpers, CEO orchestrator |
| `tests/` | pytest test suite |

## Quick start

```bash
cd ~/apps/dataStructured
cp .env.example .env             # then fill in secrets
pip install -e .[dev]
trinity start --daemon           # starts Telegram bot + scheduler
```

## Operating model

Six employees. CEO is the sole employee that talks to the founder via Telegram DM. Other employees are silent workers — they write to disk and Trinity memory.

Daily cycle: opportunity-researcher fires at 13:00 ET; CEO fires at 19:00 ET, runs the pipeline, sends one DM summary.

See `docs/superpowers/specs/2026-05-04-datastructured-design.md` for full spec.

## Naming

Working name: **DataStructured** (matches folder). Easy to rename — brand lives in `README.md`, `trinity.toml` `[company]`, `CLAUDE.md`, and the 6 employee identity files.
