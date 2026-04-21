# Intraday Correlated Basket — Sympathy, Leader-Lagger, and Sector Rotation
**Category:** basket_execution  **Timeframe:** intraday/scalp  **Confidence:** high  **Venues:** Hyperliquid perps, Binance spot + USDⓈ-M
**Adapted from:** Elite_prop_trader_on_how_he_made_17_times_his_risk_on_one_huge_trade.transcript.md, Level_2_Strategies_Every_Day_Trader_MUST_Know_Taught_by_a_Prop_Trader.transcript.md, Our_Response_To_Electric_Vehicles.transcript.md, The_Trading_Strategy_Nearly_Everyone_Missed_During_the_GameStop_Opportunity.transcript.md, Zoom_shows_us_what_to_do_in_Peloton_Trading_Strategy.transcript.md, Creating_a_Basket_of_Stocks_to_Seize_a_Special_Trading_Opportunity.transcript.md

## Preconditions
Three sub-patterns share the same category; each has distinct preconditions:

**A. Sympathy / Sector Rotation Basket**
- A known macro event or sector catalyst is creating a clear rotation (risk-on into L1s, DeFi season, AI token narrative, meme squeeze).
- Multiple correlated tokens identified in advance (e.g. L1 basket: ETH, SOL, AVAX; DeFi basket: UNI, AAVE, CRV).
- Volume on sector leader is 3x+ normal (ARVOL threshold); sector names show correlated pre-market or early-session strength.
- Baskets pre-built with allocation ratios; hotkeys or one-click order templates staged.

