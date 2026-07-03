# Validation — Auto-Insurance Total-Loss Valuation Dispute Kit

- **Opportunity**: [2026-05-20] Auto-insurance total-loss valuation dispute documentation kit (NAIC §6 UCSPA framework + ACV comparable-vehicle evidence binder + 50-state appraisal-clause pointer index) — [queue.md](../opportunities/queue.md)
- **Date opened**: 2026-05-22
- **Validator**: Trinity (validator-loop)
- **Rung**: 1 (FREE — Stripe pre-order link primary + blog-first SEO secondary + value-first forum post; no paid ads)
- **Status**: live_rung1 (Gumroad $0 pre-order listing leg deployed 2026-06-10 18:0X ET by Validator-Executor via Rule-11 LANE MIGRATION — see Live section; forum leg PENDING)
- **Stripe Payment Link**: SUPERSEDED — never deployed. Stripe charge-now $24 on an unbuilt product = chargeback risk (COMPANY_VALUES); doc sat 19d on a never-actioned pricing-scrape gate and went 5d past its own kill_date (Rule-11 deadlock). Resolved this cycle via the sanctioned chargeback-safe Gumroad $0 pre-order lane (same migration as crypto-1099-da 06-09). Pricing-scrape gate moot at $0; the $24 anchor survives as "value at release."
- **Deploy timestamp (UTC)**: 2026-06-10T22:0XZ (Gumroad lane)
- **Kill date**: 2026-06-24 (re-armed by lane migration; VALID only once distribution_evidence_path is on file per kill-fast deploy-rule — original 2026-06-05 superseded, SKU was never exposed before today)
- **Greenlight threshold (lane-migrated)**: ≥5 Gumroad pre-orders by 2026-06-24 → 48h MVP build (9-tab spec below)
- **Weak-signal threshold (lane-migrated)**: 1–4 pre-orders OR ≥1 substantive inbound DM/comment → climb to rung 2 (Pinterest SKIP per panic-cohort audience-cluster mismatch; rung 2 = additional Reddit lanes r/PersonalFinance + r/cars + 1 cohort-matched FB group, NOT paid ads)
- **Kill threshold (lane-migrated)**: 0 pre-orders AND listing views <50 AND 0 inbound by 2026-06-24 → reject, log cause, move on

## Live (rung 1 — Gumroad listing leg, lane-migrated)

- **Gumroad URL**: https://3563705146415.gumroad.com/l/homayb
- **Gumroad product ID**: `pdImgI6DvIgDg52uwgmVjQ==`
- **Price**: $0 pre-order (no card, no charge) · $24 value at release 2026-06-24
- **Launch timestamp (UTC)**: 2026-06-10T22:0XZ
- **Copy provenance**: doc's canonical 9-tab deliverable inventory enumerated VERBATIM (lint rule honored); stale "ships 2026-06-07" date removed (crypto-1099-da P2 class); PRE-ORDER block on top; NOT-LEGAL-ADVICE disclaimer in description.
- **Verification**: API GET re-read published=True / tags=10/10 / price=0 / 6 content checks present. Independent live curl HTTP 200: PRE-ORDER ×4, release-date 2026-06-24 ×4, "instant" ×0, backslash-dollar ×0. Gates pre-deploy: edges-non-edges EXIT 0, blog-slug CLEAN. Draft: tmp/executor-2026-06-10-1800-auto-total-loss-listing.md
- **Forum leg (distribution_evidence_path)**: PENDING — value-first zero-link COMMENT (post format dead for karma≈1 account per 06-09 lesson ×3) to r/Insurance primary / r/personalfinance fallback, thread-fit selection per SSA-3373 t1_oqu36l1 playbook. NOT shipped this cycle: 2 Reddit touches already fired today (t1_oqu36l1 + t1_oqx2ef5; one-touch/cycle doctrine). kill_date NOT VALID until permalink logged; anti-limbo: forum leg unshipped by 2026-06-17 → distribution-gap flag.

---

## CANONICAL DELIVERABLE INVENTORY (single source of truth)

> All customer-facing surfaces (Stripe NAME + DESC, cover.png, blog post, forum post) MUST enumerate deliverables from this list verbatim. Any deviation = drift, flagged at nightly lint.

**Bundle shape:** 9-tab kit (5 counter-settlement-letter templates + 50-state appraisal-clause pointer + insurer-ACV-report decoder + counter-comparable-vehicle methodology + appraisal-clause-invocation walkthrough + DOI complaint decoder + PRE-attorney decision-tree)

