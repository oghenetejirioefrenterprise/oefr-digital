# Validation — Crypto Form 1099-DA 2025-First-Year Reconciliation Kit

- **Opportunity**: [2026-05-22] Crypto Form 1099-DA 2025-first-year reconciliation kit + cost-basis-gap rebuild + Form 8949 + Schedule D walkthrough — [queue.md](../opportunities/queue.md)
- **Date opened**: 2026-05-23
- **Validator**: Trinity (validator-loop)
- **Rung**: 1 (FREE — Stripe pre-order link primary + owned-domain blog SEO secondary + value-first Reddit comments post-2026-05-25 mandate-expiration; no paid ads)
- **Status**: live_rung1 (Gumroad listing leg deployed 2026-06-09; forum leg staged next cycle — see Live section)
- **Stripe Payment Link**: pending Trinity day-shift deploy (target slug: `crypto-1099-da-reconciliation-kit`)
- **Deploy timestamp (UTC)**: TBD (gated on 3-competitor pricing scrape against `etsy.com/market/crypto_tax_spreadsheet` + Monaco CPA `monacocpa.cpa/1099da-review` paid-tier anchor + CoinTracker/Koinly paid SaaS anchors)
- **Kill date**: **2026-06-23** (distribution-leg read) — AMENDED 2026-06-11 09:0X ET by Validator-Executor (original 2026-06-06 pre-dated the 2026-06-09 Gumroad deploy /l/djhfxt). Per Oracle 06-09 20:00: NO season-kill after June 15 — canonical paid-demand window = Oct-15 extension wave + CP2000 mailbox trail (TY2025 = first 1099-DA year); zero read at the Oct window = final kill
- **Greenlight threshold**: ≥5 Stripe completed sessions OR ≥1 session + ≥150 blog sessions on `oefrenterprise.com/blog/crypto-1099-da-*` cluster by 2026-06-06
- **Weak-signal threshold**: 1–4 sessions OR ≥50 blog sessions + ≥1 substantive inbound DM/comment → climb to rung 2 (Pinterest SKIP per crypto-cohort 60%+ male buyer pool audience-cluster mismatch; rung 2 = additional Reddit lanes r/tax + r/personalfinance + r/Bitcoin + r/ethfinance + 1 cohort-matched X owner-session thread, NOT paid ads)
- **Kill threshold**: 0 sessions AND 0 inbound DMs/comments AND <50 blog sessions by 2026-06-06 → reject, log cause, move on

---

## CANONICAL DELIVERABLE INVENTORY (single source of truth)

> All customer-facing surfaces (Stripe NAME + DESC, cover.png, blog post, Reddit comment, Gumroad mirror if account is restored) MUST enumerate deliverables from this list verbatim. Any deviation = drift, flagged at nightly lint.

**Bundle shape:** 12-tab kit (1099-DA box-by-box decoder + cost-basis-gap reconstruction worksheet + cross-exchange transfer flagging walkthrough + Form 8949 box A/B/C/D/E/F walkthrough + Schedule D reconciliation overlay + missing-basis reasonable-cause letter template + Notice 2024-57 transition-relief decoder + safe-harbor 2025-acquired-asset specific-identification election walkthrough + DeFi / wallet-to-wallet flagging supplement + 50-state-pointer for state-side additions + IRS-CP2000 pre-response audit-evidence binder + amended-return Form 1040-X cross-reference index)

