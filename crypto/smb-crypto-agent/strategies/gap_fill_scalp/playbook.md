# Gap Fill Scalp
**Category:** imbalance_scalp  **Timeframe:** scalp  **Confidence:** high  **Venues:** Hyperliquid, Binance
**Adapted from:** Top_10_Gap_Trading_Mistakes_You_Must_Avoid_And_how_to_make_them_big_winners.transcript.md, Easy_Money_Trades_Must-Know_Setups_for_New_Traders_Advanced_Short_Strategy.transcript.md, Master_Supply_Demand_trading_Ultimate_in-depth_guide_-_2024.transcript.md, How_to_profit_from_oversold_stocks_reading_the_tape.transcript.md, The_Emotional_Overextension_Bounce_Traded_Profitably.transcript.md, 4_Steps_to_Start_Day_Trading_Like_a_Money_Making_Machine.transcript.md, How_to_Use_Tape_Reading_to_Make_Quick_Profitable_Trades_for_Scalping.transcript.md, Day_in_the_Life_of_Rising_Star_Prop_Trader.transcript.md, Do_this_one_thing_to_increase_your_trading_profits.transcript.md, trade_review_vvus.transcript.md, How_to_Combine_RSI_Bollinger_Bands_ATR_to_Catch_Reversals_High_Probability_Trading.transcript.md, The_Market_Just_CrashedHeres_EXACTLY_How_Im_Trading_It_Highest_Probability_Setups.transcript.md, Trades_We_Make_When_Volatility_Spikes.transcript.md

## Preconditions
- A price gap exists from a prior session close: specifically, the current session opened materially above or below the prior session's close, leaving an unfilled price range on the chart
- Gap types handled by this playbook:
  - **Exhaustion gap-up:** price gapped up on news; gap has not been tested; setup is for fade (short into fill)
  - **Failed flush gap-down fill:** price gapped down, sold to support, bids absorbed at support; setup is for reversal long back to fill the gap
  - **Continuation gap-down fill:** multi-day selling creates large below-close gap; capitulation volume at support creates the fill opportunity
- The prior close (gap boundary) is clearly visible on the chart and unmarked (no intraday candle has wicked through it)
- Broader market not in freefall (for gap-fill longs) or not in parabolic squeeze (for gap-fill shorts)

## Entry trigger

### Sub-type A — Failed Flush Gap-Fill Long (gap-down fill from below)
1. Asset gaps down significantly at session open; initial selling creates the flush
2. Volume climax at support level (largest red candle of the session); sellers exhausted
3. Tape shows change: bids stepping up, offers lifting, CVD stops declining
4. Enter long on VWAP reclaim OR on tape change signal, whichever comes first; stop below the flush low
5. Target: prior session close (the gap fill level); optionally VWAP as intermediate target

### Sub-type B — Exhaustion Gap-Up Short (gap-up fill from above)
1. Asset gaps up on catalyst; initial buying drives price further; gap is undefended
2. Tape/volume signals exhaustion at extension: volume contraction at new high, CVD divergence, offer refreshing
3. Enter short on first red candle that closes below the VWAP or below the session open; stop above the session high
4. Target: prior session close (gap fill); take partials at VWAP and continuation to close

### Sub-type C — Capitulation Gap-Down after Multi-Day Decline
1. Asset has declined 3+ consecutive sessions; each day's range exceeds the prior day's
2. Day 3+ opens with a gap-down; creates panic candle at session open; intraday volume spike (largest in 3+ days) marks the low
3. Higher low forms relative to the panic candle low on 5-min chart; VWAP reclaimed
4. Enter long when higher low confirmed; stop below the panic candle low
5. Target: prior day close (gap fill), then VWAP of prior session

## Invalidation
- **Long invalids (failed flush fill):** price makes new low below the flush low after tape change signal; sellers reload with volume; VWAP lost on first reclaim attempt
- **Short invalids (gap-up fill):** price holds above VWAP after gap-up and creates a new high — the gap-and-go setup takes over; abandon gap-fill short
- **Capitulation invalids:** higher low fails; price prints a lower low after entry; volume does not spike at the panic candle (capitulation not confirmed)

## Targets
- **T1:** VWAP — take 40–50% off; VWAP is fair value and represents the natural equilibrium target for gap fills
- **T2:** Prior session close (the gap fill) — take 25–30% off; this is the canonical target of the setup
- **T3:** Prior session high (for gap-up shorts from above) or continuation above the gap fill (for longs) — trail 15–25% on 5-min structure

