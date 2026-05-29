#!/usr/bin/env python3
"""Ship TTB Brewery/Winery/Distillery Directory product.

Creates Stripe product + price + Payment Link for the TTB directory.
"""
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.stripe_helpers import create_product, create_price, create_payment_link


def main():
    # Load spec
    spec_path = Path("/home/oghenetejiri/apps/dataStructured/state/products/ttb-brewery-winery-distillery-directory/spec.json")
    with open(spec_path) as f:
        spec = json.load(f)

    slug = spec["dataset"]["slug"]
    stripe_config = spec["stripe"]

    print(f"🚀 Shipping {slug}")
    print(f"   Product: {stripe_config['product_name']}")
    print(f"   Price: ${stripe_config['price_usd']}")

    # Idempotency guard: if a Payment Link already exists in the spec, the product
    # was already shipped to Stripe. Re-creating would mint a duplicate billable
    # Product/Price/Payment Link and orphan the live link. Reuse the existing link.
    existing_link = stripe_config.get("payment_link")
    if existing_link:
        print("\n⏭  Stripe Payment Link already present — skipping creation (idempotent).")
        print(f"   Payment Link: {existing_link}")
        print("\n" + "="*60)
        print("✅ ALREADY SHIPPED (Stripe Payment Link reused)")
        print("="*60)
        print(f"Payment Link: {existing_link}")
        return {
            "product_id": stripe_config.get("product_id"),
            "price_id": stripe_config.get("price_id"),
            "payment_link_url": existing_link,
        }

    # Step 1: Create Stripe product
    print("\n📦 Creating Stripe product...")
    product = create_product(
        slug=slug,
        name=stripe_config["product_name"],
        description=stripe_config["description"]
    )
    print(f"   ✅ Product ID: {product.id}")

    # Persist the product id immediately so a crash before the link is created
    # does not cause a duplicate product on re-run.
    spec["stripe"]["product_id"] = product.id
    with open(spec_path, 'w') as f:
        json.dump(spec, f, indent=2)

    # Step 2: Create price
    print("\n💰 Creating price...")
    price = create_price(
        product_id=product.id,
        price_usd=stripe_config["price_usd"]
    )
    print(f"   ✅ Price ID: {price.id}")

    # Persist the price id immediately (idempotent re-run support).
    spec["stripe"]["price_id"] = price.id
    with open(spec_path, 'w') as f:
        json.dump(spec, f, indent=2)

    # Step 3: Create Payment Link with delivery instructions
    print("\n🔗 Creating Payment Link...")
    success_message = (
        "Thank you for your purchase! Your US Winery & Distillery Directory "
        "(82,521 records, CSV format) will be delivered to your email receipt "
        "within 5 minutes. Check your inbox for the Stripe receipt email — "
        "it contains your download link. If you don't see it, check spam. "
        "Questions? Email cciephantom@gmail.com"
    )

    payment_link = create_payment_link(
        price_id=price.id,
        success_message=success_message
    )
    print(f"   ✅ Payment Link: {payment_link.url}")

    # Step 4: Update spec.json with Stripe Payment Link
    print("\n📝 Updating spec.json...")
    spec["stripe"]["payment_link"] = payment_link.url
    with open(spec_path, 'w') as f:
        json.dump(spec, f, indent=2)
    print(f"   ✅ Updated {spec_path}")

    # Output summary for next steps
    print("\n" + "="*60)
    print("✅ STRIPE SETUP COMPLETE")
    print("="*60)
    print(f"Product ID: {product.id}")
    print(f"Price ID: {price.id}")
    print(f"Payment Link: {payment_link.url}")
    print("\n📋 NEXT STEPS:")
    print("1. Set up Stripe webhook for receipt delivery")
    print("2. Create Gumroad listing")
    print("3. Smoke test both URLs")
    print("4. Write launch-report.json")
    print("5. Copy CSV to product directory")
    print("6. Append to distribution-queue.json")

    return {
        "product_id": product.id,
        "price_id": price.id,
        "payment_link_url": payment_link.url
    }


if __name__ == "__main__":
    main()
