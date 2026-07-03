# Validation: Dog Walking / Pet Sitting Operator Ops Pack

**Opportunity ref:** `[2026-04-20] Dog walking / pet sitting operator ops pack`
**Date:** 2026-05-25
**Rung:** 1 (FREE)
**Status:** killed (kill_as_never_shipped — deploy-gate-never-cleared) 2026-06-09; prior: in_validation
**Kill date:** 2026-06-08

---

## Selection rationale

- First H/H/H-scored candidate in queue order (filed 2026-04-20, 35 days unvalidated)
- Gumroad channel gap: only 30 products for "dog walking business" — underserved vs 1,000+ Etsy listings
- Premium price tolerance validated: $35 for 211-page startup planner (337 reviews, listing 905127598)
- Dedicated subreddit: r/petsitting ~60K subs — cold-start community per edges.md good-fit
- Multi-community recurring operational asks: 5+ independent r/petsitting threads on contracts/forms/pricing over multiple years
- Google Sheets ops-tool slice under-represented: Etsy dominated by Canva bundles + PDF forms; scheduling/CRM/pricing calc in Sheets is our gap
- Edge fit: H/H/H — production speed, AI-native cost, Gumroad channel gap, cold-start community, year-round demand

**Pattern risk (acknowledged):** 4 consecutive sweaty-startup ops-pack rejections (cleaning-biz / airbnb-sop / pool-service / lawn-care). Early 2 used Gumroad pre-order and still failed (0 signups in 14d). However: (a) cleaning + airbnb Reddit/forum distribution never shipped (auth blocked at time), (b) pool + lawn used Stripe-direct not Gumroad, (c) Reddit is NOW live (long-game expired today), (d) r/petsitting is a tighter community (60K vs r/sweatystartup 300K — more targeted signal). This validation tests whether ops-pack mechanism works WITH functional Reddit distribution, which prior tests lacked.

---

## Gumroad Listing Copy

**Title (56 chars):** Dog Walking & Pet Sitting Ops Pack — 10 Google Sheets

**Subtitle:** Run your pet care business like a pro. Contracts, pricing, scheduling — ready to use.

**Price:** $19

**Description (~300 words, bullet-structured):**

You started a dog walking or pet sitting business because you love animals. Now you're drowning in paperwork — contracts you wrote on a napkin, pricing you're guessing at, and zero system for tracking which dog gets walked when.

This ops pack gives you 10 ready-to-use Google Sheets and PDF templates covering everything solo pet care operators actually need:

**What's inside:**

- Client intake & pet questionnaire (medical history, vet info, feeding schedule, behavioral notes, emergency contacts)
- Service agreement with cancellation + payment terms (protects you when a client cancels last-minute)
- Meet-and-greet checklist (what to assess before saying yes to a new client)
- Key release & home access authorization form (covers you legally when you're in someone's house)
- Vet release & emergency authorization (permission to seek emergency vet care if something goes wrong)
- Per-visit report template (what happened, how long, any notes for the owner)
- Pricing calculator with per-service matrix (walk / drop-in / overnight / extended stay, weekday vs weekend, holiday surcharges)
- Recurring client scheduler (weekly route + visit tracking)
- Mileage & expense log (tax-deductible tracking for driving between clients)
- Monthly P&L tracker (revenue - expenses = are you actually making money)

**Who this is for:**

- Solo dog walkers building their client base beyond Rover/Wag
- Pet sitters who want professional forms without hiring a lawyer
- Anyone transitioning from side-gig to real pet care business

**What this is NOT:**

- Not a Canva branding kit (no logos, no Instagram templates)
- Not a business plan template (this is operational, not theoretical)

Every template is Google Sheets or Google Docs. Copy to your Drive, fill in your info, start using immediately. No Canva account needed.

**Cover image brief:** Clean, professional design. White background. Bold dark text "Dog Walking & Pet Sitting Ops Pack" at top. Simple paw-print icon or leash icon in muted blue-green. Small "10 Google Sheets & Docs Templates" subtitle. No photos of dogs, no lifestyle imagery. Think professional-ops-kit aesthetic — functional, not cute.

---

## Forum Post Copy

**Target community:** r/petsitting (~60K members, dedicated pet care operator sub)

**Backup community:** r/dogwalkers (smaller, dedicated), then r/sweatystartup (larger, general trade)

**Post title:** The meet-and-greet checklist I wish I had before my first client — what to assess before saying yes

**Post body:**

I learned the hard way that saying yes to every client is how you end up with a dog that resource-guards around strangers, an owner who cancels 30 minutes before the walk, and zero paperwork protecting you if something goes wrong.

After a few rough experiences, I put together a meet-and-greet assessment checklist. Sharing it in case it helps anyone starting out:

**Before the meet-and-greet:**

1. Get the pet's vet info and vaccination records upfront. If they can't provide rabies/DHPP proof, that's your first red flag.
2. Ask about behavioral history in writing — reactivity, resource guarding, separation anxiety, history of biting. Owners downplay in person; written answers are harder to fudge.

**During the meet-and-greet:**

3. Watch how the dog reacts to YOU specifically — not just the owner handling them. You're the one walking this dog alone.
4. Test basic leash behavior. A dog that pulls you off your feet on a 10-minute test walk will do it every single visit.
5. Check the home access situation — lockbox, hidden key, smart lock. Get this in writing with a key release form. You're liable if something happens in their house.
6. Ask about other pets, other walkers, delivery schedules — anything that changes the environment when you're there.

**After the meet-and-greet:**

7. Send a written service agreement before the first visit. Cancellation policy, payment terms, emergency vet authorization. The owners who push back on a contract are the ones you need it most with.
8. Set your pricing BEFORE the conversation, not during. Have a rate card ready — per walk, per drop-in, per overnight, weekend/holiday surcharges. Negotiating on the spot always costs you money.

