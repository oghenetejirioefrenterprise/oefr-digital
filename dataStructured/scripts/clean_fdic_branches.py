#!/usr/bin/env python3
"""
Data Steward: Clean and validate FDIC bank branch data.
Input: raw-YYYYMMDD.csv + metadata.json
Output: clean-YYYYMMDD.csv + quality-report.json
"""

import csv
import json
import random
import time
import requests
from datetime import datetime
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "state" / "datasets" / "fdic-bank-branch-directory"

def load_raw_csv(csv_path):
    """Load raw CSV into list of dicts."""
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def schema_integrity_check(rows):
    """Ensure required columns exist and drop malformed rows."""
    required_cols = ["id", "institution_name", "address", "city", "state", "source_url"]
    clean_rows = []
    dropped = 0

    for row in rows:
        # Check if all required columns have non-empty values
        if all(row.get(col, "").strip() for col in required_cols):
            clean_rows.append(row)
        else:
            dropped += 1

    return clean_rows, {"dropped_malformed": dropped}

def deduplicate(rows):
    """Remove exact duplicates by ID."""
    seen = set()
    clean_rows = []
    dupes = 0

    for row in rows:
        row_id = row.get("id", "")
        if row_id not in seen:
            seen.add(row_id)
            clean_rows.append(row)
        else:
            dupes += 1

    return clean_rows, {"duplicates_removed": dupes}

def null_garbage_scrub(rows):
    """Clean null/garbage values in critical fields."""
    clean_rows = []
    fixed = 0

    garbage_values = {"", "N/A", "TBD", "null", "NULL", "None", "NONE", "-"}

    for row in rows:
        # Clean each field
        for key, val in row.items():
            if val.strip() in garbage_values:
                row[key] = ""
                fixed += 1

        clean_rows.append(row)

    return clean_rows, {"garbage_values_cleaned": fixed}

def source_url_liveness_check(rows, sample_rate=0.10):
    """Sample 10% of rows and HEAD-request their source URLs."""
    sample_size = min(100, max(10, int(len(rows) * sample_rate)))  # Cap at 100 checks
    sample = random.sample(rows, min(sample_size, len(rows)))

    dead_count = 0
    checked_count = 0

    for row in sample:
        url = row.get("source_url", "")
        if not url:
            continue

        # One retry with a short backoff so a single transient network blip
        # doesn't get counted as a dead link (which could push the dead-rate
        # over 5% and wrongly REJECT an otherwise-good dataset).
        is_dead = True
        for attempt in range(2):
            try:
                resp = requests.head(url, timeout=5, allow_redirects=True)
                is_dead = resp.status_code >= 400
                break
            except requests.RequestException:
                if attempt == 0:
                    time.sleep(1)  # brief backoff before the single retry
                # on final attempt, leave is_dead = True
        if is_dead:
            dead_count += 1
        checked_count += 1

    dead_rate = dead_count / checked_count if checked_count > 0 else 0

    return {
        "sample_size": checked_count,
        "dead_links": dead_count,
        "dead_rate": round(dead_rate, 3),
        "status": "PASS" if dead_rate < 0.05 else "FAIL"
    }

def format_normalization(rows):
    """Normalize dates and numbers."""
    clean_rows = []
    normalized = 0

    for row in rows:
        # Established date: ensure YYYY-MM-DD or empty
        est_date = row.get("established_date", "").strip()
        if est_date and len(est_date) == 8 and est_date.isdigit():
            # Format: YYYYMMDD -> YYYY-MM-DD
            row["established_date"] = f"{est_date[:4]}-{est_date[4:6]}-{est_date[6:8]}"
            normalized += 1

        clean_rows.append(row)

    # Count only rows whose date was actually reformatted, not every row.
    return clean_rows, {"date_formats_normalized": normalized}

