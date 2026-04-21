# Pullback at Moving Average

**Category:** pullback_in_uptrend  **Timeframe:** intraday  **Confidence:** high  **Venues:** HL perps, Binance spot, Binance futures

**Adapted from:** AM_Meeting_March_7.transcript.md, AM_Meeting_May_15th.transcript.md, Bar_by_Bar_Analysis_of_5_Simple_Trades.transcript.md, High_Accuracy_Swing_Trading_Setups.transcript.md, High-Probability_Swing_Trades_Swing_Entries_Breakouts_Explained.transcript.md, How_this_trader_can_be_making_better_trades_NVDA_Pull_In_trade_example.transcript.md, Inside_One_of_the_Worlds_Top_Proprietary_Trading_Desks_An_interns_experience.transcript.md, Key_Trade_Setups_for_the_Week_Top_Entry_Exit_Strategies.transcript.md, Mastering_Swing_Setups_Breakouts_Continuations_and_Reversal_Plays.transcript.md, Moving_Average_Trading_Tutorial_For_Day_Trading.transcript.md, Scalping_An_Effective_And_Highly_Profitable_Trading_Strategy_part_II.transcript.md, Scalping_An_effective_and_highly_profitable_trading_strategy.transcript.md, The_Ultimate_Swing_Trading_Guide_For_Beginners_Developing_Traders.transcript.md, The_Weekly_Trade_Plan_Top_Stock_Ideas_In-Depth_Execution_Strategy.transcript.md, What_Moves_Momentum_Stocks_where_to_buy_Tesla.transcript.md, Why_Simple_Strategies_Are_Money_Machines.transcript.md, AM_Meeting_August_11.transcript.md, AM_Meeting_March_9th.transcript.md, AM_Meeting_June_5th.transcript.md

## Preconditions

- Asset in established uptrend: higher highs and higher lows on the reference timeframe
- Target moving average is rising (positively sloped), not flat or declining
- Supported MA levels by priority:
  - Intraday scalp: 9 EMA (1m/2m/5m) — first pullback is the highest-probability entry
  - Intraday swing: 55 EMA (5m), 20 EMA (15m)
  - Swing multi-day: 20-day or 50-day SMA on daily chart
  - Macro swing: 200-day SMA on daily — only in BTC bull cycle (BTC above 200-day itself)
- Volume contracting on the pullback leg (below average vs the prior impulse)
- Sector or market environment supporting the direction (BTC green for longs on alts)
- For 9 EMA scalp: first touch is the highest-quality entry; 3rd+ touch is lower probability

## Entry trigger

**9 EMA scalp (1m/5m):**
1. Trend impulse leg is clear (3+ consecutive candles in one direction)
2. Pullback to 9 EMA; volume contracts
3. First green candle that closes at or above the 9 EMA close — enter at close or on first uptick off EMA
4. Stop: below the low of the pullback candle that touched 9 EMA

**20/50 EMA intraday:**
1. Price tests the rising EMA on a 15m bar; candle closes above the EMA
2. Tape (HL order book) shows bid absorption at the EMA level
3. Enter on reclaim with stop below EMA low

**200-day SMA swing:**
1. Price pulls back to 200-day SMA zone (treat as ±0.5% zone, not a precise line)
2. Volume declining for 3+ days on the pullback
3. 15m bullish reversal candle (hammer, engulfing) at the zone
4. Enter on break of reversal candle high; stop at 200-day zone low

## Invalidation

- Close below the target EMA on 1m/5m with volume expansion
- Break below the pullback low that defined the setup
- Two consecutive 1m closes below the 9 EMA (for scalp)
- Daily close below 200-day SMA with meaningful volume (for macro swing)

## Targets

- 9 EMA scalp: T1 = prior swing high; T2 = measured move (prior leg length above EMA)
- Scale: take 50% at T1, trail remainder using prior bar lows or 9 EMA breaks
- 20/50 EMA intraday: T1 = 1 ATR above entry; T2 = intraday high; trail with 15m higher lows
- 200-day swing: T1 = 50-day SMA or prior swing high; T2 = prior high; trail stop using daily higher lows
- Exit when 9 EMA/VWAP cross confirms trend exhaustion (9 EMA crosses below VWAP)

## Sizing notes

- 9 EMA first-touch: full base size — highest-probability entry; tight stop allows larger position
- 20/50 EMA: standard size; reduce 30% if RVOL below 1.2× average
- 200-day SMA swing: start with 50% position, add when price breaks above consolidation high that forms after the MA touch
- Sector ETF must confirm direction (BTC for alts, ETH for DeFi) before sizing up to full
- Big-mover model filter: if RVOL > 4.7× AND beta > 2.1 AND price moved > 80% of prior day ATR from close, size to 1.5× base on the first 9 EMA pullback

## Crypto adaptation notes

- 9 EMA on 5m is the workhorse for BTC/ETH perps on HL during trend days; institutional buy programs show as rhythmic pulses that respect the 9 EMA
- For alts: use 55 EMA on 5m instead of 9 EMA — more noise on shorter period for small-cap tokens
- 200-day SMA on BTC daily is the macro bull/bear dividing line: only take pullback longs on alts when BTC itself is above its 200-day
- On HL: watch order book for bid stacking at the EMA level, not just price; price can touch and bounce without tape confirmation — tape is the gate
- Anchored VWAP from catalyst date often aligns with the 20-period EMA on 4h — when both coincide, double the conviction and size

## Common mistakes (from review transcripts)

- Entering on the 3rd or 4th touch of the 9 EMA — edge degrades sharply after the first touch; either missed or the trend is ending
- Using a flat or declining EMA as support — a flat EMA is a range indicator, not a trend indicator
- Ignoring volume: pullback to EMA on expanding volume = distribution, not a buying opportunity
- Using the same EMA period across all timeframes — 9 EMA on 1m is not the same context as 9 EMA on daily
- Shorting just because price is extended above the EMA — do not fade the trend; wait for EMA cross or pattern breakdown

## Example(s)

**BTC/USDC perp (HL), 5m chart, 9 EMA scalp:**
- BTC in morning uptrend after positive CPI data; consecutive green 5m candles to 97,500
- Pulls back on low volume over 3 candles to 96,800 (9 EMA at 96,750)
- Candle touches 9 EMA and closes green at 96,900 — enter long at 96,920
- Stop: 96,600 (below pullback low)
- T1: 97,500 (prior swing high) — exit 50%; trail 9 EMA for remainder
- T2: 98,200 (next measured move target)

**ETH/USDC perp (HL), 4h chart, 20 EMA swing:**
- ETH in multi-week uptrend; 20 EMA rising at 3,200
- Pulls back over 5 days to 3,180 (20 EMA zone) on declining volume
- 4h bullish engulfing at 3,200; enter at 3,230; stop at 3,100
- T1: 3,500 (prior swing high); T2: trail using daily higher lows

**BTC swing, 200-day SMA:**
- BTC in bull cycle; 200-day at 82,000
- 3-week pullback to 82,500 on declining volume
- Daily hammer candle at 82,000 zone; enter at 83,500 on next-day open above range
- Stop: 80,500 (below 200-day zone); T1: 93,000; T2: trail prior daily lows
