# Validations

One file per opportunity under validation. Each file is the complete test plan: Gumroad listing copy, forum post copy, kill/greenlight thresholds, measurement plan.

Written by `validator-loop` cycle. Read by Trinity (executes the plan) and by heartbeat (polls for signups / thresholds).

## Validation ladder

1. **Rung 1 — FREE.** Gumroad pre-order + value-first forum post. Kill: 0 signals in 14 days. Greenlight: ≥5 signups. Partial: climb.
2. **Rung 2 — $10–20 PAID.** Reddit/Pinterest promoted post behind same landing page. Only triggered by rung-1 partial.
3. **Rung 3 — MVP BUILD.** Only after rung 1 or 2 greenlights.

## File naming

`<YYYY-MM-DD>-<opportunity-slug>.md`

Slug should match the opportunity queue entry so the two files stay linked.

## Status lifecycle

`drafted` → `live_rung1` → `live_rung2` → `greenlit` or `rejected`

The validator cycle writes the initial doc. Trinity / heartbeat update status as results come in.