## Sizing notes
- Gap-fill setups have defined risk (stop at flush low or session high): use risk-based sizing — size so that stop = predefined dollar risk
- Capitulation gap-down fills: start with 25–30% of normal size on the initial nibble (tape uncertainty is higher), add to 100% after higher low confirmed on 5-min with VWAP reclaim
- Exhaustion gap-up shorts: use 50% initial, add on first failed VWAP reclaim; max out at full size if price prints lower high with CVD divergence

## Crypto adaptation notes
- Crypto gaps are common at session boundaries: Asia close → NY open creates the most tradeable gaps because institutional participation changes sharply
- CME Bitcoin futures gaps (formed between Friday 16:00 CT close and Sunday 17:00 CT open) have a well-documented high fill rate (historical fill rate approximately 85% within 5 sessions); track these gaps as persistent targets
- On Hyperliquid perps, "gap" is defined relative to the prior session's 00:00 UTC open/close; mark these on the chart before the NY session
- Liquidation-cascade gap-downs on crypto are the highest-probability capitulation fill setups: the impulse was forced (margin calls), the fundamental supply/demand picture did not change, and the gap will fill as rational participants re-establish positions
- Funding rate at gap fill: if funding is deeply negative at the gap-down low (longs paid), the capitulation is more complete and the fill probability is higher
- Open interest: if OI drops sharply during the gap-down (longs liquidated), the flush is genuine capitulation; if OI rises (new shorts added), the move may continue — check OI before entering gap-fill longs
- CVD divergence on 5-min chart: if price makes new low but CVD does not (fewer actual sell-side transactions), the absorption is real — this is the most reliable crypto-specific signal for capitulation

## Common mistakes (from review transcripts)
- **Entering before tape change:** price level of the prior close is the target, not the entry; entering a long into a falling knife because "the gap will fill" without tape confirmation is the most common gap-fill error
- **Chasing the fill:** once the gap is 80%+ filled, the setup is done; entering near the gap fill target hoping for continuation is a different (and lower-quality) trade
- **Ignoring the gap type:** a gap-up on a strong fundamental catalyst (ETF approval, major protocol upgrade) is more likely to hold and gap-and-go rather than fill; distinguish fundamental gaps from emotional/mechanical ones
- **Forgetting the stop:** the stop for gap-fill longs is the flush low (not the prior close); many traders misplace the stop at the gap target, giving no room for the trade to work
- **Not taking T1 at VWAP:** the setup's job is to fill the gap; if it gets to VWAP and stalls, take partial profits rather than waiting for the full gap fill which may not happen that session

## Example(s)

### Example 1 — Failed Flush Gap-Fill Long on BTC (Hyperliquid perp)
- Prior session close: BTC $64,500; opens next session at $62,000 (gap down $2,500 on macro fear)
- First 15 min: BTC flushes to $61,200; volume on that candle = 4x prior average (capitulation spike)
- Tape: bids begin stepping up at $61,200; CVD stops falling; spread tightens
- Entry: long $61,500 (on higher low formation); stop $60,900 (below flush low)
- T1: $62,800 (VWAP of current session) — 40% off
- T2: $64,500 (prior session close = gap fill) — 30% off
- T3: trail remainder on 5-min higher lows

### Example 2 — Exhaustion Gap-Up Short on BTC (Hyperliquid perp)
- Prior session close: BTC $63,000; opens next session at $65,500 on positive ETF news (gap up $2,500)
- First 30 min: BTC runs to $66,200; volume contraction at the high; CVD diverges (price new high, CVD lower)
- VWAP sits at $65,300; price fails to hold $66,000 after third attempt
- Entry: short at $65,800 on first close below $66,000; stop at $66,400 (above session high)
- T1: $65,300 (VWAP) — 40% off
- T2: $63,000 (prior session close = gap fill) — 30% off
- T3: trail remainder with 5-min lower high stops

### Example 3 — CME Gap Fill on BTC (Weekly)
- Friday CME close: $62,000; Sunday CME reopen: $60,500 (CME gap from $60,500 to $62,000)
- Within 3 sessions, BTC rallies toward $62,000 from below
- Monitor for tape absorption and VWAP alignment as price approaches gap fill zone
- Enter long on dip toward $60,500 while gap is open; target $62,000 gap fill; stop below $60,000
