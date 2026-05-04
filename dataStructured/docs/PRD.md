# DataStructured — Product Requirements Document

**Status:** Active. Reviewed 2026-05-04.
**Companion:** [`docs/superpowers/specs/2026-05-04-datastructured-design.md`](./superpowers/specs/2026-05-04-datastructured-design.md) — the v1 design spec.

---

## Vision

DataStructured is a public-data-as-a-product company operated as an autonomous agent collective. Public data → packaged for a paying audience → sold as one-time digital product, recurring membership, or SaaS-with-search-UI.

Reference companies for the model: BuiltWith ($22M/yr, 4 employees), Nomad List, Starter Story, GetLatka, SpamZilla, OfferVault. Most bootstrapped, most very lean, all built on data the public has rights to.

**The bet:** an autonomous agent collective using LLM judgment for niche selection, public-data harvest, ethics gating, and product shipping can replicate the BuiltWith pattern at higher leverage and lower headcount cost than a human-staffed equivalent.

---

## Primary success criterion (90 days)

**The autonomous system runs hands-off and produces value end-to-end.**

Revenue is secondary — any sales are a bonus. The bar for v1 is the autonomy proof: the agent collective executes the pipeline (research → harvest → clean → compliance → ship) without founder intervention except where compliance flags genuine edge cases.

This priority drives every architectural decision: optimize for the system running reliably without the founder, not for polish or marketing reach.

---

## Constraints (forever)

These do not change between phases. They are inviolable.

1. **Public data only.** No auth-bypass, no scraping behind login walls, no purchased private datasets.
2. **No PII.** Personal email, phone, home address, financial accounts, government IDs → automatic compliance FAIL.
3. **Source URL on every row.** Non-negotiable for shipping.
4. **Production code only.** No mocks, no placeholders, no half-built features in anything customer-facing.
5. **Test before claiming done.** Live URL must load + buy flow must work before any "shipped" claim.
6. **Folder-scoped.** No artifact, agent, or config here references projects outside `~/apps/dataStructured/`.
7. **Bootstrap discipline.** No paid SaaS, no premature engineering, no infra spend without unit-economic justification.
8. **Never discount.** Stack value (bonus content, tier upgrades) instead of cutting price. Discounting decays brand equity and trains buyers to wait.

---

## Phase roadmap

