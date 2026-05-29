#!/usr/bin/env python3
"""
harvest_nppes_pharmacy.py
Harvest CMS NPPES Type-2 organizational NPIs filtered by pharmacy taxonomy codes.

Steps:
  1. Download NPPES bulk ZIP (if not cached at NPPES_ZIP) and stream-filter for
     pharmacy taxonomy codes (333600000X family) — does NOT write the full 11 GB file.
  2. Filter to entity_type == 2 (organizational / facility) only.
  3. Cross-reference DEA Controlled Substance Registrant public file to attach
     DEA numbers and active dispensing status where available.
  4. Apply chain-exclusion filter: regex against top-30 chain DBA names + corporate-
     owner entity match; flag each row independent vs. chain.
  5. For TX/CA/FL/NY/PA: attach state board facility license number, status, and
     pharmacist-in-charge where publicly downloadable.
  6. Write state/datasets/independent-retail-pharmacy-directory/raw-pharmacies.csv
     and harvest.json manifest.

Public data only: NPPES, DEA FOIA registrant file, state pharmacy boards.
No PHI, no patient data.
"""

import io
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

# ─── Paths ───────────────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).resolve().parents[1]
SLUG = "independent-retail-pharmacy-directory"
DATASET_DIR = WORKSPACE / "state" / "datasets" / SLUG
DATASET_DIR.mkdir(parents=True, exist_ok=True)

NPPES_ZIP = Path("/tmp/nppes_weekly.zip")
DEA_LOCAL = Path("/tmp/dea_pharmacies.csv")
OUTPUT_CSV = DATASET_DIR / "raw-pharmacies.csv"
HARVEST_JSON = DATASET_DIR / "harvest.json"

# ─── Source URLs ──────────────────────────────────────────────────────────────
NPPES_URL = "https://download.cms.gov/nppes/NPPES_Data_Dissemination_April_2026_V2.zip"

# DEA Controlled Substance Registrant public files (tried in order)
DEA_URLS = [
    # DEA ARCOS Retail Drug Summary — pharmacy registrant file (FOIA release)
    "https://www.deadiversion.usdoj.gov/arcos/retail_drug_summary/pharmacies.csv",
    # Alternate DEA diversion reporting endpoint
    "https://www.deadiversion.usdoj.gov/registration/reports/pharmacies.csv",
]

# ─── Pharmacy Taxonomy Codes (NUCC 2024 Health Care Provider Taxonomy) ────────
PHARMACY_CODES = {
    "333600000X",  # Community/Retail (Pharmacy) — parent code
    "3336C0002X",  # Clinic Pharmacy
    "3336C0003X",  # Community/Retail Pharmacy
    "3336C0004X",  # Compounding Pharmacy
    "3336H0001X",  # Home Infusion Therapy Pharmacy
    "3336I0012X",  # Institutional Pharmacy
    "3336L0003X",  # Long-term Care Pharmacy
    "3336M0002X",  # Mail Order Pharmacy
    "3336M0003X",  # Managed Care Organization Pharmacy
    "3336N0007X",  # Nuclear Pharmacy
    "3336S0011X",  # Specialty Pharmacy
}

TAXONOMY_LABELS = {
    "333600000X": "Community/Retail Pharmacy",
    "3336C0002X": "Clinic Pharmacy",
    "3336C0003X": "Community/Retail Pharmacy",
    "3336C0004X": "Compounding Pharmacy",
    "3336H0001X": "Home Infusion Therapy Pharmacy",
    "3336I0012X": "Institutional Pharmacy",
    "3336L0003X": "Long-term Care Pharmacy",
    "3336M0002X": "Mail Order Pharmacy",
    "3336M0003X": "Managed Care Organization Pharmacy",
    "3336N0007X": "Nuclear Pharmacy",
    "3336S0011X": "Specialty Pharmacy",
}

TAX_COLS = [f"Healthcare Provider Taxonomy Code_{i}" for i in range(1, 16)]

