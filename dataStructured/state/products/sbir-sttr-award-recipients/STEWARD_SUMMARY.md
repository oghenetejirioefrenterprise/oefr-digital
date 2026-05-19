# Data Steward Validation Summary

**Product:** SBIR/STTR Award Recipients (FY2023-2025)  
**Validated:** 2026-05-19 19:10 UTC  
**Status:** ✅ COMPLETE — Awaiting Compliance Review

---

## Quality Gate Results

| Check | Status | Details |
|-------|--------|---------|
| **Deduplication** | ✅ PASS | 292 duplicates removed → 17,665 unique awards |
| **Source URLs** | ✅ PASS | 100% present and well-formed |
| **Critical Fields** | ✅ PASS | Zero null values (company, amount, agency) |
| **PII Scan** | ⚠️ FINDINGS | 14 rows flagged (0.08%) |

---

## Dataset Metrics

**Input:** 17,957 rows (raw.csv)  
**Output:** 17,665 rows (clean.csv)  
**Removed:** 292 duplicate contract numbers  
**Quality Score:** 99.5%

---

## PII Findings (14 rows)

| Type | Count | Risk Level | Examples |
|------|-------|------------|----------|
| Business emails | 8 | LOW | milton@vivreonbiosciences.com |
| Military emails | 1 | LOW | christa.phillips.1@us.af.mil |
| Company contact emails | 4 | LOW | Solutions@Navaide.com |
| Personal Gmail | 1 | MEDIUM | sudharsan.dwaraknath@gmail.com |
| Phone numbers | 1 | LOW | 222-007-0130 |

**Context:** All flagged content appears in publicly published abstracts on sbir.gov

---

## Compliance Decision Options

1. **PASS AS-IS** → Ship 17,665 awards (all data is public government info)
2. **PASS WITH REMOVAL** → Remove 14 rows → 17,651 awards (zero PII risk)
3. **PASS WITH SELECTIVE REMOVAL** → Remove only personal Gmail → 17,664 awards
4. **NEEDS REVIEW** → Escalate to founder for decision

---

## Files Delivered

✅ `clean.csv` — 17,665 deduplicated awards (36 MB)  
✅ `pii-flagged-rows.csv` — 14 rows for compliance review (40 KB)  
✅ `VALIDATION_REPORT.md` — Full technical report  
✅ `STEWARD_SUMMARY.md` — This executive summary  
✅ `pipeline-status.json` — Updated workflow status

---

## Row Count Reconciliation

| Source | Count | Notes |
|--------|-------|-------|
| Data-engineer report | 17,957 | Original harvest |
| Raw CSV | 17,957 | ✅ Matches report |
| After deduplication | 17,665 | -292 duplicates (expected) |

**Verdict:** ✅ Row count matches expectations. Duplicate removal is working correctly.

---

## Recommendation

**Data-steward recommendation:** **Option 1 (PASS AS-IS)**

**Rationale:**
- All flagged emails/phones are from publicly available sbir.gov abstracts
- 13/14 are business/government contact information (not personal PII)
- Original source (sbir.gov) publishes this information publicly
- Customers are purchasing public government data with citations intact
- Removing these rows would reduce dataset value for minimal privacy benefit

**Alternative:** If strict zero-PII policy required, **Option 2** (remove all 14 rows) is viable but represents only 0.08% data loss.

---

## Next Action

**→ Forward to compliance-officer for PASS/FAIL decision**

Files ready at: `state/products/sbir-sttr-award-recipients/`

---

**Signed:** data-steward  
**Date:** 2026-05-19
