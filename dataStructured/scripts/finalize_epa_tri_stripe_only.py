#!/usr/bin/env python3
"""
Finalize EPA TRI launch report - Stripe shipped, Gumroad pending manual creation.
Similar to NPPES Dentists pattern (task #24).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SLUG = "epa-tri-toxic-release-reporting-facilities-2026-05"
REPORT_FILE = BASE / "state" / "products" / SLUG / "launch-report.json"

report = json.loads(REPORT_FILE.read_text())

# Update report - Stripe shipped, Gumroad pending
report["status"] = "SHIPPED"
report["summary"] = (
    "Live on Stripe. CSV (78,647 rows) hosted on GitHub Release. "
    "Stripe Payment Link smoke test green. "
    "Gumroad listing pending manual creation (automation blocked on new product flow). "
    "Distribution queue deferred until Gumroad complete."
)
report["gumroad_url"] = None
report["gumroad_pending"] = True
report["gumroad_automation_failure"] = "Product type selection workflow changed - automation stuck on /products/new"

REPORT_FILE.write_text(json.dumps(report, indent=2))

print("✓ Launch report updated")
print(f"  Status: SHIPPED (Stripe only)")
print(f"  Stripe: {report['stripe_payment_link_url']}")
print(f"  Gumroad: Pending manual creation")
print("\nNext: Manually create Gumroad listing at https://app.gumroad.com/products/new")
print(f"      Title: {report['slug']}")
print(f"      Price: $49")
print("      Upload: state/datasets/epa-tri-toxic-release-reporting-facilities-2026-05.csv")
