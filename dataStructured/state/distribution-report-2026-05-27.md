# Distribution Sweep Report — 2026-05-27

## Summary

| Channel   | Posted | New Attempted | New Posted | Pending | Blocked | Notes |
|-----------|--------|---------------|------------|---------|---------|-------|
| LinkedIn  | 16/18  | 1             | 0          | 2       | 2       | Login form not rendering in headless |
| Twitter   | 0/18   | 0             | 0          | 18      | 18      | ANTHROPIC_API_KEY not set |
| Reddit    | 0/18+  | 0             | 0          | 18+     | 18+     | Same root cause as Twitter |
| **Total** | **16** | **1**         | **0**      | **38+** | **38+** | All 3 channels blocked |

## What Changed Since Last Sweep (2026-05-26)

1. **New product shipped today:** Texas Auto Dealership License Database 2026 — 21,003 records, $49, Stripe + Gumroad live
2. **EPA TRI product confirmed distributable:** Stripe link live since 2026-05-11 but never posted anywhere
3. **LinkedIn now blocked too:** Login form (`input[name='session_key']`) no longer renders in headless Chromium — 3 failed attempts today for auto-dealership post
4. **Missing `scripts/lib/` modules fixed:** Created `atomic_io.py` and `schema_validator.py` stubs so `social_helpers.py` runs without `ModuleNotFoundError`

## Active Blockers (3)

### Blocker 1: ANTHROPIC_API_KEY Not Set
- **Affects:** Twitter, Reddit (all products)
- **Root cause:** API key commented out in `~/.profile` since 2026-05-19 (Anthropic credits depleted)
- **Fix:** Restore API key once $200/mo plan renews
- **Impact:** 36+ pending posts frozen

### Blocker 2: LinkedIn Headless Detection
- **Affects:** LinkedIn (new products only — 16 existing posts succeeded in May)
- **Root cause:** LinkedIn login page no longer renders `input[name='session_key']` in headless Chromium. Possible new bot detection.
- **Error:** `Page.wait_for_selector: Timeout 15000ms exceeded` on login form
- **Intermittent:** Previously worked with fresh cookies (dialog timeout was the older issue). Now login itself fails.
- **Impact:** 2 new products (auto-dealership, EPA TRI) can't be posted

### Blocker 3: Products Without Payment Links
- **Affects:** 4 products in READY_TO_SHIP status without Stripe/Gumroad launch
- **Products:** CMS DMEPOS Suppliers, IRS 990 Nonprofits, Nonprofit Board Directors, Oil & Gas Professionals
- **Fix:** Run `launch` pipeline to create Stripe payment links before distribution

## Product Catalog — Distribution Matrix

### Tier 1: Fully Shipped + LinkedIn Posted (16 products)

| # | Product | Price | LinkedIn | Twitter | Reddit |
|---|---------|-------|----------|---------|--------|
| 1 | New FMCSA Carriers — 15,770 records | $39 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 2 | New Florida LLCs & Corps — 15,997 records | $49 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 3 | SAM.gov Small Biz IT Contractors — 4,731 records | $49 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 4 | FL Real Estate Agents & Brokers — 448,610 records | $49 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 5 | Medicare Home Health Agencies — 12,392 records | $49 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 6 | US Civil Aircraft Registration — 302,810 records | $69 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 7 | FL Active Alcohol Licensees — 52,152 records | $49 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 8 | US Physical Therapists & PT Clinics — 377,805 records | $79 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 9 | TX HVAC Contractors — 56,001 records | $49 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 10 | TX Licensed Electricians — 204,535 records | $59 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 11 | CA Licensed Contractors (CSLB) — 232,617 records | $79 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 12 | US Dentists & Dental Practices — 371,786 records | $79 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 13 | SEC RIA Database — 16,551 firms | $79 | ✅ 05-07 | ❌ blocked | ❌ blocked |
| 14 | US Bank Branch Directory (FDIC) — 77,542 branches | $49 | ✅ 05-20 | ❌ blocked | ❌ blocked |
| 15 | US Winery & Distillery Directory (TTB) — 82,500+ | $79 | ✅ 05-19 | ❌ blocked | ❌ blocked |
| 16 | SBIR/STTR Federal R&D Awards — 17,664 awards | $59 | ✅ 05-21 | ❌ blocked | ❌ blocked |

