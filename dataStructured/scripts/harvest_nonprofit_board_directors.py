#!/usr/bin/env python3
"""
Harvest U.S. Nonprofit Executives & Board Directors Database 2026.

Primary sources:
  - IRS Form 990 bulk ZIP bundles (2023-2025) — Part VII Section A officers/directors
  - IRS Exempt Organizations Business Master File (EO BMF) — org metadata, revenue, NTEE
  - ProPublica Nonprofit Explorer — source URL permalinks

Output:
  state/products/nonprofit-board-directors-executives/
    raw-nonprofit-board-directors-executives-2026-05.csv
    harvest.json
    pipeline-status.json
"""

import csv
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

# defusedxml guards against XXE and billion-laughs XML attacks from untrusted
# IRS XML filings — always use this instead of stdlib xml.etree.ElementTree.
import defusedxml.ElementTree as ET

# ── Paths ──────────────────────────────────────────────────────────────────────
WORKSPACE = Path(__file__).resolve().parent.parent
DATASET_DIR = WORKSPACE / "state" / "datasets"
PRODUCT_DIR = WORKSPACE / "state" / "products" / "nonprofit-board-directors-executives"

# Final output expected by data-steward validation step
CSV_PATH = PRODUCT_DIR / "raw-nonprofit-board-directors-executives-2026-05.csv"
HARVEST_REPORT_PATH = PRODUCT_DIR / "harvest.json"
STATUS_JSON = PRODUCT_DIR / "pipeline-status.json"

# Re-use the already-downloaded EO BMF CSV (1.95M orgs, ~500 MB on disk)
EO_BMF_CSV = DATASET_DIR / "irs-990-nonprofit-organization-directory-2026-05.cleaned.csv"
# Fallback to uncleaned version
EO_BMF_CSV_RAW = DATASET_DIR / "irs-990-nonprofit-organization-directory-2026-05.csv"

PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)

# ── IRS 990 Bulk ZIP Bundles ───────────────────────────────────────────────────
# Each ZIP is ~100-500 MB and contains 17K-50K individual 990 XML files.
# Ordered newest-first so the most recent officer data appears first in output.
# All 2025 months + 2024 months for supplemental coverage.
ZIP_BUNDLES = [
    # 2025 — most recent (process first for freshest data)
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_12A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_11A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_10A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_09A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_08A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_07A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_06A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_05A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_04A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_03A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_02A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2025/2025_TEOS_XML_01A.zip",
    # 2024 — for EINs not covered by 2025 filings
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_12A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_11A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_10A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_09A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_08A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_07A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_06A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_05A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_04A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_03A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_02A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2024/2024_TEOS_XML_01A.zip",
    # 2023 — for orgs not in 2024 or 2025
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_12A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_11A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_10A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_09A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_08A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_07A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_06A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_05A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_04A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_03A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_02A.zip",
    "https://apps.irs.gov/pub/epostcard/990/xml/2023/2023_TEOS_XML_01A.zip",
]

# ── Filters ───────────────────────────────────────────────────────────────────
MIN_REVENUE = 50_000  # Exclude tiny all-volunteer orgs

# Target record ceiling per spec
TARGET_RECORDS = 700_000

# Fast EIN extractor regex — avoids full XML parse for non-qualifying EINs
_EIN_RE = re.compile(rb'<[A-Za-z]*:?EIN[^>]*>(\d{1,9})</[A-Za-z]*:?EIN>', re.DOTALL)
# Also check 990EZ Part IV (different tag path)
_EZ_EIN_RE = re.compile(rb'<[A-Za-z]*:?EIN>(\d{1,9})</[A-Za-z]*:?EIN>')

