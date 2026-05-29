# Distribution Sweep Report — 2026-05-26

## Summary

| Channel   | Posted | Pending | Blocked | Notes |
|-----------|--------|---------|---------|-------|
| LinkedIn  | 16/16  | 0       | 0       | All products shipped |
| Twitter   | 0/16   | 16      | 16      | ANTHROPIC_API_KEY commented out in ~/.profile |
| Reddit    | 0/16+  | 16+     | 16+     | Same root cause as Twitter |
| **Total** | **16** | **32+** | **32+** | Only LinkedIn channel operational |

## Root Cause — Twitter & Reddit Frozen

**Blocker:** `ANTHROPIC_API_KEY` is commented out in `~/.profile`. Both Twitter and Reddit posting use `browser-use` (AI agent controlling Chromium), which requires a live Anthropic API key to function.

```
# ~/.profile (line found):
# export ANTHROPIC_API_KEY=<redacted>   ← COMMENTED OUT
```

**Known issue since:** 2026-05-19 (logged in second-brain as "Anthropic API credits depleted — $0 balance")

**Credentials status:**
- `X_USERNAME` / `X_PASS`: Set
- `REDDIT_USERNAME` / `REDDIT_PASSWORD`: Set
- `LINKEDIN_EMAIL` / `LINKEDIN_PASS`: Set
- `ANTHROPIC_API_KEY`: **NOT SET** (commented out)
- `browser_use` Python package: Installed

**Conclusion:** The automation pipeline is fully wired. The sole blocker is Anthropic API credit replenishment. Once the API key is re-enabled, all 32 pending posts can execute.

## LinkedIn — Complete (16/16)

All 16 products successfully posted to LinkedIn via raw Playwright (no Anthropic API needed):

| # | Product | Status | Date |
|---|---------|--------|------|
| 1 | New FMCSA Carriers — May 2026 (15,770 records, $39) | Posted | 2026-05-07 |
| 2 | New Florida LLCs & Corps — May 2026 (15,997 records, $49) | Posted | 2026-05-07 |
| 3 | SAM.gov Small Biz Contractor Leads — DMV IT (4,731 records, $49) | Posted | 2026-05-07 |
| 4 | FL Licensed Real Estate Agents & Brokers (319,247 records, $49) | Posted | 2026-05-07 |
| 5 | Medicare-Certified Home Health Agencies (12,392 records, $49) | Posted | 2026-05-07 |
| 6 | US Civil Aircraft Registration (302,810 records, $69) | Posted | 2026-05-07 |
| 7 | FL Active Alcohol Licensees (52,152 records, $49) | Posted | 2026-05-07 |
| 8 | US Physical Therapists & PT Clinics (377,805 records, $79) | Posted | 2026-05-07 |
| 9 | TX HVAC Contractors & AC Technicians ($49) | Posted | 2026-05-07 |
| 10 | TX Licensed Electricians & Electrical Contractors ($59) | Posted | 2026-05-07 |
| 11 | CA Licensed Contractors — CSLB (232,617 records, $79) | Posted | 2026-05-07 |
| 12 | US Dentists & Dental Practices (371,786 records, $79) | Posted | 2026-05-07 |
| 13 | SEC RIA Database (16,551 firms, $79) | Posted | 2026-05-07 |
| 14 | US Bank Branch Directory (77,542 branches, $49) | Posted | 2026-05-20 |
| 15 | US Winery & Distillery Directory (82,500+ producers, $79) | Posted | 2026-05-19 |
| 16 | SBIR/STTR Federal R&D Awards FY2023-2025 (17,664 awards, $59) | Posted | 2026-05-21 |

## Twitter — Blocked (0/16)

Every product needs a Twitter post. All 16 are pending, blocked by the missing Anthropic API key. The `social_helpers.py post-twitter` command uses `browser-use` (Claude Haiku 4.5 driving Chromium) to navigate X.com, log in, and post.

**Failure history:** 100+ failed attempts logged since 2026-05-07, cycling through:
- IP-level bot detection / networkidle timeouts (early May)
- `tweetTextarea_0` locator timeouts
- `ANTHROPIC_API_KEY not set` errors
- `No module named 'browser_use'` (transient, now resolved)
- `browser-use agent returned no tweet permalink` (most recent)

### Pending Twitter posts (all 16 products)

