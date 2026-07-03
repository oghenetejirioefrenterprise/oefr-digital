# OEFR Edges

**Purpose:** Document what OEFR Digital can and cannot win at. Loaded into every opportunity-scoring cycle so Trinity does not pursue markets that reward edges OEFR doesn't have.

**Hard rule:** if a market requires an edge OEFR doesn't have (community, brand, taste, personality), it is **skipped** even if demand is strong. Better to find markets that match the profile than fight uphill.

## Real edges (compete here)

| Edge | What it means | Markets that reward it |
|------|---------------|------------------------|
| **Production speed** | New product can ship in hours, not weeks | Trending/event-driven products, seasonal windows, news-cycle SEO |
| **24/7 operation** | Trinity runs while TJ sleeps; no human bottleneck | Anything that benefits from continuous iteration, response, monitoring |
| **AI-native cost** | Marginal cost per product is near zero | Volume plays, micro-tools, programmatic SEO, $5–20 price points |
| **Parallel experimentation** | Can run 100 tests simultaneously without burnout | A/B-driven optimization, opportunity scouting, multi-niche probing |
| **Willingness to kill fast** | No emotional attachment to products; sunset rules enforce it | Portfolios where most bets fail; markets that demand culling |
| **Zero overhead** | No employees, no office, no salary burn | Markets with thin margins where lean operators win |

## Non-edges (avoid markets that require these)

| Non-edge | What we lack | Markets that require it (skip) |
|----------|--------------|-------------------------------|
| **Community embeddedness** | Not embedded in any niche subculture | Etsy handmade aesthetic niches, Instagram crafts, hobbyist forums |
| **Brand trust** | New, unknown, no review history | High-consideration purchases, premium positioning, B2B enterprise |
| **Taste in subcultures** | TJ doesn't live in women's planner / wedding / wellness / homeschool worlds | Niches where insider taste compounds (most lifestyle Etsy) |
| **Personality-driven distribution** | No face on camera, no creator persona | Instagram/TikTok product sales, influencer-led launches |
| **Human sales** | No phone, no demos, no relationship building | Complex B2B, high-ticket consulting, enterprise SaaS |
| **Domain expertise (most fields)** | TJ has 16 years in networking — that's the only domain edge, and historically the wrong product type for the buying pattern | Any market that requires deep practitioner credibility we don't have |

## Channel implications

