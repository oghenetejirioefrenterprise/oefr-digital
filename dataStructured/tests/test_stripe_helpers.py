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
