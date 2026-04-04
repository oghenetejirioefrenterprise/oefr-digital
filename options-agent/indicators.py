"""
indicators.py — Volume Z-Score, VWAP, and volume regime analysis for SPX/SPY.
Central module for all volume-based indicator calculations.
Data comes from broker.py; this module only does math.
"""

import logging
import statistics
from typing import Optional

log = logging.getLogger("indicators")


class VolumeIndicators:
    """Volume Z-Score, VWAP, and volume regime analysis for SPX/SPY."""

    def calculate_vwap(self, bars) -> dict:
        """Calculate VWAP and standard deviation bands from intraday bars.

        Args:
            bars: list of BarData objects from IBKR (must have close, volume, average/wap fields)

        Returns:
            dict with keys: vwap, upper_1sd, lower_1sd, upper_2sd, lower_2sd,
                            price_vs_vwap ('above'|'below'|'at')
        """
        if not bars:
            return {}

        cumulative_tp_vol = 0.0
        cumulative_vol = 0
        tp_list = []

        for bar in bars:
            # Typical price = (high + low + close) / 3
            high = getattr(bar, 'high', 0) or 0
            low = getattr(bar, 'low', 0) or 0
            close = getattr(bar, 'close', 0) or 0
            volume = getattr(bar, 'volume', 0) or 0

            if volume <= 0 or close <= 0:
                continue

            tp = (high + low + close) / 3.0
            cumulative_tp_vol += tp * volume
            cumulative_vol += volume
            tp_list.append(tp)

        if cumulative_vol <= 0 or not tp_list:
            return {}

        vwap = cumulative_tp_vol / cumulative_vol

        # Standard deviation of typical prices around VWAP
        if len(tp_list) >= 2:
            squared_diffs = [(tp - vwap) ** 2 for tp in tp_list]
            variance = sum(squared_diffs) / len(squared_diffs)
            sd = variance ** 0.5
        else:
            sd = 0.0

        current_price = tp_list[-1]

        # Classify price position relative to VWAP
        if sd > 0:
            distance = (current_price - vwap) / sd
            if distance > 0.25:
                price_vs_vwap = "above"
            elif distance < -0.25:
                price_vs_vwap = "below"
            else:
                price_vs_vwap = "at"
        else:
            if current_price > vwap * 1.001:
                price_vs_vwap = "above"
            elif current_price < vwap * 0.999:
                price_vs_vwap = "below"
            else:
                price_vs_vwap = "at"

        return {
            "vwap": round(vwap, 2),
            "upper_1sd": round(vwap + sd, 2),
            "lower_1sd": round(vwap - sd, 2),
            "upper_2sd": round(vwap + 2 * sd, 2),
            "lower_2sd": round(vwap - 2 * sd, 2),
            "sd": round(sd, 2),
            "current_price": round(current_price, 2),
            "price_vs_vwap": price_vs_vwap,
        }

    def calculate_volume_zscore(self, current_volume: float, historical_volumes: list) -> float:
        """Calculate volume z-score.

        Z = (current_volume - mean(historical_volumes)) / std(historical_volumes)
        Return 0.0 if std is 0 or insufficient data.
        """
        if not historical_volumes or len(historical_volumes) < 2:
            return 0.0

        try:
            mean_vol = statistics.mean(historical_volumes)
            std_vol = statistics.stdev(historical_volumes)
        except (statistics.StatisticsError, ValueError):
            return 0.0

        if std_vol == 0:
            return 0.0

        return (current_volume - mean_vol) / std_vol

    def calculate_relative_volume(self, current_volume: float, avg_volume: float) -> float:
        """RVOL = current / average. Return 0.0 if avg is 0."""
        if avg_volume <= 0:
            return 0.0
        return current_volume / avg_volume

    def get_volume_regime(self, zscore: float, price_change_pct: float) -> str:
        """Classify current regime based on volume z-score and price change.

        Returns one of:
        - 'capitulation': z > 1.5 and price_change < -0.5%  (best for selling puts)
        - 'breakout': z > 1.5 and price_change > 0.5%  (caution on call spreads)
        - 'expanding': z > 1.0 and abs(price_change) < 0.5%  (range expansion imminent)
        - 'quiet': z < 0.5  (skip entries — thin market)
        - 'normal': everything else
        """
        if zscore > 1.5 and price_change_pct < -0.5:
            return "capitulation"
        if zscore > 1.5 and price_change_pct > 0.5:
            return "breakout"
        if zscore > 1.0 and abs(price_change_pct) < 0.5:
            return "expanding"
        if zscore < 0.5:
            return "quiet"
        return "normal"

    def get_entry_signal(self, vwap_data: dict, zscore: float, regime: str, strategy_type: str) -> dict:
        """Synthesize all indicators into an entry recommendation.

        Args:
            vwap_data: output from calculate_vwap()
            zscore: volume z-score
            regime: output from get_volume_regime()
            strategy_type: one of 'PCS', 'CCS', 'CONDOR', 'STRADDLE'

        Returns:
            dict with keys:
            - allow_entry: bool
            - confidence: float (0.0-1.0)
            - reason: str
            - sizing_multiplier: float (0.5-1.5, for position sizing adjustment)
        """
        # Default: allow entry, normal confidence
        result = {
            "allow_entry": True,
            "confidence": 0.5,
            "reason": "default",
            "sizing_multiplier": 1.0,
        }

        # If VWAP data unavailable, allow with warning
        if not vwap_data:
            result["reason"] = "VWAP data unavailable — allowing entry"
            return result

        price_vs_vwap = vwap_data.get("price_vs_vwap", "at")
        current_price = vwap_data.get("current_price", 0)
        vwap = vwap_data.get("vwap", 0)
        lower_1sd = vwap_data.get("lower_1sd", 0)

        stype = strategy_type.upper()

        if stype == "PCS":
            # Put credit spread: allow when price >= VWAP AND (capitulation OR normal)
            if regime == "quiet":
                result["allow_entry"] = False
                result["confidence"] = 0.1
                result["reason"] = "Quiet regime — thin market, skip PCS"
                result["sizing_multiplier"] = 0.5
                return result

            if regime == "capitulation" and price_vs_vwap in ("below", "at"):
                # High conviction: capitulation selling with price at/below VWAP
                result["allow_entry"] = True
                result["confidence"] = 0.9
                result["reason"] = f"Capitulation + VWAP support — high conviction PCS (z={zscore:.1f})"
                result["sizing_multiplier"] = 1.5
                return result

            if price_vs_vwap == "above" or regime in ("capitulation", "normal"):
                result["allow_entry"] = True
                result["confidence"] = 0.7 if price_vs_vwap == "above" else 0.5
                result["reason"] = f"Price {price_vs_vwap} VWAP, regime={regime} — PCS OK"
                result["sizing_multiplier"] = 1.0
                return result

            # Price below VWAP in non-capitulation
            result["allow_entry"] = False
            result["confidence"] = 0.3
            result["reason"] = f"Price below VWAP ({current_price:.1f} < {vwap:.1f}), regime={regime} — sellers in control"
            result["sizing_multiplier"] = 1.0
            return result

        elif stype == "CCS":
            # Call credit spread: allow when price <= VWAP AND regime != breakout
            if regime == "breakout":
                result["allow_entry"] = False
                result["confidence"] = 0.2
                result["reason"] = f"Breakout regime — avoid selling calls (z={zscore:.1f})"
                result["sizing_multiplier"] = 1.0
                return result

            if regime == "quiet":
                result["allow_entry"] = False
                result["confidence"] = 0.1
                result["reason"] = "Quiet regime — thin market, skip CCS"
                result["sizing_multiplier"] = 0.5
                return result

            if price_vs_vwap in ("below", "at"):
                result["allow_entry"] = True
                result["confidence"] = 0.7
                result["reason"] = f"Price {price_vs_vwap} VWAP, regime={regime} — CCS OK"
                result["sizing_multiplier"] = 1.0
            else:
                result["allow_entry"] = True
                result["confidence"] = 0.4
                result["reason"] = f"Price above VWAP but regime={regime} — CCS with caution"
                result["sizing_multiplier"] = 0.75
            return result

        elif stype == "CONDOR":
            # Iron condor: allow when price within VWAP +/-1 SD AND regime normal/expanding
            if regime in ("capitulation", "breakout"):
                result["allow_entry"] = False
                result["confidence"] = 0.2
                result["reason"] = f"Regime={regime} — avoid condors in trending markets"
                result["sizing_multiplier"] = 1.0
                return result

            if regime == "quiet":
                result["allow_entry"] = False
                result["confidence"] = 0.1
                result["reason"] = "Quiet regime — thin market, skip condor"
                result["sizing_multiplier"] = 0.5
                return result

            if price_vs_vwap == "at":
                result["allow_entry"] = True
                result["confidence"] = 0.8
                result["reason"] = f"Price at VWAP, regime={regime} — ideal for condor"
                result["sizing_multiplier"] = 1.0
            else:
                result["allow_entry"] = True
                result["confidence"] = 0.5
                result["reason"] = f"Price {price_vs_vwap} VWAP, regime={regime} — condor with caution"
                result["sizing_multiplier"] = 0.75
            return result

        elif stype == "STRADDLE":
            # Gamma plays: allow when regime is volatile
            if regime == "quiet":
                result["allow_entry"] = False
                result["confidence"] = 0.1
                result["reason"] = "Quiet regime — no gamma opportunity"
                result["sizing_multiplier"] = 0.5
                return result

            if regime in ("capitulation", "breakout", "expanding"):
                result["allow_entry"] = True
                result["confidence"] = 0.8
                result["reason"] = f"Regime={regime} — gamma play favorable (z={zscore:.1f})"
                result["sizing_multiplier"] = 1.0
            else:
                result["allow_entry"] = True
                result["confidence"] = 0.4
                result["reason"] = f"Regime={regime} — gamma play marginal"
                result["sizing_multiplier"] = 0.75
            return result

        # Sizing adjustments based on regime (applied on top of strategy-specific logic)
        if regime == "expanding":
            result["sizing_multiplier"] = 0.75

        return result
