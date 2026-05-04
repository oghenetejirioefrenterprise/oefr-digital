import pytest
import stripe
from unittest.mock import patch, MagicMock
from scripts.stripe_helpers import create_product


def test_create_product_uses_dsl_prefix():
    fake_product = MagicMock()
    fake_product.id = "prod_test123"
    fake_product.metadata = {"product_id": "dsl_test_niche"}

    with patch("stripe.Product.create", return_value=fake_product) as mock_create:
        product = create_product(slug="test-niche", name="Test Niche Report", description="Test product")

    args, kwargs = mock_create.call_args
    assert kwargs["metadata"]["product_id"] == "dsl_test_niche"
    assert product.id == "prod_test123"


def test_create_product_passes_name_and_description():
    fake = MagicMock(); fake.id = "prod_x"
    with patch("stripe.Product.create", return_value=fake) as mock_create:
        create_product(slug="x-y", name="X-Y Report", description="A report on X")
    _, kwargs = mock_create.call_args
    assert kwargs["name"] == "X-Y Report"
    assert kwargs["description"] == "A report on X"


from scripts.stripe_helpers import create_price, create_payment_link


def test_create_price_one_time_in_cents():
    fake = MagicMock(); fake.id = "price_x"
    with patch("stripe.Price.create", return_value=fake) as mock_create:
        create_price(product_id="prod_x", price_usd=27)
    _, kwargs = mock_create.call_args
    assert kwargs["unit_amount"] == 2700  # cents
    assert kwargs["currency"] == "usd"
    assert "recurring" not in kwargs  # one-time only in v1


def test_create_payment_link_uses_price():
    fake_link = MagicMock(); fake_link.url = "https://buy.stripe.com/test_xyz"
    with patch("stripe.PaymentLink.create", return_value=fake_link) as mock_create:
        link = create_payment_link(price_id="price_x", success_message="Thanks!")
    _, kwargs = mock_create.call_args
    assert kwargs["line_items"][0]["price"] == "price_x"
    assert kwargs["after_completion"]["type"] == "hosted_confirmation"
    assert "Thanks!" in kwargs["after_completion"]["hosted_confirmation"]["custom_message"]
    assert link.url.startswith("https://")
