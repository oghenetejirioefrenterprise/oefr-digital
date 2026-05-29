import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/distribution_queue.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_empty():
    return {"version": 1, "type": "distribution_queue", "updated_at": "2026-05-04T00:00:00Z", "items": []}


def _valid_with_item():
    return {
        "version": 1,
        "type": "distribution_queue",
        "updated_at": "2026-05-04T20:30:00Z",
        "items": [
            {
                "id": "homeowner-permit-history-fl-2026-05-04",
                "slug": "homeowner-permit-history-fl",
                "name": "Florida Homeowner Permit History Report",
                "stripe_payment_link_url": "https://buy.stripe.com/test_xyz",
                "gumroad_url": "https://gumroad.com/l/abc",
                "price_usd": 27,
                "audience": "FL homeowners pre-purchase",
                "added_at": "2026-05-04T20:30:00Z",
                "status": "ready"
            }
        ]
    }


def test_empty_queue_passes(schema):
    jsonschema.validate(_valid_empty(), schema)


def test_with_item_passes(schema):
    jsonschema.validate(_valid_with_item(), schema)


def test_invalid_status_fails(schema):
    obj = _valid_with_item()
    obj["items"][0]["status"] = "live"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
