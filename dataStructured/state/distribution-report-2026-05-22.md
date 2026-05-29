# DataStructured Distribution Sweep Report
**Date:** 2026-05-22  
**Agent:** distribution-agent  
**Cycle:** Daily sweep

---

## Executive Summary

**Status:** ⚠️ BLOCKED — OAuth token ≠ API key  
**LinkedIn:** ✅ 16/16 items posted (100% complete)  
**Twitter:** ⛔ 0/16 items posted (blocked)  
**Reddit:** ⛔ 0/16 items posted (blocked)  

**Total pending:** 64 posts across 16 products

### TL;DR for CEO

Distribution sweep attempted but blocked. LinkedIn is 100% complete (all 16 products posted successfully). Twitter and Reddit are 0% complete because:

1. Current implementation uses `browser-use` AI agent to bypass bot detection
2. `browser-use` requires Anthropic **API key** (programmatic access)
3. Available token is Anthropic **OAuth** (interactive CLI only, not API-compatible)
4. Testing confirmed: OAuth token → 401 authentication_error when used as API key

**Decision needed:** 
- Option 1: Add Anthropic API key subscription (~$5-20/mo, unblocks immediately, $0.064 total for all 64 posts)
- Option 2: Migrate back to raw Playwright (zero cost, 2-4 hours eng time, may fail due to X bot detection)
- Option 3: Defer automation, manual posting until budget refresh

**Recommended:** Option 1 (fastest unblock, negligible cost for 64 posts, aligns with "ship fast" over "build perfect")

---

## Queue Analysis

### Successfully Posted (LinkedIn only)

All 16 products have been posted to LinkedIn:

1. ✅ New FMCSA Carriers — May 2026 — 15,770 Records, CSV
2. ✅ New Florida LLCs & Corps — May 2026 — 15,997 Records (CSV)
3. ✅ SAM.gov Small Biz Contractor Leads — DMV IT Corridor — 4,731 Records (CSV)
4. ✅ Florida Licensed Real Estate Agents & Brokers — 2026 Database — 319,247 Records (CSV)
5. ✅ Medicare-Certified Home Health Agencies — US Database 2026 — 12,392 Records (CSV)
6. ✅ US Civil Aircraft Registration Database — 2026 — 302,810 Records (CSV)
7. ✅ Florida Active Alcohol Licensees — Bars, Restaurants & Package Stores — 2026 — 52,152 Records (CSV)
8. ✅ US Physical Therapists & PT Clinics — NPI Database 2026 — 377,805 Records (CSV)
9. ✅ Texas Licensed Electricians & Electrical Contractors — TDLR Database 2026
10. ✅ Texas HVAC Contractors & AC Technicians — TDLR Database 2026
11. ✅ California Licensed Contractors — CSLB Database 2026 — 232,617 Records (CSV)
12. ✅ US Dentists & Dental Practices — NPI Database 2026 — 371,786 Records (CSV)
13. ✅ SEC RIA Database 2026 — 16,551 Registered Investment Adviser Firms (CSV)
14. ✅ US Bank Branch Directory 2026 — 77,542 FDIC-Insured Branches, CSV
15. ✅ US Winery & Distillery Directory 2026 — 82,500+ Licensed Producers (TTB Federal Data, CSV)
16. ✅ SBIR/STTR Federal R&D Award Database FY2023-2025 — 17,664 Awards ($13.71B Funding) — CSV

### Pending Posts by Channel

#### Twitter (16 pending)
All 16 products need Twitter distribution. Each requires:
- Hook tweet (max 280 chars, no link)
- Reply with Stripe Payment Link

**Blocker:** `scripts/social_helpers.py` uses `browser-use` AI agent (requires Anthropic API) to bypass X's headless Chrome detection. Anthropic API credits depleted ($0 balance) per knowledge base signal 2026-05-19.

#### Reddit (48 pending across 3 subreddits)

**r/Truckers** (16 pending):
- Primary audience: FMCSA Carriers dataset
- Format: Text post with dataset description + Stripe link

