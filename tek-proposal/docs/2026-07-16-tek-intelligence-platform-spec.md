# TEK Restaurant Intelligence Platform

## Product Specification & Requirements Document (PRD)

| | |
|---|---|
| **Client** | TEK — Tasty E-Kitchen Ltd, London, UK (tekvers.ai) |
| **Prepared by** | Oghenetejiri Orukpe — OEFR Enterprise Inc (oefrenterprise.com) |
| **Date** | 19 July 2026 (v1.0: 16 July 2026) |
| **Version** | 2.0 — Revised all-inclusive proposal |
| **Status** | For client review |

---

## 1. Executive Summary

TEK positions itself as "the intelligence layer that powers the future of hospitality." This document specifies the buildout of the core platform that delivers that promise: a multi-tenant SaaS for independent restaurants and hospitality groups, built from scratch, comprising five integrated modules:

1. **First-party customer food-preference database** — TEK-owned capture surfaces that turn every guest interaction into structured preference data.
2. **AI meal recommendation engine** — personalised dish recommendations per guest, per venue, with human-readable reasoning.
3. **CRM with automated personalised marketing and loyalty programmes** — segmentation, automated campaigns (email/SMS), and a configurable loyalty engine.
4. **AI predictive analytics** — churn risk, demand forecasting, and menu-performance intelligence surfaced in a venue dashboard.
5. **TEK Guest mobile app** — iOS & Android app (single cross-platform codebase) bringing the menu, ordering, personalised recommendations, loyalty wallet and consent-gated push notifications to guests' phones.

The platform is delivered in five fixed-price phases, each independently valuable and demonstrable, quoted as a single **all-inclusive engagement** (Section 12).

**Out of scope for this engagement:** VR food visualisation/commerce and hardware/smart-kitchen infrastructure. The architecture leaves clean seams for both.

---

## 2. Background, Problem & Goals

### 2.1 Problem

Independent restaurants lose the retention game: the guest relationship is owned by aggregators and generic booking tools. Venues rarely know *who* their guests are, *what* they like, or *when* they are about to lapse. TEK's own market framing cites customer-retention struggles affecting 86% of hospitality businesses.

### 2.2 Product goals

- **G1** — Give every TEK venue a first-party, GDPR-compliant guest database it owns, populated automatically from TEK capture surfaces.
- **G2** — Convert that data into measurable revenue actions: recommendations that lift average order value, campaigns that lift visit frequency, loyalty that lifts retention.
- **G3** — Give operators forward-looking intelligence (churn, demand, menu performance) rather than backward-looking reports.
- **G4** — Support TEK's commercial model (Starter Intelligence at £249/venue/month; Enterprise custom) with per-venue multi-tenancy, seat management, and usage isolation from day one.

### 2.3 Success criteria (platform-level)

| Metric | Target (first 6 months post-launch) |
|---|---|
| Guest profiles captured per active venue | ≥ 500 |
| Guests with ≥ 3 preference signals | ≥ 60% of profiles |
| Recommendation click-through (QR menu) | ≥ 15% |
| Campaign-attributed repeat visits | measurable per campaign, ≥ 8% redemption |
| Churn-model precision @ top decile | ≥ 2× baseline repeat rate |
| Dashboard weekly active usage | ≥ 70% of paying venues |

---

## 3. Scope

### 3.1 In scope

- Multi-tenant SaaS core: organisations → venues → seats (role-based access), venue onboarding wizard.
- Guest-facing capture surfaces: QR web menu, web ordering page, signup/consent forms, post-visit feedback prompts, loyalty join flow.
- Customer food-preference database (Module 1) with a unified guest-event spine.
- AI meal recommendation engine (Module 2).
- CRM, campaign automation (email + SMS), and loyalty engine (Module 3).
- Predictive analytics: churn scoring, demand forecasting, menu-performance analytics (Module 4).
- Venue-facing business intelligence dashboard.
- GDPR/UK-DPA compliance tooling: consent records, export, right-to-erasure.
- TEK internal admin panel (tenant management, plan limits, platform health).
- TEK Guest mobile app for iOS & Android (Module 5) with push notifications.

