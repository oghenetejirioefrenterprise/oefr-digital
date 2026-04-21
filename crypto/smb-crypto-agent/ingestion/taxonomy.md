# Controlled Vocabulary — Ingestion Taxonomy

Subagents MUST use these category tags. Do not invent new tags. If a transcript fits no tag, use `other` and explain in `skip_reason`.

## Setup categories (tradeable)

- `breaking_news` — trade an economic print, data release, or news catalyst at the moment of release
- `trend_day_continuation` — recognize a trend day, hold for higher highs, fade counter-moves
- `pullback_in_uptrend` — buy a controlled retrace in an established uptrend (2nd day continuation, etc.)
- `second_chance_retest` — missed the breakout, take the retest of the breakout level
- `fashionably_late` — join a confirmed, mature trend
- `imbalance_scalp` — small tactical scalp into a price imbalance / gap fill
- `relative_strength` — pick the strongest-in-basket when market moves
- `fade_the_extended` — fade a move that has extended beyond ATR / prior range
- `opening_range_breakout` — break of a defined early-session range
- `liquidity_sweep` — stop hunt / liquidity grab, fade the reversal
- `basket_execution` — execution technique (not a setup itself but adjacent)

## Principle categories (not tradeable setups, but rules to consume)

- `game_planning` — pre-session scenario planning and trade preparation
- `risk_management` — sizing, stops, drawdown discipline
- `trade_review` — post-trade / post-session review discipline
- `trader_development` — career, process, psychology advice (usually low tactical score)

## Equity-only categories (use `equity_only: true`)

- `options_expression` — option-specific expression of a trade
- `earnings_trade` — equity earnings-release plays
- `ipo_lockup` — IPO, lockup, secondary offering plays
- `short_interest` — equity-specific short interest / squeeze plays

## Other

- `other` — use only when no tag above fits; explain in `skip_reason`
