#!/usr/bin/env python3
"""
Harvest script: FL Real Estate Agent Licenses (DBPR Weekly CSV)
Source: https://www2.myfloridalicense.com/sto/file_download/extracts/REALESTATE2501LICENSE_1.csv
Output: fl-real-estate-agent-licenses-2026-05.csv
"""

import csv
import sys
from pathlib import Path

SOURCE_URL = "https://www2.myfloridalicense.com/sto/file_download/extracts/REALESTATE2501LICENSE_1.csv"
INPUT_FILE = "/tmp/fl_realestate_raw.csv"
OUTPUT_FILE = Path(__file__).parent / "fl-real-estate-agent-licenses-2026-05.csv"

RANK_MAP = {
    "SL Sales Associate": "Sales Associate",
    "BK Broker": "Broker",
    "BL Broker Sales": "Broker Associate",
}

OUTPUT_FIELDS = [
    "license_code",
    "licensee_name",
    "dba_name",
    "rank",
    "street",
    "city",
    "state",
    "zip",
    "county",
    "license_number",
    "primary_status",
    "original_issue_date",
    "expiration_date",
    "source_url",
]

# Column indices (0-based, no header row)
COL_LICENSE_CODE = 0
COL_LICENSEE_NAME = 1
COL_RANK = 3
COL_STREET1 = 4
COL_STREET2 = 5
COL_STREET3 = 6
COL_CITY = 7
COL_STATE = 8
COL_ZIP = 9
COL_COUNTY = 10
COL_PRIMARY_STATUS = 13
COL_ORIGINAL_ISSUE_DATE = 14
COL_EXPIRATION_DATE = 16
COL_LICENSE_NUMBER = 17
COL_DBA_NAME = 19

MIN_COLS = 20  # minimum columns expected per row


def normalize_rank(raw: str) -> str:
    return RANK_MAP.get(raw.strip(), raw.strip())


def build_street(row: list[str]) -> str:
    parts = [row[COL_STREET1].strip(), row[COL_STREET2].strip(), row[COL_STREET3].strip()]
    return " ".join(p for p in parts if p)


def process_row(row: list[str]) -> dict | None:
    if len(row) < MIN_COLS:
        return None
    return {
        "license_code": row[COL_LICENSE_CODE].strip(),
        "licensee_name": row[COL_LICENSEE_NAME].strip(),
        "dba_name": row[COL_DBA_NAME].strip(),
        "rank": normalize_rank(row[COL_RANK]),
        "street": build_street(row),
        "city": row[COL_CITY].strip(),
        "state": row[COL_STATE].strip(),
        "zip": row[COL_ZIP].strip(),
        "county": row[COL_COUNTY].strip(),
        "license_number": row[COL_LICENSE_NUMBER].strip(),
        "primary_status": row[COL_PRIMARY_STATUS].strip(),
        "original_issue_date": row[COL_ORIGINAL_ISSUE_DATE].strip(),
        "expiration_date": row[COL_EXPIRATION_DATE].strip(),
        "source_url": SOURCE_URL,
    }


def main():
    written = 0
    skipped = 0

    with open(INPUT_FILE, encoding="utf-8", errors="replace") as fin, \
         open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as fout:

        reader = csv.reader(fin)
        writer = csv.DictWriter(fout, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()

        for raw_row in reader:
            record = process_row(raw_row)
            if record is None:
                skipped += 1
                continue
            # Skip rows with no license number and no licensee name (blank rows)
            if not record["license_number"] and not record["licensee_name"]:
                skipped += 1
                continue
            writer.writerow(record)
            written += 1

    print(f"Done. Written: {written:,}  Skipped: {skipped:,}")
    print(f"Output: {OUTPUT_FILE}")

    # Spot-check: show first 3 records
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        print("\nSpot-check (first 3 rows):")
        for i, row in enumerate(reader):
            if i >= 3:
                break
            for k, v in row.items():
                print(f"  {k}: {v}")
            print()


if __name__ == "__main__":
    main()
