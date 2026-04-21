# VWAP Reversion Scalp
**Category:** imbalance_scalp  **Timeframe:** scalp  **Confidence:** high  **Venues:** Hyperliquid, Binance
**Adapted from:** How_to_Scalp_Like_an_Elite_Prop_Trader_Inside_Look.transcript.md, How_to_Read_the_Tape_on_a_Breakout.transcript.md, How_to_profit_from_oversold_stocks_reading_the_tape.transcript.md, Master_Supply_Demand_trading_Ultimate_in-depth_guide_-_2024.transcript.md, The_4_Keys_to_Mean_Reversion_Trades.transcript.md, Market_Profile_A_SMB_Trader_Reveals_How_to_Use_This_Tool_to_Make_Effective_Trades_in_SPY.transcript.md, How_to_Trade_Oil_Futures.transcript.md, Volume_Profiling_to_Trade_the_Emini_SP_500.transcript.md, Current_Emini_SP_500_Market_Structure.transcript.md, Trading_BOX.transcript.md, Trading_Volatile_Markets_Is_Hard_Until_You_See_This.transcript.md, The_Trading_Pattern_You_Need_to_Know.transcript.md, Savvy_Advice_From_a_Prop_Trader_on_How_You_Can_Improve.transcript.md, Scalping_An_effective_and_highly_profitable_trading_strategy.transcript.md, SMB_Futures_Morning_Trading_Webcast_February_22nd.transcript.md, Find_great_levels_in_the_SP500.transcript.md, Why_You_Are_Not_Consistently_Making_Money_As_A_Trader.transcript.md, Trades_We_Make_When_Volatility_Spikes.transcript.md, Top_3_Strategies_to_Profit_From_the_ATR_Indicator_Prop_Trader_Secrets.transcript.md

## Preconditions
- Session VWAP is calculable and visible (anchored to current session open: 00:00 UTC or NY session 13:00 UTC)
- Asset is trading at least 1.0–2.0x ATR (session ATR) away from VWAP — extension is the prerequisite, not a minor deviation
- No strong fundamental catalyst justifying the extension (pure momentum/emotional move, liquidation cascade, or mechanical squeeze)
- RVOL > 2x session average confirming participation (liquid enough to exit the trade)
- Market regime: ranging or mean-reverting (not a confirmed trend day where price holds one side of VWAP all session)

## Entry trigger

### Sub-type A — Extended Above VWAP: VWAP Fade Short
1. Price has moved 1.5–2.5x session ATR above VWAP without a meaningful consolidation
2. Volume contraction at the extension high (no new buyers stepping in) — CVD flattens or turns
3. Tape confirms: offer refreshing at extension, bids not absorbing, spread widening on up ticks
4. Enter short on first red 1-min candle that closes back below the VWAP extension or on explicit tape change signal (bids fade, offers step down)
5. Stop: above the session high (extension extreme)

### Sub-type B — Extended Below VWAP: VWAP Bounce Long
1. Price has moved 1.5–2.5x session ATR below VWAP — often driven by a liquidation cascade or macro flush
2. Volume crescendo at the extension low: largest volume bar of the session, price fails to close materially below prior low
3. Tape: change of character — bids stepping up, offers lifting, CVD bottoms and turns up
4. Enter long on VWAP reclaim (price returns above VWAP on 1-min with volume) or on tape change at extension low; stop below the session low
5. Partial entry at the extension low (50% size) with add on VWAP reclaim (50%)

### Sub-type C — VWAP Battle (Intraday Range): Short from Above / Long from Below
1. Price oscillating within 1 ATR of VWAP in a ranging session
2. Persistent offer refreshing above VWAP (or bid absorption below VWAP) creates directional bias
3. Short: enter when price approaches offer wall above VWAP, tape confirms (bids thin, offer holds); stop above the offer wall
4. Long: enter when price approaches bid support below VWAP, tape confirms (bids step up, offer lifts); stop below the bid support
5. Target: opposite VWAP boundary (1 ATR from VWAP in reversal direction)

### Sub-type D — VWAP Continuation Scalp (Pullback in Trending Session)
1. On confirmed trend day, price trades on one side of VWAP for 2+ hours
2. Minor pullback brings price back to VWAP on reduced volume (not aggressive selling through VWAP)
3. Tape shows buyers absorbing at VWAP; bids hold; offers lift
4. Enter long on tape confirmation of VWAP hold; stop below the VWAP wick low
5. Target: prior session high or 1 ATR continuation above VWAP

## Invalidation
- **Sub-type A short:** VWAP reclaimed with volume and held for 2+ candles (the extension was a breakout, not overextension); new session high printed
- **Sub-type B long:** session low violated on a new volume candle after tape change signal; sellers reload rather than covering
- **Sub-type C range:** price accepts outside the 1-ATR VWAP range for 3+ candles on volume — trend day developing; stop fading and join the trend
- **Sub-type D continuation:** VWAP lost on volume (sellers through VWAP); trend character changes to mixed or reversal