### 3.2 Out of scope (this engagement)

- VR/3D food visualisation and VR commerce.
- Payments/ordering fulfilment beyond capture (no kitchen display, no delivery logistics).
- Multi-language localisation (English-first; i18n-ready string handling).
- Per-venue custom-branded mobile apps, offline mode, and in-app payment processing (the TEK Guest app ships under the TEK brand; venues appear within it).

### 3.3 Assumptions

- TEK supplies brand assets, domain(s), and legal copy (privacy policy, terms) — templates provided by OEFR.
- TEK supplies Apple Developer and Google Play accounts (and store listing approvals) for the mobile app; OEFR prepares builds and store assets.
- TEK operates the commercial relationships with venues; OEFR delivers the platform.
- Third-party service costs (hosting, email/SMS delivery, LLM API usage) are billed directly to TEK's accounts; estimates in Section 11.
- Pilot cohort of 3–10 venues available for Phase 2–3 validation.

---

## 4. Users & Personas

| Persona | Description | Primary needs |
|---|---|---|
| **Venue Owner/GM** | Runs 1–3 sites, time-poor | Retention, revenue lift, zero-admin tooling |
| **Marketing Manager** | Group/franchise level | Segments, campaigns, loyalty configuration, attribution |
| **Front-of-house staff** | Service staff | Guest preference card at a glance (allergies, favourites, VIP) |
| **Guest (diner)** | End customer | Fast menu/ordering, relevant recommendations, rewards worth joining, control over their data |
| **TEK Admin** | TEK's own team | Tenant provisioning, plan enforcement, platform health, model performance |

---

## 5. Module 1 — First-Party Customer Food-Preference Database

The foundation. Every other module reads from this.

### 5.1 Concept: the guest-event spine

All guest activity is written as immutable events against a guest profile: `menu_view`, `dish_view`, `order_placed`, `order_item`, `feedback_given`, `campaign_open`, `campaign_click`, `reward_redeemed`, `visit_checkin`, `preference_declared`. Preferences are **derived** (from behaviour) and **declared** (explicitly stated), kept distinct and both queryable.

### 5.2 Capture surfaces (v1, TEK-owned)

| Surface | Captures |
|---|---|
| QR web menu (per venue/table) | Menu/dish views, dwell, session device link |
| Web ordering page | Orders, items, modifiers, spend, time-of-day |
| Signup & loyalty join flow | Identity (email/phone), declared preferences, dietary needs, marketing consent |
| Post-visit feedback prompt (email/SMS link) | Dish ratings, visit rating, free-text comment |
| Staff quick-note (dashboard) | FOH-entered notes: allergies, occasions, VIP flags |

### 5.3 Guest profile

- Identity: email and/or mobile (E.164), name optional; anonymous sessions merge into a profile on identification (deterministic matching only).
- Declared: dietary requirements (vegan, halal, gluten-free, allergens list), cuisine likes/dislikes, spice tolerance, favourite dishes, occasions (birthday, anniversary).
- Derived: taste vector (per taxonomy tags), price-band affinity, visit cadence, channel preference, RFM scores (recency/frequency/monetary).
- Consent object: per-channel marketing consent with timestamped audit trail; profiling opt-out flag honoured by Modules 2–4.

### 5.4 Menu & taxonomy

- Venue menu manager: categories, dishes, prices, photos, availability windows.
- TEK food taxonomy: every dish tagged (cuisine, ingredients, allergens, spice level, dietary flags, preparation) — tags proposed automatically by LLM from the dish name/description, confirmed by the venue in onboarding.

### 5.5 Acceptance criteria (Module 1)

