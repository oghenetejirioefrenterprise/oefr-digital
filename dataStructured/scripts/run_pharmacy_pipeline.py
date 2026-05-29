#!/usr/bin/env python3
"""CEO pipeline for independent-retail-pharmacy-directory (brief score 8/10).

Sequence (per CEO orchestration 2026-05-28):
  data-engineer -> data-steward -> compliance-officer
  -> if compliance verdict == PASS: write product spec.json -> engineer (ship)

Self-contained: derives the harvest spec from the opportunity brief (no
pre-existing spec.json required), writes spec.json only after a PASS verdict.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from scripts.ceo_orchestrator import (  # noqa: E402
    dispatch_employee,
    write_pipeline_status,
    next_pipeline_step,
)

SLUG = "independent-retail-pharmacy-directory"
BRIEF_PATH = WORKSPACE / "state" / "opportunities" / "2026-05-28-independent-retail-pharmacy-directory.json"
DATASET_DIR = WORKSPACE / "state" / "datasets" / SLUG
PRODUCT_DIR = WORKSPACE / "state" / "products" / SLUG


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def build_spec(brief: dict) -> dict:
    """Derive a product_spec.json from the approved opportunity brief."""
    return {
        "version": 1,
        "type": "product_spec",
        "slug": SLUG,
        "created": datetime.now(timezone.utc).isoformat(),
        "created_by": "ceo",
        "status": "READY_TO_SHIP",
        "compliance_verdict": "PASS",
        "product_name": "U.S. Independent Retail Pharmacy Facility Directory 2026",
        "one_liner": (
            "Complete CSV of independent community, compounding, specialty, and LTC "
            "pharmacy FACILITIES (~19,400 NCPA independents after chain exclusion) — "
            "with NPI (Type 2), DEA registration, NABP number, state license status, "
            "pharmacist-in-charge, owner-of-record, and services-offered flags. "
            "The chain-exclusion filter (CVS/Walgreens/Rite Aid/Walmart/Kroger removed) "
            "is a wedge no existing $1,500-$6,000/yr vendor offers."
        ),
        "audience": brief.get("target_audience", ""),
        "core_fields": [
            "Pharmacy DBA name",
            "Legal entity name",
            "NABP number",
            "DEA registration number",
            "NPI (Type 2 organizational)",
            "Street address (street, city, state, ZIP)",
            "Phone",
            "Owner-of-record name",
            "Pharmacist-in-charge",
            "License status",
            "Services offered (retail / compounding / specialty / LTC / mail-order)",
            "Medicare/Medicaid enrollment flag",
            "Chain-exclusion flag (independent vs. top-30 chain)",
            "340B contract-pharmacy flag",
            "Source URL (state board / DEA / NABP / CMS NPPES)",
        ],
        "estimated_row_count": 19400,
        "estimated_row_count_rationale": brief.get("estimated_market_size", ""),
        "price_usd": 49,
        "pricing_tiers": {
            "state_csv": 49,
            "state_csv_high_value": 79,
            "top5_state_bundle": 199,
            "national_independents_bundle": 349,
            "addon_340b_only": 99,
            "addon_compounding_only": 99,
        },
        "pricing_rationale": brief.get("monetization_model", ""),
        "source_url": "; ".join(brief.get("public_data_sources", [])),
        "data_freshness_requirement": brief.get("data_freshness_requirement", ""),
        "compliance_notes": brief.get("compliance_notes", ""),
        "distribution_channels": [
            "Gumroad one-time download (primary storefront)",
            "LinkedIn DM outreach to PMS vendors (PioneerRx/BestRx/ComputerRx), PSAOs, and pharma wholesaler account teams",
            "r/pharmacy and NCPA member channels",
            "Direct vendor partner programs",
        ],
        "next_steps": brief.get("next_steps", []),
    }


def main() -> int:
    brief = json.loads(BRIEF_PATH.read_text())
    log(f"Running CEO pipeline for {SLUG} (brief score {brief.get('score')})")

    # ---- Phase 1: data-engineer (harvest) ----
    log("Phase 1: data-engineer (harvest)")
    write_pipeline_status(WORKSPACE, SLUG, {"phase": "harvest", "status": "running"})
    harvest_task = (
        f"Harvest the dataset for '{SLUG}' (Independent Retail Pharmacy Facility Directory). "
        f"Write raw output to state/datasets/{SLUG}/raw-pharmacies.csv. Steps: "
        "(1) Harvest CMS NPPES Type 2 organizational NPIs filtered by pharmacy taxonomy 333600000X "
        "(Community/Retail Pharmacy) and compounding/specialty/LTC subcodes — adapt scripts/harvest_nppes_dental.py "
        "(same NPPES bulk zip, swap taxonomy codes; stream-filter, do not write the full 11GB file). "
        "(2) Cross-reference the DEA Controlled Substance Registrant public file to attach DEA numbers and active dispensing status. "
        "(3) Build a chain-exclusion filter: regex against top-30 chain DBA names "
        "(CVS, Walgreens, Rite Aid, Walmart, Kroger, Publix, Costco, Sam's Club, Albertsons, Safeway, H-E-B, Target, Wegmans, etc.) "
        "plus corporate-owner entity match; flag each row independent vs. chain. "
        "(4) For TX/CA/FL/NY/PA, attach state board facility license number, status, and pharmacist-in-charge where publicly available. "
        "Public data only (NPPES, DEA FOIA file, state pharmacy boards, NABP public lookup) — no PHI, no patient data. "
        f"Write a harvest manifest to state/datasets/{SLUG}/harvest.json with row_count, source URLs, and taxonomy codes used."
    )
    try:
        out = dispatch_employee("data-engineer", harvest_task, timeout_sec=10800)
        log("data-engineer OK\n" + out[-2000:])
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "harvest", "status": "ok"})
    except Exception as e:
        log(f"data-engineer FAILED: {e}")
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "harvest", "status": "failed", "error": str(e)})
        return 1

    # ---- Phase 2: data-steward (validate) ----
    log("Phase 2: data-steward (validate)")
    write_pipeline_status(WORKSPACE, SLUG, {"phase": "validate", "status": "running"})
    validate_task = (
        f"Validate and clean the dataset for '{SLUG}'. Read state/datasets/{SLUG}/raw-*.csv, "
        f"dedupe by NPI/NABP, normalize addresses and phone numbers, drop rows missing a facility identifier, "
        f"verify the chain-exclusion flag, and write a cleaned file to state/datasets/{SLUG}/clean-pharmacies.csv "
        f"plus a validation report state/datasets/{SLUG}.validation.json (row_count, dedupe stats, field completeness)."
    )
    try:
        out = dispatch_employee("data-steward", validate_task, timeout_sec=5400)
        log("data-steward OK\n" + out[-2000:])
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "validate", "status": "ok"})
    except Exception as e:
        log(f"data-steward FAILED: {e}")
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "validate", "status": "failed", "error": str(e)})
        return 1

    # ---- Phase 3: compliance-officer (audit) ----
    log("Phase 3: compliance-officer (audit)")
    write_pipeline_status(WORKSPACE, SLUG, {"phase": "compliance", "status": "running"})
    compliance_task = (
        f"Compliance audit for '{SLUG}'. Read state/datasets/{SLUG}/clean-*.csv. "
        "Scan for PII/PHI (patient data, SSNs, personal emails), confirm all data is public "
        "(state pharmacy boards, DEA FOIA registrant file, NABP public lookup, CMS NPPES organizational NPIs), "
        "verify source URLs are present, and confirm business/facility entities only. "
        f"Write the verdict to state/ethics-ledger/2026-05-28-{SLUG}.json with fields: "
        'slug, verdict ("PASS" or "FAIL"), reason, issues, checks_performed, data_source, '
        "data_classification, auth_required, pii_detected, row_count, audited_at."
    )
    try:
        out = dispatch_employee("compliance-officer", compliance_task, timeout_sec=2700)
        log("compliance-officer OK\n" + out[-2000:])
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "compliance", "status": "ok"})
    except Exception as e:
        log(f"compliance-officer FAILED: {e}")
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "compliance", "status": "failed", "error": str(e)})
        return 1

    # ---- Gate: read compliance verdict ----
    step = next_pipeline_step(WORKSPACE, SLUG)
    ledger_files = sorted((WORKSPACE / "state" / "ethics-ledger").glob(f"*-{SLUG}.json"))
    verdict = None
    if ledger_files:
        verdict = json.loads(ledger_files[-1].read_text()).get("verdict")
    log(f"Compliance verdict: {verdict} (next_pipeline_step -> {step})")

    if verdict != "PASS":
        log("Compliance did NOT pass — halting before ship. CEO review required.")
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "compliance", "status": "blocked", "verdict": verdict})
        return 2

    # ---- Write product spec.json (CEO action, post-PASS) ----
    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
    spec = build_spec(brief)
    (PRODUCT_DIR / "spec.json").write_text(json.dumps(spec, indent=2) + "\n")
    log(f"Wrote {PRODUCT_DIR / 'spec.json'}")

    # ---- Phase 4: engineer (ship) ----
    log("Phase 4: engineer (ship)")
    write_pipeline_status(WORKSPACE, SLUG, {"phase": "ship", "status": "running"})
    ship_task = (
        f"Ship product '{SLUG}'. Read state/products/{SLUG}/spec.json and state/datasets/{SLUG}/clean-*.csv. "
        "Create the Gumroad listing(s) per the pricing tiers in the spec (start with the TX independents-only "
        "state CSV at $49 as the first SKU) and a Stripe Payment Link. Never discount — stack bonuses. "
        f"Write a launch report to state/products/{SLUG}/launch-report.json with status SHIPPED|FAILED|BLOCKED, "
        "the Gumroad URL(s), Stripe URL, price, and row_count."
    )
    try:
        out = dispatch_employee("engineer", ship_task, timeout_sec=5400)
        log("engineer OK\n" + out[-2000:])
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "ship", "status": "ok"})
    except Exception as e:
        log(f"engineer FAILED: {e}")
        write_pipeline_status(WORKSPACE, SLUG, {"phase": "ship", "status": "failed", "error": str(e)})
        return 1

    write_pipeline_status(WORKSPACE, SLUG, {"phase": "done", "status": "ok"})
    log(f"Pipeline complete for {SLUG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