Each phase has explicit entry triggers (what must be true to start it), success criteria (what proves it worked), and scope (what's added vs deferred).

### Phase 1 (v1) — Minimum Viable Autonomous Loop

**Entry trigger:** approved design spec + writing-plans-generated implementation plan.

**Scope (what's in):**
- 6 employees: `ceo`, `opportunity-researcher`, `data-engineer`, `data-steward`, `compliance-officer`, `engineer`
- Stripe Payment Links (customized branding) + Gumroad listings via browser automation
- DM-only Telegram (new bot, founder + bot, no groups)
- CEO is sole comms layer
- File-based domain state in `state/`, Trinity memory in `.trinity/`
- Cron cycles at 13:00 ET (research) and 19:00 ET (CEO pipeline)
- One-time product format only

**Scope (what's out):**
- Custom subdomain storefront
- Recurring billing / memberships
- Marketing, partnerships, CFO, customer-success agents
- Multi-vertical specialized harvest tools
- Customer support inbox

**Success criteria (Phase 1 → Phase 2 trigger):**
- 14 consecutive days of daily 19:00 DMs delivered without founder intervention
- ≥ 1 product shipped end-to-end through the autonomous pipeline (smoke-test passing, live URLs)
- Zero compliance ledger REVOCATIONs (no retroactive ethics issues surfaced)
- ≤ 3 founder-required interventions in those 14 days (signal that minimal-gates is calibrated correctly, not too loose)

**Failure mode → revert:** if 14 days produces fewer than 7 daily DMs (system can't stay alive), the autonomy bet has not been proven and the design needs revisiting before adding more roles.

---

### Phase 2 — Productization Polish

**Entry trigger:** Phase 1 success criteria met.

**Scope (what's added):**
- `product-manager` agent — richer packaging logic beyond CEO drafting; A/B-test product format types (one-time vs membership vs SaaS) per niche
- `customer-success` agent — activates at first paid sale; handles onboarding email, day-3 check-in, refresh notifications, support inbox triage
- Custom subdomain storefront (Next.js page per product) on a chosen subdomain (e.g. `data.<owned-domain>`); engineer publishes to subdomain alongside Stripe + Gumroad
- Recurring-billing capability (one product converted to a $9-49/month membership with quarterly refresh cadence)
- Distribution queue consumer (early — CEO posts to one channel manually as preparation for `marketing-lead` in phase 3)

**Scope (what's still out):**
- Marketing-lead, partnerships-lead, CFO, SEO operator agents
- Multi-channel Telegram reporting
- Affiliate tracking
- Cross-vertical specialized harvest tools

**Success criteria (Phase 2 → Phase 3 trigger):**
- ≥ 3 products live (any combination of one-time + membership)
- ≥ 1 paying customer retained ≥ 30 days
- Custom subdomain serves all live products with green smoke tests for 14 consecutive days
- `customer-success` activates correctly on first paid checkout; ≥ 1 successful onboarding email sent

---

### Phase 3 — Distribution Sophistication

**Entry trigger:** Phase 2 success criteria met.

**Scope (what's added):**
- `marketing-lead` agent — channel selection, content drafting, automated posting (LinkedIn, X, Reddit, niche communities)
- `partnerships-lead` agent — affiliate recruitment via personalized outreach; affiliate-pipeline tracking
- `cfo` agent — daily metrics digest (MRR, refunds, anomalies); pricing-experiment proposals
- `seo-operator` agent — SEO-optimized product descriptions, blog content for organic capture
- Multi-channel Telegram reporting (separate channels for compliance flags, financial alerts, marketing reports — keeps DM-with-CEO clean while routing specialized output to topic-specific channels)
- Affiliate tracking with manual UTM links + Stripe metadata reconciliation

**Scope (what's still out):**
- Specialized per-vertical harvest tools (real-estate-specific, SaaS-specific, etc.)
- Self-improving feedback loops
- Multi-product parallel orchestration (CEO still serial in v3)

**Success criteria (Phase 3 → Phase 4 trigger):**
- ≥ 10 paying customers across all products
- Organic discovery measurable (≥ 20% of new customers from non-paid channels — SEO, affiliate, word-of-mouth)
- ≥ 1 active affiliate driving sales
- CFO daily digest delivered for 60 consecutive days

---

### Phase 4 — Scale

**Entry trigger:** Phase 3 success criteria met.

**Scope (what's added):**
- Vertical-specialized plugin tools (e.g., specialized harvest for real-estate permits, SaaS pricing pages, vendor compatibility matrices)
- Multi-product parallel CEO orchestration (multiple briefs advancing in the same cycle, with bounded concurrency)
- Self-improving feedback loops — production sales data feeds back into agent identities (e.g., compliance officer learns from past PASSes that produced no objections; researcher learns from products that actually sold)
- Memory system upgrades — automated cleanup of stale memories, better cross-cycle pattern detection
- Multi-workspace coordination (if a sister LoB launches, share Trinity memory selectively)

**Success criteria (Phase 4 ongoing):**
- ≥ $1K MRR
- ≥ 3 verticals with shipped products
- Multi-product parallelism stable for 30 days (no resource contention, no failure cascades)
- Founder time-to-DataStructured ≤ 30 min/week (if founder is spending more, autonomy regression — investigate)

---

## Roles roadmap (when each agent enters)

| Role | Phase | v1 substitute |
|---|---|---|
| ceo | 1 | — |
| opportunity-researcher | 1 | — |
| data-engineer | 1 | — |
| data-steward | 1 | — |
| compliance-officer | 1 | — |
| engineer | 1 | — |
| product-manager | 2 | CEO drafts product specs |
| customer-success | 2 | (no automation; activates with first paid sale) |
| marketing-lead | 3 | (no marketing in v1-v2; CEO can post manually if needed) |
| partnerships-lead | 3 | — |
| cfo | 3 | (CEO + Stripe dashboard manual check) |
| seo-operator | 3 | — |

---

## Open questions for future phases

These are deliberate unknowns left for future-decision rather than locked in now:

| Question | Phase to resolve |
|---|---|
| When does Trinity memory growth require automated cleanup? | Phase 4 (or earlier if memory size > 100 MB) |
| Stripe account namespace strategy when DataStructured products grow past 50 — split into a sub-account or stay flat with `dsl_` prefix? | Phase 3 |
| Custom domain (vs subdomain) for DataStructured brand — register dedicated, or stay under parent enterprise? | Phase 2 entry decision |
| Multi-bot Telegram setup (separate bots per channel) vs one bot with multiple chats — when does the latter break? | Phase 3 |
| Recurring-billing churn mitigation playbook — pause-not-cancel? annual prepay? | Phase 2 once first membership has data |
| When does the autonomy-vs-revenue priority flip? (Currently autonomy is primary; at some point revenue should become primary.) | Phase 3 — once revenue exists, founder reassesses |

---

## Non-goals

What this company will deliberately not become:

- A general-purpose AI agent platform — it's specifically a data-products company.
- A B2B sales-led ACV-driven business — it's bootstrapped self-serve digital products.
- A consumer brand — it's tools/data for buyers who already know they want what we sell.
- A content company (blog, newsletter, YouTube) — content may exist as marketing in phase 3, but the product is data, not content.
- A platform with many sellers — single owner / single brand.

---

## Operating philosophy

(These are not constraints — they're how the company should be run mentally, codified so future-founder doesn't drift.)

- **Autonomy beats polish in v1.** Working ugly trumps not-working pretty.
- **Demand-evidence-first, always.** Never build before we can quote three independent buyers asking for it.
- **One move per cycle.** The CEO that picks five things does none. The CEO that picks one ships.
- **Halt-and-surface beats best-effort.** When the agents are uncertain, halting and DMing the founder is cheaper than shipping a wrong thing.
- **Bootstrap discipline forever.** Even at $1K MRR, ask "do we need this paid tool?" before adding it. The whole bet is high-leverage low-cost.
- **The PRD is a living document.** Update it when reality contradicts it. Don't hide failures by editing the past.
