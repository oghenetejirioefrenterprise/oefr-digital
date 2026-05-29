#!/usr/bin/env python3
"""
Harvest OSHA inspection data from publicly available OSHA data files.
Uses the OSHA Open Data Initiative files.

Source: https://www.osha.gov/stateplans/open-data
Alternative: Direct OSHA establishment search exports

This script downloads and processes OSHA inspection records for 2022-2025.
"""

import csv
import gzip
import io
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict

DATASET_DIR = Path(__file__).parent.parent / "state" / "datasets"
RAW_DIR = DATASET_DIR / "raw_osha"
SLUG = "osha-employer-inspection-violation-records-2026-05"
CSV_PATH = DATASET_DIR / f"{SLUG}.csv"
HARVEST_META_PATH = DATASET_DIR / f"{SLUG}.harvest.json"

# OSHA provides data files - these URLs may need to be updated
# Check https://www.osha.gov/stateplans/open-data for current files
OSHA_DATA_URLS = {
    "inspections": "https://www.osha.gov/sites/default/files/enforcement/OSHA_inspections.csv.gz",
    "violations": "https://www.osha.gov/sites/default/files/enforcement/OSHA_violations.csv.gz",
}

# Target fields for output CSV
OUTPUT_COLUMNS = [
    "activity_nr",
    "estab_name",
    "site_address",
    "site_city",
    "site_state",
    "site_zip",
    "naics_code",
    "insp_type",
    "insp_scope",
    "open_date",
    "close_conf_date",
    "close_case_date",
    "nr_in_estab",
    "tot_current_penalty",
    "tot_initial_penalty",
    "total_violations",
    "serious_violations",
    "willful_violations",
    "repeat_violations",
    "other_violations",
    "standards_violated",
    "source_url",
]

START_YEAR = 2022
END_YEAR = 2025


def download_file(url: str, dest_path: Path) -> bool:
    """Download a file from URL to destination."""
    print(f"Downloading {url}...")

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "DataStructured/1.0 (public data harvest)",
                "Accept": "*/*",
            },
        )

        with urllib.request.urlopen(req, timeout=300) as response:
            data = response.read()

            with open(dest_path, "wb") as f:
                f.write(data)

        print(f"  Downloaded: {len(data):,} bytes")
        return True

    except Exception as e:
        print(f"  Error downloading: {e}")
        return False


def safe_int(value) -> int:
    """Parse a CSV field as a non-negative integer, tolerating blanks,
    decimals ('1.5'), and sentinel strings ('N/A'). Government CSVs routinely
    contain these; a bare int() would raise ValueError and abort the harvest."""
    if value is None:
        return 0
    s = str(value).strip()
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except ValueError:
            return 0


def parse_inspection_year(date_str: str) -> int:
    """Extract year from date string."""
    if not date_str:
        return 0

    try:
        # Handle various date formats: YYYY-MM-DD, MM/DD/YYYY, etc.
        if "-" in date_str:
            return int(date_str.split("-")[0])
        elif "/" in date_str:
            parts = date_str.split("/")
            if len(parts[2]) == 4:
                return int(parts[2])
            elif len(parts[0]) == 4:
                return int(parts[0])
    except:
        pass

    return 0


def process_inspections_file(file_path: Path) -> List[Dict]:
    """Process the OSHA inspections CSV file."""
    print(f"\nProcessing inspections file: {file_path}")

    inspections = []

    # Open file (handle both .csv and .csv.gz). Stream the DictReader row-by-row
    # rather than list(reader) — these files are hundreds of MB to GBs and
    # materializing them all as dicts can OOM the harvest box.
    if file_path.suffix == ".gz":
        f = gzip.open(file_path, "rt", encoding="utf-8", errors="replace")
    else:
        f = open(file_path, "r", encoding="utf-8", errors="replace")

    total_rows = 0
    filtered = 0
    try:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            open_date = row.get("open_date", "") or row.get("insp_date", "")
            year = parse_inspection_year(open_date)

            if START_YEAR <= year <= END_YEAR:
                # Check if has violations (various possible field names). Use
                # safe_int so a non-integer cell ('1.5', 'N/A', blanks) does not
                # raise ValueError and abort the entire harvest on one bad row.
                has_violations = (
                    safe_int(row.get("nr_total")) > 0
                    or safe_int(row.get("total_violations")) > 0
                    or safe_int(row.get("tot_viol")) > 0
                )

                if has_violations:
                    inspections.append(row)
                    filtered += 1
    finally:
        f.close()

    print(f"  Total rows in file: {total_rows:,}")
    print(f"  Filtered to {START_YEAR}-{END_YEAR} with violations: {filtered:,} records")
    return inspections