- A guest can scan a QR code, browse the venue menu, and their session events persist and merge into their profile after signup.
- A venue can view, search, filter, and export its guest list; guests are strictly invisible across tenants.
- A guest can request their data (export) and erasure; erasure completes across all modules within 30 days and is logged.
- Preference records distinguish declared vs derived, each with provenance and timestamps.

---

## 6. Module 2 — AI Meal Recommendation Engine

### 6.1 Behaviour

- **Known guest, on QR menu/ordering page:** "For you" rail of 3–6 dishes ranked by taste-vector match, order history, dietary constraints (hard filters), availability, and margin weighting (venue-configurable).
- **Unknown guest:** venue-level popularity + time-of-day priors (cold start), improving within the session from dish views.
- **Explanations:** each recommendation carries a short human-readable reason ("Because you loved the Jollof Special"), LLM-generated from structured signals — never invented facts.
- **Staff view:** FOH preference card shows the same top picks for table-side upsell.

### 6.2 Engine design

- Stage 1 (retrieval): hard constraint filtering — allergens, dietary flags, availability. **Allergen safety is absolute: a dish containing a declared allergen is never recommended, and the filter is enforced in code, not by the model.**
- Stage 2 (ranking): weighted hybrid — item-based collaborative filtering on order events + content similarity on taxonomy tags + recency/novelty terms. Deterministic, unit-testable scoring.
- Stage 3 (presentation): LLM formats explanation copy from the scoring evidence.
- Feedback loop: impressions and clicks logged as events; weekly offline evaluation (CTR, add-to-order rate) per venue.

### 6.3 Acceptance criteria (Module 2)

- Recommendations respond < 300 ms p95 (excluding explanation copy, which streams after).
- A guest with a declared allergen never sees a dish containing it (verified by automated test across full menu permutations).
- Venue can toggle margin weighting and see recommendation CTR in the dashboard.
- Cold-start venues get sensible popularity-based rails from day one.

---

## 7. Module 3 — CRM, Automated Marketing & Loyalty

### 7.1 CRM & segmentation

- Segment builder over profile + event data: attributes (dietary, preferences, RFM band, churn-risk band from Module 4), behaviours ("ordered ≥ 2× in 30 days", "viewed menu but didn't order"), and consent state (always enforced).
- Saved segments update dynamically; counts preview before sending.

### 7.2 Campaign automation

- Channels: **email + SMS** in v1 (Resend/Postmark for email, Twilio for SMS — final vendor choice at Phase 3 kickoff).
- Campaign types: one-off blasts, and **automations** triggered by events/conditions: welcome series, lapsed-guest win-back (churn-risk triggered), birthday/occasion, post-visit feedback ask, reward-earned notification.
- Personalisation: merge fields + AI-drafted copy variants per segment (venue approves before send; nothing auto-sends unreviewed copy in v1).
- Attribution: per-campaign UTM/short-link + redemption codes; dashboard reports opens, clicks, visits/orders attributed, revenue attributed.
- Compliance: per-channel consent enforced at send time; one-click unsubscribe; suppression lists; PECR-compliant sender identities.

### 7.3 Loyalty engine

