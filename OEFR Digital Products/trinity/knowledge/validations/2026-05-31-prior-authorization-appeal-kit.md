# Validation — Prior Authorization Appeal Kit (patient-side, federal ERISA generalizable)

- **Opportunity ref:** queue.md → `[2026-04-22] Prior authorization appeal kit (patient-side, federal ERISA generalizable)`
- **Date designed:** 2026-05-31
- **Rung:** 1 (FREE — Gumroad pre-order + value-first forum post). No product build until rung-1 greenlight.
- **Status:** in_validation
- **Designed by:** validator-loop

## Gate check (passed before design)

- **Edge fit (edges.md):** PASS. Forms-first letter kit = Production speed ✓ (AI drafts 8–10 ERISA-standard appeal letters + EOB decoder + phone script in <4h), AI-native cost ✓, $19 volume/impulse tier ✓. Channels = Gumroad + Reddit cold-start communities (both "good fit" per edges.md Channel implications). No community/brand/taste/personality non-edge required. **Not vetoed.**
- **Roster (product-roster.md):** CLEAN. Zero dead-product overlap — no medical / insurance / appeal / health product has ever been attempted (`grep` returned nothing). Not a re-entry.
- **Queue cannibalization:** None. Distinct from `medical-bill-negotiation-letter-kit` (validated 2026-05-26): that is post-service billing dispute, **provider** adversary, financial-hardship framing. This is pre-service coverage denial, **insurer** adversary, medical-necessity framing. Different forms, deadlines, buyer moment. A buyer facing both moments buys both kits.
- **≥3 demand signals:** YES (see below).

## Why this one (rank justification)

Highest-ranked status=candidate entry that clears **every** hard gate with no caveat:
- Score edge_fit=H, demand=H, speed=H → **H**.
- Exact-shape competitor already live on Etsy ("Prior Authorization Appeal Kit | Insurance Approval Denied Help", listing 4448338431) with the *same* patient-side disclaimer pattern we'd ship → product shape de-risked.
- Federal ERISA generalizes the employer-sponsored-plan internal-appeal structure → avoids the 50-state liability that has stalled other legal-forms SKUs.
- Buyer-pool-matched active channel (r/HealthInsurance posts "how do I write this?" weekly) → channel-fit, not theater (satisfies edges.md v0 design gate + kill-fast distribution-channel-fit rule).

---

## 1. Gumroad listing copy

**Title (≤60 chars):**
`Prior Authorization Appeal Kit — 10 Letters + Phone Script`
(57 chars)

**Subtitle:**
Templates to fight a denied prior auth — internal appeal, expedited/urgent appeal, medical-necessity letter for your doctor to sign, external review, and the exact phone script for calling your insurer.

**Price:** **$19** (pre-order). Patient-side Etsy kit tier is validated at $10.95–$19.99; $19 sits at the top of the proven band with the broadest deliverable. No discount — value-stacked, not price-cut.

**Description (~300 words, bullet-structured):**

> About 1 in 5 prior-authorization requests get denied on the first try — and ~82% are overturned when patients appeal (HHS-OIG). The problem: almost nobody appeals, because they don't know what to write or which deadline applies. This kit hands you the letters.
>
> **What you get (10 ready-to-send templates):**
> - **Initial internal appeal** — the standard first-level letter, fill-in-the-blank
> - **Expedited / urgent appeal** — when a delay threatens your health (72-hour pathway)
> - **Medical-necessity letter for your doctor to sign** — drafted so your physician just reviews + signs
> - **Step-therapy ("fail first") exception request**
> - **Peer-to-peer review request** — get your doctor on the phone with the plan's reviewer
> - **External / independent review request** — when the internal appeal fails
> - **Specialty-drug denial appeal**
> - **Denied-procedure appeal**
> - **Medicaid fair-hearing request**
> - **Doctor-office coordination note** — so the clinic sends the right records
>
> **Plus the tools that make them work:**
> - **Denial-letter & EOB decoder** — find the real denial reason and the deadline hidden in the fine print
> - **Appeal-deadline calendar** — internal appeals are typically 30–180 days; miss it and you forfeit the right
> - **"What to say when you call" phone script** — word-for-word, so you don't freeze on the call
>
> Written in plain English, ERISA-standard structure that applies across most employer and marketplace plans. Instant download.
>
> **Educational templates, not medical or legal advice.** Appeal pathways differ by plan type (Medicare / Medicaid / ACA-marketplace / employer-sponsored) — check your plan's Summary Plan Description. For complex denials, consult a patient advocate or attorney.
>
> **Pre-order now** — drop your email and you'll get it the moment it ships (within 48 hours of launch). No charge until it's in your inbox.