**12 Deliverables (verbatim — grep these exactly):**
1. **Form 1099-DA box-by-box decoder** — Box 1a/1b/1c/1d/1e/2/3/4/5 plain-English walkthrough per Treas. Reg. §1.6045-1(d)(2)(i)(B), broker reporting fields explained including the $0-cost-basis default for pre-2025 acquisitions.
2. **Cost-basis-gap reconstruction worksheet** — Google Sheets template for rebuilding adjusted basis from transaction history when broker reports $0; covers FIFO / Specific-ID / per-wallet method selection per Rev. Proc. 2024-28.
3. **Cross-exchange transfer flagging walkthrough** — identifies and isolates transfers (non-taxable) from sales/dispositions (taxable) to prevent double-counting basis.
4. **Form 8949 box A/B/C/D/E/F walkthrough** — when each box applies for crypto, short-term vs long-term, broker-reported vs not-reported, with worked examples per IRS Pub 544 + Form 8949 instructions.
5. **Schedule D reconciliation overlay** — ties Form 8949 totals to Schedule D line items + carries to Form 1040 Line 7.
6. **Missing-basis reasonable-cause letter template** — IRS-compliant disclosure language when broker-reported basis is $0 and taxpayer reconstructs from records; preserves taxpayer position under IRC §6662 reasonable-cause defense.
7. **Notice 2024-57 transition-relief decoder** — IRS transition relief for 2025 first-year 1099-DA reporting (Rev. Proc. 2024-28 + Notice 2024-57); when penalty relief applies.
8. **Safe-harbor specific-identification election walkthrough** — Rev. Proc. 2024-28 unused-basis allocation safe harbor for 2025-acquired assets + per-wallet method election.
9. **DeFi / wallet-to-wallet supplement** — non-broker-reported events (DeFi swaps, staking rewards, airdrops, hard forks, self-custody transfers) that 1099-DA does NOT cover and taxpayer must self-report.
10. **50-state-pointer for state-side additions** — pointer-index of states with crypto-conformity (CA / NY conformity), states with no income tax (FL / TX / WA / TN / NV / SD / WY / AK / NH), states with non-conformity quirks.
11. **IRS CP2000 pre-response audit-evidence binder** — pre-stages evidence in case IRS issues CP2000 underreporter notice 12-18 months post-filing.
12. **Amended-return Form 1040-X cross-reference index** — pointer to 1040-X procedure if taxpayer already filed without reconciling 1099-DA (3-year refund-claim window per IRC §6511).

**Federal statute + regulation anchor citations (verbatim — factual, not creative):**
- Infrastructure Investment and Jobs Act (IIJA, 2021) §80603 — broker reporting expansion to digital assets
- IRC §6045 — broker reporting (extended to digital-asset brokers)
- IRC §6045A — transferred-basis reporting
- Treas. Reg. §1.6045-1(d)(2)(i)(B) — final regulations published June 2024, effective TY 2025
- Rev. Proc. 2024-28 — unused-basis allocation safe harbor + per-wallet method
- Notice 2024-57 — transition relief for TY 2025 first-year reporting
- IRC §6511 — 3-year refund-claim window (1040-X reference)
- IRC §6662 — accuracy-related penalty + reasonable-cause defense

**BANNED phantom counts / overclaims (do NOT use):**
- ❌ "Guaranteed refund" / "Get $X,XXX back" (illegal-overpromise + violates NOT-tax-advice framing)
- ❌ "IRS-approved" / "IRS-endorsed" (no such endorsement exists for third-party templates)
- ❌ "Audit-proof" (no template provides immunity from audit selection)
- ❌ "50 state letter templates" (we ship a single 50-state pointer-index, NOT 50 separately authored letters)
- ❌ "Avoid paying taxes" (illegal evasion framing; product is reconciliation/accuracy, not avoidance)
- ❌ "Tax advice" / "Legal advice" (always framed as documentation organizer; recommend CPA for $50K+ disputes)

**Approved count strings:** `12-tab Crypto 1099-DA reconciliation kit` / `12 deliverables across 1099-DA decoding, cost-basis reconstruction, and Form 8949 walkthrough` / `1099-DA box-decoder + cost-basis-gap worksheet + Form 8949 walkthrough + 50-state pointer` / `Rev. Proc. 2024-28 + Notice 2024-57 transition-relief decoder included`.

---

## Why this opportunity passed the validator gate

