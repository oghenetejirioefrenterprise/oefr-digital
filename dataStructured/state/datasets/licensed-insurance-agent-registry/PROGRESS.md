# Licensed Insurance Agent Registry - Harvest Progress

**Last Updated**: 2026-05-16  
**Opportunity Brief**: `state/opportunities/2026-05-16-licensed-insurance-agent-registry.json`

---

## Phase 1: Texas Harvest ✅ COMPLETE

### Results
- **Records Harvested**: 952,724
- **Source**: Texas Department of Insurance via data.texas.gov (Socrata API)
- **Harvest Duration**: 143.4 seconds
- **File Size**: 212 MB
- **Output**: `raw_texas.csv`
- **Metadata**: `harvest_phase1_texas.json`

### Data Quality
- ✅ All 952K+ records successfully fetched via API
- ✅ NPN (National Producer Number) present for all records
- ✅ License types include: General Lines Agent, Adjuster, Pre-Need Agent
- ✅ Geographic coverage: TX residents + non-residents licensed in TX
- ✅ Source URLs generated for verification

### Limitations (Texas Data)
- ❌ **No explicit license status** - must infer from expiration_date
- ❌ **No agency affiliations** - not in primary dataset
- ❌ **No carrier appointments** - separate dataset available but not harvested yet
- ❌ **No multi-state license tracking** - each state license is separate record

### Sample Records
```csv
npn,license_number,name,license_type,qualification
562269,27,WILLIAM BRASSFIELD,Adjuster,Adjuster - P&C
3518148,47,BAY JOHN LONG,Adjuster,Adjuster - All Lines
1309320,101,CHRISTINE GALVAN,General Lines Agent,Property and Casualty
```

---

## Current Status: 952,724 / ~1,200,000 records (79% Texas complete)

**Brief target**: ~1.2M insurance agents across all 50 states + DC

**Texas contribution**: 953K licenses (~79% of target, but includes multi-state duplicates)

**Estimated unique agents nationwide**: ~800K-900K individuals (many hold licenses in multiple states)

---

## Phase 2: Multi-State Expansion 🔍 IN PROGRESS

### Priority Research Tasks

1. **Identify bulk download states** (Target: 10-15 states with APIs/bulk CSVs)
   - [ ] California (~400K agents) - check data.ca.gov
   - [ ] Florida (~350K agents) - check data.fl.gov or myfloridacfo.com
   - [ ] New York (~250K agents) - check data.ny.gov
   - [ ] Illinois (~150K agents) - check data.illinois.gov
   - [ ] Pennsylvania - check data.pa.gov
   - [ ] Ohio - check data.ohio.gov
   - [ ] Georgia - oci.georgia.gov/agents-agency-licensing
   - [ ] North Carolina - check ncdoi.gov
   - [ ] Michigan - check michigan.gov/difs
   - [ ] New Jersey - check state.nj.us/dobi

2. **Test NIPR API access**
   - [ ] Determine if NIPR offers programmatic access for our use case
   - [ ] Check "permissible purpose" requirements under FCRA
   - [ ] Pricing for batch data access (if available)

3. **Catalog state DOI websites**
   - [ ] Map all 50 state insurance department URLs
   - [ ] Identify which offer searchable databases vs. downloadable files
   - [ ] Document API endpoints where available

### Estimated Timeline
- **Phase 2 Research**: 1-2 days
- **Phase 2 Harvest (bulk states)**: 2-3 days
- **Phase 3 (scraping fallback)**: 3-5 days (if needed)
- **Phase 4 (deduplication/merge)**: 1-2 days

**Total estimated time to 1.2M records**: 7-12 days

---

## Phase 3: Deduplication & Normalization (Pending Phase 2)

### Tasks
- [ ] Merge all state datasets
- [ ] Deduplicate by NPN (National Producer Number)
- [ ] Standardize license status across states
- [ ] Add resident_state vs. non_resident_states columns
- [ ] Enrich with agency affiliations where available
- [ ] Generate final `licensed-insurance-agent-registry-2026.csv`

---

## Phase 4: Compliance & Quality Gate (Pending Phase 3)

### Checklist
- [ ] Verify all data is public (no PII, no auth-gated sources)
- [ ] Confirm source URLs on every row
- [ ] Validate no revoked/fraud-suspended licenses included
- [ ] Check for duplicate records after NPN deduplication
- [ ] Run through data-steward quality checks
- [ ] Pass to compliance-officer for ethics gate

---

## Output Target

**Final Dataset Spec**:
- **Slug**: `licensed-insurance-agent-registry-2026`
- **Target Rows**: 1,000,000 - 1,200,000 (after deduplication)
- **Pricing**: $99-$149 one-time CSV (per opportunity brief)
- **Distribution**: Gumroad + Stripe Payment Link
- **Audience**: Insurance carriers, InsurTech vendors, CE providers, financial services

**Columns (Final)**:
- `npn` - National Producer Number
- `license_number` - State license number
- `name` - Full name
- `license_type` - Agent, Broker, Adjuster, etc.
- `license_status` - Active, Inactive, Expired, Suspended
- `qualification` - Life, Health, P&C, etc.
- `license_issue_date`
- `expiration_date`
- `resident_state` - Primary state
- `non_resident_states` - Comma-separated (if applicable)
- `agency_name` - Affiliated agency (if available)
- `city`
- `state`
- `postal_code`
- `source_url` - Verification URL
- `source_state` - State that provided record
- `harvest_date`

---

## Blockers / Risks

1. **🟡 License status ambiguity**: Not all states provide explicit active/inactive status
   - **Mitigation**: Infer from expiration_date + handle edge cases

2. **🟡 Multi-state deduplication complexity**: Same person, multiple licenses across states
   - **Mitigation**: Use NPN as primary key, create `non_resident_states` field

3. **🟠 NIPR access restrictions**: May require "permissible purpose" justification
   - **Mitigation**: Harvest directly from state DOIs instead (public sources)

4. **🟠 Scraping effort for non-API states**: 30-40 states may require web scraping
   - **Mitigation**: Prioritize top 10-15 states by population, accept partial coverage if needed

5. **🔴 Time constraint**: Full 50-state harvest could take 2-3 weeks
   - **Mitigation**: Ship Phase 1 (Texas) + Phase 2 (top 10 states) = 80%+ coverage

---

## Decision Point

**Option A**: Ship Texas-only dataset now (953K records, $79 price point)
- ✅ Fast to market (ready today)
- ✅ Still largest state by agent count
- ❌ Misses opportunity brief's "all 50 states" positioning
- ❌ Lower perceived value vs. competitors

**Option B**: Complete top 10 states before shipping (estimated 7-10 days)
- ✅ Covers 80%+ of US insurance agents
- ✅ "Multi-state coverage" marketing angle
- ✅ Stronger competitive positioning
- ⏳ Delays launch by 1-2 weeks

**Option C**: Complete all 50 states (estimated 2-3 weeks)
- ✅ Matches opportunity brief exactly
- ✅ Maximum willingness-to-pay validation
- ✅ "Complete nationwide coverage" positioning
- ⏳ Delays launch by 2-3 weeks

**Recommended**: **Option B** - Top 10 states = 80/20 rule, ships in 1-2 weeks with strong competitive position.

---

## Next Actions

1. **data-engineer** (current): Research Phase 2 state sources (CA, FL, NY, IL priority)
2. **data-engineer**: Build harvest scripts for bulk-download states
3. **data-steward**: Quality check Texas data sample
4. **ceo**: Decide on shipping strategy (Option A/B/C above)