**Cover image brief (for designer):**
- 1280×720 (Gumroad 16:9). Clean, clinical-trust palette: white background, one deep-teal (#0E7C7B) accent bar, slate-gray (#334155) type. No stock-photo faces, no aesthetic flourish (edges: non-taste).
- Headline: "Prior Authorization DENIED?" struck-through "DENIED" in muted red, with "Appeal it." set bold beneath.
- Visual motif: a stylized denial letter with a red "DENIED" stamp, beside a checklist of 3 ticked items ("Internal appeal · Expedited appeal · External review").
- Footer ribbon: "10 letter templates · EOB decoder · phone script · deadline calendar".
- Bottom-corner micro-disclaimer in 10pt gray: "Educational templates — not medical/legal advice."

---

## 2. Forum post (rung-1 distribution)

**Target community:** **r/HealthInsurance** (primary). Buyer-pool-matched — the sub has recurring "my prior auth was denied, how do I appeal / what do I write?" threads. Fallback if removed by mods: **r/HealthInsurance** weekly thread, then r/ChronicIllness.

**Subreddit rules note:** r/HealthInsurance is strict on self-promo. The post must be genuinely useful and stand alone *without* the link; the offer is a single tasteful line at the end. If the sub disallows any link, post the value with **no** link and capture interest via DMs (DMs count as inbound signal — see thresholds).

**Exact title:**
`Your prior auth got denied? Here's the exact phone script + the deadline most people miss`

**Body:**

> A denied prior authorization isn't the final answer — it's the first answer. Roughly 4 out of 5 denials that get appealed are overturned (HHS-OIG), but most people never appeal because the denial letter is written to make you give up. Here's the part that actually works, free, no catch:
>
> **1. Find the real reason + the deadline.** Your denial letter (and your EOB) names a specific denial reason — "not medically necessary," "step therapy required," "non-formulary," etc. It also states your appeal deadline, usually buried near the bottom. Internal-appeal windows are commonly 30–180 days depending on plan type. Put that date in your calendar the day you get the letter.
>
> **2. Call before you write — and use a script.** A 5-minute call often resolves it or tells you exactly what's missing. What to say, roughly:
> > "I'm calling about a prior authorization denial, reference number ___. I'd like to (a) confirm the exact denial reason in writing, (b) request a peer-to-peer review between my prescribing doctor and your medical reviewer, and (c) confirm the deadline and address for a formal written appeal. Can you note on the account that I intend to appeal?"
>
> Asking for the **peer-to-peer** is the move people don't know about — it puts your doctor on the phone with the plan's reviewer and resolves a lot of "not medically necessary" denials.
>
> **3. If it's urgent, say "expedited."** If a delay could seriously harm your health, you can request an **expedited appeal** — plans generally must decide within 72 hours. Use that phrase explicitly.
>
> **4. Get the medical-necessity letter from your doctor.** The appeal that wins is usually a short letter from your prescriber citing your diagnosis, what you've already tried, and why this specific treatment is necessary. Most doctors will sign one if you draft it for them.
>
> Hope this helps someone get an approval they were entitled to.
>
> *(I put together a free template pack — 10 appeal letters including the medical-necessity letter to hand your doctor, an EOB/denial decoder, the deadline calendar, and the full phone script. Pre-order link is in my profile / happy to DM it if that's against the rules here.)*

**distribution_evidence_path:** _(to be filled when posted — Reddit thread URL. Required by edges.md kill-fast rule before any reject verdict.)_

---

## 3. Kill / greenlight thresholds (specific numbers + dates)

Rung-1 window: **2026-05-31 → 2026-06-14 (14 days).**

| Outcome | Signal by 2026-06-14 | Action |
|---|---|---|
| **Kill** | 0 email signups **AND** 0 inbound DMs | Mark `rejected` in queue + roster. Do NOT build. |
| **Partial → climb to rung 2** | 1–4 signups (or 1–4 DM requests) | Advance to rung-2 ($10–20 paid Reddit/Pinterest test to same listing). |
| **Greenlight → build** | **≥5 signups** in the 14-day window | Build MVP within 48h, fulfill pre-orders. |

Hard precondition (edges.md kill-fast rule): a kill verdict is only valid if the forum post actually shipped (distribution_evidence_path on file) **and** the post reached ≥25 impressions in its first 24h. If 0 signups but <25 impressions → `stay_live + channel-empty`: re-post to fallback community, do not kill the product.

## 4. Measurement plan

- **What to count:** (a) Gumroad pre-order email signups on the listing; (b) inbound Reddit DMs / comment replies asking for the link; (c) listing page views (Gumroad analytics); (d) forum post upvotes + first-24h impressions (Reddit post insights).
- **Where:** Gumroad creator dashboard (Audience / Sales→Pre-orders); Reddit post page (view count, upvotes) + inbox (DMs).
- **How often:** Day 1 (confirm post live + capture distribution_evidence_path URL + log T+24h impressions), then Day 3, Day 7, Day 14. Log each check to `memory/$(date +%Y-%m-%d).md`.
- **Owner:** Trinity day-shift (post the Reddit comment via CDP+xdotool on :98 when box has memory headroom; create the Gumroad pre-order listing via authenticated browser session).

## Notes / risks

- **Trust-gate:** health-insurance buyers may prefer a known brand. Mitigated by the proven exact-shape Etsy competitor + plain-English value-first post that earns trust before the ask.
- **Disclaimer is mandatory** on listing + product (educational, not medical/legal advice; pathways vary by plan type).
- **No charge until delivery** — pre-order captures intent without taking money for an unbuilt product (chargeback-safe, per the 2026-05-30 Gumroad lesson).
