import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/product_spec.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid():
    return {
        "version": 1,
        "type": "product_spec",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T20:00:00Z",
        "created_by": "ceo",
        "status": "READY_TO_SHIP",
        "summary": "Florida Homeowner Permit History Report — $27 one-time CSV",
        "name": "Florida Homeowner Permit History Report",
        "format": "one_time",
        "deliverable": "csv",
        "price_usd": 27,
        "bonus_stack": ["Quick-start PDF", "Slack channel access (first 50 buyers)"],
        "dataset_file": "state/datasets/homeowner-permit-history-fl/clean-2026-05-04.csv",
        "ethics_ledger": "state/ethics-ledger/2026-05-04-homeowner-permit-history-fl.json",
        "audience": "FL homeowners pre-purchase + flippers",
        "stripe_product_prefix": "dsl_",
        "channels": ["stripe_payment_link", "gumroad"]
    }


def test_valid_passes(schema):
    jsonschema.validate(_valid(), schema)


def test_invalid_format_fails(schema):
    obj = _valid()
    obj["format"] = "subscription"  # not in v1 enum
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_zero_price_fails(schema):
    obj = _valid()
    obj["price_usd"] = 0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_missing_ethics_ledger_fails(schema):
    obj = _valid()
    del obj["ethics_ledger"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
