import json
from pathlib import Path
import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parents[2] / "state/_schemas/ethics_ledger_entry.schema.json"


@pytest.fixture
def schema():
    return json.loads(SCHEMA_PATH.read_text())


def _valid_pass():
    return {
        "version": 1,
        "type": "ethics_ledger_entry",
        "slug": "homeowner-permit-history-fl",
        "created": "2026-05-04T19:55:00Z",
        "created_by": "compliance-officer",
        "verdict": "PASS",
        "summary": "All sources public county records; no PII; ToS clean.",
        "audit": {
            "public_access": {"answer": "Yes", "evidence": ["https://miamidade.gov/...", "https://broward.org/..."]},
            "pii": {"answer": "No", "detail": "Address is property address, not personal residence"},
            "robots_tos_clean": {"answer": "Yes", "domains_checked": ["miamidade.gov"]},
            "no_copyright_verbatim": {"answer": "Yes", "spot_check": "10 random rows"},
            "dual_use_sensitive": {"answer": "No", "justification": "n/a"},
            "subject_objection_test": {"answer": "Pass", "reasoning": "Property records are public by statute"},
            "gdpr_ccpa_clean": {"answer": "Yes", "reasoning": "No EU/CA persons in dataset"}
        },
        "dataset_file": "state/datasets/homeowner-permit-history-fl/clean-2026-05-04.csv"
    }


def test_pass_with_all_audit_passes(schema):
    jsonschema.validate(_valid_pass(), schema)


def test_pass_missing_audit_question_fails(schema):
    obj = _valid_pass()
    del obj["audit"]["pii"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_fail_requires_unblocker(schema):
    obj = _valid_pass()
    obj["verdict"] = "FAIL"
    obj["audit"]["pii"]["answer"] = "Yes"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)


def test_fail_with_unblocker_passes(schema):
    obj = _valid_pass()
    obj["verdict"] = "FAIL"
    obj["audit"]["pii"]["answer"] = "Yes"
    obj["unblocker"] = "Strip homeowner names; resubmit"
    jsonschema.validate(obj, schema)


def test_revocation_must_reference_original(schema):
    obj = _valid_pass()
    obj["verdict"] = "REVOCATION"
    # missing 'revokes'
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, schema)
