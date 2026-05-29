# Insurance Agent License Data Sources by State

## Harvest Status

| State | Status | Access Method | Records | API/Bulk Download | Notes |
|-------|--------|---------------|---------|-------------------|-------|
| TX | ✅ Phase 1 | Socrata API | 953K | Yes | data.texas.gov/resource/kxv3-diwf.json |
| CA | 🔍 Research | Web search | ? | TBD | insurance.ca.gov/license-status/ |
| FL | 🔍 Research | Web search | ? | TBD | myfloridacfo.com likely source |
| NY | 🔍 Research | Web search | ? | TBD | dfs.ny.gov likely source |
| IL | 🔍 Research | Web search | ? | TBD | insurance.illinois.gov likely source |
| PA | 🔍 Research | Web search | ? | TBD | insurance.pa.gov likely source |
| OH | 🔍 Research | Web search | ? | TBD | insurance.ohio.gov likely source |
| GA | 🔍 Research | Web search | ? | TBD | oci.georgia.gov/agents-agency-licensing |
| NC | 🔍 Research | Web search | ? | TBD | ncdoi.gov likely source |
| MI | 🔍 Research | Web search | ? | TBD | michigan.gov/difs likely source |

## Data Aggregators

### NIPR (National Insurance Producer Registry)
- **URL**: https://nipr.com/licensing/verify-existing-licenses
- **Coverage**: All 50 states + DC
- **Access**: Requires "permissible purpose" under FCRA
- **Cost**: Subscription-based, batch reports available
- **Status**: ❌ Likely restricted for our use case
- **Notes**: Individual free reports available (1 per year), but bulk access requires business justification

### State Open Data Portals (Socrata, CKAN, etc.)
- Many states use Socrata (like Texas)
- Search pattern: `data.{state}.gov` or `{state}.gov/data`
- Check for "insurance", "licensing", "permits" categories

## Priority States (by agent population)

1. **California** - ~400K agents
2. **Texas** - ~953K licenses (✅ harvested)
3. **Florida** - ~350K agents
4. **New York** - ~250K agents
5. **Illinois** - ~150K agents

## Known State DOI URLs

| State | DOI Website | License Lookup URL |
|-------|-------------|-------------------|
| TX | tdi.texas.gov | appscenter.tdi.texas.gov/reports/p/sirconReport |
| CA | insurance.ca.gov | cdicloud.insurance.ca.gov/cal |
| FL | myfloridacfo.com | myfloridacfo.com/division/agents |
| NY | dfs.ny.gov | myportal.dfs.ny.gov |
| GA | oci.georgia.gov | oci.georgia.gov/agents-agency-licensing |

## Harvest Strategy

### Phase 1: Texas (✅ Complete)
- **Method**: Socrata API bulk download
- **Records**: 953K
- **Status**: Complete

### Phase 2: Identify bulk download states (In Progress)
- Search state open data portals for insurance/licensing datasets
- Prioritize states with Socrata, CKAN, or other OData portals
- Test API endpoints and download availability

### Phase 3: Web scraping fallback
- For states without bulk downloads, use individual lookups
- Consider rate limits and robots.txt
- Use Playwright for JavaScript-heavy sites

### Phase 4: Deduplication and normalization
- Merge all state data
- Deduplicate multi-state license holders by NPN (National Producer Number)
- Standardize column names and data formats
- Add source_url for each record

## Field Mapping

### Standard Output Columns
- `npn` - National Producer Number (NAIC)
- `license_number` - State-specific license number
- `name` - Agent full name
- `license_type` - Type (Agent, Broker, Adjuster, etc.)
- `license_status` - Active, Inactive, Expired, Suspended, Revoked
- `qualification` - Insurance types (Life, Health, P&C, etc.)
- `license_issue_date` - Original issue date
- `expiration_date` - Current expiration date
- `resident_state` - Primary state
- `non_resident_states` - Other states where licensed (if available)
- `agency_name` - Affiliated agency (if available)
- `carrier_appointments` - Appointed carriers (if available)
- `city` - Practice city
- `state` - Practice state
- `postal_code` - ZIP/postal code
- `source_url` - URL to verify record
- `source_state` - State that provided this record
- `harvest_date` - Date record was harvested

## Research Tasks

- [ ] Check if any states besides TX offer Socrata/open data APIs
- [ ] Test NIPR API access (may require business account)
- [ ] Catalog state DOI websites with searchable databases
- [ ] Identify states with downloadable CSV/Excel files
- [ ] Check for reciprocity databases that aggregate multi-state data
