"""Real-estate / building permits harvester.

Queries Socrata-based municipal open-data portals for permit records.
Returns a unified CSV of recent permits across configured cities.

Each city's Socrata dataset has a known dataset_id; the plugin queries with
date filters and assembles a normalized CSV.

No PII: permits are issued to LLCs/companies + addresses. No personal
contact info except company contact (treated as business contact, public).
"""
from __future__ import annotations
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode
import urllib.request

# (city_name, base_url, dataset_id, normalize_fn_name)
# Each entry: standard Socrata 4x4 dataset id. Limit to public bulk endpoints.
KNOWN_CITIES = [
    ("Chicago", "https://data.cityofchicago.org/resource/ydr8-5enu.json", "permits"),
    ("Los Angeles", "https://data.lacity.org/resource/yv23-pmwf.json", "permits"),
    ("Boston", "https://data.boston.gov/api/3/action/datastore_search?resource_id=6ddcd912-32a0-43df-9908-63574f8c7e77", "permits-boston-ckan"),
    ("Seattle", "https://data.seattle.gov/resource/76t5-zqzr.json", "permits"),
    ("San Francisco", "https://data.sfgov.org/resource/i98e-djp9.json", "permits"),
]


def _fetch_socrata(base_url: str, days_back: int = 30, limit: int = 5000) -> list[dict]:
    """Fetch records from a Socrata JSON endpoint, filtered to recent issuance."""
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S.000")
    # Socrata SoQL: filter by issued_date or similar. Use $where with permissive field name.
    # Different cities use different timestamp column names — try common ones, fall through.
    for date_col in ("issue_date", "issued_date", "permit_creation_date", "application_date", "issuance_date"):
        query = {
            "$where": f"{date_col} > '{since}'",
            "$limit": limit,
        }
        url = f"{base_url}?{urlencode(query)}"
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read())
                    if isinstance(data, list) and data:
                        return data
        except Exception:
            continue
    return []


def _fetch_ckan(base_url: str, days_back: int = 30, limit: int = 5000) -> list[dict]:
    """Boston's CKAN endpoint variant."""
    try:
        url = f"{base_url}&limit={limit}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            if resp.status == 200:
                data = json.loads(resp.read())
                return data.get("result", {}).get("records", [])
    except Exception:
        pass
    return []


def _normalize(record: dict, city: str) -> dict:
    """Project a raw permit record into a normalized schema. Best-effort."""
    return {
        "city": city,
        "permit_number": record.get("permit_") or record.get("permit_number") or record.get("permit_id") or record.get("permit#") or "",
        "permit_type": record.get("permit_type") or record.get("permittype") or record.get("type_") or record.get("permit_class") or "",
        "address": record.get("address") or record.get("location") or record.get("street_address") or "",
        "applicant": record.get("contact_1_name") or record.get("contact") or record.get("applicantname") or record.get("contractor_name") or "",
        "estimated_cost_usd": record.get("estimated_cost") or record.get("valuation") or record.get("declared_value") or record.get("estimated_cost_") or "",
        "issued_date": record.get("issue_date") or record.get("issued_date") or record.get("permit_creation_date") or record.get("issuance_date") or record.get("application_date") or "",
        "work_description": record.get("description_of_work") or record.get("work_description") or record.get("description") or record.get("scope_of_work") or "",
        "source_url": "",  # filled by caller
    }


def harvest(brief: dict, workspace: Path) -> Optional[Path]:
    """Harvest recent building permits from configured municipal Socrata portals.

    Returns path to cleaned CSV on success, None on failure (caller falls back to generic).
    """
    slug = brief.get("slug", "real-estate-permits-harvest")
    out_path = workspace / "state" / f"{slug}.csv"

    all_records = []
    for city, url, label in KNOWN_CITIES:
        if "ckan" in label:
            records = _fetch_ckan(url)
        else:
            records = _fetch_socrata(url)
        if not records:
            continue
        for raw in records:
            norm = _normalize(raw, city)
            norm["source_url"] = url
            all_records.append(norm)

    if not all_records:
        return None

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["city", "permit_number", "permit_type", "address", "applicant", "estimated_cost_usd", "issued_date", "work_description", "source_url"]
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in all_records:
            writer.writerow(r)

    return out_path
