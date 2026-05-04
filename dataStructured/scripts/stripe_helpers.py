"""Stripe helpers — product, price, Payment Link creation for DataStructured.

Reads STRIPE_SECRET_KEY from environment. Always namespaces products with `dsl_` prefix.
"""
import os
import stripe

from scripts.lib.slug import stripe_product_id


def _ensure_key() -> None:
    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY not set in environment")
    stripe.api_key = key


def create_product(slug: str, name: str, description: str):
    """Create a Stripe product with `dsl_` prefix in metadata.product_id."""
    _ensure_key()
    pid = stripe_product_id(slug)
    return stripe.Product.create(
        name=name,
        description=description,
        metadata={"product_id": pid, "lob": "datastructured"}
    )


def create_price(product_id: str, price_usd: int):
    """Create a one-time Stripe Price in USD cents."""
    _ensure_key()
    return stripe.Price.create(
        product=product_id,
        unit_amount=price_usd * 100,
        currency="usd",
    )


def create_payment_link(price_id: str, success_message: str):
    """Create a Payment Link with a custom hosted confirmation message."""
    _ensure_key()
    return stripe.PaymentLink.create(
        line_items=[{"price": price_id, "quantity": 1}],
        after_completion={
            "type": "hosted_confirmation",
            "hosted_confirmation": {"custom_message": success_message},
        },
    )