COLUMN_MAP = {
    "NPI": "npi",
    "Entity Type Code": "entity_type",
    "Provider Organization Name (Legal Business Name)": "legal_entity_name",
    "Provider Other Organization Name": "dba_name",
    "Provider Other Organization Name Type Code": "dba_name_type",
    "Provider First Line Business Practice Location Address": "street1",
    "Provider Second Line Business Practice Location Address": "street2",
    "Provider Business Practice Location Address City Name": "city",
    "Provider Business Practice Location Address State Name": "state",
    "Provider Business Practice Location Address Postal Code": "zip_code",
    "Provider Business Practice Location Address Telephone Number": "phone",
    "Healthcare Provider Taxonomy Code_1": "taxonomy_code_1",
    "Healthcare Provider Taxonomy Code_2": "taxonomy_code_2",
    "Provider License Number_1": "license_number_1",
    "Provider License Number State Code_1": "license_state_1",
    "NPI Deactivation Date": "deactivation_date",
    "Last Update Date": "last_update_date",
    "Authorized Official Last Name": "authorized_official_last",
    "Authorized Official First Name": "authorized_official_first",
    "Authorized Official Title or Position": "authorized_official_title",
    "Is Organization Subpart": "is_subpart",
    "Parent Organization LBN": "parent_org_name",
    "Parent Organization TIN": "parent_org_tin",
}

CHUNKSIZE = 50_000

# ─── Chain Exclusion Patterns ─────────────────────────────────────────────────
# National and regional chain pharmacy / grocery-chain pharmacy DBA patterns
_CHAIN_DBA_PATTERNS = [
    # Top national chains
    r"\bCVS\b",
    r"\bWALGREEN",
    r"\bRITE\s*AID\b",
    r"\bWAL[- ]?MART\b",
    r"\bKROGER\b",
    r"\bPUBLIX\b",
    r"\bCOSTCO\b",
    r"\bSAM'?S\s+CLUB\b",
    r"\bSAM'?S\s+WEST\b",
    r"\bALBERTSONS?\b",
    r"\bSAFEWAY\b",
    r"\bH-?E-?B\b",
    r"\bTARGET\b",
    r"\bWEGMANS?\b",
    # Grocery chain pharmacies
    r"\bMEIJER\b",
    r"\bHARRIS\s+TEETER\b",
    r"\bWINN[\s-]?DIXIE\b",
    r"\bECKERD\b",
    r"\bLONG\s+DRUG\b",
    r"\bBROOKS?\s+PHARM",
    r"\bDUANE\s+READE\b",
    r"\bOSCO\b",
    r"\bSAV-?ON\b",
    r"\bFRED\s+MEYER\b",
    r"\bVONS?\b",
    r"\bSHOPRITE\b",
    r"\bGIANT\s+(EAGLE|FOOD)\b",
    r"\bSTOP\s*&\s*SHOP\b",
    r"\bRALPH'?S\b",
    r"\bFRY'?S?\s+(FOOD|MARKET)\b",
    r"\bKINGS?\s+(SUPER)?MARKET\b",
    r"\bSMITH'?S\s+(FOOD|MARKET)\b",
    r"\bFOOD\s+(LION|CITY|WORLD)\b",
    r"\bINGLES?\b",
    r"\bBILO\b",
    r"\bPIGGLY\s+WIGGLY\b",
    r"\bWEIS\s+(MARKET|PHARM)\b",
    # LTC / mail-order chains
    r"\bOMNICARE\b",
    r"\bPHARMERICA\b",
    r"\bBIGLOTS?\b",
    r"\bBIOSCRIPT\b",
    r"\bAMERICARE\b",
    r"\bEXPRESS\s*SCRIPTS?\b",
    r"\bOPTUMRX\b",
    r"\bCVS\s+CAREMARK\b",
    r"\bMEDCO\b",
    r"\bPRIME\s*THERAPEUTICS\b",
    r"\bHUMANA\s+PHARM",
    r"\bKINDRED\b",
    r"\bBRIGHTSPRING\b",
    r"\bENCORE\s+HEALTHCARE\b",
    # Warehouse / club stores
    r"\bBJ'?S\s+(WHOLESALE|CLUB)\b",
    r"\bDOLLAR\s+GENERAL\b",
    r"\bDOLLAR\s+TREE\b",
    # Note: Health Mart, Medicine Shoppe, and Good Neighbor are franchises
    # but members are often independently owned; exclude only branded corporate ops:
    r"\bMEDICINE\s+SHOPPE\s+CORP",
    r"\bHEALTH\s+MART\s+CORP",
]

