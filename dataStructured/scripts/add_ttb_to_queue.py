#!/usr/bin/env python3
"""Add TTB product to distribution queue."""

import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.lib.distribution_queue import append_item, read_queue

QUEUE_FILE = Path("/home/oghenetejiri/apps/dataStructured/state/distribution-queue.json")
SPEC_FILE = Path("/home/oghenetejiri/apps/dataStructured/state/products/ttb-brewery-winery-distillery-directory/spec.json")

# Load spec for product details
spec = json.loads(SPEC_FILE.read_text())

# Create new queue item
new_item = {
    "id": f"{spec['slug']}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
    "slug": spec["slug"],
    "name": spec["name"],
    "stripe_payment_link_url": spec["stripe"]["payment_link"],
    "gumroad_url": spec["gumroad"].get("listing_url"),
    "price_usd": spec["price_usd"],
    "audience": "Equipment suppliers (barrel brokers, bottling lines, tanks) prospecting new wineries & distilleries, POS platforms (Toast, Arryved) targeting craft beverage producers, ingredient vendors (hops, grapes, grains, yeasts) building craft beverage prospect lists, packaging companies, compliance consultants, insurance brokers, marketing agencies",
    "added_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "status": "ready"
}

# Idempotency: skip if an item with this id is already queued.
existing_ids = {it.get("id") for it in read_queue(QUEUE_FILE).get("items", [])}
if new_item["id"] in existing_ids:
    print(f"⏭  Already in distribution queue (id={new_item['id']}); nothing to do.")
else:
    # append_item handles lazy queue creation, file-locking, atomic write,
    # and JSON-schema validation of the resulting queue.
    append_item(QUEUE_FILE, new_item)
    print("✅ Added to distribution queue:")
    print(f"   ID: {new_item['id']}")
    print(f"   Name: {new_item['name']}")
    print(f"   Stripe: {new_item['stripe_payment_link_url']}")
    print(f"   Gumroad: {new_item['gumroad_url']}")
    print(f"   Status: {new_item['status']}")