## Targets
- **T1:** VWAP (for extensions: primary reversion target) — take 40–50% off
- **T2:** Prior swing level on the VWAP-proximate side, or value area boundary (VPOC, VAH/VAL) — take 25–30%
- **T3:** Full range reversion target or measured move from extension; trail 15–25% with 5-min structure

## Sizing notes
- Scaling rule: enter 50% at extension extreme (tape change signal) + add 50% on VWAP retest (when VWAP reclaim confirms direction)
- In weak market regime: take profits at 50–70% of the expected VWAP reversion move; conditions deteriorate quickly
- ATR-based stop sizing: size position so stop (at session extreme) = 0.5% of account at risk; never exceed this on a single VWAP reversion entry
- RVOL < 2x: reduce size by 50%; illiquid sessions create fakeouts and wide spreads on VWAP approaches

## Crypto adaptation notes
- VWAP is one of the most universally used tools by crypto professional traders and is natively supported on Hyperliquid's charting interface
- Anchor VWAP to: (a) current session open (00:00 UTC daily), (b) NY open (13:00 UTC), or (c) major swing low/high for multi-session VWAPs — use 24h VWAP as the default reference
- Liquidation cascades create the most reliable extension-below-VWAP setups in crypto: when a cascade pushes price 2x+ ATR below VWAP with a volume spike (the largest candle of the session), the setup is A+ grade — the move was forced, not informed
- Funding rate at VWAP: deeply negative funding at extension below VWAP = additional confirmation for long reversion (shorts are paying a significant rate, incentivizing closure); highly positive funding at extension above VWAP = additional confirmation for short reversion
- CVD at extension: look for CVD divergence — price new session low but CVD less negative than prior low means absorption is occurring; this is the highest-quality entry signal for sub-type B
- VPOC (volume point of control) and VWAP often converge by mid-session on ranging days; VPOC below VWAP = price will revert to VPOC first, VWAP second; use this as intermediate target calibration
- Session timing matters: VWAP reversion setups have the highest win rate during NY session (13:00–20:00 UTC) and lowest during Asia session (00:00–07:00 UTC) due to liquidity

## Common mistakes (from review transcripts)
- **Fading trend days:** the most common VWAP reversion error — buying below VWAP on a day when price has been below VWAP all session (trend day down); restrict reversion longs to days where price has been above VWAP for at least 2 hours
- **Lazy scaling:** adding to a losing VWAP reversion position without tape confirmation is the opposite of the correct process; add AFTER tape change is confirmed, not before
- **No RVOL check:** low-volume sessions make VWAP extensions meaningless (thin markets move from friction, not order flow); always confirm RVOL > 2x before entering
- **Holding through VWAP retest failure:** if price reaches VWAP and then fails to hold above (for longs) or below (for shorts) — exit immediately; the reversion is over or the structure has changed
- **Not taking T1 at VWAP:** taking 40–50% off at VWAP ensures profitability even if the trade does not continue to T2/T3; traders who hold through VWAP "for more" often give back all profits on the snap-back

## Example(s)

### Example 1 — Sub-type B: Liquidation Flush Below VWAP Long on BTC (Hyperliquid)
- Session: BTC opens at $65,000; VWAP anchors at session open
- Mid-session: liquidation cascade drops BTC from $65,000 to $62,500 (2.5x ATR below VWAP); VWAP sits at $64,500
- Volume on cascade candle: 5x session average (crescendo)
- CVD: price new session low, but CVD is less negative than the prior intraday low (divergence)
- Funding rate: deeply negative (-0.08% per 8h) — shorts paying longs
- Tape: large bids appearing at $62,500; offers lifting; CVD turns up
- Entry: 50% at $62,700 (tape change signal); add 50% on VWAP reclaim at $63,800
- T1: $64,500 (VWAP) — 40% off first tranche
- T2: $65,200 (prior session high) — 25% off
- T3: trail remainder with 5-min higher lows

### Example 2 — Sub-type A: Extension Above VWAP Short on ETH (Hyperliquid)
- Session: ETH VWAP at $3,300; price runs to $3,480 (1.8x ATR above VWAP) on positive funding news
- Volume at $3,480: contracting; CVD flat on the 3rd push to HOD
- Tape: large offer refreshing at $3,470; bids thin; spread widening
- Entry: short at $3,460 on first red 1-min candle; stop at $3,510 (above HOD)
- T1: $3,380 (midpoint to VWAP) — 40% off
- T2: $3,300 (VWAP) — 30% off
- T3: trail remainder on 5-min lower high stops

### Example 3 — Sub-type D: VWAP Continuation Scalp on BTC Trend Day (Hyperliquid)
- BTC in clear uptrend: held above VWAP since session open, funding positive but not extreme
- Midday pullback: BTC returns to $64,000 VWAP on 1/3 of morning volume (no aggressive selling)
- Tape: bids hold at VWAP; large bid visible at $63,900; offers lifting
- Entry: long at $64,050 on tape confirmation; stop at $63,700 (below VWAP wick)
- T1: $64,800 (prior HOD) — 50% off
- T2: trail remainder with 5-min 20 EMA
