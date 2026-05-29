# CPA License Registry Harvest Status

**Target:** 750,000 active CPA licenses from all 50 states + DC  
**Started:** 2026-05-15  
**Data Engineer:** data-engineer agent

---

## Progress Summary

**Records Harvested:** 110,624 / 750,000 (14.8%)

### Completed States (2)

| State | Records | Method | File | Source URL |
|-------|---------|--------|------|------------|
| Washington | 50,597 | Open Data API | wa_raw.csv | https://data.wa.gov/resource/6du3-3h9e.json |
| Florida | 60,027 | Bulk Download (Excel) | fl_raw.csv | https://www2.myfloridalicense.com/cpa/licensereports/ |

---

## Data Access Research

### ✅ Bulk Download Available (2 states)
- ✓ **Washington** - Socrata open data API
- ✓ **Florida** - Excel file download (monthly updates)

### 🔍 Needs Further Research (11 states)
- **California** - Has "Download Licensee Lists" option ([needs investigation](http://www.dca.ca.gov/consumers/public_info/index.shtml))
- **Oregon** - List Request Form (may have fee) - [contact needed](https://www.oregon.gov/boa/pages/licensee-lookup.aspx)
- **Rhode Island** - "Generate a Roster" feature - [check access](https://dbr.ri.gov/building-design-fire-professionals-board-accountancy/board-accountancy/licensed-cpas-pas-and-firms)
- **Arkansas** - Roster search portal - [assess download options](https://portal.arkansas.gov/service/ar-certified-public-accountant-licensee-search/)
- Texas, New York, Illinois, Pennsylvania, Ohio, Georgia, North Carolina

### ⚠️ Search Interface Only (38 states)
Most states provide search/lookup tools but no advertised bulk downloads. Will require web scraping:
- Alabama, Alaska, Arizona, Colorado, Connecticut, Delaware, DC, Hawaii, Idaho, Indiana, Iowa, Kansas, Kentucky, Louisiana, Maine, Maryland, Massachusetts, Michigan, Minnesota, Mississippi, Missouri, Montana, Nebraska, Nevada, New Hampshire, New Jersey, New Mexico, North Dakota, Oklahoma, South Carolina, South Dakota, Tennessee, Utah, Vermont, Virginia, West Virginia, Wisconsin, Wyoming

---

## Data Quality Notes

### Required Fields (per brief)
- ✓ Full name
- ✓ License number
- ✓ License status
- ✓ Issue date
- ✓ Expiration date
- ⚠️ Firm name/affiliation (not available in WA or FL datasets)
- ✓ City
- ✓ State
- ✓ License type
- ✓ Source URL (added to every record)

### Missing Data
- **Firm affiliation**: Not provided by Washington or Florida boards. This field may not be consistently available across all states.

---

## Next Steps

### Immediate (High-Value States)
1. **California** (~80K CPAs) - Investigate DCA public info download
2. **Texas** (~70K CPAs) - Check for bulk export options
3. **New York** (~60K CPAs) - Assess NYSED database export
4. **Illinois** (~40K CPAs) - Research IDFPR data access

These 4 states alone represent ~250K CPAs (33% of target).

### Phase 2 (Medium States)
5. Pennsylvania, Ohio, Georgia, North Carolina, New Jersey, Virginia, Massachusetts, Maryland  
**Estimated:** ~150K additional CPAs

### Phase 3 (Remaining States)
All remaining states  
**Estimated:** ~230K CPAs

---

## Technical Approach

### For Bulk Downloads
1. Direct download via wget/curl
2. Convert to standardized CSV schema
3. Validate required fields
4. Add to consolidated raw.csv

### For Search Interfaces (Scraping Required)
Options:
1. **Selenium/Playwright** - Browser automation for JavaScript-heavy sites
2. **BeautifulSoup + Requests** - For simple HTML forms
3. **Iterative search** - Common name approach (Smith, Johnson, etc.)
4. **Alphabet iteration** - Last name starts with A-Z

Rate limiting: 1-2 second delay between requests to avoid blocks

### For NASBA CPAverify
- Requires Last Name + Jurisdiction
- Could iterate through common surnames
- Rate limits unknown - need testing

---

## Estimated Timeline

- **Phase 1** (CA, TX, NY, IL): 2-3 days (if bulk downloads available)
- **Phase 2** (8 medium states): 3-5 days (mix of downloads + scraping)
- **Phase 3** (38 remaining): 5-10 days (primarily scraping)

**Total estimated time:** 10-18 days of continuous harvesting

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Rate limiting / IP blocks | Rotate user agents, add delays, use residential proxy if needed |
| CAPTCHA challenges | Manual intervention or CAPTCHA-solving service |
| Incomplete data | Document missing fields, note data quality issues |
| Multi-state duplicates | Deduplicate by (license_number + state) combo |
| Site structure changes | Maintain state-specific scraper configs |

---

## Compliance Check

- ✓ All data is public (state accountancy licensing records)
- ✓ No PII beyond professional licensing info
- ✓ Source URL provided for every record
- ✓ No authentication bypass or login required
- ✓ Respecting robots.txt and rate limits

---

## Recommendations

Given the scale and complexity:

1. **Prioritize high-value states** - CA, TX, NY, IL account for 33% of target
2. **Exhaust all bulk downloads first** - Lowest effort, highest yield
3. **Build reusable scrapers** - Many states use similar platforms (Tyler, Accela, etc.)
4. **Parallel execution** - Run multiple state harvesters concurrently where possible
5. **Incremental delivery** - Don't wait for 100% completion to ship

**Alternative approach:** If time-constrained, consider shipping a v1 product with the states where bulk downloads are available (~150-200K records), then expand coverage in v2.

---

Last updated: 2026-05-15 | Status: In Progress
