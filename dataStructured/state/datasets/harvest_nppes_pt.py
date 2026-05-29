#!/usr/bin/env python3
"""
Harvest NPPES Physical Therapist data via the public CMS NPPES API.
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


def fetch_page(params):
    """Fetch one page from the NPPES API, return results list."""
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data.get("results", [])


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


def harvest(enumeration_type, taxonomy_description, label):
    """Paginate the NPPES API for the given enumeration_type and taxonomy."""
    records = []
    skip = 0
    page_num = 0
    api_cap_hit = False

    while True:
        params = {
            "version": "2.1",
            "taxonomy_description": taxonomy_description,
            "enumeration_type": enumeration_type,
            "limit": 200,
            "skip": skip,
        }
        try:
            results = fetch_page(params)
        except Exception as e:
            print(f"  [ERROR] page {page_num} (skip={skip}): {e}")
            break

        if not results:
            break

        for item in results:
            records.append(parse_record(item))

        page_num += 1
        print(f"  [{label}] page {page_num} — fetched {len(results)}, total so far: {len(records)}")

        if len(results) < 200:
            # Last page — done
            break

        skip += 200

        # NPPES API hard cap: if we've fetched 1200 records and are still
        # getting full pages, note it but keep trying until results dry up
        if skip >= 10000:
            print(f"  [{label}] Reached skip={skip}; API may be capped. Stopping.")
            api_cap_hit = True
            break

        time.sleep(0.5)  # polite delay

    return records, api_cap_hit


def main():
    harvested_at = datetime.now(timezone.utc).isoformat()
    all_records = []
    notes = []
    cap_hit_any = False

    # --- NPI-1: Individual Physical Therapists ---
    print("Harvesting NPI-1 (individual PTs)...")
    records_npi1, cap1 = harvest("NPI-1", "Physical Therapist", "NPI-1")
    all_records.extend(records_npi1)
    notes.append(f"NPI-1 individual PTs: {len(records_npi1)} records fetched.")
    if cap1:
        cap_hit_any = True
        notes.append("NPI-1 harvest stopped at skip=10000 (API cap guard).")

    # --- NPI-2: PT Organizations/Clinics ---
    print("Harvesting NPI-2 (PT organizations)...")
    records_npi2, cap2 = harvest("NPI-2", "Physical Therapist", "NPI-2")
    all_records.extend(records_npi2)
    notes.append(f"NPI-2 PT organizations: {len(records_npi2)} records fetched.")
    if cap2:
        cap_hit_any = True
        notes.append("NPI-2 harvest stopped at skip=10000 (API cap guard).")

    # Deduplicate by NPI number
    seen_npis = set()
    deduped = []
    for r in all_records:
        npi = r["npi"]
        if npi not in seen_npis:
            seen_npis.add(npi)
            deduped.append(r)

    duplicates_removed = len(all_records) - len(deduped)
    if duplicates_removed:
        notes.append(f"Removed {duplicates_removed} duplicate NPI rows.")

    print(f"\nTotal unique records: {len(deduped)}")

    # Write CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"CSV written: {CSV_PATH}")

    # Write harvest report
    if cap_hit_any:
        notes.append(
            "API pagination cap encountered. NPPES API limits results; "
            "total count is lower than the ~337,000 known PTs in the full NPPES dataset. "
            "Full-dataset harvest would require downloading the weekly bulk file "
            "(https://download.cms.gov/nppes/NPI_Files.html) and filtering to taxonomy 225100000X."
        )

    report = {
        "version": 1,
        "type": "harvest_report",
        "slug": "nppes-physical-therapist-clinics-2026-05",
        "harvested_at": harvested_at,
        "source_url": "https://npiregistry.cms.hhs.gov/api/",
        "row_count_raw": len(deduped),
        "npi1_count": len(records_npi1),
        "npi2_count": len(records_npi2),
        "columns": FIELDNAMES,
        "notes": " | ".join(notes) if notes else "Clean harvest, no issues.",
        "api_cap_hit": cap_hit_any,
        "status": "SUCCESS",
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"Harvest report written: {REPORT_PATH}")
    print(f"\nDone. {len(deduped)} unique PT records harvested.")
    return len(deduped)


if __name__ == "__main__":
    main()
