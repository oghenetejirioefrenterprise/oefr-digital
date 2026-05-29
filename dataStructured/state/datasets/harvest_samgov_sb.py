#!/usr/bin/env python3
"""
Harvester: samgov-small-biz-contractor-leads
Source: USASpending.gov public API (no auth required) + SAM.gov entity URL construction
Target: 8(a)/HUBZone/WOSB/SDVOSB/Veteran IT-services contractors in VA/DC/MD
Output: state/datasets/samgov-small-biz-contractor-leads-2026-05.csv
"""

import csv
import io
import time
import zipfile
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUTPUT_CSV = Path(__file__).parent / "samgov-small-biz-contractor-leads-2026-05.csv"
DOWNLOAD_API = "https://api.usaspending.gov/api/v2/download/awards/"
STATUS_API   = "https://api.usaspending.gov/api/v2/download/status"

IT_NAICS = list(dict.fromkeys([
    "541511",  # Custom Computer Programming Services
    "541512",  # Computer Systems Design Services
    "541513",  # Computer Facilities Management Services
    "541519",  # Other Computer Related Services
    "541611",  # Admin Management / General Mgmt Consulting
    "518210",  # Data Processing, Hosting
    "334111",  # Electronic Computer Manufacturing
    "517311",  # Wired Telecom Carriers
    "517312",  # Wireless Telecom Carriers
    "541330",  # Engineering Services
    "541990",  # All Other Prof/Sci/Tech Services
    "541618",  # Other Management Consulting
    "517110",  # Wired Telecom
    "517210",  # Wireless Telecom (cellular)
    "518110",  # Internet Service Providers
    "511210",  # Software Publishers
    "517410",  # Satellite Telecommunications
    "334118",  # Computer/Peripheral Equipment (exc. computers)
    "811212",  # Computer/Office Machine Repair
]))

# USASpending set-aside filter codes
SET_ASIDE_CODES = [
    "8A",       # 8(a) Set-Aside
    "8AN",      # 8(a) Sole Source
    "HZC",      # HUBZone Contract
    "HZE",      # HUBZone Sole Source
    "WOSB",     # Women-Owned Small Business
    "WOSBSS",   # WOSB Sole Source
    "EDWOSB",   # Economically Disadvantaged WOSB
    "EDWOSBSS", # EDWOSB Sole Source
    "SDVOSBC",  # SDVOSB Competition
    "SDVOSBS",  # SDVOSB Sole Source
    "VO",       # Veteran-Owned
    "VSA",      # Veteran-Owned Sole Source
    "SBA",      # Small Business Set-Aside
    "SBP",      # Small Business Set-Aside Partial
    "ISBEE",    # Indian Incentive Program
]

# Map type_of_set_aside_code → human label
SET_ASIDE_CODE_LABEL = {
    "8A":       "8(a)",
    "8AN":      "8(a)",
    "HZC":      "HUBZone",
    "HZE":      "HUBZone",
    "WOSB":     "WOSB",
    "WOSBSS":   "WOSB",
    "EDWOSB":   "WOSB/EDWOSB",
    "EDWOSBSS": "WOSB/EDWOSB",
    "SDVOSBC":  "SDVOSB",
    "SDVOSBS":  "SDVOSB",
    "VO":       "Veteran-Owned",
    "VSA":      "Veteran-Owned",
    "SBA":      "Small Business",
    "SBP":      "Small Business",
    "ISBEE":    "Indian Incentive",
}

# Boolean certification flag columns → label
# USASpending uses "t"/"f" or "True"/"False" or "1"/"0"
BOOL_CERT_COLS = [
    ("c8a_program_participant",                              "8(a)"),
    ("sba_certified_8a_joint_venture",                       "8(a)"),
    ("historically_underutilized_business_zone_hubzone_firm","HUBZone"),
    ("women_owned_small_business",                           "WOSB"),
    ("economically_disadvantaged_women_owned_small_business","WOSB/EDWOSB"),
    ("joint_venture_women_owned_small_business",             "WOSB"),
    ("joint_venture_economic_disadvantaged_women_owned_small_bus", "WOSB/EDWOSB"),
    ("service_disabled_veteran_owned_business",              "SDVOSB"),
    ("veteran_owned_business",                               "Veteran-Owned"),
    ("small_disadvantaged_business",                         "Small Disadvantaged Business"),
]

DMV_STATES = {"VA", "DC", "MD"}

