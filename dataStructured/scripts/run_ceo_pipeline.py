#!/usr/bin/env python3
"""Run the CEO's daily pipeline for a single brief."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ceo_orchestrator import dispatch_employee, write_pipeline_status

WORKSPACE = Path(__file__).resolve().parents[1]


def run_pipeline(slug: str) -> dict:
    """Run data-engineer → data-steward → compliance-officer → engineer pipeline."""

    # Phase 1: Harvest
    write_pipeline_status(WORKSPACE, slug, {"phase": "harvest", "status": "running"})
    try:
        harvest_out = dispatch_employee(
            "data-engineer",
            f"Harvest dataset for {slug}. Read the approved opportunity brief at state/opportunities/*-{slug}*.json. Write output to state/products/{slug}/dataset.csv and log harvest report to state/products/{slug}/harvest-report.json."
        )
        print(f"✅ Harvest complete:\n{harvest_out[:500]}")
        write_pipeline_status(WORKSPACE, slug, {"phase": "harvest", "status": "ok"})
    except Exception as e:
        write_pipeline_status(WORKSPACE, slug, {"phase": "harvest", "status": "failed", "error": str(e)})
        return {"slug": slug, "status": "failed", "phase": "harvest", "error": str(e)}

    # Phase 2: Validate
    write_pipeline_status(WORKSPACE, slug, {"phase": "validate", "status": "running"})
    try:
        validate_out = dispatch_employee(
            "data-steward",
            f"Validate dataset {slug}. Read harvest report at state/products/{slug}/harvest-report.json, validate the dataset, and write clean CSV + validation report."
        )
        print(f"✅ Validation complete:\n{validate_out[:500]}")
        write_pipeline_status(WORKSPACE, slug, {"phase": "validate", "status": "ok"})
    except Exception as e:
        write_pipeline_status(WORKSPACE, slug, {"phase": "validate", "status": "failed", "error": str(e)})
        return {"slug": slug, "status": "failed", "phase": "validate", "error": str(e)}

    # Phase 3: Compliance
    write_pipeline_status(WORKSPACE, slug, {"phase": "compliance", "status": "running"})
    try:
        compliance_out = dispatch_employee(
            "compliance-officer",
            f"Compliance audit for {slug}. Read spec at state/products/{slug}/spec.json and dataset. Audit for PII, auth requirements, and public-data compliance. Write verdict to state/ethics-ledger/."
        )
        print(f"✅ Compliance audit complete:\n{compliance_out[:500]}")
        write_pipeline_status(WORKSPACE, slug, {"phase": "compliance", "status": "ok"})

        # Check verdict
        import json
        ledger_files = list((WORKSPACE / "state" / "ethics-ledger").glob(f"*-{slug}.json"))
        if not ledger_files:
            return {"slug": slug, "status": "failed", "phase": "compliance", "error": "No ledger file found"}

        ledger = json.loads(ledger_files[-1].read_text())
        if ledger.get("verdict") != "PASS":
            verdict = ledger.get("verdict", "UNKNOWN")
            reason = ledger.get("block_reason", "No reason provided")
            return {"slug": slug, "status": "blocked", "phase": "compliance", "verdict": verdict, "reason": reason}
    except Exception as e:
        write_pipeline_status(WORKSPACE, slug, {"phase": "compliance", "status": "failed", "error": str(e)})
        return {"slug": slug, "status": "failed", "phase": "compliance", "error": str(e)}

    # Phase 4: Ship
    write_pipeline_status(WORKSPACE, slug, {"phase": "ship", "status": "running"})
    try:
        ship_out = dispatch_employee(
            "engineer",
            f"Ship product {slug}. Read spec at state/products/{slug}/spec.json, create Stripe Payment Link, create Gumroad listing, and write launch report to state/products/{slug}/launch-report.json."
        )
        print(f"✅ Ship complete:\n{ship_out[:500]}")
        write_pipeline_status(WORKSPACE, slug, {"phase": "ship", "status": "ok"})

        # Read launch report to confirm shipped
        import json
        launch_report_path = WORKSPACE / "state" / "products" / slug / "launch-report.json"
        if not launch_report_path.exists():
            return {"slug": slug, "status": "failed", "phase": "ship", "error": "No launch report found"}

        launch_report = json.loads(launch_report_path.read_text())
        return {
            "slug": slug,
            "status": launch_report.get("status", "UNKNOWN"),
            "stripe_url": launch_report.get("stripe_payment_link_url", ""),
            "gumroad_url": launch_report.get("gumroad_listing_url", ""),
        }
    except Exception as e:
        write_pipeline_status(WORKSPACE, slug, {"phase": "ship", "status": "failed", "error": str(e)})
        return {"slug": slug, "status": "failed", "phase": "ship", "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: run_ceo_pipeline.py <slug>")
        sys.exit(1)

    slug = sys.argv[1]
    result = run_pipeline(slug)

    import json
    print("\n" + "="*60)
    print("PIPELINE RESULT:")
    print(json.dumps(result, indent=2))
    print("="*60)

    sys.exit(0 if result.get("status") in ("SHIPPED", "FULLY_SHIPPED") else 1)
