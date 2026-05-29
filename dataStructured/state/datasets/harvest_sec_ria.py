#!/usr/bin/env python3
"""
Harvest SEC IAPD Form ADV bulk data for all SEC-registered investment adviser firms.

Source: https://adviserinfo.sec.gov/compilation (May 2026 registered file)
Raw ZIP: state/datasets/sec_ria_raw/ia050126.zip

Extracts ~15,870 SEC-registered RIA firms with enriched fields:
  firm name, CRD, SEC#, address, phone, website, AUM, employee count,
  client count, client types, fee structure, entity type, disclosure flag.

Outputs:
  state/datasets/sec-registered-investment-advisers-2026-05.csv
  state/datasets/sec-registered-investment-advisers-2026-05.harvest.json
"""

import csv
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
RAW_ZIP = BASE_DIR / "sec_ria_raw" / "ia050126.zip"
SLUG = "sec-registered-investment-advisers-2026-05"
CSV_PATH = BASE_DIR / f"{SLUG}.csv"
REPORT_PATH = BASE_DIR / f"{SLUG}.harvest.json"

SOURCE_URL = "https://adviserinfo.sec.gov/compilation"

# ---------------------------------------------------------------------------
# Output columns
# ---------------------------------------------------------------------------
FIELDNAMES = [
    "crd_number",
    "sec_number",
    "firm_name",
    "legal_name",
    "registration_status",
    "sec_region",
    "firm_type",
    "entity_type",
    "state_of_incorporation",
    "fiscal_year_end_month",
    "latest_adv_filing_date",
    "street_address_1",
    "street_address_2",
    "city",
    "state",
    "zip_code",
    "phone",
    "fax",
    "website",
    # AUM (Item 5F)
    "aum_discretionary_usd",
    "aum_non_discretionary_usd",
    "aum_total_usd",
    "clients_discretionary",
    "clients_non_discretionary",
    "clients_total_managed",
    # Employees (Item 5A/5B)
    "employees_total",
    "employees_advisory",
    "employees_registered_reps_bd",
    "employees_registered_reps_insurance",
    "employees_insurance_agents",
    "employees_financial_planners",
    # Client counts by type (Item 5D — discretionary + non-discretionary combined)
    "clients_individuals",
    "clients_hnw_individuals",
    "clients_banking_thrift",
    "clients_investment_companies",
    "clients_business_dev_companies",
    "clients_pooled_investment_vehicles",
    "clients_pension_profit_sharing",
    "clients_charitable_organizations",
    "clients_state_municipal_govt",
    "clients_other_investment_advisers",
    "clients_insurance_companies",
    "clients_sovereign_wealth_funds",
    "clients_corporations_other_businesses",
    "clients_other",
    # Client type tags (human-readable summary)
    "client_types_served",
    # Fee structure (Item 5E)
    "fee_pct_aum",
    "fee_hourly",
    "fee_subscription",
    "fee_fixed",
    "fee_performance_based",
    "fee_other",
    "fee_types",
    # Private funds (Item 7B)
    "has_private_funds",
    "private_funds_gross_assets_usd",
    "count_hedge_funds",
    "count_pe_funds",
    "count_vc_funds",
    # Disclosure (Item 11)
    "has_disclosure_events",
    "disclosure_event_count",
    # Source
    "source_url",
]

# ---------------------------------------------------------------------------
# Client type (5D) field mappings: (label, discretionary_col, non_disc_col)
# ---------------------------------------------------------------------------
CLIENT_TYPES = [
    ("Individuals",                 "5D(a)(1)", "5D(a)(2)", "clients_individuals"),
    ("HNW Individuals",             "5D(b)(1)", "5D(b)(2)", "clients_hnw_individuals"),
    ("Banking/Thrift",              "5D(c)(1)", "5D(c)(2)", "clients_banking_thrift"),
    ("Investment Companies",        "5D(d)(1)", "5D(d)(3)", "clients_investment_companies"),
    ("Business Dev Companies",      "5D(e)(1)", "5D(e)(3)", "clients_business_dev_companies"),
    ("Pooled Investment Vehicles",  "5D(f)(1)", "5D(f)(3)", "clients_pooled_investment_vehicles"),
    ("Pension/Profit Sharing",      "5D(g)(1)", "5D(g)(2)", "clients_pension_profit_sharing"),
    ("Charitable Orgs",             "5D(h)(1)", "5D(h)(2)", "clients_charitable_organizations"),
    ("State/Municipal Govt",        "5D(i)(1)", "5D(i)(2)", "clients_state_municipal_govt"),
    ("Other Inv Advisers",          "5D(j)(1)", "5D(j)(2)", "clients_other_investment_advisers"),
    ("Insurance Companies",         "5D(k)(1)", "5D(k)(2)", "clients_insurance_companies"),
    ("Sovereign Wealth Funds",      "5D(l)(1)", "5D(l)(2)", "clients_sovereign_wealth_funds"),
    ("Corporations/Businesses",     "5D(m)(1)", "5D(m)(2)", "clients_corporations_other_businesses"),
    ("Other",                       "5D(n)(1)", "5D(n)(2)", "clients_other"),
]

