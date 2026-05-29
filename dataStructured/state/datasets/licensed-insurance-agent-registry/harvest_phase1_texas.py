#!/usr/bin/env python3
"""
Phase 1: Harvest Texas insurance agent licenses from data.texas.gov
Source: Texas Department of Insurance via Socrata Open Data Portal
API: https://data.texas.gov/resource/kxv3-diwf.json
Output: state/datasets/licensed-insurance-agent-registry/raw_texas.csv

Fields harvested:
- npn: National Producer Number
- license_number: TX license number
- name: Agent name
- license_type: Type of license
- qualification: Insurance type qualified to sell
- license_issue_date: Issue date
- expiration_date: Expiration date
- city: City
- state: State
- pstl_cd: Postal code
- province: Province (if Canada)

Note: Texas data does NOT include license status (active/inactive/suspended)
or agency affiliations. Will need to infer status from expiration_date.
"""

import csv
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Socrata API endpoint for Texas insurance agents
BASE_URL = "https://data.texas.gov/resource/kxv3-diwf.json"
DATASET_DIR = Path(__file__).parent
RAW_CSV = DATASET_DIR / "raw_texas.csv"
METADATA_JSON = DATASET_DIR / "harvest_phase1_texas.json"

# Column mapping from API to our canonical format
COLUMNS = [
    "npn",
    "license_number",
    "name",
    "license_type",
    "qualification",
    "license_issue_date",
    "expiration_date",
    "city",
    "state",
    "pstl_cd",
    "province",
    "source_url",
    "source_state",
    "license_status_inferred",
]

PAGE_SIZE = 50000  # Socrata allows up to 50k per request
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def fetch_page(offset: int) -> list[dict]:
    """Fetch a single page of results from the Socrata API."""
    params = {
        "$limit": str(PAGE_SIZE),
        "$offset": str(offset),
        "$order": "license_number ASC",
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                print(f"  Fetched {len(data)} records (offset {offset})")
                return data
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after error: {exc}")
                time.sleep(RETRY_DELAY)
            else:
                raise

    return []


def infer_license_status(expiration_date_str: str) -> str:
    """
    Infer license status from expiration date.
    Returns: 'active', 'expired', or 'unknown'
    """
    if not expiration_date_str:
        return "unknown"

    try:
        # Parse ISO timestamp (e.g., "2025-12-31T00:00:00.000")
        exp_date = datetime.fromisoformat(expiration_date_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)

        if exp_date > now:
            return "active"
        else:
            return "expired"
    except Exception:
        return "unknown"


def normalize_row(raw: dict) -> dict:
    """Normalize a raw API record into our canonical column set."""
    license_num = raw.get("license_number", "")
    expiration_date = raw.get("expiration_date", "")

    row = {}
    for col in COLUMNS:
        if col == "source_url":
            # Texas TDI agent lookup by license number
            row["source_url"] = (
                f"https://appscenter.tdi.texas.gov/reports/p/sirconReport?licenseNumber={license_num}"
                if license_num
                else ""
            )
        elif col == "source_state":
            row["source_state"] = "TX"
        elif col == "license_status_inferred":
            row["license_status_inferred"] = infer_license_status(expiration_date)
        else:
            row[col] = raw.get(col, "")

    return row


def harvest():
    """Harvest all Texas insurance agent licenses via Socrata API."""
    print(f"Starting Texas insurance agent harvest from {BASE_URL}")
    start_time = time.time()

    all_records = []
    offset = 0
    total_fetched = 0

    while True:
        page = fetch_page(offset)

        if not page:
            print(f"  No more records at offset {offset}")
            break

        all_records.extend([normalize_row(rec) for rec in page])
        total_fetched += len(page)
        offset += PAGE_SIZE

        # Stop if we got fewer records than PAGE_SIZE (last page)
        if len(page) < PAGE_SIZE:
            print(f"  Last page reached ({len(page)} records)")
            break

        # Rate limiting: brief pause between requests
        time.sleep(0.5)

    # Write to CSV
    print(f"\nWriting {len(all_records)} records to {RAW_CSV}")
    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    with open(RAW_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(all_records)

    # Write harvest metadata
    elapsed = time.time() - start_time
    metadata = {
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "source_url": BASE_URL,
        "source_state": "TX",
        "source_description": "Texas Department of Insurance - Insurance Agents, Adjusters, and People",
        "records_harvested": len(all_records),
        "harvest_duration_seconds": round(elapsed, 2),
        "output_file": str(RAW_CSV.name),
        "columns": COLUMNS,
        "notes": [
            "Texas data does NOT include explicit license status field",
            "Status inferred from expiration_date: active if future, expired if past",
            "Agency affiliations and non-resident states not available in this dataset",
            "Multi-state license holders appear in multiple rows (one per license)",
        ],
    }

    with open(METADATA_JSON, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nHarvest complete!")
    print(f"  Records: {len(all_records):,}")
    print(f"  Duration: {elapsed:.1f}s")
    print(f"  Output: {RAW_CSV}")
    print(f"  Metadata: {METADATA_JSON}")


if __name__ == "__main__":
    harvest()