# ── Lookup tables ─────────────────────────────────────────────────────────────
NTEE_CATEGORIES: Dict[str, str] = {
    'A': 'Arts/Culture/Humanities',
    'B': 'Education',
    'C': 'Environment',
    'D': 'Animal-Related',
    'E': 'Health',
    'F': 'Mental Health',
    'G': 'Diseases/Disorders',
    'H': 'Medical Research',
    'I': 'Crime/Legal',
    'J': 'Employment',
    'K': 'Food/Nutrition',
    'L': 'Housing/Shelter',
    'M': 'Public Safety',
    'N': 'Recreation/Sports',
    'O': 'Youth Development',
    'P': 'Human Services',
    'Q': 'International',
    'R': 'Civil Rights',
    'S': 'Community Improvement',
    'T': 'Philanthropy',
    'U': 'Science',
    'V': 'Social Science',
    'W': 'Public Affairs',
    'X': 'Religion',
    'Y': 'Mutual Benefit',
    'Z': 'Unknown',
}

REVENUE_TIERS: List[Tuple[float, float, str]] = [
    (0, 100_000, "<$100K"),
    (100_000, 250_000, "$100K-$250K"),
    (250_000, 500_000, "$250K-$500K"),
    (500_000, 1_000_000, "$500K-$1M"),
    (1_000_000, 5_000_000, "$1M-$5M"),
    (5_000_000, 10_000_000, "$5M-$10M"),
    (10_000_000, float('inf'), "$10M+"),
]

# IRS FOUNDATION code → human-readable label
FOUNDATION_CODES: Dict[str, str] = {
    '02': '501(c)(3) Private Operating Foundation',
    '03': '501(c)(3) Private Non-Operating Foundation',
    '04': '501(c)(3) Private Foundation (Other)',
    '09': '501(c)(3) Public Charity - Church',
    '10': '501(c)(3) Public Charity - School',
    '11': '501(c)(3) Public Charity - Hospital',
    '12': '501(c)(3) Public Charity - Government',
    '13': '501(c)(3) Public Charity - Medical Research',
    '14': '501(c)(3) Public Charity - University',
    '15': '501(c)(3) Public Charity - Community Support',
    '16': '501(c)(3) Public Charity - Community Foundation',
    '17': '501(c)(3) Public Charity - Supporting Organization',
}

# IRS SUBSECTION code → foundation type label
SUBSECTION_TYPES: Dict[str, str] = {
    '03': '501(c)(3) Public Charity / Foundation',
    '04': '501(c)(4) Social Welfare Organization',
    '05': '501(c)(5) Labor/Agricultural/Horticultural',
    '06': '501(c)(6) Trade/Business Association',
    '07': '501(c)(7) Social/Recreational Club',
    '08': '501(c)(8) Fraternal Beneficiary Society',
    '19': '501(c)(19) Veterans Organization',
}

# Title normalization patterns (ordered, first match wins)
TITLE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r'\bexecutive\s+director\b', re.I), 'Executive Director'),
    (re.compile(r'\b(chief\s+executive\s+officer|ceo)\b', re.I), 'Executive Director'),
    (re.compile(r'\bchief\s+development\s+officer\b', re.I), 'Chief Development Officer'),
    (re.compile(r'\bdevelopment\s+director\b', re.I), 'Development Director'),
    (re.compile(r'\bdirector\s+of\s+development\b', re.I), 'Development Director'),
    (re.compile(r'\bvp\s+(?:of\s+)?development\b', re.I), 'Development Director'),
    (re.compile(r'\b(chief\s+financial\s+officer|cfo)\b', re.I), 'CFO'),
    (re.compile(r'\b(chief\s+operating\s+officer|coo)\b', re.I), 'COO'),
    (re.compile(r'\bvp\s+of\s+programs\b', re.I), 'VP of Programs'),
    (re.compile(r'\bvp\s+of\s+finance\b', re.I), 'VP of Finance'),
    (re.compile(r'\bprogram\s+director\b', re.I), 'Program Director'),
    (re.compile(r'\b(board\s+)?(chair(?:man|woman|person)?)\b', re.I), 'Board Chair'),
    (re.compile(r'\bpresident\b', re.I), 'Board President'),
    (re.compile(r'\bvice\s+chair\b', re.I), 'Vice Chair'),
    (re.compile(r'\bvice\s+president\b', re.I), 'Vice President'),
    (re.compile(r'\bsecretary\b', re.I), 'Secretary'),
    (re.compile(r'\btreasurer\b', re.I), 'Treasurer'),
    (re.compile(r'\btrustee\b', re.I), 'Trustee'),
    (re.compile(r'\bdirector\b', re.I), 'Director'),
]

