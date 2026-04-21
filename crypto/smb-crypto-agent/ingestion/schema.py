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
    preconditions: str = ""
    entry_trigger: str = ""
    invalidation: str = ""
    targets: str = ""
    timeframe: Literal["scalp", "intraday", "swing"] = "intraday"
    confidence: Literal["high", "med", "low"] = "med"
    crypto_adaptation_notes: str = ""
    quotes: list[str] = Field(default_factory=list)

    @field_validator("quotes", mode="before")
    @classmethod
    def _coerce_quotes(cls, v: object) -> object:
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [x if isinstance(x, str) else str(x) for x in v if x]
        return v

    @field_validator(
        "preconditions",
        "entry_trigger",
        "invalidation",
        "targets",
        "crypto_adaptation_notes",
        mode="before",
    )
    @classmethod
    def _coerce_list_to_string(cls, v: object) -> object:
        if isinstance(v, list):
            return "\n- ".join(str(x) for x in v)
        return v

    @field_validator("timeframe", mode="before")
    @classmethod
    def _coerce_timeframe(cls, v: object) -> object:
        if not isinstance(v, str):
            return v
        lowered = v.strip().lower()
        if lowered in {"scalp", "intraday", "swing"}:
            return lowered
        if "scalp" in lowered:
            return "scalp"
        if "swing" in lowered or "multi-day" in lowered or "multi_day" in lowered:
            return "swing"
        if "intraday" in lowered:
            return "intraday"
        scalp_markers = ("1m", "3m", "5m", "10m", "15m", "1min", "3min", "5min", "10min", "15min", "tick")
        swing_markers = ("daily", "1d", "weekly", "1w", "monthly", "position", "day hold", "1-3 day", "multi day", "days", "day ", "day-to-day", "post-result", "overnight")
        if any(m in lowered for m in scalp_markers):
            return "scalp"
        if any(m in lowered for m in swing_markers):
            return "swing"
        if "minute" in lowered or "min " in lowered or "min," in lowered or "min;" in lowered:
            return "scalp"
        if "hour" in lowered or "1h" in lowered or "2h" in lowered or "4h" in lowered:
            return "intraday"
        return "intraday"

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, v: object) -> object:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            score = float(v)
            if score >= 0.7:
                return "high"
            if score >= 0.4:
                return "med"
            return "low"
        if isinstance(v, str):
            lowered = v.strip().lower()
            if lowered in {"high", "med", "low"}:
                return lowered
            if lowered in {"medium", "mid", "moderate"}:
                return "med"
            if lowered in {"strong", "very high", "very_high"}:
                return "high"
            if lowered in {"weak", "very low", "very_low"}:
                return "low"
        return v


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

    @field_validator("video_id", "title", mode="before")
    @classmethod
    def _coerce_none_to_empty_string(cls, v: object) -> object:
        return "" if v is None else v

    @field_validator("principles", mode="before")
    @classmethod
    def _coerce_principles(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        out: list[str] = []
        for item in v:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("principle") or item.get("lesson")
                if text is None:
                    text = str(item)
                out.append(str(text))
            else:
                out.append(str(item))
        return out

    @field_validator("categories", mode="before")
    @classmethod
    def _coerce_categories(cls, v: object) -> object:
        if not isinstance(v, list):
            return v
        aliases = {
            "psychology": "trader_development",
            "career": "trader_development",
            "mindset": "trader_development",
            "discipline": "trader_development",
            "options": "options_expression",
            "earnings": "earnings_trade",
            "ipo": "ipo_lockup",
            "lockup": "ipo_lockup",
            "short-squeeze": "short_interest",
            "short_squeeze": "short_interest",
            "squeeze": "short_interest",
            "tape-reading": "other",
            "tape_reading": "other",
            "momentum": "trend_day_continuation",
            "scalping": "imbalance_scalp",
            "fade": "fade_the_extended",
            "pullback": "pullback_in_uptrend",
            "retest": "second_chance_retest",
            "breakout": "opening_range_breakout",
            "news": "breaking_news",
            "sweep": "liquidity_sweep",
            "basket": "basket_execution",
            "gameplan": "game_planning",
            "game_plan": "game_planning",
            "review": "trade_review",
        }
        out: list[str] = []
        for c in v:
            if not isinstance(c, str):
                continue
            key = c.strip().lower().replace("-", "_").replace(" ", "_")
            if key in VALID_CATEGORIES:
                out.append(key)
            elif key in aliases:
                out.append(aliases[key])
            # silently drop unknowns
        if not out:
            out.append("other")
        return list(dict.fromkeys(out))  # dedupe, preserve order

    @field_validator("categories")
    @classmethod
    def _validate_categories(cls, v: list[str]) -> list[str]:
        unknown = [c for c in v if c not in VALID_CATEGORIES]
        if unknown:
            raise ValueError(f"Unknown categories: {unknown}")
        return v
