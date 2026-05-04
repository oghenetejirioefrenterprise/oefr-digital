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
