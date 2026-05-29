"""Stripe helpers — product, price, Payment Link creation for DataStructured.

Reads STRIPE_SECRET from environment (matches the convention in ~/.profile).
Always namespaces products with `dsl_` prefix.
"""
import os
import stripe

from scripts.lib.slug import stripe_product_id


def _ensure_key() -> None:
    key = os.environ.get("STRIPE_SECRET")
    if not key:
        raise RuntimeError("STRIPE_SECRET not set in environment")
    stripe.api_key = key


def create_product(slug: str, name: str, description: str, *, idempotency_key: str = None):
    """Create a Stripe product with `dsl_` prefix in metadata.product_id.

    Pass ``idempotency_key`` (e.g. derived from the slug) to make retries safe —
    Stripe returns the original object instead of creating a duplicate.
    """
    _ensure_key()
    pid = stripe_product_id(slug)
    kwargs = dict(
        name=name,
        description=description,
        metadata={"product_id": pid, "lob": "datastructured"},
    )
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key
    return stripe.Product.create(**kwargs)


def create_price(product_id: str, price_usd: int, *, idempotency_key: str = None):
    """Create a one-time Stripe Price. ``price_usd`` is DOLLARS (converted to cents)."""
    _ensure_key()
    kwargs = dict(
        product=product_id,
        unit_amount=price_usd * 100,
        currency="usd",
    )
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key
    return stripe.Price.create(**kwargs)


def create_payment_link(price_id: str, success_message: str, *, idempotency_key: str = None):
    """Create a Payment Link with a custom hosted confirmation message."""
    _ensure_key()
    kwargs = dict(
        line_items=[{"price": price_id, "quantity": 1}],
        after_completion={
            "type": "hosted_confirmation",
            "hosted_confirmation": {"custom_message": success_message},
        },
    )
    if idempotency_key:
        kwargs["idempotency_key"] = idempotency_key
    return stripe.PaymentLink.create(**kwargs)