def main():
    # Find latest raw CSV
    raw_files = sorted(DATASET_DIR.glob("raw-*.csv"))
    if not raw_files:
        print("[steward] ERROR: No raw CSV found. Aborting.")
        return 1

    raw_csv_path = raw_files[-1]
    print(f"[steward] Loading {raw_csv_path.name}...")
    rows = load_raw_csv(raw_csv_path)
    initial_count = len(rows)
    print(f"[steward] Initial row count: {initial_count}")

    transformations = []

    # 1. Schema integrity
    rows, stats = schema_integrity_check(rows)
    transformations.append({"step": "schema_integrity", "stats": stats})
    print(f"[steward] Schema check: {stats['dropped_malformed']} malformed rows dropped")

    # 2. Deduplication
    rows, stats = deduplicate(rows)
    transformations.append({"step": "deduplication", "stats": stats})
    print(f"[steward] Deduplication: {stats['duplicates_removed']} duplicates removed")

    # 3. Null/garbage scrub
    rows, stats = null_garbage_scrub(rows)
    transformations.append({"step": "null_garbage_scrub", "stats": stats})
    print(f"[steward] Garbage scrub: {stats['garbage_values_cleaned']} garbage values cleaned")

    # 4. Source URL liveness (sample 10%)
    print(f"[steward] Checking source URL liveness (10% sample)...")
    liveness_stats = source_url_liveness_check(rows)
    transformations.append({"step": "source_url_liveness", "stats": liveness_stats})
    print(f"[steward] Liveness check: {liveness_stats['dead_links']}/{liveness_stats['sample_size']} dead ({liveness_stats['dead_rate']*100:.1f}%)")

    if liveness_stats["status"] == "FAIL":
        print(f"[steward] REJECT: > 5% dead source URLs. Unblocker: Re-harvest with live sources.")
        # Write rejection report
        quality_report = {
            "version": 1,
            "slug": "fdic-bank-branch-directory",
            "status": "REJECTED",
            "initial_row_count": initial_count,
            "final_row_count": len(rows),
            "transformations": transformations,
            "unblocker": "Re-harvest: > 5% of source URLs are dead. Update API query or source."
        }
        report_path = DATASET_DIR / "quality-report.json"
        with open(report_path, "w") as f:
            json.dump(quality_report, f, indent=2)
        print(f"[steward] ✗ Wrote rejection report to {report_path}")
        return 1

    # 5. Format normalization
    rows, stats = format_normalization(rows)
    transformations.append({"step": "format_normalization", "stats": stats})
    print(f"[steward] Format normalization: {stats['date_formats_normalized']} dates normalized")

    # Check signal:noise ratio
    dropped = initial_count - len(rows)
    signal_noise_ratio = len(rows) / initial_count if initial_count > 0 else 0
    print(f"[steward] Signal:noise ratio: {signal_noise_ratio*100:.1f}% ({len(rows)}/{initial_count})")

    if signal_noise_ratio < 0.70:
        print(f"[steward] REJECT: Signal:noise < 70%. Too much data loss.")
        quality_report = {
            "version": 1,
            "slug": "fdic-bank-branch-directory",
            "status": "REJECTED",
            "initial_row_count": initial_count,
            "final_row_count": len(rows),
            "transformations": transformations,
            "unblocker": f"Signal:noise ratio {signal_noise_ratio*100:.1f}% is below 70% threshold. Review raw data quality."
        }
        report_path = DATASET_DIR / "quality-report.json"
        with open(report_path, "w") as f:
            json.dump(quality_report, f, indent=2)
        print(f"[steward] ✗ Wrote rejection report to {report_path}")
        return 1

    # Write clean CSV
    today = datetime.now().strftime("%Y%m%d")
    clean_csv_path = DATASET_DIR / f"clean-{today}.csv"

    fieldnames = list(rows[0].keys())
    with open(clean_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[steward] ✓ Wrote {len(rows)} clean rows to {clean_csv_path}")

    # Write quality report
    quality_report = {
        "version": 1,
        "slug": "fdic-bank-branch-directory",
        "status": "APPROVED",
        "initial_row_count": initial_count,
        "final_row_count": len(rows),
        "signal_noise_ratio": round(signal_noise_ratio, 3),
        "transformations": transformations,
        "refresh_cadence": "monthly",
        "notes": "High-quality government API data. Minimal cleaning required. Monthly refresh recommended."
    }

    report_path = DATASET_DIR / "quality-report.json"
    with open(report_path, "w") as f:
        json.dump(quality_report, f, indent=2)

    print(f"[steward] ✓ Wrote quality report to {report_path}")
    print("[steward] ✓ Data Steward sign-off: APPROVED")
    return 0

if __name__ == "__main__":
    exit(main())
