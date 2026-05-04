"""Stripe test-mode E2E smoke. Requires STRIPE_SECRET_KEY=sk_test_... in env."""
import os
import pytest
import requests

from scripts.stripe_helpers import create_product, create_price, create_payment_link


pytestmark = pytest.mark.skipif(
    not os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_test_"),
    reason="Requires STRIPE_SECRET_KEY=sk_test_... in env"
)


def test_full_stripe_flow_test_mode():
    product = create_product(slug="smoke-test-niche", name="Smoke Test Niche", description="Smoke test product")
    assert product.id.startswith("prod_")

    price = create_price(product_id=product.id, price_usd=27)
    assert price.id.startswith("price_")
    assert price.unit_amount == 2700

    link = create_payment_link(price_id=price.id, success_message="Smoke test thank-you")
    assert link.url.startswith("https://")

    response = requests.get(link.url, timeout=15)
    assert response.status_code == 200
    assert "stripe" in response.text.lower() or "checkout" in response.text.lower()