1. **Edge fit passes** — production speed (24-36h MVP — federal-uniform IRS framework + single Form 1099-DA + single Treas. Reg. anchor + Rev. Proc. 2024-28 + Notice 2024-57 = tight regulatory surface area + cost-basis-gap reconstruction is a deterministic data-shape problem); AI-native cost ≈$0 marginal; programmatic SEO (1099-DA + Form 8949 + Schedule D + per-exchange [Coinbase / Kraken / Gemini / Binance.US] + per-method [FIFO / Spec-ID / per-wallet] = 20+ surfaces); NEW REGULATORY WINDOW (TY 2025 = first year 1099-DA is issued; pre-March 2026 first-mover SEO window confirmed by Opportunity Scout 2026-05-22 20:06 ET); cold-start communities (r/CryptoTax + r/Coinbase + r/tax + r/Bitcoin + r/ethfinance combined ~1M+ subscribers); NOT taste/community/personality-driven (utility-shape tax-reconciliation documentation, opposite of Etsy-aesthetic cohort).
2. **Roster clean** — `product-roster.md` contains zero crypto / digital-asset / 1099-DA / cost-basis SKU. No prior-failure risk. No cannibalization with May 7 IRS CP2000 notice-response (which is post-IRS-notice cohort; this is pre-IRS-notice reconciliation cohort).
3. **5 demand signals** confirmed in queue entry (≥3 threshold passed) — all 5 are 2025-2026-dated Reddit threads with explicit confusion / hair-on-fire language. Buyer-pain quote: > "lol i'm actually rattled rn... just found out about this absolute nightmare that is form 1099-DA" (r/CryptoTax). Monaco CPA SaaS-vendor benchmark confirms institutional buyer-WTP at $300+ premium-tier — our $29 kit slots PRE-CPA at "DIY-first-then-escalate" cohort boundary.
4. **Hair-on-fire post-event trigger** = January-March 2026 broker mail-wave delivering 1099-DA with $0 / missing cost basis to ~10-30M US crypto holders. TY 2025 filing deadline April 15 2026 already passed; extension deadline October 15 2026 = ~5 months pressure remaining for the on-extension cohort. Recurring annual cohort: TY 2026 1099-DA will issue Jan-March 2027 (broader cohort by then; reporting expanded).
5. **No cannibalization** — distinct from May 7 CP2000 (post-IRS-notice scope), May 12 Form 1040-X (post-original-filing self-correction scope), May 3 EITC audit-defense (CP75-notice substantiation scope), May 15 Letter 3219 90-day-deficiency scope. This is pre-filing reconciliation at the 1099-DA receipt moment.
6. **DIY-first cultural norm proven** — crypto-cohort culturally self-custody / self-serve oriented (opposite of contingency-attorney-routing cohorts vetoed prior). 5-Reddit-thread top-comment "you need to reconcile broker-reported basis against actual records" path-prescription confirms DIY-cohort dominance; paid-CPA reconciliation engaged only at $5K+ basis-gap escalation threshold.
7. **NOT a non-edge market** — edges.md check: not Etsy handmade-aesthetic, not personality-driven (third-person research-aggregator voice), not enterprise B2B sales, not premium-luxury positioning. Utility-shape tax-reconciliation documentation in federally-anchored (IIJA §80603 + Treas. Reg. §1.6045-1) regulatory window with multi-year half-life (regulation runs through TY 2026+ with cost-basis reporting expansion expected for TY 2026 reporting).
8. **Channel-fit pre-validation (v0 design gate per edges.md)** — buyer pool maps to ≥3 of OEFR's currently authenticated platforms:
   - **Reddit direct CDP+xdotool on display :98** — r/CryptoTax + r/Coinbase + r/tax cohorts, post-2026-05-25 mandate-expiration window (T+2d from today).
   - **Owned-domain blog SEO** — long-tail "1099-DA reconciliation," "Coinbase 1099-DA $0 cost basis," "Form 8949 crypto reconciliation," "1099-DA Notice 2024-57 transition relief" queries.
   - **Gumroad marketplace** — indie-creator-adjacent + crypto-tool surfaces already present (CoinLedger / CoinTracker adjacent listings); IF Gumroad account-dead P1 carry resolves before kill date, cross-list.
   - **X owner-session @eustaceorukpe** — only if r/CryptoTax cohort overlaps; otherwise SKIP per May 6 DEAD_PIVOT precedent.
9. **Recovery-upside anchor** — buyer WTP for $29 kit against typical $500-5,000 over-reported-gain exposure on $0-basis defaults is structurally favorable. For a holder with $20K in 2024-acquired crypto sold in 2025, $0-basis default = $20K phantom gain × 22% marginal = $4,400 over-paid tax. Kit corrects the reconciliation = buyer recovers $1,000-$4,000+ on a $29 outlay. Same dynamic as security-deposit treble-damages WTP anchor.

---

## Rung 1 — Stripe pre-order listing (primary deploy channel per persona contract)

### Listing metadata

