import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/launch_report.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid():
    return {
        "version": 1,
        "type": "launch_report",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T20:30:00Z",
        "created_by": "engineer",
        "status": "SHIPPED",
        "summary": "Live on Stripe + Gumroad. Smoke tests green.",
        "stripe_product_id": "prod_dsl_abc123",
        "stripe_price_id": "price_xyz789",
        "stripe_payment_link_url": "https://buy.stripe.com/test_xyz",
        "gumroad_url": "https://gumroad.com/l/abc",
        "smoke_test": {"passed": True, "checked_at": "2026-05-04T20:29:00Z"},
        "spec_file": "state/products/homeowner-permit-history-fl/spec.json"
    }


def test_shipped_passes(schema):
    jsonschema.validate(_valid(), schema)


def test_failed_smoke_test_blocks_status(schema):
    obj = _valid()
    obj["status"] = "FAILED"
    obj["smoke_test"] = {"passed": False, "checked_at": "...", "failure_reason": "Stripe URL 404"}
    obj["failure_reason"] = "Stripe URL 404"
    jsonschema.validate(obj, schema)


def test_shipped_requires_smoke_pass(schema):
    obj = _valid()
    obj["smoke_test"]["passed"] = False
    # If shipped, smoke must be passed: enforced via allOf
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