# Corporate legal-entity name patterns (parent_org_name / legal_entity_name)
_CORPORATE_ENTITY_PATTERNS = [
    r"CVS HEALTH",
    r"CVS PHARMACY",
    r"WALGREEN CO",
    r"WALGREENS BOOTS",
    r"RITE AID CORP",
    r"WAL-?MART STORES",
    r"WALMART INC",
    r"KROGER CO",
    r"KROGER PHARM",
    r"PUBLIX SUPER",
    r"COSTCO WHOLESALE",
    r"SAMS? WEST INC",
    r"WAL-MART REAL ESTATE",
    r"ALBERTSONS COMPANIES",
    r"SAFEWAY INC",
    r"H E B GROCERY",
    r"TARGET CORP",
    r"WEGMANS FOOD",
    r"OMNICARE INC",
    r"PHARMERICA CORP",
    r"KINDRED HEALTHCARE",
    r"BIOSCRIPT INC",
    r"BRIGHTSPRING HEALTH",
    r"EXPRESS SCRIPTS",
    r"OPTUMRX INC",
    r"CVS CAREMARK",
    r"MEDCO HEALTH",
    r"MEIJER INC",
    r"HARRIS TEETER",
    r"WINN-DIXIE",
    r"FRED MEYER STORES",
    r"RITE AID HDQTRS",
]

CHAIN_DBA_RE = re.compile("|".join(_CHAIN_DBA_PATTERNS), re.IGNORECASE)
CORPORATE_RE = re.compile("|".join(_CORPORATE_ENTITY_PATTERNS), re.IGNORECASE)


def is_chain(row) -> bool:
    """Return True if DBA name or legal entity name matches a known chain."""
    dba = str(row.get("dba_name", "") or "")
    legal = str(row.get("legal_entity_name", "") or "")
    parent = str(row.get("parent_org_name", "") or "")
    if CHAIN_DBA_RE.search(dba) or CHAIN_DBA_RE.search(legal):
        return True
    if CORPORATE_RE.search(legal) or CORPORATE_RE.search(parent):
        return True
    return False


# ─── Helpers ──────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def normalize_zip(z) -> str:
    if not isinstance(z, str):
        return ""
    z = z.strip()
    if len(z) > 5 and z[5] == "-":
        return z[:5]
    return z[:5] if len(z) >= 5 else z


def pharmacy_mask(chunk: pd.DataFrame) -> pd.Series:
    """Vectorized mask: True for rows where ANY taxonomy column is a pharmacy code."""
    present = [c for c in TAX_COLS if c in chunk.columns]
    if not present:
        return pd.Series(False, index=chunk.index)
    stripped = chunk[present].apply(lambda s: s.str.strip())
    return stripped.isin(PHARMACY_CODES).any(axis=1)


def find_npi_member(zf: zipfile.ZipFile) -> str | None:
    """Locate the main npidata_pfile CSV inside the ZIP dynamically."""
    candidates = [
        n for n in zf.namelist()
        if n.lower().endswith(".csv")
        and "npidata_pfile" in n.lower()
        and "fileheader" not in n.lower()
    ]
    if not candidates:
        return None
    # Largest file = main data file
    return max(candidates, key=lambda n: zf.getinfo(n).file_size)


