# Fade ATR Extension
**Category:** fade_the_extended  **Timeframe:** scalp  **Confidence:** high  **Venues:** Hyperliquid, Binance
**Adapted from:** 5_Trading_Lessons_from_Facebook.transcript.md, 6_Career-Making_Lessons_from_the_Gold_Silver_Surge.transcript.md, How_to_Combine_RSI_Bollinger_Bands_ATR_to_Catch_Reversals_High_Probability_Trading.transcript.md, How_to_use_RSI_Indicator_for_Better_Entries.transcript.md, The_4_Keys_to_Mean_Reversion_Trades.transcript.md, Two_Variables_that_lead_to_an_A_trade.transcript.md, Every_Trader_Needs_to_Know_This.transcript.md, How_To_Short_An_Overbought_Market.transcript.md, The_Mean_Reversion_Trade_4_things_you_must_do.transcript.md, This_Trading_Indicator_is_Incredible_Detects_snapbacks_AND_major_moves.transcript.md, Finding_Edge_in_VXX.transcript.md

## Preconditions
**Multi-indicator overextension gate — ALL must align for A+ trade:**
1. RSI >90 on daily chart (use 20-period custom RSI for responsiveness; standard 14-period >80 acceptable)
2. RSI >80 simultaneously on hourly AND 15-min AND 30-min charts (multi-timeframe RSI confirmation)
3. Price closing outside the upper Bollinger Band (2 standard deviations) on the daily chart
4. Price 5+ ATRs above the 5-day low (measured from the lowest close of the last 5 days)
5. Multiple gap-up days (2+) in the past week without a close below the prior day's low
6. No fresh fundamental catalyst on the most recent ATR extension — pure momentum/continuation

**On Day 2 of extension (ATR extension fade specific):**
- Asset has already moved 1 full ATR from the open on Day 2 following a strong Day 1 directional move
- Day 2 continues in the same direction as Day 1 without meaningful pullback

**Intraday criteria (entry gate):**
- Opening high printed early (first 30-45 minutes), lower highs forming on 5-min
- Price holding below intraday VWAP (for short setups) or above VWAP (for long bounces)
- Volume contracting on the most recent push to the extension extreme

## Entry trigger
**Multi-timeframe RSI short:**
Short the break of the first 15-min candle that closes below the prior 15-min candle (first sign of momentum failure). Conservative: short on first close below prior 15-min bar. Add on lower high: stop above lower high on 1-min, add when lower high confirmed with tape showing offers flooding.

**ATR extension Day 2 short:**
Short at 1.0-1.5 ATR above the Day 2 open when reversal candles appear (lower high, increasing offer volume, bids not absorbing). Stop above the 1.5 ATR extension level.

**Multi-indicator fade (all 5 criteria met):**
Any of these intraday triggers qualifies as entry: (1) intraday VWAP failure after opening push, (2) opening range breakdown on first red day close, (3) first 15-min lower high after the extension.

**Keltner Channel cross-check:** If price is at 1.5+ ATRs above the 30-bar linear regression (slow mean), and the 2-4 bar momentum trigger rolls down — that combination is the systematic fade signal.

## Invalidation
- Price makes new closing high above the overextension level on elevated volume (momentum continuation, not exhaustion)
- RSI fails to turn down after first 15-min lower bar — RSI staying >80 with price acceleration = trend continuation
- Fresh fundamental catalyst arrives justifying the extension (buy the news = no fade)
- Price closes above 1.5 ATR on Day 2 with volume expansion (sellers absent)

## Targets
- T1: Close the most recent gap (return to the gap-up open of the final extension day) — cover 50%
- T2: Prior week's VWAP or 5-day average price — cover 25%
- T3: 20-period moving average on daily — trail remainder using 15-min candle closes
- Extended target: 2-standard-deviation lower Bollinger Band (full mean reversion)
- Exit rule for multi-timeframe RSI: hold while 15-min candles don't close above prior bar high; exit on first close above

## Sizing notes
- This setup has more variance than backside shorts; reduce position size 25-30% relative to standard risk
- Full size only when ALL 5 multi-indicator criteria are met simultaneously
- Scale: 25% at first sign (VWAP failure), 50% on 15-min lower high confirmation, 25% on continuation below Day 2 open
- ATR-based stop: stop must be placed beyond the extension extreme — no wiggle room (no tight stops that get chopped out)

## Crypto adaptation notes
- Crypto RSI extremes are more pronounced and frequent: BTC/ETH can sustain RSI >90 for 2-3 days before exhaustion. Tighter time-based filter required: require multi-timeframe RSI (4H + 1H + 15-min all >80) before entering.
- Funding rate >0.1% per 8h is the crypto-specific ATR extension confirmation signal — it indicates over-levered longs that are vulnerable to flush on any reversal
- DVOL (Deribit volatility index) serves as the crypto IV analog: if DVOL is also extended, fade timing often clusters at weekly options expiry (Thursday/Friday equivalent in crypto = Friday UTC)
- ATR works directly on crypto perpetuals — use 14-period ATR on the relevant timeframe (1h for scalp, daily for swing) to measure extension and set targets
- The 5-period daily ATR from the 5-day low translates directly: on Hyperliquid, use the 5-period ATR of the daily chart to measure extension
- Basis compression (spot vs perp basis compressing) is a crypto-specific fade signal: when perps trade at tight or negative basis after an extension, smart money has already distributed

## Common mistakes (from review transcripts)
- Using a single RSI timeframe — require multi-timeframe confirmation (daily + 130-min or 4H + 30-min) to eliminate false extremes
- Fading too early before the extension criteria are all met — partial criteria = much lower probability
- Taking profits too slowly on Day 2 extension fades (these are scalp-oriented; don't hold for multi-day on Day 2 ATR fade)
- Ignoring the "no new fundamental catalyst" filter — always verify the extension is momentum-driven, not catalyst-driven
- Trying to short at the exact ATR extension high without waiting for the 15-min lower bar — enter on the first momentum failure signal, not at the price level

## Example(s)
**Facebook post-catalyst ATR extension (Day 2):** Day 1 massive catalyst move; Day 2 extended 1 ATR from open without pullback; short at 1.0 ATR above Day 2 open on reversal candle; target return to Day 2 open; covered at 1 ATR pullback.

**Gold/GLD overextension intraday:** Volume >150% above average; price >5 ATRs in <5 days; outside upper Bollinger Band; identified 5-min support level; support broke with volume = short entry; covered into sharp moves down where volume increased.

**BTC/altcoin RSI >90 multi-timeframe (generalized):** BTC RSI 92 on daily; 4H RSI 88; 1H RSI 85; funding rate 0.12%/8h; no fresh news on that day; first 15-min candle closes below prior bar = short entry; T1 at gap close, T2 at 20-period daily MA.
