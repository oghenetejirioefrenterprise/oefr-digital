#!/usr/bin/env python3
"""
Florida Sunbiz Corporate Filing Parser
Source: Florida Division of Corporations (DOS) daily SFTP bulk data
Public credentials: sftp.floridados.gov  user=Public  pass=PubAccess1845!
Field layout: https://dos.sunbiz.org/data-definitions/cor.html
Record length: 1440 chars (fixed-width)
"""

import csv
import glob
import hashlib
import os
import re
import sys
from datetime import datetime, timezone

# ── Field positions (1-indexed in docs; converted to 0-indexed Python slices) ──
RECORD_LEN = 1440

CORP_NUMBER_START   = 0;   CORP_NUMBER_END   = 12
CORP_NAME_START     = 12;  CORP_NAME_END     = 204
STATUS_POS          = 204
FILING_TYPE_START   = 205; FILING_TYPE_END   = 220
ADDR1_START         = 220; ADDR1_END         = 262
ADDR2_START         = 262; ADDR2_END         = 304
CITY_START          = 304; CITY_END          = 332
STATE_START         = 332; STATE_END         = 334
ZIP_START           = 334; ZIP_END           = 344
COUNTRY_START       = 344; COUNTRY_END       = 346
MAIL_ADDR1_START    = 346; MAIL_ADDR1_END    = 388
MAIL_ADDR2_START    = 388; MAIL_ADDR2_END    = 430
MAIL_CITY_START     = 430; MAIL_CITY_END     = 458
MAIL_STATE_START    = 458; MAIL_STATE_END    = 460
MAIL_ZIP_START      = 460; MAIL_ZIP_END      = 470
MAIL_COUNTRY_START  = 470; MAIL_COUNTRY_END  = 472
FILE_DATE_START     = 472; FILE_DATE_END     = 480
FEI_START           = 480; FEI_END           = 494
GT6_OFFICERS_POS    = 494
LAST_TRANS_START    = 495; LAST_TRANS_END    = 503
STATE_CTRY_START    = 503; STATE_CTRY_END    = 505
# Report year/date fields 506-544 (skipped)
RA_NAME_START       = 544; RA_NAME_END       = 586
RA_TYPE_POS         = 586
RA_ADDR_START       = 587; RA_ADDR_END       = 629
RA_CITY_START       = 629; RA_CITY_END       = 657
RA_STATE_START      = 657; RA_STATE_END      = 659
RA_ZIP_START        = 659; RA_ZIP_END        = 668

# Officer 1 block starts at 668 (0-indexed) = position 669 (1-indexed)
# Empirically determined: Title(4), Type(1), Name(36), Addr(36), City(28), State(2), Zip(9) = 116 chars
# Docs say 669-788 = 120 chars; the remaining 4 are filler between officers.
OFF1_TITLE_START    = 668;  OFF1_TITLE_END  = 672   # 4 chars (e.g. "AMBR", "MGR ", "PRES")
OFF1_TYPE_POS       = 672                            # 1 char: P=person, C=corp
OFF1_NAME_START     = 673;  OFF1_NAME_END   = 709   # 36 chars
OFF1_ADDR_START     = 709;  OFF1_ADDR_END   = 745
OFF1_CITY_START     = 745;  OFF1_CITY_END   = 773
OFF1_STATE_START    = 773;  OFF1_STATE_END  = 775
OFF1_ZIP_START      = 775;  OFF1_ZIP_END    = 784

# Known filing type codes → human-readable labels
# FL SOS uses two coding conventions: legacy "FL*" and newer plain "DOM*"/"FOR*"
FILING_TYPE_MAP = {
    # Domestic LLC variants
    "FLAL":  "Limited Liability Company",
    "FLLC":  "Limited Liability Company",
    "DOML":  "Limited Liability Company",
    "DOMLC": "Limited Liability Company",
    # Domestic Profit Corporation
    "FLINC": "Profit Corporation",
    "DOMP":  "Profit Corporation",
    "DOMPF": "Profit Corporation",
    # Domestic Non-Profit
    "FLNP":  "Non-Profit Corporation",
    "DOMNP": "Non-Profit Corporation",
    # Domestic Limited Partnership
    "FLLP":  "Limited Partnership",
    "DOMLP": "Limited Partnership",
    # Domestic Limited Liability Limited Partnership
    "FLLLLP":"Limited Liability Limited Partnership",
    "FLLLP": "Limited Liability Limited Partnership",
    "DOMLLP":"Limited Liability Limited Partnership",
    # Florida Professional Association
    "FLPA":  "Professional Association",
    # Florida General Partnership
    "FLGP":  "General Partnership",
    # Florida Co-operative
    "FICA":  "Co-operative Association",
    "FLCOOP":"Co-operative Association",
    # Foreign entities
    "FORL":  "Foreign Limited Liability Company",
    "FORLC": "Foreign Limited Liability Company",
    "FORLLC":"Foreign Limited Liability Company",
    "FORP":  "Foreign Profit Corporation",
    "FORPC": "Foreign Profit Corporation",
    "FORNP": "Foreign Non-Profit Corporation",
    "FORLP": "Foreign Limited Partnership",
    # Trusts / other
    "TRUST": "Business Trust",
    "ENTRT": "Business Entity",
}


def clean(s: str) -> str:
    """Strip padding and normalize whitespace."""
    if not s:
        return ""
    return " ".join(s.strip().replace("\x00", "").split())