**Good fits given the edges:**
- **Gumroad** — algorithm-agnostic, higher AI tolerance, direct sales
- **Own SEO landing pages** — programmatic content, long-tail keywords, AI-native
- **Niche professional workflows** — small B2B-adjacent micro-tools for underserved trades
- **Seasonal/event-driven digital products** — narrow windows where speed wins (tax season, Mother's Day, graduation, back-to-school)
- **Cold-start communities** — small subreddits, niche forums where signal is cheap
- **Etsy keyword-searched digital downloads** (form-kits, organizers, checklists, spreadsheets) — *added 2026-06-11 per TURNAROUND-PLAN.md*. Buyers search keywords, not brands; the marketplace brings intrinsic traffic; rewards production speed + AI-native cost. The only sale in company history ($9.99) came from this exact pattern. Distinct from handmade-aesthetic Etsy below, which stays vetoed.

**Poor fits despite demand:**
- **Etsy handmade-aesthetic niches** — brand/taste/reviews compound over years (does NOT cover keyword-searched digital downloads — see good fits above)
- **Instagram/TikTok consumer products** — requires personality, face, persona
- **Enterprise B2B SaaS** — requires sales motion
- **Premium-positioned "luxury" anything** — requires brand we don't have

## Niche scoring rule

For any opportunity entering the scout queue, score on these axes:

1. **Demand size** (search volume, community size, buying intent signals)
2. **Competition density** (how saturated, how strong are top players)
3. **Speed fit** (can we produce in <48h?)
4. **Edge match** — does this market reward our edges or penalize them? **This is the veto column.**
5. **Unit economics** (price × expected conversion vs. cost to ship)
6. **Seasonality window** (how long is the opportunity open)

Edge match is binary: pass or veto. A market that requires non-edges (community, brand, taste, personality) is vetoed regardless of how strong the other axes are.

## Domain neutrality

Networking products have no special status. They enter the queue and pass/fail validation like everything else. TJ's expertise is **not a default niche** — it's one possible input that must earn its place by passing the same gates.

Historical lesson: Trinity defaulted to networking products because TJ's identity was the loudest signal in the agent's context. With sensors providing market signal, the input changes. With this `edges.md` consulted at scoring time, the decision is gated on fit, not identity.

## Deploy rules

These gates run BEFORE state-machine transitions (kill / reshape / reprice / promote). They convert decisions from narrative-grounded to evidence-grounded. Validator-Executor reads these at 09:00 ET. New rules added here become binding the next cycle.

### Kill-fast deploy-rule (added 2026-05-07, supersedes narrative-only carry from Oracle 2026-05-07 07:05 ET + 20:00 ET)

**Symmetric with the reshape gate below.** Before any `live_rung1 → rejected` verdict on a 0-session plink, require evidence of at least ONE channel-fit distribution attempt logged in the SKU's validation doc.

**Distribution log = file path or post URL** (e.g. tweet URL, Reddit thread URL, LinkedIn post URL, blog post URL). Narrative claims do not count. The validation doc must contain a `distribution_evidence_path:` field per attempt.

**Branches at verdict time (09:00 ET validator-executor cycle):**

| Sessions (n) | Distribution log on file | T+24h impressions | Verdict |
|---|---|---|---|
| ≥1 | any | any | distribution-works → defer kill / consider promote to rung 2 |
| 0 | none | n/a | `stay_live_rung1 + distribution-gap` (defer kill 48h, ship distribution attempt first) |
| 0 | on file | ≥25 | `live_rung1 → rejected` (product-empty kill grounded — real channel exposure, no buyer interest) |
| 0 | on file | <25 | `stay_live_rung1 + channel-empty` (no measurable exposure — hold SKU, change distribution channel, retest) |

**Why channel-empty ≠ product-empty:** killing a channel-empty SKU forfeits the buyer-interest experiment. Same product re-launched 6 weeks later faces identical 0-data state. Channel-empty hold preserves SKU optionality at the cost of 48h delay. The May 6 23:00 ET DEAD_PIVOT verdict on the women-pivot 4-arm matrix was an early instance of this distinction (X channel structurally non-converting for the audience under utility-shape — channel/shape failure, not product failure).

**Distribution channel must match the SKU's documented buyer pool.** Running a Pinterest pin for an injured-worker workers-comp SKU is theater (Pinterest skews 60%+ female; workers-comp buyer is male blue-collar). Same applies to running a women-pivot productivity SKU through r/lawncare. Channel-fit theater is rejected at the validation-doc review.

**Rule does NOT relitigate past kills.** Applies prospectively only. The four already-killed 0-distribution SKUs (cleaning-biz, airbnb-sop, pool-service, debt-lawsuit) are sunk cost.

### Reshape / reprice deploy-rule (added 2026-05-07, codifies narrative-only Oracle 2026-05-05 20:04 ET)

Before shipping reshape or reprice work on a non-converting line, run a minimum-viable channel-fit test on the buyer pool's actual shopping surface (≥1 distribution post on a buyer-pool-matched channel, 48h session window). Same evidence schema as kill-fast: distribution_evidence_path on file or no reshape ships.

Rationale: reshape/reprice without channel-fit evidence is reshaping against narrative. The 0-session signal could be channel-empty rather than shape-empty — the May 6 keepsake-bundle pivot post-mortem caught this case.

### v0 design gate (added 2026-05-07, codifies Oracle 2026-05-07 20:00 ET Action #5)

Each new product's v0 design must specify a distribution channel that produces measurable impression signal (≥25 T+24h) on the buyer pool at $0, using OEFR's currently authenticated platform set:

- **X owner-session** — works for buyer pools that overlap @eustaceorukpe followers + algorithmic feed. Note May 6 23:00 ET DEAD_PIVOT on women-pivot utility-shape; not all buyer pools convert here.
- **Reddit direct CDP+xdotool on display :98** — login + cookie verification proven 2026-05-05. Comment-posting unverified at scale; verify per-thread.
- **Etsy organic search** — best for women-skewed gift / planner / digital-download buyer pools.
- **Gumroad marketplace** — best for indie-creator-adjacent buyer pools (templates, prompt packs, dev tools).
- **Owned-domain blog SEO** — best for long-tail informational queries with buyer intent.

If the v0 design's buyer pool maps to none of these, the product = channel-blocked at design time, not just kill-fast-blind at deploy time. **Hold the design until either (a) a matching channel is authenticated or (b) the buyer pool definition is revised to one of the above.**

LinkedIn is currently TJ-blocker (no `LINKEDIN_*` creds in `~/.profile`). Pipeline products with LinkedIn-primary buyer pools (most B2B professional micro-tools — foster-parent, senior-parent, OO-trucking, remote-worker-w2) must either wait on TJ credential ruling or plan a non-LinkedIn primary channel.

### Operations-lane ownership (added 2026-05-07)

There is no separate "Operations" agent in cron or `~/.openclaw/agents/`. Handoffs labeled "Operations (P0)" or similar are **Trinity-owned by default** under the SOUL.md Full Autonomy Directive ("Update any config, cron, or automation"). When a cron-cycle entry hands work to "Operations," that work falls to Trinity's next main session OR to whichever cron agent next encounters the carry — whichever comes first. Do NOT defer Operations work as if it required TJ approval; Operations is inside the autonomy list.

This rule retires the "Operations" handoff label as a fictional-owner carry. Replace with `Trinity day-shift` or assign to a specific cron lane.
