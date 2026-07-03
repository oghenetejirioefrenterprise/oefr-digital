# Validation — Senior Parent Downsizing / 8-Week Move Logistics Kit

- **Opportunity**: [2026-04-28] Senior parent downsizing / household-disposition 8-week move logistics kit (life-event admin, NOT decluttering aesthetic) — queue.md
- **Date opened**: 2026-04-28
- **Validator**: Trinity (validator-loop)
- **Rung**: 1 (FREE — Stripe pre-order link primary; r/AgingParents value-first comment when Reddit auth unwedges; FB-group fallback path documented)
- **Status**: killed (kill_as_never_shipped — deploy-gate-never-cleared) 2026-06-09; prior: designed (Stripe deploy + forum post pending validator-executor next cycle; Reddit ship gated by 15+ cycle Reddit auth wedge — FB-fallback path baked in)
- **Stripe Payment Link**: TBD by validator-executor at deploy
- **Deploy timestamp (UTC)**: TBD
- **Kill date**: 2026-05-12 (14 days from today)
- **Greenlight threshold (persona-contract strict)**: ≥5 Stripe completed sessions by 2026-05-12 → build MVP immediately
- **Weak-signal threshold**: 1–4 sessions OR ≥1 session + ≥3 substantive inbound DMs/comments asking "when is this ready" → climb to rung 2 ($15 Pinterest pin or Reddit promoted post once auth unwedges)
- **Kill threshold**: 0 sessions AND 0 inbound DMs by 2026-05-12 → reject, log cause, archive

## Why this opportunity passed the validator gate

