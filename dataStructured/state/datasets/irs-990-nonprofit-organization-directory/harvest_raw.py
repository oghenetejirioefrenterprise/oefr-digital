#!/usr/bin/env python3
"""
Harvest IRS Exempt Organization Business Master File (BMF) - raw format.

Downloads eo1.csv–eo4.csv from IRS, writes raw-20260509.csv with
original IRS column names + source_url, plus metadata.json and provenance.json.
"""

import csv
import json
import sys
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import requests

OUTPUT_DIR = Path(__file__).parent
CSV_PATH = OUTPUT_DIR / "raw-20260509.csv"
META_PATH = OUTPUT_DIR / "metadata.json"
PROV_PATH = OUTPUT_DIR / "provenance.json"

# IRS publishes these at irs-soi; apps.irs.gov/epostcard URL listed in product brief
DOWNLOAD_BASE = "https://www.irs.gov/pub/irs-soi/"
SOURCE_URL = "https://apps.irs.gov/pub/epostcard/data-download/"

BMF_FILES = ["eo1.csv", "eo2.csv", "eo3.csv", "eo4.csv"]

# Output column spec (original IRS BMF names)
FIELDNAMES = [
    "NAME",
    "EIN",
    "STREET",
    "CITY",
    "STATE",
    "ZIP",
    "GROUP",
    "SUBSECTION",
    "AFFILIATION",
    "CLASSIFICATION",
    "RULING",
    "DEDUCTIBILITY",
    "FOUNDATION",
    "ACTIVITY",
    "ORGANIZATION",
    "STATUS",
    "INCOME_CD",
    "FILING_REQ_CD",
    "PF_FILING_REQ_CD",
    "ACCT_PRD",
    "ASSET_CD",
    "INCOME_AMT",
    "ASSET_AMT",
    "NTEE_CD",
    "SORT_NAME",
    "source_url",
]

# Mapping from IRS raw header → our output column
IRS_TO_OUTPUT = {
    "NAME": "NAME",
    "EIN": "EIN",
    "STREET": "STREET",
    "CITY": "CITY",
    "STATE": "STATE",
    "ZIP": "ZIP",
    "GROUP": "GROUP",
    "SUBSECTION": "SUBSECTION",
    "AFFILIATION": "AFFILIATION",
    "CLASSIFICATION": "CLASSIFICATION",
    "RULING": "RULING",
    "DEDUCTIBILITY": "DEDUCTIBILITY",
    "FOUNDATION": "FOUNDATION",
    "ACTIVITY": "ACTIVITY",
    "ORGANIZATION": "ORGANIZATION",
    "STATUS": "STATUS",
    "INCOME_CD": "INCOME_CD",
    "FILING_REQ_CD": "FILING_REQ_CD",
    "PF_FILING_REQ_CD": "PF_FILING_REQ_CD",
    "ACCT_PD": "ACCT_PRD",   # IRS uses ACCT_PD; we normalise to ACCT_PRD
    "ACCT_PRD": "ACCT_PRD",
    "ASSET_CD": "ASSET_CD",
    "INCOME_AMT": "INCOME_AMT",
    "ASSET_AMT": "ASSET_AMT",
    "NTEE_CD": "NTEE_CD",
    "SORT_NAME": "SORT_NAME",
}


def download(filename):
    url = DOWNLOAD_BASE + filename
    print(f"  Downloading {url} ...", flush=True)
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    try:
        return r.content.decode("utf-8"), url
    except UnicodeDecodeError:
        return r.content.decode("latin-1"), url


def map_row(raw):
    out = {}
    for irs_col, out_col in IRS_TO_OUTPUT.items():
        val = raw.get(irs_col, "") or ""
        out[out_col] = str(val).strip()
    out["source_url"] = SOURCE_URL
    return out


def main():
    start = datetime.now(timezone.utc)
    total_rows = 0
    files_meta = []
    errors = []

    print(f"Output → {CSV_PATH}", flush=True)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()

        for filename in BMF_FILES:
            try:
                text, url = download(filename)
                reader = csv.DictReader(StringIO(text))
                count = 0
                for raw in reader:
                    writer.writerow(map_row(raw))
                    count += 1
                total_rows += count
                files_meta.append({"file": filename, "url": url, "rows": count})
                print(f"    ✓ {count:,} rows", flush=True)
                time.sleep(0.5)
            except Exception as e:
                msg = f"{filename}: {e}"
                print(f"  ERROR: {msg}", file=sys.stderr)
                errors.append(msg)

    end = datetime.now(timezone.utc)
    elapsed = round((end - start).total_seconds(), 1)

    # metadata.json
    meta = {
        "version": 1,
        "slug": "irs-990-nonprofit-organization-directory",
        "harvest_date": "2026-05-09",
        "harvested_at": end.isoformat(),
        "row_count": total_rows,
        "columns": FIELDNAMES,
        "status": "READY_FOR_STEWARD",
        "errors": errors,
        "elapsed_seconds": elapsed,
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)

    # provenance.json
    prov = {
        "version": 1,
        "slug": "irs-990-nonprofit-organization-directory",
        "harvest_date": "2026-05-09",
        "harvested_at": end.isoformat(),
        "harvested_by": "data-engineer",
        "source_name": "IRS Exempt Organization Business Master File (BMF)",
        "source_url": SOURCE_URL,
        "source_license": "Public Domain — IRS public data, no authentication required",
        "download_urls": [DOWNLOAD_BASE + f for f in BMF_FILES],
        "files_harvested": files_meta,
        "row_count": total_rows,
        "output_file": str(CSV_PATH),
        "notes": (
            "IRS BMF files eo1–eo4 downloaded from https://www.irs.gov/pub/irs-soi/ "
            "(canonical listing page: https://apps.irs.gov/pub/epostcard/data-download/). "
            "Four domestic US regional files only (no PR/international for this product). "
            "Columns preserved as original IRS header names. source_url set to base listing URL."
        ),
    }
    with open(PROV_PATH, "w") as f:
        json.dump(prov, f, indent=2)

    print(f"\nTotal rows : {total_rows:,}", flush=True)
    print(f"Elapsed    : {elapsed}s", flush=True)
    print(f"Output CSV : {CSV_PATH}", flush=True)
    print(f"Metadata   : {META_PATH}", flush=True)
    print(f"Provenance : {PROV_PATH}", flush=True)
    if errors:
        print(f"ERRORS: {errors}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
