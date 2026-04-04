"""
strategies/smb_scorer.py — SMB Capital 7-Checks-in-Favor Scoring System

Computes a 0-10 score from quantitative checks on SPX price/volume data.
Score drives strategy selection when ACTIVE_STRATEGY=SMB:
  7-10 → LONG_CALL (strong breakout, buy gamma)
  5-6  → CALL_SPREAD (moderate setup, defined risk)
  3-4  → BWB/CONDOR (sell premium in ranging market)
  0-2  → flat (stay out)

Checks requiring visual/news data (narrative, blue sky, clean tape) use
env-override or neutral 0.5 default.
"""

import logging
import os
import statistics
from datetime import datetime, timedelta
from typing import Optional

from ib_insync import util

from broker import IBKRBroker

log = logging.getLogger("strategy.smb_scorer")

# Regime thresholds
BREAKOUT_MIN  = 7
MODERATE_MIN  = 5
RANGE_MIN     = 3


class SMBScorer:
    """
    Scores the current SPX setup on the SMB 7-checks-in-favor framework.

    All 7 MUST-HAVE checks are scored 0 or 1 (partial checks get 0.5).
    3 manual-override checks read from env vars (default 0.5 = neutral).
    Score = sum of all 7 → range 0–7, scaled to 0–10 for clarity.
    Internally we use integer 0/1/0.5 per check then scale.
    """

    def __init__(self, broker: IBKRBroker):
        self.broker = broker
        self._last_score: Optional[dict] = None
        self._last_scored_at: Optional[datetime] = None

    # ─── Public API ─────────────────────────────────────────────────────────

    def score(self) -> dict:
        """
        Run all checks and return:
          {
            "score": int (0-10),
            "raw": float (0.0-7.0),
            "checks": {check_name: 0|0.5|1},
            "regime": "BREAKOUT"|"MODERATE"|"RANGE"|"FLAT",
            "timestamp": str
          }
        """
        try:
            result = self._compute_score()
        except Exception as e:
            log.warning(f"SMB scoring failed: {e} — returning neutral score")
            result = self._neutral_score(reason=str(e))

        self._last_score = result
        self._last_scored_at = datetime.now()
        log.info(
            f"SMB Score: {result['score']}/10 | Regime: {result['regime']} | "
            + " ".join(f"{k}={v}" for k, v in result["checks"].items())
        )
        return result

    def get_regime(self) -> str:
        if self._last_score:
            return self._last_score["regime"]
        return self.score()["regime"]

    def last(self) -> Optional[dict]:
        return self._last_score

    def needs_rescore(self, interval_secs: int) -> bool:
        if self._last_scored_at is None:
            return True
        return (datetime.now() - self._last_scored_at).total_seconds() >= interval_secs

    # ─── Core computation ────────────────────────────────────────────────────

    def _compute_score(self) -> dict:
        price = self.broker.get_underlying_price()
        if price is None or price != price or price <= 0:
            raise ValueError(f"Invalid underlying price: {price}")

        # Fetch 30-day daily bars for historical context
        bars_30d = self._get_daily_bars(days=30)
        # Fetch 5-day 5-minute bars for intraday context
        bars_intraday = self._get_intraday_bars(days=5)

        checks = {}

        # ── Check 1: Pink Line (price near multi-day breakout level) ──────
        checks["pink_line"] = self._check_pink_line(price, bars_30d)

        # ── Check 2: Higher Timeframe Squeeze (BB compression) ────────────
        checks["hf_squeeze"] = self._check_squeeze(bars_30d)

        # ── Check 3: Blue Sky (no overhead resistance) ────────────────────
        # Can partially compute from price range; also supports env override
        checks["blue_sky"] = self._check_blue_sky(price, bars_30d)

        # ── Check 4: Narrative ────────────────────────────────────────────
        # Cannot compute from price — read env override, default 0.5
        checks["narrative"] = float(os.getenv("SMB_NARRATIVE_SCORE", "0.5"))
        checks["narrative"] = max(0.0, min(1.0, checks["narrative"]))

        # ── Check 5: Volume Moment ────────────────────────────────────────
        checks["volume_moment"] = self._check_volume(bars_30d)

        # ── Check 6: Clean Tape ───────────────────────────────────────────
        checks["clean_tape"] = self._check_clean_tape(price, bars_intraday)

        # ── Check 7: Hidden Relative Strength ─────────────────────────────
        checks["hidden_rs"] = self._check_relative_strength(bars_30d)

        # Score = sum of 7 checks (max 7.0), scaled to 10
        raw = sum(checks.values())
        score_10 = round(raw / 7.0 * 10)
        score_10 = max(0, min(10, score_10))

        regime = self._regime(score_10)

        return {
            "score": score_10,
            "raw": raw,
            "checks": checks,
            "regime": regime,
            "timestamp": datetime.now().isoformat(),
        }

    # ─── Individual Checks ───────────────────────────────────────────────────

    def _check_pink_line(self, price: float, bars: list) -> float:
        """
        Check 1 — Pink Line: price is near or at a significant multi-day high.
        Proxy: is current price within 0.3% of the 20-day high?
        Scoring:
          1.0 = within 0.3% of 20d high (at the breakout level)
          0.5 = within 1.0% of 20d high (approaching)
          0.0 = more than 1% below 20d high
        """
        if not bars:
            return 0.5
        try:
            highs = [b.high for b in bars[-20:] if b.high == b.high]
            if not highs:
                return 0.5
            high_20d = max(highs)
            pct_from_high = (high_20d - price) / high_20d
            if pct_from_high <= 0.003:
                return 1.0
            elif pct_from_high <= 0.010:
                return 0.5
            else:
                return 0.0
        except Exception as e:
            log.debug(f"pink_line check error: {e}")
            return 0.5

    def _check_squeeze(self, bars: list) -> float:
        """
        Check 2 — Higher Timeframe Squeeze: Bollinger Band width compressed.
        BB width = (upper - lower) / middle
        Squeeze = current BB width < 50th percentile of 30-day BB widths
        """
        if len(bars) < 20:
            return 0.5
        try:
            closes = [b.close for b in bars if b.close == b.close]
            if len(closes) < 20:
                return 0.5

            def bb_width(window):
                mean = statistics.mean(window)
                std = statistics.stdev(window)
                return (2 * std) / mean if mean else 0

            # Rolling BB widths over the available history
            widths = []
            for i in range(19, len(closes)):
                widths.append(bb_width(closes[i-19:i+1]))

            if len(widths) < 2:
                return 0.5

            current_width = widths[-1]
            median_width = statistics.median(widths)

            # Squeeze = current BB width is below median (compressed)
            if current_width < median_width * 0.8:
                return 1.0  # strong squeeze
            elif current_width < median_width:
                return 0.5  # moderate compression
            else:
                return 0.0  # expanding / no squeeze
        except Exception as e:
            log.debug(f"squeeze check error: {e}")
            return 0.5

    def _check_blue_sky(self, price: float, bars: list) -> float:
        """
        Check 3 — Blue Sky: no significant overhead resistance.
        Proxy: if price is within 0.5% of the all-time 30d high, overhead
        resistance is absent (we're already at the top).
        If price is significantly below recent swing highs, resistance overhead.

        Also supports env override: SMB_BLUE_SKY_SCORE (0 or 1)
        """
        env_val = os.getenv("SMB_BLUE_SKY_SCORE")
        if env_val is not None:
            try:
                return float(env_val)
            except ValueError:
                pass

        if not bars:
            return 0.5
        try:
            highs = [b.high for b in bars if b.high == b.high]
            if not highs:
                return 0.5
            max_high = max(highs)
            pct_below_high = (max_high - price) / max_high

            if pct_below_high <= 0.005:
                return 1.0  # at or near all-time-range high = blue sky
            elif pct_below_high <= 0.015:
                return 0.5
            else:
                return 0.0  # well below recent high = overhead resistance
        except Exception as e:
            log.debug(f"blue_sky check error: {e}")
            return 0.5

    def _check_volume(self, bars: list) -> float:
        """
        Check 5 — Volume Moment: outlier volume at/near current price level.
        Most recent bar volume vs 20-day average. 2+ std devs = 1.0.
        """
        if len(bars) < 5:
            return 0.5
        try:
            volumes = [b.volume for b in bars if b.volume and b.volume == b.volume]
            if len(volumes) < 5:
                return 0.5

            mean_vol = statistics.mean(volumes[:-1])  # exclude today
            std_vol = statistics.stdev(volumes[:-1]) if len(volumes) > 2 else mean_vol * 0.5
            today_vol = volumes[-1]

            if std_vol == 0:
                return 0.5

            z_score = (today_vol - mean_vol) / std_vol

            if z_score >= 2.0:
                return 1.0  # 2+ std devs = outlier volume = confirmed
            elif z_score >= 1.0:
                return 0.5  # above average but not outlier
            else:
                return 0.0  # below average volume = weak signal
        except Exception as e:
            log.debug(f"volume check error: {e}")
            return 0.5

    def _check_clean_tape(self, price: float, bars: list) -> float:
        """
        Check 6 — Clean Tape: orderly price action (low intraday volatility).
        Proxy: today's range / close < median of prior 5 days' ranges.
        Tight range = clean tape. Wide wicky range = messy.
        """
        if not bars:
            return 0.5
        try:
            ranges = []
            for b in bars:
                if b.high == b.high and b.low == b.low and b.close and b.close > 0:
                    ranges.append((b.high - b.low) / b.close)

            if len(ranges) < 2:
                return 0.5

            median_range = statistics.median(ranges[:-1])
            today_range = ranges[-1] if ranges else 0

            if today_range <= median_range * 0.7:
                return 1.0  # tight tape
            elif today_range <= median_range:
                return 0.5
            else:
                return 0.0  # wider than normal = messy tape
        except Exception as e:
            log.debug(f"clean_tape check error: {e}")
            return 0.5

    def _check_relative_strength(self, bars: list) -> float:
        """
        Check 7 — Hidden Relative Strength: price holds/ticks up on dips.
        Proxy: compare the last 5 closes. Is the trend direction positive
        even though the overall market (SPX IS the market here)?
        Better proxy: is today's close above the 5-day EMA (holding strength)?
        Also: did price make a higher low vs 3 days ago?
        """
        if len(bars) < 5:
            return 0.5
        try:
            closes = [b.close for b in bars[-5:] if b.close == b.close]
            if len(closes) < 5:
                return 0.5

            # Simple 5-period EMA
            k = 2 / (5 + 1)
            ema = closes[0]
            for c in closes[1:]:
                ema = c * k + ema * (1 - k)

            today_close = closes[-1]
            three_days_ago_low = min(b.low for b in bars[-3:] if b.low == b.low)
            five_days_ago_low = min(b.low for b in bars[-5:-3] if b.low == b.low)

            above_ema = today_close > ema
            higher_low = three_days_ago_low > five_days_ago_low * 0.999

            if above_ema and higher_low:
                return 1.0
            elif above_ema or higher_low:
                return 0.5
            else:
                return 0.0
        except Exception as e:
            log.debug(f"relative_strength check error: {e}")
            return 0.5

    # ─── Data helpers ────────────────────────────────────────────────────────

    def _get_daily_bars(self, days: int = 30) -> list:
        """Fetch daily OHLCV bars for SPX."""
        try:
            import config
            from ib_insync import Stock, Index
            contract = self.broker._get_underlying_contract()
            end = ""
            bars = self.broker.ib.reqHistoricalData(
                contract,
                endDateTime=end,
                durationStr=f"{days} D",
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )
            return bars if bars else []
        except Exception as e:
            log.warning(f"Failed to fetch daily bars: {e}")
            return []

    def _get_intraday_bars(self, days: int = 5) -> list:
        """Fetch 5-minute intraday bars."""
        try:
            contract = self.broker._get_underlying_contract()
            bars = self.broker.ib.reqHistoricalData(
                contract,
                endDateTime="",
                durationStr=f"{days} D",
                barSizeSetting="5 mins",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )
            return bars if bars else []
        except Exception as e:
            log.warning(f"Failed to fetch intraday bars: {e}")
            return []

    # ─── Utilities ───────────────────────────────────────────────────────────

    def _regime(self, score: int) -> str:
        if score >= BREAKOUT_MIN:
            return "BREAKOUT"
        elif score >= MODERATE_MIN:
            return "MODERATE"
        elif score >= RANGE_MIN:
            return "RANGE"
        else:
            return "FLAT"

    def _neutral_score(self, reason: str = "") -> dict:
        checks = {
            "pink_line": 0.0,
            "hf_squeeze": 0.0,
            "blue_sky": 0.0,
            "narrative": 0.5,
            "volume_moment": 0.0,
            "clean_tape": 0.5,
            "hidden_rs": 0.0,
        }
        return {
            "score": 2,
            "raw": 1.0,
            "checks": checks,
            "regime": "FLAT",
            "timestamp": datetime.now().isoformat(),
            "error": reason,
        }