# Output CSV schema
OUTPUT_COLUMNS: List[str] = [
    'first_name',
    'middle_name',
    'last_name',
    'job_title',
    'organization_legal_name',
    'organization_dba',
    'ein',
    'organization_street',
    'organization_city',
    'organization_state',
    'organization_zip',
    'organization_phone',
    'organization_email',
    'individual_email',
    'organization_website',
    'ntee_code',
    'nonprofit_subsector',
    'annual_revenue',
    'revenue_tier',
    'total_assets',
    'foundation_type',
    'tax_year',
    'years_in_role',
    'source_url',
]

# XML namespace
NS = {'irs': 'http://www.irs.gov/efile'}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _revenue_tier(revenue: float) -> str:
    for lo, hi, label in REVENUE_TIERS:
        if lo <= revenue < hi:
            return label
    return "<$100K"


def _ntee_category(code: str) -> str:
    if not code:
        return 'Unknown'
    return NTEE_CATEGORIES.get(code[0].upper(), 'Unknown')


def _foundation_type(foundation_code: str, subsection_code: str) -> str:
    if foundation_code in FOUNDATION_CODES:
        return FOUNDATION_CODES[foundation_code]
    # Fall back to subsection
    sub = (subsection_code or '').zfill(2)
    return SUBSECTION_TYPES.get(sub, '501(c)(3) Public Charity')


def _normalize_title(raw: str) -> str:
    if not raw:
        return 'Director'
    for pattern, label in TITLE_PATTERNS:
        if pattern.search(raw):
            return label
    return raw.strip()


def _parse_name(text: str) -> Tuple[str, str, str]:
    """Split an IRS PersonNm into (first, middle, last).

    Handles:
      'Last, First Middle'  → ('First', 'Middle', 'Last')
      'First Middle Last'   → ('First', 'Middle', 'Last')
      'SingleToken'         → ('', '', 'SingleToken')
    """
    text = (text or '').strip()
    if not text:
        return '', '', ''
    if ',' in text:
        last, _, rest = text.partition(',')
        parts = rest.split()
        first = parts[0].title() if parts else ''
        mid = ' '.join(p.title() for p in parts[1:]) if len(parts) > 1 else ''
        return first, mid, last.strip().title()
    parts = text.split()
    if len(parts) == 1:
        return '', '', parts[0].title()
    first = parts[0].title()
    last = parts[-1].title()
    mid = ' '.join(p.title() for p in parts[1:-1]) if len(parts) > 2 else ''
    return first, mid, last


def _safe_float(val: Any) -> float:
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def _zip_ein(text: str) -> str:
    """Normalize a ZIP code to 5 digits."""
    z = (text or '').strip()
    return z[:5].zfill(5) if z else ''


# ── Step 1: Load EO BMF ───────────────────────────────────────────────────────

