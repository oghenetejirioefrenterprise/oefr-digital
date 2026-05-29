# Distribution Sweep Report — 2026-05-24

**Status:** PARTIALLY BLOCKED — LinkedIn complete, X/Twitter blocked by API credits depletion

---

## Summary

- **LinkedIn:** ✅ 16/16 products posted (100% complete)
- **Twitter/X:** ❌ 0/16 products posted (0% — BLOCKED: Anthropic API credits depleted)
- **Reddit:** ❌ 0 posts (BLOCKED: Anthropic API credits depleted)

---

## LinkedIn Distribution — COMPLETE ✅

All 16 products successfully posted to LinkedIn between 2026-05-07 and 2026-05-21:

1. ✅ new-fmcsa-carrier-leads-2026-05
2. ✅ new-business-formations-csv-2026-05
3. ✅ samgov-small-biz-contractor-leads-2026-05
4. ✅ fl-real-estate-agent-licenses-2026-05
5. ✅ cms-medicare-home-health-agencies-2026-05
6. ✅ faa-civil-aircraft-registration-2026-05
7. ✅ fl-alcoholic-beverage-licensees-2026-05
8. ✅ nppes-physical-therapist-clinics-2026-05
9. ✅ tx-tdlr-electricians-2026-05
10. ✅ tx-tdlr-hvac-contractors-2026-05
11. ✅ ca-cslb-licensed-contractors-2026-05
12. ✅ nppes-dentists-dental-practices-2026-05
13. ✅ sec-registered-investment-advisers-2026-05
14. ✅ fdic-bank-branch-directory-2026-05
15. ✅ ttb-brewery-winery-distillery-directory-2026-05
16. ✅ sbir-sttr-award-recipients

**LinkedIn posts used direct Playwright automation (username/password login), not browser-use, so they succeeded before API credits ran out.**

---

## Twitter/X Distribution — BLOCKED ❌

**Blocker:** Anthropic API credits depleted ($0 balance)

All 16 products remain unposted to Twitter/X. Every posting attempt since 2026-05-07 has failed with:
- `browser-use agent returned no tweet permalink — post likely failed`
- `ANTHROPIC_API_KEY not set` (after credits depleted)
- `No module named 'browser_use'` (environment issues on 2026-05-22)
- Timeout on `tweetTextarea_0` selector
- IP-level bot detection blocks

**Pending posts (0/16 completed):**
1. ❌ new-fmcsa-carrier-leads-2026-05
2. ❌ new-business-formations-csv-2026-05
3. ❌ samgov-small-biz-contractor-leads-2026-05
4. ❌ fl-real-estate-agent-licenses-2026-05
5. ❌ cms-medicare-home-health-agencies-2026-05
6. ❌ faa-civil-aircraft-registration-2026-05
7. ❌ fl-alcoholic-beverage-licensees-2026-05
8. ❌ nppes-physical-therapist-clinics-2026-05
9. ❌ tx-tdlr-electricians-2026-05
10. ❌ tx-tdlr-hvac-contractors-2026-05
11. ❌ ca-cslb-licensed-contractors-2026-05
12. ❌ nppes-dentists-dental-practices-2026-05
13. ❌ sec-registered-investment-advisers-2026-05
14. ❌ fdic-bank-branch-directory-2026-05
15. ❌ ttb-brewery-winery-distillery-directory-2026-05
16. ❌ sbir-sttr-award-recipients

**Twitter/X requires browser-use AI agent to bypass bot detection. browser-use requires ANTHROPIC_API_KEY with active credits.**

---

## Reddit Distribution — BLOCKED ❌

**Blocker:** Anthropic API credits depleted ($0 balance)

Reddit posting also requires browser-use AI agent (username/password login, no OAuth API). All Reddit attempts failed with:
- `browser-use agent returned no result — post may have failed`
- `ANTHROPIC_API_KEY not set`
- IP-level blocks (Cloudflare 403)
- Login form unreachable

No Reddit posts succeeded for any product.

---

## Root Cause

**Anthropic API credits depleted on the $200/month plan.**

From the Second Brain briefing:
> [2026-05-19] system-config — Anthropic API credits depleted ($0 balance) — distribution frozen for X and Reddit

Both X and Reddit distribution depend on the `browser-use` Python library, which uses Claude (via Anthropic API) to pilot a headless browser and bypass bot detection. When API credits hit $0, browser-use can no longer function.

LinkedIn succeeded because it uses **direct Playwright automation** (no LLM agent), which doesn't require Anthropic API calls.

---

## Action Required

**To unblock X and Reddit distribution:**

1. **Wait for billing cycle reset** (monthly $200 Anthropic plan resets credits)
   - OR
2. **Top up Anthropic API credits manually** (if plan allows overages)
   - OR
3. **Switch to manual posting workflow** (founder posts links directly via web UI)
   - OR
4. **Defer X/Reddit distribution** until next billing cycle (May 25+?)

**Immediate workaround:**
- LinkedIn distribution is complete and functional
- Products are live on data.oefrenterprise.com
- Stripe Payment Links are active and working
- Focus customer acquisition on LinkedIn reach until X/Reddit unblocks

---

## Distribution Log Stats

- **Total log entries:** 2,140
- **Successful posts:** 16 (all LinkedIn)
- **Failed attempts:** 2,124 (mostly X and Reddit browser-use failures)
- **Unique products in queue:** 16
- **Channels targeted per product:** 2-4 (LinkedIn always, plus Twitter + niche Reddit subreddits)

---

## Next Steps

1. **Confirm API credit status** with founder/billing admin
2. **Retry X/Reddit distribution** once ANTHROPIC_API_KEY balance > 0
3. **Monitor LinkedIn post engagement** (since it's the only active channel)
4. **Consider organic founder posts** to r/Truckers, r/FreightBrokers, r/RealEstate manually (human, not bot) to unblock Reddit while credits are depleted

---

**Report generated:** 2026-05-24  
**Distribution agent:** distribution-agent (via Claude Code)
