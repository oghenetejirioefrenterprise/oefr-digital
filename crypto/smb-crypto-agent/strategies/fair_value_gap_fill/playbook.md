# Fair Value Gap Fill
**Category:** imbalance_scalp  **Timeframe:** scalp  **Confidence:** high  **Venues:** Hyperliquid, Binance
**Adapted from:** Master_Supply_Demand_trading_Ultimate_in-depth_guide_-_2024.transcript.md, Easy_Money_Trades_Must-Know_Setups_for_New_Traders_Advanced_Short_Strategy.transcript.md, Top_10_Gap_Trading_Mistakes_You_Must_Avoid_And_how_to_make_them_big_winners.transcript.md, How_to_Combine_RSI_Bollinger_Bands_ATR_to_Catch_Reversals_High_Probability_Trading.transcript.md, How_to_profit_from_oversold_stocks_reading_the_tape.transcript.md, How_to_use_Tape_Reading_to_make_a_professional_trade.transcript.md, Price_Action_Trading_Like_an_Elite_Prop_Trader_4_Killer_Setups.transcript.md, The_Emotional_Overextension_Bounce_Traded_Profitably.transcript.md, How_to_Time_Exact_Entries_Exits_Bar-By-Bar_Analysis.transcript.md, Prop_Trader_Details_a_Stock_Trade_You_Can_Make_Right_on_the_Open.transcript.md, trade_review_vvus.transcript.md, Trading_BOX.transcript.md, The_Change_of_Character_Trading_Strategy.transcript.md

## Preconditions
- A fair value gap (FVG) exists on the chart: a 3-candle structure where candle 3's range does not overlap with candle 1's range, leaving an unfilled price zone. In ICT terminology: bullish FVG = candle 1 high < candle 3 low (gap below current price); bearish FVG = candle 1 low > candle 3 high (gap above current price)
- The FVG was created by an impulsive move (elevated volume, strong momentum candle) — not a low-volume drift
- Price is returning to fill the FVG from the other side after the impulse
- Higher-timeframe structure favors the fill direction (e.g., bullish FVG fill only when HTF is in uptrend or at HTF support)
- No significant new catalyst has invalidated the imbalance since it was created

## Entry trigger

### Sub-type A — Bullish FVG Fill (price returns to fill gap below)
1. Price impulse creates bullish FVG on 1m/3m/5m/15m chart
2. Price pulls back into the FVG zone (gap between candle 1 high and candle 3 low)
3. Watch for first sign of buyer absorption within the FVG: tape bids stepping up, CVD bottoming, volume spike that fails to close below candle 1 high
4. Enter long at the midpoint or upper boundary of the FVG; stop below the FVG (below candle 1 high)
5. In aggressive entries: enter as price enters the top 50% of the FVG on first test

### Sub-type B — Bearish FVG Fill (price returns to fill gap above)
1. Price impulse creates bearish FVG on chart
2. Price rallies back into the FVG zone (gap between candle 1 low and candle 3 high)
3. Watch for offer absorption failure: tape slows, bids stall, CVD tops, spread widens
4. Enter short at the midpoint or lower boundary of the FVG; stop above the FVG
5. Combine with VWAP being below the FVG for additional confluence (price extended above fair value)

### Sub-type C — Gap Give-and-Go (session-open gap fill with continuation)
1. Asset gaps at session open (crypto: large session-to-session gap, or post-news move)
2. Initial impulse direction meets resistance/support; price "gives back" toward gap open level
3. Buyer/seller absorption visible at gap open level (tape confirmation, large bid/ask holds)
4. Enter in direction of original gap once give-back shows absorption; stop beyond gap level
5. Target: VWAP reclaim (50% of gap), then continuation to gap destination

## Invalidation
- Price closes below the FVG entirely on a volume bar (gap becomes resistance, not support)
- A new impulsive candle in the opposite direction forms within the FVG (new imbalance created)
- HTF structure breaks: e.g., daily closes below the prior swing low for a bullish FVG fill
- Gap give-and-go: price fills the gap fully (closes the entire gap) and continues through — the give-back became a trend reversal

