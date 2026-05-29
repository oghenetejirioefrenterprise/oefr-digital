#!/usr/bin/env python3
"""
Harvest OSHA employer inspection and violation records from DOL enforcement data.
Source: DOL OSHA Enforcement API - https://enforcedata.dol.gov/views/data_summary.php
Scope: Closed inspections from 2022-2025 with at least one citation
Output: state/datasets/osha-employer-inspection-violation-records-2026-05.csv
"""

import csv
import json
import urllib.request
from datetime import datetime
from pathlib import Path

# OSHA Enforcement API endpoint (via data.dol.gov)
BASE_URL = "https://data.dol.gov/get/inspection"
DATASET_DIR = Path(__file__).parent.parent / "state" / "datasets"
SLUG = "osha-employer-inspection-violation-records-2026-05"
CSV_PATH = DATASET_DIR / f"{SLUG}.csv"
HARVEST_META_PATH = DATASET_DIR / f"{SLUG}.harvest.json"

# Date range: FY2022 through FY2025 (Oct 1, 2021 through Sep 30, 2025)
START_DATE = "2021-10-01"
END_DATE = "2025-09-30"

# Fields to extract from OSHA inspection records
COLUMNS = [
    "activity_nr",  # Inspection ID
    "estab_name",  # Employer name
    "site_address",
    "site_city",
    "site_state",
    "site_zip",
    "naics_code",
    "insp_type",  # Inspection type code
    "insp_scope",
    "open_date",
    "close_conf_date",
    "close_case_date",
    "nr_in_estab",  # Number of employees
    "tot_current_penalty",
    "tot_initial_penalty",
    "nr_serious",  # Number of serious violations
    "nr_willful",  # Number of willful violations
    "nr_repeat",  # Number of repeat violations
    "nr_other",  # Number of other-than-serious violations
    "citation_type",
    "standard_violated",
    "source_url",
]

# Inspection type codes per OSHA documentation
INSP_TYPES = {
    "A": "Accident",
    "B": "Complaint",
    "C": "Referral",
    "D": "Monitoring",
    "E": "Variance",
    "F": "Followup Inspection",
    "G": "Unprog Rel",
    "H": "Planned Programmed",
    "I": "Programmed Related",
    "J": "Unprogrammed",
    "K": "Followup Complaint",
    "L": "Other-L",
}

PAGE_SIZE = 1000
MAX_RETRIES = 3
RETRY_DELAY = 3  # seconds
MAX_PAGES = 1000  # Safety limit (adjustable)


