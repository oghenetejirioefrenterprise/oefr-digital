#!/usr/bin/env python3
"""
Harvest FDIC bank branch locations from public API.
Source: https://api.fdic.gov/banks/locations
No auth required. ~78,347 records as of May 2026.
"""

import csv
import json
import requests
import time
from datetime import datetime
from pathlib import Path

# Workspace paths
BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "state" / "datasets" / "fdic-bank-branch-directory"
DATASET_DIR.mkdir(parents=True, exist_ok=True)

# API config
API_BASE = "https://api.fdic.gov/banks/locations"
LIMIT = 10000  # Max per request
TIMEOUT = 30

def fetch_all_branches():
    """Fetch all branch records from FDIC API with pagination."""
    all_records = []
    offset = 0
    total = None

    print(f"[harvest] Starting FDIC branch harvest...")

    while True:
        url = f"{API_BASE}?limit={LIMIT}&offset={offset}"
        print(f"[harvest] Fetching offset {offset}...")

        try:
            resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            # First request: capture total count. Fail loudly if it is
            # missing/zero — a falsy total previously caused the loop to break
            # after the first page (len >= 0 is always True), silently shipping
            # a ~10k-row slice as a complete national directory. Do NOT trust a
            # missing total; treat it as a schema/outage error.
            if total is None:
                total = data.get("meta", {}).get("total", 0)
                print(f"[harvest] Total records available: {total}")
                if not total:
                    raise RuntimeError(
                        "FDIC API response is missing meta.total (got "
                        f"{total!r}). Refusing to ship a truncated dataset. "
                        "This indicates schema drift, a partial outage, or an "
                        "error page. Aborting harvest."
                    )

            # Extract records
            records = data.get("data", [])
            if not records:
                break

            all_records.extend(records)
            print(f"[harvest] Fetched {len(records)} records (total so far: {len(all_records)})")

            # Drive pagination off the returned page length: stop only once a
            # page comes back short (fewer than LIMIT records) or we have reached
            # the reported total. Relying on len >= total alone is fragile if
            # total is stale, so also stop on a short page.
            if len(records) < LIMIT or len(all_records) >= total:
                break

            offset += LIMIT
            time.sleep(1)  # Rate limiting: 1 req/sec

        except requests.exceptions.RequestException as e:
            print(f"[harvest] ERROR fetching {url}: {e}")
            if len(all_records) > 0:
                print(f"[harvest] Partial harvest: {len(all_records)} records saved")
                break
            else:
                raise

    print(f"[harvest] Harvest complete: {len(all_records)} total records")
    return all_records

def normalize_record(rec):
    """Normalize API record to CSV row."""
    data = rec.get("data", {})
    return {
        "id": f"fdic-branch-{data.get('UNINUM', '')}",
        "branch_name": data.get("OFFNAME", ""),
        "address": data.get("ADDRESS", ""),
        "city": data.get("CITY", ""),
        "state": data.get("STALP", ""),
        "zip": data.get("ZIP", ""),
        "county": data.get("COUNTY", ""),
        "latitude": data.get("LATITUDE", ""),
        "longitude": data.get("LONGITUDE", ""),
        "cert_number": data.get("CERT", ""),
        "institution_name": data.get("NAME", ""),
        "asset": data.get("ASSET", ""),
        "branch_deposits": data.get("DEPSUMBR", ""),
        "service_type": data.get("SERVTYPE_DESC", ""),
        "established_date": data.get("ESTYMD", ""),
        "cbsa_metro": data.get("CBSA_METRO_NAME", ""),
        "uni_number": data.get("UNINUM", ""),
        "source_url": f"https://api.fdic.gov/banks/locations?filters=UNINUM%3A{data.get('UNINUM', '')}",
        "source_fetched_at": datetime.utcnow().isoformat() + "Z"
    }

def main():
    # Fetch all records
    raw_records = fetch_all_branches()

    if len(raw_records) == 0:
        print("[harvest] ERROR: No records fetched. Aborting.")
        return 1

    # Normalize to CSV rows
    rows = [normalize_record(rec) for rec in raw_records]

    # Write CSV
    today = datetime.utcnow().strftime("%Y%m%d")
    csv_path = DATASET_DIR / f"raw-{today}.csv"

    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[harvest] ✓ Wrote {len(rows)} rows to {csv_path}")

    # Write metadata
    metadata_path = DATASET_DIR / f"raw-{today}.metadata.json"
    metadata = {
        "version": 1,
        "slug": "fdic-bank-branch-directory",
        "status": "READY_FOR_STEWARD",
        "harvested_at": datetime.utcnow().isoformat() + "Z",
        "row_count": len(rows),
        "columns": fieldnames,
        "source_api": API_BASE,
        "notes": f"Harvested {len(rows)} FDIC-insured bank branch locations via public API. No auth required."
    }
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[harvest] ✓ Wrote metadata to {metadata_path}")

    # Write provenance
    provenance_path = DATASET_DIR / "provenance.json"
    provenance = {
        "version": 1,
        "harvest_method": "direct_api",
        "queries": [
            {
                "url": API_BASE,
                "params": {"limit": LIMIT, "offset": "paginated"},
                "result_count": len(rows)
            }
        ],
        "toolchain": ["requests", "python-stdlib"],
        "gaps": "None identified. Full coverage via official FDIC API.",
        "notes": "Public API, no auth required. Paginated through all records."
    }
    with open(provenance_path, "w") as f:
        json.dump(provenance, f, indent=2)

    print(f"[harvest] ✓ Wrote provenance to {provenance_path}")
    print("[harvest] ✓ Data Engineer handoff complete.")
    return 0

if __name__ == "__main__":
    exit(main())
