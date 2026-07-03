# Product Roster

**Single source of truth for all OEFR Digital products.** Read by `trinity/rules/` (allocator, killer); written by `killer-loop` and (Phase 1+) sensor-fed allocator.

## Status enum

- `candidate` — opportunity scored, not yet validated
- `validating` — validation test in flight (landing page / paid traffic / community probe)
- `producing` — built, launched, in observation window (default 14 days)
- `scaling` — has revenue or traffic signal, running structured experiments
- `maintain` — stable revenue, low-touch
- `sunset-pending` — failed kill rule; grace period before unlist (default 7 days)
- `dead` — sunset complete, archived

## Kill rule format

`metric < threshold in window` — windows in days.

Standard rules:
- New products (default at launch): `views < 10 in 14d`
- Producing → Scaling threshold: `sales >= 1 in 30d` OR `views >= 100 in 14d`
- Scaling → Maintain: stable revenue trend
- Any product: `sales < 1 in 60d AND views < 50 in 30d` → sunset-pending

## Conventions

- `Last signal` = most recent date a sale, view, or other positive signal was recorded.
- `Revenue 30d` in USD. `0` means literally zero, `?` means not yet measured (Phase 1 sensors will populate).
- New columns may be added; rules layer ignores unknown columns.
- TJ may hand-edit `Status` to `maintain` for products that are intentionally kept (with rationale in Notes). The killer respects manual `maintain` and does not auto-sunset; it is logged as an override.

## Active products


| Product | Status | Thesis | Kill rule | Launched | Last signal | Revenue 30d | Notes |
|---|---|---|---|---|---|---|---|
| netarch-pro | dead | Networking cert buyers want a curated study path | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | TJ-default niche; Phase 0 candidate for sunset |
| habitforge | dead | Habit tracking SaaS | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | No validation pre-build |
| resume-builder | dead | Free resume builder with paid export | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Saturated category |
| invoice-generator | dead | Free invoice generator | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Saturated category |
| subscription-tracker | dead | Track recurring subs | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | No validation |
| content-calendar | dead | Editorial calendar tool | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | No validation |
| meal-planner | dead | Drag-drop meal planning | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Lifestyle niche, no edge |
| password-vault | dead | Browser-side encrypted vault | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Saturated, trust-required market. **Neo P3 (2026-05-18):** `.env.local` (gitignored, 223B, mtime Mar 28) carries live `STRIPE_SECRET_KEY=sk_live_…` on a dead-status product — TJ keep/trash ruling pending day 5. Zero current exposure (gitignored, no git history) but theoretical drift if dir ever bundled/synced. ~30s fix: `trash` the file. |
| compliance-calendar | dead | Compliance deadline tracker | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | B2B-adjacent, no sales motion |
| budget-tracker | dead | Personal finance tracker | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Saturated |
| net-salary-calc | dead | Net salary calculator | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Free-tool category, monetization unclear |
| ai-layoff-pack | dead | Layoff survival templates | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Specific moment, window may have passed |
| entryexpert | maintain | Stock market scanner with IBKR (TJ active user) | manual | 2026-03 | — | 0 | TJ uses internally; keep alive even at $0 revenue |
| adhd-productivity | dead | ADHD productivity templates | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | No validation pre-build |
| adhd-productivity-os | dead | ADHD Notion OS bundle | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | No validation pre-build |
| ai-policy-pack | dead | AI policy templates for orgs | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | B2B, requires sales |
| etsy-spreadsheets | producing | Spreadsheet bundles on Etsy | sales<1 in 60d AND views<50 in 30d | 2026-03 | 2026-04-01 | 5 | 1 confirmed sale (date approx 2026-04-01, revenue $5 placeholder); TJ to confirm exact listing and amount. **Neo P1 (2026-04-20):** 3 AI-prompt-category listings in shop violate Etsy Creativity Standards — shop-suspension vector across ALL 44 listings. **Neo P1 (2026-04-27): Day 6 past 48h reposition window — still unfixed. Trinity-owned under autonomy mandate. Asymmetric tail risk: a single Etsy reviewer kills 27 listings including the 5-star anchor and the entire MD women's catalog.** **Neo P2 (2026-05-18):** budget-planner-bundle alignment flag from TJ Telegram 2026-05-17 12:00 ET — investigation TJ-context-blocked (ours/comp/building unclear, which element unclear). Etsy shop reputation cross-listing reinforced by TJ — strengthens P1 priority on CATEGORY-KILL 3 legacy AI-Prompts listings. |
| exam_simulator | dead | Cert exam practice | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | TJ-default niche |
| first-100-users-playbook | dead | Marketing playbook | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Crowded category |
| gumroad-products | meta | Meta directory for Gumroad listings | n/a | n/a | n/a | n/a | Not a product itself; meta-org |
| n8n-network-templates | dead | n8n workflows for networking | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | TJ-default niche |
| network-resume-bundle | dead | Resume templates for network engineers | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | TJ-default niche; networking buyers don't pay $15 templates |
| network-spreadsheet-pack | dead | Spreadsheets for network engineers | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | TJ-default niche |
| notion-templates | dead | Job tracker templates | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Saturated |
| tax-organizer-2026 | maintain | Tax season organizer spreadsheet | manual | 2026-03 | — | 0 | Seasonal protection through 2026-04-30; reassess May 1 — flip to producing with normal kill rule. **Neo P1 (2026-04-20):** Currently discounted 25% under shop-wide SPRING2026 sale (Apr 15–May 15) — violates "never discount" directive; TJ binary decision pending Day 5. **Neo P2 (2026-06-08 weekly):** This week's active revenue push (Etsy 4483521294 / Gumroad qnljkix, June-15 SEO seeding). Fulfillment is Etsy/Gumroad-native (no custom checkout) → low code surface. BUT any own-landing/SEO seeding needs an oefr-website deploy, which hits the standing **Vercel promote-scope foot-gun** (autonomous CLI builds Ready but cannot promote `www` → silently leaves prod stale). Gate every oefr-website deploy on `web-deploy-guard.py --preflight` + curl-verify the live page post-promote. If a custom Stripe download is ever added, the shared-Stripe-account paywall-bind (product+amount+currency) is mandatory before launch. |
| Tax-relief | dead | Tax relief research + config gen | sales<1 in 60d AND views<50 in 30d | 2026-03 | — | 0 | Research-stage, no live offer |

