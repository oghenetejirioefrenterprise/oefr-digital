#!/usr/bin/env python3
"""
Data-steward cleaning script for:
  faa-civil-aircraft-registration-2026-05.csv

Outputs:
  faa-civil-aircraft-registration-2026-05.cleaned.csv
  faa-civil-aircraft-registration-2026-05.validation.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATASETS = Path("/home/oghenetejiri/apps/dataStructured/state/datasets")
INPUT_CSV = DATASETS / "faa-civil-aircraft-registration-2026-05.csv"
OUTPUT_CSV = DATASETS / "faa-civil-aircraft-registration-2026-05.cleaned.csv"
REPORT_JSON = DATASETS / "faa-civil-aircraft-registration-2026-05.validation.json"

SLUG = "faa-civil-aircraft-registration-2026-05"
FALLBACK_SOURCE_URL = (
    "https://www.faa.gov/licenses_certificates/aircraft_certification/"
    "aircraft_registry/releasable_aircraft_download"
)
INPUT_ROW_COUNT = 306618  # known from harvest

# Valid US state/territory abbreviations
VALID_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
    "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
    "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
    # DC + territories
    "DC","PR","VI","GU","AS","MP",
    # Military APO/FPO
    "AA","AE","AP",
}


def write_fail_report(total_dropped, dups_removed, blank_n_dropped,
                      blank_reg_dropped, invalid_state_dropped, failure_reasons):
    """Write a FAIL validation report for a degenerate (empty post-filter) frame."""
    drop_pct = total_dropped / INPUT_ROW_COUNT * 100 if INPUT_ROW_COUNT else 0.0
    report = {
        "version": 1,
        "type": "validation_report",
        "slug": SLUG,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "row_count_input": INPUT_ROW_COUNT,
        "row_count_cleaned": 0,
        "rows_dropped": {
            "duplicates": int(dups_removed),
            "blank_n_number": int(blank_n_dropped),
            "blank_registrant_name": int(blank_reg_dropped),
            "invalid_state": int(invalid_state_dropped),
            "total": int(total_dropped),
            "pct_of_input": f"{drop_pct:.2f}%",
        },
        "null_rates": {},
        "duplicate_n_numbers_in_cleaned": 0,
        "distributions": {},
        "sample_rows": [],
        "status": "FAIL",
        "failure_reasons": failure_reasons,
    }
    print(f"Writing validation report → {REPORT_JSON} …", flush=True)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def main():
    # -----------------------------------------------------------------------
    # Load
    # -----------------------------------------------------------------------
    print("Loading CSV …", flush=True)
    df = pd.read_csv(INPUT_CSV, dtype=str, keep_default_na=False)
    print(f"  Loaded {len(df):,} rows, {len(df.columns)} columns", flush=True)

    # -----------------------------------------------------------------------
    # Step 1 — Deduplicate on n_number (keep first)
    # -----------------------------------------------------------------------
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["n_number"], keep="first")
    dups_removed = before_dedup - len(df)
    print(f"  Duplicates removed: {dups_removed:,}", flush=True)

    # -----------------------------------------------------------------------
    # Step 2 — Trim whitespace from all string columns
    # -----------------------------------------------------------------------
    str_cols = df.select_dtypes(include="object").columns.tolist()
    for col in str_cols:
        df[col] = df[col].str.strip()

    # -----------------------------------------------------------------------
    # Step 3 — Normalize empty / None / N/A to ""
    # -----------------------------------------------------------------------
    NONE_VALUES = {"None", "none", "NONE", "N/A", "n/a", "NA", "na"}
    for col in str_cols:
        df[col] = df[col].replace(NONE_VALUES, "")

    # -----------------------------------------------------------------------
    # Step 4 — n_number: drop blank or not starting with "N"
    # -----------------------------------------------------------------------
    before = len(df)
    df = df[df["n_number"].str.startswith("N", na=False) & (df["n_number"] != "")]
    blank_n_dropped = before - len(df)
    print(f"  Rows dropped (blank/invalid n_number): {blank_n_dropped:,}", flush=True)

    # -----------------------------------------------------------------------
    # Step 5 — registrant_name: drop completely blank
    # -----------------------------------------------------------------------
    before = len(df)
    df = df[df["registrant_name"] != ""]
    blank_reg_dropped = before - len(df)
    print(f"  Rows dropped (blank registrant_name): {blank_reg_dropped:,}", flush=True)

    # -----------------------------------------------------------------------
    # Step 6 — state: normalize to 2-letter uppercase, drop invalid
    # -----------------------------------------------------------------------
    df["state"] = df["state"].str.upper().str.strip()
    before = len(df)
    df = df[df["state"].isin(VALID_STATES)]
    invalid_state_dropped = before - len(df)
    print(f"  Rows dropped (invalid state): {invalid_state_dropped:,}", flush=True)

    # -----------------------------------------------------------------------
    # Step 7 — zip_code: strip to first 5 digits; blank if not parseable
    # -----------------------------------------------------------------------
    def normalize_zip(z):
        z = str(z).strip()
        digits = z[:5]
        if digits.isdigit() and len(digits) == 5:
            return digits
        return ""

    df["zip_code"] = df["zip_code"].apply(normalize_zip)

    # -----------------------------------------------------------------------
    # Step 8 — year_mfr: must be 4-digit int between 1900–2027; blank otherwise
    # -----------------------------------------------------------------------
    def normalize_year(y):
        try:
            v = int(str(y).strip())
            if 1900 <= v <= 2027:
                return str(v)
            return ""
        except (ValueError, TypeError):
            return ""

    df["year_mfr"] = df["year_mfr"].apply(normalize_year)

    # -----------------------------------------------------------------------
    # Step 9 — source_url: fill missing with fallback
    # -----------------------------------------------------------------------
    df["source_url"] = df["source_url"].apply(
        lambda u: u if u and u.strip() else FALLBACK_SOURCE_URL
    )

    # -----------------------------------------------------------------------
    # Step 10 — Drop status_code column
    # -----------------------------------------------------------------------
    if "status_code" in df.columns:
        df = df.drop(columns=["status_code"])
        print("  Dropped column: status_code", flush=True)

    # -----------------------------------------------------------------------
    # Degenerate-frame guard: if every row was filtered out, we cannot compute
    # null rates (division by zero) or sample rows (df.iloc[0]/[-1] IndexError).
    # Emit a FAIL report and exit non-zero instead of crashing.
    # -----------------------------------------------------------------------
    total_dropped = dups_removed + blank_n_dropped + blank_reg_dropped + invalid_state_dropped
    if len(df) == 0:
        failure_reasons = [
            "Cleaned frame has 0 rows after filtering — all input rows were "
            "dropped (possible schema drift or wrong column values). "
            f"Dropped {total_dropped:,} of {INPUT_ROW_COUNT:,} input rows."
        ]
        print("  FAIL: cleaned frame is empty after filtering", flush=True)
        write_fail_report(total_dropped, dups_removed, blank_n_dropped,
                          blank_reg_dropped, invalid_state_dropped, failure_reasons)
        print("\nDone. Status: FAIL", flush=True)
        for r in failure_reasons:
            print(f"  FAIL: {r}", flush=True)
        return 1

    # -----------------------------------------------------------------------
    # Write cleaned CSV
    # -----------------------------------------------------------------------
    print(f"Writing cleaned CSV → {OUTPUT_CSV} …", flush=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"  Wrote {len(df):,} rows", flush=True)

    # -----------------------------------------------------------------------
    # Validation report
    # -----------------------------------------------------------------------
    cleaned_cols = [c for c in df.columns]

    # Null/blank rates
    null_rates = {}
    for col in cleaned_cols:
        blank_count = (df[col] == "").sum()
        pct = blank_count / len(df) * 100
        null_rates[col] = f"{pct:.2f}%"

    # Duplicate n_numbers in cleaned output
    dup_n_count = df["n_number"].duplicated().sum()

    # Distributions
    def top_n_dist(series, n=5):
        return (
            series.replace("", pd.NA)
            .dropna()
            .value_counts()
            .head(n)
            .to_dict()
        )

    type_aircraft_dist = top_n_dist(df["type_aircraft"], 5)
    registrant_type_dist = top_n_dist(df["registrant_type"], 5)
    airworthiness_dist = top_n_dist(df["airworthiness_class"], 5)
    state_dist = top_n_dist(df["state"], 10)

    # Sample rows
    total_rows = len(df)
    mid_idx = total_rows // 2
    sample_rows = [
        df.iloc[0].to_dict(),
        df.iloc[mid_idx].to_dict(),
        df.iloc[-1].to_dict(),
    ]

    # PASS / FAIL determination
    failure_reasons = []

    if total_rows <= 250000:
        failure_reasons.append(f"Row count {total_rows:,} is <= 250,000")
    if null_rates.get("n_number", "100%") != "0.00%":
        failure_reasons.append(f"n_number null rate is non-zero: {null_rates['n_number']}")

    reg_blank_pct = float(null_rates.get("registrant_name", "0%").rstrip("%"))
    if reg_blank_pct >= 5.0:
        failure_reasons.append(f"registrant_name null rate {reg_blank_pct:.2f}% >= 5%")

    if null_rates.get("source_url", "100%") != "0.00%":
        failure_reasons.append(f"source_url null rate is non-zero: {null_rates['source_url']}")

    if dup_n_count > 0:
        failure_reasons.append(f"Duplicate n_numbers in cleaned output: {dup_n_count}")

    # Flag if more than 5% of rows were dropped
    drop_pct = total_dropped / INPUT_ROW_COUNT * 100
    if drop_pct > 5.0:
        failure_reasons.append(
            f"Total rows dropped ({total_dropped:,} = {drop_pct:.2f}%) exceeds 5% threshold"
        )

    status = "PASS" if not failure_reasons else "FAIL"

    report = {
        "version": 1,
        "type": "validation_report",
        "slug": SLUG,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "row_count_input": INPUT_ROW_COUNT,
        "row_count_cleaned": total_rows,
        "rows_dropped": {
            "duplicates": int(dups_removed),
            "blank_n_number": int(blank_n_dropped),
            "blank_registrant_name": int(blank_reg_dropped),
            "invalid_state": int(invalid_state_dropped),
            "total": int(total_dropped),
            "pct_of_input": f"{drop_pct:.2f}%",
        },
        "null_rates": null_rates,
        "duplicate_n_numbers_in_cleaned": int(dup_n_count),
        "distributions": {
            "type_aircraft": {k: int(v) for k, v in type_aircraft_dist.items()},
            "registrant_type": {k: int(v) for k, v in registrant_type_dist.items()},
            "airworthiness_class": {k: int(v) for k, v in airworthiness_dist.items()},
            "state_top10": {k: int(v) for k, v in state_dist.items()},
        },
        "sample_rows": sample_rows,
        "status": status,
    }

    if failure_reasons:
        report["failure_reasons"] = failure_reasons

    print(f"Writing validation report → {REPORT_JSON} …", flush=True)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Status: {status}", flush=True)
    if failure_reasons:
        for r in failure_reasons:
            print(f"  FAIL: {r}", flush=True)

    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
