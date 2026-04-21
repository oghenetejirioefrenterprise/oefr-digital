from typing import Literal
from pydantic import BaseModel, Field, field_validator

VALID_CATEGORIES: set[str] = {
    "breaking_news",
    "trend_day_continuation",
    "pullback_in_uptrend",
    "second_chance_retest",
    "fashionably_late",
    "imbalance_scalp",
    "relative_strength",
    "fade_the_extended",
    "opening_range_breakout",
    "liquidity_sweep",
    "basket_execution",
    "game_planning",
    "risk_management",
    "trade_review",
    "trader_development",
    "options_expression",
    "earnings_trade",
    "ipo_lockup",
    "short_interest",
    "other",
}

VALID_TIMEFRAMES: set[str] = {"scalp", "intraday", "swing"}
VALID_CONFIDENCE: set[str] = {"high", "med", "low"}


class Setup(BaseModel):
    name: str
    preconditions: str
    entry_trigger: str
    invalidation: str
    targets: str
    timeframe: Literal["scalp", "intraday", "swing"]
    confidence: Literal["high", "med", "low"]
    crypto_adaptation_notes: str
    quotes: list[str] = Field(default_factory=list)


class TranscriptSummary(BaseModel):
    file: str
    video_id: str
    title: str
    categories: list[str]
    equity_only: bool
    crypto_translatable: bool
    tactical_score: int = Field(ge=0, le=5)
    setups: list[Setup] = Field(default_factory=list)
    principles: list[str] = Field(default_factory=list)
    skip_reason: str | None = None

    @field_validator("categories")
    @classmethod
    def _validate_categories(cls, v: list[str]) -> list[str]:
        unknown = [c for c in v if c not in VALID_CATEGORIES]
        if unknown:
            raise ValueError(f"Unknown categories: {unknown}")
        return v
