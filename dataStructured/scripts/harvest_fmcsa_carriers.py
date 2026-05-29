#!/usr/bin/env python3
"""
Harvest new FMCSA carrier registrations from the DOT public data portal.
Source: Company Census File — data.transportation.gov/resource/az4n-8mr2
Filters: add_date >= 30 days ago (new carriers only)
Output: state/datasets/new-fmcsa-carrier-leads-2026-05.csv
"""

import csv
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

BASE_URL = "https://data.transportation.gov/resource/az4n-8mr2.json"
DATASET_DIR = Path(__file__).parent.parent / "state" / "datasets"
SLUG = "new-fmcsa-carrier-leads-2026-05"
CSV_PATH = DATASET_DIR / f"{SLUG}.csv"

# 30 days back from 2026-05-04
CUTOFF_DATE = "20260404"

# Fields to extract — all confirmed present in the dataset
COLUMNS = [
    "dot_number",
    "legal_name",
    "dba_name",
    "phy_street",
    "phy_city",
    "phy_state",
    "phy_zip",
    "phy_cnty",
    "phone",
    "email_address",
    "carrier_operation",
    "status_code",
    "fleetsize",
    "power_units",
    "carship",
    "hm_ind",
    "interstate_beyond_100_miles",
    "intrastate_beyond_100_miles",
    "add_date",
    "mcs150_date",
    "company_officer_1",
    "source_url",
]

PAGE_SIZE = 5000
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def fetch_page(offset: int) -> list[dict]:
    """Fetch a single page of results from the Socrata API."""
    params = {
        "$where": f"add_date >= '{CUTOFF_DATE}'",
        "$order": "add_date DESC, dot_number ASC",
        "$limit": str(PAGE_SIZE),
        "$offset": str(offset),
        "$select": ",".join(
            c for c in COLUMNS if c != "source_url"
        ),  # source_url added synthetically
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "DataStructured/1.0 (public data harvest)",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after error: {exc}")
                time.sleep(RETRY_DELAY)
            else:
                raise

    return []


def normalize_row(raw: dict) -> dict:
    """Normalize a raw API record into our canonical column set."""
    row = {}
    for col in COLUMNS:
        if col == "source_url":
            dot = raw.get("dot_number", "")
            row["source_url"] = (
                f"https://safer.fmcsa.dot.gov/CompanySnapshot.aspx?query=Number&searchtype=ANY&query_param=USDOT&query_string={dot}"
                if dot
                else ""
            )
        else:
            row[col] = raw.get(col, "")
    return row


def main():
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Harvesting FMCSA carriers added since {CUTOFF_DATE}...")
    print(f"Output: {CSV_PATH}")

    total_fetched = 0
    offset = 0
    all_rows = []

    while True:
        print(f"  Fetching offset={offset} ...", end=" ", flush=True)
        page = fetch_page(offset)
        count = len(page)
        print(f"{count} records")

        if count == 0:
            break

        for raw in page:
            all_rows.append(normalize_row(raw))

        total_fetched += count
        offset += PAGE_SIZE

        if count < PAGE_SIZE:
            break  # last page

        time.sleep(0.3)  # polite rate limiting

    print(f"\nTotal records fetched: {total_fetched}")

    # Write CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"CSV written: {CSV_PATH}")
    print(f"Rows: {len(all_rows)}")

    # Print sample
    print("\nSample (first 3 rows):")
    for row in all_rows[:3]:
        print(
            f"  DOT={row['dot_number']} | {row['legal_name']} | {row['phy_city']}, {row['phy_state']} | added={row['add_date']}"
        )

    return len(all_rows)


if __name__ == "__main__":
    main()
