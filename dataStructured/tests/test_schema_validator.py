import pytest
from scripts.lib.schema_validator import validate, SchemaValidationError


def test_valid_brief_passes():
    brief = {
        "version": 1,
        "type": "opportunity_brief",
        "slug": "test-niche",
        "created": "2026-05-04T13:00:00Z",
        "created_by": "opportunity-researcher",
        "status": "PROPOSED",
        "score": 8,
        "summary": "Strong demand signal in niche X.",
        "audience": {"who": "test", "where_found": ["test"]},
        "data_wanted": "test data",
        "evidence": [{"source": "test", "url": "https://example.com"}],
        "willingness_to_pay": {"signal": "$10", "confidence": "moderate"},
        "source_rights": {"public": True, "examples": ["example.com"]},
        "first_sale_path": {"channel": "test", "angle": "test"}
    }
    validate("opportunity_brief", brief)  # should not raise


def test_invalid_brief_raises():
    bad_brief = {"version": 1, "type": "opportunity_brief"}
    with pytest.raises(SchemaValidationError) as exc:
        validate("opportunity_brief", bad_brief)
    assert "score" in str(exc.value) or "required" in str(exc.value)


def test_unknown_schema_raises():
    with pytest.raises(SchemaValidationError):
        validate("nonexistent_type", {})
