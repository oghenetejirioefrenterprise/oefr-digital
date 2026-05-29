# Validation Report: nonprofit-board-directors-executives
**Product:** U.S. Nonprofit Executives & Board Directors Database 2026  
**Validator:** data-steward  
**Date:** 2026-05-23  
**Status:** ⛔ BLOCKED

## Summary

Cannot proceed with validation - **no raw dataset exists**.

## Expected Input

The data-steward validation phase requires:
- **File:** `state/products/nonprofit-board-directors-executives/raw-nonprofit-board-directors-executives-2026-05.csv`
- **Source:** Extracted by data-engineer from IRS Form 990 Part VII (Officers, Directors, Trustees, Key Employees)

## Current State

✅ Product spec exists (`spec.json`)  
✅ Opportunity approved (score: 8)  
❌ **No raw CSV data file**  
❌ No harvest metadata  
❌ Cannot validate what doesn't exist

## Blocker Details

The spec calls for **550,000 individual board member/executive records** extracted from:
1. IRS Form 990 Part VII Section A (officer/director/trustee listings)
2. Cross-referenced with IRS Exempt Organizations Business Master File
3. Supplemented with state charity registry contact data

This requires:
- Downloading/accessing IRS Form 990 XML files (bulk download or ProPublica API)
- Parsing Part VII to extract individual names, titles, compensation
- Joining with org-level IRS EO BMF data for revenue/assets/NTEE codes
- Normalizing job titles (Executive Director, Board Chair, Development Director, CFO, etc.)
- Deduplicating individuals across organizations
- Optional: Email enrichment via state registries or LinkedIn

## Workflow Dependency

```
opportunity-researcher → ceo (approve) → [data-engineer] → data-steward → compliance-officer → engineer
                                              ↑
                                         BLOCKED HERE
```

## Next Action Required

**data-engineer** must:
1. Create extraction script (likely `scripts/extract_990_part_vii.py` or similar)
2. Source IRS Form 990 XML files (via bulk download or ProPublica Nonprofit Explorer API)
3. Parse Part VII Section A for all individuals
4. Join with existing `irs-990-nonprofit-organization-directory-2026-05.cleaned.csv` for org metadata
5. Normalize position titles per spec taxonomy
6. Output: `raw-nonprofit-board-directors-executives-2026-05.csv`
7. Create harvest metadata: `.harvest.json` with source URLs, record counts, extraction timestamp

Once raw data exists, data-steward will:
- Validate field completeness (name, title, org EIN, contact info)
- Check for duplicates
- Verify source URL on every row
- Remove any PII (personal emails/phones if not org-level)
- Apply quality scoring
- Produce `clean-nonprofit-board-directors-executives-2026-05.csv`

## Related Files

- Product spec: `state/products/nonprofit-board-directors-executives/spec.json`
- Opportunity brief: `state/opportunities/2026-05-23-nonprofit-board-directors-executives.json`
- Existing org-level dataset: `state/datasets/irs-990-nonprofit-organization-directory-2026-05.cleaned.csv` (486MB, organization records only - no individual officers)

## Recommendation

Route this task to **data-engineer** employee for raw data extraction before re-assigning to data-steward.
