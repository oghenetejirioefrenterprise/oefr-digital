# Stuffed Trade Reversal — Institutional Stop-Hunt and Reverse
**Category:** liquidity_sweep  **Timeframe:** intraday  **Confidence:** high  **Venues:** Hyperliquid, Binance, Bybit
**Adapted from:** How_to_Ride_the_Momentum_from_BIG_Money_Traders_episode_1.transcript.md, How_to_Take_ADVANTAGE_of_a_Short_Squeeze_And_Avoid_Getting_Crushed.transcript.md, The_ONE_Strategy_for_Beginner_Traders_Based_on_20_years_of_Prop_Trading_Experience.transcript.md, Trading_an_unusual_held_bid_on_the_tape_hidden_bidder.transcript.md, Trading_Eli_Lilly.transcript.md, How_To_Catch_Big_Reversal_Trades_Prop_Trading_Technique.transcript.md, Trading_Risk_Management_How_to_Smartly_Increase_Risk_to_Boost_Trading_Profits_PTON.transcript.md, Trade_Review_With_A_Year-3_Proprietary_Trader.transcript.md

## Preconditions
- Institutional-grade asset (BTC, ETH, or high-liquidity perp) with a known structural level: prior day low, round number, prior earnings gap, key VWAP
- Price flushes through the key support level on high volume — the flush itself is the "stuffed" move: selling is aggressive, sloppy, and happens fast (implies stop-hunt or forced liquidation, not deliberate distribution)
- Tape / order book shows sudden absorption: bids step in at or just below the swept level as the aggressive sell orders dry up
- Hidden or iceberg buyer visible: large refreshing bid at the support level absorbs 3+ waves of selling without the level breaking further — each wave hits the bid, the bid refreshes
- For the short-squeeze variant (Rows 20, 34): high short interest or extreme negative funding rate before the flush; "bids don't drop" — every pullback during the squeeze gets re-bid immediately
- Regime check: market not in a sustained trend-down regime; this setup fails in genuine bear trends where the stuffed level is simply distribution

## Entry trigger
**Long entry (classic stuffed trade):**
- Price flushes through support, then absorption is confirmed: bids are holding, aggressive selling volume is declining, tape shows large refreshing buyer
- First entry: when the hidden buyer absorbs 3+ waves and the price ticks up from the bid — enter long on the uptick
- Second entry: on the reclaim of the swept support level — buy when price trades back above the level that was briefly broken
- 9 EMA on 1-minute chart breaks upward (for the short-squeeze continuation variant) — stay long above it

**Short entry (post-absorption exhaustion / absorbed buyer fails):**
- Large buyer that was absorbing all selling finally pulls (lifts from the level) — the absorption exhaustion signal
- Price immediately loses the key level on the next candle with volume
- Short on the break below the level where the buyer was, with stop above the last print where the buyer was active
- Timing: this is often an intraday timing decision — patient observation until the absorbed buyer gives up is required

## Invalidation
**Long:** Absorbed buyer finally lifts and price breaks below the swept level with continued selling volume — the stuffed trade failed; exit and flip bias to short  
**Long:** Price cannot reclaim the swept support within 5 candles — continuation lower is more likely than reversal  
**Short (post-absorption fail):** New institutional buyer steps in at same level; price reclaims the absorbed level with volume  
Stop placement: just below the flush low (long) or just above the last buyer print (short)

## Targets
- T1: VWAP for the session (cover 25–33%) — minimum expectation for any successful stuffed trade
- T2: Undisturbed price — the price level that existed before the catalyst event (prior session close or open before the flush) (cover 25–33%)
- T3: Measured move equal to the size of the flush below support, added to the reclaim level — trail remainder with stop at prior consolidation low
- Short-squeeze continuation (9 EMA variant): stay long while 9 EMA on 1-minute holds; exit on first close below it