def parse_date(raw: str) -> str:
    """Convert MMDDYYYY → YYYY-MM-DD. Return empty string on failure."""
    raw = raw.strip().replace("\x00", "")
    if len(raw) == 8 and raw.isdigit():
        try:
            mm, dd, yyyy = raw[:2], raw[2:4], raw[4:]
            dt = datetime(int(yyyy), int(mm), int(dd))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def build_address(*parts) -> str:
    """Concatenate non-empty address parts into a single string."""
    return ", ".join(p for p in (clean(p) for p in parts) if p)


def sunbiz_url(corp_number: str) -> str:
    num = corp_number.strip()
    return (
        f"https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResultDetail"
        f"?inquiryType=DocumentNumber&inquiryDirectionType=ForwardList"
        f"&searchNameOrder={num}&masterSequenceNumber=&topmostSequenceNumber="
        f"&listNameIndex=0&listStatus=A"
    )


def parse_record(line: str, source_file: str, fetched_at: str) -> dict | None:
    """
    Parse a single 1440-char fixed-width record.
    Returns None for records that should be skipped (inactive, foreign, wrong length).
    """
    # Pad or ignore malformed lines
    if len(line) < 480:          # need at least up to file date
        return None

    line = line.ljust(RECORD_LEN)

    status      = line[STATUS_POS]
    filing_type = clean(line[FILING_TYPE_START:FILING_TYPE_END])
    file_date   = parse_date(line[FILE_DATE_START:FILE_DATE_END])
    corp_number = clean(line[CORP_NUMBER_START:CORP_NUMBER_END])
    corp_name   = clean(line[CORP_NAME_START:CORP_NAME_END])

    # Skip inactive records
    if status != "A":
        return None

    # Derive entity_type label
    ft_key = filing_type[:6].strip().upper()
    entity_type_label = FILING_TYPE_MAP.get(ft_key, filing_type if filing_type else "Unknown")

    # Build principal address
    principal_address = build_address(
        line[ADDR1_START:ADDR1_END],
        line[ADDR2_START:ADDR2_END],
        line[CITY_START:CITY_END],
        line[STATE_START:STATE_END],
        line[ZIP_START:ZIP_END],
    )
    # Fall back to mailing address if principal is blank
    if not principal_address:
        principal_address = build_address(
            line[MAIL_ADDR1_START:MAIL_ADDR1_END],
            line[MAIL_ADDR2_START:MAIL_ADDR2_END],
            line[MAIL_CITY_START:MAIL_CITY_END],
            line[MAIL_STATE_START:MAIL_STATE_END],
            line[MAIL_ZIP_START:MAIL_ZIP_END],
        )

    # Registered agent
    ra_name    = clean(line[RA_NAME_START:RA_NAME_END])
    ra_address = build_address(
        line[RA_ADDR_START:RA_ADDR_END],
        line[RA_CITY_START:RA_CITY_END],
        line[RA_STATE_START:RA_STATE_END],
        line[RA_ZIP_START:RA_ZIP_END],
    )

    # Officer 1 name (organizer/officer)
    off1_name = ""
    if len(line) >= OFF1_NAME_END:
        off1_name = clean(line[OFF1_NAME_START:OFF1_NAME_END])

    # Stable deterministic ID
    row_id = hashlib.md5(f"FL:{corp_number}".encode()).hexdigest()[:12]

    return {
        "id":                       row_id,
        "entity_name":              corp_name,
        "entity_type":              entity_type_label,
        "state":                    "FL",
        "filing_date":              file_date,
        "registered_agent_name":    ra_name,
        "registered_agent_address": ra_address,
        "principal_address":        principal_address,
        "organizer_officer_name":   off1_name,
        "source_url":               sunbiz_url(corp_number),
        "source_fetched_at":        fetched_at,
    }


def parse_files(raw_dir: str, output_csv: str) -> int:
    """Parse all daily FL files in raw_dir, write to output_csv. Returns row count."""
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    columns = [
        "id", "entity_name", "entity_type", "state", "filing_date",
        "registered_agent_name", "registered_agent_address",
        "principal_address", "organizer_officer_name",
        "source_url", "source_fetched_at",
    ]

    files = sorted(glob.glob(os.path.join(raw_dir, "*.txt")))
    if not files:
        print(f"ERROR: No .txt files found in {raw_dir}", file=sys.stderr)
        return 0

    seen_ids = set()
    rows = []

    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"  Parsing {filename} …", file=sys.stderr)
        with open(filepath, "r", encoding="latin-1", errors="replace") as fh:
            for line in fh:
                line = line.rstrip("\n").rstrip("\r")
                rec = parse_record(line, filename, fetched_at)
                if rec is None:
                    continue
                # Deduplicate by ID (same entity can appear in multiple daily files)
                if rec["id"] in seen_ids:
                    continue
                seen_ids.add(rec["id"])
                # Only include records with a filing date (new formations have it)
                if not rec["filing_date"]:
                    continue
                rows.append(rec)

    print(f"  Total unique active records with filing date: {len(rows)}", file=sys.stderr)

    with open(output_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


if __name__ == "__main__":
    RAW_DIR    = os.path.join(os.path.dirname(__file__), "raw_fl")
    OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "new-business-formations-csv-2026-05.csv")

    print(f"Parsing FL Sunbiz files from {RAW_DIR} …")
    count = parse_files(RAW_DIR, OUTPUT_CSV)
    print(f"Done. {count} rows → {OUTPUT_CSV}")
