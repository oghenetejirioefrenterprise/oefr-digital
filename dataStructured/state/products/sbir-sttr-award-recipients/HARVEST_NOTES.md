# SBIR/STTR Award Recipients Harvest Notes

## Harvest Summary

**Date:** 2026-05-19  
**Status:** ✅ COMPLETE  
**Output:** `raw.csv` (37 MB, 17,957 awards)

## Dataset Details

- **Fiscal Years:** 2023, 2024, 2025
- **Total Awards:** 17,957
- **Total Funding:** $13.71 billion
- **Data Source:** https://data.www.sbir.gov/mod_awarddatapublic/award_data.csv
- **Source File Size:** 394 MB (540,341 total awards from program inception)

### Fiscal Year Breakdown

| Fiscal Year | Award Count | 
|-------------|-------------|
| FY2023 | 6,325 |
| FY2024 | 6,412 |
| FY2025 | 5,220 |
| **Total** | **17,957** |

## Data Quality

- **Completeness:** 99.4%
- **Missing ZIP codes:** 115 (0.6%)
- **All other required fields:** 100% populated

## Fields Extracted

✅ Each row includes:
- Company name, city, state, ZIP
- Award amount and date
- Fiscal year
- Awarding agency (DoD, NIH, NSF, DOE, NASA, USDA, DHS, ED, EPA, HHS, USDT)
- Agency component (DARPA, NCI, Army, Air Force, etc.)
- Program phase (Phase I, II, IIB)
- Program type (SBIR or STTR)
- Contract/grant number
- Agency tracking number
- Topic code and title
- Award abstract (100-500 words)
- Solicitation number and year
- **Source URL** (https://www.sbir.gov/sbirsearch/detail/{contract_number})

## Spec Discrepancy Note

**Original Spec Estimate:** 36,000+ awards, $8B+ funding  
**Actual Data:** 17,957 awards, $13.71B funding

### Why the Difference?

The spec overestimated award count but underestimated total dollar value. The actual dataset is MORE valuable than projected:

- **Higher dollar value:** $13.71B vs $8B estimated (+71% more valuable)
- **Fewer awards:** 17,957 vs 36K estimated (50% fewer transactions)
- **Higher average award:** $763,682/award vs $222K estimated

This reflects the trend toward larger SBIR/STTR awards in recent years, with more Phase II and Phase IIB (commercialization) awards at higher dollar amounts.

## Data Source Notes

From sbir.gov/data-resources:
- "Files are refreshed monthly"
- "The Award database is continually updated throughout the year. As a result, data for FY25 is not expected to be complete until March 2026"
- Current download includes awards through May 2026 (155 early FY2026 awards in source file)

## File Processing

1. Downloaded full award data CSV (394 MB, all years since program inception)
2. Filtered to FY2023-2025 using Award Year field
3. Mapped columns to DataStructured schema
4. Generated source URLs for each award using contract number
5. Exported to raw.csv with proper CSV quoting for multi-line abstracts

## Next Steps

Per DataStructured workflow:
1. ✅ **Harvest** (data-engineer) — COMPLETE
2. **Quality Gate** (data-steward) — review for deduplication, validation
3. **Compliance** (compliance-officer) — verify no PII, all public data
4. **Spec Update** (ceo) — adjust row count and pricing if needed
5. **Engineering** (engineer) — create Stripe Payment Link + Gumroad listing