# ─── Step 1: Download NPPES ───────────────────────────────────────────────────
def ensure_nppes_zip() -> None:
    if NPPES_ZIP.exists():
        log(f"NPPES ZIP already cached at {NPPES_ZIP} ({NPPES_ZIP.stat().st_size:,} bytes)")
        return
    log(f"Downloading NPPES bulk ZIP from {NPPES_URL} …")
    log("This is a large file (≈ 4–8 GB compressed). This will take several minutes.")
    with requests.get(NPPES_URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        downloaded = 0
        with open(NPPES_ZIP, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MB chunks
                f.write(chunk)
                downloaded += len(chunk)
                if total and downloaded % (100 << 20) == 0:
                    pct = 100 * downloaded / total
                    log(f"  {downloaded / (1 << 20):.0f} MB / {total / (1 << 20):.0f} MB ({pct:.1f}%)")
    log(f"Download complete: {NPPES_ZIP.stat().st_size:,} bytes")


# ─── Step 2: Stream-filter NPPES ─────────────────────────────────────────────
def harvest_nppes() -> tuple[pd.DataFrame, str, int]:
    """Stream the NPPES bulk ZIP and return (DataFrame of pharmacy orgs, zip member name, raw_row_count)."""
    records = []
    raw_count = 0
    chunk_num = 0

    with zipfile.ZipFile(NPPES_ZIP, "r") as zf:
        npi_member = find_npi_member(zf)
        if npi_member is None:
            log(f"ERROR: No npidata_pfile_*.csv in ZIP. Contents: {zf.namelist()[:10]}")
            sys.exit(1)
        log(f"Streaming member: {npi_member}")
        with zf.open(npi_member) as f:
            for chunk in pd.read_csv(
                f,
                chunksize=CHUNKSIZE,
                dtype=str,
                low_memory=False,
                encoding="utf-8",
                on_bad_lines="skip",
            ):
                chunk_num += 1
                raw_count += len(chunk)
                if chunk_num % 20 == 0:
                    log(f"  Chunk {chunk_num}: {raw_count:,} rows scanned, {len(records):,} pharmacy orgs found")

                # Filter to pharmacy taxonomy codes
                mask = pharmacy_mask(chunk)
                matched = chunk[mask]
                if matched.empty:
                    continue

                # Type 2 (organizational) only
                if "Entity Type Code" in matched.columns:
                    matched = matched[matched["Entity Type Code"].str.strip() == "2"]
                if matched.empty:
                    continue

                # Skip deactivated NPIs
                if "NPI Deactivation Date" in matched.columns:
                    matched = matched[
                        matched["NPI Deactivation Date"].isna()
                        | (matched["NPI Deactivation Date"].str.strip() == "")
                    ]
                if matched.empty:
                    continue

                # Map columns
                keep = {}
                for src, dst in COLUMN_MAP.items():
                    if src in matched.columns:
                        keep[dst] = matched[src].fillna("").astype(str).str.strip()
                    else:
                        keep[dst] = ""
                df_out = pd.DataFrame(keep)
                df_out["zip_code"] = df_out["zip_code"].apply(normalize_zip)
                df_out["source_url"] = NPPES_URL
                records.append(df_out)

    log(f"NPPES scan complete. Raw rows: {raw_count:,}")
    if not records:
        log("ERROR: No pharmacy records found!")
        sys.exit(1)

    df = pd.concat(records, ignore_index=True)
    # Belt-and-suspenders deactivation filter
    df = df[~df["deactivation_date"].str.strip().astype(bool)]
    # Require 2-letter state code
    df = df[df["state"].str.len() == 2]
    # Deduplicate on NPI
    df = df.drop_duplicates(subset=["npi"])
    log(f"After filters: {len(df):,} pharmacy org records")
    return df, npi_member, raw_count


# ─── Step 3: DEA Cross-reference ─────────────────────────────────────────────
def fetch_dea_data() -> tuple[pd.DataFrame | None, str]:
    """
    Attempt to download the DEA Controlled Substance Registrant public file.
    Returns (DataFrame with dea_number/dea_status indexed by some key, source_url)
    or (None, note) if unavailable.
    """
    if DEA_LOCAL.exists():
        log(f"DEA file cached at {DEA_LOCAL}")
        try:
            df = pd.read_csv(DEA_LOCAL, dtype=str)
            return df, str(DEA_LOCAL)
        except Exception as e:
            log(f"DEA cache read failed: {e}")

    for url in DEA_URLS:
        log(f"Trying DEA source: {url}")
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and len(r.content) > 1000:
                DEA_LOCAL.write_bytes(r.content)
                df = pd.read_csv(io.StringIO(r.text), dtype=str)
                log(f"DEA data downloaded: {len(df):,} rows from {url}")
                return df, url
            else:
                log(f"  HTTP {r.status_code} or empty response from {url}")
        except Exception as e:
            log(f"  DEA download failed ({url}): {e}")

    log("DEA bulk registrant file not available via public download. "
        "All dispensing pharmacies must hold active DEA registration (21 CFR § 1301). "
        "Verify individual registrations at: https://www.deadiversion.usdoj.gov/registration/index.html")
    return None, "NOT_AVAILABLE"


def attach_dea(df: pd.DataFrame, dea_df: pd.DataFrame | None) -> pd.DataFrame:
    """
    Cross-reference DEA data against the pharmacy dataset.
    Adds columns: dea_number, dea_schedule, dea_status, dea_business_activity.
    """
    df["dea_number"] = ""
    df["dea_status"] = ""
    df["dea_business_activity"] = ""
    df["dea_registration_required"] = "True"  # all dispensing pharmacies must be registered

    if dea_df is None:
        df["dea_note"] = (
            "DEA bulk registrant file not publicly available. "
            "Verify at https://www.deadiversion.usdoj.gov/registration/index.html"
        )
        return df

    # DEA data may have various column schemas depending on the release.
    # Try common column names for NPI or address-based matching.
    dea_df.columns = [c.strip().lower().replace(" ", "_") for c in dea_df.columns]
    log(f"DEA columns: {list(dea_df.columns[:15])}")

    # Attempt NPI-based join if column exists
    if "npi" in dea_df.columns:
        dea_indexed = dea_df.set_index("npi")
        def _get_dea(npi):
            if npi in dea_indexed.index:
                row = dea_indexed.loc[npi]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                return (
                    str(row.get("dea_number", row.get("dea_reg_num", row.get("registration_number", "")))),
                    str(row.get("activity_code", row.get("business_activity", ""))),
                    str(row.get("expire_date", row.get("expiration_date", ""))),
                )
            return "", "", ""
        dea_fields = df["npi"].apply(_get_dea)
        df["dea_number"] = dea_fields.apply(lambda x: x[0])
        df["dea_business_activity"] = dea_fields.apply(lambda x: x[1])
        df["dea_status"] = dea_fields.apply(lambda x: "active" if x[2] else "")
        matched = (df["dea_number"] != "").sum()
        log(f"DEA join by NPI: {matched:,} / {len(df):,} matched")
    else:
        log("DEA data has no NPI column — DEA number enrichment skipped.")
        df["dea_note"] = "DEA data available but no NPI key for joining."

    return df


# ─── Step 4: Chain Exclusion ──────────────────────────────────────────────────
def apply_chain_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Add chain_flag column: 'independent' | 'chain'."""
    df["chain_flag"] = df.apply(
        lambda r: "chain" if is_chain(r) else "independent", axis=1
    )
    chain_ct = (df["chain_flag"] == "chain").sum()
    indep_ct = (df["chain_flag"] == "independent").sum()
    log(f"Chain filter: {chain_ct:,} chain / {indep_ct:,} independent ({len(df):,} total)")
    return df


# ─── Step 5: State Board Enrichment ──────────────────────────────────────────
# State-specific publicly downloadable license data.
# Each function returns a dict: {(name_key): {license_number, license_status, pharmacist_in_charge}}
# or an empty dict if unavailable.

STATE_BOARD_META = {
    "TX": {
        "description": "Texas State Board of Pharmacy (TSBP) — Facility License List",
        "url": "https://www.pharmacy.texas.gov/files/fac_licenses.xlsx",
        "fallback_url": "https://www.pharmacy.texas.gov/general/statistics.asp",
        "lookup_url": "https://www.pharmacy.texas.gov/general/fac-lic.asp",
    },
    "CA": {
        "description": "California Board of Pharmacy — DCA Licensee Data",
        "url": "https://data.dca.ca.gov/api/views/64cg-jy5t/rows.csv?accessType=DOWNLOAD",
        "fallback_url": "https://www.pharmacy.ca.gov/about/licensee_list.shtml",
        "lookup_url": "https://search.dca.ca.gov/",
    },
    "FL": {
        "description": "Florida Department of Health — Board of Pharmacy",
        "url": None,  # Requires MQA portal; no direct bulk download
        "lookup_url": "https://mqa-internet.doh.state.fl.us/MQASearchServices/HealthCareProviders",
    },
    "NY": {
        "description": "New York State Education Department — Office of Professions (Pharmacy)",
        "url": None,  # Requires NYSED eServices portal
        "lookup_url": "https://eservices.op.nysed.gov/pls/apex/f?p=145:1",
    },
    "PA": {
        "description": "Pennsylvania State Board of Pharmacy — PALS",
        "url": None,  # Requires PALS portal
        "lookup_url": "https://www.pals.pa.gov/",
    },
}


def _try_download_csv(url: str, state: str) -> pd.DataFrame | None:
    """Attempt HTTP download of a state board CSV/Excel; return DataFrame or None."""
    try:
        log(f"  [{state}] Fetching: {url}")
        r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or len(r.content) < 500:
            log(f"  [{state}] HTTP {r.status_code} or too small ({len(r.content)} bytes) — skipped")
            return None
        content_type = r.headers.get("Content-Type", "")
        if "excel" in content_type or "xlsx" in content_type or url.endswith(".xlsx"):
            return pd.read_excel(io.BytesIO(r.content), dtype=str)
        else:
            return pd.read_csv(io.StringIO(r.text), dtype=str, on_bad_lines="skip")
    except Exception as e:
        log(f"  [{state}] Download failed: {e}")
        return None


def fetch_tx_board(df_state: pd.DataFrame) -> dict:
    """Attach TX TSBP facility license data by address / name fuzzy match."""
    meta = STATE_BOARD_META["TX"]
    board_df = _try_download_csv(meta["url"], "TX")
    if board_df is None:
        return {"status": "unavailable", "url": meta["url"]}

    board_df.columns = [c.strip().lower().replace(" ", "_") for c in board_df.columns]
    log(f"  [TX] Board columns: {list(board_df.columns[:10])}")
    # Common TSBP column names: license_number, facility_name, address, city, status, pic_name
    return {"status": "downloaded", "row_count": len(board_df), "url": meta["url"],
            "columns": list(board_df.columns[:10]), "data": board_df}


def fetch_ca_board(df_state: pd.DataFrame) -> dict:
    """Attach CA Board of Pharmacy license data."""
    meta = STATE_BOARD_META["CA"]
    board_df = _try_download_csv(meta["url"], "CA")
    if board_df is None:
        return {"status": "unavailable", "url": meta["url"]}
    board_df.columns = [c.strip().lower().replace(" ", "_") for c in board_df.columns]
    log(f"  [CA] Board columns: {list(board_df.columns[:10])}")
    return {"status": "downloaded", "row_count": len(board_df), "url": meta["url"],
            "columns": list(board_df.columns[:10]), "data": board_df}


def _no_bulk_download(state: str) -> dict:
    meta = STATE_BOARD_META[state]
    log(f"  [{state}] No public bulk download available. Lookup at: {meta['lookup_url']}")
    return {"status": "no_bulk_download", "lookup_url": meta["lookup_url"]}


def attach_state_board_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Enrich records for TX/CA/FL/NY/PA with state board facility license data.
    Adds columns: sb_license_number, sb_license_status, sb_pharmacist_in_charge, sb_source.
    """
    df["sb_license_number"] = ""
    df["sb_license_status"] = ""
    df["sb_pharmacist_in_charge"] = ""
    df["sb_source"] = ""

    state_board_results = {}

    # ── Texas ──
    log("State board: Texas (TSBP)")
    tx_mask = df["state"] == "TX"
    tx_result = fetch_tx_board(df[tx_mask])
    state_board_results["TX"] = {k: v for k, v in tx_result.items() if k != "data"}

    if tx_result.get("status") == "downloaded" and "data" in tx_result:
        board = tx_result["data"]
        # Try to join on zip+name similarity. Use license_number column if present.
        lic_col = next((c for c in board.columns if "license" in c and "num" in c), None)
        name_col = next((c for c in board.columns if "name" in c or "facility" in c), None)
        status_col = next((c for c in board.columns if "status" in c or "active" in c), None)
        pic_col = next((c for c in board.columns if "pic" in c or "pharmacist" in c or "charge" in c), None)
        zip_col = next((c for c in board.columns if "zip" in c or "postal" in c), None)

        if lic_col and zip_col:
            board_idx = board.set_index(zip_col)
            def _enrich_tx(row):
                if row["state"] != "TX":
                    return row
                z = row["zip_code"]
                if z in board_idx.index:
                    candidates = board_idx.loc[[z]] if isinstance(board_idx.loc[z], pd.Series) else board_idx.loc[[z]]
                    if isinstance(candidates, pd.Series):
                        candidates = candidates.to_frame().T
                    # Name match
                    name_q = (row.get("dba_name") or row.get("legal_entity_name", "")).upper()
                    for _, b in candidates.iterrows():
                        bname = str(b.get(name_col, "")).upper() if name_col else ""
                        if name_q and bname and (name_q[:8] in bname or bname[:8] in name_q):
                            row["sb_license_number"] = str(b.get(lic_col, ""))
                            row["sb_license_status"] = str(b.get(status_col, "")) if status_col else ""
                            row["sb_pharmacist_in_charge"] = str(b.get(pic_col, "")) if pic_col else ""
                            row["sb_source"] = STATE_BOARD_META["TX"]["url"]
                            break
                return row

            df = df.apply(_enrich_tx, axis=1)
            tx_enriched = (df[tx_mask]["sb_license_number"] != "").sum()
            log(f"  [TX] Enriched {tx_enriched:,} / {tx_mask.sum():,} TX records")
            state_board_results["TX"]["enriched_count"] = int(tx_enriched)

    # ── California ──
    log("State board: California (CA DCA / Board of Pharmacy)")
    ca_mask = df["state"] == "CA"
    ca_result = fetch_ca_board(df[ca_mask])
    state_board_results["CA"] = {k: v for k, v in ca_result.items() if k != "data"}

    if ca_result.get("status") == "downloaded" and "data" in ca_result:
        board = ca_result["data"]
        lic_col = next((c for c in board.columns if "license" in c or "number" in c), None)
        status_col = next((c for c in board.columns if "status" in c or "active" in c), None)
        npi_col = next((c for c in board.columns if "npi" in c), None)

        if npi_col:
            board_npi = board.set_index(npi_col)
            def _enrich_ca(row):
                if row["state"] != "CA":
                    return row
                npi = row["npi"]
                if npi in board_npi.index:
                    b = board_npi.loc[npi]
                    if isinstance(b, pd.DataFrame):
                        b = b.iloc[0]
                    row["sb_license_number"] = str(b.get(lic_col, "")) if lic_col else ""
                    row["sb_license_status"] = str(b.get(status_col, "")) if status_col else ""
                    row["sb_source"] = STATE_BOARD_META["CA"]["url"]
                return row
            df = df.apply(_enrich_ca, axis=1)
            ca_enriched = (df[ca_mask]["sb_license_number"] != "").sum()
            log(f"  [CA] Enriched {ca_enriched:,} / {ca_mask.sum():,} CA records")
            state_board_results["CA"]["enriched_count"] = int(ca_enriched)

    # ── Florida, New York, Pennsylvania — no public bulk download ──
    for st in ["FL", "NY", "PA"]:
        state_board_results[st] = _no_bulk_download(st)

    return df, state_board_results


# ─── Step 6: Taxonomy Label ───────────────────────────────────────────────────
def add_taxonomy_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Add human-readable taxonomy label and services-offered flags."""
    df["taxonomy_label"] = df["taxonomy_code_1"].map(TAXONOMY_LABELS).fillna("Pharmacy")

    df["svc_compounding"] = df["taxonomy_code_1"].isin(["3336C0004X"]).astype(int) | \
                            df["taxonomy_code_2"].isin(["3336C0004X"]).astype(int)
    df["svc_specialty"] = df["taxonomy_code_1"].isin(["3336S0011X"]).astype(int) | \
                          df["taxonomy_code_2"].isin(["3336S0011X"]).astype(int)
    df["svc_ltc"] = df["taxonomy_code_1"].isin(["3336L0003X"]).astype(int) | \
                    df["taxonomy_code_2"].isin(["3336L0003X"]).astype(int)
    df["svc_home_infusion"] = df["taxonomy_code_1"].isin(["3336H0001X"]).astype(int) | \
                              df["taxonomy_code_2"].isin(["3336H0001X"]).astype(int)
    df["svc_mail_order"] = df["taxonomy_code_1"].isin(["3336M0002X"]).astype(int) | \
                           df["taxonomy_code_2"].isin(["3336M0002X"]).astype(int)
    return df


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> int:
    start = datetime.now(timezone.utc)
    log(f"=== Independent Retail Pharmacy Directory Harvest ===")
    log(f"Output directory: {DATASET_DIR}")

    # Step 1: Ensure NPPES ZIP is available
    ensure_nppes_zip()

    # Step 2: Stream-filter NPPES for pharmacy taxonomy codes (Type 2 only)
    log("=== Step 2: NPPES stream-filter (pharmacy taxonomy codes, Type 2) ===")
    df, npi_member, raw_count = harvest_nppes()

    # Step 3: DEA cross-reference
    log("=== Step 3: DEA Controlled Substance Registrant cross-reference ===")
    dea_df, dea_source = fetch_dea_data()
    df = attach_dea(df, dea_df)

    # Step 4: Chain-exclusion filter
    log("=== Step 4: Chain-exclusion filter ===")
    df = apply_chain_filter(df)

    # Step 5: Taxonomy labels + services flags
    df = add_taxonomy_labels(df)

    # Step 6: State board enrichment for TX/CA/FL/NY/PA
    log("=== Step 5: State board enrichment (TX/CA/FL/NY/PA) ===")
    df, state_board_results = attach_state_board_data(df)

    # ── Final stats ──
    phone_pct = round(100 * (df["phone"].str.len() > 0).mean(), 1)
    state_counts = df["state"].value_counts().head(15).to_dict()
    tax_counts = df["taxonomy_code_1"].value_counts().head(15).to_dict()
    chain_counts = df["chain_flag"].value_counts().to_dict()
    indep_count = chain_counts.get("independent", 0)
    chain_count = chain_counts.get("chain", 0)

    log(f"Phone coverage: {phone_pct}%")
    log(f"Top states: {state_counts}")
    log(f"Taxonomy breakdown: {tax_counts}")
    log(f"Chain filter: {chain_count:,} chain / {indep_count:,} independent")

    # ── Write CSV ──
    output_cols = [
        "npi",
        "legal_entity_name",
        "dba_name",
        "taxonomy_code_1",
        "taxonomy_code_2",
        "taxonomy_label",
        "entity_type",
        "chain_flag",
        "street1",
        "street2",
        "city",
        "state",
        "zip_code",
        "phone",
        "authorized_official_first",
        "authorized_official_last",
        "authorized_official_title",
        "license_number_1",
        "license_state_1",
        "parent_org_name",
        "is_subpart",
        "dea_number",
        "dea_status",
        "dea_business_activity",
        "dea_registration_required",
        "sb_license_number",
        "sb_license_status",
        "sb_pharmacist_in_charge",
        "sb_source",
        "svc_compounding",
        "svc_specialty",
        "svc_ltc",
        "svc_home_infusion",
        "svc_mail_order",
        "last_update_date",
        "source_url",
    ]
    # Only include columns that exist
    output_cols = [c for c in output_cols if c in df.columns]
    df[output_cols].to_csv(OUTPUT_CSV, index=False)
    log(f"Wrote raw CSV: {OUTPUT_CSV} ({len(df):,} rows)")

    end = datetime.now(timezone.utc)
    elapsed_sec = (end - start).total_seconds()

    # ── Write harvest manifest ──
    harvest = {
        "slug": SLUG,
        "harvest_date": start.isoformat(),
        "elapsed_seconds": round(elapsed_sec, 1),
        "harvested_by": "data-engineer",
        "row_count": len(df),
        "independent_count": int(indep_count),
        "chain_count": int(chain_count),
        "sources": {
            "nppes": {
                "url": NPPES_URL,
                "zip_member": npi_member,
                "raw_row_count": raw_count,
                "description": "CMS NPPES Full Replacement Monthly File — Type 2 (organizational) pharmacy NPIs",
            },
            "dea": {
                "url": dea_source,
                "description": (
                    "DEA Controlled Substance Registrant public file. "
                    "All dispensing pharmacies must hold active DEA registration (21 CFR § 1301.11). "
                    "Verify individual registrations: "
                    "https://www.deadiversion.usdoj.gov/registration/index.html"
                ),
                "status": "available" if dea_df is not None else "not_available_as_bulk",
            },
            "state_boards": state_board_results,
        },
        "taxonomy_codes": sorted(PHARMACY_CODES),
        "taxonomy_labels": TAXONOMY_LABELS,
        "chain_filter": {
            "dba_pattern_count": len(_CHAIN_DBA_PATTERNS),
            "corporate_pattern_count": len(_CORPORATE_ENTITY_PATTERNS),
            "flagged_as_chain": int(chain_count),
            "flagged_as_independent": int(indep_count),
        },
        "field_coverage": {
            "phone_pct": phone_pct,
            "dea_number_pct": round(100 * (df["dea_number"].str.len() > 0).mean(), 1)
            if "dea_number" in df.columns else 0,
            "sb_license_pct": round(100 * (df["sb_license_number"].str.len() > 0).mean(), 1)
            if "sb_license_number" in df.columns else 0,
        },
        "top_states": state_counts,
        "top_taxonomy_codes": tax_counts,
        "chain_flag_breakdown": chain_counts,
        "output_file": str(OUTPUT_CSV),
        "status": "COMPLETE",
    }

    HARVEST_JSON.write_text(json.dumps(harvest, indent=2) + "\n")
    log(f"Wrote harvest manifest: {HARVEST_JSON}")
    log(f"\n✓ Pharmacy directory harvest complete: {len(df):,} records ({indep_count:,} independent, {chain_count:,} chain)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
