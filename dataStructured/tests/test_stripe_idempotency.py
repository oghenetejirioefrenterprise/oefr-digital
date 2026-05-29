"""Idempotency-key support for the Stripe helpers (added in the dedup refactor).

The key safety property: passing idempotency_key must NOT change the dollar
amount charged — unit_amount stays price_usd * 100 cents.
"""
from unittest.mock import patch, MagicMock

from scripts.stripe_helpers import create_product, create_price, create_payment_link


def test_idempotency_key_forwarded_when_provided():
    fake = MagicMock(); fake.id = "prod_x"
    with patch("stripe.Product.create", return_value=fake) as m:
        create_product(slug="x-y", name="X", description="d", idempotency_key="dsl_x_y")
    _, kwargs = m.call_args
    assert kwargs["idempotency_key"] == "dsl_x_y"


def test_idempotency_key_omitted_when_absent():
    fake = MagicMock(); fake.id = "prod_x"
    with patch("stripe.Product.create", return_value=fake) as m:
        create_product(slug="x-y", name="X", description="d")
    _, kwargs = m.call_args
    assert "idempotency_key" not in kwargs


def test_price_amount_unchanged_with_idempotency_key():
    fake = MagicMock(); fake.id = "price_x"
    with patch("stripe.Price.create", return_value=fake) as m:
        create_price(product_id="prod_x", price_usd=49, idempotency_key="dsl_x_price")
    _, kwargs = m.call_args
    assert kwargs["unit_amount"] == 4900  # dollars -> cents, unaffected by idempotency
    assert kwargs["currency"] == "usd"
    assert kwargs["idempotency_key"] == "dsl_x_price"


def test_payment_link_idempotency_key_forwarded():
    fake = MagicMock(); fake.url = "https://buy.stripe.com/x"
    with patch("stripe.PaymentLink.create", return_value=fake) as m:
        create_payment_link(price_id="price_x", success_message="Thanks!", idempotency_key="dsl_x_link")
    _, kwargs = m.call_args
    assert kwargs["idempotency_key"] == "dsl_x_link"
