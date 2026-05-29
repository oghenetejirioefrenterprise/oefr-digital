#!/usr/bin/env python3
"""
Harvest TTB Alcohol Beverage Permit Directory.
Sources:
- Wine Producers & Blenders
- Distilled Spirits Plants (DSP)
- Basic Permit Importers
- Basic Permit Wholesalers

All data from https://www.ttb.gov/public-information/foia/list-of-permittees
No auth required. Updated weekly by TTB.
"""

import csv
import io
import json
import requests
import time
from datetime import datetime
from pathlib import Path

# Workspace paths
BASE_DIR = Path(__file__).parent.parent
STATE_DIR = BASE_DIR / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

# TTB CSV sources (updated 2025-04)
TTB_BASE = "https://www.ttb.gov"
PERMIT_SOURCES = [
    {
        "name": "Wine Producer/Blender",
        "url": f"{TTB_BASE}/system/files/2025-04/FRL_Wine_Producer_and_Blender_Permit_List.csv",
        "permit_type": "WINE_PRODUCER_BLENDER"
    },
    {
        "name": "Distilled Spirits Producer/Bottler",
        "url": f"{TTB_BASE}/system/files/2025-04/FRL_Spirits_Producers_and_Bottlers_List.csv",
        "permit_type": "DISTILLED_SPIRITS_PLANT"
    },
    {
        "name": "Alcohol Importer",
        "url": f"{TTB_BASE}/system/files/2025-04/FRL_Alcohol_Importer_Permit_List.csv",
        "permit_type": "BASIC_PERMIT_IMPORTER"
    },
    {
        "name": "Alcohol Wholesaler",
        "url": f"{TTB_BASE}/system/files/2025-04/FRL_Alcohol_Wholesaler_Permit_List.csv",
        "permit_type": "BASIC_PERMIT_WHOLESALER"
    }
]

TIMEOUT = 60

def download_csv(url, permit_type_name):
    """Download a single TTB CSV file and return rows."""
    print(f"[harvest] Downloading {permit_type_name} from {url}...")

    try:
        resp = requests.get(url, timeout=TIMEOUT)
        resp.raise_for_status()

        # When the server sends no explicit charset, requests defaults to
        # ISO-8859-1, which mangles UTF-8 (the common encoding for these files).
        # Fall back to the content-sniffed apparent encoding in that case.
        if "charset" not in (resp.headers.get("content-type") or "").lower():
            resp.encoding = resp.apparent_encoding or resp.encoding

        # Parse CSV via the csv module so RFC-4180 quoting is honored. Do NOT
        # pre-split on '\n' — that breaks any record with a newline inside a
        # quoted field (multi-line addresses/owner names are common in permit
        # data), merging lines and shifting all subsequent column values.
        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)

        print(f"[harvest] ✓ {permit_type_name}: {len(rows)} records")
        return rows

    except requests.exceptions.RequestException as e:
        print(f"[harvest] ERROR downloading {url}: {e}")
        return []

def normalize_row(row, permit_type, source_url):
    """Normalize TTB row to standard format."""
    # TTB CSV columns (as of 2025-04):
    # Permit/Registry_Number, Owner_Name, Operating_Name, Street, City,
    # Prem_Zip, Prem_County, New_Permit_Flag

    # Some CSVs may have slightly different column names
    permit_num = row.get("Permit/Registry_Number") or row.get("Permit_Number") or row.get("Registry_Number") or ""
    owner_name = row.get("Owner_Name") or ""
    operating_name = row.get("Operating_Name") or ""
    street = row.get("Street") or ""
    city = row.get("City") or ""
    zip_code = row.get("Prem_Zip") or row.get("Zip") or ""
    county = row.get("Prem_County") or row.get("County") or ""
    new_permit = row.get("New_Permit_Flag") or ""

    return {
        "permit_number": permit_num.strip(),
        "permit_type": permit_type,
        "owner_name": owner_name.strip(),
        "operating_name": operating_name.strip(),
        "street_address": street.strip(),
        "city": city.strip(),
        "state": row.get("State", "").strip(),
        "zip_code": zip_code.strip(),
        "county": county.strip(),
        "new_permit_flag": new_permit.strip(),
        "source_url": source_url,
        "source_fetched_at": datetime.utcnow().isoformat() + "Z"
    }

def main():
    all_rows = []
    download_summary = []

    print("[harvest] Starting TTB permit directory harvest...")
    print(f"[harvest] Downloading {len(PERMIT_SOURCES)} permit types...")

    # Download each permit type
    for source in PERMIT_SOURCES:
        raw_rows = download_csv(source["url"], source["name"])

        if len(raw_rows) == 0:
            print(f"[harvest] WARNING: No rows from {source['name']}")
            continue

        # Normalize rows
        normalized = [
            normalize_row(row, source["permit_type"], source["url"])
            for row in raw_rows
        ]

        all_rows.extend(normalized)

        download_summary.append({
            "permit_type": source["name"],
            "url": source["url"],
            "row_count": len(raw_rows)
        })

        time.sleep(1)  # Rate limiting

    if len(all_rows) == 0:
        print("[harvest] ERROR: No records fetched. Aborting.")
        return 1

    print(f"[harvest] Total records harvested: {len(all_rows)}")

    # Write combined CSV
    timestamp = datetime.utcnow().strftime("%Y-%m")
    csv_path = STATE_DIR / f"ttb-brewery-winery-distillery-directory-{timestamp}.csv"

    fieldnames = list(all_rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"[harvest] ✓ Wrote {len(all_rows)} rows to {csv_path}")

    # Write harvest metadata
    harvest_path = STATE_DIR / f"ttb-brewery-winery-distillery-directory-{timestamp}.harvest.json"
    harvest_metadata = {
        "version": 1,
        "type": "harvest_report",
        "slug": "ttb-brewery-winery-distillery-directory",
        "harvested_at": datetime.utcnow().isoformat() + "Z",
        "source_url": "https://www.ttb.gov/public-information/foia/list-of-permittees",
        "permit_types": download_summary,
        "row_count": len(all_rows),
        "columns": fieldnames,
        "status": "SUCCESS",
        "notes": "Combined TTB Federal Register List (FRL) permit data: Wine Producers/Blenders, Distilled Spirits Plants, Basic Permit Importers, and Basic Permit Wholesalers. NOTE: Brewery registrations are classified as tax return information under IRC Section 6103 and are NOT included in TTB's public list. All data is publicly downloadable with no authentication required. Updated weekly by TTB."
    }

    with open(harvest_path, "w") as f:
        json.dump(harvest_metadata, f, indent=2)

    print(f"[harvest] ✓ Wrote harvest metadata to {harvest_path}")
    print("[harvest] ✓ Data Engineer handoff complete.")

    # Summary
    print("\n" + "="*60)
    print("HARVEST SUMMARY")
    print("="*60)
    for item in download_summary:
        print(f"  {item['permit_type']}: {item['row_count']:,} records")
    print(f"\nTOTAL: {len(all_rows):,} records")
    print(f"OUTPUT: {csv_path}")
    print("="*60)

    return 0

if __name__ == "__main__":
    exit(main())