**B. Leader-Lagger Fade**
- A sector leader is breaking down while a correlated lagger is still pressing highs (or vice versa for longs).
- The divergence window is typically 20–30 seconds; lagger has not yet responded to leader's move.
- Both assets belong to the same theme/sector basket (BTC leads → ETH lags; one L1 breaks → correlated L1 hasn't yet moved).
- Squeeze or high-beta altcoin surging while BTC/ETH sells off (deleverage dynamic from GME analog).

**C. Oversold Basket Mean Reversion (Swing)**
- Basket (BTC + ETH + SOL or broad L1 index) has corrected 10–15% from local highs into a major structural support zone (prior swing lows, high-volume node).
- Multiple assets in the basket simultaneously at key support.
- Risk can be defined using options (defined-risk long) + spot position for core.

## Entry trigger
**A. Sympathy / Sector Rotation:**
- Deploy long basket (sector beneficiaries) and short basket (sector losers, if any) simultaneously within 1–2 minutes of catalyst or sector breakout.
- Build core in 3 tranches: initial entry at first breakout, add on first pullback that holds VWAP, add on second breakout above session high. Do not go full size on Tranche 1.
- Within-basket conviction filter: if 2 of 3 basket names are showing correlated buying simultaneously, add size. If only 1 of 3 names is moving, reduce size until others confirm.

**B. Leader-Lagger Fade:**
- Wait for leader to confirm breakdown (break key intraday support + close below on 2-min chart).
- Fade the lagger (enter in direction of expected move) within the 20–30 second divergence window.
- Do not wait for the lagger to start moving — entry is on the leader's signal, not the lagger's confirmation.

**C. Oversold Mean Reversion:**
- Scale into long as price reaches support zone — do not buy all at once.
- Get more aggressive on gap-down flush into the support zone (better average entry).
- If price gaps up the next session and holds, add aggressively (do not wait for another pullback after this confirmation).

## Invalidation
**A. Sympathy / Sector:**
- Sector leader fails to hold breakout; names diverge and more than one basket leg weakens.
- More than 2 of 3 basket legs close below their opening range on 5-min chart.

**B. Leader-Lagger:**
- Lagger breaks above its intraday high with follow-through volume (invalidates short fade) or below its intraday low with follow-through (invalidates long fade).
- Leader recovers and reclaims the broken level.

**C. Mean Reversion:**
- Price holds below the defined support zone and makes new lows below it (structural support fails).
- Basket continues to new lows on expanding volume through the entry zone (no absorption).

## Targets
**A. Sympathy / Sector:**
- Names closing in top/bottom 15% of session range = strong signal for next-day continuation; hold overnight with stop at session VWAP.
- Intraday target: first ATR extension from breakout; partial at 50%, trail remainder with 15-min EMA.

**B. Leader-Lagger:**
- Target: lagger moves to match leader's level (full mean reversion of the divergence).
- Measured move = approximately one full ATR on the lagger.
- This is a 5-minute trade; do not hold beyond the initial reversion unless new structure develops.
- Cover into flush of new lows (for short fade); exit when tape shows buyers at key support levels.

**C. Mean Reversion:**
- Scale out 25% on Day 1 bounce, 50% on Day 2, exit remainder on Day 3–4 gap up.
- Four consecutive gap-ups is historically rare; take risk off after the third.
- Do not look back once a gap-up day holds the prior session high — add, not reduce, on that confirmation.

## Sizing notes
- Sympathy basket: use the name with highest ARVOL (volume relative to normal) as the primary leg with largest size; secondary legs sized at 50–70% of primary.
- Leader-lagger: size is scalp-scale; risk 0.5–1 ATR on the lagger move. Because the window is short, size should be pre-determined (not calculated mid-trade).
- Mean reversion swing: use options for a defined-risk long (maximum loss = premium paid) plus a smaller spot position for the core. Knowing exact premium at risk before entry is mandatory.
- Three-tranche building (Sympathy): Tranche 1 = 40% of planned size, Tranche 2 = 35%, Tranche 3 = 25%. Do not exceed planned total.
- Basket sizing across HL + Binance: primary liquid legs on HL perps; altcoin legs or spot exposure on Binance. Avoid splitting the same asset across both venues simultaneously (reconciliation complexity).

## Crypto adaptation notes
- **BTC is the universal leader.** BTC leads; ETH, SOL lag by 20–60 seconds in fast moves. Monitor BTC dominance in real time as a within-basket weighting signal.
- **Sector baskets by narrative cohort:** L1s (ETH, SOL, AVAX, APT), DeFi bluechips (UNI, AAVE, MKR), AI tokens (FET, RENDER, OCEAN), meme tier (DOGE, SHIB, PEPE). When one token in a cohort breaks out or breaks down, the correlated names in that cohort follow within 1–5 minutes.
- **Squeeze / deleverage analog (GME pattern):** When a low-cap altcoin squeezes aggressively, BTC and ETH often sell off as leveraged players deleverage. When the altcoin shows exhaustion (volume climax, funding rate spike + reversal, wick rejection on the high), buy BTC/ETH as the recovery trade. Monitor funding rate on the squeezing asset — funding rate reversal is the exhaustion signal.
- **Order book replaces Level 2 tape:** Large bids in the order book at key price levels on HL signal institutional support. Use 1-min and 3-min charts with order flow overlays (if available) as the tape-reading substitute. Consistent large fills on the bid = accumulation; consistent large fills on the ask = distribution.
- **ARVOL threshold for crypto:** 3x+ normal session volume on the asset within the first 30 minutes of a move signals the sector is in play and the basket trade has high expected value.
- **Perp vs spot delta balance:** For multi-day basket carries, pair HL perp (directional) with spot on Binance (delta anchor) to avoid full funding-rate exposure while maintaining sector exposure. This is the crypto equivalent of the equity "core position + intraday scalp component" approach.

## Common mistakes (from review transcripts)
- **Using a single name when the basket is confirming.** If ETH, SOL, and AVAX are all printing the same signal simultaneously, sizing only into ETH misses the diversified conviction signal. The basket is the edge; single-name is noise.
- **Entering the lagger before the leader confirms.** The 20–30 second window feels urgent; traders jump in before the leader has decisively broken the level. Wait for the leader first.
- **Adding size after a sympathy move is already extended.** Tranche 3 should only fire on a confirmed second breakout above session high, not on a continuation of an already-extended move.
- **Missing the inverse correlation trade on squeezes.** The most commonly missed trade in the source material (GME analog): while the squeezing asset captures all attention, the correlated blue-chips (BTC/ETH) sell off temporarily and offer a high-confidence mean-reversion long once the squeeze exhausts.
- **Not building a core position for trend days — scalping instead.** On days where basket alignment is clear and trend is established, the mistake is repeatedly scalping small profits out. Build a core and hold it; scalp around the core with small size.
- **Exiting too early on gap-up confirmation in mean reversion.** Day 2 gap-up that holds is an add signal, not an exit signal. Premature full exit on Day 2 leaves the largest portion of the swing move on the table.

## Example(s)
**EV / L1 Sector Opening Drive (sympathy basket):**
- Pre-session: L1 sector showing correlated strength in pre-market. ETH +2.1%, SOL +2.4%, AVAX +1.8%. SOL has 4x normal pre-market volume = primary leg.
- Open: SOL tests pre-session low, holds on tape (bid absorption). ETH and AVAX also hold at VWAP. All three bid simultaneously.
- Tranche 1: long SOL-PERP (primary, 40% of planned size), ETH-PERP (30%), AVAX-PERP on Binance (30%).
- First pullback holds VWAP on all three names. Tranche 2 add.
- SOL breaks above session high. ETH and AVAX follow. Tranche 3 add on SOL only (leader).
- Partial at 50% of Tranche 1+2 at 1 ATR. Trail remainder with 15-min EMA.
- Names close in top 10% of session range = hold overnight, stop at session VWAP.

**Leader-Lagger Fade (BTC leads → ETH lags):**
- BTC breaks below a key intraday support level on 2-min chart. ETH is still 0.3% above its corresponding support level.
- Enter short ETH-PERP within 20 seconds of BTC's confirmed break.
- ETH follows BTC lower within 45 seconds.
- Cover at ETH's key support level (matches BTC's relative move size).
- Total trade duration: 3–7 minutes.

**Squeeze Exhaustion — Buy BTC on Altcoin Flush:**
- Low-cap altcoin (BONK analog) has surged 40% in 2 hours. Funding rate on that asset hits +0.15% per 8h (extreme).
- BTC and ETH have sold off -2.1% during the squeeze (deleverage pressure).
- BONK shows volume climax candle + wick rejection at the high. Funding rate begins reversing.
- Enter long BTC-PERP and ETH-PERP simultaneously on exhaustion signal.
- Target: BTC and ETH recover to pre-squeeze levels. Trail with 5-min EMA.
