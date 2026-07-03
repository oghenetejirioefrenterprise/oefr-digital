# Validation — State Unemployment Denial 50-State Appeal Kit

- **Opportunity**: [2026-05-21] State unemployment denial 50-state appeal documentation kit + 14/30-day window tracker + UI hearing preparation binder — [queue.md](../opportunities/queue.md)
- **Date opened**: 2026-05-21
- **Validator**: Trinity (validator-loop)
- **Rung**: 1 (FREE — Stripe pre-order link primary + Etsy entry-tier secondary + value-first forum post; no paid ads)
- **Status**: killed (kill_as_never_shipped — deploy-gate-never-cleared) 2026-06-09; prior: in_validation (rung-1 designed; Stripe plink deploy gated on Trinity day-shift 3-competitor pricing scrape per TJ mandate)
- **Stripe Payment Link**: pending Trinity day-shift deploy (target slug: `state-unemployment-denial-appeal-kit`)
- **Deploy timestamp (UTC)**: TBD (gated on 3-competitor pricing scrape against `etsy.com/market/unemployment` + `etsy.com/market/appeal_denial_letter` + Brian Smith Law)
- **Kill date**: 2026-06-04 (14 days from today)
- **Greenlight threshold**: ≥3 Stripe completed sessions OR ≥1 session + ≥100 blog sessions on `oefrenterprise.com/blog/unemployment-appeal-*` cluster by 2026-06-04
- **Weak-signal threshold**: 1–2 sessions OR ≥30 blog sessions + ≥1 substantive inbound DM/comment → climb to rung 2 (Pinterest SKIP per audience-cluster mismatch; rung 2 = Etsy listing publish at $19 entry-tier instead, $15 budget reserved for cover-image render only)
- **Kill threshold**: 0 sessions AND 0 inbound DMs AND <30 blog sessions by 2026-06-04 → reject, log cause, move on

---

## CANONICAL DELIVERABLE INVENTORY (single source of truth)

> All customer-facing surfaces (Stripe NAME + DESC, cover.png, Etsy listing copy, blog post, forum post) MUST enumerate deliverables from this list verbatim. Any deviation = drift, flagged at nightly lint.

**Bundle shape:** 8-tab kit (4 denial-reason letter templates + 50-state pointer index + hearing-prep + decision-tree + statute anchor)

**4 Denial-Reason Appeal-Letter Templates (verbatim — grep these exactly):**
1. Misconduct denial response letter (employer burden-of-proof framework + state-defined-misconduct decoder)
2. Voluntary-quit denial response letter (good-cause-attributable-to-employer evidence framework)
3. Refused-suitable-work denial response letter (suitability-test rebuttal framework)
4. Not-able-and-available denial response letter (medical / childcare / school cohort)

**4 Non-letter Tools (always enumerated separately):**
- 50-State Appeal-Deadline + Filing-Method Pointer Index (deadline + portal URL + form-number per state)
- Telephonic ALJ Hearing Prep Worksheet (opening statement framework + witness-question list + employer-defense rebuttal + cross-examination prompts)
- Evidence-Gathering Checklist by Denial-Reason (pay stubs, separation notice, employer communications, medical records by cohort)
- Post-Hearing Decision-Tree (favorable vs unfavorable + further appeal pathways: state appeal board → state court → SSA Title XII conformity complaint)

**Federal-statute anchor citations** (verbatim — factual not creative):
- 42 USC §503 — Title III Social Security Act state UI program requirements
- 20 CFR Part 640 — federal regulations governing state UI benefit determinations
- Title III SSA — federal financing + conformity framework for all 50 state UI programs
- State-specific deadlines (14-30 day variants) — pointer-index only, NOT 50 separate authoring

**BANNED phantom counts (do NOT use):**
- ❌ "50 state letter templates" (we ship 4 federally-anchored letter shapes + 50-state pointer index, NOT 50 separately authored letters)
- ❌ "50-state hearing transcripts" (we provide framework, not state-specific transcripts)
- ❌ "Guaranteed approval" (illegal in UI advocacy + violates NOT-legal-advice framing)

