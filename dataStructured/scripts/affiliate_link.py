"""Affiliate UTM-link generator for DataStructured partnerships.

Generates a Stripe Payment Link with `?client_reference_id=<id>` appended,
where `<id>` deterministically encodes (partner_handle, product_slug). The
generated link is persisted in `state/partnerships/utm-links.json` so the
customer-success agent's sweep can reconcile incoming Stripe charges back
to the originating partner (see scripts/customer_sweep.py reconcile_affiliates).

CLI:
    python scripts/affiliate_link.py --partner <handle> \\
        --product-slug <slug> [--commission-pct N]

Reads `state/products/<slug>/launch-report.json` to find the base Stripe
Payment Link. Writes/updates `state/partnerships/utm-links.json` idempotently
(replaces any prior entry for the same (partner, product) pair). Prints the
final affiliate URL to stdout — that's the link the partner gets.

Phase 3 sub-project 6.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
LINKS_FILE = WORKSPACE / "state" / "partnerships" / "utm-links.json"


def short_hash(s: str) -> str:
    """Deterministic 6-char hex digest used to namespace the client_reference_id."""
    return hashlib.sha1(s.encode()).hexdigest()[:6]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Stripe Payment Link with a partner-scoped client_reference_id."
    )
    parser.add_argument("--partner", required=True,
                        help="Partner handle (e.g. trucker_dad_newsletter)")
    parser.add_argument("--product-slug", required=True,
                        help="Product slug under state/products/")
    parser.add_argument("--commission-pct", type=int, default=30,
                        help="Commission percentage owed to partner (default: 30)")
    args = parser.parse_args()

    launch = WORKSPACE / "state" / "products" / args.product_slug / "launch-report.json"
    if not launch.exists():
        raise SystemExit(f"no launch-report for {args.product_slug}")
    report = json.loads(launch.read_text())
    base_link = report.get("stripe_payment_link_url")
    if not base_link:
        raise SystemExit(f"no stripe_payment_link_url in {launch}")

    client_ref = (
        f"{args.partner}"
        f"_{args.product_slug.split('-')[0]}"
        f"_{short_hash(args.partner + args.product_slug)}"
    )
    affiliate_link = f"{base_link}?client_reference_id={client_ref}"

    LINKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {"version": 1, "links": []}
    if LINKS_FILE.exists():
        data = json.loads(LINKS_FILE.read_text())
    # Idempotent: replace any prior entry for the same (partner, product)
    data["links"] = [
        e for e in data["links"]
        if not (e["partner"] == args.partner
                and e["product_slug"] == args.product_slug)
    ]
    data["links"].append({
        "partner": args.partner,
        "product_slug": args.product_slug,
        "client_reference_id": client_ref,
        "stripe_payment_link_with_ref": affiliate_link,
        "commission_pct": args.commission_pct,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    LINKS_FILE.write_text(json.dumps(data, indent=2) + "\n")
    print(affiliate_link)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
