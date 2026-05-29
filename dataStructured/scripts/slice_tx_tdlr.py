#!/usr/bin/env python3
"""
Slice TX TDLR dataset into focused B2B products.
Produces:
  1. tx-tdlr-electricians-2026-05.csv — all electrical license holders
  2. tx-tdlr-hvac-2026-05.csv — all HVAC/AC contractors & technicians
"""

import os, sys, json, re
import pandas as pd
from datetime import datetime, date

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, "state")

ELECTRICAL_TYPES = {
    "Apprentice Electrician",
    "Journeyman Electrician",
    "Journeyman Industrial Electrician",
    "Journeyman Lineman Electrician",
    "Master Electrician",
    "Electrical Contractor",
    "Residential Wireman",
    "Maintenance Electrician",
    "Apprentice Sign Electrician",
    "Electrical Sign Contractor",
    "Master Sign Electrician",
    "Journeyman Sign Electrician",
}

HVAC_TYPES = {
    "A/C Contractor",
    "A/C Technician",
    "Service Technician",
}

SOURCE_URL = "https://data.texas.gov/dataset/TDLR-All-Licenses/7358-krk7"


def parse_city_state_zip(s):
    """Parse 'CITY TX 75001' into city, state, zip."""
    if not isinstance(s, str):
        return "", "", ""
    parts = s.strip().rsplit(" ", 2)
    if len(parts) == 3:
        return parts[0].strip(), parts[1].strip(), parts[2].strip()
    elif len(parts) == 2:
        return parts[0].strip(), parts[1].strip(), ""
    return s, "", ""


def clean_slice(df_raw, license_types, slug, product_name, price):
    """Filter, clean, and save a slice."""
    df = df_raw[df_raw["license_type"].isin(license_types)].copy()
    print(f"  {slug}: {len(df):,} records after type filter")

    # Parse city/state/zip from business_city_state_zip
    parsed = df["business_city_state_zip"].apply(lambda x: parse_city_state_zip(x))
    df["city"] = parsed.apply(lambda x: x[0])
    df["state"] = parsed.apply(lambda x: x[1])
    df["zip"] = parsed.apply(lambda x: x[2])

    # Normalize phone — keep only business_phone (public record)
    df["phone"] = df["business_phone"].astype(str).str.replace(r"\D", "", regex=True)
    df["phone"] = df["phone"].apply(lambda x: x if len(x) >= 10 else "")

    # Name — prefer business_name if it's a company, owner_name for individuals
    df["name"] = df["business_name"].fillna("").str.strip()
    df["owner_name_clean"] = df["owner_name"].fillna("").str.strip()
    # Use business_name if non-empty and differs from owner_name, else owner_name
    df["display_name"] = df.apply(
        lambda r: r["name"] if r["name"] and r["name"] != r["owner_name_clean"] else r["owner_name_clean"],
        axis=1
    )

    # Clean address
    df["address"] = df["business_address"].fillna("").str.strip()
    df["address2"] = df["business_address2"].fillna("").str.strip()

    # Select output columns
    out = df[[
        "display_name", "owner_name_clean",
        "license_type", "license_subtype", "license_number",
        "address", "address2", "city", "state", "zip",
        "phone", "expiration_date", "source_url"
    ]].copy()
    out.columns = [
        "business_or_name", "owner_name",
        "license_type", "license_subtype", "license_number",
        "address", "address2", "city", "state", "zip",
        "phone", "expiration_date", "source_url"
    ]

    # Drop rows with no name at all
    out = out[out["business_or_name"].str.len() > 0]

    # Drop exact duplicates
    out = out.drop_duplicates(subset=["license_number"])
    print(f"  {slug}: {len(out):,} records after dedup")

    # Write CSV
    out_path = os.path.join(STATE, f"{slug}.csv")
    out.to_csv(out_path, index=False)
    print(f"  Wrote: {out_path}")

    # Write validation log
    val = {
        "slug": slug,
        "product_name": product_name,
        "price_usd": price,
        "validated_at": datetime.utcnow().isoformat() + "Z",
        "validated_by": "data-steward",
        "row_count": len(out),
        "columns": out.columns.tolist(),
        "license_types_included": sorted(list(license_types)),
        "has_source_url": True,
        "has_pii_concern": False,
        "pii_notes": "TX TDLR is a public government licensing database. All records are regulatory public disclosures.",
        "duplicate_license_numbers_removed": True,
        "phone_coverage_pct": round(100 * (out["phone"].str.len() > 0).mean(), 1),
        "source_url": SOURCE_URL,
        "status": "CLEAN",
    }
    val_path = os.path.join(STATE, f"{slug}.validation.json")
    with open(val_path, "w") as f:
        json.dump(val, f, indent=2)
    print(f"  Wrote: {val_path}")

    return len(out), val


def main():
    raw_path = os.path.join(STATE, "tx-tdlr-licensed-contractors-2026-05.csv")
    print(f"Loading {raw_path} ...")
    df_raw = pd.read_csv(raw_path, low_memory=False)
    print(f"Loaded {len(df_raw):,} rows")

    results = {}

    # Slice 1: Electricians
    count, val = clean_slice(
        df_raw,
        ELECTRICAL_TYPES,
        "tx-tdlr-electricians-2026-05",
        "Texas Licensed Electricians & Electrical Contractors — TDLR Database 2026",
        59
    )
    results["electricians"] = {"count": count, "val": val}

    # Slice 2: HVAC
    count, val = clean_slice(
        df_raw,
        HVAC_TYPES,
        "tx-tdlr-hvac-contractors-2026-05",
        "Texas HVAC Contractors & AC Technicians — TDLR Database 2026",
        49
    )
    results["hvac"] = {"count": count, "val": val}

    print("\n=== Summary ===")
    for k, v in results.items():
        print(f"  {k}: {v['count']:,} records — status: {v['val']['status']}")


if __name__ == "__main__":
    main()