## Sizing notes
- Entry in three layers: initial at first absorption confirmation (smallest), second at support reclaim, third on VWAP hold (largest, if the setup is proving out)
- For the "A+ risk request" principle (Row 44): this is the setup that justifies escalating to maximum size — but only with tape confirmation at each layer; do not front-run without confirmation
- Absorbed buyer's position size visible on the tape/order book is a guide to how much supply is being cleared; larger absorber = larger subsequent move
- Time-based sizing: if the absorption is happening in pre-market or low-liquidity hours, reduce size — thinner order books can manufacture false absorption signals

## Crypto adaptation notes
The stuffed trade is uniquely well-suited to crypto perpetual markets because:

1. **Liquidation cascades are the mechanism.** In equities, "weak hands" are retail stop-loss orders. In crypto perps, the forced sellers are overleveraged longs being liquidated — the liquidation engine is deterministic and visible in open interest data. When open interest drops sharply during the flush and then stabilizes, forced selling has exhausted itself.

2. **Funding rate as the stuffed-trade confirmation.** During the flush, funding spikes negatively as shorts flood in. When funding begins to normalize back toward zero while price holds above the swept level, that is the "absorbed buyer" signal in funding-rate form — the aggressive momentum shorts are losing their edge.

3. **Order book iceberg detection.** On Hyperliquid, large refreshing buy orders at key levels (iceberg orders) are directly observable. An order that absorbs 500 BTC of selling and refreshes three times is a stronger signal than any chart pattern.

4. **Undisturbed price as extended target.** The "undisturbed price before the catalyst" concept from SMB's stuffed trade maps perfectly to crypto. If BTC was at $95,000 before a liquidation cascade drove it to $91,000, and the stuffed trade triggers at $91,500, the extended target is $95,000 — the pre-catalyst equilibrium.

5. **ICT community framing:** This is the "breaker block" or "order block" entry in ICT terms — institutional buyers clearing sell-side liquidity at a key level to establish long positions. The SMB "stuffed trade" and the ICT "smart money reversal" are the same trade described in different vocabularies.

## Common mistakes (from review transcripts)
- Entering at the flush low before absorption is confirmed — being the first buyer into an ongoing liquidation cascade means absorbing further downside; wait for the tape signal
- Confusing a slow grinding decline with a stuffed trade — the stuffed trade requires a fast, sloppy flush (urgency), not a methodical selling program
- Targeting VWAP only and not holding for the undisturbed price / measured move target — the highest-reward part of the setup is the extended T3 which most traders exit too early
- Not recognizing when the absorbed buyer has given up — this is the flip signal to short; missing it turns a properly observed setup into a loss
- Trading the stuffed trade against a confirmed trend-day-down regime — this is a reversal setup and requires mean-reversion conditions, not trend continuation conditions
- Sizing the entire position at once at the flush low — the layered entry approach is critical because the exact flush low is rarely identifiable in real time

## Example(s)
**BTC liquidation cascade stuffed trade (illustrative):** BTC at $82,000 key level. Liquidation cascade prints to $80,500 on 3x normal volume in 2 minutes. Open interest drops 8%. Funding spikes to -0.05%. Large refreshing buy wall appears at $80,600 on Hyperliquid order book, absorbs 3 waves of selling. Enter long at $80,650 (layer 1). Funding normalizes to -0.01%. Price reclaims $82,000 (layer 2 add). VWAP at $82,500 covered (T1, 33%). Target $83,800 undisturbed pre-cascade level (T2, 33%). Measured move target $84,000 (T3, trail).

**Hidden refreshing bidder long (source Row 38/40):** Stock/token selling hard into key support. Large bid at the level absorbs 3+ waves without breaking. Enter long on the uptick after 3rd absorption. T1 = VWAP, T2 = prior day high, runner trailing 5-min higher lows.

**Post-squeeze reversal short (source Row 20):** Token in short squeeze (9 EMA long running). 3-5 large green candles. Bids present but price no longer advancing. Consolidation forms near high. Bid suddenly drops. Short on first offer hit that does not recover. T1 = VWAP, T2 = 50% retrace of squeeze move.