## Sunset queue

Products in `sunset-pending` move to `dead` after 7 days unless a new positive signal arrives. The killer-loop manages transitions automatically. Actual unlisting from Etsy/Gumroad is queued for a Phase 1 `sunset-executor` cycle (browser automation) — Phase 0 only updates state and notifies via Telegram.

## Override log

When TJ manually sets a product to `maintain` (or otherwise overrides killer-loop), the override is logged here with date and rationale. After 30 days, killer-loop reviews overrides against actual outcomes — repeated underperforming overrides become a governance signal.

| Date | Product | Override | Rationale | Outcome (30d) |
|------|---------|----------|-----------|---------------|
| 2026-04-16 | entryexpert | maintain (no auto-sunset) | TJ's internal trading tool, value isn't revenue | — |
| 2026-04-16 | tax-organizer-2026 | maintain through 2026-04-30 | Seasonal protection — tax season window; killer would otherwise sunset before season ends | — |

## Post-mortems

When a product moves to `dead`, killer-loop appends a one-line entry here with the cause. Patterns become inputs to opportunity-scout to avoid repeat failures.

| Date | Product | Cause | Lesson |
|------|---------|-------|--------|
| 2026-04-16 | netarch-pro | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | habitforge | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | resume-builder | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | invoice-generator | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | subscription-tracker | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | content-calendar | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | meal-planner | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | password-vault | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | compliance-calendar | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | budget-tracker | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | net-salary-calc | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | ai-layoff-pack | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | adhd-productivity | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | adhd-productivity-os | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | ai-policy-pack | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | exam_simulator | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | first-100-users-playbook | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | n8n-network-templates | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | network-resume-bundle | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | network-spreadsheet-pack | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | notion-templates | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
| 2026-04-16 | Tax-relief | sales<1 in 60d (skipped Phase 0: views<50 in 30d (no sensor)) | No validation pre-build; consider validation gate before next product in this category |
