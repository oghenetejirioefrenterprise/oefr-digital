import pytest
from scripts.lib.slug import slugify, stripe_product_id


def test_slugify_lowercases_and_dashes():
    assert slugify("Florida Homeowner Permit History") == "florida-homeowner-permit-history"


def test_slugify_strips_punctuation():
    assert slugify("Permits! & Records 2026") == "permits-records-2026"


def test_slugify_collapses_whitespace():
    assert slugify("  multiple   spaces  ") == "multiple-spaces"


def test_slugify_rejects_empty():
    with pytest.raises(ValueError):
        slugify("")


def test_slugify_rejects_only_punctuation():
    with pytest.raises(ValueError):
        slugify("!!!")


def test_stripe_product_id_prefixed():
    assert stripe_product_id("homeowner-permits-fl") == "dsl_homeowner_permits_fl"


def test_stripe_product_id_idempotent():
    sid = stripe_product_id("test-niche")
    assert stripe_product_id(sid.replace("dsl_", "").replace("_", "-")) == sid
