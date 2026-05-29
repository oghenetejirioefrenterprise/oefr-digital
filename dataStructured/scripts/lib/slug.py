"""Slug helpers — niche slugs and Stripe product IDs (LoB-namespaced)."""
import re

_VALID_CHARS = re.compile(r"[^a-z0-9]+")
STRIPE_PREFIX = "dsl_"


def slugify(text: str) -> str:
    """Lowercase + dash-separated. Raise ValueError on empty or all-punctuation."""
    s = text.strip().lower()
    s = _VALID_CHARS.sub("-", s).strip("-")
    if not s:
        raise ValueError(f"Cannot slugify {text!r} — no valid characters")
    return s


def stripe_product_id(slug: str) -> str:
    """Return the LoB-namespaced Stripe product ID for *slug*."""
    s = slugify(slug).replace("-", "_")
    return f"{STRIPE_PREFIX}{s}"