## Targets
- **T1:** Opposite edge of the FVG zone (gap filled) — take 40–50% off; this is the minimum target
- **T2:** Next FVG in the same direction; or VWAP if entering from below — take 25–30%
- **T3:** Prior swing high/low or measured move from the FVG width — trail 20–25% with 1-min structure

## Sizing notes
- FVG setups on 1m/3m charts: smaller size due to noise; only enter full size on 5m+ FVGs with clear impulsive origin
- Require tape confirmation before full size — a blind limit into the FVG midpoint without tape signal is a feeler entry (50% of normal size), not conviction entry
- Gap give-and-go at session opens: slightly larger size allowed due to liquidity concentration at the open — but reduce if first 5-min candle is a massive range candle (risk of whipsaw)

## Crypto adaptation notes
- FVG is native to crypto ICT (Inner Circle Trader) methodology and is extensively used by crypto traders — this is one of the most direct translations from the SMB corpus to crypto
- On Hyperliquid perps: FVGs appear most clearly on 5m, 15m, and 1h charts; the 1m/3m FVGs are often noise unless they formed on extreme volume
- Crypto-specific FVG use: FVGs created during liquidation cascades are especially high-probability fill targets because the impulse was forced (liquidations) rather than informed selling — the underlying supply/demand imbalance is weak
- Session boundaries matter in crypto: the FVG created at the Asia/Europe handoff or at CME futures open is the most "institutional" and thus the most reliably filled
- CVD (cumulative volume delta) is critical for FVG entries in crypto — if CVD does not diverge (i.e., selling pressure remains as price enters bullish FVG), skip the entry
- Funding rate context: entering a bullish FVG fill when funding is deeply negative (longs being paid, market oversold) = A+ setup; entering when funding is highly positive = C grade

## Common mistakes (from review transcripts)
- **Entering the FVG without tape confirmation:** the price level of the gap is the where; the tape (order book absorption) is the when — without tape confirmation, entries into FVGs have poor timing and wide effective stops
- **Not accounting for HTF structure:** a bullish FVG fill on the 1m chart inside a daily downtrend is a low-probability fade — check at least one higher timeframe before entry
- **Filling "too much":** expecting the gap to fill to the penny rather than trading from the first absorption signal within the zone; the FVG midpoint entry is statistically better than waiting for full-depth test
- **Trading FVGs in strong trend days:** on trend days, FVGs in the trend direction get blown through rather than filled — restrict FVG fills to counter-trend entries (or continuation in low-volatility regimes)
- **Holding through a new impulse candle:** if a large momentum candle forms within the FVG against your direction, the gap structure is broken — exit immediately regardless of paper loss

## Example(s)

### Example 1 — Bullish FVG Fill on BTC 15m (Hyperliquid perp)
- Context: BTC breaks out from $62k with a large 15m impulse candle; candle 1 high = $62,200, candle 3 low = $63,500; FVG = $62,200–$63,500 zone
- After the impulse, price consolidates at $65k; begins pulling back
- Price enters the FVG at $63,500; CVD stops falling; bid stacking appears at $63,200 (FVG midpoint)
- Entry: long at $63,200, stop at $62,100 (below FVG bottom)
- T1: $63,500 (top of FVG) — 50% off
- T2: $65,000 (prior HOD) — 25% off
- T3: trail remainder on 15m higher lows

### Example 2 — Gap Give-and-Go on ETH after news catalyst
- Context: ETH gaps up 4% at NY session open on protocol upgrade news; gap open = $3,400
- Initial move to $3,550; then "give" pullback to $3,420 (near gap open)
- Tape: large bid visible at $3,400; CVD holds; spread tightens
- Entry: long at $3,420, stop at $3,380 (below gap open)
- T1: $3,500 (VWAP) — 50% off
- T2: $3,550 (prior HOD) — 30% off
- T3: trail remainder with 5m higher lows
