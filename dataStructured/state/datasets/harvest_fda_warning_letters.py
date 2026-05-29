#!/usr/bin/env python3
"""
Harvest FDA Warning Letters (Jan 2020 – Dec 2025)

Source: FDA.gov Warning Letters DataTables AJAX endpoint
       (server-side processed Drupal View backed by Solr)

Endpoint: POST https://www.fda.gov/datatables/views/ajax
View: warning_letter_solr_index / warning_letter_solr_block

Two-phase approach:
  Phase 1: Bulk download all records via AJAX endpoint (fast, paginated)
  Phase 2: Enrich each letter with detail page scrape for city/state/country/pdf_url
           (slow — 1 request per 2-5 sec as per robots.txt)

Output: state/datasets/fda-warning-letters-enforcement-2026-05/raw-fda-warning-letters.csv
"""

import csv
import json
import os
import re
import sys
import time
import random
import logging
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests

# ── Config ──────────────────────────────────────────────────────────────
BASE_URL = "https://www.fda.gov"
AJAX_URL = f"{BASE_URL}/datatables/views/ajax"
REFERER = f"{BASE_URL}/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters"
PAGE_SIZE = 100  # records per AJAX request
RATE_LIMIT_MIN = 2.0  # seconds between detail-page requests
RATE_LIMIT_MAX = 5.0
DATE_START = datetime(2020, 1, 1)
DATE_END = datetime(2025, 12, 31, 23, 59, 59)

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "fda-warning-letters-enforcement-2026-05"
OUTPUT_CSV = OUTPUT_DIR / "raw-fda-warning-letters.csv"
CHECKPOINT_FILE = OUTPUT_DIR / ".harvest_checkpoint.json"