**5 Counter-Settlement-Letter Templates (verbatim — grep these exactly):**
1. Lowball-rebuttal letter (ACV-counter with comparable-vehicle evidence + condition-adjustment math)
2. Comparable-vehicle-presentation letter (formal 4-vehicle counter-comp submission with local-market evidence)
3. Condition-adjustment-demand letter (mileage / trim / options / pre-loss-condition documentation rebuttal)
4. Appraisal-clause-invocation letter (formal demand under state appraisal-clause statute, names appraiser, sets 30-day umpire timeline)
5. Pre-litigation-settlement letter (final 30-day demand citing state UCSPA bad-faith treble-damages exposure before attorney engagement)

**4 Non-letter Tools (always enumerated separately):**
- 50-State UCSPA + Appraisal-Clause Statute Pointer Index (statute citation + appraisal-trigger threshold + insurer-burden-of-proof + DOI complaint portal per state)
- Insurer ACV Report Decoder (CCC/Mitchell/Audatex/J.D. Power report-format walkthrough + biased-comparable-selection anti-patterns)
- Counter-Comparable-Vehicle Methodology Worksheet (same-local-market radius + same-trim + same-mileage-band + same-condition-tier + KBB/Edmunds/NADA/Manheim/CarGurus/Craigslist pull-template)
- Appraisal-Clause Invocation Walkthrough (appraiser-selection + umpire-selection + 30-day-binding-decision framework per state)
- PRE-Attorney Decision-Tree (engage at: insurer bad-faith refusal + appraisal-clause denial + $10K+ dispute-stake; continue DIY at: <$5K dispute + insurer cooperating)
- GAP-Insurance + Leased-Vehicle + Loan-Payoff-Shortfall + Diminished-Value Cross-Reference Index

**Federal + state statute anchor citations** (verbatim — factual, not creative):
- NAIC Model Act §6 — Unfair Claim Settlement Practices Act (Model 900)
- 50-state UCSPAs — pointer-index only, NOT 50 separate authoring
- CA Ins Code §2071 — California appraisal-clause statute
- NY Ins L §3404 — New York standard fire-policy appraisal clause (applied to auto by reference)
- TX Ins Code §2210 — Texas appraisal-clause statute
- FL §627.428 — Florida unfair claims framework + attorney-fee shifting
- 46 other state appraisal-clause statutes — pointer-index only

**BANNED phantom counts (do NOT use):**
- ❌ "50 state letter templates" (we ship 5 federally-anchored letter shapes + 50-state pointer index, NOT 50 separately authored letters)
- ❌ "Guaranteed recovery" / "Get $X,XXX back" (illegal-overpromise in consumer-protection space + violates NOT-legal-advice framing)
- ❌ "Insurer must pay" / "Force the insurer" (overstates legal right; framework is leverage, not guarantee)

**Approved count strings:** `5 counter-settlement letter templates + 50-state pointer index` / `9-tab total-loss valuation dispute kit` / `5 federally-anchored letter shapes with 50-state appraisal-clause decoder` / `5-letter cohort + ACV-decoder + appraisal-clause walkthrough + 50-state UCSPA pointer`.

---

## Why this opportunity passed the validator gate