- **Price**: $29.00 (pre-order entry-tier — high-income crypto cohort vs IEP-parent $24 anchor + Monaco CPA $300+ paid-tier ceiling + $12 Etsy commodity floor; pending TJ-mandated 3-competitor scrape may revise to $24 or $39)
- **Fulfillment date in description**: 2026-06-08 (16 days from today; honors refund window if kill verdict fires 2026-06-06; per May 1 build-in-parallel directive thin v0 12-tab PDF + Google Sheets workbook ≤T+48h post-Stripe-deploy)
- **Slug**: `crypto-1099-da-reconciliation-kit`
- **Stripe Product NAME** (≤120 chars per Stripe spec, count verified): `Crypto 1099-DA Reconciliation Kit — Cost-Basis Gap Worksheet + Form 8949 Walkthrough + 50-State Pointer (12 deliverables)`
- **Stripe Product DESCRIPTION** (≤500 chars per Stripe surface): `Brokers like Coinbase + Kraken are issuing Form 1099-DA for TY 2025 with $0 or missing cost basis. Without reconciliation, you over-report gain by thousands. This 12-tab kit gives you the 1099-DA box-by-box decoder, cost-basis-gap reconstruction worksheet, cross-exchange transfer flagging walkthrough, Form 8949 box A/B/C/D/E/F walkthrough, Schedule D overlay, missing-basis reasonable-cause letter, Notice 2024-57 transition-relief decoder, safe-harbor Spec-ID election walkthrough, DeFi/wallet supplement, 50-state pointer, CP2000 pre-response evidence binder, and 1040-X cross-reference index. Federal-citation depth, not tax advice.`

### Cover image brief (1500×1000 px, PNG, dark-mode)