def fetch_osha_inspections_api() -> list[dict]:
    """
    Attempt to fetch from OSHA enforcement API.
    Note: The public API may have rate limits or require different endpoints.
    This is a starting point - may need adjustment based on actual API structure.
    """
    all_records = []

    # Try the enforcement data API
    # The actual endpoint structure may vary - this is based on common patterns
    api_base = "https://data.dol.gov/get/inspection"

    print("Attempting to fetch from OSHA enforcement API...")
    print(f"Date range: {START_DATE} to {END_DATE}")

    # Try a test fetch first
    try:
        test_url = f"{api_base}/1"
        req = urllib.request.Request(
            test_url,
            headers={
                "Accept": "application/json",
                "User-Agent": "DataStructured/1.0 (public data harvest)",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            test_data = json.loads(resp.read().decode())
            print(f"API test successful. Sample structure: {list(test_data.keys())[:5]}")
            return []  # Placeholder - needs full implementation
    except Exception as e:
        print(f"API access issue: {e}")
        print("Falling back to documented bulk download approach...")
        return []


def download_bulk_files() -> list[dict]:
    """
    Download bulk OSHA inspection files from enforcedata.dol.gov.
    According to the brief, bulk ZIP files are available quarterly.
    """
    print("=" * 80)
    print("OSHA Bulk Data Download Required")
    print("=" * 80)
    print()
    print("The OSHA enforcement data is best accessed via bulk downloads from:")
    print("https://enforcedata.dol.gov/views/data_summary.php")
    print()
    print("Required files (2022-2025):")
    print("  1. Inspection data (osha_inspection.csv)")
    print("  2. Violation data (osha_violation.csv)")
    print("  3. Optional related activity (osha_related_activity.csv)")
    print()
    print("Download location: state/datasets/raw_osha/")
    print()
    print("This script does not implement the bulk merge. The working OSHA")
    print("harvester is scripts/harvest_osha_bulk.py — run that instead:")
    print("  python scripts/harvest_osha_bulk.py")
    print()

    return []


def process_inspection_record(raw: dict) -> dict:
    """Normalize a raw inspection record into canonical format."""
    row = {}

    for col in COLUMNS:
        if col == "source_url":
            # Generate source URL pointing to OSHA establishment search
            estab_name = raw.get("estab_name", "")
            site_city = raw.get("site_city", "")
            site_state = raw.get("site_state", "")
            activity_nr = raw.get("activity_nr", "")

            # OSHA establishment search URL
            if activity_nr:
                row["source_url"] = f"https://www.osha.gov/pls/imis/establishment.inspection_detail?id={activity_nr}"
            else:
                row["source_url"] = "https://www.osha.gov/pls/imis/establishment.html"

        elif col == "citation_type":
            # Aggregate citation types
            serious = int(raw.get("nr_serious", 0) or 0)
            willful = int(raw.get("nr_willful", 0) or 0)
            repeat = int(raw.get("nr_repeat", 0) or 0)
            other = int(raw.get("nr_other", 0) or 0)

            types = []
            if willful > 0:
                types.append(f"Willful({willful})")
            if serious > 0:
                types.append(f"Serious({serious})")
            if repeat > 0:
                types.append(f"Repeat({repeat})")
            if other > 0:
                types.append(f"Other({other})")

            row["citation_type"] = "; ".join(types) if types else ""

        elif col == "standard_violated":
            # Placeholder - would come from joined violation records
            row["standard_violated"] = raw.get("standard_violated", "")

        else:
            row[col] = raw.get(col, "")

    return row


def main():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("OSHA Employer Inspection & Violation Records Harvest")
    print("=" * 80)
    print(f"Target: Inspections from {START_DATE} to {END_DATE}")
    print(f"Expected: 400,000-600,000 records")
    print(f"Output: {CSV_PATH}")
    print()

    # Try API approach first
    records = fetch_osha_inspections_api()

    if not records:
        # Provide instructions for bulk download
        records = download_bulk_files()

    if not records:
        print()
        print("=" * 80)
        print("NO RECORDS PRODUCED — this harvester is not implemented")
        print("=" * 80)
        print("This script cannot produce OSHA inspection records on its own.")
        print("The working harvester is scripts/harvest_osha_bulk.py, which shares")
        print(f"the same output slug ({SLUG}).")
        print()
        print("To harvest OSHA data, run:")
        print("  python scripts/harvest_osha_bulk.py")
        print()
        # Deliberately do NOT write to HARVEST_META_PATH / CSV_PATH here.
        # Both this script and harvest_osha_bulk.py resolve those paths from the
        # same SLUG, so writing a zero-record "REQUIRES_BULK_DOWNLOAD" marker would
        # clobber the real product's harvest.json/CSV produced by harvest_osha_bulk.
        # Fail loud (non-zero) so this stub is never mistaken for a successful run.
        return -1

    # If we got records, process and write them
    print(f"\nTotal records fetched: {len(records)}")

    # Write CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)

    print(f"CSV written: {CSV_PATH}")
    print(f"Rows: {len(records)}")

    # Create harvest metadata
    harvest_meta = {
        "slug": SLUG,
        "harvested_at": datetime.now().isoformat(),
        "source": "https://enforcedata.dol.gov/views/data_summary.php",
        "date_range": f"{START_DATE} to {END_DATE}",
        "total_records": len(records),
        "sample_record": records[0] if records else None,
    }

    with open(HARVEST_META_PATH, "w") as f:
        json.dump(harvest_meta, f, indent=2)

    # Print sample
    if records:
        print("\nSample (first 3 rows):")
        for row in records[:3]:
            print(
                f"  ID={row.get('activity_nr')} | {row.get('estab_name')} | "
                f"{row.get('site_city')}, {row.get('site_state')} | "
                f"Citations: {row.get('citation_type')}"
            )

    return len(records)


if __name__ == "__main__":
    result = main()
    exit(0 if result >= 0 else 1)