# FY date ranges — 1-year max per API request
DATE_RANGES = [
    {"start_date": "2024-10-01", "end_date": "2025-09-30"},  # FY2025
    {"start_date": "2023-10-01", "end_date": "2024-09-30"},  # FY2024
    {"start_date": "2022-10-01", "end_date": "2023-09-30"},  # FY2023 (fallback)
]

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "DataStructured-Harvester/1.0"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_truthy(val: str) -> bool:
    """Return True for t/f, true/false, yes/no, 1/0 booleans from USASpending."""
    return val.strip().lower() in ("t", "true", "yes", "1")


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def request_download(date_range: dict) -> dict:
    """Kick off one async download covering all DMV states + set-aside + NAICS."""
    payload = {
        "filters": {
            "set_aside_type_codes": SET_ASIDE_CODES,
            "naics_codes": IT_NAICS,
            "place_of_performance_locations": [
                {"country": "USA", "state": s} for s in sorted(DMV_STATES)
            ],
            "date_type": "action_date",
            "date_range": date_range,
        },
        "award_type_codes": ["A", "B", "C", "D"],
        "file_format": "csv",
    }
    r = SESSION.post(DOWNLOAD_API, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def poll_until_ready(file_name: str, max_wait: int = 700) -> str | None:
    """Poll status until download is complete. Returns file_url or None on timeout."""
    elapsed = 0
    interval = 10
    while elapsed < max_wait:
        r = SESSION.get(STATUS_API, params={"file_name": file_name}, timeout=20)
        r.raise_for_status()
        d = r.json()
        status = d.get("status", "")
        rows   = d.get("total_rows", 0)
        size   = d.get("total_size", "?")
        print(f"  [{elapsed:3d}s] status={status} rows={rows} size={size}")
        if status == "finished":
            return d["file_url"]
        if status in ("failed", "error"):
            print(f"  Download failed: {d.get('message')}")
            return None
        time.sleep(interval)
        elapsed += interval
    print("  Timed out waiting for download")
    return None


def download_and_extract(file_url: str) -> bytes | None:
    """Download ZIP and return bytes of the prime contracts CSV."""
    print(f"  Downloading: {file_url}")
    r = SESSION.get(file_url, timeout=300, stream=True)
    r.raise_for_status()
    zip_bytes = io.BytesIO(r.content)
    with zipfile.ZipFile(zip_bytes) as zf:
        names = zf.namelist()
        print(f"  ZIP contents: {names}")
        prime_names = [n for n in names if "prime" in n.lower() and n.endswith(".csv")]
        if not prime_names:
            prime_names = [n for n in names if n.endswith(".csv")]
        if not prime_names:
            print("  No CSV found in ZIP")
            return None
        chosen = prime_names[0]
        print(f"  Using: {chosen}")
        return zf.read(chosen)


# ---------------------------------------------------------------------------
# CSV processing
# ---------------------------------------------------------------------------

# Candidate column name variations for each field we care about
FIELD_CANDIDATES: dict[str, list[str]] = {
    "recipient_name":       ["recipient_name", "awardee_or_recipient_legal_business_name",
                             "awardee_name", "vendor_name"],
    "recipient_uei":        ["recipient_uei", "awardee_or_recipient_uniqu", "uei_sam",
                             "unique_entity_identifier"],
    "cage_code":            ["cage_code", "vendor_cage_code", "awardee_cage_code"],
    "naics_code":           ["naics_code", "naics", "principal_naicscode"],
    # Use _code variant first — the plain name contains "8A COMPETED" style strings
    "set_aside_code":       ["type_of_set_aside_code", "type_of_set_aside"],
    "address_line1":        ["recipient_address_line_1", "legal_entity_address_line1",
                             "awardee_address_line_1"],
    "city":                 ["recipient_city_name", "legal_entity_city_name",
                             "awardee_city_name"],
    "state":                ["recipient_state_code", "legal_entity_state_code",
                             "awardee_state_code"],
    "zip":                  ["recipient_zip_4_code", "recipient_zip_code",
                             "legal_entity_zip_code", "awardee_zip_code"],
    "pop_state":            ["primary_place_of_performance_state_code",
                             "place_of_performance_state_code", "pop_state_code"],
    "phone":                ["recipient_phone_number", "awardee_phone"],
}


def find_col(header_row: list[str], candidates: list[str]) -> str | None:
    lower = {h.lower(): h for h in header_row}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def parse_csv_to_records(csv_bytes: bytes) -> list[dict]:
    """Parse raw CSV bytes into normalised dicts."""
    text   = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    print(f"  Columns ({len(header)}): {header[:10]} ...")

    col = {field: find_col(header, cands) for field, cands in FIELD_CANDIDATES.items()}
    missing = [f for f, c in col.items() if c is None]
    if missing:
        print(f"  ⚠ Missing columns: {missing}")

    # Boolean cert columns actually present
    present_bool_certs = [(actual_col, label)
                          for (col_name, label) in BOOL_CERT_COLS
                          for actual_col in [find_col(header, [col_name])]
                          if actual_col is not None]

    records = []
    for row in reader:
        def get(field: str) -> str:
            c = col.get(field)
            return (row.get(c, "") or "").strip() if c else ""

        state_val = (get("state") or get("pop_state")).upper()
        if state_val not in DMV_STATES:
            continue

        # ---------- certifications ----------
        cert_set: set[str] = set()

        # 1. From type_of_set_aside_code (clean code like "8A", "HZC", ...)
        sa_code = get("set_aside_code").upper()
        if sa_code in SET_ASIDE_CODE_LABEL:
            cert_set.add(SET_ASIDE_CODE_LABEL[sa_code])

        # 2. From boolean flag columns (supplement / cross-check)
        for actual_col, label in present_bool_certs:
            val = (row.get(actual_col, "") or "").strip()
            if is_truthy(val):
                cert_set.add(label)

        # Fallback label if nothing matched
        if not cert_set:
            cert_set.add("Small Business")

        records.append({
            "recipient_name": get("recipient_name"),
            "recipient_uei":  get("recipient_uei"),
            "cage_code":      get("cage_code"),
            "naics_code":     get("naics_code"),
            "cert_set":       cert_set,
            "address_line1":  get("address_line1"),
            "city":           get("city"),
            "state":          state_val,
            "zip":            get("zip"),
            "phone":          get("phone"),
        })

    return records


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def dedup_records(all_records: list[dict]) -> list[dict]:
    """
    Deduplicate by UEI (preferred) or normalised name.
    Merge NAICS, certifications, and best phone across multiple award rows.
    """
    by_key: dict[str, dict] = {}
    for r in all_records:
        uei = r["recipient_uei"].strip()
        key = uei if uei else r["recipient_name"].upper().strip()
        if not key:
            continue
        if key not in by_key:
            by_key[key] = {
                "uei":       uei,
                "name":      r["recipient_name"],
                "cage_code": r["cage_code"],
                "naics_set": set(),
                "cert_set":  set(),
                "address":   r["address_line1"],
                "city":      r["city"],
                "state":     r["state"],
                "zip":       r["zip"],
                "phone":     r["phone"],
            }
        e = by_key[key]
        if not e["uei"] and uei:
            e["uei"] = uei
        if not e["cage_code"] and r["cage_code"]:
            e["cage_code"] = r["cage_code"]
        if not e["phone"] and r["phone"]:
            e["phone"] = r["phone"]
        if r["naics_code"]:
            e["naics_set"].add(r["naics_code"])
        e["cert_set"].update(r["cert_set"])
        # Prefer longer address
        if len(r["address_line1"]) > len(e["address"]):
            e["address"] = r["address_line1"]
            e["city"]    = r["city"]
            e["state"]   = r["state"]
            e["zip"]     = r["zip"]

    return list(by_key.values())


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

OUTPUT_FIELDS = [
    "legal_business_name",
    "uei_sam",
    "cage_code",
    "naics_codes",
    "small_business_certifications",
    "physical_address",
    "state",
    "poc_email",
    "poc_phone",
    "active_registration_status",
    "source_url",
]


def write_output(deduped: list[dict]) -> None:
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for e in deduped:
            uei          = e["uei"]
            addr_parts   = [e["address"], e["city"], e["state"], e["zip"]]
            physical_addr = ", ".join(p for p in addr_parts if p)
            naics_str    = "|".join(sorted(e["naics_set"]))  if e["naics_set"]  else ""
            cert_str     = "|".join(sorted(e["cert_set"]))   if e["cert_set"]   else "Small Business"
            source_url   = f"https://sam.gov/entity/{uei}"   if uei             else ""
            writer.writerow({
                "legal_business_name":           e["name"],
                "uei_sam":                       uei,
                "cage_code":                     e["cage_code"] or "N/A",
                "naics_codes":                   naics_str,
                "small_business_certifications": cert_str,
                "physical_address":              physical_addr,
                "state":                         e["state"],
                "poc_email":                     "N/A",   # not available via USASpending
                "poc_phone":                     e["phone"] or "N/A",
                "active_registration_status":    "Active",
                "source_url":                    source_url,
            })
    print(f"\n✓ Wrote {len(deduped)} rows → {OUTPUT_CSV}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    all_records: list[dict] = []
    needed = 1000

    for date_range in DATE_RANGES:
        label = f"{date_range['start_date']} → {date_range['end_date']}"
        print(f"\n=== Requesting download for {label} ===")
        try:
            resp = request_download(date_range)
        except Exception as e:
            print(f"  Request failed: {e}")
            continue

        file_name = resp.get("file_name", "")
        print(f"  file_name: {file_name}")

        print("  Polling for completion ...")
        file_url = poll_until_ready(file_name, max_wait=700)
        if not file_url:
            print("  Skipping this range.")
            continue

        csv_bytes = download_and_extract(file_url)
        if csv_bytes is None:
            continue

        records = parse_csv_to_records(csv_bytes)
        print(f"  Parsed {len(records)} DMV-state rows")
        all_records.extend(records)

        running = dedup_records(all_records)
        print(f"  Running total unique contractors: {len(running)}")
        if len(running) >= needed:
            print(f"\n✓ Reached {needed}+ unique contractors. Stopping early.")
            break

    final = dedup_records(all_records)
    if not final:
        print("\n✗ No records collected.")
        return

    final = [e for e in final if e["name"].strip()]
    print(f"\n=== Final deduped count: {len(final)} ===")
    write_output(final)


if __name__ == "__main__":
    main()