### Tier 2: Shipped with Payment Links, LinkedIn NOT Posted (2 products)

| # | Product | Price | Stripe Link | LinkedIn | Twitter | Reddit |
|---|---------|-------|-------------|----------|---------|--------|
| 17 | **TX Auto Dealership Licenses — 21,003 records** | $49 | [Live](https://buy.stripe.com/00w28k6KXcvdcD90ey7IY0D) | ❌ 3 attempts failed | ❌ blocked | ❌ blocked |
| 18 | **EPA Toxic Release Inventory — 78,647 records** | $49 | [Live](https://buy.stripe.com/14A00cd9l7aT7iP1iC7IY0u) | ❌ not attempted (same blocker) | ❌ blocked | ❌ blocked |

### Tier 3: Ready to Ship, No Payment Links Yet (4 products)

| Product | Price | Status | Blocker |
|---------|-------|--------|---------|
| CMS DMEPOS Medicare Supplier Directory — 57,000+ suppliers | $49 | READY_TO_SHIP | No Stripe link |
| IRS 990 US Nonprofit Directory — 1.94M organizations | $59 | READY_TO_SHIP | No Stripe link |
| Nonprofit Board Directors & Executives | $149 | READY_TO_SHIP | Launch failed |
| Oil & Gas Energy Industry Professionals | $149 | READY_TO_SHIP | No Stripe link |

### Tier 4: Not Ready (5 products)

| Product | Status | Issue |
|---------|--------|-------|
| GSA Schedule Contract Holders | BLOCKED_BY_COMPLIANCE | Compliance review needed |
| FDA Medical Device Establishments — 28,000+ | DRAFT_BY_PM | Spec incomplete |
| FDA Warning Letters — 1,200+ actions | DRAFT_BY_PM | Spec incomplete |
| Multi-State HVAC Contractors | DRAFT_BY_PM | Spec incomplete |
| Remote Work Policy Database — 1,000 companies | DRAFT_BY_PM | Spec incomplete |

## Twitter — Pending Content (all 18 distributable products)

All tweets are pre-drafted. Hook tweet + Stripe link reply strategy. Ready to fire once ANTHROPIC_API_KEY is restored.

| Product | Hook Tweet (draft) | Reply Link |
|---------|-------------------|------------|
| FMCSA Carriers | 15,770 trucking companies just got their DOT authority in 2026. Need insurance, ELD, factoring, tires. Public data — most sales teams haven't touched it. | buy.stripe.com/...7IY0c |
| FL LLCs & Corps | 15,997 new Florida LLCs filed May 2026. Every one needs bank account, insurance, bookkeeper, website. On record before most salespeople know. | buy.stripe.com/...7IY0f |
| SAM.gov IT Contractors | 4,731 small-biz IT contractors in DC/MD/VA on SAM.gov. Need teaming partners, staffing, compliance tools. | buy.stripe.com/...7IY0g |
| FL Real Estate Agents | 319,247 FL licensed real estate agents — public DBPR data. Proptech SDRs, mortgage lenders, E&O brokers: your prospect list. | buy.stripe.com/...7IY0k |
| Home Health Agencies | 12,392 Medicare-certified home health agencies. EVV vendors, DME reps, staffing agencies — this is your prospect list. | buy.stripe.com/...7IY0h |
| FAA Aircraft | 302,810 US-registered civil aircraft from FAA data. Aviation insurance, avionics shops, MRO, parts vendors. | buy.stripe.com/...7IY0l |
| FL Alcohol Licensees | 52,152 active Florida alcohol licensees. Liquor distributors, POS vendors, payment processors — your territory in a CSV. | buy.stripe.com/...7IY0m |
| US Physical Therapists | 377,805 US PTs, 99.98% with phone numbers. Medical SaaS, equipment reps, staffing, CE providers. | buy.stripe.com/...7IY0n |
| TX Electricians | 204,535 licensed electricians in Texas from TDLR. Supply distributors, SaaS SDRs, safety training, CE companies. | buy.stripe.com/...7IY0o |
| TX HVAC Contractors | 56,001 active HVAC contractors in Texas from TDLR. Equipment distributors, software vendors, refrigerant suppliers. | buy.stripe.com/...7IY0p |
| CA Contractors (CSLB) | 232,617 active licensed contractors in California. Largest state contractor database. | buy.stripe.com/...7IY0q |
| US Dentists | 371,786 dentists from CMS NPI registry. 100% phone coverage. Supply reps, SaaS SDRs, labs, CE. | buy.stripe.com/...7IY0r |
| SEC RIAs | 16,551 SEC-registered investment adviser firms. Wealthtech, ETF sponsors, recruiters, M&A advisers. | buy.stripe.com/...7IY0s |
| FDIC Bank Branches | 77,542 FDIC-insured bank branches. Fintech BD teams, CRE brokers, insurance companies. | buy.stripe.com/...7IY0v |
| Wineries & Distilleries | 82,500+ US licensed producers from TTB data. Equipment suppliers, POS platforms, ingredient vendors. | buy.stripe.com/...7IY0w |
| SBIR/STTR Awards | 17,664 federal R&D awards, $13.71B. Defense primes, deep-tech VCs, SBIR consultants. | buy.stripe.com/...7IY0y |
| **TX Auto Dealers** | 21,003 licensed auto dealers in Texas from TxDMV. CRM/DMS vendors, parts distributors, F&I providers. | buy.stripe.com/...7IY0D |
| **EPA Toxic Release** | 78,647 facility-chemical records from EPA TRI. Same data as $10K ESG platforms. $49 once. | buy.stripe.com/...7IY0u |

## Reddit — Pending Targets (all 18 products)

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
| TX Auto Dealers | r/askcarsales, r/dealership |
| EPA Toxic Release | r/environment, r/sustainability |

## Infrastructure Fix: Missing Python Modules

Created two missing modules that were blocking `social_helpers.py`:
- `scripts/lib/atomic_io.py` — atomic JSON read/write with tmp-file rename
- `scripts/lib/schema_validator.py` — lightweight distribution log schema validation

These were imported by `distribution_log.py` but never existed, causing `ModuleNotFoundError` on every `social_helpers.py` invocation.

## Failure Log Statistics (cumulative)

| Period | Twitter | Reddit | LinkedIn |
|--------|---------|--------|----------|
| 2026-05-07 | 12 | 28 | 2 |
| 2026-05-08 | 9 | 0 | 0 |
| 2026-05-10 | 30 | 13 | 0 |
| 2026-05-11 | 1 | 0 | 0 |
| 2026-05-17 | 2 | 0 | 0 |
| 2026-05-18 | 2 | 2 | 2 |
| 2026-05-19 | 36 | 38 | 1 |
| 2026-05-20 | 0 | 0 | 2 |
| 2026-05-21 | 1 | 0 | 0 |
| 2026-05-22 | 17 | 0 | 0 |
| 2026-05-23 | 0 | 1 | 0 |
| 2026-05-28* | 0 | 0 | 3 |
| **Total** | **110** | **82** | **10** |

*\*2026-05-28 entries are from this sweep (UTC timestamps — 3 LinkedIn attempts for auto-dealership)*

## Actions Required

### Immediate (unblocks all 3 channels)
1. **Restore ANTHROPIC_API_KEY** — Uncomment in `~/.profile` once Anthropic plan renews. Unblocks Twitter (18 products) and Reddit (18+ targets).

### Short-term (unblocks LinkedIn for new products)
2. **Diagnose LinkedIn headless detection** — Login form no longer renders in headless Chromium. Options:
   - Try with updated user-agent and viewport size
   - Use `browser-use` AI agent for LinkedIn (like Twitter/Reddit) instead of raw Playwright
   - Manual posting by founder for the 2 pending products
3. **Post auto-dealership and EPA TRI to LinkedIn manually** if automation can't be fixed quickly

### Medium-term (expands product catalog)
4. **Launch 4 READY_TO_SHIP products** — CMS DMEPOS, IRS 990 Nonprofits, Nonprofit Board Directors, Oil & Gas — need Stripe payment link creation before distribution
5. **Complete 4 DRAFT_BY_PM products** — FDA devices, FDA warnings, multi-state HVAC, remote work policy

### Process fix
6. **Rebuild distribution-queue.json** — File is missing (only lock file exists). The sweep currently derives queue from products directory + log cross-reference. Consider regenerating from product catalog.

---

*Generated by distribution-agent sweep on 2026-05-27. 3 LinkedIn posting attempts made (all failed — headless login blocked). 0 Twitter/Reddit attempts (ANTHROPIC_API_KEY not set). Infrastructure: fixed 2 missing Python modules.*
