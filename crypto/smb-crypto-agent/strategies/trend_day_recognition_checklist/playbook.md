# Trend Day Recognition Checklist
**Category:** trend_day_continuation  **Timeframe:** intraday  **Confidence:** high  **Venues:** HL perps, Binance futures

**Adapted from:** 10_Steps_to_Trading_Trend_Days_How_to_CRUSH_It.transcript.md, How_to_Nail_The_Market_Environment_Nearly_Every_Day.transcript.md, The_Ultimate_Trend_Day_Trading_Course_For_Beginners_Developing_Traders.transcript.md, How_to_use_ADD_and_TICK_to_make_winning_trades_in_SPY_part_1.transcript.md, How_to_use_ADD_and_TICK_to_make_winning_trades_in_SPY_part_2.transcript.md, Top_3_Technical_Analysis_Indicators_For_0DTE_Options.transcript.md, How_to_PROFIT_from_market_crashes_Survive_Thrive.transcript.md, Time_To_Get_Lucky.transcript.md, See_A_Potential_Trend_Day_BEFORE_The_Open.transcript.md, Trading_Signals_You_Can_Spot_Right_On_The_Open_To_Catch_Huge_Stock_Market_Trades.transcript.md, 10_Key_Strategies_to_Trade_an_Economic_News_Release.transcript.md, Conviction_and_Vision_for_Better_Trading.transcript.md, november1stflv.transcript.md

## Preconditions

Equity framework (translated to crypto analogs):
- **VOLD ratio analog:** Compute (up-volume across top 100 crypto tokens by market cap) / (down-volume across top 100). Ratio >3:1 bullish or <0.33:1 bearish within first 30 minutes signals trend day.
- **ADD analog:** Count number of top-100 tokens making net gains vs net losses on the session. Pinned at +60 or higher (bullish) / -60 or lower (bearish) = internals aligned for trend day.
- **TICK analog:** Aggregated BTC perpetual cumulative delta trending in one direction persistently (not oscillating). On bull trend days: positive CVD all session with minimal pullbacks. On bear trend days: CVD trending negative.
- **Sector/offense-defense rotation:** Offense sectors (L1 gas fees rising, DeFi TVL growing, perp OI expanding) outperforming on bullish trend days. Defensive signals (USDT dominance spiking, funding going negative) confirm bearish trend days.
- **Macro catalyst present:** CPI print, FOMC decision, major geopolitical event, or large technical breakout from multi-week range creates the necessary directional energy.
- Pre-market overnight session has broken above/below a key balance zone and is holding the break. BTC futures holding above overnight balance high = bullish setup.

## Entry trigger

**All 3 internals must align in the same direction within the first 30 minutes:**
1. Volume ratio (up-volume/down-volume top-100) at extreme
2. Breadth count (coins up vs coins down) pinned at extreme
3. CVD on BTC perpetual trending in one direction

When all 3 confirm: bias the entire session to that direction. Enter on the first Opening Range Break (first 5-minute ORB) in the trend direction. Add on each VWAP pullback that holds (see trend_day_add_into_strength.md).

**Pre-market checklist (run before session open):**
- Did overnight session break a key balance zone and hold?
- Is BTC holding above/below overnight balance?
- Is there a macro catalyst driving the move?
- Are sector leaders showing relative strength/weakness vs BTC?

## Invalidation

- VOLD/breadth ratio reverts toward neutral (1:1) — internals no longer aligned
- CVD reverses sharply against the trending direction after being persistent
- Price fails to hold the Opening Range Break for 2+ bars
- TICK/CVD character changes from trending to oscillating
- ADD divergence: price makes new high but breadth count does not follow

## Targets

- **Hold-all-day discipline:** Confirmed trend day means trade-to-hold, not scalp. Close at or near the high (bullish) or low (bearish) of day is the expectation.
- First confirmation level: prior day's high (bull) or low (bear)
- Extended target: prior all-time high or major structural support/resistance
- Add points along the way at each VWAP test that holds (see trend_day_add_into_strength.md)

## Sizing notes

- Full size on confirmed trend day entries (all 3 internals aligned, ORB confirmed)
- Do not size up before confirmation — wait for the 30-minute read
- If internals diverge after initial entry, reduce to half size but maintain directional bias until invalidation triggers
- Trend days are the highest conviction environment: use 40-50% of daily stop on the primary trade

## Crypto adaptation notes

**VOLD → Crypto Breadth Ratio:** Pull top-100 tokens from CoinGecko or exchange APIs. Compute (# tokens up >1% on session) / (# tokens down >1% on session). >3:1 or <0.33:1 are the threshold signals.

**ADD → Token Advance-Decline:** Track a fixed basket of 20-50 liquid perp tokens. Count tokens with positive price change vs negative. If >70% positive all session = trend day up; <30% = trend day down.

**TICK → BTC CVD (Cumulative Volume Delta):** Use BTC perpetual CVD on 1-minute chart. Trending CVD (consistently higher highs or lower lows without mean-reversion oscillation) = trend day signal. Available on TradingView via "Cumulative Delta Volume" indicator.

**Funding rate pinned:** On confirmed bull trend days, funding rate on Hyperliquid stays positive or rises. On bear trend days, funding goes negative and stays there. Funding is a lagging confirmation, not a leading signal.

**BTC daily open (00:00 UTC) analog to 9:30 ET open:** The 00:00 UTC reset is the primary session anchor for crypto trend day analysis. The US cash open (9:30-10:00 ET / 13:30-14:00 UTC) is a secondary inflection that often accelerates established trends.

**Pre-market window:** 00:00-09:30 ET (overnight session in crypto terms). Hold above/below the overnight balance zone = trend day setup confirmed.

## Common mistakes (from review transcripts)

- **Fading early:** Trying to call the top/bottom on a trend day destroys P&L. "Do not fade fear momentum on a trend day." (november1stflv)
- **Scalping instead of holding:** Taking profits at 0.5 ATR on a 2 ATR trend day. Trend days require trade-to-hold discipline.
- **Checking out after first win:** "Professionals keep asking what is the next trade on best days." (How_to_improve_your_best_trading_day_ever) — stay engaged all session.
- **Neutral days mistaken for trend days:** Internals oscillating (not trending) = iron-condor day, not trend day. Do not force trend setups on neutral days.
- **Not confirming with all 3 internals:** Price alone is insufficient. A stock making new highs does not confirm a trend day without breadth and volume ratio confirmation.
- **Fighting the trend after 10:30:** After the first 30-60 minutes establish the trend, counter-trend trades have very low probability. Stop trying to pick reversals.

## Example(s)

**BTC Bull Trend Day (macro catalyst):**
- CPI comes in below expectations at 8:30 ET
- Within 15 minutes: BTC CVD trending strongly positive, top-100 breadth at 78/100 tokens up, perp OI expanding
- Funding rate on Hyperliquid rises from 0.003% to 0.008% (positive = longs paying shorts = bullish confirmation)
- Entry: long BTC perp on first 5-min ORB break above overnight high at 09:35 ET
- Add: on first VWAP pullback at 11:00 ET that holds (see trend_day_add_into_strength.md)
- Hold: close at or near day's high; trail with 15-min 20 EMA

**BTC Bear Trend Day (regulatory shock):**
- Major exchange hack or regulatory enforcement announced pre-market
- Breadth: 15/100 tokens positive, CVD making new lows persistently, funding going negative
- Entry: short on ORB break below overnight low
- Add: on each VWAP bounce that fails to hold (see trend_day_counter_move_fade.md)
- Target: prior week's support level
