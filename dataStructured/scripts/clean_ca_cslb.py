#!/usr/bin/env python3
"""
Clean CA CSLB licensed contractor CSV.
Input:  state/ca-cslb-licensed-contractors-2026-05.csv
Output: state/ca-cslb-licensed-contractors-2026-05.cleaned.csv
        state/ca-cslb-licensed-contractors-2026-05.validation.json
"""

import os, json, re
import pandas as pd
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(BASE, "state")

SLUG = "ca-cslb-licensed-contractors-2026-05"

def clean_phone(s):
    if not isinstance(s, str):
        return ""
    digits = re.sub(r"\D", "", s)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == "1":
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return ""

def main():
    in_path = os.path.join(STATE, f"{SLUG}.csv")
    print(f"Loading {in_path} ...")
    df = pd.read_csv(in_path, low_memory=False)
    print(f"Loaded {len(df):,} rows")
    # True raw loaded row count, captured before any filtering, for accurate lineage.
    raw_count = len(df)

    # Normalize strings
    for col in ["business_name", "dba", "full_business_name", "city", "state",
                "zip_code", "county", "mailing_address", "license_classifications",
                "entity_type", "license_status"]:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    # Ensure optional columns referenced below exist so we never KeyError on a
    # harvested CSV that happens to omit them (the guarded loop above proves
    # these columns are not guaranteed to be present).
    for c in ("full_business_name", "business_phone"):
        if c not in df.columns:
            df[c] = ""

    # Preferred display name: use full_business_name if available, else business_name
    df["display_name"] = df.apply(
        lambda r: r["full_business_name"] if r["full_business_name"] else r["business_name"],
        axis=1
    )

    # Clean phone
    df["phone_clean"] = df["business_phone"].apply(clean_phone)

    # Zip — keep first 5 digits
    df["zip_clean"] = df["zip_code"].astype(str).str[:5].str.strip()

    # Filter: keep only CLEAR status (already filtered at harvest, but ensure)
    before = len(df)
    df = df[df["license_status"] == "CLEAR"]
    print(f"  Status filter: {before:,} → {len(df):,} CLEAR records")

    # Drop duplicates on license_number
    before = len(df)
    df = df.drop_duplicates(subset=["license_number"])
    print(f"  Dedup: {before:,} → {len(df):,} unique license numbers")

    # Build clean output
    out = df[[
        "license_number", "display_name", "dba",
        "license_classifications", "entity_type",
        "mailing_address", "city", "state", "zip_clean", "county",
        "phone_clean", "expiration_date", "issue_date",
        "source_url"
    ]].copy()
    out.columns = [
        "license_number", "business_name", "dba",
        "license_class", "entity_type",
        "address", "city", "state", "zip", "county",
        "phone", "expiration_date", "issue_date",
        "source_url"
    ]

    # Drop rows with no business name
    out = out[out["business_name"].str.len() > 0]
    print(f"  After name filter: {len(out):,} records")

    # Write cleaned CSV
    out_path = os.path.join(STATE, f"{SLUG}.cleaned.csv")
    out.to_csv(out_path, index=False)
    print(f"  Wrote: {out_path}")

    # License class breakdown
    class_counts = out["license_class"].value_counts().head(10).to_dict()

    # Phone coverage
    phone_pct = round(100 * (out["phone"].str.len() > 0).mean(), 1)

    # Validation log
    val = {
        "slug": SLUG,
        "product_name": "California Licensed Contractors — CSLB Database 2026",
        "price_usd": 79,
        "validated_at": datetime.now().isoformat() + "Z",
        "validated_by": "data-steward",
        "raw_row_count": raw_count,
        "clean_row_count": len(out),
        "columns": out.columns.tolist(),
        "license_status_filter": "CLEAR only",
        "phone_coverage_pct": phone_pct,
        "has_source_url": True,
        "top_license_classes": class_counts,
        "duplicate_license_numbers_removed": True,
        "status": "CLEAN",
    }
    val_path = os.path.join(STATE, f"{SLUG}.validation.json")
    with open(val_path, "w") as f:
        json.dump(val, f, indent=2)
    print(f"  Wrote: {val_path}")

    print(f"\n✓ CA CSLB clean complete: {len(out):,} records, {phone_pct}% phone coverage")
    print(f"  Top classes: {class_counts}")

if __name__ == "__main__":
    main()