- Configurable per venue (or shared across a group — TEK's multi-venue selling point): points per £ spent, visit stamps, or tiered (Bronze/Silver/Gold).
- Rewards: free item, tier perks, occasion bonuses. **No percentage-discount mechanics required for v1** — reward catalogue is value-add oriented.
- Guest experience: join in one step from any capture surface; balance visible on menu page; redemption via short code shown to staff (staff confirm in dashboard).
- AI assist: reward suggestions per segment based on preference data ("Top reward for your Friday regulars: free dessert — 68% of them order dessert").

### 7.4 Acceptance criteria (Module 3)

- A venue can create a segment, launch an automated win-back campaign, and see attributed redemptions end-to-end.
- Consent revocation stops all sends to that guest within minutes.
- A guest can join loyalty, earn on an order, see balance, and redeem in-venue with staff confirmation.
- Every send is logged (who, what, when, channel, consent basis).

---

## 8. Module 4 — AI Predictive Analytics

### 8.1 Capabilities

| Capability | Description | Method (v1) |
|---|---|---|
| **Churn risk** | Per-guest lapse probability, banded (healthy / cooling / at-risk / lost) | Gradient-boosted classifier on recency/frequency/monetary + engagement features; retrained weekly per tenant cohort |
| **Demand forecast** | Expected orders/covers by day and daypart, 14-day horizon | Time-series model (seasonality + trend + holiday calendar); per venue |
| **Menu performance** | Dish-level views→orders conversion, attach rate, margin contribution, rising/falling movers | Deterministic analytics over the event spine |
| **Preference trends** | Shifting taste-tag demand per venue ("vegan mains +22% this quarter") | Aggregated tag analytics with significance thresholds |

### 8.2 Dashboard

- Venue home: today's expected demand, at-risk guest count with one-click "send win-back", top movers on the menu, campaign performance summary.
- Weekly AI digest: plain-English summary of what changed and the single highest-impact suggested action (LLM-written from computed metrics only — every number in the digest traces to a stored metric).
- All predictions display confidence/coverage honestly; models degrade gracefully to heuristics when a venue has thin data, and the UI says so.

### 8.3 Acceptance criteria (Module 4)

- Churn bands populate for any venue with ≥ 90 days of data; backtest report generated per model version.
- Forecast accuracy tracked and displayed (MAPE vs actuals) — no unmeasured claims.
- Weekly digest delivered to venue owner by email; every figure reproducible from the dashboard.

---

## 8A. Module 5 — TEK Guest Mobile App (iOS & Android)

### 8A.1 Scope

Single cross-platform codebase (React Native/Expo) shipping to both stores under the TEK brand, consuming the same APIs as the web surfaces:

- **Venue entry:** scan a table QR or enter a venue code; recent venues remembered.
- **Menu & ordering:** full menu with allergen labels, dish detail, capture-only ordering — identical scope to the web ordering surface (§5.2).
- **For-you recommendations:** the Module 2 rail, with the same code-enforced allergen filtering.
- **Loyalty wallet:** balance/progress, reward catalogue, redemption short codes; join in one step.
- **Push notifications:** campaign and reward messages via a dedicated `push` consent channel (opt-in at first run, one-tap opt-out, enforced at send time exactly like email/SMS — Module 3's compliance rules apply unchanged).
- **Account & privacy:** profile, consent management, data export/erasure — parity with the web privacy hub (§5.3, Module 1 GDPR tooling).

### 8A.2 Acceptance criteria (Module 5)

- App approved and live on both the Apple App Store and Google Play under TEK's accounts.
- A guest can scan a venue QR from the app, order, join loyalty, and redeem — end-to-end parity with the web journey.
- Push messages deliver only to guests with explicit push consent; opt-out stops sends within minutes.
- All allergen and consent guarantees hold identically to the web surfaces (shared API enforcement, verified by the same test suites).

---

## 9. Architecture & Technical Design

### 9.1 Approach: modular monolith (approved)

One Next.js (App Router) application serving venue dashboard, guest capture surfaces, and API routes; PostgreSQL as the single source of truth with **row-level security keyed on tenant ID**; a Python worker service for ML jobs; LLM APIs for language tasks. Chosen over microservices (2–3× cost, unneeded at this scale) and third-party CRM assembly (per-contact fees destroy the £249/venue margin; TEK must own the intelligence layer).

```
Guests (QR menu / ordering / signup)     Venue staff (dashboard)      TEK admin
        │                                        │                        │
        ▼                                        ▼                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Next.js app (Vercel) — guest surfaces · dashboard · admin · API routes      │
└──────────────┬───────────────────────────────────────────────┬──────────────┘
               │                                               │
               ▼                                               ▼
     PostgreSQL (managed, RLS multi-tenant)          Job queue (Postgres-backed)
     profiles · events · menus · segments                      │
     campaigns · loyalty · predictions                         ▼
               ▲                                   Python ML worker (VM/container)
               │                                   churn · forecast · taxonomy
               └── LLM API (OpenAI) ── explanations · copy drafts · digests
     Email (Resend) · SMS (Twilio) · Object storage (dish photos)
```

### 9.2 Stack

| Layer | Choice | Rationale |
|---|---|---|
| Web/app/API | Next.js 15+, TypeScript, App Router | Matches TEK's advertised stack; one deploy target |
| Database | Managed PostgreSQL with RLS | Tenant isolation enforced at the database, not just app code |
| ML worker | Python 3.12 (scikit-learn, statsmodels/prophet-class), containerised | Right tool for churn/forecast; isolated from web path |
| Queue/jobs | Postgres-backed queue (e.g. pg-boss) | No extra infrastructure at this scale |
| LLM | OpenAI API (per TEK stack); provider-abstracted client | Explanations, copy drafts, taxonomy tagging, digests |
| Email / SMS | Resend or Postmark / Twilio | Deliverability + UK SMS compliance |
| Hosting | Vercel (app) + one small container host (worker) + managed Postgres | Minimal ops surface |
| Auth | Email/password + magic link; seat-based RBAC (Owner/Manager/Staff/TEK-Admin) | No social-login dependency |

### 9.3 Data model (core tables, abbreviated)

`organizations`, `venues`, `seats/users`, `guests`, `guest_identities`, `consents`, `events` (partitioned, append-only), `menus`, `dishes`, `dish_tags`, `preferences` (declared/derived, provenance), `segments`, `campaigns`, `sends`, `loyalty_programs`, `loyalty_accounts`, `loyalty_transactions`, `rewards`, `redemptions`, `predictions` (model, version, score, band, computed_at), `model_runs` (metrics, backtests).

### 9.4 Security & non-functional requirements

- **Tenant isolation:** Postgres RLS on every tenant-scoped table; cross-tenant access is a test-suite failure class of its own.
- **PII:** encrypted at rest (managed-DB level) and in transit; PII columns access-audited; secrets in environment config, never in code.
- **GDPR/UK DPA:** consent audit trail, subject access export (JSON/CSV), erasure workflow (hard-delete PII, pseudonymise events), data-processing register documentation handed to TEK.
- **Performance:** guest surfaces LCP < 2.5 s on 4G; recommendation API < 300 ms p95; dashboard queries < 1 s p95.
- **Availability:** target 99.9% on managed platforms; graceful degradation — if ML worker or LLM is down, menus/ordering/loyalty continue (recommendations fall back to popularity, digests skip a week).
- **Observability:** structured logs, error tracking (Sentry-class), per-tenant usage metering (supports TEK's plan enforcement).
- **Testing:** unit + integration suites per module; the allergen-filter and consent-enforcement paths get exhaustive automated tests; each phase ends with a UAT script executed with TEK.

---

## 10. Delivery Plan & Timeline

| Phase | Contents | Duration | Demo/exit criteria |
|---|---|---|---|
| **1 — Data Foundation** | Multi-tenant core, auth/RBAC, venue onboarding, menu manager + AI taxonomy tagging, QR menu + ordering + signup surfaces, guest profiles + event spine, GDPR tooling, TEK admin panel | 5 weeks | A pilot venue onboards itself, guests browse/order/sign up, profiles populate, erasure works |
| **2 — Intelligence** | Recommendation engine (all 3 stages), analytics dashboard, churn model, demand forecast, menu performance, weekly digest | 5 weeks | Live recommendations on the pilot venue's menu; churn bands + forecasts on real captured data; backtest reports |
| **3 — Activation** | Segment builder, campaign automation (email+SMS), attribution, loyalty engine + guest surfaces + staff redemption, AI copy/reward assist | 5 weeks | End-to-end: segment → automated campaign → attributed redemption; loyalty earn/redeem live |
| **4 — POS Integrations** | Square, Toast or Lightspeed connectors (2 in scope): historical import + ongoing order sync into the event spine | 4 weeks | Pilot venue's POS orders flow into profiles and retrain models |
| **5 — Mobile App** | TEK Guest app (iOS & Android): menu/ordering, recommendations, loyalty wallet, push notifications, privacy parity | 4 weeks (overlaps Phase 4) | App live in both stores; end-to-end guest journey passes on device |

Total programme (Phases 1–5): **~19 weeks** from kickoff (Phases 4 and 5 run in parallel). Each phase gates on written acceptance before the next begins.

---

## 11. Running Costs (TEK's accounts, estimates)

| Item | Est. monthly (pilot scale, ≤ 25 venues) |
|---|---|
| Hosting (Vercel Pro + worker host + managed Postgres) | £90–£180 |
| Email (per-send) | £15–£60 |
| SMS (Twilio UK, usage-based) | £0.04/msg — campaign dependent |
| LLM API | £30–£120 (explanations cached; copy drafts on demand) |
| Error tracking / monitoring | £0–£25 |

Per-venue infrastructure cost at pilot scale: **≈ £6–£15/month**, comfortably inside the £249/venue price point.

---

## 12. Commercial Terms — Agreed All-Inclusive Engagement

Terms agreed between TEK and OEFR Enterprise Inc in direct negotiation, superseding the v1.0 two-track quotation (OEFR-PF-2026-001/-002). One fixed price covers the complete programme — all five phases, nothing optional:

| Phase | Fixed Price |
|---|---|
| 1 — Data Foundation | £4,999 |
| 2 — Intelligence | £4,800 |
| 3 — Activation | £4,000 |
| 4 — POS Integrations (2 connectors) | £2,500 |
| 5 — Mobile App (iOS & Android) | £2,500 |
| **Programme total (all-inclusive)** | **£18,799** |

Delivery wrap: solo senior delivery, AI-accelerated; 30-day post-phase defect warranty; async support (48 h response); essential documentation (admin guide + API reference); dedicated staging environment with seeded demo tenant (already live for TEK review).

### Ongoing operations (optional, post-launch)

| Plan | Scope | Monthly |
|---|---|---|
| Ops Essential | Monitoring, patching, model retraining oversight, 8 h/month improvements | £1,500 |
| Ops Growth | Essential + 24 h/month feature development, campaign/model tuning, monthly performance report | £3,500 |

### Payment terms

- **40% to commence (£7,519), 60% on final written acceptance (£11,280)** of the Phase 5 exit criteria.
- Prices exclude VAT (if applicable) and third-party running costs (Section 11, plus app store developer fees on TEK's accounts).
- Terms valid 30 days from the date of this document.
- Scope changes handled by written change order against a day rate agreed at signature.

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Thin data at pilot venues weakens models | Heuristic fallbacks shipped first; models activate at data thresholds; honest confidence display |
| Email/SMS deliverability | Dedicated sending domains, warm-up plan, suppression hygiene from day one |
| Allergen/dietary errors | Hard-coded constraint filtering (never model-decided), exhaustive automated tests, venue confirmation step on taxonomy |
| GDPR exposure | Consent-first design, erasure workflow tested in UAT, processing register delivered |
| Scope drift from TEK's broader vision (VR, hardware) | Fixed per-phase scope with written acceptance gates; change-order process |
| LLM cost/latency | Explanations cached per (guest-segment × dish); language tasks off the critical path |

---

## 14. Acceptance & Next Steps

1. TEK confirms written acceptance of this document and the agreed terms (pro forma invoice OEFR-PF-2026-003).
2. Statement of Work + commencement invoice issued; kickoff within 5 business days of deposit.
3. Weekly written progress reports; phase demos on the shared staging environment (already live).

*Prepared by OEFR Enterprise Inc · oefrenterprise.com · Contact: Oghenetejiri Orukpe*
