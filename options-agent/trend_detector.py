"""
trend_detector.py — Trend Day Detection using SMB Capital's 3-Technique Framework.
Combines market internals (TICK, A/D, volume ratio), ETF sector rotation
(offense vs defense), and price action (VWAP, opening range) to produce
a trend day probability score and recommended action.
Data comes from broker.py; this module only does math and classification.
"""

import logging
import statistics
from typing import Optional

import config

log = logging.getLogger("trend_detector")


class TrendDayDetector:
    """Detect trend days using SMB Capital's 3-technique framework.

    Combines market internals, ETF sector rotation, and price action
    to produce a trend day probability score and recommended action.
    """

    def __init__(self, broker):
        self.broker = broker
        self.cumulative_tick = 0.0
        self.tick_readings = []
        self.opening_range = {'high': None, 'low': None, 'set': False}
        self.internals_history = []
        self._last_internals = {}
        self._last_rotation = {}

    # ─── Daily Reset ─────────────────────────────────────────────────────

    def reset_daily(self):
        """Reset all daily state at the start of each trading day."""
        self.cumulative_tick = 0.0
        self.tick_readings = []
        self.opening_range = {'high': None, 'low': None, 'set': False}
        self.internals_history = []
        self._last_internals = {}
        self._last_rotation = {}
        log.info("TrendDayDetector: daily state reset")

    # ─── Market Internals ────────────────────────────────────────────────

    def get_market_internals(self) -> dict:
        """Fetch current market internals from IBKR and classify.

        Returns dict with:
        - vol_ratio: float (up volume / down volume)
        - advance_decline: float (advancing - declining stocks)
        - tick: float (current TICK reading)
        - cumulative_tick: float (running sum of TICK)
        - vol_ratio_signal: str
        - ad_signal: str
        - tick_trend: str
        - internals_signal: str ('extreme_bullish'|'extreme_bearish'|'bullish'|'bearish'|'neutral')
        """
        raw = self.broker.get_market_internals()
        if not raw:
            log.warning("TrendDayDetector: no market internals data available")
            return {}

        tick = raw.get('tick', 0)
        add = raw.get('add', 0)
        uvol = raw.get('uvol', 0)
        dvol = raw.get('dvol', 0)

        # Volume ratio
        vol_ratio = uvol / dvol if dvol > 0 else (10.0 if uvol > 0 else 1.0)

        # Update cumulative tick
        self.update_cumulative_tick(tick)

        # Classify each component
        vol_ratio_signal = self.classify_vol_ratio(vol_ratio)
        ad_signal = self.classify_advance_decline(add)
        tick_trend = self.get_cumulative_tick_trend()

        # Composite internals signal
        internals_signal = self._composite_internals_signal(vol_ratio_signal, ad_signal, tick_trend)

        result = {
            'vol_ratio': round(vol_ratio, 2),
            'advance_decline': add,
            'tick': tick,
            'cumulative_tick': round(self.cumulative_tick, 1),
            'vol_ratio_signal': vol_ratio_signal,
            'ad_signal': ad_signal,
            'tick_trend': tick_trend,
            'internals_signal': internals_signal,
        }
        self._last_internals = result
        self.internals_history.append(result)
        return result

    def _composite_internals_signal(self, vol_signal: str, ad_signal: str, tick_trend: str) -> str:
        """Determine composite internals direction from individual signals."""
        bullish_signals = 0
        bearish_signals = 0

        for signal in [vol_signal, ad_signal]:
            if 'bullish' in signal:
                bullish_signals += 1
            elif 'bearish' in signal:
                bearish_signals += 1

        if tick_trend == 'up_trend':
            bullish_signals += 1
        elif tick_trend == 'down_trend':
            bearish_signals += 1

        if bullish_signals >= 3:
            if 'extreme' in vol_signal or 'extreme' in ad_signal:
                return 'extreme_bullish'
            return 'bullish'
        elif bearish_signals >= 3:
            if 'extreme' in vol_signal or 'extreme' in ad_signal:
                return 'extreme_bearish'
            return 'bearish'
        elif bullish_signals >= 2:
            return 'bullish'
        elif bearish_signals >= 2:
            return 'bearish'
        return 'neutral'

    def classify_vol_ratio(self, ratio: float) -> str:
        """Classify volume ratio.

        Returns:
        - 'extreme_bullish': ratio > 4.0
        - 'bullish': ratio > 2.0
        - 'neutral': 0.5 <= ratio <= 2.0
        - 'bearish': ratio < 0.5
        - 'extreme_bearish': ratio < 0.25
        """
        cfg = config.TREND_DAY
        if ratio > cfg.vol_ratio_extreme:
            return 'extreme_bullish'
        elif ratio > 2.0:
            return 'bullish'
        elif ratio < 1.0 / cfg.vol_ratio_extreme:
            return 'extreme_bearish'
        elif ratio < 0.5:
            return 'bearish'
        return 'neutral'

    def classify_advance_decline(self, ad_value: float) -> str:
        """Classify advance/decline reading.

        Returns:
        - 'extreme_bullish': ad > 2000
        - 'bullish': ad > 1000
        - 'neutral': -1000 <= ad <= 1000
        - 'bearish': ad < -1000
        - 'extreme_bearish': ad < -2000
        """
        cfg = config.TREND_DAY
        if ad_value > cfg.ad_extreme:
            return 'extreme_bullish'
        elif ad_value > 1000:
            return 'bullish'
        elif ad_value < -cfg.ad_extreme:
            return 'extreme_bearish'
        elif ad_value < -1000:
            return 'bearish'
        return 'neutral'

    def update_cumulative_tick(self, tick: float) -> float:
        """Add tick reading to cumulative total. Return cumulative value."""
        self.cumulative_tick += tick
        self.tick_readings.append(tick)
        return self.cumulative_tick

    def get_cumulative_tick_trend(self) -> str:
        """Analyze cumulative tick history for trend.

        Uses simple higher-highs/higher-lows check on rolling cumulative sums.

        Returns:
        - 'up_trend': cumulative tick making higher highs/lows
        - 'down_trend': cumulative tick making lower highs/lows
        - 'neutral': no clear trend
        """
        if len(self.tick_readings) < 5:
            return 'neutral'

        # Build cumulative tick series
        cum_series = []
        running = 0.0
        for t in self.tick_readings:
            running += t
            cum_series.append(running)

        # Check last N readings for trend using simple slope
        window = min(len(cum_series), 20)
        recent = cum_series[-window:]

        if len(recent) < 5:
            return 'neutral'

        # Simple linear regression slope (y = mx + b, we only need m)
        n = len(recent)
        x_mean = (n - 1) / 2.0
        y_mean = statistics.mean(recent)
        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 'neutral'

        slope = numerator / denominator

        # Normalize slope by the range of values to determine significance
        y_range = max(recent) - min(recent)
        if y_range == 0:
            return 'neutral'

        # Significant trend if slope is meaningful relative to data range
        normalized_slope = slope * n / y_range if y_range > 0 else 0

        cfg = config.TREND_DAY
        # Also check if cumulative tick is extreme
        if self.cumulative_tick > cfg.tick_extreme * 5 and normalized_slope > 0.3:
            return 'up_trend'
        elif self.cumulative_tick < -cfg.tick_extreme * 5 and normalized_slope < -0.3:
            return 'down_trend'
        elif normalized_slope > 0.5:
            return 'up_trend'
        elif normalized_slope < -0.5:
            return 'down_trend'

        return 'neutral'

    # ─── ETF Sector Rotation ─────────────────────────────────────────────

    def get_sector_rotation(self) -> dict:
        """Compare offensive vs defensive ETF performance from open.

        Returns dict with:
        - offense_avg_change: float (avg % change from open)
        - defense_avg_change: float (avg % change from open)
        - spread: float (offense - defense)
        - leader: str ('offense'|'defense'|'neutral')
        - signal: str ('risk_on'|'risk_off'|'neutral')
        - details: dict (per-ETF breakdown)
        """
        cfg = config.TREND_DAY
        all_symbols = cfg.etf_offense + cfg.etf_defense

        etf_data = self.broker.get_etf_prices(all_symbols)
        if not etf_data:
            log.warning("TrendDayDetector: no ETF data available")
            return {
                'offense_avg_change': 0.0, 'defense_avg_change': 0.0,
                'spread': 0.0, 'leader': 'neutral', 'signal': 'neutral',
                'details': {},
            }

        # Calculate average % change for each group
        offense_changes = []
        defense_changes = []

        for sym in cfg.etf_offense:
            data = etf_data.get(sym)
            if data and data.get('change_pct') is not None:
                offense_changes.append(data['change_pct'])

        for sym in cfg.etf_defense:
            data = etf_data.get(sym)
            if data and data.get('change_pct') is not None:
                defense_changes.append(data['change_pct'])

        offense_avg = statistics.mean(offense_changes) if offense_changes else 0.0
        defense_avg = statistics.mean(defense_changes) if defense_changes else 0.0
        spread = offense_avg - defense_avg

        if spread > cfg.etf_spread_threshold:
            leader = 'offense'
            signal = 'risk_on'
        elif spread < -cfg.etf_spread_threshold:
            leader = 'defense'
            signal = 'risk_off'
        else:
            leader = 'neutral'
            signal = 'neutral'

        result = {
            'offense_avg_change': round(offense_avg, 3),
            'defense_avg_change': round(defense_avg, 3),
            'spread': round(spread, 3),
            'leader': leader,
            'signal': signal,
            'details': etf_data,
        }
        self._last_rotation = result
        return result

    # ─── Opening Range ───────────────────────────────────────────────────

    def set_opening_range(self, high: float, low: float):
        """Set the opening range (first 30 minutes high/low).
        Called once after 10:00 AM with the 9:30-10:00 price range."""
        self.opening_range = {'high': high, 'low': low, 'set': True}
        log.info(f"Opening range set: high={high:.2f} low={low:.2f} (range={high-low:.2f})")

    def check_opening_range_break(self, current_price: float) -> str:
        """Check if price has broken the opening range.

        Returns:
        - 'break_up': price > opening range high
        - 'break_down': price < opening range low
        - 'inside': price within range
        - 'not_set': opening range not yet established
        """
        if not self.opening_range['set']:
            return 'not_set'
        if current_price > self.opening_range['high']:
            return 'break_up'
        elif current_price < self.opening_range['low']:
            return 'break_down'
        return 'inside'

    # ─── Trend Day Scoring ───────────────────────────────────────────────

    def calculate_trend_score(self) -> dict:
        """Calculate composite trend day probability score.

        Combines all three techniques:
        1. Market internals (vol ratio + A/D + tick): 0-40 points
        2. ETF sector rotation (offense/defense): 0-30 points
        3. Price action (VWAP position + opening range + trend structure): 0-30 points

        Returns dict with:
        - score: int (0-100)
        - direction: str ('bullish'|'bearish'|'neutral')
        - confidence: str ('high'|'medium'|'low'|'none')
        - is_trend_day: bool (score >= threshold)
        - components: dict (breakdown of each technique's contribution)
        - recommended_action: str
        """
        cfg = config.TREND_DAY
        internals = self._last_internals
        rotation = self._last_rotation

        # ── 1. Internals Score (0-40) ──
        internals_score, internals_direction = self._score_internals(internals)

        # ── 2. ETF Score (0-30) ──
        etf_score, etf_direction = self._score_etf(rotation, internals_direction)

        # ── 3. Price Action Score (0-30) ──
        price_score, price_direction = self._score_price_action(internals_direction)

        # ── Composite ──
        total_score = internals_score + etf_score + price_score

        # Determine overall direction
        directions = [internals_direction, etf_direction, price_direction]
        bullish_count = sum(1 for d in directions if d == 'bullish')
        bearish_count = sum(1 for d in directions if d == 'bearish')

        if bullish_count > bearish_count:
            direction = 'bullish'
        elif bearish_count > bullish_count:
            direction = 'bearish'
        else:
            direction = 'neutral'

        # Confidence level
        if total_score >= cfg.high_conviction_threshold:
            confidence = 'high'
        elif total_score >= cfg.trend_day_threshold:
            confidence = 'medium'
        elif total_score >= cfg.reduce_size_threshold:
            confidence = 'low'
        else:
            confidence = 'none'

        is_trend_day = total_score >= cfg.trend_day_threshold
        recommended_action = self.get_recommended_action(total_score, direction)

        return {
            'score': total_score,
            'direction': direction,
            'confidence': confidence,
            'is_trend_day': is_trend_day,
            'components': {
                'internals_score': internals_score,
                'etf_score': etf_score,
                'price_action_score': price_score,
                'internals_direction': internals_direction,
                'etf_direction': etf_direction,
                'price_direction': price_direction,
            },
            'recommended_action': recommended_action,
        }

    def _score_internals(self, internals: dict) -> tuple:
        """Score market internals (0-40 points). Returns (score, direction)."""
        if not internals:
            return 0, 'neutral'

        cfg = config.TREND_DAY
        vol_signal = internals.get('vol_ratio_signal', 'neutral')
        ad_signal = internals.get('ad_signal', 'neutral')
        tick_trend = internals.get('tick_trend', 'neutral')
        vol_ratio = internals.get('vol_ratio', 1.0)
        ad_value = internals.get('advance_decline', 0)

        # Vol ratio score (0-15)
        vol_score = 0
        if abs(vol_ratio - 1.0) > 0:
            effective_ratio = vol_ratio if vol_ratio > 1.0 else 1.0 / vol_ratio
            if effective_ratio > cfg.vol_ratio_extreme:
                vol_score = 15
            elif effective_ratio > 2.5:
                vol_score = 10
            elif effective_ratio > 1.5:
                vol_score = 5

        # A/D score (0-15)
        ad_score = 0
        abs_ad = abs(ad_value)
        if abs_ad > cfg.ad_extreme:
            ad_score = 15
        elif abs_ad > 1500:
            ad_score = 10
        elif abs_ad > 1000:
            ad_score = 5

        # Cumulative TICK score (0-10)
        tick_score = 0
        if tick_trend == 'up_trend' or tick_trend == 'down_trend':
            tick_score = 10
        elif len(self.tick_readings) >= 3:
            # Partial trend: check if most readings are in same direction
            positive = sum(1 for t in self.tick_readings[-10:] if t > 0)
            negative = sum(1 for t in self.tick_readings[-10:] if t < 0)
            total = positive + negative
            if total > 0 and max(positive, negative) / total > 0.7:
                tick_score = 5
            elif total > 0 and max(positive, negative) / total > 0.5:
                tick_score = 2

        total = vol_score + ad_score + tick_score

        # Direction agreement check — all must align for full points
        bullish_count = sum(1 for s in [vol_signal, ad_signal]
                           if 'bullish' in s) + (1 if tick_trend == 'up_trend' else 0)
        bearish_count = sum(1 for s in [vol_signal, ad_signal]
                           if 'bearish' in s) + (1 if tick_trend == 'down_trend' else 0)

        if bullish_count >= 2:
            direction = 'bullish'
        elif bearish_count >= 2:
            direction = 'bearish'
        else:
            direction = 'neutral'
            # Mixed signals — cap at 15
            total = min(total, 15)

        return total, direction

    def _score_etf(self, rotation: dict, internals_direction: str) -> tuple:
        """Score ETF sector rotation (0-30 points). Returns (score, direction)."""
        if not rotation:
            return 0, 'neutral'

        spread = rotation.get('spread', 0.0)
        leader = rotation.get('leader', 'neutral')

        etf_score = 0
        abs_spread = abs(spread)

        if leader == 'offense':
            # Offense leading = bullish signal
            if abs_spread > 1.0:
                etf_score = 30
            elif abs_spread > 0.5:
                etf_score = 20
            elif abs_spread > 0.2:
                etf_score = 10
            etf_direction = 'bullish'
        elif leader == 'defense':
            # Defense leading = bearish trend day possible
            etf_score = 5
            etf_direction = 'bearish'
        else:
            etf_score = 0
            etf_direction = 'neutral'

        # Direction must match internals for full points
        if etf_direction != 'neutral' and internals_direction != 'neutral':
            if etf_direction != internals_direction:
                etf_score = min(etf_score, 10)

        return etf_score, etf_direction

    def _score_price_action(self, internals_direction: str) -> tuple:
        """Score price action signals (0-30 points). Returns (score, direction)."""
        price_score = 0
        direction = 'neutral'

        # Get current price for VWAP and opening range checks
        try:
            current_price = self.broker.get_underlying_price()
        except Exception:
            return 0, 'neutral'

        # 1. VWAP position (0-10 points)
        # Check if agent has VWAP data cached
        vwap_data = None
        agent = getattr(self.broker, '_agent_ref', None)
        if agent and hasattr(agent, 'current_vwap_data'):
            vwap_data = agent.current_vwap_data

        if vwap_data:
            price_vs_vwap = vwap_data.get('price_vs_vwap', 'at')
            if price_vs_vwap == 'above':
                price_score += 10
                direction = 'bullish'
            elif price_vs_vwap == 'below':
                price_score += 10
                direction = 'bearish'

        # 2. Opening range break (0-10 points)
        or_break = self.check_opening_range_break(current_price)
        if or_break == 'break_up':
            price_score += 10
            if direction == 'neutral':
                direction = 'bullish'
        elif or_break == 'break_down':
            price_score += 10
            if direction == 'neutral':
                direction = 'bearish'

        # 3. Trend structure via internals history (0-5 points)
        if len(self.internals_history) >= 3:
            # Check if internals have been consistently directional
            recent_signals = [h.get('internals_signal', 'neutral')
                              for h in self.internals_history[-5:]]
            bullish = sum(1 for s in recent_signals if 'bullish' in s)
            bearish = sum(1 for s in recent_signals if 'bearish' in s)
            if bullish >= 3 or bearish >= 3:
                price_score += 5

        # 4. Range expansion proxy (0-5 points)
        if self.opening_range['set']:
            or_range = self.opening_range['high'] - self.opening_range['low']
            if or_range > 0:
                current_range = abs(current_price - (self.opening_range['high'] + self.opening_range['low']) / 2)
                if current_range > or_range * 2:
                    price_score += 5

        # Direction must match internals
        if direction != 'neutral' and internals_direction != 'neutral':
            if direction != internals_direction:
                price_score = min(price_score, 10)

        return price_score, direction

    def get_recommended_action(self, score: int, direction: str) -> str:
        """Map trend score to agent action.

        Returns:
        - 'buy_convexity': score >= 80 (high conviction)
        - 'block_premium_selling': score >= 65 (trend day)
        - 'reduce_premium_selling': 50 <= score < 65 (elevated risk)
        - 'normal': 30 <= score < 50 (no trend signal)
        - 'favorable_for_premium': score < 30 (low trend risk)
        """
        cfg = config.TREND_DAY
        if score >= cfg.high_conviction_threshold and cfg.enable_convexity_buying:
            return 'buy_convexity'
        elif score >= cfg.trend_day_threshold:
            return 'block_premium_selling'
        elif score >= cfg.reduce_size_threshold:
            return 'reduce_premium_selling'
        elif score >= 30:
            return 'normal'
        return 'favorable_for_premium'
