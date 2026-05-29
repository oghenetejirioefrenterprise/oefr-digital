#!/usr/bin/env python3
"""
Harvest EPA Toxic Release Inventory (TRI) 2023 data.

Source: EPA Envirofacts Data Service API — no auth required.
URL: https://data.epa.gov/efservice/downloads/tri/mv_tri_basic_download/2023_US/csv

Produces:
  state/datasets/epa-tri-toxic-release-reporting-facilities-2026-05.csv
  state/datasets/epa-tri-toxic-release-reporting-facilities-2026-05.harvest.json
"""

import csv
import io
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SLUG = "epa-tri-toxic-release-reporting-facilities-2026-05"
DATASET_DIR = Path(__file__).parent.parent / "state" / "datasets"
CSV_PATH = DATASET_DIR / f"{SLUG}.csv"
HARVEST_META_PATH = DATASET_DIR / f"{SLUG}.harvest.json"

# Retry/backoff for the single large download — a transient network blip or 5xx
# on the 61MB government endpoint should not abort the whole harvest.
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds (exponential backoff: 5, 10, 20)

# Confirmed working 2026-05-10: HTTP 200, 61MB, 78K+ rows, no auth required
TRI_URL = "https://data.epa.gov/efservice/downloads/tri/mv_tri_basic_download/2023_US/csv"

# Source URL template per facility record
SOURCE_URL_TEMPLATE = (
    "https://www.epa.gov/toxics-release-inventory-tri-program/tri-basic-plus-data-files-calendar-years-1987-present"
)

# Output columns for the product CSV
OUTPUT_COLUMNS = [
    "year",
    "tri_facility_id",
    "facility_name",
    "street_address",
    "city",
    "state",
    "zip",
    "county",
    "latitude",
    "longitude",
    "parent_company",
    "primary_naics",
    "industry_sector",
    "federal_facility",
    "chemical",
    "cas_number",
    "clean_air_act_chemical",
    "carcinogen",
    "pbt",
    "pfas",
    "total_on_site_releases_lbs",
    "total_off_site_releases_lbs",
    "total_releases_lbs",
    "fugitive_air_lbs",
    "stack_air_lbs",
    "water_lbs",
    "source_url",
]

# Mapping from raw TRI column names to our output names
COL_MAP = {
    "1. YEAR": "year",
    "2. TRIFD": "tri_facility_id",
    "4. FACILITY NAME": "facility_name",
    "5. STREET ADDRESS": "street_address",
    "6. CITY": "city",
    "8. ST": "state",
    "9. ZIP": "zip",
    "7. COUNTY": "county",
    "12. LATITUDE": "latitude",
    "13. LONGITUDE": "longitude",
    "15. PARENT CO NAME": "parent_company",
    "30. PRIMARY NAICS": "primary_naics",
    "23. INDUSTRY SECTOR": "industry_sector",
    "21. FEDERAL FACILITY": "federal_facility",
    "37. CHEMICAL": "chemical",
    "40. CAS#": "cas_number",
    "42. CLEAN AIR ACT CHEMICAL": "clean_air_act_chemical",
    "46. CARCINOGEN": "carcinogen",
    "47. PBT": "pbt",
    "48. PFAS": "pfas",
    "65. ON-SITE RELEASE TOTAL": "total_on_site_releases_lbs",
    "88. OFF-SITE RELEASE TOTAL": "total_off_site_releases_lbs",
    "107. TOTAL RELEASES": "total_releases_lbs",
    "51. 5.1 - FUGITIVE AIR": "fugitive_air_lbs",
    "52. 5.2 - STACK AIR": "stack_air_lbs",
    "53. 5.3 - WATER": "water_lbs",
}


