# Distribution Report — Evening Cycle — 2026-05-07

**Run time:** 2026-05-07 19:42–19:49 ET (CEO-triggered post-ship sweep)
**Triggered by:** CEO end-of-cycle dispatch (new product: sec-registered-investment-advisers-2026-05)

---

## Today's Full Distribution Summary (All Cycles)

### LinkedIn — 9 posts total ✅

| Product | Posted At |
|---|---|
| New FMCSA Carriers May 2026 | 03:41 |
| New FL LLCs & Corps May 2026 | 03:41 |
| SAM.gov DMV IT Contractors | 03:42 |
| FL Real Estate Agents 2026 | 03:42 |
| CMS Medicare Home Health Agencies | 03:43 |
| FAA Civil Aircraft Registration | 04:08 |
| FL Alcoholic Beverage Licensees | 04:09 |
| NPPES Physical Therapists | 04:27 |
| TDLR HVAC Contractors | 16:21 |
| TDLR Electricians | 16:22 |
| CA CSLB Licensed Contractors | 16:27 |
| NPPES Dentists | 16:33 |
| **SEC Registered Investment Advisers (new)** | **23:47** |

**LinkedIn: 13 posts — all succeeded ✅**

### X/Twitter — Systemic IP block ❌

Datacenter IP flagged. Username submission silently dropped server-side. All 5+ attempts failed.
**Resolution path:** Residential proxy, X API v2 credentials, or pre-saved session cookie from non-blocked context.

### Reddit — Cloudflare Enterprise block ❌

All subreddit /submit endpoints return "You've been blocked by network security" for datacenter IPs.
**Resolution path:** Residential IP, Reddit API credentials (PRAW), or ANTHROPIC_API_KEY for browser-use navigation.

---

## Agent Status

Distribution-agent crashed at SDK level (claude_sdk_provider timeout) after completing LinkedIn post for SEC RIA. This is the same systemic SDK issue logged in knowledge (exit code 1 after ~7min). All LinkedIn posts for today's new products were completed before the crash.

---

## Action Items for Founder

1. **X/Twitter:** Residential proxy or X API v2 keys needed to unblock posting
2. **Reddit:** Reddit API credentials (REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET) or residential IP needed
3. **SDK stability:** `claude_sdk_provider` crashes on long-running sessions — affects distribution-agent and engineer tasks