def process_violations_file(file_path: Path) -> Dict[str, List[Dict]]:
    """Process violations file and group by inspection activity_nr."""
    print(f"\nProcessing violations file: {file_path}")

    violations_by_inspection = {}

    # Stream the DictReader row-by-row and build the index in a single pass
    # rather than list(reader) then re-loop — avoids holding a second full copy
    # of a multi-million-row violations file in memory.
    if file_path.suffix == ".gz":
        f = gzip.open(file_path, "rt", encoding="utf-8", errors="replace")
    else:
        f = open(file_path, "r", encoding="utf-8", errors="replace")

    total_rows = 0
    try:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            activity_nr = row.get("activity_nr", "")
            if activity_nr:
                violations_by_inspection.setdefault(activity_nr, []).append(row)
    finally:
        f.close()

    print(f"  Total violation rows: {total_rows:,}")
    print(f"  Grouped by inspection: {len(violations_by_inspection):,} unique inspections")
    return violations_by_inspection


def merge_inspection_with_violations(
    inspection: Dict, violations: List[Dict]
) -> Dict:
    """Merge inspection record with its violations."""

    # Count violations by type
    serious = 0
    willful = 0
    repeat = 0
    other = 0
    standards = set()

    for v in violations:
        citation_type = v.get("citation_type", "").lower()

        if "serious" in citation_type:
            serious += 1
        if "willful" in citation_type:
            willful += 1
        if "repeat" in citation_type:
            repeat += 1
        if "other" in citation_type:
            other += 1

        # Collect standards violated
        standard = v.get("standard", "") or v.get("fed_std", "")
        if standard:
            standards.add(standard)

    # Build output record
    activity_nr = inspection.get("activity_nr", "")

    record = {
        "activity_nr": activity_nr,
        "estab_name": inspection.get("estab_name", ""),
        "site_address": inspection.get("site_address", "")
        or inspection.get("site_addr_1", ""),
        "site_city": inspection.get("site_city", ""),
        "site_state": inspection.get("site_state", ""),
        "site_zip": inspection.get("site_zip", ""),
        "naics_code": inspection.get("naics_code", "") or inspection.get("naics", ""),
        "insp_type": inspection.get("insp_type", ""),
        "insp_scope": inspection.get("insp_scope", ""),
        "open_date": inspection.get("open_date", "") or inspection.get("insp_date", ""),
        "close_conf_date": inspection.get("close_conf_date", ""),
        "close_case_date": inspection.get("close_case_date", ""),
        "nr_in_estab": inspection.get("nr_in_estab", "")
        or inspection.get("nr_exposed", ""),
        "tot_current_penalty": inspection.get("tot_current_penalty", "")
        or inspection.get("total_current_penalty", ""),
        "tot_initial_penalty": inspection.get("tot_initial_penalty", "")
        or inspection.get("total_initial_penalty", ""),
        "total_violations": len(violations),
        "serious_violations": serious,
        "willful_violations": willful,
        "repeat_violations": repeat,
        "other_violations": other,
        "standards_violated": "; ".join(sorted(standards)[:10]),  # Top 10 standards
        "source_url": f"https://www.osha.gov/pls/imis/establishment.inspection_detail?id={activity_nr}"
        if activity_nr
        else "https://www.osha.gov/pls/imis/establishment.html",
    }

    return record


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("OSHA Employer Inspection & Violation Records Harvest")
    print("=" * 80)
    print(f"Target years: {START_YEAR}-{END_YEAR}")
    print(f"Output: {CSV_PATH}")
    print()

    # Step 1: Download data files
    print("Step 1: Downloading OSHA data files...")
    print("=" * 80)

    inspections_file = RAW_DIR / "osha_inspections.csv.gz"
    violations_file = RAW_DIR / "osha_violations.csv.gz"

    # Try to download (may fail if URLs are outdated)
    download_success = True

    if not inspections_file.exists():
        if not download_file(OSHA_DATA_URLS["inspections"], inspections_file):
            download_success = False

    if not violations_file.exists():
        if not download_file(OSHA_DATA_URLS["violations"], violations_file):
            download_success = False

    if not download_success:
        print()
        print("=" * 80)
        print("MANUAL DOWNLOAD REQUIRED")
        print("=" * 80)
        print("The automatic download failed. Please manually download:")
        print()
        print("1. Visit: https://www.osha.gov/stateplans/open-data")
        print("2. Download: OSHA Inspections CSV file")
        print("3. Download: OSHA Violations CSV file")
        print(f"4. Place files in: {RAW_DIR}/")
        print("   - osha_inspections.csv (or .csv.gz)")
        print("   - osha_violations.csv (or .csv.gz)")
        print()
        print("Then run this script again.")
        print("=" * 80)

        # Create placeholder harvest metadata
        harvest_meta = {
            "slug": SLUG,
            "harvested_at": datetime.now().isoformat(),
            "source": "https://www.osha.gov/stateplans/open-data",
            "status": "REQUIRES_MANUAL_DOWNLOAD",
            "instructions": "Manual download required from OSHA Open Data portal",
            "total_records": 0,
        }

        with open(HARVEST_META_PATH, "w") as f:
            json.dump(harvest_meta, f, indent=2)

        return 0

    # Step 2: Process files
    print("\nStep 2: Processing data files...")
    print("=" * 80)

    # Find actual downloaded files (may have different names)
    inspection_files = list(RAW_DIR.glob("*inspection*.csv*"))
    violation_files = list(RAW_DIR.glob("*violation*.csv*"))

    if not inspection_files:
        print("ERROR: No inspection files found in raw_osha/")
        return 1

    inspections = process_inspections_file(inspection_files[0])

    # Process violations if available
    violations_by_inspection = {}
    if violation_files:
        violations_by_inspection = process_violations_file(violation_files[0])
    else:
        print("\nWARNING: No violations file found. Proceeding with inspections only.")

    # Step 3: Merge and create final records
    print("\nStep 3: Merging data...")
    print("=" * 80)

    final_records = []

    for inspection in inspections:
        activity_nr = inspection.get("activity_nr", "")
        violations = violations_by_inspection.get(activity_nr, [])

        record = merge_inspection_with_violations(inspection, violations)
        final_records.append(record)

    print(f"Final record count: {len(final_records):,}")

    # Step 4: Write output CSV
    print("\nStep 4: Writing output CSV...")
    print("=" * 80)

    # Atomic write: write to a temp file in the same directory then os.replace()
    # onto the final path. A kill mid-write (OOM, SIGTERM, disk full) then leaves
    # the previous good product CSV intact rather than a truncated/corrupt file.
    tmp_path = CSV_PATH.with_suffix(CSV_PATH.suffix + ".tmp")
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(final_records)
    os.replace(tmp_path, CSV_PATH)

    print(f"✓ CSV written: {CSV_PATH}")
    print(f"✓ Total rows: {len(final_records):,}")

    # Step 5: Create harvest metadata
    harvest_meta = {
        "slug": SLUG,
        "harvested_at": datetime.now().isoformat(),
        "source": "https://www.osha.gov/stateplans/open-data",
        "date_range": f"{START_YEAR}-{END_YEAR}",
        "status": "SUCCESS",
        "total_records": len(final_records),
        "files_processed": {
            "inspections": str(inspection_files[0].name) if inspection_files else None,
            "violations": str(violation_files[0].name) if violation_files else None,
        },
        "sample_record": final_records[0] if final_records else None,
    }

    with open(HARVEST_META_PATH, "w") as f:
        json.dump(harvest_meta, f, indent=2)

    print(f"✓ Harvest metadata: {HARVEST_META_PATH}")

    # Print samples
    if final_records:
        print("\nSample records (first 5):")
        print("-" * 80)
        for i, record in enumerate(final_records[:5], 1):
            print(f"{i}. {record['estab_name']}")
            print(f"   Location: {record['site_city']}, {record['site_state']}")
            print(
                f"   Violations: {record['total_violations']} "
                f"(S:{record['serious_violations']} W:{record['willful_violations']} "
                f"R:{record['repeat_violations']})"
            )
            print(f"   Penalty: ${record['tot_current_penalty']}")
            print(f"   Date: {record['open_date']}")
            print()

    print("=" * 80)
    print("HARVEST COMPLETE")
    print("=" * 80)

    return len(final_records)


if __name__ == "__main__":
    try:
        count = main()
        exit(0 if count > 0 else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        exit(1)
