import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/raw_dataset_metadata.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid():
    return {
        "version": 1,
        "type": "raw_dataset_metadata",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T19:30:00Z",
        "created_by": "data-engineer",
        "status": "READY_FOR_STEWARD",
        "summary": "1234 permit records across 6 FL counties.",
        "source_brief": "state/opportunities/2026-05-04-homeowner-permit-history-fl.json",
        "data_file": "state/datasets/homeowner-permit-history-fl/raw-2026-05-04.csv",
        "row_count": 1234,
        "columns": ["id", "address", "permit_date", "permit_type", "source_url"],
        "queries_executed": ["site:miamidade.gov permits"],
        "urls_fetched": 87,
        "known_gaps": "Broward county records gated by captcha"
    }


def test_valid_passes(schema):
    jsonschema.validate(_valid(), schema)


def test_zero_rows_fails(schema):
    obj = _valid()
    obj["row_count"] = 0
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_missing_columns_fails(schema):
    obj = _valid()
    del obj["columns"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_invalid_status_fails(schema):
    obj = _valid()
    obj["status"] = "DONE"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