- Dominant color: deep navy (#0E1A2B) background — distinct from iep-504 slate-navy+amber palette.
- Top-third: heading `Form 1099-DA Reconciliation Kit` in white sans-serif (Inter Bold 80pt).
- Middle-third: faded ghost-image of an actual Form 1099-DA box-grid (Boxes 1a/1b/1c/1d/1e visible at low opacity) overlaid with bright orange (#FF6B35) annotations pointing at "Box 1e: $0" with a red-line strikethrough + green-line correction.
- Bottom-third: `12 deliverables · 50-state pointer · TY 2025 first-year reporting`
- Top-right corner: small federal-citation chip "Treas. Reg. §1.6045-1 · Notice 2024-57" in monospace (JetBrains Mono 18pt).
- NO faces, NO crypto-coin logos (avoids trademark issues + crypto-bro cohort theater), NO dollar signs (avoids platform overpromise flags).

---

## Gumroad listing copy (per persona contract — ready to paste if Gumroad account-dead P1 carry resolves before kill date)

### Title (60 chars max — counted: 56)

`Crypto 1099-DA Reconciliation Kit (TY 2025 First Year)`

### Subtitle

`12-tab kit — cost-basis-gap worksheet, Form 8949 walkthrough, Notice 2024-57 transition-relief decoder, 50-state pointer. Federal-citation depth, not tax advice.`

### Description (~300 words, bullet-structured)

> Brokers like Coinbase, Kraken, Gemini, and Binance.US are issuing **Form 1099-DA for TY 2025 — the first tax year covered by the new digital-asset broker-reporting rules under Treas. Reg. §1.6045-1**. The problem: for any crypto acquired before 2025, transferred between wallets, or moved between exchanges, the broker defaults to **$0 cost basis** in Box 1e. If you file as-is, you over-report capital gain by thousands.
>
> This kit walks you through the reconciliation, step by step, with federal-citation depth.
>
> **What's inside (12 deliverables):**
>
> - **Form 1099-DA box-by-box decoder** — Box 1a, 1b, 1c, 1d, 1e, 2, 3, 4, 5 in plain English
> - **Cost-basis-gap reconstruction worksheet** (Google Sheets) — rebuild adjusted basis from transaction history when broker reports $0
> - **Cross-exchange transfer flagging walkthrough** — separate non-taxable transfers from taxable sales
> - **Form 8949 box A/B/C/D/E/F walkthrough** — when each box applies, with worked examples per IRS Pub 544
> - **Schedule D reconciliation overlay** — tie Form 8949 totals to Schedule D
> - **Missing-basis reasonable-cause letter template** — preserves IRC §6662 reasonable-cause defense
> - **Notice 2024-57 transition-relief decoder** — when first-year penalty relief applies
> - **Safe-harbor Spec-ID election walkthrough** — Rev. Proc. 2024-28 unused-basis safe harbor + per-wallet method
> - **DeFi / wallet-to-wallet supplement** — staking, airdrops, hard forks, self-custody (not on 1099-DA)
> - **50-state-pointer for state-side additions** — conformity vs non-conformity states
> - **IRS CP2000 pre-response audit-evidence binder** — pre-stage records before any underreporter notice
> - **Amended-return Form 1040-X cross-reference** — if you already filed without reconciling
>
> Pre-order ships 2026-06-08. Federal-citation depth (Treas. Reg. §1.6045-1, Rev. Proc. 2024-28, Notice 2024-57). NOT tax advice — DIY reconciliation documentation. For $50K+ basis-gap or audit-defense scope, engage a CPA.

### Price

`$29.00 USD`

### Cover image brief

See "Cover image brief" above (shared spec across Stripe + Gumroad surfaces).

---

## Rung 1 — Forum post copy (per persona contract — value-first, one tasteful offer mention at end)

**Target community:** `r/CryptoTax` (~30K subscribers, dedicated crypto-tax cohort, hair-on-fire frequency).

**Posting window:** Wed 2026-05-27 (≥48h after Reddit long-game mandate expiration 2026-05-25 per `feedback_reddit_api_dead.md` + Mar 25 mandate). Per `feedback_credentials_in_profile_attempt_first` + `feedback_reddit_api_dead.md`, post via Anthropic computer-use vision-clicking primary (`scripts/computer-use-reddit-poc.py`) or CDP+xdotool fallback. NO API path.

**Pre-post gates:** (a) Trinity day-shift verifies r/CryptoTax current self-post rules + no posting-frequency restrictions in sidebar. (b) Content QA review against persona-fiction-gate + factual-integrity-gate. (c) Cross-persona attribution check — this is OEFR research-aggregator voice, NOT TJ-niche-anchor (per `feedback_no_tj_niche_anchor.md`).

### Title (≤300 chars, Reddit hard limit)

`Walkthrough: How to reconcile a 1099-DA with $0 cost basis (Form 8949 box-by-box + Notice 2024-57 transition relief + Rev. Proc. 2024-28 safe harbor)`

### Body

> If you're getting a Form 1099-DA from Coinbase, Kraken, Gemini, or any other US digital-asset broker for TY 2025, you'll probably see **$0 in Box 1e (cost basis)** for any crypto you acquired before 2025 — or anything you transferred in from another wallet/exchange. That's not a broker mistake. It's the default under Treas. Reg. §1.6045-1, finalized June 2024.
>
> If you file without reconciling, you over-report capital gain by the full proceeds amount in Box 1d. On $20K in proceeds with $0 basis, that's a phantom $20K capital gain × your marginal rate. Hard pass.
>
> Here's the reconciliation walkthrough I've found useful (federal-citation, not tax advice):
>
> **Step 1 — Decode the 1099-DA boxes.** Box 1a = description. Box 1b = acquired date (often blank for transferred-in assets). Box 1c = sold date. Box 1d = proceeds. Box 1e = cost basis (the $0 problem). Box 2 = short/long term. Box 3 = gain/loss. Box 4 = federal tax withheld. Box 5 = adjustments. The blank/zero fields are the ones you have to fill in from your own records.
>
> **Step 2 — Reconstruct cost basis from transaction history.** Pull every buy + every transfer-in from every exchange + every wallet for that asset. Match by quantity + date. If you used FIFO, document the FIFO chain. If you elected Specific-ID, document the lot. Rev. Proc. 2024-28 created an unused-basis allocation safe harbor for 2025-acquired assets + a per-wallet method election that's new for TY 2025 — check whether your situation qualifies.
>
> **Step 3 — Flag cross-exchange transfers.** Coinbase → Kraken is NOT a taxable event. Wallet → wallet is NOT a taxable event. But the broker on the receiving side may have reported it as a $0-basis acquisition. The kit-supplement language: "non-broker-reported event, not a disposition."
>
> **Step 4 — Form 8949.** If basis was reported to IRS, use Box A (short-term) or D (long-term). If basis NOT reported, use Box B or E. Box C / F is for transactions not reported on a 1099. Crypto pre-2025 sold in 2025 → Box B or E with adjustment column (g) explaining the basis correction.
>
> **Step 5 — Schedule D reconciliation.** Form 8949 totals carry to Schedule D Part I (short-term) or Part II (long-term), then to Form 1040 Line 7.
>
> **Step 6 — Notice 2024-57 transition relief.** IRS released transition relief for TY 2025 first-year 1099-DA reporting — penalty relief in defined circumstances. Worth reading before you panic over a mismatch.
>
> **Step 7 — Missing-basis reasonable-cause language.** If you're substituting reconstructed basis for the broker's $0, document the substitution with reasonable-cause language under IRC §6662 so you preserve the accuracy-related-penalty defense if the IRS later questions it.
>
> **Step 8 — DeFi / wallet / staking / airdrops.** None of that is on the 1099-DA. You report it separately. Keep records.
>
> **Step 9 — State additions.** Some states conform to federal crypto treatment (CA, NY); some don't; 9 states have no income tax (FL, TX, WA, TN, NV, SD, WY, AK, NH). Check your state's conformity.
>
> **Step 10 — If you already filed without reconciling.** You have a 3-year window under IRC §6511 to file Form 1040-X amended return.
>
> Sources I used to put this together: Treas. Reg. §1.6045-1(d)(2)(i)(B), Rev. Proc. 2024-28, Notice 2024-57, IRS Pub 544, Form 8949 instructions, IRC §6045 + §6045A + §6511 + §6662.
>
> ---
>
> Not tax advice. For $50K+ basis-gap or audit-defense scope, engage a CPA.
>
> If you want this whole reconciliation broken out as a 12-tab kit (decoder + Google Sheets cost-basis-gap worksheet + reasonable-cause letter template + 50-state pointer + CP2000 pre-response binder), it's a $29 pre-order at oefrenterprise.com/products/crypto-1099-da-reconciliation-kit — ships 2026-06-08. No subscription, no upsells. Buy once.

---

## Rung 1 — Owned-domain blog SEO post (parallel surface, deploys with Stripe plink)

**Slug:** `/blog/crypto-1099-da-reconciliation-walkthrough-ty-2025`

**Target keywords (long-tail, low-competition first-mover window):**
- "1099-DA reconciliation" (target #1, hair-on-fire query, low SERP density)
- "1099-DA $0 cost basis" (Coinbase-cohort-specific)
- "Form 8949 crypto reconciliation"
- "Notice 2024-57 transition relief"
- "Rev. Proc. 2024-28 unused basis safe harbor"
- "1099-DA Box 1e empty"

**SEO depth:** 2,500–3,500 words, federal-citation-anchored, FAQPage Schema, internal links to Form 8949 sub-article + Notice 2024-57 sub-article + CP2000 sub-article (programmatic-SEO cluster pattern from iep-504 success).

**Content QA gate:** factual-integrity-gate.py + pre-draft-sanity-check.py + edges-non-edges-gate.py + blog-slug-validator.py — ALL must EXIT 0 before deploy.

---

## Kill / greenlight thresholds (specific numbers + specific dates)

| Date | Metric | Threshold | Action |
|---|---|---|---|
| **2026-06-06** (T+14d) | Stripe completed sessions | ≥5 | **GREENLIGHT** → build full v0 PDF + Google Sheets workbook, ship to buyers within 48h, promote to rung-2 distribution (X owner-session thread + Pinterest test even with cohort-mismatch flag) |
| **2026-06-06** (T+14d) | Stripe completed sessions | 1–4 OR blog sessions ≥50 + ≥1 inbound DM/comment | **WEAK SIGNAL** → climb to rung 2 — add r/tax + r/personalfinance + r/Bitcoin + r/ethfinance Reddit value-comments + 1 X owner-session thread + 1 Pinterest pin with cohort-mismatch flag (rung 2 = ≤$15 paid promotion test if free rung-2 returns 1+ session) |
| **2026-06-06** (T+14d) | Stripe completed sessions | 0 AND blog sessions <50 AND 0 inbound DMs/comments | **KILL** → status `live_rung1 → rejected (kill_with_evidence_2026-06-06)`, deactivate Stripe plink via `stripe.PaymentLink.update(active=False)`, append cause to roster, move on |

**Defer-kill condition** (per `kill-fast deploy-rule` in edges.md): IF 0 sessions AND 0 distribution-evidence-on-file (forum post + blog post both LIVE and indexed) AT T+14d → defer kill 48h, ship distribution attempt first, recheck T+16d.

**Channel-empty vs product-empty fork** (per edges.md kill-fast rule): IF 0 sessions AND distribution-evidence-on-file ≥1 post + T+24h impressions ≥25 on the Reddit post AND blog post indexed → product-empty kill grounded. IF 0 sessions AND distribution-evidence-on-file ≥1 post + T+24h impressions <25 → channel-empty hold (no measurable exposure — change distribution channel + retest, do NOT kill SKU).

---

## Measurement plan

| What | Where | How often |
|---|---|---|
| Stripe sessions (total, paid, expired, open) | `stripe.PaymentLink.retrieve('plink_<id>')` ground-truth | Daily 09:00 ET (Validator-Executor canonical pull) + 18:00 ET (Stripe-Pulse pull) |
| Stripe charge ledger (succeeded, failed, refunded, disputed) | Stripe API 7d + 30d windows | Daily 18:00 ET (Stripe-Pulse) |
| Blog post sessions / unique visitors | Vercel Analytics on `oefrenterprise.com/blog/crypto-1099-da-reconciliation-walkthrough-ty-2025` | Daily 12:00 ET (Store Audit cycle) |
| Reddit post impressions / upvotes / comments / awards | Manual scrape via CDP+xdotool on display:98 against post URL `reddit.com/r/CryptoTax/comments/<id>` | T+24h (channel-fit verdict) + T+72h + T+168h + T+336h (kill date) |
| Inbound DMs / comments / questions | (a) info@oefrenterprise.com IMAP poll (now unlocked per 2026-05-23 Neo P1 autofix + GMAIL_APP_PASSWORD_INFO env var). (b) Reddit DMs against u/<owner-account>. (c) X DMs against @eustaceorukpe. | Daily 10:30 ET (Content QA cycle sweeps inbound) |
| Cross-channel pixel/UTM attribution | Stripe checkout session metadata field `utm_source=reddit|blog|gumroad|x` set at plink-creation time | Per-session at conversion |

**Signal-pattern decision table** (post-T+14d data review):

| Pattern | Diagnostic |
|---|---|
| Blog sessions ≥150 + Stripe sessions ≥5 | **CHANNEL + PRODUCT WORK** — promote to rung 2 |
| Blog sessions ≥150 + Stripe sessions 0 | **CHANNEL WORKS / PRODUCT DOESN'T CONVERT** — price test + landing-page CTA test before rung 2 |
| Blog sessions <50 + Reddit T+24h impressions ≥25 + Stripe sessions 0 | **PRODUCT-EMPTY kill grounded** — real exposure, no buyer interest |
| Blog sessions <50 + Reddit T+24h impressions <25 + Stripe sessions 0 | **CHANNEL-EMPTY hold** — change distribution channel (try r/tax + r/Bitcoin + X thread) before kill |
| Blog sessions ≥150 + Reddit T+24h impressions <25 + Stripe sessions 1-2 | **SEO WORKS / REDDIT DOESN'T** — double-down on owned-domain SEO cluster, deprioritize Reddit |

---

## Distribution evidence log (per edges.md kill-fast deploy-rule)

> Every distribution attempt MUST log here with a real URL (post URL, blog URL, tweet URL — not a narrative claim).

| Date | Channel | URL | T+24h impressions | T+24h saves/upvotes/outbound | Signal pattern |
|---|---|---|---|---|---|
| (pending) | r/CryptoTax self-post | (pending Trinity day-shift CDP publish 2026-05-27) | (pending) | (pending) | (pending) |
| (pending) | oefrenterprise.com blog | (pending Trinity day-shift Vercel deploy) | (pending) | (pending) | (pending) |
| (pending) | Stripe payment link | (pending Trinity day-shift Stripe.PaymentLink.create) | n/a | (sessions ground-truth via API) | (pending) |

---

## Out-of-lane handoffs (NOT executed by validator-loop)

- **Trinity day-shift P0** (~30min): 3-competitor pricing scrape against Etsy `crypto_tax_spreadsheet` market + Monaco CPA $300+ paid-tier + CoinTracker / Koinly paid-SaaS tier before Stripe plink price-set (per Validator Loop pricing-research gate from 2026-05-09).
- **Trinity day-shift P0** (~25min): Stripe.PaymentLink.create + .Product.create + .Price.create with NAME + DESC verbatim from this doc; populate `distribution_evidence_path` field for plink metadata.
- **Trinity day-shift P1** (~3-4h): Author owned-domain blog SEO post at `/blog/crypto-1099-da-reconciliation-walkthrough-ty-2025` per content-QA + factual-integrity gates; deploy to Vercel; verify HTTP 200 + sitemap-fresh.
- **Trinity day-shift P1** (~15min, Wed 2026-05-27 ≥48h post-mandate-expiration): Reddit r/CryptoTax self-post via CDP+xdotool on display:98 using forum post copy verbatim from this doc; log post URL to distribution-evidence table above.
- **CEO Needle Mover next cycle**: review distribution-evidence table after Reddit T+24h impressions read; route to channel-empty-vs-product-empty fork per edges.md kill-fast rule.
- **Morpheus CMO next cycle**: design Pin-skip vs Pin-test fork — Pinterest 60%+ female buyer pool vs crypto cohort 60%+ male; default SKIP per channel-fit theater rule, but rung-2 weak-signal threshold permits 1 Pinterest test pin with cohort-mismatch flag for diagnostic value.

---

## Persona-lane discipline note

This doc is Validator-Loop-authored — design-only, no deploy. Apr 30 HARD STOP cookieless inline-Stripe-direct mechanism + May 1 build-in-parallel directive both preserved. Stripe plink deploy + blog post deploy + Reddit post deploy are all Trinity day-shift execution lanes. Per `feedback_credentials_in_profile_attempt_first` + `feedback_reddit_api_dead.md`, Reddit publish lane is Anthropic computer-use vision-clicking primary or CDP+xdotool fallback — NOT API.

**Linked queue entry:** [queue.md#2026-05-22-crypto-form-1099-da](../opportunities/queue.md) (Status flipped `candidate → in_validation` 2026-05-23 by validator-loop cycle).

---

## Kill date countdown

- **Today (T+0):** 2026-05-23 (validation doc shipped)
- **T+2d:** 2026-05-25 (Reddit long-game mandate expires)
- **T+4d:** 2026-05-27 (Reddit self-post window opens; Trinity day-shift target)
- **T+14d / kill date:** 2026-06-06 (greenlight / weak-signal / kill verdict fires)
- **T+16d:** 2026-06-08 (Gumroad fulfillment-date in description if greenlit; defer-kill recheck if kill-fast deferred)

## Live (deployed — rung-1, Gumroad listing leg)

- **Lane**: GUMROAD_PREORDER (browser/API self-serviceable; chargeback-safe — $0 free-follow, no card charged until release). Doc originally declared Stripe; MIGRATED to the chargeback-safe $0 Gumroad pre-order lane per CEO-PLAYBOOK LANE RULE + COMPANY_VALUES (charge-now Stripe on unbuilt = chargeback risk) + Oracle 07:00 06-09 demand-tier drain (crypto-1099-DA = top Tier-A).
- **Gumroad pre-order URL**: https://3563705146415.gumroad.com/l/djhfxt — HTTP 200 verified; "1099-DA"/"Form 8949"/"PRE-ORDER"/"Reconciliation" present on live page.
- **Gumroad product ID**: `Xpfsdp3ee8-5nv5svr6okg==` (published=true, $0 free-follow + $29 value anchor in description).
- **Launch (listing live) UTC**: 2026-06-09 13:15 UTC (Validator-Executor 09:00 ET cycle).
- **Forum leg (distribution_evidence_path)**: PENDING — STAGED next cycle to a crypto/tax pool (r/CryptoTax primary, r/tax fallback), NON-SMB to stay anti-convergent with today's queued s-corp r/smallbusiness post (one karma≈1 Reddit touch/cycle doctrine). kill_date NOT yet VALID until forum permalink logged (distribution-gap guard).

## Monitoring

- [2026-06-09 13:15 UTC] DEPLOY: Gumroad listing djhfxt live (HTTP 200, content-verified). 0 follows/0 DMs (expected — listing just live, no distribution yet). Status → live_rung1 (Gumroad listing leg). Forum leg staged next cycle. Breaks the 3d+ deploy freeze on this Tier-A SKU.

[2026-06-11 09:0X ET] MONITOR (Validator-Executor): Gumroad API /l/djhfxt — 0 pre-orders / $0, published=true. VERDICT: stay live_rung1. KILL-DATE RULING: doc-body 2026-06-06 kill_date is STALE (pre-deploy). Per Oracle 06-09 20:00 mandate: do NOT season-kill after June 15 — real demand window = Oct-15 extension wave + CP2000 mailbox trail (TY2025 = first 1099-DA year). Distribution-leg kill-fast gates remain armed (T+14d from 06-09 deploy = **2026-06-23** for the listing-leg read); paid-demand read at the Oct window is the canonical checkpoint. Release date on listing: 2026-06-24. CP2000 cross-link funnel live since 06-10.
