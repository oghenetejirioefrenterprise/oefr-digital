#!/usr/bin/env python3
"""Rebuild state/distribution-queue.json from shipped products' launch reports.

The queue file was missing. This reconstructs it from the authoritative
launch-report.json (live Stripe/Gumroad URLs) + spec.json (name/price/audience)
for every product that has actually shipped (valid Stripe payment link).

Item IDs reuse the historical id from the distribution log where one exists, so
that already_posted() dedup continues to match prior entries.
"""
import glob
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.atomic_io import write_json_atomic  # noqa: E402
from scripts.lib.schema_validator import validate  # noqa: E402

QUEUE_PATH = BASE / "state" / "distribution-queue.json"
LOG_PATH = BASE / "state" / "distribution-log.json"

STRIPE_RE = re.compile(r"https://buy\.stripe\.com/[A-Za-z0-9]+")
GUMROAD_RE = re.compile(r"https://[A-Za-z0-9.\-]*gumroad\.com/l/[A-Za-z0-9]+")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def historical_ids() -> dict:
    """slug -> earliest item_id seen in the distribution log."""
    if not LOG_PATH.exists():
        return {}
    log = json.loads(LOG_PATH.read_text())
    out = {}
    for e in log.get("entries", []):
        out.setdefault(e["slug"], e["item_id"])
    return out


def main() -> None:
    slug2id = historical_ids()
    items = []
    skipped = []

    for lr_path in sorted(glob.glob(str(BASE / "state" / "products" / "*" / "launch-report.json"))):
        lr = json.loads(Path(lr_path).read_text())
        slug = lr.get("slug")
        spec_path = Path(lr_path).parent / "spec.json"
        if not spec_path.exists():
            skipped.append((slug, "no spec.json"))
            continue
        spec = json.loads(spec_path.read_text())

        blob = json.dumps(lr)
        stripe_m = STRIPE_RE.search(blob)
        if not stripe_m:
            skipped.append((slug, "no valid stripe payment link — not shipped"))
            continue
        stripe_url = stripe_m.group(0)

        gum_m = GUMROAD_RE.search(blob)
        gumroad_url = gum_m.group(0) if gum_m else None

        # Prefer the slug that appears in the log (it carries the historical id);
        # fall back to constructing one from creation date.
        item_id = slug2id.get(slug)
        if not item_id:
            created = (lr.get("created") or spec.get("created") or _now())[:10]
            item_id = f"{slug}-{created}"

        items.append({
            "id": item_id,
            "slug": slug,
            "name": spec.get("name", slug),
            "stripe_payment_link_url": stripe_url,
            "gumroad_url": gumroad_url,
            "price_usd": int(spec.get("price_usd") or 49),
            "audience": spec.get("audience", "Sales, marketing, and data teams prospecting this vertical."),
            "added_at": _now(),
            "status": "ready",
        })

    queue = {
        "version": 1,
        "type": "distribution_queue",
        "updated_at": _now(),
        "items": items,
    }
    validate("distribution_queue", queue)
    write_json_atomic(QUEUE_PATH, queue)

    print(f"✅ Rebuilt queue with {len(items)} shipped products -> {QUEUE_PATH}")
    for it in items:
        print(f"   • {it['id']:55} ${it['price_usd']:<4} gumroad={'Y' if it['gumroad_url'] else '-'}")
    if skipped:
        print("\nSkipped (not shipped / incomplete):")
        for slug, why in skipped:
            print(f"   - {slug}: {why}")


if __name__ == "__main__":
    main()