CSV_FIELDS = [
    "issue_date",
    "warning_letter_number",
    "company_name",
    "company_city",
    "company_state",
    "company_country",
    "product_category",
    "issuing_office",
    "violation_categories",
    "subject_summary",
    "pdf_url",
    "source_url",
    "posted_date",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": REFERER,
    "Accept-Language": "en-US,en;q=0.9",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fda-harvest")

# ── Issuing Office → Product Category mapping ──────────────────────────
OFFICE_TO_CATEGORY = {
    "CDER": "Drugs",
    "Center for Drug Evaluation and Research": "Drugs",
    "CDRH": "Medical Devices",
    "Center for Devices and Radiological Health": "Medical Devices",
    "CFSAN": "Food",
    "Center for Food Safety and Applied Nutrition": "Food",
    "CVM": "Veterinary",
    "Center for Veterinary Medicine": "Veterinary",
    "CTP": "Tobacco",
    "Center for Tobacco Products": "Tobacco",
    "CBER": "Biologics",
    "Center for Biologics Evaluation and Research": "Biologics",
    "Office of Compliance and Biologics Quality": "Biologics",
    "ORA": "Multiple",
    "Office of Regulatory Affairs": "Multiple",
}

# Subject keywords → product category (fallback when office is ambiguous)
SUBJECT_TO_CATEGORY = {
    "drug": "Drugs",
    "pharmaceutical": "Drugs",
    "cgmp/finished pharmaceuticals": "Drugs",
    "compounding": "Drugs",
    "biologic": "Biologics",
    "blood": "Biologics",
    "clinical investigator": "Biologics",
    "bimo": "Biologics",
    "tissue": "Biologics",
    "device": "Medical Devices",
    "medical device": "Medical Devices",
    "qsr": "Medical Devices",
    "food": "Food",
    "haccp": "Food",
    "seafood": "Food",
    "juice": "Food",
    "allergen": "Food",
    "sanitation": "Food",
    "cgmp for foods": "Food",
    "dietary supplement": "Dietary Supplements",
    "supplement": "Dietary Supplements",
    "new drug": "Dietary Supplements",  # Often DS sold as unapproved drugs
    "cosmetic": "Cosmetics",
    "tobacco": "Tobacco",
    "smoking prevention": "Tobacco",
    "veterinary": "Veterinary",
    "animal": "Veterinary",
    "pet food": "Veterinary",
}


# ── HTML helpers ────────────────────────────────────────────────────────
class SimpleHTMLTextExtractor(HTMLParser):
    """Extract plain text from an HTML snippet."""
    def __init__(self):
        super().__init__()
        self._text = []
        self._attrs = {}

    def handle_data(self, data):
        self._text.append(data.strip())

    def handle_starttag(self, tag, attrs):
        self._attrs[tag] = dict(attrs)

    @property
    def text(self):
        return " ".join(t for t in self._text if t)

    @property
    def attrs(self):
        return self._attrs


def parse_html_cell(html_str):
    """Return (text, attrs_dict) from an HTML cell."""
    if not html_str or not html_str.strip():
        return "", {}
    p = SimpleHTMLTextExtractor()
    p.feed(html_str)
    return p.text, p.attrs


def extract_datetime(html_str):
    """Extract date from <time datetime='...'> tag."""
    match = re.search(r'datetime="([^"]+)"', html_str or "")
    if match:
        dt_str = match.group(1)
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            pass
    # Fallback: parse visible text
    text, _ = parse_html_cell(html_str)
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def extract_link(html_str):
    """Extract (text, href) from an <a> tag."""
    text, attrs = parse_html_cell(html_str)
    href = attrs.get("a", {}).get("href", "")
    return text, href


def extract_letter_number(url_path):
    """Extract warning letter number from URL slug like company-name-719607-03122026."""
    match = re.search(r'-(\d{5,7})-\d{6,8}$', url_path)
    if match:
        return match.group(1)
    # Try alternate pattern
    match2 = re.search(r'/([^/]+-(\d{5,7})-\d+)$', url_path)
    if match2:
        return match2.group(2)
    return ""


def classify_product_category(issuing_office, subject):
    """Derive product category from issuing office + subject."""
    # First try office mapping
    for key, cat in OFFICE_TO_CATEGORY.items():
        if key.lower() in issuing_office.lower():
            if cat != "Multiple":
                return cat
            break  # Office is ambiguous, fall through to subject

    # Try subject keywords
    subj_lower = subject.lower()
    for key, cat in SUBJECT_TO_CATEGORY.items():
        if key in subj_lower:
            return cat

    # Check for Division of ... which indicates ORA regional offices
    if "division of" in issuing_office.lower():
        div_lower = issuing_office.lower()
        if "food" in div_lower:
            return "Food"
        if "drug" in div_lower:
            return "Drugs"
        if "device" in div_lower:
            return "Medical Devices"
        if "biologic" in div_lower:
            return "Biologics"
        # ORA field divisions handle food/drug/device together
        # Use subject to disambiguate
        for key, cat in SUBJECT_TO_CATEGORY.items():
            if key in subj_lower:
                return cat

    return "Other"


def map_issuing_office_code(office):
    """Map verbose office name to standard code."""
    office_lower = office.lower()
    if "drug evaluation" in office_lower or "cder" in office_lower:
        return "CDER"
    if "devices" in office_lower or "radiological" in office_lower or "cdrh" in office_lower:
        return "CDRH"
    if "food safety" in office_lower or "cfsan" in office_lower:
        return "CFSAN"
    if "veterinary" in office_lower or "cvm" in office_lower:
        return "CVM"
    if "tobacco" in office_lower or "ctp" in office_lower:
        return "CTP"
    if "biologics" in office_lower or "cber" in office_lower:
        return "CBER"
    if "regulatory affairs" in office_lower or "ora" in office_lower:
        return "ORA"
    if "division of" in office_lower:
        return "ORA"  # ORA field divisions
    if "office of compliance" in office_lower:
        if "biologics" in office_lower:
            return "CBER"
        return "ORA"
    return office[:30]  # Keep original if no match


# ── Phase 1: Bulk download via AJAX ────────────────────────────────────
def fetch_all_records():
    """Download all warning letter records via DataTables AJAX endpoint."""
    session = requests.Session()
    session.headers.update(HEADERS)

    all_records = []
    start = 0
    draw = 1
    total = None

    while True:
        payload = {
            "draw": str(draw),
            "start": str(start),
            "length": str(PAGE_SIZE),
            "view_name": "warning_letter_solr_index",
            "view_display_id": "warning_letter_solr_block",
            "view_base_path": "inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters/datatables-data",
            "view_path": "/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters",
        }

        resp = session.post(AJAX_URL, data=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if total is None:
            total = data.get("recordsTotal", 0)
            log.info(f"Total records in database: {total}")

        rows = data.get("data", [])
        if not rows:
            break

        for row in rows:
            # row is a list of 8 HTML cells
            posted_dt = extract_datetime(row[0] if len(row) > 0 else "")
            issue_dt = extract_datetime(row[1] if len(row) > 1 else "")
            company_name, href = extract_link(row[2] if len(row) > 2 else "")
            issuing_office = parse_html_cell(row[3] if len(row) > 3 else "")[0]
            subject = parse_html_cell(row[4] if len(row) > 4 else "")[0]

            # Filter by date range (2020–2025)
            if issue_dt:
                # Normalize to naive datetime for comparison
                issue_naive = issue_dt.replace(tzinfo=None) if issue_dt.tzinfo else issue_dt
                if issue_naive < DATE_START or issue_naive > DATE_END:
                    continue

            letter_number = extract_letter_number(href)
            source_url = urljoin(BASE_URL, href) if href else ""
            product_category = classify_product_category(issuing_office, subject)
            office_code = map_issuing_office_code(issuing_office)

            record = {
                "issue_date": issue_dt.strftime("%Y-%m-%d") if issue_dt else "",
                "warning_letter_number": letter_number,
                "company_name": company_name,
                "company_city": "",
                "company_state": "",
                "company_country": "",
                "product_category": product_category,
                "issuing_office": office_code,
                "violation_categories": subject,
                "subject_summary": subject,
                "pdf_url": "",
                "source_url": source_url,
                "posted_date": posted_dt.strftime("%Y-%m-%d") if posted_dt else "",
            }
            all_records.append(record)

        log.info(f"  Fetched {start + len(rows)}/{total} (kept {len(all_records)} in 2020-2025)")
        start += PAGE_SIZE
        draw += 1

        if start >= total:
            break

        # Respectful rate limit between AJAX pages
        time.sleep(0.5)

    return all_records


# ── Phase 2: Enrich with detail page scrape ─────────────────────────────
def scrape_detail_page(session, url):
    """Scrape an individual warning letter page for city/state/country/pdf_url."""
    info = {
        "company_city": "",
        "company_state": "",
        "company_country": "",
        "pdf_url": "",
    }
    try:
        resp = session.get(url, timeout=30)
        if resp.status_code != 200:
            return info
        html = resp.text

        # Look for address block - typically in the letter body
        # FDA warning letters have a standard format with company address at top

        # Pattern 1: Structured address in metadata or header section
        # Many letters have the address in a specific div/section
        addr_patterns = [
            # "Company Name\nStreet\nCity, State ZIP\nCountry"
            r'<div[^>]*class="[^"]*address[^"]*"[^>]*>(.*?)</div>',
            # Alt: look for city, state pattern near company name
            r'(?:address|location|recipient)[^<]*</[^>]+>\s*(?:<[^>]+>)*(.*?(?:\d{5}(?:-\d{4})?).*?)</(?:p|div)',
        ]

        # Better approach: look for the "Recipient:" or address section
        # which typically appears early in the letter content
        content_match = re.search(
            r'<div[^>]*class="[^"]*field--name-body[^"]*"[^>]*>(.*?)</div>\s*</div>',
            html, re.DOTALL | re.IGNORECASE
        )
        if content_match:
            body = content_match.group(1)[:3000]  # Only check first 3000 chars

            # Look for US state pattern: "City, ST ZIP"
            state_match = re.search(
                r'([A-Z][a-zA-Z\s.-]+),\s*([A-Z]{2})\s+(\d{5}(?:-\d{4})?)',
                body
            )
            if state_match:
                info["company_city"] = state_match.group(1).strip()
                info["company_state"] = state_match.group(2)
                info["company_country"] = "United States"
            else:
                # International: look for country names
                country_match = re.search(
                    r'(?:China|India|Japan|Korea|Germany|France|Italy|Spain|Mexico|Canada|Brazil|'
                    r'United Kingdom|UK|Taiwan|Thailand|Vietnam|Indonesia|Pakistan|Bangladesh|'
                    r'Israel|Turkey|Egypt|Colombia|Argentina|Peru|Chile|Australia|New Zealand|'
                    r'South Africa|Nigeria|Kenya|Philippines|Malaysia|Singapore|'
                    r'Switzerland|Netherlands|Belgium|Ireland|Sweden|Denmark|Norway|Finland|'
                    r'Austria|Portugal|Poland|Czech Republic|Hungary|Romania|Bulgaria|Croatia|'
                    r'Puerto Rico|Dominican Republic|Costa Rica|Guatemala|Honduras|El Salvador|'
                    r'Ecuador|Venezuela|Bolivia|Paraguay|Uruguay|Jamaica|Trinidad|'
                    r'Saudi Arabia|UAE|United Arab Emirates|Qatar|Kuwait|Jordan|Lebanon)',
                    body, re.IGNORECASE
                )
                if country_match:
                    info["company_country"] = country_match.group(0).title()

                    # Try to get city before country
                    pre_country = body[:country_match.start()]
                    city_match = re.search(
                        r'([A-Z][a-zA-Z\s.-]+?)(?:\s*,\s*|\s+)$',
                        pre_country[-100:]
                    )
                    if city_match:
                        info["company_city"] = city_match.group(1).strip()

        # Look for PDF link
        pdf_match = re.search(r'href="([^"]*\.pdf)"', html, re.IGNORECASE)
        if pdf_match:
            pdf_path = pdf_match.group(1)
            info["pdf_url"] = urljoin(url, pdf_path)

    except Exception as e:
        log.warning(f"  Detail scrape failed for {url}: {e}")

    return info


def enrich_records(records):
    """Phase 2: Enrich records with detail page data."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": HEADERS["User-Agent"],
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })

    # Load checkpoint if exists
    checkpoint = {}
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            checkpoint = json.load(f)
        log.info(f"Loaded checkpoint with {len(checkpoint)} enriched records")

    enriched_count = 0
    total = len(records)

    for i, record in enumerate(records):
        url = record.get("source_url", "")
        if not url:
            continue

        # Check checkpoint
        if url in checkpoint:
            info = checkpoint[url]
            record["company_city"] = info.get("company_city", "")
            record["company_state"] = info.get("company_state", "")
            record["company_country"] = info.get("company_country", "")
            record["pdf_url"] = info.get("pdf_url", "")
            enriched_count += 1
            continue

        # Rate limit
        delay = random.uniform(RATE_LIMIT_MIN, RATE_LIMIT_MAX)
        time.sleep(delay)

        info = scrape_detail_page(session, url)
        record["company_city"] = info.get("company_city", "")
        record["company_state"] = info.get("company_state", "")
        record["company_country"] = info.get("company_country", "")
        record["pdf_url"] = info.get("pdf_url", "")

        # Save to checkpoint
        checkpoint[url] = info
        enriched_count += 1

        # Save checkpoint every 50 records
        if enriched_count % 50 == 0:
            with open(CHECKPOINT_FILE, "w") as f:
                json.dump(checkpoint, f)
            log.info(f"  Enriched {enriched_count}/{total} (checkpoint saved)")

        if enriched_count % 10 == 0:
            log.info(f"  Enriching {enriched_count}/{total}...")

    # Final checkpoint save
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(checkpoint, f)

    return records


# ── Write CSV ──────────────────────────────────────────────────────────
def write_csv(records):
    """Write final CSV output."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Deduplicate by (issue_date, company_name, warning_letter_number)
    seen = set()
    unique_records = []
    for r in records:
        key = (r["issue_date"], r["company_name"], r["warning_letter_number"])
        if key not in seen:
            seen.add(key)
            unique_records.append(r)

    # Sort by issue_date descending
    unique_records.sort(key=lambda r: r["issue_date"], reverse=True)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(unique_records)

    log.info(f"Wrote {len(unique_records)} records to {OUTPUT_CSV}")
    return len(unique_records)


# ── Main ────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("FDA Warning Letters Harvest — Jan 2020 to Dec 2025")
    log.info("=" * 60)

    # Phase 1: Bulk download
    log.info("\n▸ Phase 1: Downloading all records via AJAX endpoint...")
    records = fetch_all_records()
    log.info(f"  → {len(records)} records in date range 2020-01-01 to 2025-12-31")

    if not records:
        log.error("No records found. Aborting.")
        sys.exit(1)

    # Phase 2: Enrich with detail pages (optional — skip with --fast flag)
    skip_enrich = "--fast" in sys.argv
    if skip_enrich:
        log.info("\n▸ Phase 2: SKIPPED (--fast flag)")
    else:
        log.info(f"\n▸ Phase 2: Enriching {len(records)} records from detail pages...")
        log.info(f"  Rate limit: {RATE_LIMIT_MIN}-{RATE_LIMIT_MAX}s between requests")
        est_time = len(records) * (RATE_LIMIT_MIN + RATE_LIMIT_MAX) / 2
        log.info(f"  Estimated time: ~{est_time/60:.0f} minutes")
        records = enrich_records(records)

    # Write CSV
    log.info("\n▸ Writing CSV...")
    count = write_csv(records)

    # Summary
    log.info("\n" + "=" * 60)
    log.info("HARVEST COMPLETE")
    log.info(f"  Records: {count}")
    log.info(f"  Output:  {OUTPUT_CSV}")
    log.info(f"  Date range: 2020-01-01 to 2025-12-31")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
