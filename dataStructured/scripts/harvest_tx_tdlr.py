#!/usr/bin/env python3
"""
Harvest Texas TDLR licensed contractors from Texas Open Data Portal.
Source: https://data.texas.gov/dataset/TDLR-All-Licenses/7358-krk7

Filters to licenses not yet expired as of harvest date.
Writes CSV to state/tx-tdlr-licensed-contractors-2026-05.csv
Writes harvest log to state/tx-tdlr-licensed-contractors-2026-05.harvest.json
"""

import csv
import io
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime

import pandas as pd

# ── config ────────────────────────────────────────────────────────────────────
BASE_DIR = "/home/oghenetejiri/apps/dataStructured"
OUTPUT_CSV = os.path.join(BASE_DIR, "state", "tx-tdlr-licensed-contractors-2026-05.csv")
HARVEST_LOG = os.path.join(BASE_DIR, "state", "tx-tdlr-licensed-contractors-2026-05.harvest.json")

SOURCE_URL = "https://data.texas.gov/resource/7358-krk7.csv"
DATASET_PAGE = "https://data.texas.gov/dataset/TDLR-All-Licenses/7358-krk7"

PAGE_SIZE = 50000
HARVEST_DATE = date.today().isoformat()  # 2026-05-07

HEADERS = {"User-Agent": "DataStructured-Harvest/1.0 (public data; oefrenterprise.com)"}

# Trade categories we care about (partial match, case-insensitive)
TRADE_KEYWORDS = [
    "electrician", "plumber", "plumbing", "hvac", "air condition", "a/c",
    "refrigerat", "heating", "roofing", "boiler", "contractor", "mechanical",
    "fire suppression", "fire sprinkler", "elevator", "amusement", "mold",
    "water well", "irrigat", "landscape", "sign", "wrecker", "tow",
    "cosmetol", "barber", "esthetician", "massage", "manicure",
    "architect", "engineer", "surveyor",
]


def fetch_page(offset: int, limit: int) -> str:
    url = f"{SOURCE_URL}?$limit={limit}&$offset={offset}&$order=license_number"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read().decode("utf-8")


def main():
    print(f"[{HARVEST_DATE}] Starting TDLR harvest …")

    all_rows = []
    offset = 0
    batch = 0

    while True:
        batch += 1
        print(f"  Fetching batch {batch} (offset={offset}, size={PAGE_SIZE}) …", end=" ", flush=True)
        try:
            raw = fetch_page(offset, PAGE_SIZE)
        except Exception as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)

        reader = csv.DictReader(io.StringIO(raw))
        rows = list(reader)
        count = len(rows)
        print(f"{count} rows")

        if count == 0:
            break

        all_rows.extend(rows)
        offset += count

        if count < PAGE_SIZE:
            # last page
            break

        time.sleep(0.3)  # be polite

    raw_count = len(all_rows)
    print(f"  Total raw rows downloaded: {raw_count:,}")

    # ── build DataFrame ────────────────────────────────────────────────────────
    df = pd.DataFrame(all_rows)
    print(f"  Columns: {list(df.columns)}")

    # Rename columns to clean names
    col_map = {
        "license_type":                   "license_type",
        "license_number":                 "license_number",
        "license_subtype":                "license_subtype",
        "license_expiration_date_mmddccyy": "expiration_date",
        "business_name":                  "business_name",
        "owner_name":                     "owner_name",
        "business_county":                "business_county",
        "business_address_line1":         "business_address",
        "business_address_line2":         "business_address2",
        "business_city_state_zip":        "business_city_state_zip",
        "business_telephone":             "business_phone",
        "mailing_address_line1":          "mailing_address",
        "mailing_address_line2":          "mailing_address2",
        "mailing_address_city_state_zip": "mailing_city_state_zip",
        "mailing_address_county":         "mailing_county",
        "owner_telephone":                "owner_phone",
        "continuing_education_flag":      "continuing_education",
        "business_mailing":               "business_mailing",
    }
    # Only rename columns that actually exist
    existing = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=existing)

    # ── parse expiration date ──────────────────────────────────────────────────
    df["expiration_date"] = pd.to_datetime(
        df["expiration_date"], format="%m/%d/%Y", errors="coerce"
    )

    today = pd.Timestamp(HARVEST_DATE)

    # Active = expiration date is today or in the future (or unknown → keep)
    active_mask = (df["expiration_date"].isna()) | (df["expiration_date"] >= today)
    df_active = df[active_mask].copy()

    active_count = len(df_active)
    expired_count = raw_count - active_count
    print(f"  Active (not expired as of {HARVEST_DATE}): {active_count:,}")
    print(f"  Expired (filtered out): {expired_count:,}")

    # ── trade categories found ─────────────────────────────────────────────────
    license_types = sorted(df_active["license_type"].dropna().unique().tolist())
    print(f"  Unique license types: {len(license_types)}")

    # ── add source URL column ──────────────────────────────────────────────────
    df_active["source_url"] = DATASET_PAGE

    # ── format expiration date back to ISO string ──────────────────────────────
    df_active["expiration_date"] = df_active["expiration_date"].dt.strftime("%Y-%m-%d")

    # ── define final output columns ────────────────────────────────────────────
    desired_cols = [
        "license_type",
        "license_subtype",
        "license_number",
        "business_name",
        "owner_name",
        "business_county",
        "business_address",
        "business_address2",
        "business_city_state_zip",
        "business_phone",
        "mailing_address",
        "mailing_address2",
        "mailing_city_state_zip",
        "mailing_county",
        "owner_phone",
        "expiration_date",
        "continuing_education",
        "source_url",
    ]
    # Keep only cols that exist in dataframe
    output_cols = [c for c in desired_cols if c in df_active.columns]
    df_out = df_active[output_cols].copy()

    # ── write CSV ──────────────────────────────────────────────────────────────
    df_out.to_csv(OUTPUT_CSV, index=False)
    print(f"  Written: {OUTPUT_CSV}")

    # ── harvest log ────────────────────────────────────────────────────────────
    log = {
        "source_url": DATASET_PAGE,
        "api_url": SOURCE_URL,
        "download_date": HARVEST_DATE,
        "download_timestamp": datetime.utcnow().isoformat() + "Z",
        "raw_count": raw_count,
        "active_count": active_count,
        "expired_filtered_count": expired_count,
        "active_filter_logic": f"expiration_date >= {HARVEST_DATE} or null",
        "trade_categories_found": license_types,
        "trade_categories_count": len(license_types),
        "columns_in_output": output_cols,
        "output_file": OUTPUT_CSV,
        "notes": (
            "TDLR All Licenses dataset does not have an explicit license_status column. "
            "Active filter applied by comparing license_expiration_date to harvest date. "
            "Records with null expiration date retained as likely-active. "
            "Source is Texas Open Data Portal (public government data, no login required)."
        ),
    }

    with open(HARVEST_LOG, "w") as f:
        json.dump(log, f, indent=2)
    print(f"  Written: {HARVEST_LOG}")

    print(f"\nDone. {active_count:,} active records across {len(license_types)} license types.")
    return log


if __name__ == "__main__":
    main()