# Fee fields: (label, column)
FEE_FIELDS = [
    ("AUM%",        "5E(1)", "fee_pct_aum"),
    ("Hourly",      "5E(2)", "fee_hourly"),
    ("Subscription","5E(3)", "fee_subscription"),
    ("Fixed",       "5E(4)", "fee_fixed"),
    ("Performance", "5E(5)", "fee_performance_based"),
    ("Other",       "5E(6)", "fee_other"),
]

# Disclosure count columns (Item 11)
DISCLOSURE_COUNT_COLS = [
    "Count of 11A(1) disclosures", "Count of 11A(2) disclosures",
    "Count of 11B(1) disclosures", "Count of 11B(2) disclosures",
    "Count of 11C(1) disclosures", "Count of 11C(2) disclosures",
    "Count of 11C(3) disclosures", "Count of 11C(4) disclosures",
    "Count of 11C(5) disclosures",
    "Count of 11D(1) disclosures", "Count of 11D(2) disclosures",
    "Count of 11D(3) disclosures", "Count of 11D(4) disclosures",
    "Count of 11D(5) disclosures",
    "Count of 11E(1) disclosures", "Count of 11E(2) disclosures",
    "Count of 11E(3) disclosures", "Count of 11E(4) disclosures",
    "Count of 11F disclosures",
    "Count of 11G disclosures",
    "Count of 11H(1)(a) disclosures", "Count of 11H(1)(b) disclosures",
    "Count of 11H(1)(c) disclosures", "Count of 11H(2) disclosures",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_money(val: str) -> str:
    """Strip leading/trailing whitespace, commas, and trailing .00 from currency strings."""
    if not val:
        return ""
    val = val.strip().replace(",", "")
    # Remove trailing .00 for cleanliness (they're integers anyway)
    val = re.sub(r"\.00$", "", val)
    return val if val else ""


def clean_int(val: str) -> str:
    """Strip whitespace from integer-like fields."""
    if not val:
        return ""
    return val.strip()


def sum_client_counts(row: dict, disc_col: str, nondisc_col: str) -> str:
    """
    Add discretionary + non-discretionary counts for a client type.
    Handles the SEC's 'Fewer than 5 clients' sentinel by returning '< 5'.
    Returns '' if both are empty.
    """
    d_raw = row.get(disc_col, "").strip()
    nd_raw = row.get(nondisc_col, "").strip()

    few_sentinel = "fewer than 5 clients"
    d_is_few = d_raw.lower() == few_sentinel
    nd_is_few = nd_raw.lower() == few_sentinel

    if not d_raw and not nd_raw:
        return ""

    # If either is a "fewer than 5" sentinel and neither is a real number
    try:
        d_n = int(d_raw) if (d_raw and not d_is_few) else 0
    except ValueError:
        d_n = 0
        d_is_few = True

    try:
        nd_n = int(nd_raw) if (nd_raw and not nd_is_few) else 0
    except ValueError:
        nd_n = 0
        nd_is_few = True

    total = d_n + nd_n
    if d_is_few or nd_is_few:
        # At least one bucket is < 5; return total + qualifier
        if total == 0:
            return "< 5"
        return f"< {total + 5}"  # conservative upper bound

    if total == 0 and not d_raw and not nd_raw:
        return ""

    return str(total) if total > 0 else ""


def parse_record(row: dict) -> dict:
    """Map raw ADV columns to clean output record."""
    out = {}

    # --- Identifiers ---
    out["crd_number"] = row.get("Organization CRD#", "").strip()
    out["sec_number"] = row.get("SEC#", "").strip()
    out["firm_name"] = row.get("Primary Business Name", "").strip()
    out["legal_name"] = row.get("Legal Name", "").strip()
    out["registration_status"] = row.get("SEC Current Status", "").strip()
    out["sec_region"] = row.get("SEC Region", "").strip()
    out["firm_type"] = row.get("Firm Type", "").strip()

    # --- Firm details ---
    out["entity_type"] = row.get("3A", "").strip()
    out["state_of_incorporation"] = row.get("3C-State", "").strip()
    out["fiscal_year_end_month"] = row.get("3B", "").strip()
    out["latest_adv_filing_date"] = row.get("Latest ADV Filing Date", "").strip()

    # --- Contact ---
    out["street_address_1"] = row.get("Main Office Street Address 1", "").strip()
    out["street_address_2"] = row.get("Main Office Street Address 2", "").strip()
    out["city"] = row.get("Main Office City", "").strip()
    out["state"] = row.get("Main Office State", "").strip()
    zip_raw = row.get("Main Office Postal Code", "").strip()
    # Normalise to 5-digit ZIP for US addresses
    out["zip_code"] = zip_raw[:5] if (zip_raw and row.get("Main Office Country", "").strip() == "United States") else zip_raw
    out["phone"] = row.get("Main Office Telephone Number", "").strip()
    out["fax"] = row.get("Main Office Facsimile Number", "").strip()
    out["website"] = row.get("Website Address", "").strip()

    # --- AUM (Item 5F) ---
    out["aum_discretionary_usd"] = clean_money(row.get("5F(2)(a)", ""))
    out["aum_non_discretionary_usd"] = clean_money(row.get("5F(2)(b)", ""))
    out["aum_total_usd"] = clean_money(row.get("5F(2)(c)", ""))
    out["clients_discretionary"] = clean_int(row.get("5F(2)(d)", ""))
    out["clients_non_discretionary"] = clean_int(row.get("5F(2)(e)", ""))
    out["clients_total_managed"] = clean_int(row.get("5F(2)(f)", ""))

    # --- Employees (Items 5A, 5B) ---
    out["employees_total"] = clean_int(row.get("5A", ""))
    out["employees_advisory"] = clean_int(row.get("5B(1)", ""))
    out["employees_registered_reps_bd"] = clean_int(row.get("5B(3)", ""))
    out["employees_registered_reps_insurance"] = clean_int(row.get("5B(4)", ""))
    out["employees_insurance_agents"] = clean_int(row.get("5B(5)", ""))
    out["employees_financial_planners"] = clean_int(row.get("5B(6)", ""))

    # --- Client types (Item 5D) ---
    client_type_labels = []
    for label, disc_col, nondisc_col, out_key in CLIENT_TYPES:
        val = sum_client_counts(row, disc_col, nondisc_col)
        out[out_key] = val
        if val:
            client_type_labels.append(label)

    out["client_types_served"] = "; ".join(client_type_labels)

    # --- Fee structure (Item 5E) ---
    fee_labels = []
    for label, col, out_key in FEE_FIELDS:
        yn = row.get(col, "").strip()
        out[out_key] = yn
        if yn.upper() == "Y":
            fee_labels.append(label)
    out["fee_types"] = "; ".join(fee_labels)

    # --- Private funds (Item 7B) ---
    out["has_private_funds"] = row.get("7B", "").strip()
    out["private_funds_gross_assets_usd"] = clean_money(row.get("Total Gross Assets of Private Funds", ""))
    out["count_hedge_funds"] = clean_int(row.get("Total number of Hedge funds", ""))
    out["count_pe_funds"] = clean_int(row.get("Total number of PE funds", ""))
    out["count_vc_funds"] = clean_int(row.get("Total number of VC funds", ""))

    # --- Disclosures (Item 11) ---
    out["has_disclosure_events"] = row.get("11", "").strip()
    total_disclosures = 0
    for col in DISCLOSURE_COUNT_COLS:
        raw = row.get(col, "").strip()
        try:
            total_disclosures += int(raw)
        except ValueError:
            pass
    out["disclosure_event_count"] = str(total_disclosures) if total_disclosures > 0 else ""

    # --- Source ---
    out["source_url"] = SOURCE_URL

    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    harvested_at = datetime.now(timezone.utc).isoformat()
    notes = []
    records = []
    raw_rows = 0
    skipped_non_sec = 0
    skipped_not_approved = 0

    print(f"Opening {RAW_ZIP} ...")
    with zipfile.ZipFile(RAW_ZIP) as z:
        fname = z.namelist()[0]
        print(f"  Extracting: {fname}")
        with z.open(fname) as fh:
            reader = csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"))
            for raw_row in reader:
                raw_rows += 1
                if raw_rows % 2000 == 0:
                    print(f"  Read {raw_rows:,} rows ...")

                # Keep only SEC-registered firms (not state-registered, not ERA)
                firm_type = raw_row.get("Firm Type", "").strip()
                if firm_type.lower() not in ("registered",):
                    skipped_non_sec += 1
                    continue

                # Keep only currently approved registrations
                status = raw_row.get("SEC Current Status", "").strip().lower()
                if status not in ("approved",):
                    skipped_not_approved += 1
                    continue

                records.append(parse_record(raw_row))

    print(f"\nRaw rows read: {raw_rows:,}")
    print(f"Skipped (non-registered firm type): {skipped_non_sec:,}")
    print(f"Skipped (status != Approved): {skipped_not_approved:,}")
    print(f"Final records: {len(records):,}")

    if skipped_non_sec:
        notes.append(f"Skipped {skipped_non_sec} rows with non-registered Firm Type (ERA/other).")
    if skipped_not_approved:
        notes.append(f"Skipped {skipped_not_approved} rows with non-Approved SEC status (Pending, Inactive, etc.).")

    # Write CSV
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)

    print(f"\nCSV written: {CSV_PATH}")
    print(f"Rows: {len(records):,}  Columns: {len(FIELDNAMES)}")

    # Quick quality spot-check
    with_phone = sum(1 for r in records if r["phone"])
    with_website = sum(1 for r in records if r["website"])
    with_aum = sum(1 for r in records if r["aum_total_usd"])
    with_disclosure = sum(1 for r in records if r["has_disclosure_events"].upper() == "Y")

    print(f"\nQuality check:")
    print(f"  Records with phone:   {with_phone:,} ({with_phone/len(records)*100:.1f}%)")
    print(f"  Records with website: {with_website:,} ({with_website/len(records)*100:.1f}%)")
    print(f"  Records with AUM:     {with_aum:,} ({with_aum/len(records)*100:.1f}%)")
    print(f"  Records with disclosures: {with_disclosure:,} ({with_disclosure/len(records)*100:.1f}%)")

    notes.append(
        f"Phone coverage: {with_phone/len(records)*100:.1f}%. "
        f"Website coverage: {with_website/len(records)*100:.1f}%. "
        f"AUM coverage: {with_aum/len(records)*100:.1f}%."
    )
    notes.append(
        "Custodian names (Schedule D Part 1) are not present in this flat file; "
        "they require the separate IAPD Schedule D bulk extract."
    )

    # Write harvest report
    report = {
        "version": 1,
        "type": "harvest_report",
        "slug": SLUG,
        "harvested_at": harvested_at,
        "source_url": SOURCE_URL,
        "raw_zip": "sec_ria_raw/ia050126.zip",
        "raw_zip_original_url": "https://www.sec.gov/files/investment/data/other/information-about-registered-investment-advisers-exempt-reporting-advisers/ia050126.zip",
        "row_count_raw_file": raw_rows,
        "row_count_output": len(records),
        "skipped_non_registered": skipped_non_sec,
        "skipped_non_approved": skipped_not_approved,
        "columns": FIELDNAMES,
        "column_count": len(FIELDNAMES),
        "quality": {
            "with_phone": with_phone,
            "phone_pct": round(with_phone / len(records) * 100, 1),
            "with_website": with_website,
            "website_pct": round(with_website / len(records) * 100, 1),
            "with_aum": with_aum,
            "aum_pct": round(with_aum / len(records) * 100, 1),
            "with_disclosure_events": with_disclosure,
        },
        "notes": " | ".join(notes),
        "status": "SUCCESS",
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\nHarvest report written: {REPORT_PATH}")
    print(f"\nDone. {len(records):,} SEC-registered RIA firms harvested.")
    return len(records)


if __name__ == "__main__":
    main()
