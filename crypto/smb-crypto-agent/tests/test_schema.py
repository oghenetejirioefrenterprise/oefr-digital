import pytest
from pydantic import ValidationError
from ingestion.schema import Setup, TranscriptSummary, VALID_CATEGORIES, VALID_TIMEFRAMES, VALID_CONFIDENCE


def test_valid_setup_parses():
    s = Setup(
        name="Breaking News Long",
        preconditions="Major macro print due; game plan prepared",
        entry_trigger="Buy on confirmed direction 1-3 minutes post-release",
        invalidation="Price closes back through release range mid",
        targets="1R and trail remainder",
        timeframe="intraday",
        confidence="high",
        crypto_adaptation_notes="CPI/FOMC apply; also ETF flow prints, unlock events",
        quotes=["breaking news trade", "pay for the trade"]
    )
    assert s.confidence == "high"


def test_timeframe_must_be_valid():
    with pytest.raises(ValidationError):
        Setup(
            name="X", preconditions="y", entry_trigger="y", invalidation="y",
            targets="y", timeframe=12345, confidence="high",
            crypto_adaptation_notes="", quotes=[],
        )


def test_confidence_must_be_valid():
    with pytest.raises(ValidationError):
        Setup(
            name="X", preconditions="y", entry_trigger="y", invalidation="y",
            targets="y", timeframe="intraday", confidence="maybe",
            crypto_adaptation_notes="", quotes=[],
        )


def test_valid_summary_parses():
    t = TranscriptSummary(
        file="Example_Video.transcript.md",
        video_id="abc123",
        title="Example",
        categories=["breaking_news", "risk_management"],
        equity_only=False,
        crypto_translatable=True,
        tactical_score=4,
        setups=[],
        principles=["Always pre-plan"],
        skip_reason=None,
    )
    assert t.tactical_score == 4


def test_category_must_be_in_vocab():
    t = TranscriptSummary(
        file="x.md", video_id="", title="",
        categories=["made_up_tag"],
        equity_only=False, crypto_translatable=True,
        tactical_score=0, setups=[], principles=[], skip_reason=None,
    )
    assert t.categories == ["other"]

    t2 = TranscriptSummary(
        file="x.md", video_id="", title="",
        categories=["psychology", "risk-management"],
        equity_only=False, crypto_translatable=True,
        tactical_score=0, setups=[], principles=[], skip_reason=None,
    )
    assert "trader_development" in t2.categories
    assert "risk_management" in t2.categories


def test_tactical_score_bounds():
    with pytest.raises(ValidationError):
        TranscriptSummary(
            file="x.md", video_id="", title="",
            categories=[], equity_only=False, crypto_translatable=True,
            tactical_score=6, setups=[], principles=[], skip_reason=None,
        )


def test_vocab_constants_populated():
    assert "breaking_news" in VALID_CATEGORIES
    assert "intraday" in VALID_TIMEFRAMES
    assert "high" in VALID_CONFIDENCE