| Product | Hook Tweet (draft) | Reply Link |
|---------|-------------------|------------|
| FMCSA Carriers | 15,770 trucking companies just got their DOT authority in 2026. Need insurance, ELD, factoring, tires. Public data — most sales teams haven't touched it. | buy.stripe.com/...7IY0c |
| FL LLCs & Corps | 15,997 new Florida LLCs and corps filed May 2026. Every one needs a bank account, insurance, bookkeeper, website. On record before most salespeople know. | buy.stripe.com/...7IY0f |
| SAM.gov IT Contractors | 4,731 small-biz IT contractors in the DC/MD/VA corridor, registered on SAM.gov. Need teaming partners, staffing, compliance tools. | buy.stripe.com/...7IY0g |
| FL Real Estate Agents | 319,247 FL licensed real estate agents and brokers — public DBPR data. Proptech SDRs, mortgage lenders, E&O brokers: your prospect list. | buy.stripe.com/...7IY0k |
| Home Health Agencies | 12,392 Medicare-certified home health agencies. EVV vendors, DME reps, staffing agencies — this is your prospect list. | buy.stripe.com/...7IY0h |
| FAA Aircraft Registration | 302,810 US-registered civil aircraft from FAA data. Aviation insurance, avionics shops, MRO, parts vendors, flight schools. | buy.stripe.com/...7IY0l |
| FL Alcohol Licensees | 52,152 active Florida alcohol licensees. Liquor distributors, POS vendors, payment processors, insurance brokers — your territory in a CSV. | buy.stripe.com/...7IY0m |
| US Physical Therapists | 377,805 US PTs and clinics, 99.98% have phone numbers. Medical SaaS, equipment reps, staffing agencies, CE providers. | buy.stripe.com/...7IY0n |
| TX Electricians | 204,535 licensed electricians in Texas from TDLR. Supply distributors, SaaS SDRs, safety training, CE companies. | buy.stripe.com/...7IY0o |
| TX HVAC Contractors | 56,001 active HVAC contractors in Texas from TDLR. Equipment distributors, software vendors, refrigerant suppliers. | buy.stripe.com/...7IY0p |
| CA Contractors (CSLB) | 232,617 active licensed contractors in California. Largest state contractor database in the US. | buy.stripe.com/...7IY0q |
| US Dentists | 371,786 dentists and dental practices from CMS NPI registry. 100% phone coverage. Supply reps, SaaS SDRs, labs, CE. | buy.stripe.com/...7IY0r |
| SEC RIAs | 16,551 SEC-registered investment adviser firms. Wealthtech, ETF sponsors, recruiters, M&A advisers. | buy.stripe.com/...7IY0s |
| FDIC Bank Branches | 77,542 FDIC-insured bank branches. Fintech BD teams, CRE brokers, insurance companies, ATM operators. | buy.stripe.com/...7IY0v |
| Wineries & Distilleries | 82,500+ US licensed wineries, breweries, distilleries from TTB data. Equipment suppliers, POS platforms, ingredient vendors. | buy.stripe.com/...7IY0w |
| SBIR/STTR Awards | 17,664 federal R&D awards totaling $13.71B. Defense primes, deep-tech VCs, SBIR consultants. | buy.stripe.com/...7IY0y |

## Reddit — Blocked (0/16+)

Same Anthropic API blocker as Twitter. Planned niche subreddits per product:

| Product | Target Subreddits |
|---------|-------------------|
| FMCSA Carriers | r/Truckers, r/FreightBrokers |
| FL LLCs & Corps | r/smallbusiness |
| SAM.gov IT Contractors | r/govcontracting |
| FL Real Estate Agents | r/realtors, r/RealEstate |
| Home Health Agencies | r/homehealth |
| FAA Aircraft | r/aviation |
| FL Alcohol Licensees | r/bartenders |
| US Physical Therapists | r/physicaltherapy |
| TX Electricians | r/electricians |
| TX HVAC Contractors | r/HVAC |
| CA Contractors | r/Construction |
| US Dentists | r/Dentistry |
| SEC RIAs | r/FinancialPlanning |
| FDIC Bank Branches | r/fintech |
| Wineries & Distilleries | r/TheBrewery, r/winemaking |
| SBIR/STTR Awards | r/govcontracting, r/startups |

**Additional historical blocker:** Reddit Cloudflare 403 / bot-detection blocks from datacenter IP. Even with API key restored, Reddit success is not guaranteed.

## Actions Required

1. **Restore Anthropic API credits** — Uncomment `ANTHROPIC_API_KEY` in `~/.profile` once the $200/mo plan renews or credits are topped up. This unblocks both Twitter and Reddit.
2. **Re-run distribution sweep** — Once API key is live, re-run this sweep. The `already_posted()` dedup function only counts `status: "posted"` entries, so failed retries won't block future attempts.
3. **Reddit IP strategy** — Consider whether Reddit posting needs a residential proxy or manual posting by the founder, since Cloudflare bot-detection has historically blocked datacenter IPs even when the API key was active.

## Failure Log Statistics

| Period | Twitter Failures | Reddit Failures | LinkedIn Failures |
|--------|-----------------|-----------------|-------------------|
| 2026-05-07 | 20 | 22 | 2 |
| 2026-05-08 | 10 | 0 | 0 |
| 2026-05-10 | 16 | 13 | 0 |
| 2026-05-11 | 1 | 0 | 0 |
| 2026-05-17 | 2 | 0 | 0 |
| 2026-05-18 | 2 | 2 | 2 |
| 2026-05-19 | 34 | 34 | 3 |
| 2026-05-20 | 0 | 0 | 2 |
| 2026-05-21 | 1 | 0 | 0 |
| 2026-05-22 | 17 | 0 | 0 |
| 2026-05-23 | 0 | 1 | 0 |
| **Total** | **103** | **72** | **9** |

---

*Generated by distribution-agent sweep on 2026-05-26. No posts attempted — all viable channels (LinkedIn) already complete; blocked channels (Twitter, Reddit) awaiting Anthropic API key restoration.*
