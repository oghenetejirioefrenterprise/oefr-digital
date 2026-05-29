#!/usr/bin/env python3
"""
Filter NPPES full bulk CSV to Dentist/Dental taxonomy codes.
Uses streaming extraction to avoid writing the full 11GB file to disk.
Output: state/nppes-dentists-dental-practices-2026-05.csv
"""
import zipfile
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path

ZIP_PATH = "/tmp/nppes_weekly.zip"
NPI_FILENAME = "npidata_pfile_20050523-20260412.csv"
STATE_DIR = Path("/home/oghenetejiri/apps/dataStructured/state")
OUTPUT_CSV = STATE_DIR / "nppes-dentists-dental-practices-2026-05.csv"
OUTPUT_HARVEST = STATE_DIR / "nppes-dentists-dental-practices-2026-05.harvest.json"
SOURCE_URL = "https://download.cms.gov/nppes/NPPES_Data_Dissemination_April_2026_V2.zip"

# All dental taxonomy codes (NUCC Health Care Provider Taxonomy)
DENTAL_CODES = {
    '122300000X',  # Dentist
    '1223G0001X',  # General Practice Dentist
    '1223D0001X',  # Dental Public Health
    '1223E0200X',  # Endodontics
    '1223X0400X',  # Oral & Maxillofacial Pathology
    '1223X0008X',  # Oral & Maxillofacial Radiology
    '1223S0112X',  # Oral & Maxillofacial Surgery
    '1223P0221X',  # Orthodontics
    '1223P0300X',  # Pediatric Dentistry (Pedodontics)
    '1223P0700X',  # Periodontics
    '1223P0106X',  # Prosthodontics
    '126800000X',  # Dental Hygienist (often co-located, useful for dental practice lists)
    '1268D0000X',  # Dentist (other)
}

TAX_COLS = [f'Healthcare Provider Taxonomy Code_{i}' for i in range(1, 16)]

COLUMN_MAP = {
    'NPI': 'npi',
    'Entity Type Code': 'entity_type',
    'Provider First Name': 'first_name',
    'Provider Last Name (Legal Name)': 'last_name',
    'Provider Credential Text': 'credential',
    'Provider Organization Name (Legal Business Name)': 'practice_name',
    'Provider First Line Business Practice Location Address': 'street1',
    'Provider Second Line Business Practice Location Address': 'street2',
    'Provider Business Practice Location Address City Name': 'city',
    'Provider Business Practice Location Address State Name': 'state',
    'Provider Business Practice Location Address Postal Code': 'zip_code',
    'Provider Business Practice Location Address Telephone Number': 'phone',
    'Healthcare Provider Taxonomy Code_1': 'taxonomy_code',
    'Provider License Number_1': 'license_number',
    'NPI Deactivation Date': 'deactivation_date',
    'Last Update Date': 'last_update_date',
}

CHUNKSIZE = 50_000

def dental_mask(chunk):
    """Vectorized boolean mask: True for rows where any taxonomy column matches a
    dental code. Replaces a per-row apply(axis=1) over 15 columns (O(rows*15) in
    pure Python) with vectorized pandas ops — typically 10-100x faster on the
    full NPPES file."""
    present_cols = [c for c in TAX_COLS if c in chunk.columns]
    if not present_cols:
        return pd.Series(False, index=chunk.index)
    # Strip whitespace vectorized (dtype=str, but be defensive about NaN), then
    # test membership against the dental code set across all taxonomy columns.
    stripped = chunk[present_cols].apply(lambda s: s.str.strip())
    return stripped.isin(DENTAL_CODES).any(axis=1)

def normalize_zip(z):
    if not isinstance(z, str):
        return ""
    z = z.strip()
    if len(z) > 5 and z[5] == '-':
        return z[:5]
    return z[:5] if len(z) >= 5 else z

print(f"[{datetime.now().isoformat()}] Opening ZIP: {ZIP_PATH}")

# Fail loud with an actionable message if the transient /tmp download is missing
# (it is wiped on reboot and there is no download step in this script).
if not os.path.exists(ZIP_PATH):
    print(
        f"ERROR: NPPES ZIP not found at {ZIP_PATH}.\n"
        f"This is a transient /tmp file with no download step in this script.\n"
        f"Download the weekly dissemination from {SOURCE_URL} to {ZIP_PATH} and re-run."
    )
    exit(1)


def find_npi_member(zf):
    """Locate the main npidata_pfile CSV inside the ZIP. CMS changes the dated
    filename every weekly release, so discover it dynamically instead of
    hardcoding a specific dissemination date. Excludes the FileHeader companion."""
    candidates = [
        n for n in zf.namelist()
        if n.lower().endswith(".csv")
        and "npidata_pfile" in n.lower()
        and "fileheader" not in n.lower()
    ]
    if not candidates:
        return None
    # Prefer the exact hardcoded name if still present, else the largest match.
    if NPI_FILENAME in candidates:
        return NPI_FILENAME
    # Largest file is the main data file (vs. any header/aux CSVs).
    return max(candidates, key=lambda n: zf.getinfo(n).file_size)


