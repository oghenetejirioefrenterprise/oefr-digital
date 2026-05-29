# OSHA Harvest Status Report

**Dataset:** osha-employer-inspection-violation-records-2026-05  
**Date:** 2026-05-10  
**Engineer:** data-engineer  
**Status:** 🟡 BLOCKED — Manual download required

---

## Summary

OSHA enforcement data harvest is ready to proceed but blocked by data access restrictions. The DOL Open Data Portal blocks automated downloads (HTTP 403 Forbidden). A manual browser-based download is required.

**Readiness:** ✅ Scripts created, processing logic complete  
**Blocker:** ⚠️ Data files not accessible via direct download  
**Workaround:** Manual download from DOL portal

---

## What's Ready

### ✅ Harvest Scripts
- **Created:** `scripts/harvest_osha_bulk.py` (291 lines)
- **Features:**
  - Processes OSHA inspection + violation CSV files
  - Filters to FY2022-FY2025 with citations
  - Merges violations with inspections
  - Generates source URLs for each record
  - Handles multiple date formats and field name variations
  - Error handling and retry logic

### ✅ Documentation
- **Created:** `state/datasets/raw_osha/README.md`
- **Contains:**
  - Step-by-step download instructions
  - Data source URLs
  - Required file specifications
  - Troubleshooting guide
  - Expected output format

### ✅ Metadata
- **Created:** `osha-employer-inspection-violation-records-2026-05.harvest.json`
- **Contains:** Source tracking, scope definition, blocker documentation

---

## Blocker Details

### Problem
OSHA bulk data files are publicly available but protected from automated download:

```
$ curl https://www.osha.gov/sites/default/files/enforcement/OSHA_inspections.csv.gz
HTTP/1.1 403 Forbidden
```

### Root Cause
Government data portals commonly block:
- Non-browser User-Agents
- Direct file downloads without session cookies
- Automated scraping (bot protection)

### Impact
Cannot complete harvest using scripts alone. Human intervention required.

---

## Required Action

### Option 1: Manual Download (Recommended)
**Who:** Human operator (TJ or designated assistant)  
**Time:** ~10-15 minutes  
**Steps:**

1. Open browser, navigate to: https://data.dol.gov/datasets
2. Search for: "OSHA inspection"
3. Download files:
   - OSHA Inspections CSV (~150-300 MB)
   - OSHA Violations CSV (~200-500 MB)
4. Save to: `state/datasets/raw_osha/`
5. Run: `python3 scripts/harvest_osha_bulk.py`

**See:** `state/datasets/raw_osha/README.md` for detailed instructions

### Option 2: Browser Automation (Complex)
**Who:** data-engineer with Playwright/Selenium  
**Time:** ~2-4 hours to develop  
**Trade-off:** Adds complexity, may still hit CAPTCHA/bot-detection

### Option 3: API Access (If Available)
**Who:** data-engineer  
**Requirement:** DOL API token (if public access exists)  
**Status:** Investigated, no clear public API found

---

## Next Steps

### Immediate
1. **CEO decision:** Choose Option 1 (manual) vs Option 2 (automation)
2. If Option 1: Assign download task to human operator
3. If Option 2: Authorize browser automation development

### After Files Downloaded
1. Run `python3 scripts/harvest_osha_bulk.py`
2. Verify output: `osha-employer-inspection-violation-records-2026-05.csv`
3. Hand off to **data-steward** for validation
4. Proceed to compliance review

---

## Estimated Timeline

| Phase | Time | Status |
|-------|------|--------|
| Script development | 2h | ✅ Complete |
| Data download | 15min | ⏳ Waiting |
| Processing | 5-10min | ⏳ Ready |
| Data steward validation | 30min | ⏳ Pending |
| Compliance review | 15min | ⏳ Pending |
| Product creation | 1h | ⏳ Pending |

**Total remaining:** ~2 hours (after download)

---

## Delivery Confidence

**Once files obtained:** 95% confident in successful harvest

**Risks:**
- File format changes (low risk — OSHA data structure is stable)
- Incomplete data (low risk — known source)
- Processing errors (low risk — script tested with common variations)

**Mitigation:** Comprehensive error handling, flexible field mapping, sample testing

---

## Alternative Data Sources (Investigated)

❌ **https://www.osha.gov/sites/default/files/enforcement/** — 403 Forbidden  
❌ **Direct API access** — No public endpoint found  
❌ **Socrata API** — OSHA not on Socrata platform  
✅ **DOL Open Data Portal** — Requires browser download  
✅ **OSHA Data Portal** — www.osha.gov/data (requires browser)

---

## Recommendation

**Proceed with Option 1 (Manual Download)**

**Reasoning:**
- Fastest path to completion
- 15 minutes vs 2-4 hours of automation development
- Lower technical risk
- One-time task (not recurring harvest)
- Processing script already handles all downstream steps

**Next:** CEO assigns download task → data-engineer processes → data-steward validates

---

## Files Inventory

```
state/datasets/
├── raw_osha/
│   └── README.md ✅ Created (detailed instructions)
├── osha-employer-inspection-violation-records-2026-05.harvest.json ✅ Created
├── osha-employer-inspection-violation-records-2026-05.STATUS.md ✅ Created
└── osha-employer-inspection-violation-records-2026-05.csv ⏳ Awaiting generation

scripts/
└── harvest_osha_bulk.py ✅ Created (ready to run)
```

---

**Engineer:** data-engineer  
**Handoff to:** CEO (for decision) or Human operator (for download)  
**Contact:** Via Trinity orchestration layer
