import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/opportunity_brief.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_brief():
    return {
        "version": 1,
        "type": "opportunity_brief",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T13:00:00Z",
        "created_by": "opportunity-researcher",
        "status": "PROPOSED",
        "score": 8,
        "summary": "Florida homeowners want pre-purchase permit reports.",
        "audience": {"who": "FL homeowners", "where_found": ["r/RealEstate"]},
        "data_wanted": "Permit history per address",
        "evidence": [{"source": "reddit", "url": "https://reddit.com/...", "quote": "Would pay $50"}],
        "willingness_to_pay": {"signal": "$50 mentioned", "confidence": "moderate"},
        "source_rights": {"public": True, "examples": ["miamidade.gov/permits"]},
        "first_sale_path": {"channel": "FB groups", "angle": "instant report"}
    }


def test_valid_brief_passes(schema):
    jsonschema.validate(_valid_brief(), schema)


def test_missing_score_fails(schema):
    brief = _valid_brief()
    del brief["score"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(brief, schema)


def test_score_out_of_range_fails(schema):
    brief = _valid_brief()
    brief["score"] = 11
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(brief, schema)


def test_invalid_status_fails(schema):
    brief = _valid_brief()
    brief["status"] = "MAYBE"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(brief, schema)


def test_missing_evidence_fails(schema):
    brief = _valid_brief()
    del brief["evidence"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(brief, schema)
