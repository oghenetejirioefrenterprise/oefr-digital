import os
import json
import stripe
from pathlib import Path
from datetime import datetime, timedelta, timezone

stripe.api_key = os.environ["STRIPE_SECRET"]

SLUG = "new-fmcsa-carrier-leads-2026-05"
WORKSPACE = Path(__file__).resolve().parents[1]
LAUNCH_REPORT = WORKSPACE / "state" / "products" / SLUG / "launch-report.json"
SUB_PRODUCTS = WORKSPACE / "state" / "subscription-products.json"

report = json.loads(LAUNCH_REPORT.read_text())
if report.get("stripe_subscription_payment_link_url"):
    print("Subscription Payment Link already exists:", report["stripe_subscription_payment_link_url"])
    raise SystemExit(0)

product = stripe.Product.create(
    name="New FMCSA Carriers — Monthly Subscription",
    description="15,770+ newly authorized US trucking carriers, refreshed quarterly. Cancel anytime.",
    metadata={"slug": SLUG, "dsl_product_type": "subscription"},
)

price = stripe.Price.create(
    product=product.id,
    unit_amount=2900,
    currency="usd",
    recurring={"interval": "month"},
)

payment_link = stripe.PaymentLink.create(
    line_items=[{"price": price.id, "quantity": 1}],
)

report["stripe_subscription_product_id"] = product.id
report["stripe_subscription_price_id"] = price.id
report["stripe_subscription_payment_link_url"] = payment_link.url
LAUNCH_REPORT.write_text(json.dumps(report, indent=2) + "\n")

next_refresh = (datetime.now(timezone.utc) + timedelta(days=90)).date().isoformat()
sub_data = {"version": 1, "products": {}}
if SUB_PRODUCTS.exists():
    sub_data = json.loads(SUB_PRODUCTS.read_text())
sub_data["products"][SLUG] = {
    "stripe_subscription_product_id": product.id,
    "stripe_subscription_price_id": price.id,
    "stripe_subscription_payment_link_url": payment_link.url,
    "monthly_price_usd": 29,
    "refresh_cadence_days": 90,
    "next_refresh_due": next_refresh,
}
SUB_PRODUCTS.write_text(json.dumps(sub_data, indent=2) + "\n")

print("Created subscription:", payment_link.url)