records = []
raw_count = 0
chunk_num = 0

with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
    npi_member = find_npi_member(zf)
    if npi_member is None:
        print(
            f"ERROR: No npidata_pfile_*.csv member found inside {ZIP_PATH}.\n"
            f"ZIP contents: {zf.namelist()[:20]}"
        )
        exit(1)
    print(f"[{datetime.now().isoformat()}] Reading member: {npi_member}")
    with zf.open(npi_member) as f:
        for chunk in pd.read_csv(
            f,
            chunksize=CHUNKSIZE,
            dtype=str,
            low_memory=False,
            encoding='utf-8',
            on_bad_lines='skip',
        ):
            chunk_num += 1
            raw_count += len(chunk)
            if chunk_num % 20 == 0:
                print(f"  Chunk {chunk_num}: {raw_count:,} rows scanned, {len(records):,} dental found")

            # Filter to dental taxonomies (vectorized — see dental_mask)
            mask = dental_mask(chunk)
            matched = chunk[mask]
            if matched.empty:
                continue

            # Skip deactivated NPIs
            if 'NPI Deactivation Date' in matched.columns:
                matched = matched[matched['NPI Deactivation Date'].isna() | (matched['NPI Deactivation Date'].str.strip() == '')]

            # Map columns
            keep = {}
            for src, dst in COLUMN_MAP.items():
                if src in matched.columns:
                    keep[dst] = matched[src].fillna('').astype(str).str.strip()
                else:
                    keep[dst] = ''

            df_out = pd.DataFrame(keep)
            df_out['zip_code'] = df_out['zip_code'].apply(normalize_zip)

            # Build display name
            df_out['name'] = df_out.apply(
                lambda r: r['practice_name'] if r['practice_name'] and r['entity_type'] == '2'
                else f"{r['first_name']} {r['last_name']} {r['credential']}".strip() if r['entity_type'] == '1'
                else r['practice_name'] or f"{r['first_name']} {r['last_name']}".strip(),
                axis=1
            )
            df_out['source_url'] = SOURCE_URL

            records.append(df_out)

print(f"[{datetime.now().isoformat()}] Scan complete. Raw rows: {raw_count:,}")

if not records:
    print("ERROR: No dental records found!")
    exit(1)

df_all = pd.concat(records, ignore_index=True)
print(f"Total dental records: {len(df_all):,}")

# Remove deactivated (belt+suspenders)
df_all = df_all[~df_all['deactivation_date'].str.strip().astype(bool)]
print(f"After deactivation filter: {len(df_all):,}")

# Remove rows with no state (likely bad data)
df_all = df_all[df_all['state'].str.len() == 2]
print(f"After state filter: {len(df_all):,}")

# Drop duplicates on NPI
df_all = df_all.drop_duplicates(subset=['npi'])
print(f"After dedup: {len(df_all):,}")

# Phone coverage
phone_pct = round(100 * (df_all['phone'].str.len() > 0).mean(), 1)
print(f"Phone coverage: {phone_pct}%")

# State breakdown (top 10)
state_counts = df_all['state'].value_counts().head(10).to_dict()
print(f"Top states: {state_counts}")

# Taxonomy breakdown
tax_counts = df_all['taxonomy_code'].value_counts().head(10).to_dict()
print(f"Top taxonomy codes: {tax_counts}")

# Write output
output_cols = [
    'npi', 'name', 'first_name', 'last_name', 'credential',
    'practice_name', 'taxonomy_code', 'license_number', 'entity_type',
    'street1', 'street2', 'city', 'state', 'zip_code', 'phone',
    'last_update_date', 'source_url'
]
STATE_DIR.mkdir(parents=True, exist_ok=True)
df_all[output_cols].to_csv(OUTPUT_CSV, index=False)
print(f"Wrote: {OUTPUT_CSV}")

# Harvest log
harvest = {
    "slug": "nppes-dentists-dental-practices-2026-05",
    "source_url": SOURCE_URL,
    "source_file": npi_member,
    "download_date": datetime.now().isoformat() + "Z",
    "harvested_by": "data-engineer",
    "raw_row_count": raw_count,
    "dental_row_count": len(df_all),
    "phone_coverage_pct": phone_pct,
    "taxonomy_codes": list(DENTAL_CODES),
    "top_states": state_counts,
    "top_taxonomy_codes": tax_counts,
    "output_file": str(OUTPUT_CSV),
    "status": "COMPLETE",
}
with open(OUTPUT_HARVEST, 'w') as f:
    json.dump(harvest, f, indent=2)
print(f"Wrote: {OUTPUT_HARVEST}")
print(f"\n✓ NPPES Dental harvest complete: {len(df_all):,} records")