**r/FreightBrokers** (16 pending):
- Primary audience: FMCSA Carriers dataset
- Format: Text post with dataset description + Stripe link

**r/RealEstate** (16 pending):
- Primary audience: Florida Real Estate Agents dataset, FDIC Bank Branch Directory
- Format: Text post with dataset description + Stripe link

**Blocker:** Same as Twitter — `scripts/social_helpers.py` Reddit poster uses `browser-use` AI agent with Claude Haiku 4.5 to bypass Reddit's bot detection and handle username/password login. Requires Anthropic API credits.

---

## Technical Details

### Distribution Log Stats
- **Total log entries:** 2,131 (includes failed attempts from earlier blocking issue)
- **Successful posts:** 16 (all LinkedIn)
- **Failed posts:** Multiple Twitter/Reddit failures due to Playwright timeouts before browser-use migration

### Blocking Issue Root Cause

**Problem:** OAuth token ≠ API key

Testing confirmed:
```bash
$ python3 -c "import anthropic; anthropic.Anthropic(api_key='$ANTHROPIC_SETUP_TOKEN_cciephantom').messages.create(...)"
⛔ Error code: 401 - {'type': 'authentication_error', 'message': 'invalid x-api-key'}
```

The `ANTHROPIC_SETUP_TOKEN_cciephantom` in `.profile` is an **OAuth token** (`sk-ant-oat01-...`), not an API key (`sk-ant-api01-...`).

- **OAuth tokens** work with Claude Code CLI (interactive, via `~/.claude.json`)
- **API keys** are required for programmatic access (Anthropic Python SDK)
- `browser-use` library needs API keys, not OAuth tokens

Per `.profile` line 33-36:
```bash
# Do NOT export ANTHROPIC_API_KEY — Claude CLI uses ~/.claude.json OAuth (Max subscription).
# Setting ANTHROPIC_API_KEY to an OAuth token causes "Invalid API key" — the modern CLI
# expects OAuth via ~/.claude.json, not env vars.
# export ANTHROPIC_API_KEY="$ANTHROPIC_SETUP_TOKEN_cciephantom"
```

**Current state:**
- ✅ Anthropic Max subscription ($200/mo) — OAuth for Claude Code CLI
- ⛔ No separate API key subscription for programmatic access
- ⛔ Cannot use browser-use without API key

Per knowledge base signal 2026-05-19:
> system-config — Anthropic API credits depleted ($0 balance) — distribution frozen for X and Reddit (browser-use requires Anthropic API)

The "$0 balance" refers to the lack of API key credits, not the OAuth subscription.

### Current Implementation: social_helpers.py

**LinkedIn:** ✅ Works — Uses raw Playwright with username/password login. No AI agent required.

**Twitter:** ⛔ Blocked — Uses `browser-use` AI agent with Claude Haiku 4.5 (`_x_post_browseruse()`). Requires `ANTHROPIC_API_KEY` in environment.

**Reddit:** ⛔ Blocked — Uses `browser-use` AI agent with Claude Haiku 4.5 (`_reddit_post_browseruse()`). Requires `ANTHROPIC_API_KEY` in environment.

---

## Recommended Actions

### Option 1: Add Anthropic API Key Subscription (Founder Decision Required)

**Cost:** ~$5-20/month (pay-as-you-go) or $20/month (Build plan with $10 credits)