The biggest mistake I see new pet sitters make: treating it like a favor instead of a business. Professional forms aren't overkill — they're what separates "I walk dogs sometimes" from "I run a pet care business."

---

*I ended up building a full ops pack with all these templates (intake form, service agreement, key release, vet authorization, pricing calculator, scheduler, expense tracker — 10 total, Google Sheets/Docs). Link in my profile if anyone wants the complete set.*

---

## Kill / Greenlight Thresholds

| Metric | Kill | Partial (climb to rung 2) | Greenlight (build full pack) |
|--------|------|---------------------------|-------------------------------|
| Gumroad pre-order signups | 0 by 2026-06-08 | 1-4 by 2026-06-08 | >=5 by 2026-06-08 |
| Inbound DMs / comments asking for it | 0 by 2026-06-08 | n/a | Any 2+ "where can I get this" |
| Reddit post engagement (upvotes) | <3 upvotes | 3-10 upvotes | >10 upvotes (validates resonance) |

**Kill date:** 2026-06-08 (14 days from listing)
**Decision date:** 2026-06-09 (Day 15 — read metrics, make verdict)

If KILLED: append to queue.md Rejected table with evidence. 5th consecutive ops-pack rejection confirms systematic mechanism failure for trade-ops Gumroad pre-orders. Move on.
If PARTIAL (1-4 signups): evaluate rung-2 spend ($15 Reddit promoted post targeting r/petsitting, same landing page). This would be the first partial signal in ops-pack category — notable.
If GREENLIT (>=5): build full 10-template ops pack within 48 hours. Deploy to Gumroad. Cross-list on Etsy if Etsy session is live.

---

## Measurement Plan

| What to count | Where to look | How often |
|---------------|---------------|-----------|
| Gumroad pre-order page views | Gumroad dashboard analytics | Every 48h |
| Email signups / pre-order purchases | Gumroad notifications + dashboard | Every 48h |
| Reddit post upvotes + comments | Thread URL (log below) | Every 48h |
| "Where can I get this" DMs | Reddit inbox | Every 48h |
| Gumroad search impressions (if available) | Gumroad creator dashboard | Day 7 + Day 14 |

**Distribution evidence path:** (to be filled on execution)
- `gumroad_listing_url:` TBD
- `reddit_post_url:` TBD
- `reddit_post_date:` TBD (target: 2026-05-25 or 2026-05-26)
- `screenshot_path:` TBD

---

## Execution Sequence (Trinity day-shift)

1. **Create Gumroad listing** — title, subtitle, description per copy above. $19 price. Pre-order / coming-soon mode. Cover image placeholder (text-only acceptable for validation). Use Gumroad API or browser via `GUMROAD_ACCESS_TOKEN` in ~/.profile.
2. **Post to r/petsitting** — value-first post per copy above. Reddit long-game expired TODAY (2026-05-25). Post as new thread. Adapt tone to recent thread activity if needed. Use CDP+xdotool on display :98 or computer-use script (`REDDIT_USERNAME` + `REDDIT_PASSWORD` from ~/.profile).
3. **Screenshot + log** — capture Reddit post URL and Gumroad listing URL. Update `distribution_evidence_path` fields above.
4. **Set Day 7 check** — 2026-06-01 read metrics.
5. **Set Day 14 verdict** — 2026-06-08 final read, make kill/partial/greenlight call.

**Reddit channel note:** This is the FIRST ops-pack validation with functional Reddit distribution. Prior rejections (cleaning-biz, airbnb-sop) had Reddit auth blocked during their test windows. r/petsitting is a tighter, more operator-focused community than r/sweatystartup (used in prior failed tests). If this test also fails with working Reddit distribution, it's strong evidence that trade-ops Gumroad pre-orders are a dead mechanism regardless of channel.

---

## Risk Notes

1. **4-rejection pattern:** If this test fails, ops-pack category should be globally deprioritized in the queue. Signal to opportunity-scout to stop scoring new trade-ops-packs as H.
2. **Gumroad pre-order vs Stripe:** This test uses Gumroad (per persona contract), not Stripe-direct (per Apr 30 HARD STOP). First Gumroad pre-order test since cleaning-biz (Apr 16) — mechanism has been untested for 39 days while Stripe-direct variants accumulated 4 additional rejections.
3. **r/petsitting moderation:** Check sub rules before posting. Some subs prohibit commercial mentions even in profile-linked form. If r/petsitting blocks, fallback to r/dogwalkers then r/sweatystartup.
4. **Overlap with queued mobile-pet-grooming pack (Apr 29):** Different operator (walker vs groomer), different forms (leash/key release vs safety/matting release), different sub (r/petsitting vs r/doggrooming). Minimal cannibalization. But if dog-walking fails, grooming ops pack should also be deprioritized.

## Kill verdict — kill_as_never_shipped (deploy-gate-never-cleared)
- **Date**: 2026-06-09 (Validator-Executor 09:00 ET cycle)
- **Authority**: CEO-PLAYBOOK Rule 11 + Oracle 07:00 06-09 demand-tier limbo drain. Tier-C SKU: never deployed (no Live section, empty distribution_evidence_path), 14d+ past own kill_date, deploy gate (pricing-scrape / content-QA / URL-audit) never cleared.
- **Edge rationale**: low-WTP ops-pack family (cleaning/airbnb/pool/lawn all killed); non-edge
- **Verdict**: kill_as_never_shipped. This is DISTINCT from a live_rung1→rejected kill — the SKU forfeits ~0 option value (pre-deploy, zero sunk distribution, edges-vetoed pool). Resolves the validation-limbo deadlock per monitor.