1. **Edge fit passes (cleanest on queue this cycle)** — production speed (24-36h MVP: 8-week timeline + 30+ federal address-change checklist + decision matrix + Google Sheets + PDF), AI-native cost (LLM drafts checklists + state-pointer index at near-zero marginal cost), programmatic SEO (long-tail "how to help aging parent downsize 8 week checklist 2026" + "senior parent move address change checklist"), volume play (~10K Americans/day turn 65 + 30%+ of 65+ households move within 5 years post-65), evergreen + counter-cyclical (sustained regardless of housing-market direction), federal-uniform admin slice (USPS COA / SSA / Medicare / VA / IRS — federal forms-first, NOT 50-state procedural variance), zero community/brand/taste/personality/sales-motion requirement (logistics, NOT "spark joy" decluttering aesthetic). NO disqualifying half-edge — opportunity-scout 20:09 Apr 27 explicitly ranked this #1 on "cleanest edge-fit" of the 3-opportunity Apr 28 batch.
2. **Roster clean** — `grep -i "downsiz\|aging.parent.move\|household.disposition\|senior.relocat"` on `product-roster.md` returns zero hits. No prior repeat-failure on this slice. Closest adjacent: dead `meal-planner` (lifestyle niche, different form-factor, different buyer pain) and active `etsy-spreadsheets` producing line (different SKU set, no senior-downsizing entry).
3. **5+ demand signals confirmed (≥3 threshold passed)** in queue entry:
   - **5-bucket Etsy primary category indexed** — `/market/downsizing_for_seniors_checklist` + `/market/senior_downsizing_checklist_template` + `/market/senior_downsizing_guide` + `/market/downsizing_checklist_template` + active dedicated listing 4484299857 ("Aging Parent Move Transition Planner Checklist — 8-Week Guide") confirms search-engine-level category-validation + 8-week-timeline form-factor.
   - **Multi-sub Reddit recurring buying-intent (5 distinct threads, ≥3 distinct subs, multi-year recurring)** — r/declutter `17tbsm9` "Trying to help elderly parents downsize and move across the country" + r/AgingParents `1e1fxjq` "My aging parents need help letting go of 'stuff'" + r/AgingParents `1i56jl7` "to move home or manage aging parents' needs long distance" + r/eldercare `1ql4g7o` "Elderly parents are downsizing — where do they go?" + r/AgingParents `hm1nzs` "Parents won't downsize house?". Five threads, three subs, multi-year recurring = explicit unmet demand verbalized in buyer's own words.
   - **Gumroad channel gap is EXTREME** — `gumroad.com/discover?query=senior+downsizing` returns **only 1 product**. Cleanest channel-gap profile on queue this week alongside chimney-sweep (0) / HOA (0) / USAJOBS (0). Same channel-gap profile that put cleaning-biz / debt-lawsuit / workers-comp into rung-1.
   - **Volume × demographic tailwind structurally durable** — ~10K Americans turn 65 every day (SSA actuarial); 65+ population doubling to ~95M by 2060 (Census); Sandwich Generation ~11M caregivers (Pew). Sustained 20+-year tailwind, not a one-cycle window.
   - **Adjacent-axis triple-validation** — three independent slices on the same demographic axis already passed evidence + edge-fit gates: estate-sale operator (Apr 27 #1-ranked) + aging-parent-caregiver organizer (Apr 22 H/H/H) + this entry. Three independent evidence stacks confirm the demographic-axis is a real ongoing buying pool, not a one-cycle anomaly.
4. **No cannibalization with adjacent slices** — distinct from [2026-04-22 sandwich-gen aging-parent caregiver organizer] which is the LIFECYCLE daily-management slice (medication log, ER-ready sheet, fall audit, Medicare). This is the ACUTE 60-90 day MOVE-EVENT slice. Family-side companion to [2026-04-27 estate-sale operator pack] which is the operator running the sale. Same 3-slice demographic-axis pattern that lets debt-lawsuit (defendant) + medical-bill-negotiation (patient) coexist without cannibalization.
5. **Federal-uniform anchor + state-pointer where required = no 50-state liability** — USPS Change-of-Address (COA) is federal. SSA address change is federal. Medicare address change is federal. VA address change is federal. IRS address change (Form 8822) is federal. Same scope-narrowing pattern that protects IEP-504 / VA-disability / workers-comp / lemon-law / newcomer-USA. Where state-pointer is needed (DMV, voter registration, state-Medicaid, utility-disconnect, state estate-sale rules), kit POINTS to state agency lookup tools — does NOT generate state forms.
6. **Hair-on-fire moments stacked** — moving day medication / paperwork / immediate-need go-bag (ACUTE 24h window), USPS mail-forward window (12-day setup before move-day for full forwarding), utility disconnect/reconnect timing (overlap-by-1-day rule to avoid empty-house theft), post-move 30-day setup (new doctor transfer, new pharmacy, fall-audit at new home — fall-risk window peaks first 30 days post-move per CDC). Recurring deadline-panic, not one-shot.

## Rung 1 — Stripe pre-order listing (primary deploy channel per persona contract)

### Listing metadata

- **Price**: $22.00 (pre-order). Sits inside the consumer life-event admin kit band ($19–24 per IEP-504 + debt-lawsuit + foster-parent + workers-comp + Medicaid-LTC anchors). Anchored above the $9-15 commodity Etsy floor (where most senior-downsizing checklists currently sit) and below the elder-law / move-management consult tier ($300-500/hr Senior Move Manager + ~$2K-7K full-service NASMM-network move). Buyer-anchor argument when comp-pricing is questioned: "Senior Move Managers charge $300-500/hr to do this; the $9 Etsy checklist is missing the federal-agency master list and the 8-week timeline integration. This is the documentation-organization the SMM uses, structured for the family."
- **Fulfillment date in description**: 2026-05-28 (30 days from today; honors refund window if we kill on 2026-05-12).
- **Slug**: `senior-parent-downsizing-move-logistics-kit`
- **Stripe product name**: `Aging Parent Move Logistics Kit (8-Week Timeline)`
- **Completed-sessions cap**: 20 (self-caps on validation; urgency signal in checkout meta — same cap pattern as IEP-504, debt-lawsuit, workers-comp).
- **URL target post-deploy**: `https://buy.stripe.com/<TBD>` — link added to monitoring log on deploy.
- **Tags (Gumroad mirror, post-greenlight)**: `aging parent`, `senior downsizing`, `move logistics`, `address change checklist`, `USPS change of address`, `8 week timeline`, `assisted living move`, `eldercare`, `downsizing checklist`, `family move planner`.

### Title (60 chars max)

```
Aging Parent Move Logistics Kit (8-Week Timeline)
```
(50 chars — fits under cap.)

### Subtitle

```
For adult children helping a parent downsize and move. 8-week countdown, 30+ federal address-change checklists, room-by-room decision matrix, moving-day go-bag, post-move 30-day setup. Documentation-only. Spend-down strategy and estate planning excluded.
```

### Description (~300 words, bullet-structured, concrete)

```
You're trying to coordinate eight weeks of admin while sitting in your parent's living room arguing about which dining table goes to your sister.

The doctor wants the medication list re-routed to a new pharmacy. USPS mail forwarding has a 12-day lead time the post-office clerk didn't mention. Medicare doesn't auto-update from USPS. SSA wants a separate change. The DMV is a different rule per state. The estate sale company wants the inventory tabbed three different ways.

This kit is the move-event documentation system, structured for the family.

It is documentation-organization ONLY — it does not generate spend-down strategy, estate-planning trusts, Medicaid-lookback documentation, or sale contracts. Where state-specific forms are required (DMV, voter registration, utilities, state-Medicaid), the kit POINTS to the right agency lookup tool. For NASMM Senior Move Manager referral, the kit links the directory.

What's inside (Google Sheets + PDF, 30+ tools):

• 8-Week Timeline Master — week-by-week task list, drop-dead dates, owner-of-task column for split-family-coordination
• Federal Address-Change Master List — USPS COA, SSA, Medicare, VA, IRS Form 8822, banks, brokerage, insurance, prescription pharmacy, doctor offices (with form numbers + filing windows)
• State-Pointer Index — DMV, voter registration, state-Medicaid, utility-disconnect rules (links to state agency lookup, not 50-state form generation)
• Room-by-Room Inventory + Decision Matrix — keep / gift-to-family / sell / donate / archive-photo, per item
• Family-Heirloom Decision Sheet — split-family coordination column, "claim or release" deadline column
• Estate-Sale-vs-Auction-vs-Charity Decision Tree
• Moving-Company Quote-Comparison Sheet — apples-to-apples on packing / hourly / valuation / mileage
• Utility Disconnect & Reconnect Schedule — overlap-by-1-day rule documented to avoid empty-house theft window
• Mail-Forward Window Calculator (12-day USPS lead time)
• Moving-Day Go-Bag Checklist — medications, paperwork, immediate-need, 72-hour kit
• Post-Move 30-Day Setup — new doctor transfer, new pharmacy, fall-audit at new home (CDC fall-risk peaks first 30 days post-move)
• New-Address Family-Contact Update Tracker

Pre-order ships 2026-05-28. Refunds available before fulfillment.
```

### Cover image brief (for designer / codex image_gen)

- **Composition**: 3-device composite (laptop screen + tablet on stand + printed timeline poster), staged on a paper-textured tan/cream desktop in OEFR Paper-and-Ink palette (Paper #f4efe6 background, Ink #1a1713 type, Accent #a66a2c rule).
- **Laptop screen**: Google Sheet "8-Week Timeline Master" with W-1 / W-2 / ... / W-8 column headers, ~12 example tasks visible (USPS COA file by W-3; SSA address change W-3; Medicare update W-2; mover quotes due W-5; estate-sale operator booked W-4; etc.), with a faded teal-green "✓ DONE" highlight on completed cells to make the document feel actively used.
- **Tablet screen**: PDF "Federal Address-Change Master List" with the 5 federal agencies tabbed at top (USPS / SSA / Medicare / VA / IRS) and a check-list scroll showing form-numbers and filing-windows.
- **Printed poster**: 8-week countdown wall poster (W-8 → W-1 → MOVE DAY → W+1 → W+4 setup), hand-drawn vibe in Fraunces serif headlines + Inter sans body, dated for a sample move on 2026-06-15.
- **Editorial typography**: title in Fraunces serif: "Aging Parent Move Logistics Kit"; sub in Inter: "8-Week Timeline · Federal Address-Change Master · 30+ Tools · Family-Side Admin"; small-cap rule "OEFR DIGITAL · 2026". No stock-photo elderly-couple-holding-hands clichés. No sparkle / no gradient backgrounds / no AI-rendered humans.
- **Anti-slop guards (per oefr-design ref)**: NO faux-3D mockup with auto-generated reflection, NO purple-pink gradient, NO stock-rotated-pills imagery. Print + paper texture + actual-Sheets-cells = "this exists and someone uses it."

## Rung 1 — Forum post (cold-start community probe)

### Target community + thread

**Primary**: r/AgingParents — comment on existing thread `1e1fxjq` ("My aging parents need help letting go of 'stuff'") OR `hm1nzs` ("Parents won't downsize house?") OR top weekly thread on AgingParents at ship time. Reddit auth currently wedged 15+ cluster cycles per HANDOFF.md — ship blocked until either (a) TJ adds REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET to ~/.profile per HANDOFF.md, or (b) Trinity Tier-C CDP-browser fallback ships per nightly self-improvement Apr 27.

**Secondary (if Reddit stays wedged 7+ days)**: r/declutter — comment on `17tbsm9` ("Trying to help elderly parents downsize and move across the country"). Lower buying-intent density than r/AgingParents but same-axis demand-stack confirmed in queue evidence.

**FB-fallback (if Reddit stays wedged 14 days = full kill window)**: a non-pitchy value comment in 1-2 of the AgingParents / eldercare-focused FB groups already in the OEFR ship-targets list (groups confirmed accessible per Apr 28 cleaning-biz ship pattern). Same value-first format with offer mentioned once at the end. FB-fallback was the path that successfully shipped cleaning-biz v2 today (08:00 ET) when Reddit stayed wedged.

### Post title

```
Federal address-change checklist for moving an aging parent — the agency-by-agency order USPS / SSA / Medicare / VA / IRS that adult kids consistently miss
```

### Post body (genuinely useful — solves a real problem; one tasteful offer mention at the end)

```
Coordinating an aging parent's move means changing addresses across more agencies than most adult kids realize, and several of them do NOT auto-sync from USPS. Reviewed the federal-agency address-change procedures across r/AgingParents, r/eldercare, USPS / SSA / Medicare / VA / IRS official guidance, and benefits-counselor forum threads to compile the order most adult kids miss on day one. Nothing here is legal advice — just the federal-agency-published order with timing windows that the federal sites themselves publish.

USPS Change-of-Address (COA) — file at least 2 weeks before the move (per usps.com/manage/forward.htm: 7–12 business days processing). The "next-day" framing is only for advertising mail; full forwarding takes the full 7–12 business days, and Medicare / SSA / IRS will NOT honor a USPS-only forward.

Social Security Administration — separate change. Online via my Social Security if the parent has an account; otherwise call 1-800-772-1213 or visit a local SSA office. SSA will NOT update Medicare automatically (different system).

Medicare — separate change again. medicare.gov "Change my address" link or 1-800-MEDICARE. Critical because EOBs and benefit notices route here, and a missed denial-letter window can torch an appeal right.

VA (if applicable) — VA.gov address change tool, or call 1-800-827-1000. Disability comp and pension payments route by VA address, not SSA address.

IRS — Form 8822 (Change of Address). Mail to the IRS address listed on the form for the parent's filing state. Not strictly time-sensitive, but if there's an estimated-tax payment owed, miss this and the notice goes to the old address.

Other federal-uniform-but-easy-to-miss: Veterans-pension direct deposit, TSP if a federal retiree, OPM annuity, USPS bond mailings. State-side, DMV / voter registration / state-Medicaid / utilities all have their own rules and timelines — best to check the specific state's USA.gov state-services page rather than assuming.

A few often-missed details surfaced repeatedly in r/AgingParents and r/eldercare threads on cross-state senior moves:

• Direct-deposit destinations don't change automatically when an address changes. SSA, VA, OPM, and pension payers track address and direct-deposit as two separate fields. Both need updating.

• Pharmacy address changes need TWO updates: pharmacy-of-record AND each individual prescription's mail-order address (some pharmacies key by prescription, not by patient).

• Medicare-Advantage / Part-D plans may be tied to the OLD ZIP code's network. If the move crosses a county or state line, the parent may need a Special Enrollment Period before the next Annual Enrollment Period to keep coverage continuous.

Additions or corrections from anyone who has run this checklist on a real move would strengthen future versions — community-sourced refinement is the goal here.

(For full transparency: OEFR Digital is putting together a more complete documentation kit that collects all of this plus the room-by-room decision matrix, moving-day go-bag, mover quote-comparison sheet, and a post-move 30-day setup checklist. Pre-order link in first comment if helpful — totally optional, the checklist above is the genuinely-useful part regardless.)
```

**Length**: ~470 words. Density-justified (12 federal-agency facts + 3 things-that-bit-me + value-first community pattern + single soft CTA at end).

**Voice check (per COMPANY_VALUES.md)**: operator-direct ("nothing here is legal advice, just the order I learned the hard way"), no influencer-sparkle, no trash-talking unnamed competitors, no "transform your life" framing. Anti-pattern flags audited: zero defensive-tone words, zero fabricated-precision (each timeline window is sourced to a federal agency the reader can verify), single CTA earned via density-first per persona rule.

## Pre-ship Content QA gate (mandatory before forum post)

Before either Stripe-deploy or forum-ship, the following phantom-audit and accuracy gate must pass — same gate baked into Apr 26+ ship scripts after 11+ fabricated-precision flags in 13 days:

1. **Federal-form-number audit** — verify each cited form-number / phone-number / agency-link is currently live (Form 8822 IRS / SSA 1-800-772-1213 / Medicare 1-800-MEDICARE / VA 1-800-827-1000 / medicare.gov change-address page). Spot-check 3 of 5 with HEAD curl pre-ship.
2. **Timeline-window claim audit** — "USPS COA 12 days before move" is the official USPS recommendation per usps.com/manage/forward.htm. "Medicare-Advantage cross-county SEP" verify per medicare.gov SEP rules page. Source-link every numeric claim or remove the number.
3. **Phantom-claim regex audit** — strip any "automatically pulls from", "syncs with", "auto-updates" phrasing where the kit does not literally automate the agency call. Documentation-organization ONLY framing — same regex gate that caught the Apr 27 Pin 4 "Names pull from the Guest List tab automatically" hard-fail.
4. **Scope-exclusion clarity audit** — explicit disclaimer at top of Stripe description and forum post that this kit is documentation-organization, NOT spend-down strategy / estate-planning trusts / Medicaid-lookback (those slices have their own queue entries) / sale contracts / state-specific form generation.
5. **No-discount audit** — pre-order is at standard $22 with no countdown, no "limited time", no SALE asterisk, no defensive trash-talk on free-checklist alternatives. Stack-bonus framing only ("includes the federal address-change master list as a free pre-order bonus" — the master list is part of the kit, not a separate giveaway).

## Kill / Greenlight thresholds (specific numbers, specific dates)

| Metric | Threshold | Action |
|---|---|---|
| **Greenlight (persona-strict)** | ≥5 Stripe completed sessions by 2026-05-12 | Build full MVP within 48 hours of greenlight. Refund-honor ship 2026-05-28. |
| **Weak partial** | 1–4 sessions OR ≥1 session + ≥3 substantive inbound DMs/comments asking "when ready" | Climb to rung 2: $15 Pinterest pin OR Reddit promoted post (gated on auth unwedge) targeting r/AgingParents demographic. New 14-day window. |
| **Kill** | 0 sessions AND 0 inbound DMs/comments by 2026-05-12 | Reject. Append rejection row to queue.md Rejected table with cause. Archive validation doc. Do not build. |
| **Forum signal proxy** (independent of Stripe) | ≥10 net-positive upvotes on the comment + ≥2 substantive replies (not "thanks") | Counts toward weak-partial threshold even at 0 Stripe sessions — community-trust signal precedes purchase intent in cold-start subs. |

## Measurement plan (what to count, where, how often)

- **Stripe metrics** (validator-executor cycle, 09:00 / 13:00 / 18:00 / 22:00 ET daily):
  - `payment_link.list` → confirm link `active=true`, daily 200 OK on link URL
  - `checkout.session.list` → count `status=complete` sessions; track `status=expired` for funnel-leak diagnostic
  - `customer.list` → email-capture flag (each completed session = qualified email)
- **Forum metrics** (Trinity main session, daily ~10 min when Reddit auth unwedges; FB-fallback daily check ~5 min if cleaning-biz pattern):
  - Post upvotes (target: ≥10 net-positive in 14d for cold-start community signal)
  - Top-level replies that are substantive (not "thanks", not auto-mod)
  - Inbound DMs asking "when is this ready" / "what does it include"
- **Reporting cadence** — append a daily monitoring row to this validation doc:
  ```
  | YYYY-MM-DD HH:MM ET | day N/14 | sessions: X paid, Y expired | upvotes: Z | DMs: W | state: live_rung1 / weak_partial / killed | notes: ... |
  ```
- **Decision trigger dates**:
  - **2026-04-29** — Stripe link deploy target (validator-executor next cycle)
  - **2026-05-05** — Mid-validation 7-day check (1/2 window). If 0 sessions + 0 DMs + 0 upvote signal, audit copy / target / ship channel. If Reddit still wedged 7d, escalate FB-fallback ship.
  - **2026-05-12** — Kill / greenlight verdict by EOD ET. Default verdict = REJECT if no positive signal accumulated.

## Risks / known gaps

1. **Reddit auth wedge unresolved 15+ cycles** — primary channel for buying-intent surface remains gated. Mitigations: FB-fallback (proven on cleaning-biz Apr 28), r/declutter secondary thread, Trinity Tier-C CDP-browser fallback per Apr 27 nightly self-improvement.
2. **No 5K-10K-review aesthetic moat veto, but Etsy 8-week-timeline listing 4484299857 already active** — minor competitor risk on the timeline form-factor specifically. Mitigation: our kit is Sheets-first + federal-master-list-anchored + family-coordination-column, distinct from PDF-only printable aesthetic checklists.
3. **Senior Move Manager (NASMM) referral natural-destination overhead** — some buyers will hire a $300-500/hr SMM instead of buying a $22 organizer. Mitigation: position as the PRE-SMM documentation organizer that saves SMM billable-hours (same value-prop pattern that worked for workers-comp pre-attorney organization framing). Our kit also LINKS the NASMM directory in scope — we are NOT trying to be the SMM, we are the family's pre-SMM and during-SMM checklist.
4. **Emotional-load buyer state** — buyer is mid-life-event-stress with parent. Refund vector higher than $22 wedding-budget if buyer feels the kit "isn't enough" during emotional move-week. Mitigation: explicit scope-exclusion at top of description (no spend-down / no estate-planning / no Medicaid lookback / no sale contracts), 30-day refund window, no countdown timer / no urgency manipulation.
5. **Kit accuracy is the trust gate** — Apr 27 Pin 4 fabricated-precision (auto-pull formula claim) and 12+ similar flags in 13 days mean Content QA pre-ship audit on every federal-form-number / timeline-window / phone-number is mandatory. `wiki.py lint-product-spec v1` (Ops carry, ~50h overdue) would automate this; until shipped, manual gate per Pre-ship Content QA section above.
6. **Reddit wedge cascade risk** — if FB-fallback also gets wedged (admin approval queue + member-status restrictions), validation has zero ship channel. Mitigation: 7-day mid-validation audit explicitly checks for ship-channel availability, escalates Tier-C CDP-browser auth fallback if both Reddit and FB are degraded.

## Monitoring log

| YYYY-MM-DD HH:MM | day N/14 | sessions (paid/expired) | upvotes | DMs | state | notes |
|---|---|---|---|---|---|---|
| 2026-04-28 11:30 ET | 0/14 | — | — | — | designed | Validation doc shipped. Stripe deploy + forum post pending validator-executor next cycle (Reddit ship gated by 15+ cycle auth wedge — FB-fallback path documented). |

## Kill verdict — kill_as_never_shipped (deploy-gate-never-cleared)
- **Date**: 2026-06-09 (Validator-Executor 09:00 ET cycle)
- **Authority**: CEO-PLAYBOOK Rule 11 + Oracle 07:00 06-09 demand-tier limbo drain. Tier-C SKU: never deployed (no Live section, empty distribution_evidence_path), 14d+ past own kill_date, deploy gate (pricing-scrape / content-QA / URL-audit) never cleared.
- **Edge rationale**: low-WTP lifestyle non-edge; deploy gate (Reddit auth/FB) never cleared 40d+
- **Verdict**: kill_as_never_shipped. This is DISTINCT from a live_rung1→rejected kill — the SKU forfeits ~0 option value (pre-deploy, zero sunk distribution, edges-vetoed pool). Resolves the validation-limbo deadlock per monitor.