def download_tri_csv() -> list[dict]:
    """Download and parse the EPA TRI 2023 national CSV."""
    print(f"Downloading EPA TRI 2023 national CSV (~61MB)...")
    print(f"URL: {TRI_URL}")
    start = time.time()

    req = urllib.request.Request(
        TRI_URL,
        headers={
            "User-Agent": "DataStructured/1.0 (public data research; contact: data@datastructured.io)",
            "Accept": "text/csv,*/*",
        },
    )

    raw = None
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                raw = response.read().decode("utf-8", errors="replace")
            break
        except Exception as exc:  # URLError, HTTPError, socket.timeout, etc.
            last_exc = exc
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2 ** attempt)
                print(f"  Download attempt {attempt + 1}/{MAX_RETRIES} failed: {exc}")
                print(f"  Retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"  Download failed after {MAX_RETRIES} attempts: {exc}")
                raise
    if raw is None:
        # Defensive: should be unreachable (loop either breaks or re-raises).
        raise RuntimeError(f"EPA TRI download produced no data: {last_exc}")

    elapsed = time.time() - start
    size_mb = len(raw) / 1024 / 1024
    print(f"Downloaded {size_mb:.1f}MB in {elapsed:.1f}s")

    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)
    print(f"Parsed {len(rows):,} records")
    return rows


def transform_rows(raw_rows: list[dict]) -> list[dict]:
    """Map raw TRI columns to output schema, filter US records."""
    out = []
    for row in raw_rows:
        # Only US facilities (state codes are 2-letter US state abbrevs)
        state = row.get("8. ST", "").strip()
        if not state or len(state) != 2:
            continue

        record = {}
        for raw_col, out_col in COL_MAP.items():
            record[out_col] = row.get(raw_col, "").strip()

        # Add source URL
        tid = record.get("tri_facility_id", "")
        year = record.get("year", "2023")
        record["source_url"] = (
            f"https://enviro.epa.gov/enviro/ef_metadata_html.tri_page?p_year={year}&p_tri_id={tid}"
            if tid
            else SOURCE_URL_TEMPLATE
        )

        out.append(record)

    print(f"Kept {len(out):,} US records after filtering")
    return out


def write_csv(records: list[dict]) -> None:
    """Write output CSV atomically (temp file + os.replace) so a kill mid-write
    leaves the previous good product CSV intact rather than a truncated file."""
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = CSV_PATH.with_suffix(CSV_PATH.suffix + ".tmp")
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    os.replace(tmp_path, CSV_PATH)
    size_mb = CSV_PATH.stat().st_size / 1024 / 1024
    print(f"Wrote {len(records):,} rows → {CSV_PATH} ({size_mb:.1f}MB)")


def write_harvest_meta(records: list[dict]) -> None:
    """Write harvest metadata JSON."""
    states = sorted({r["state"] for r in records if r.get("state")})
    chemicals = len({r["chemical"] for r in records if r.get("chemical")})
    facilities = len({r["tri_facility_id"] for r in records if r.get("tri_facility_id")})

    meta = {
        "slug": SLUG,
        "harvested_at": datetime.now(timezone.utc).isoformat(),
        "source_url": TRI_URL,
        "source_name": "EPA Toxics Release Inventory (TRI) Basic Plus Data Files 2023",
        "source_authority": "U.S. Environmental Protection Agency",
        "public": True,
        "auth_required": False,
        "row_count": len(records),
        "unique_facilities": facilities,
        "unique_chemicals": chemicals,
        "states_covered": states,
        "year": "2023",
        "columns": OUTPUT_COLUMNS,
    }

    with open(HARVEST_META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Wrote harvest metadata → {HARVEST_META_PATH}")


def main():
    print(f"=== EPA TRI Harvest === {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if CSV_PATH.exists():
        size = CSV_PATH.stat().st_size
        print(f"CSV already exists ({size / 1024 / 1024:.1f}MB), skipping download.")
        print("Delete the file to re-harvest.")
        return

    raw_rows = download_tri_csv()
    records = transform_rows(raw_rows)
    write_csv(records)
    write_harvest_meta(records)

    print(f"\n✅ Harvest complete: {len(records):,} records")
    print(f"   Output: {CSV_PATH}")


if __name__ == "__main__":
    main()