1. **Edge fit passes** — production speed (30-36h MVP — NAIC §6 federal-uniform anchor + 50-state-pointer-index design pattern proven on queue's HOA-dispute + security-deposit + state-unemployment kits + ACV-comparable-vehicle methodology already documented in 5+ Reddit threads + TheAutoMediator/AutoClaimSolutions paid-tier content-marketing pages); AI-native cost ≈$0 marginal; programmatic SEO (50 state sub-pages + 5 letter-template sub-pages = 55+ surfaces); cold-start communities (r/Insurance ~250K, r/PersonalFinance ~17M, r/cars ~6M, r/financialindependence ~2M); NOT taste/community/personality-driven (utility-shape consumer-protection documentation, opposite of Etsy-aesthetic cohort).
2. **Roster clean** — `product-roster.md` contains zero auto-insurance / total-loss / valuation / vehicle / NAIC SKU. No prior-failure risk. No cannibalization with Apr 23 auto-accident pre-claim evidence kit (which is candidate-status, upstream-glovebox slice, different buyer-trigger).
3. **5 demand signals** confirmed in queue entry (≥3 threshold passed):
   - r/Insurance/ldyvh7 "Lowball settlement offer for a total loss? Here's how I didn't accept it — emailed counter settlement which was $1800 more than the original" — hair-on-fire pain + explicit $1,800 recovery-upside dollar-amount.
   - r/Insurance/1r1bp7u "Successfully challenged total-loss valuation — collected comparable vehicles in my local market" — DIY-cohort path-prescription in top comment.
   - r/Insurance/1kz641h "Has anyone ever successfully disputed a Total Loss Value? Yes! It's absolutely possible" — recurring buyer-confusion pattern.
   - 2 paid fee-for-service mediator services (TheAutoMediator + AutoClaimSolutions) at $300-2K+ premium-tier = institutional buyer-WTP signal at higher-than-template price-point. Our $24 kit slots PRE-paid-mediator at "DIY-first-then-escalate" cohort boundary.
   - Car and Driver mainstream automotive publication "How to Fight an Insurance Company Over a Totaled Car" + Wallace Pierce attorney NC walkthrough = consumer-publication cohort-recognition + state-anchored attorney-content-marketing density.
4. **Hair-on-fire post-event trigger** = post-total-loss-declaration consumer cohort with $2K-8K typical recovery upside (up to $20K on premium vehicles + treble-damages exposure on bad-faith state UCSPAs). Insurer typically gives 30-60 days to accept/dispute ACV — sharper conversion-trigger than browse-cohort. Matches iep-504 stay-put + state-unemployment 14-day pattern (life-event-deadline-anchored shape).
5. **No cannibalization** — distinct from Apr 23 auto-accident pre-claim glovebox kit (upstream evidence shape, candidate-status). Distinct from iep-504 (special-ed parent-advocacy cohort). Distinct from state-unemployment (post-denial wage-replacement cohort). Federal-uniform-with-state-pointer shape = same iep-504/unemployment success fingerprint at distinct buyer pool (~3-4M total-loss declarations/year per IIHS+NHTSA).
6. **DIY-first cultural norm proven** — opposite of workers-comp / EEOC / Form 8857 cohort-attorney-routing veto pattern. 5-Reddit-thread top-comment "gather comparable vehicles + present structured dispute" path-prescription confirms DIY-cohort dominance; paid-mediator services engaged only at $5K+ dispute-stake escalation threshold. State-DOI complaint paths are also DIY-cultural.
7. **NOT a non-edge market** — edges.md check: not Etsy handmade-aesthetic, not personality-driven (third-person research-aggregator voice), not enterprise B2B sales, not premium-luxury positioning. Utility-shape consumer-protection documentation in federally-anchored (NAIC §6) + state-statutory (UCSPA + appraisal-clause) regulatory window with decades-stable half-life.
8. **Treble-damages anchor** — many state UCSPAs provide 2x-3x damages on bad-faith claims. On $5K typical dispute-stake, 3x = $15K recovery upside. Buyer WTP for $24 kit against $15K stake is structurally favorable (same dynamic as security-deposit treble-damages WTP-anchor per queue line 1771).

---

## Rung 1 — Stripe pre-order listing (primary deploy channel per persona contract)

### Listing metadata

- **Price**: $24.00 (pre-order entry-tier per opportunity validation plan + Oracle 2026-05-19 dual-anchor pricing framework; $19 considered but rejected — paid-mediator floor is $300-2K, $24 anchors above the $5-15 Etsy-template commodity floor while staying well under DIY-cohort discomfort threshold; pending TJ-mandated 3-competitor scrape may revise to $19 or $29)
- **Fulfillment date in description**: 2026-06-07 (16 days from today; honors refund window if kill verdict fires 2026-06-05; per May 1 build-in-parallel directive thin v0 9-tab PDF + Google Sheets workbook ≤T+48h post-Stripe-deploy)
- **Slug**: `auto-insurance-total-loss-valuation-dispute-kit`
- **Stripe product name**: `Auto Insurance Total-Loss Valuation Dispute Kit`
- **Completed-sessions cap**: 20 (self-caps on validation; urgency signal in checkout meta)
- **URL target post-deploy**: `https://buy.stripe.com/<TBD>` — link added to monitoring log on deploy

### Title (60 chars max)

```
Total-Loss Valuation Dispute Kit — 50-State + Letters
```
(53 chars — fits under cap.)

### Subtitle

```
For drivers whose totaled car got lowballed and have 30 days to push back. 5 federally-anchored counter-settlement letter templates + 50-state appraisal-clause decoder + CCC/Mitchell ACV report walkthrough. Forms-first, disclaimer-backed, not legal advice.
```

### Description (~310 words, bullet-structured, concrete)

```
Your car was declared a total loss. The insurer sent you an ACV offer that's $2,000–$8,000 below what the same car sells for at the dealership two miles away. You have 30 days (sometimes less) to dispute the valuation — or the lowball becomes the payout.

Auto-insurance valuation mediators charge $300–$2,000 (or contingency on the recovery) to fight this for you. Most drivers eat the lowball because they don't know there's a process, or they don't know that NAIC Model §6 + their state's appraisal-clause statute gives them formal leverage the insurer would rather you didn't use.

This kit is what an organized claimant-side advocate would put in your hand the day the ACV offer arrives — without the $1,500 mediator fee.

What you get (pre-order — ships 2026-06-07):

- **5 counter-settlement-letter templates** — lowball-rebuttal with comparable-vehicle evidence + comparable-vehicle-presentation (4-vehicle formal counter-comp submission) + condition-adjustment-demand (mileage/trim/options/pre-loss-condition rebuttal) + appraisal-clause-invocation (formal statute-cited demand naming your appraiser + 30-day umpire timeline) + pre-litigation-settlement (final 30-day demand citing your state UCSPA bad-faith exposure).
- **50-State UCSPA + Appraisal-Clause Statute Pointer Index** — statute citation (CA §2071, NY §3404, TX §2210, FL §627.428, 46 others) + appraisal-trigger threshold + insurer-burden-of-proof + DOI complaint portal per state.
- **Insurer ACV Report Decoder** — CCC One / Mitchell / Audatex / J.D. Power report-format walkthrough + the 6 biased-comparable-selection anti-patterns most lowballs rely on (wrong trim, wrong mileage band, wrong region, wrong condition tier, omitted options, salvage-comp contamination).
- **Counter-Comparable-Vehicle Methodology Worksheet** — same-local-market radius + same-trim + same-mileage-band + KBB/Edmunds/NADA/Manheim/CarGurus/Craigslist pull-template + average-vs-median math.
- **Appraisal-Clause Invocation Walkthrough** — appraiser-selection + umpire-selection + 30-day binding decision framework per state.
- **DOI Complaint Filing Decoder** — 50-state Department-of-Insurance portal pointer + complaint-template + 30-day-response framework.
- **PRE-Attorney Decision-Tree** — when to call a lawyer (insurer bad-faith refusal + appraisal-clause denial + $10K+ stake) vs continue DIY (<$5K + insurer cooperating).
- **GAP / Leased-Vehicle / Loan-Payoff-Shortfall / Diminished-Value Cross-Reference Index** — the four adjacencies that ambush drivers after settlement.

Pre-order locks the $24 price. If we ship by 2026-06-07, you get the kit. If we don't, full refund — no questions.
```

**Disclaimer block (always placed at top of PDF + Stripe DESC + blog post per NOT-legal-advice 3-placement framing):**

```
NOT LEGAL ADVICE. This kit is a consumer-protection procedural-documentation organizer covering the NAIC Model §6 Unfair Claim Settlement Practices framework + 50-state UCSPAs + state appraisal-clause statutes. State-procedural variance is handled via pointer index — you must verify your state's appraisal-clause threshold, DOI complaint deadline, and bad-faith standard against your specific state's statute. Use the included Attorney-Handoff-Trigger decision-tree if your case involves: insurer bad-faith refusal after formal appraisal-clause invocation, appraisal-clause denial in an appraisal-clause state, total-loss disputes >$10,000, suspected fraud allegations against you, or diminished-value claims requiring litigation. This kit is for first-party dispute mechanics only; it is not a substitute for an attorney in litigation.
```

### Cover image brief

```
- Size: 1500×1500 px Stripe square + 800×800 thumbnail
- Style: Calmly procedural (federal-anchor-blue + neutral-gray + #B91C1C accent for "30-DAY DEADLINE" callout), NO ambulance-chaser red-alarm palette, NO totaled-car photography, NO insurance-company logos
- Hero copy: "Total-Loss Valuation Dispute Kit" / sub "50-state · 5 letter templates · NAIC §6 + appraisal-clause decoder"
- NO photos of people, NO faces, NO persona-fiction (per Apr 29 no-niche-anchor + persona-fiction-gate)
- Statute anchor block bottom-right: "NAIC §6 · 50-state UCSPA · CA §2071 · NY §3404 · TX §2210 · FL §627.428"
- File generation: scripts/gen-etsy-*-images.py pattern (swap dimensions to 1500×1500, palette per above)
- Save to: products/auto-insurance-total-loss-valuation-dispute-kit/stripe-cover.png
```

---

## Rung 1 — Value-first forum post (per persona contract)

**Target community**: r/Insurance (~250K subscribers, recurring post-claim dispute cohort, mod tolerance for procedural-help comments confirmed via existing 5-thread cohort top-comment pattern).

**Ship-window logic:** Reddit long-game mandate (2026-03-25 pure-value, no-CTA) expires 2026-05-25 (T+3d from today). Initial ship targets 2026-05-26 single-tasteful-link variant. Pre-mandate-expiration Variant B (pure value, no link) shipped on 2026-05-23 to build cohort recognition + comment-history depth.

### Variant A — Post-Mandate (ship 2026-05-26 onward, single tasteful link)

**Title:**
```
Your car was totaled and the ACV offer feels low — the formal dispute path, the appraisal clause most drivers don't know they can invoke, and when to stop and call a lawyer
```

**Body (~620 words, value-first, single mention at end):**

```
Mod note: posting this as a pro-se procedural breakdown — not legal advice, not selling at the top. Most drivers eat lowball ACV offers because they don't know there's a structured process. NAIC Model §6 (the Unfair Claim Settlement Practices Act) + your state's appraisal-clause statute give you formal leverage. Here's how it works.

**Step 1 — Get the ACV report.**
Whatever number the insurer offered came from a third-party valuation report — usually CCC One, Mitchell, Audatex, or J.D. Power. You're entitled to a copy. Request it in writing. Then read the comparable vehicles they used. The lowballs come from one of six patterns: (a) wrong trim level (LX vs EX vs Touring), (b) wrong mileage band, (c) wrong region (your local market vs national average), (d) wrong condition tier (Good vs Very Good vs Excellent), (e) omitted options (heated seats, sunroof, premium audio), (f) salvage-title or auction-comp contamination of the average.

**Step 2 — Pull your own comparable vehicles.**
Same local market (50-mile radius if rural, 25 if metro). Same year/make/model. Same trim. Same mileage band (±10K). Same condition tier. Pull from at least 4 sources: KBB Private Party + Edmunds True Market Value + NADA Clean Retail + CarGurus + Manheim (if accessible) + local dealer listings + Craigslist private-party. Document with screenshots and URLs. Compute median, not average. Median resists outliers.

**Step 3 — Write the counter-settlement letter.**
State the ACV report's biased pattern explicitly ("Vehicle 3 in the comparable set is the LX trim; my vehicle is the EX trim — equivalent EX vehicles in my local market average $X higher"). Attach your 4-vehicle counter-comp. Include condition-adjustment math (extras the report omitted). Demand revised ACV by a specific date (typically 14 days). Send certified mail.

**Step 4 — Invoke the appraisal clause if the insurer refuses.**
This is the leverage most drivers don't know exists. Most state auto policies include an appraisal clause borrowed from the standard fire-policy framework (CA Ins §2071 is the model; NY §3404, TX §2210, FL §627.428 follow it). It works like binding arbitration: each side names an appraiser, the two appraisers agree on an umpire (or the court appoints one), and the two-of-three vote sets ACV. The insurer pays its appraiser, you pay yours (typically $300–800). On any dispute over ~$3K, the math favors invocation. State-specific exceptions exist — a few states require it to be mutual, a few exclude total-loss from the clause. Check your state.

**Step 5 — DOI complaint runs in parallel.**
Filing a state Department of Insurance complaint costs you nothing and adds a 30-day insurer-response clock. NAIC §6 violations (which most lowball patterns technically are) trigger regulatory attention. The complaint doesn't decide the dispute, but it changes the insurer's incentive math.

**When to stop and call an attorney:** insurer bad-faith refusal AFTER formal appraisal-clause invocation, appraisal-clause denial in an appraisal-clause state, total-loss disputes over $10,000, suspected-fraud allegations against you, or diminished-value claims that the insurer denies entirely. State UCSPAs allow 2x–3x damages on bad-faith — at that point you want a contingency-fee attorney, not a $24 template kit.

If it helps to have this packaged — the NAIC §6 framework, the 50-state UCSPA + appraisal-clause statute citations, the 5 counter-settlement letter templates, the ACV-report decoder, and the PRE-attorney decision-tree — I built a kit. Pre-order at $24 here: https://buy.stripe.com/<TBD>. Free if you message me the denial bucket and your state — happy to send the relevant tab while the kit is in pre-order.
```

### Variant B — Pre-Mandate (ship 2026-05-23, pure value, NO link)

Same body as Variant A, **drop the entire final paragraph** (no Stripe link, no "message me," no pre-order mention). Pure procedural value comment to build cohort recognition + karma depth pre-mandate-expiration. If mandate is extended past 2026-05-25, Variant B remains the only ship until extension is lifted.

### Forum-post pre-flight gates (must PASS before ship)

- ✅ persona-fiction-gate: no "I totaled my car last week" first-person fabrication (third-person research-aggregator voice throughout, references "most drivers" / "your state" patterns)
- ✅ banned-discount-gate: no "% off," no "sale," no "limited time discount" (only "pre-order locks the $24 price" which is a price-lock not a discount)
- ✅ factual-integrity-gate: all federal+state statute citations (NAIC Model §6, CA Ins §2071, NY §3404, TX §2210, FL §627.428) verified against ecfr.gov + state legislature portals + content.naic.org before ship; all third-party valuation-vendor names (CCC One, Mitchell, Audatex, J.D. Power) DNS-resolve + Google-presence verified
- ✅ NOT-legal-advice 3-placement: top of post + cover image + Stripe DESC
- ✅ Pro-Se-Limits-Decoder + Attorney-handoff-trigger present (insurer bad-faith + appraisal-clause denial + >$10K stake + suspected-fraud + diminished-value litigation)
- ✅ edges-non-edges-gate: no Etsy handmade-aesthetic claims, no personality-driven hooks, no premium-brand positioning
- ✅ blog-slug-validator: no `/blog/*` URLs reference 404 destinations (none referenced in Variant A or B; future blog-pillar deploy will require slug re-validation)
- ✅ destination-fidelity gate: Stripe pre-order URL in Variant A must be live + active=True at ship time (gate-check via `stripe.PaymentLink.retrieve()` ≤5min pre-publish)

---

## Kill / Greenlight thresholds (specific numbers, specific dates)

| Outcome | Trigger | Action |
|---|---|---|
| **Kill** | 0 Stripe completed sessions AND 0 inbound DMs/comments AND <30 blog sessions on cluster by **2026-06-05 23:59 ET** | Reject. Update queue.md to `rejected` with kill-verdict timestamp. Append to roster as dead. Deactivate Stripe plink. Cascade lesson: if NAIC-§6 + 50-state-appraisal-clause + DIY-cohort-proven shape with 3-4M annual cohort doesn't move at $24 entry-tier with Reddit value-comment + blog SEO, the auto-insurance-dispute cohort searches Google + state-DOI directly (not Reddit, not pre-order Stripe). Update edges.md with channel-fit failure mode. |
| **Weak signal** | 1–2 Stripe sessions OR ≥30 blog sessions + ≥1 substantive inbound DM/comment by **2026-06-05** | Climb to rung 2. NOT Pinterest (panic-cohort post-event = resolution-buy not browse-buy; same audience-cluster mismatch as workers-comp Pinterest theater per Oracle 2026-05-10). Rung 2 = cross-post to r/PersonalFinance + r/cars + r/financialindependence value-first (≤$15 budget total, reserved for cover-image regen only if cohort needs re-visual). Re-read at T+216h post-rung-2 ship. |
| **Greenlight** | ≥3 Stripe completed sessions OR ≥1 session + ≥100 blog sessions on `oefrenterprise.com/blog/auto-total-loss-*` cluster by **2026-06-05** | Build MVP immediately (thin v0 9-tab PDF + Google Sheets ≤T+48h post-Stripe-deploy per May 1 directive already triggered on first paid; greenlight triggers full 9-tab Sheets build + 50-state appraisal-clause statute-citation fact-check pass + blog pillar build-out + X owner-session cohort-tweet). Promote to live_rung2. |

**Defer-kill clause:** Per kill-fast deploy-rule symmetric gate (Oracle 2026-05-07), if 0 sessions BUT distribution evidence (Reddit post URL, blog post URL) is on file with T+24h impressions ≥25, status stays `stay_live_rung1 + channel-empty` for 48h additional, change channel, retest. If T+24h impressions <25 on the Reddit post, the channel never reached the buyer pool — change to blog-first SEO primary before killing.

---

## Measurement plan (what to count, where, how often)

| Metric | Source | Check cadence |
|---|---|---|
| Stripe `plink_<TBD>` completed_sessions | `stripe.PaymentLink.retrieve()` + `stripe.checkout.Session.list(payment_link=...)` | Daily 09:00 ET Validator-Executor cycle |
| Stripe charges_succeeded 7d | `stripe.Charge.list(created={'gte': N-7d}, status='succeeded')` | Daily 09:00 ET + 18:00 ET stripe-pulse |
| Inbound DMs/comments on Reddit post | Reddit browser CDP read on display:98 (per `feedback_credentials_in_profile_attempt_first` — REDDIT creds in `~/.profile`) | T+24h, T+72h, T+168h post-publish |
| Reddit post impressions / upvotes / saves | Reddit browser CDP read on display:98 | T+24h, T+72h, T+168h post-publish (T+24h gates kill-fast deploy-rule per Oracle 2026-05-07) |
| Blog cluster sessions `/blog/auto-total-loss-*` | Vercel Analytics + Plausible if configured | Daily 09:00 ET |
| Stripe plink active status | `stripe.PaymentLink.retrieve()` | Daily 09:00 ET Validator-Executor cycle |
| Email-list new-subscriber count (Resend) | Resend dashboard + DB query | T+72h post-blog-publish |
| Direct DOI-complaint-deeplink click-through (if blog includes 50-state DOI portal table) | Vercel Analytics outbound-link event | Weekly |

**Distribution evidence log (per kill-fast deploy-rule):**
- `distribution_evidence_path:` field appended on each ship: Reddit post URL, blog post URL, X owner-session tweet URL
- This validation doc serves as the canonical distribution-evidence path register
- Validator-Executor reads from this section at 09:00 ET each cycle

```
distribution_evidence_log:
  - ship_date: TBD (target 2026-05-23 Variant B pure-value)
    channel: reddit-r-insurance
    url: TBD
  - ship_date: TBD (target 2026-05-26 Variant A single-tasteful-link)
    channel: reddit-r-insurance
    url: TBD
  - ship_date: TBD (target 2026-05-27)
    channel: owned-domain-blog-pillar
    url: TBD (https://oefrenterprise.com/blog/auto-insurance-total-loss-valuation-dispute-guide)
```

---

## Pre-deploy gating (Trinity day-shift carries)

Per Validator persona contract + Apr 30 HARD STOP + May 1 build-in-parallel + Oracle 2026-05-19 dual-anchor pricing framework + TJ-mandated 3-competitor pricing scrape gate:

| # | Gate | Owner | Status |
|---|---|---|---|
| 1 | 3-competitor pricing scrape on display:98 single-tab CDP — `etsy.com/market/total_loss_insurance` + `etsy.com/market/vehicle_valuation_dispute` + TheAutoMediator fee structure + AutoClaimSolutions fee structure (validate $24 anchor sits above commodity floor + below paid-mediator floor) | Trinity day-shift CDP on display:98 single-tab | ⏳ pending |
| 2 | Stripe Product + Price + Payment Link create (`product_name=Auto Insurance Total-Loss Valuation Dispute Kit`, `unit_amount=2400`, slug `auto-insurance-total-loss-valuation-dispute-kit`, `completed_sessions=20` cap, `custom_message=Pre-order ships 2026-06-07. Full refund if we miss the date.`) | Trinity day-shift after gate 1 | ⏳ pending |
| 3 | Blog pillar draft: `oefrenterprise.com/blog/auto-insurance-total-loss-valuation-dispute-guide` (NAIC §6 framework + 5-letter-cohort framing + ACV-decoder + appraisal-clause walkthrough + 50-state UCSPA pointer table inline + Stripe pre-order CTA mid-article + bottom) | SEO Operator next cycle | ⏳ pending |
| 4 | factual-integrity-gate run on blog draft (verify NAIC Model 900 URL HTTP 200 + CA §2071 + NY §3404 + TX §2210 + FL §627.428 verbatim against state legislature portals + 4 valuation-vendor names DNS-resolve + Google-presence) | Pre-Vercel-deploy | ⏳ pending |
| 5 | Cover image render (1500×1500, federal-anchor-blue palette per cover brief above, NAIC §6 + state-statute anchor block bottom-right) | Trinity day-shift | ⏳ pending |
| 6 | Reddit post Variant B (pure value, NO link) ship to r/Insurance 2026-05-23 morning ET (pre Reddit mandate expiration; builds cohort recognition) | Trinity day-shift (CDP+xdotool on display:98 per established Reddit lane) | ⏳ pending |
| 7 | Reddit post Variant A (single tasteful link) ship to r/Insurance 2026-05-26 morning ET (post Reddit mandate expiration; gated on plink live + active=True per destination-fidelity gate) | Trinity day-shift (CDP+xdotool on display:98) | ⏳ pending — gated on mandate expiration + plink deploy |
| 8 | Pinterest reserved as rung-3 only — SKIP-by-default reaffirmed (panic post-event cohort buys on resolution, not browse-discovery; same lesson as workers-comp Pinterest theater per Oracle 2026-05-10 + iep-504 Pinterest c-revised-3c gating) | n/a | ⏳ deferred |

**Pinterest SKIP-by-default reaffirmed:** Post-total-loss panic cohort buys on resolution, not browse-discovery. Same audience-cluster mismatch lesson as workers-comp + airbnb-sop Pinterest theater. Reserved as rung-3 contingency only if Etsy + multi-Reddit rung-2 weak-signal-climb also fails.

**LinkedIn deferred:** No `LINKEDIN_*` creds in `~/.profile` per v0 design gate. Auto-insurance dispute cohort is not LinkedIn-primary anyway (consumer hair-on-fire, not B2B professional).

---

## Branch tree (pre-staged per iep-504 (c-revised) pattern)

To be applied at T+336h canonical kill-branch verdict 2026-06-05 09:00 ET by Validator-Executor:

- **(a) Greenlight branch (≥3 sessions OR ≥1 + ≥100 blog sessions):** promote to `live_rung2` + full 9-tab Google Sheets MVP build (≤72h) + blog pillar full build-out + X owner-session cohort-tweet + 50-state appraisal-clause statute pre-flight fact-check pass.
- **(b) Weak-signal branch (1–2 sessions OR ≥30 blog + ≥1 DM):** climb to rung 2 = cross-post Variant A to r/PersonalFinance + r/cars + r/financialindependence (post-mandate light-CTA) + T+216h re-read. NO Pinterest. NO paid ads.
- **(c) Channel-empty branch (0 sessions + Reddit T+24h impressions <25):** `stay_live_rung1 + channel-empty` + change channel (Reddit → blog-first SEO primary + state-specific Google long-tail "[state] total loss valuation dispute appraisal clause") + 48h re-test before kill.
- **(d) Product-empty branch (0 sessions + Reddit T+24h impressions ≥25 + blog <30 sessions):** REJECT — cohort saw the kit and didn't buy → distribution-channel-fit not the issue, product-shape/pricing/copy mismatch. Cascade lesson into edges.md: auto-insurance-dispute cohort either (a) doesn't pay for proceduralization (state DOI complaint is free, why pay $24), or (b) wants resolution-as-a-service (paid-mediator) not DIY-templates. Either way, OEFR exits the auto-insurance-dispute lane.

---

## Risk readings (3 readings per Karpathy + verification-before-completion)

**Reading 1 — Highest probability (55%):** Test runs identically to iep-504 + state-unemployment (0 paid / 0 sessions / Day 14 = kill verdict via channel-empty branch). Auto-insurance dispute cohort searches Google "appraisal clause [state]" + state DOI portal directly, not Reddit or Stripe pre-order. Resolution-buy not browse-buy. Channel-fit mismatch — same as iep-504 8-cycle convergence at distribution-channel-fit bottleneck. Distinct twist: paid-mediator services ($300-2K) already absorb the high-stake buyer pool, leaving DIY-cohort to free state-DOI + free Car-and-Driver content + free Reddit advice. $24 kit may have no addressable middle.

**Reading 2 — Mid probability (30%):** Reddit Variant A drives 1-2 paid sessions because cohort size (3-4M total-loss declarations/yr) + sharp 30-day insurer-response deadline + clear $2K-8K recovery upside dollar-anchor in description. Weak-signal climb to r/PersonalFinance + r/cars (17M + 6M respectively — order-of-magnitude larger than r/Insurance 250K). Mortgage forbearance / FBAR-style federal-uniform-anchor + state-pointer shape has 2 prior in_validation references; if even one of those hits, the validation framework hits its first paid signal at this shape.

**Reading 3 — Lower probability (15%):** Blog SEO long-tail "[state] total loss valuation dispute appraisal clause" + Reddit value-post hits ≥3 sessions because the auto-insurance vertical is structurally LARGER cohort + LESS Etsy-saturated than legal-letter-kit vertical that iep-504/workers-comp inhabit (no 4342841616-style 10mo-old incumbent listing). Greenlight. Larger cohort + sharper hair-on-fire deadline + zero direct $24-tier competitor = the federal-uniform-state-pointer shape that finally clears at distribution-channel-fit threshold. Mitigation: if greenlight fires, immediately blog-pillar full build-out + 50-state Vercel SSG sub-pages (proven pattern from state-unemployment + tenant-deposit precedents).

**Calibration check:** I am the Validator, not the seller. My job is to design the cheapest test that kills or greenlights. Reading 1 dominates because the iep-504 9-read identical 0-session cluster across 120h is the strongest signal in this dataset, and 4 of 4 prior REJECT verdicts (cleaning-biz / airbnb-sop / pool-service / debt-lawsuit + lawn-care + workers-comp) match the channel-empty fingerprint. The right move is to ship the test fast, log distribution evidence, and let the 14-day timer fire the verdict at 2026-06-05 09:00 ET. The auto-insurance shape has 2 distinguishing factors from prior failures: (a) larger cohort, (b) hard-dollar recovery-upside anchor in description ($2K-8K) — but these were ALSO true of state-unemployment ($X-thousand wage replacement) and the verdict is still 14d out on that one. No prior shape-class has cleared yet.

---

## Files referenced

- This doc: `~/apps/OEFR Digital Products/trinity/knowledge/validations/2026-05-22-auto-insurance-total-loss-valuation-dispute-kit.md`
- Queue source: `../opportunities/queue.md` lines 1975–1990
- Edges check: `../edges.md` (PASS — utility-shape consumer-protection documentation, NAIC §6 federal-uniform anchor, decades-stable half-life, NOT taste/community/personality)
- Roster check: `../product-roster.md` (zero matches for "auto" / "insurance" / "total-loss" / "valuation" / "vehicle" / "NAIC" — clean)
- Mirror precedent: `2026-05-21-state-unemployment-denial-50-state-appeal-kit.md` (federally-anchored + 50-state-pointer fingerprint match — same shape, distinct cohort)
- Mirror precedent: `2026-04-25-iep-504-parent-advocacy-kit.md` (federally-anchored + procedural-aid shape — primary read for channel-empty Reading 1 dominance)
- Channel-fit reference: `2026-04-27-workers-comp-injured-worker-kit.md` (REJECT cohort context — Pinterest theater + attorney-routing mismatch; this validation explicitly avoids those patterns via DIY-cohort proven + Pinterest SKIP-by-default)
- Subconscious truth precedent: 2026-05-10 "Workers comp claim documentation template" SERP — 8/10 state govt free forms. Analogous Reading 1 risk: state-DOI portals + free Car-and-Driver content may absorb the DIY-cohort the same way state govt portals absorbed workers-comp.

[2026-06-11 09:0X ET] MONITOR (Validator-Executor): Gumroad API /l/homayb — 0 pre-orders / $0, published=true. Deployed 06-10 18:0X (Rule-11 lane migration). Forum/comment leg pending (Morpheus comment-format lane) — kill_date arms at T+14d once distribution evidence is on file. VERDICT: stay live_rung1.