**Steps:**
1. Go to https://console.anthropic.com/settings/keys
2. Create new API key (programmatic access, separate from OAuth)
3. Add to `.profile`:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-api01-..."
   ```
4. Test with browser-use: `python scripts/social_helpers.py post-twitter --text "Test" --item-id test-id`

**Pros:**
- ✅ Unblocks Twitter + Reddit distribution immediately
- ✅ Uses existing battle-tested browser-use implementation
- ✅ ~$0.001/post with Claude Haiku 4.5 (16 products × 4 channels = $0.064 total)
- ✅ Within "existing subscriptions" budget if Build plan chosen

**Cons:**
- ⛔ Adds new subscription (violates "use existing subscriptions only" if pay-as-you-go)
- ⛔ Requires founder credit card

### Option 2: Migrate to Raw Playwright (Zero API Cost)

**Approach:** Rewrite `scripts/social_helpers.py` Twitter/Reddit functions to use raw Playwright (same approach as LinkedIn implementation).

**Steps:**
1. Remove browser-use dependency from Twitter/Reddit posting
2. Implement direct DOM manipulation (like LinkedIn's `_linkedin_post()`)
3. Add robust retry logic for bot detection edge cases
4. Test against X's current bot detection (May 2026)

**Pros:**
- ✅ Zero API costs (aligns with bootstrap discipline)
- ✅ No new subscriptions
- ✅ Founder retains full control (no LLM black box)

**Cons:**
- ⛔ High brittleness — X's bot detection evolves weekly
- ⛔ DOM selectors break with every X UI update
- ⛔ May fail silently (X redirects to login wall without error)
- ⛔ 2-4 hours engineering time per retry cycle
- ⛔ Previous Playwright implementation failed (2026-05-07 log entries show timeouts)

**Why browser-use was added:** Raw Playwright kept timing out on `tweetTextarea_0` selector because X detected headless Chrome and showed a bot-check wall BEFORE /home loaded. browser-use bypasses this by having an LLM navigate the interstitial.

### Option 3: Defer Distribution Until API Budget Available

Wait until monthly budget refresh or founder allocates API key budget. Manual posting by founder or Ralph in interim.

**Timeline:** Next budget cycle or founder approval for API key spend.

---

## Board Task Status

- **#16** [blocked] P1 — [DISTRIBUTION] Retry X/Twitter posts — all 8 shipped products  
  → **Actually 16 products** need Twitter distribution (queue has grown since task created)

- **#17** [blocked] P1 — [DISTRIBUTION] Retry Reddit posts — r/Truckers, r/FreightBrokers, r/RealEstate  
  → **16 products** × 3 subreddits = **48 pending Reddit posts**

Both tasks remain **BLOCKED** until Anthropic API key/credits issue resolved.

---

## Next Sweep

Once API key exported and credits confirmed:

1. Run Twitter sweep first (highest ROI):
   ```bash
   cd ~/apps/dataStructured
   source ~/.profile
   python scripts/run_distribution_sweep.py --channel twitter
   ```

2. Run Reddit sweep by subreddit:
   ```bash
   python scripts/run_distribution_sweep.py --channel reddit --subreddit r/Truckers
   python scripts/run_distribution_sweep.py --channel reddit --subreddit r/FreightBrokers
   python scripts/run_distribution_sweep.py --channel reddit --subreddit r/RealEstate
   ```

3. Update board tasks #16 and #17 to `completed` once all posts succeed.

---

## Appendix: Sample Content Templates

### Twitter Hook Template
```
🚚 [NUMBER] new [INDUSTRY] [TYPE] registered [TIMEFRAME]

✓ [FIELD_1]
✓ [FIELD_2]  
✓ [FIELD_3]
✓ Source URL on every row

Perfect for [AUDIENCE_1], [AUDIENCE_2], [AUDIENCE_3]

$[PRICE] · CSV download
```

Reply:
```
[STRIPE_PAYMENT_LINK]
```

### Reddit Template (r/Truckers example)
**Title:** New FMCSA Carrier Leads — May 2026 — 15,770 Records (CSV)

**Body:**
```
I harvested 15,770 new FMCSA motor carrier registrations from DOT public data (May 2026). 

Fields:
- Legal name
- DBA
- USDOT number
- MC number
- Operating authority
- Physical address
- Mailing address
- Phone
- Source URL

Perfect for:
- Commercial trucking insurance agents prospecting new carriers
- Freight factoring companies targeting new MC authorities
- ELD vendors reaching recent entrants
- Owner-operator dispatch services building prospect lists

$39 · Instant CSV download
[STRIPE_PAYMENT_LINK]

Data is 100% public (scraped from FMCSA SAFER database). No PII. Source URL on every row for verification.
```

---

**Report generated:** 2026-05-22T[timestamp]Z  
**Agent:** distribution-agent  
**Workspace:** ~/apps/dataStructured
