import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/quality_report.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_approved():
    return {
        "version": 1,
        "type": "quality_report",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T19:45:00Z",
        "created_by": "data-steward",
        "status": "APPROVED",
        "summary": "1180 rows after dedupe; signal:noise 96%.",
        "source_metadata": "state/datasets/homeowner-permit-history-fl/raw-2026-05-04.metadata.json",
        "data_file": "state/datasets/homeowner-permit-history-fl/clean-2026-05-04.csv",
        "rows_in": 1234,
        "rows_out": 1180,
        "transformations": [
            {"step": "schema_fix", "rows_before": 1234, "rows_after": 1230, "notes": "4 malformed rows dropped"}
        ],
        "source_liveness_sample": {"sampled": 118, "dead": 3, "action": "below threshold"},
        "refresh_recommendation": "monthly"
    }


def test_valid_approved_passes(schema):
    jsonschema.validate(_valid_approved(), schema)


def test_rejected_requires_unblocker(schema):
    obj = _valid_approved()
    obj["status"] = "REJECTED"
    # Missing unblocker → must fail
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_rejected_with_unblocker_passes(schema):
    obj = _valid_approved()
    obj["status"] = "REJECTED"
    obj["unblocker"] = "Engineer dropped 40% of rows; re-run with broader query set"
    jsonschema.validate(obj, schema)


def test_invalid_refresh_fails(schema):
    obj = _valid_approved()
    obj["refresh_recommendation"] = "yearly"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
