#!/usr/bin/env python3
"""
Harvest IRS Exempt Organization Business Master File (BMF).

Sources:
  https://www.irs.gov/pub/irs-soi/eo1.csv  (NE + Mid-Atlantic + South)
  https://www.irs.gov/pub/irs-soi/eo2.csv  (Midwest + South-Central)
  https://www.irs.gov/pub/irs-soi/eo3.csv  (Mountain + Pacific)
  https://www.irs.gov/pub/irs-soi/eo4.csv  (Remaining US)
  https://www.irs.gov/pub/irs-soi/eo_pr.csv (Puerto Rico)
  https://www.irs.gov/pub/irs-soi/eo_xx.csv (International / APO / FPO)

All files are open public data; no login or API key required.
Output: irs-990-nonprofit-organization-directory-2026-05.csv + .harvest.json
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
CSV_PATH = OUTPUT_DIR / "irs-990-nonprofit-organization-directory-2026-05.csv"
REPORT_PATH = OUTPUT_DIR / "irs-990-nonprofit-organization-directory-2026-05.harvest.json"
SOURCE_BASE = "https://www.irs.gov/pub/irs-soi/"

BMF_FILES = ["eo1.csv", "eo2.csv", "eo3.csv", "eo4.csv", "eo_pr.csv", "eo_xx.csv"]

# Canonical output columns (IRS BMF column names → clean snake_case)
FIELDNAMES = [
    "ein",
    "organization_name",
    "ico",
    "street_address",
    "city",
    "state",
    "zip_code",
    "group_exemption",
    "subsection_code",
    "affiliation_code",
    "classification_code",
    "ruling_year",
    "deductibility_code",
    "foundation_code",
    "activity_1",
    "activity_2",
    "activity_3",
    "organization_code",
    "status_code",
    "tax_period",
    "asset_code",
    "income_code",
    "filing_req_code",
    "pf_filing_req_code",
    "accounting_period",
    "asset_amount",
    "income_amount",
    "revenue_amount",
    "ntee_code",
    "sort_name",
    "source_url",
]

SOURCE_URL = "https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf"


def parse_activity(raw):
    """IRS ACTIVITY field: 9-char string = three 3-char activity codes."""
    raw = str(raw).strip().zfill(9)
    return raw[0:3].lstrip("0"), raw[3:6].lstrip("0"), raw[6:9].lstrip("0")


def ruling_to_year(ruling):
    """RULING field is YYYYMM; extract YYYY."""
    s = str(ruling).strip()
    if len(s) >= 4 and s[:4].isdigit():
        return s[:4]
    return ""


def map_row(raw):
    """Map raw IRS BMF dict (upper-case keys) → clean output dict."""
    activity_raw = raw.get("ACTIVITY", "") or ""
    a1, a2, a3 = parse_activity(activity_raw)

    zip_raw = str(raw.get("ZIP", "") or "").strip()
    zip5 = zip_raw[:5] if zip_raw else ""

    return {
        "ein": str(raw.get("EIN", "") or "").strip(),
        "organization_name": str(raw.get("NAME", "") or "").strip(),
        "ico": str(raw.get("ICO", "") or "").strip(),
        "street_address": str(raw.get("STREET", "") or "").strip(),
        "city": str(raw.get("CITY", "") or "").strip(),
        "state": str(raw.get("STATE", "") or "").strip(),
        "zip_code": zip5,
        "group_exemption": str(raw.get("GROUP", "") or "").strip(),
        "subsection_code": str(raw.get("SUBSECTION", "") or "").strip(),
        "affiliation_code": str(raw.get("AFFILIATION", "") or "").strip(),
        "classification_code": str(raw.get("CLASSIFICATION", "") or "").strip(),
        "ruling_year": ruling_to_year(raw.get("RULING", "") or ""),
        "deductibility_code": str(raw.get("DEDUCTIBILITY", "") or "").strip(),
        "foundation_code": str(raw.get("FOUNDATION", "") or "").strip(),
        "activity_1": a1,
        "activity_2": a2,
        "activity_3": a3,
        "organization_code": str(raw.get("ORGANIZATION", "") or "").strip(),
        "status_code": str(raw.get("STATUS", "") or "").strip(),
        "tax_period": str(raw.get("TAX_PERIOD", "") or "").strip(),
        "asset_code": str(raw.get("ASSET_CD", "") or "").strip(),
        "income_code": str(raw.get("INCOME_CD", "") or "").strip(),
        "filing_req_code": str(raw.get("FILING_REQ_CD", "") or "").strip(),
        "pf_filing_req_code": str(raw.get("PF_FILING_REQ_CD", "") or "").strip(),
        "accounting_period": str(raw.get("ACCT_PD", "") or "").strip(),
        "asset_amount": str(raw.get("ASSET_AMT", "") or "").strip(),
        "income_amount": str(raw.get("INCOME_AMT", "") or "").strip(),
        "revenue_amount": str(raw.get("REVENUE_AMT", "") or "").strip(),
        "ntee_code": str(raw.get("NTEE_CD", "") or "").strip(),
        "sort_name": str(raw.get("SORT_NAME", "") or "").strip(),
        "source_url": SOURCE_URL,
    }


def download_file(filename):
    """Download a single IRS BMF CSV file; return text content."""
    url = SOURCE_BASE + filename
    print(f"  Downloading {url} ...", flush=True)
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    # IRS BMF files are UTF-8 (or latin-1 fallback)
    try:
        return r.content.decode("utf-8")
    except UnicodeDecodeError:
        return r.content.decode("latin-1")


def main():
    start = datetime.now(timezone.utc)
    total_raw = 0
    files_harvested = []
    errors = []

    print("IRS 990 BMF Harvest", flush=True)
    print(f"Output: {CSV_PATH}", flush=True)

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fout:
        writer = csv.DictWriter(fout, fieldnames=FIELDNAMES)
        writer.writeheader()

        for filename in BMF_FILES:
            url = SOURCE_BASE + filename
            try:
                text = download_file(filename)
                reader = csv.DictReader(StringIO(text))
                file_count = 0
                for raw in reader:
                    row = map_row(raw)
                    writer.writerow(row)
                    file_count += 1
                total_raw += file_count
                files_harvested.append({"file": filename, "url": url, "rows": file_count})
                print(f"    → {file_count:,} rows", flush=True)
                time.sleep(0.5)  # polite pause between files
            except Exception as e:
                msg = f"{filename}: {e}"
                print(f"  ERROR: {msg}", file=sys.stderr)
                errors.append(msg)

    end = datetime.now(timezone.utc)
    elapsed = round((end - start).total_seconds(), 1)

    report = {
        "version": 1,
        "type": "harvest_report",
        "slug": "irs-990-nonprofit-organization-directory-2026-05",
        "harvested_at": end.isoformat(),
        "elapsed_seconds": elapsed,
        "source_url": SOURCE_URL,
        "files": files_harvested,
        "row_count_raw": total_raw,
        "columns": FIELDNAMES,
        "errors": errors,
        "status": "SUCCESS" if not errors else "PARTIAL",
        "notes": (
            "IRS Exempt Organization Business Master File (BMF) downloaded from "
            "https://www.irs.gov/pub/irs-soi/. Six regional CSV files: eo1–eo4 "
            "(domestic US regions), eo_pr (Puerto Rico), eo_xx (international/APO/FPO). "
            "All files are freely downloadable with no authentication. "
            "ACTIVITY field (9-char) split into three 3-char activity codes. "
            "RULING field (YYYYMM) converted to 4-digit year. "
            "ZIP truncated to 5 digits. Source URL appended to every row."
        ),
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nTotal rows: {total_raw:,}", flush=True)
    print(f"Elapsed: {elapsed}s", flush=True)
    if errors:
        print(f"Errors: {errors}", file=sys.stderr)
    print(f"Report: {REPORT_PATH}", flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
