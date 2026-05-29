#!/usr/bin/env python3
"""Run the CEO pipeline for nonprofit-board-directors-executives."""

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent

# Ensure the repo root is importable regardless of the launch cwd.
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from scripts.ceo_orchestrator import dispatch_employee, write_pipeline_status
slug = "nonprofit-board-directors-executives"

print(f"🔄 Running pipeline for {slug}")

# Harvest
print(f"\n📥 Phase 1: data-engineer (harvest)")
write_pipeline_status(WORKSPACE, slug, {"phase": "harvest", "status": "running"})
try:
    result = dispatch_employee(
        "data-engineer",
        f"Harvest dataset for {slug}. Read state/products/{slug}/spec.json for full requirements. Extract from IRS Form 990 Part VII and state charity registries.",
        timeout_sec=7200  # 2 hours
    )
    print(result)
    write_pipeline_status(WORKSPACE, slug, {"phase": "harvest", "status": "ok"})
except Exception as e:
    print(f"❌ data-engineer failed: {e}")
    write_pipeline_status(WORKSPACE, slug, {"phase": "harvest", "status": "failed", "error": str(e)})
    sys.exit(1)

# Validate
print(f"\n🧹 Phase 2: data-steward (validate)")
write_pipeline_status(WORKSPACE, slug, {"phase": "validate", "status": "running"})
try:
    result = dispatch_employee(
        "data-steward",
        f"Validate dataset {slug}. Check state/datasets/{slug}/raw-*.csv and produce clean-*.csv.",
        timeout_sec=3600
    )
    print(result)
    write_pipeline_status(WORKSPACE, slug, {"phase": "validate", "status": "ok"})
except Exception as e:
    print(f"❌ data-steward failed: {e}")
    write_pipeline_status(WORKSPACE, slug, {"phase": "validate", "status": "failed", "error": str(e)})
    sys.exit(1)

# Compliance
print(f"\n⚖️ Phase 3: compliance-officer (audit)")
write_pipeline_status(WORKSPACE, slug, {"phase": "compliance", "status": "running"})
try:
    result = dispatch_employee(
        "compliance-officer",
        f"Compliance audit for {slug}. Check state/datasets/{slug}/clean-*.csv for PII and public data compliance.",
        timeout_sec=1800
    )
    print(result)
    write_pipeline_status(WORKSPACE, slug, {"phase": "compliance", "status": "ok"})
except Exception as e:
    print(f"❌ compliance-officer failed: {e}")
    write_pipeline_status(WORKSPACE, slug, {"phase": "compliance", "status": "failed", "error": str(e)})
    sys.exit(1)

# Ship
print(f"\n🚀 Phase 4: engineer (ship)")
write_pipeline_status(WORKSPACE, slug, {"phase": "ship", "status": "running"})
try:
    result = dispatch_employee(
        "engineer",
        f"Ship product {slug}. Create Stripe Payment Link and Gumroad listing using state/products/{slug}/spec.json and state/datasets/{slug}/clean-*.csv.",
        timeout_sec=3600
    )
    print(result)
    write_pipeline_status(WORKSPACE, slug, {"phase": "ship", "status": "ok"})
except Exception as e:
    print(f"❌ engineer failed: {e}")
    write_pipeline_status(WORKSPACE, slug, {"phase": "ship", "status": "failed", "error": str(e)})
    sys.exit(1)

# Done
write_pipeline_status(WORKSPACE, slug, {"phase": "done", "status": "ok"})
print(f"\n✅ Pipeline complete for {slug}")