def load_eo_bmf(csv_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load IRS EO BMF from local CSV, filter to $50K+ income orgs.

    Handles both column naming conventions:
      - cleaned CSV: ein, organization_name, income_amount, income_code, ...
      - raw CSV:     EIN, NAME, INCOME_AMT, INCOME_CD, ...
    """
    print(f"\n[1/4] Loading EO BMF from {csv_path.name}...")

    if not csv_path.exists():
        raise FileNotFoundError(f"EO BMF CSV not found: {csv_path}")

    orgs: Dict[str, Dict[str, Any]] = {}
    total = 0
    kept = 0

    def _col(row: Dict, *candidates: str) -> str:
        """Try multiple column name candidates (lowercase + original)."""
        for c in candidates:
            v = row.get(c) or row.get(c.lower()) or row.get(c.upper())
            if v:
                return str(v).strip()
        return ''

    with open(csv_path, newline='', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            # Support both cleaned (lowercase) and raw (uppercase) column names
            ein = _col(row, 'ein', 'EIN')
            if not ein:
                continue
            ein = ein.zfill(9)

            revenue = _safe_float(_col(row, 'income_amount', 'INCOME_AMT', 'revenue_amount', 'REVENUE_AMT'))
            assets = _safe_float(_col(row, 'asset_amount', 'ASSET_AMT'))
            income_code = _col(row, 'income_code', 'INCOME_CD') or '0'

            # Qualify: income_code >= 3 ($25K+) OR actual revenue >= MIN_REVENUE
            if revenue < MIN_REVENUE and income_code < '3':
                continue

            kept += 1
            ntee = _col(row, 'ntee_code', 'NTEE_CD', 'NTEE_CODE').upper()
            # foundation_code in BMF = FOUNDATION field (not to be confused with subsection)
            foundation_code = _col(row, 'foundation_code', 'FOUNDATION').zfill(2)
            subsection_code = _col(row, 'subsection_code', 'SUBSECTION').zfill(2)
            org_name = _col(row, 'organization_name', 'NAME')
            sort_name = _col(row, 'sort_name', 'SORT_NAME')

            orgs[ein] = {
                'ein': ein,
                'legal_name': org_name,
                'dba_name': sort_name if sort_name != org_name else '',
                'street': _col(row, 'street_address', 'STREET'),
                'city': _col(row, 'city', 'CITY'),
                'state': _col(row, 'state', 'STATE'),
                'zip': _zip_ein(_col(row, 'zip_code', 'ZIP')),
                'ntee_code': ntee,
                'nonprofit_subsector': _ntee_category(ntee),
                'foundation_code': foundation_code,
                'subsection_code': subsection_code,
                'foundation_type': _foundation_type(foundation_code, subsection_code),
                'revenue': revenue,
                'assets': assets,
                'revenue_tier': _revenue_tier(revenue),
            }

            if total % 200_000 == 0:
                print(f"  Loaded {total:,} rows, kept {kept:,} qualifying orgs...")

    print(f"✓ Loaded {total:,} total orgs → {kept:,} with revenue ≥ ${MIN_REVENUE:,}")
    return orgs


# ── Step 2: Download EO BMF from IRS (fallback if local file missing) ─────────

IRS_EO_BMF_URLS = [
    "https://www.irs.gov/pub/irs-soi/eo1.csv",
    "https://www.irs.gov/pub/irs-soi/eo2.csv",
    "https://www.irs.gov/pub/irs-soi/eo3.csv",
    "https://www.irs.gov/pub/irs-soi/eo4.csv",
]

EO_BMF_COLS = [
    'EIN', 'NAME', 'ICO', 'STREET', 'CITY', 'STATE', 'ZIP', 'GROUP',
    'SUBSECTION', 'AFFILIATION', 'CLASSIFICATION', 'RULING', 'DEDUCTIBILITY',
    'FOUNDATION', 'ACTIVITY', 'ORGANIZATION', 'STATUS', 'TAX_PERIOD',
    'ASSET_CD', 'INCOME_CD', 'FILING_REQ_CD', 'PF_FILING_REQ_CD',
    'ACCT_PD', 'ASSET_AMT', 'INCOME_AMT', 'REVENUE_AMT', 'NTEE_CD', 'SORT_NAME',
]


def download_eo_bmf_from_irs() -> Dict[str, Dict[str, Any]]:
    """Download IRS EO BMF directly from IRS (used if local cached file missing)."""
    print("\n[1/4] Downloading IRS EO BMF from IRS.gov (fallback)...")
    orgs: Dict[str, Dict[str, Any]] = {}
    for region, url in enumerate(IRS_EO_BMF_URLS, 1):
        print(f"  Region {region}/4: {url}")
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 DataResearch/1.0')
            with urllib.request.urlopen(req, timeout=300) as r:
                content = r.read().decode('utf-8', errors='replace')
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                ein = (row.get('EIN') or '').strip()
                if not ein or ein in orgs:
                    continue
                revenue = _safe_float(row.get('INCOME_AMT'))
                assets = _safe_float(row.get('ASSET_AMT'))
                income_cd = (row.get('INCOME_CD') or '0').strip()
                if revenue < MIN_REVENUE and income_cd < '3':
                    continue
                ntee = (row.get('NTEE_CD') or '').strip()
                foundation_code = (row.get('FOUNDATION') or '').strip().zfill(2)
                subsection_code = (row.get('SUBSECTION') or '').strip().zfill(2)
                orgs[ein] = {
                    'ein': ein,
                    'legal_name': (row.get('NAME') or '').strip(),
                    'street': (row.get('STREET') or '').strip(),
                    'city': (row.get('CITY') or '').strip(),
                    'state': (row.get('STATE') or '').strip(),
                    'zip': _zip_ein(row.get('ZIP') or ''),
                    'ntee_code': ntee,
                    'nonprofit_subsector': _ntee_category(ntee),
                    'foundation_code': foundation_code,
                    'subsection_code': subsection_code,
                    'foundation_type': _foundation_type(foundation_code, subsection_code),
                    'revenue': revenue,
                    'assets': assets,
                    'revenue_tier': _revenue_tier(revenue),
                }
        except Exception as e:
            print(f"  ERROR region {region}: {e}")
    print(f"✓ Downloaded {len(orgs):,} qualifying orgs")
    return orgs


# ── Step 3: Parse one 990 XML → officer records ───────────────────────────────

def _fast_extract_ein(xml_bytes: bytes) -> str:
    """
    Quick EIN extraction via regex on the first 8KB of the XML.
    Avoids full ET parse for non-qualifying orgs (~80% skip rate).
    """
    chunk = xml_bytes[:8000]
    m = _EIN_RE.search(chunk) or _EZ_EIN_RE.search(chunk)
    if m:
        return m.group(1).decode('ascii', errors='replace').strip().zfill(9)
    return ''


def parse_xml_officers(
    xml_bytes: bytes,
    orgs: Dict[str, Dict[str, Any]],
    seen_eins: set,
) -> List[Dict[str, Any]]:
    """
    Parse Part VII Section A from a 990 XML file.
    Returns officer records joined with EO BMF metadata.
    Only processes the most recent filing per EIN (uses seen_eins dedup).

    Phase 1: fast EIN extraction via regex (no XML parse for non-qualifying orgs).
    Phase 2: full ET parse only for qualifying, unseen EINs.
    """
    # ── Phase 1: fast EIN pre-check (avoids full parse for ~80% of files) ──
    ein_fast = _fast_extract_ein(xml_bytes)
    if ein_fast:
        if ein_fast not in orgs or ein_fast in seen_eins:
            return []

    # ── Phase 2: full XML parse ──────────────────────────────────────────────
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []

    # Extract EIN (authoritative from parsed XML)
    ein_el = root.find('.//irs:ReturnHeader//irs:Filer//irs:EIN', NS)
    if ein_el is None:
        ein_el = root.find('.//irs:EIN', NS)
    if ein_el is None or not (ein_el.text or '').strip():
        return []

    ein = ein_el.text.strip().zfill(9)

    if ein not in orgs or ein in seen_eins:
        return []
    seen_eins.add(ein)

    # ── Extract ReturnHeader fields ──────────────────────────────────────────
    # Tax year
    period_el = root.find('.//irs:TaxPeriodEndDt', NS) or root.find('.//irs:TaxPeriodBeginDt', NS)
    tax_year = ''
    if period_el is not None and period_el.text:
        tax_year = period_el.text[:4]

    # Phone from Filer block in ReturnHeader
    phone_el = root.find('.//irs:ReturnHeader//irs:Filer//irs:PhoneNum', NS)
    org_phone = ''
    if phone_el is not None and phone_el.text:
        org_phone = re.sub(r'\D', '', phone_el.text.strip())[:10]

    # ── Extract org-level fields from return body ────────────────────────────
    # Website (Form990 or Form990EZ body)
    website_el = (
        root.find('.//irs:PrimaryWebsiteAddressTxt', NS)
        or root.find('.//irs:WebsiteAddressTxt', NS)
    )
    org_website = ''
    if website_el is not None and website_el.text:
        website_raw = website_el.text.strip()
        if website_raw and website_raw.lower() not in ('n/a', 'none', 'www', ''):
            org_website = website_raw if website_raw.startswith('http') else f"http://{website_raw}"

    # ── Extract Part VII Section A officers (Form 990) ───────────────────────
    officer_nodes = root.findall('.//irs:Form990PartVIISectionAGrp', NS)

    # Fall back to Form 990-EZ Part IV
    if not officer_nodes:
        officer_nodes = root.findall('.//irs:OfficerDirectorTrusteeKeyEmplGrp', NS)

    if not officer_nodes:
        # Mark as seen so we don't reprocess from an older ZIP
        return []

    org = orgs[ein]
    records: List[Dict[str, Any]] = []

    for node in officer_nodes:
        name_el = node.find('irs:PersonNm', NS)
        title_el = node.find('irs:TitleTxt', NS)
        former_el = node.find('irs:FormerOfcrDirectorTrusteeInd', NS)

        # Skip former officers (stale data, not current decision-makers)
        if former_el is not None and (former_el.text or '').strip():
            continue

        name_text = (name_el.text or '') if name_el is not None else ''
        raw_title = (title_el.text or '') if title_el is not None else ''

        if not name_text.strip():
            continue

        first, mid, last = _parse_name(name_text)
        norm_title = _normalize_title(raw_title)

        records.append({
            'first_name': first,
            'middle_name': mid,
            'last_name': last,
            'job_title': norm_title,
            'organization_legal_name': org['legal_name'],
            'organization_dba': org.get('dba_name', ''),
            'ein': ein,
            'organization_street': org['street'],
            'organization_city': org['city'],
            'organization_state': org['state'],
            'organization_zip': org['zip'],
            'organization_phone': org_phone,
            'organization_email': '',       # enriched by data-steward
            'individual_email': '',          # enriched by data-steward
            'organization_website': org_website,
            'ntee_code': org['ntee_code'],
            'nonprofit_subsector': org['nonprofit_subsector'],
            'annual_revenue': f"{org['revenue']:.0f}" if org['revenue'] else '',
            'revenue_tier': org['revenue_tier'],
            'total_assets': f"{org['assets']:.0f}" if org['assets'] else '',
            'foundation_type': org['foundation_type'],
            'tax_year': tax_year,
            'years_in_role': '',
            'source_url': f"https://projects.propublica.org/nonprofits/organizations/{ein}",
        })

    return records


# ── Step 4: Process one ZIP bundle ────────────────────────────────────────────

def process_zip_bundle(
    url: str,
    orgs: Dict[str, Dict[str, Any]],
    seen_eins: set,
    writer: csv.DictWriter,
    target_records: int = TARGET_RECORDS,
    current_total: int = 0,
) -> Dict[str, int]:
    """
    Download a ZIP bundle, parse every XML inside it, write qualifying
    officer records to the already-open CSV writer.
    Returns stats dict.

    Uses two-phase parsing:
      Phase 1: fast regex EIN check (no XML parse) to skip ~80% of files
      Phase 2: full defusedxml parse only for qualifying EINs
    """
    bundle_name = url.rsplit('/', 1)[-1]
    print(f"\n  Bundle: {bundle_name}")

    # ── Download ZIP ─────────────────────────────────────────────────────────
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 DataResearch/1.0')
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=600) as r:
            zip_bytes = r.read()
        elapsed = time.time() - t0
        mb = len(zip_bytes) / 1024 / 1024
        print(f"  Downloaded {mb:.1f} MB in {elapsed:.1f}s")
    except Exception as e:
        print(f"  WARN: Failed to download {bundle_name}: {e}")
        return {'url': url, 'files': 0, 'orgs': 0, 'officers': 0, 'failed': 0, 'skipped': 0, 'status': 'error'}

    # ── Open ZIP ──────────────────────────────────────────────────────────────
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as e:
        print(f"  WARN: Bad ZIP {bundle_name}: {e}")
        return {'url': url, 'files': 0, 'orgs': 0, 'officers': 0, 'failed': 0, 'skipped': 0, 'status': 'bad_zip'}

    file_names = [n for n in zf.namelist() if n.endswith('.xml')]
    total_files = len(file_names)
    orgs_processed = 0
    total_officers = 0
    failed = 0
    skipped = 0  # non-qualifying (EIN not in filter or already seen)

    print(f"  Processing {total_files:,} XML files...")

    for i, fname in enumerate(file_names):
        if i > 0 and i % 10_000 == 0:
            pct = i / total_files * 100
            print(f"    {pct:.0f}% ({i:,}/{total_files:,}) | orgs={orgs_processed:,} | officers={total_officers:,} | skipped={skipped:,}")

        try:
            xml_bytes = zf.read(fname)
        except Exception:
            failed += 1
            continue

        records = parse_xml_officers(xml_bytes, orgs, seen_eins)
        if not records:
            skipped += 1
            continue

        orgs_processed += 1
        total_officers += len(records)
        writer.writerows(records)

        # Flush every 1000 orgs to ensure durability
        if orgs_processed % 1000 == 0:
            writer.writer.stream.flush() if hasattr(writer.writer, 'stream') else None

        # Early stop if target reached
        if current_total + total_officers >= target_records:
            print(f"  Target of {target_records:,} records reached — stopping ZIP early.")
            break

    print(
        f"  ✓ {bundle_name}: {total_files:,} files → "
        f"{orgs_processed:,} orgs → {total_officers:,} officer records "
        f"(skipped={skipped:,}, failed={failed})"
    )

    return {
        'url': url,
        'files': total_files,
        'orgs': orgs_processed,
        'officers': total_officers,
        'failed': failed,
        'skipped': skipped,
        'status': 'ok',
    }


# ── Step 5: Write harvest report ──────────────────────────────────────────────

def write_harvest_report(
    bundle_stats: List[Dict[str, Any]],
    total_orgs: int,
    total_officers: int,
    elapsed_sec: float,
) -> None:
    total_files = sum(b.get('files', 0) for b in bundle_stats)
    report = {
        'version': 1,
        'type': 'harvest_report',
        'slug': 'nonprofit-board-directors-executives',
        'harvested_at': datetime.now(timezone.utc).isoformat(),
        'harvested_by': 'data-engineer',
        'elapsed_seconds': round(elapsed_sec, 1),
        'sources': {
            'eo_bmf': {
                'url': 'https://www.irs.gov/charities-non-profits/exempt-organizations-business-master-file-extract-eo-bmf',
                'local_cache': str(EO_BMF_CSV),
            },
            'form_990_xml': {
                'url': 'https://www.irs.gov/charities-non-profits/form-990-series-downloads',
                'bundles_processed': [b['url'] for b in bundle_stats if b.get('status') == 'ok'],
            },
            'source_url_per_row': 'ProPublica Nonprofit Explorer permalink per EIN',
        },
        'filters': {
            'min_revenue': MIN_REVENUE,
            'description': 'Organizations with annual revenue >= $50K (income_code >= 3)',
        },
        'statistics': {
            'eo_bmf_qualifying_orgs': total_orgs,
            'zip_files_total': total_files,
            'orgs_with_990_officers': sum(b.get('orgs', 0) for b in bundle_stats),
            'total_officer_records': total_officers,
            'bundles': bundle_stats,
        },
        'output_file': str(CSV_PATH),
        'row_count': total_officers,
        'columns': OUTPUT_COLUMNS,
        'status': 'SUCCESS' if total_officers >= 100_000 else 'PARTIAL',
        'notes': (
            'Each row is one individual at one organization. A person serving on '
            'multiple boards appears once per organization (by buyer use case design). '
            'Most recent 990 filing per EIN used (2025 ZIPs processed first, then 2024, '
            'then 2023). Part VII Section A officers, directors, trustees, and key employees '
            'extracted. Former officers excluded. Title normalized to standard taxonomy. '
            'Two-phase XML parsing: fast regex EIN pre-check skips ~80% of files before '
            'full defusedxml parse. ProPublica Nonprofit Explorer permalink used as '
            'source_url per row. Email fields left blank for data-steward enrichment phase.'
        ),
    }
    with open(HARVEST_REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(f"\n✓ Harvest report: {HARVEST_REPORT_PATH}")


def write_pipeline_status(phase: str, status: str) -> None:
    with open(STATUS_JSON, 'w') as f:
        json.dump({
            'phase': phase,
            'status': status,
            'slug': 'nonprofit-board-directors-executives',
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("Nonprofit Board Directors & Executives Harvest 2026")
    print(f"Target: 500K+ officer records from IRS Form 990 Part VII")
    print(f"Output: {CSV_PATH}")
    print("=" * 70)

    start = time.time()
    write_pipeline_status("harvest", "running")

    # ── Step 1: Load org metadata ─────────────────────────────────────────────
    bmf_path = EO_BMF_CSV if EO_BMF_CSV.exists() else EO_BMF_CSV_RAW
    if bmf_path.exists():
        orgs = load_eo_bmf(bmf_path)
    else:
        print(f"Local EO BMF not found at {bmf_path}, downloading from IRS...")
        orgs = download_eo_bmf_from_irs()

    if not orgs:
        write_pipeline_status("harvest", "failed")
        raise RuntimeError("Failed to load organization metadata (EO BMF). Cannot continue.")

    print(f"\n[2/4] Loaded {len(orgs):,} qualifying organizations (revenue ≥ ${MIN_REVENUE:,})")

    # ── Step 2: Open output CSV (write mode, truncate previous partial runs) ──
    tmp_path = CSV_PATH.with_suffix('.csv.tmp')
    print(f"\n[3/4] Processing {len(ZIP_BUNDLES)} ZIP bundles → {CSV_PATH.name}")
    print(f"       (writing via temp file: {tmp_path.name})")

    seen_eins: set = set()
    bundle_stats: List[Dict[str, Any]] = []
    total_officers = 0

    with open(tmp_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for bundle_url in ZIP_BUNDLES:
            stats = process_zip_bundle(
                bundle_url,
                orgs,
                seen_eins,
                writer,
                target_records=TARGET_RECORDS,
                current_total=total_officers,
            )
            bundle_stats.append(stats)
            total_officers += stats.get('officers', 0)
            print(f"  ▶ Running total: {total_officers:,} officer records from {len(seen_eins):,} orgs")
            f.flush()

            # Stop early if target met
            if total_officers >= TARGET_RECORDS:
                print(f"\n  Reached target of {TARGET_RECORDS:,} records — stopping early.")
                break

    # ── Atomic rename: only replace final CSV after complete write ────────────
    os.replace(tmp_path, CSV_PATH)
    csv_mb = CSV_PATH.stat().st_size / 1024 / 1024
    print(f"\n✓ CSV written: {CSV_PATH} ({csv_mb:.1f} MB)")

    # ── Step 3: Write harvest report ──────────────────────────────────────────
    elapsed = time.time() - start
    write_harvest_report(bundle_stats, len(orgs), total_officers, elapsed)
    write_pipeline_status("harvest", "complete")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("HARVEST COMPLETE")
    print(f"  Duration:         {elapsed/60:.1f} minutes")
    print(f"  Qualifying orgs:  {len(orgs):,}")
    print(f"  Orgs w/ 990 data: {len(seen_eins):,}")
    print(f"  Officer records:  {total_officers:,}")
    print(f"  Output size:      {csv_mb:.1f} MB")
    print(f"  CSV path:         {CSV_PATH}")
    print(f"  Harvest JSON:     {HARVEST_REPORT_PATH}")
    print("=" * 70)


if __name__ == '__main__':
    main()