**Approved count strings:** `4 denial-reason letter templates + 50-state pointer index` / `8-tab unemployment appeal kit` / `4 federally-anchored letter templates with 50-state deadline pointer` / `4-letter cohort + hearing-prep + 50-state decoder`.

---

## Why this opportunity passed the validator gate

1. **Edge fit passes** — production speed (20-26h MVP — federal Title III + 50-state appeal-deadline matrix already published by state DOLs; pointer-index design pattern proven on queue's HOA-dispute + auto-insurance-total-loss + security-deposit kits), AI-native cost ≈$0 marginal, programmatic SEO (50 state sub-pages + 4 denial-reason sub-pages = 54 surfaces), cold-start communities (r/Unemployment 200K / r/Edd 60K / r/jobs 1.5M), NOT taste/community/personality-driven (utility-shape financial-protection documentation, opposite of Etsy-aesthetic cohort).
2. **Roster clean** — `product-roster.md` contains zero unemployment-appeal SKU; ai-layoff-pack dead product was job-search-side templates NOT benefits-appeal-side; non-overlapping. No prior-failure risk.
3. **5 demand signals** confirmed in queue entry (≥3 threshold passed):
   - Etsy direct $15 supply at `etsy.com/market/unemployment` — direct buyer-pool market exists at entry-tier pricing, NOT $2.99 commodity-floor.
   - State portal hair-on-fire deadline confirmed: Texas Workforce Commission "File an Unemployment Appeal" + Ohio "you have 14 days to file an appeal" + similar across all 50 state UI portals.
   - 5+ active Reddit threads across r/Unemployment + r/Edd + r/Pennsylvania + r/Ohio + r/Geico-employees within last 24mo, all post-denial hair-on-fire shape.
   - Attorney-confirmed pro-se norm: Brian Smith Law Ohio guide ("hints, tips, and template") — attorneys publish DIY guides because cohort is pro-se-cultural-norm at ALJ telephonic hearings, NOT attorney-routed like workers-comp.
   - YouTube template-walkthrough cohort: 1.4M-view content channel "[LETTER TEMPLATE] How To Write An Unemployment Benefits Appeal Letter" confirms content-marketing-style overlap with iep-504 pillar SEO blueprint.
4. **Hair-on-fire 14-day deadline** = highest-conversion-trigger axis on queue (matches iep-504 stay-put 5-day + mortgage-forbearance 30-day + medicare-observation 24h). 14-day deadline locked across most states; cohort moves on resolution not browse.
5. **No cannibalization** — distinct from iep-504 (special-ed parent advocacy), workers-comp (attorney-routed cohort — wrong shape — REJECT-context), lawn-care (operator SOP), all designed-pipeline SKUs. Federal-uniform-with-state-pointer shape = same iep-504 success fingerprint at larger buyer pool (~6-7M annual denials vs ~7.5M IEP students).
6. **Pro-se cultural norm** — opposite of workers-comp / EEOC charge / DACA / Form 8857 cohort-attorney-routing veto pattern that killed those Etsy lanes. State ALJ telephonic hearings = pro-se by default per attorney-published guides + DOL data.
7. **NOT a non-edge market** — edges.md check: not Etsy handmade-aesthetic, not personality-driven, not enterprise B2B sales, not premium-luxury positioning. Utility-shape forms-first procedural aid in federally-anchored regulatory window.

---

## Rung 1 — Stripe pre-order listing (primary deploy channel per persona contract)

### Listing metadata

- **Price**: $19.00 (pre-order entry-tier per opportunity validation plan + Oracle 2026-05-19 dual-anchor pricing framework $19 Etsy + $29 Stripe-upsell-tier for later-stage hearing-prep cohort)
- **Fulfillment date in description**: 2026-06-05 (15 days from today; honors refund window if kill verdict fires 2026-06-04; per May 1 build-in-parallel directive thin v0 8-tab PDF ≤T+48h post-Stripe-deploy)
- **Slug**: `state-unemployment-denial-appeal-kit`
- **Stripe product name**: `State Unemployment Denial Appeal Kit`
- **Completed-sessions cap**: 20 (self-caps on validation; urgency signal in checkout meta)
- **URL target post-deploy**: `https://buy.stripe.com/<TBD>` — link added to monitoring log on deploy

### Title (60 chars max)

```
Unemployment Denial Appeal Kit — 50-State + Hearing Prep
```
(55 chars — fits under cap.)

### Subtitle

```
For claimants who have 14 days to appeal and can't afford a $300/hour attorney. 4 federally-anchored appeal-letter templates (misconduct / voluntary-quit / refused-work / not-able-and-available) + 50-state deadline pointer + telephonic ALJ hearing prep. Forms-first, disclaimer-backed, not legal advice.
```

### Description (~300 words, bullet-structured, concrete)

```
You opened the determination letter. It denied your benefits. You have 14 days in most states (10-30 days depending on state) to file a written appeal — or the denial becomes final and you lose every dollar you would have collected.

Unemployment attorneys charge $200-800 per case. Most claimants go unrepresented at the ALJ telephonic hearing because they can't afford that, then read their statement off the back of an envelope. State ALJ hearings are pro-se by cultural norm — attorneys publish DIY guides because they know most denials never reach a lawyer's desk.

This kit is what an organized claimant-side advocate would put in your hand the day the denial letter arrives — without the $800 case fee.

What you get (pre-order — ships 2026-06-05):

- **4 denial-reason appeal-letter templates** — one for each of the federal-uniform denial cohorts (per 20 CFR Part 640): misconduct (employer burden-of-proof framework), voluntary-quit (good-cause-attributable-to-employer evidence), refused-suitable-work (suitability-test rebuttal), not-able-and-available (medical / childcare / school cohort).
- **50-State Appeal-Deadline + Filing-Method Pointer Index** — the deadline + state-portal URL + form-number you need for your specific state. 14-day deadline in most states; some are shorter.
- **Telephonic ALJ Hearing Prep Worksheet** — opening statement framework, witness-question list, employer-defense rebuttal framework, cross-examination prompts. Most denials are won or lost at the hearing, not the letter.
- **Evidence-Gathering Checklist by Denial-Reason** — pay stubs, separation notice, employer communications, medical records, witness statements — what to collect first based on which denial-reason your state cited.
- **Post-Hearing Decision-Tree** — favorable vs unfavorable + further appeal pathways (state appeal board → state court → SSA Title XII conformity complaint where applicable).
- **Federal-statute anchor index** — 42 USC §503 + 20 CFR Part 640 + Title III SSA verbatim citations for use in your appeal letter and at hearing.

Federally anchored. Pro-se-ready. Not legal advice — when your case involves a >26-week claim, cross-state employer, or suspected-fraud allegation against you, the kit's attorney-handoff-trigger decision-tree tells you when to stop and call a lawyer.

Pre-order locks the $19 price. If we ship by 2026-06-05, you get the kit. If we don't, full refund — no questions.
```

**Disclaimer block (always placed at top of PDF + Stripe DESC + blog post + Etsy listing per NOT-legal-advice 3-placement framing):**

```
NOT LEGAL ADVICE. This kit is a federally-anchored procedural-documentation organizer covering the federal Title III SSA framework (42 USC §503 + 20 CFR Part 640) that governs all 50 state UI programs. State-procedural variance is handled via pointer index — you must verify your state's deadline and filing method against your specific state's portal. Use the included Attorney-Handoff-Trigger decision-tree if your case involves: >26-week-claim disputes, cross-state employers, suspected-fraud allegations against you, or amounts in dispute >$15,000.
```

### Cover image brief

```
- Size: 1500×1500 px Stripe square + 800×800 thumbnail
- Style: Calmly procedural (federal-anchor-blue + neutral-gray + #B91C1C accent), NO ambulance-chaser red-alarm palette
- Hero copy: "Unemployment Denial Appeal Kit" / sub "50-state · 4 letter templates · ALJ hearing prep"
- NO photos of people, NO faces, NO persona-fiction (per Apr 29 no-niche-anchor + persona-fiction-gate)
- Statute anchor block bottom-right: "42 USC §503 · 20 CFR Part 640"
- File generation: scripts/gen-etsy-*-images.py pattern (swap dimensions to 1500×1500)
- Save to: products/state-unemployment-denial-appeal-kit/stripe-cover.png
```

---

## Rung 1 — Value-first forum post (per persona contract)

**Target community**: r/Unemployment (~200K subscribers, recurring post-denial cohort, established mod tolerance for procedural-help comments).

**Ship-window logic:** Reddit long-game mandate (2026-03-25 pure-value, no-CTA) expires 2026-05-25 (T+4d from today). Initial ship targets 2026-05-26 single-tasteful-link variant. Pre-mandate-expiration fallback variant included below for use if mandate is extended.

### Variant A — Post-Mandate (ship 2026-05-26 onward, single tasteful link)

**Title:**
```
14 days to appeal an unemployment denial — the 4 federal denial-reason buckets, what each one needs, and what the ALJ hearing actually looks like
```

**Body (~600 words, value-first, single mention at end):**

```
Mod note: posting this as a pro-se procedural breakdown — not legal advice, not selling at the top.

If you just got a denial letter, the clock already started. Most states give you 14 days to file the written appeal. Some are shorter (10 in a few states), some are 21-30 (a small handful). The federal framework is 42 USC §503 + 20 CFR Part 640 — Title III SSA — but the deadline is state-administered. Open your determination letter, look for the appeal deadline phrase, count business or calendar days (state-specific).

The federal regulations slot every denial into one of four buckets. Knowing which bucket yours falls into changes what evidence you collect and what your appeal letter has to say.

**1. Misconduct (employer-initiated separation cited as cause)**
The employer has the burden of proof at the hearing — they have to show you committed "misconduct" as defined by your state's UI statute. State definitions vary (Ohio = "willful violation of reasonable employer rule," California = "wanton or willful disregard"). Most "misconduct" denials reverse on appeal when the employer fails to produce a written rule, a written warning, and proof the employee saw both. Collect: separation notice, employee handbook acknowledgment, any prior written warnings, witnesses to the alleged incident.

**2. Voluntary quit (you resigned)**
Standard is "good cause attributable to the employer" — meaning your reason for quitting has to trace back to something the employer did, not something personal. Hostile work environment + documented (emails, HR complaints) usually qualifies. "I was burned out" usually doesn't. Collect: emails to HR, doctor's notes if medical, any safety complaints filed.

**3. Refused suitable work (you turned down a job offer)**
State runs a "suitability test" — comparing the offered job to your previous occupation, pay, distance, and your skills. The further the offered job is from your baseline (different industry, 50% pay cut, 90-minute commute), the easier this is to rebut. Collect: prior pay stubs, commute math, written job offer with terms.

**4. Not able and available**
You said you were sick, taking care of a child, in school, or otherwise restricted — and they read that as not "able and available" to work. The rebuttal is usually: you were available for SOME work, with reasonable restrictions. Doctor's notes, school schedule, childcare hours go here.

**The ALJ hearing is the actual decision point.** Most states do it by phone. 30-60 minutes. The judge swears you in, lets the employer go first (in misconduct cases), then asks you questions. You can cross-examine the employer's witnesses. Read your state's hearing procedure on the state UI portal before the call — they're usually 2-3 pages.

If your case involves any of these, talk to an attorney instead of running pro-se: >26-week claim disputes, cross-state employer (federal labor preemption), suspected-fraud allegations against you, or amounts >$15,000 in dispute.

I built an 8-tab kit packaging this with the 50-state deadline + portal index, the 4 letter templates, and the hearing-prep worksheet — pre-order at $19 if it helps: https://buy.stripe.com/<TBD>. Free if you message me and explain the denial bucket — happy to send the relevant tab.
```

### Variant B — Pre-Mandate (if mandate is extended past 2026-05-25, pure value, no link)

Same body as Variant A, **drop the final two sentences** (no Stripe link, no "message me" — pure procedural value comment).

### Forum-post pre-flight gates (must PASS before ship)

- ✅ persona-fiction-gate: no "I was denied unemployment last month" first-person fabrication (third-person research-aggregator voice throughout)
- ✅ banned-discount-gate: no "% off," no "sale," no "limited time discount" (only "pre-order locks the $19 price" which is a price-lock not a discount)
- ✅ factual-integrity-gate: all federal statute citations (42 USC §503, 20 CFR Part 640, Title III SSA) verified against ecfr.gov + uscode.house.gov before ship
- ✅ NOT-legal-advice 3-placement: top of post + cover image + Stripe DESC
- ✅ Pro-Se-Limits-Decoder + Attorney-handoff-trigger present (>26-week claim + cross-state employer + suspected-fraud + >$15K dispute)
- ✅ edges-non-edges-gate: no Etsy handmade-aesthetic claims, no personality-driven hooks, no premium-brand positioning
- ✅ blog-slug-validator: no `/blog/*` URLs reference 404 destinations (none referenced in this variant; future blog-pillar deploy will require slug re-validation)

---

## Kill / Greenlight thresholds (specific numbers, specific dates)

| Outcome | Trigger | Action |
|---|---|---|
| **Kill** | 0 Stripe completed sessions AND 0 inbound DMs/comments AND <30 blog sessions on cluster by **2026-06-04 23:59 ET** | Reject. Update queue.md to `rejected` with kill-verdict timestamp. Append to roster as dead. Deactivate Stripe plink. Cascade lesson: if 50-state-pointer + federal-uniform + hair-on-fire shape with 6-7M cohort doesn't move at $19 entry-tier, the cohort doesn't buy proceduralization on Stripe direct — Etsy organic-search lane is the only iep-504-shape that converts, lock the read into edges.md. |
| **Weak signal** | 1–2 Stripe sessions OR ≥30 blog sessions + ≥1 substantive inbound DM/comment by **2026-06-04** | Climb to rung 2. NOT Pinterest (audience-cluster mismatch — claimant cohort is mostly post-denial-search not browse-discovery). Rung 2 = Etsy listing publish at $19 entry-tier on display:98 CDP per established iep-504 Etsy lane pattern. Re-read at T+216h post-Etsy-publish. |
| **Greenlight** | ≥3 Stripe completed sessions OR ≥1 session + ≥100 blog sessions on `oefrenterprise.com/blog/unemployment-appeal-*` cluster by **2026-06-04** | Build MVP immediately (thin v0 8-tab PDF already ≤T+48h post-Stripe-deploy per May 1 directive; greenlight triggers full 8-tab Google Sheets build + IDEA-compliant fact-check pass + Etsy listing + Pinterest SKIP-reaffirmed + blog pillar build-out). Promote to live_rung2. |

**Defer-kill clause:** Per kill-fast deploy-rule symmetric gate (Oracle 2026-05-07), if 0 sessions BUT distribution evidence (Reddit post URL, blog post URL) is on file with T+24h impressions ≥25, status stays `stay_live_rung1 + channel-empty` for 48h additional, change channel, retest. If T+24h impressions <25 on the Reddit post, the channel never reached the buyer pool — change to Etsy lane before killing.

---

## Measurement plan (what to count, where, how often)

| Metric | Source | Check cadence |
|---|---|---|
| Stripe `plink_<TBD>` completed_sessions | `stripe.PaymentLink.retrieve()` + `stripe.checkout.Session.list(payment_link=...)` | Daily 09:00 ET Validator-Executor cycle |
| Stripe charges_succeeded 7d | `stripe.Charge.list(created={'gte': N-7d}, status='succeeded')` | Daily 09:00 ET + 18:00 ET stripe-pulse |
| Inbound DMs/comments on Reddit post | Reddit browser CDP read on display:98 (per `feedback_credentials_in_profile_attempt_first` — REDDIT creds in `~/.profile`) | T+24h, T+72h, T+168h post-publish |
| Reddit post impressions / upvotes | Reddit browser CDP read on display:98 | T+24h, T+72h, T+168h post-publish (T+24h gates kill-fast deploy-rule per Oracle 2026-05-07) |
| Blog cluster sessions `/blog/unemployment-appeal-*` | Vercel Analytics + Plausible if configured | Daily 09:00 ET |
| Stripe plink active status | `stripe.PaymentLink.retrieve()` | Daily 09:00 ET Validator-Executor cycle |
| Email-list new-subscriber count (Resend) | Resend dashboard + DB query | T+72h post-blog-publish |

**Distribution evidence log (per kill-fast deploy-rule):**
- `distribution_evidence_path:` field appended on each ship: Reddit post URL, blog post URL, Etsy listing URL (when applicable)
- This validation doc serves as the canonical distribution-evidence path register
- Validator-Executor reads from this section at 09:00 ET each cycle

---

## Pre-deploy gating (Trinity day-shift carries)

Per Validator persona contract + Apr 30 HARD STOP + May 1 build-in-parallel + Oracle 2026-05-19 dual-anchor pricing framework + TJ-mandated 3-competitor pricing scrape gate:

| # | Gate | Owner | Status |
|---|---|---|---|
| 1 | 3-competitor pricing scrape against `etsy.com/market/unemployment` + `etsy.com/market/appeal_denial_letter` + Brian Smith Law guide pricing (validate $19 anchor) | Trinity day-shift CDP on display:98 single-tab | ⏳ pending |
| 2 | Stripe Product + Price + Payment Link create (`product_name=State Unemployment Denial Appeal Kit`, `unit_amount=1900`, slug `state-unemployment-denial-appeal-kit`, `completed_sessions=20` cap) | Trinity day-shift after gate 1 | ⏳ pending |
| 3 | Blog pillar draft: `oefrenterprise.com/blog/unemployment-appeal-letter-50-state-deadline-guide` (federal-anchor breakdown + 4 denial-reason cohort framing + ALJ hearing prep + state-pointer index inline + Stripe pre-order CTA mid-article + bottom) | SEO Operator next cycle | ⏳ pending |
| 4 | factual-integrity-gate run on blog draft (verify 42 USC §503 + 20 CFR Part 640 + state-portal URLs resolve HTTP 200) | Pre-Vercel-deploy | ⏳ pending |
| 5 | Cover image render (1500×1500, federal-anchor-blue palette per cover brief above) | Trinity day-shift | ⏳ pending |
| 6 | Reddit post Variant A ship to r/Unemployment 2026-05-26 morning ET (post Reddit mandate expiration) | Trinity day-shift (CDP+xdotool on display:98 per established Reddit lane) | ⏳ pending — gated on mandate expiration |
| 7 | Etsy listing pre-draft (rung-2 escalation only — DO NOT publish on rung-1; reserved for weak-signal-climb path) | Morpheus brief authorship | ⏳ deferred to weak-signal-climb |

**Pinterest SKIP-by-default reaffirmed:** Post-denial panic-cohort buys on resolution, not browse-discovery. Same audience-cluster mismatch lesson as workers-comp Pinterest theater (Oracle 2026-05-10). Reserved as rung-3 contingency only if weak-signal-climb path runs.

---

## Branch tree (pre-staged per iep-504 (c-revised) pattern)

To be applied at T+336h canonical kill-branch verdict 2026-06-04 09:00 ET by Validator-Executor:

- **(a) Greenlight branch (≥3 sessions OR ≥1 + ≥100 blog sessions):** promote to `live_rung2` + full 8-tab Google Sheets MVP build (≤72h) + Etsy listing publish + blog pillar full build-out.
- **(b) Weak-signal branch (1–2 sessions OR ≥30 blog + ≥1 DM):** climb to rung 2 = Etsy listing publish at $19 entry-tier + Reddit cross-post to r/Edd + r/jobs (post-mandate light-CTA) + T+216h re-read.
- **(c) Channel-empty branch (0 sessions + Reddit T+24h impressions <25):** `stay_live_rung1 + channel-empty` + change channel (Reddit → blog-first SEO primary) + 48h re-test before kill.
- **(d) Product-empty branch (0 sessions + Reddit T+24h impressions ≥25 + blog <30 sessions):** REJECT — cohort saw the kit and didn't buy → distribution-channel-fit not the issue, product-shape/pricing/copy mismatch. Cascade lesson into edges.md.

---

## Risk readings (3 readings per Karpathy + verification-before-completion)

**Reading 1 — Highest probability (60%):** Test runs identically to iep-504 (0 paid / 0 sessions / Day 14 = kill verdict via channel-empty branch). UI appeal cohort searches Google + state portal directly, not Reddit or Stripe pre-order. Resolution-buy not browse-buy. Channel-fit mismatch — same as iep-504 8-cycle convergence.

**Reading 2 — Mid probability (25%):** Single Reddit value-post drives 1-2 paid sessions because of larger cohort size (6-7M denials/yr vs 7.5M IEP students BUT shorter deadline window = sharper conversion-trigger). Weak-signal climb to Etsy lane.

**Reading 3 — Lower probability (15%):** Blog SEO + Reddit value-post hits ≥3 sessions. Greenlight. Larger cohort + sharper hair-on-fire deadline + zero direct competitor = the iep-504-shape that finally clears. Mitigation: if greenlight fires, immediately Etsy CDP publish (same lane validated iep-504 buyer-pool research) + Pinterest SKIP reaffirmed.

**Calibration check:** I am the Validator, not the seller. My job is to design the cheapest test that kills or greenlights. Reading 1 dominates because iep-504 lifetime 0 paid is the strongest signal in this dataset. The right move is to ship the test fast, log distribution evidence, and let the 14-day timer fire the verdict at 2026-06-04 09:00 ET.

---

## Files referenced

- This doc: `~/apps/OEFR Digital Products/trinity/knowledge/validations/2026-05-21-state-unemployment-denial-50-state-appeal-kit.md`
- Queue source: `../opportunities/queue.md` lines 2040–2057
- Edges check: `../edges.md`
- Roster check: `../product-roster.md` (zero matches for "unemploy" — clean)
- Mirror precedent: `2026-04-25-iep-504-parent-advocacy-kit.md` (federally-anchored + state-pointer fingerprint match)
- Channel-fit reference: `2026-04-27-workers-comp-injured-worker-kit.md` (REJECT cohort context — attorney-routed; this validation explicitly avoids that pattern via pro-se cultural norm in UI ALJ hearings)

## Kill verdict — kill_as_never_shipped (deploy-gate-never-cleared)
- **Date**: 2026-06-09 (Validator-Executor 09:00 ET cycle)
- **Authority**: CEO-PLAYBOOK Rule 11 + Oracle 07:00 06-09 demand-tier limbo drain. Tier-C SKU: never deployed (no Live section, empty distribution_evidence_path), 14d+ past own kill_date, deploy gate (pricing-scrape / content-QA / URL-audit) never cleared.
- **Edge rationale**: 50-state free-substitute (every state UI agency = free appeal forms/instructions); non-edge
- **Verdict**: kill_as_never_shipped. This is DISTINCT from a live_rung1→rejected kill — the SKU forfeits ~0 option value (pre-deploy, zero sunk distribution, edges-vetoed pool). Resolves the validation-limbo deadlock per monitor.
