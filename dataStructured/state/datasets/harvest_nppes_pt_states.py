#!/usr/bin/env python3
"""
Harvest NPPES Physical Therapist data via the public CMS NPPES API,
using state-by-state pagination to overcome the ~1,200 global-query cap.
Covers all 50 states + DC + territories.
Outputs CSV + harvest report JSON.
"""

import requests
import csv
import time
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = "https://npiregistry.cms.hhs.gov/api/"
OUTPUT_DIR = Path(__file__).parent
CSV_PATH = OUTPUT_DIR / "nppes-physical-therapist-clinics-2026-05.csv"
REPORT_PATH = OUTPUT_DIR / "nppes-physical-therapist-clinics-2026-05.harvest.json"

FIELDNAMES = [
    "npi",
    "enumeration_type",
    "provider_first_name",
    "provider_last_name",
    "provider_credential_text",
    "provider_organization_name",
    "npi_taxonomy_code",
    "taxonomy_desc",
    "street1",
    "street2",
    "city",
    "state",
    "zip_code",
    "phone",
    "enumeration_date",
    "last_update_date",
    "source_url",
]

# All US states + DC + territories
ALL_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "GU", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA",
    "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "PR", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "VI",
    "WA", "WV", "WI", "WY",
]


def fetch_page_with_retry(params, max_retries=4):
    """Fetch one page from the NPPES API with retry logic."""
    for attempt in range(max_retries):
        try:
            r = requests.get(BASE, params=params, timeout=45)
            r.raise_for_status()
            return r.json().get("results", [])
        except Exception as e:
            wait = (attempt + 1) * 3
            print(f"    [WARN] Attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    print(f"    [ERROR] All {max_retries} retries failed for params={params}")
    return None  # None signals a fetch failure


def parse_record(item):
    basic = item.get("basic", {})
    addresses = item.get("addresses", [])
    taxonomies = item.get("taxonomies", [])

    # Prefer LOCATION address; fall back to first available
    addr = next(
        (a for a in addresses if a.get("address_purpose") == "LOCATION"),
        addresses[0] if addresses else {},
    )

    # Prefer primary taxonomy; fall back to first
    tax = next(
        (t for t in taxonomies if t.get("primary")),
        taxonomies[0] if taxonomies else {},
    )

    zip_raw = addr.get("postal_code", "")
    zip5 = zip_raw[:5] if zip_raw else ""

    return {
        "npi": item.get("number", ""),
        "enumeration_type": item.get("enumeration_type", ""),
        "provider_first_name": basic.get("first_name", ""),
        "provider_last_name": basic.get("last_name", ""),
        "provider_credential_text": basic.get("credential", ""),
        "provider_organization_name": basic.get("organization_name", ""),
        "npi_taxonomy_code": tax.get("code", ""),
        "taxonomy_desc": tax.get("desc", ""),
        "street1": addr.get("address_1", ""),
        "street2": addr.get("address_2", ""),
        "city": addr.get("city", ""),
        "state": addr.get("state", ""),
        "zip_code": zip5,
        "phone": addr.get("telephone_number", ""),
        "enumeration_date": basic.get("enumeration_date", ""),
        "last_update_date": basic.get("last_updated", ""),
        "source_url": "https://npiregistry.cms.hhs.gov/",
    }


def harvest_state(state_code, enumeration_type, taxonomy_description):
    """Paginate the NPPES API for one state + enumeration_type combination."""
    records = []
    skip = 0
    fetch_errors = 0

    while True:
        params = {
            "version": "2.1",
            "taxonomy_description": taxonomy_description,
            "enumeration_type": enumeration_type,
            "state": state_code,
            "limit": 200,
            "skip": skip,
        }
        results = fetch_page_with_retry(params)

        if results is None:
            # Hard failure after all retries
            fetch_errors += 1
            print(f"    [{state_code}/{enumeration_type}] SKIPPED page at skip={skip} after retries.")
            break

        if not results:
            break  # No more results for this state

        for item in results:
            records.append(parse_record(item))

        if len(results) < 200:
            break  # Last page

        skip += 200
        time.sleep(0.4)  # Polite pacing

    return records, fetch_errors


def main():
    harvested_at = datetime.now(timezone.utc).isoformat()
    all_records = []
    state_summary = {}
    total_fetch_errors = 0

    for state in ALL_STATES:
        state_total = 0
        state_errors = 0

        # NPI-1: Individual PTs
        recs_npi1, errs1 = harvest_state(state, "NPI-1", "Physical Therapist")
        state_total += len(recs_npi1)
        state_errors += errs1
        all_records.extend(recs_npi1)

        # NPI-2: PT Organizations / Clinics
        recs_npi2, errs2 = harvest_state(state, "NPI-2", "Physical Therapist")
        state_total += len(recs_npi2)
        state_errors += errs2
        all_records.extend(recs_npi2)

        total_fetch_errors += state_errors
        state_summary[state] = {"npi1": len(recs_npi1), "npi2": len(recs_npi2), "errors": state_errors}
        print(f"  {state}: NPI-1={len(recs_npi1)}, NPI-2={len(recs_npi2)}, total={state_total}")

    print(f"\nRaw records before dedup: {len(all_records)}")

    # Deduplicate by NPI number (keep first occurrence)
    seen_npis = set()
    deduped = []
    for r in all_records:
        npi = r["npi"]
        if npi not in seen_npis:
            seen_npis.add(npi)
            deduped.append(r)

    duplicates_removed = len(all_records) - len(deduped)
    print(f"Duplicates removed: {duplicates_removed}")
    print(f"Unique records: {len(deduped)}")

    # Write CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"CSV written: {CSV_PATH}")

    # Taxonomy code breakdown
    tax_counts = {}
    for r in deduped:
        c = r["npi_taxonomy_code"]
        tax_counts[c] = tax_counts.get(c, 0) + 1

    # Enum type breakdown
    etype_counts = {}
    for r in deduped:
        e = r["enumeration_type"]
        etype_counts[e] = etype_counts.get(e, 0) + 1

    # Build harvest report
    notes_parts = [
        f"State-by-state pagination used to bypass NPPES API global query cap (~1,200 without state filter).",
        f"NPI-1 (individuals) + NPI-2 (organizations) both harvested per state.",
        f"Raw records before dedup: {len(all_records)}. Duplicates removed: {duplicates_removed}.",
        f"Unique records: {len(deduped)}.",
        f"Taxonomy code distribution (top codes): {dict(sorted(tax_counts.items(), key=lambda x: -x[1])[:5])}.",
        f"Enumeration type distribution: {etype_counts}.",
    ]
    if total_fetch_errors > 0:
        notes_parts.append(f"Fetch errors (pages that failed all retries): {total_fetch_errors}.")
    else:
        notes_parts.append("Zero fetch errors — clean harvest.")

    report = {
        "version": 1,
        "type": "harvest_report",
        "slug": "nppes-physical-therapist-clinics-2026-05",
        "harvested_at": harvested_at,
        "source_url": "https://npiregistry.cms.hhs.gov/api/",
        "row_count_raw": len(deduped),
        "raw_before_dedup": len(all_records),
        "duplicates_removed": duplicates_removed,
        "npi1_count": etype_counts.get("NPI-1", 0),
        "npi2_count": etype_counts.get("NPI-2", 0),
        "taxonomy_distribution": tax_counts,
        "state_summary": state_summary,
        "columns": FIELDNAMES,
        "notes": " | ".join(notes_parts),
        "fetch_errors": total_fetch_errors,
        "status": "SUCCESS",
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Harvest report written: {REPORT_PATH}")
    print(f"\nDone. {len(deduped)} unique PT records harvested.")
    return len(deduped)


if __name__ == "__main__":
    main()
