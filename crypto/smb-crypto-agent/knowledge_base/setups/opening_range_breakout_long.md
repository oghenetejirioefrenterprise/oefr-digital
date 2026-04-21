# Opening Range Breakout Long

**Category:** opening_range_breakout  **Timeframe:** scalp/intraday  **Confidence:** high  **Venues:** Hyperliquid perps, Binance spot/futures
**Adapted from:** The_ORB_Strategy_High_Odds_Breakout_Technique.transcript.md, My_Incredibly_Easy_Trading_Strategy_that_works_nearly_every_day.transcript.md, The_Opening_Drive_Momentum_Trade_reading_the_tape.transcript.md, How_to_trade_the_open.transcript.md, The_Ultimate_Trend_Day_Trading_Course_For_Beginners_Developing_Traders.transcript.md, Powerful_Gap_Trading_Strategy_For_Active_Day_Traders.transcript.md, Gap_Give_Go_Trading_Strategy_Explained_in_3_minutes.transcript.md, How_to_Read_the_Tape_on_a_Breakout.transcript.md, 2_Essential_Indicators_to_Improve_Your_Breakout_Trades.transcript.md, How_to_trade_Breakout_Trades_more_effectively_ETSY.transcript.md, Elite_Prop_Traders_High_Odds_Breakout_Technique_Step-by-Step_Instructions.transcript.md, The_Daily_Breakout_Trade_Strategy.transcript.md, Prop_Trader_Details_a_Stock_Trade_You_Can_Make_Right_on_the_Open.transcript.md, WATCH_3_prop_traders_present_how_they_united.transcript.md, Trading_the_Post-Trump_Inauguration.transcript.md, I_ONLY_Focus_on_These_2_Things_In_Trading.transcript.md

## Preconditions

- Asset has a quantifiable **opening range** defined in the first 15–30 minutes of a major session open:
  - **US cash session** (NY open): ~13:30 UTC. Use the 13:30–14:00 UTC range as the ORB.
  - **Daily UTC candle**: 00:00–00:30 UTC opening range for crypto-native timing.
  - **Asia session**: ~00:00–01:00 UTC. EU session: ~08:00–08:30 UTC.
- **Volume confirmation (non-negotiable):** Relative volume (RVOL) ≥ 1.5× 20-day average at the time of break. The breakout bar's volume must be the highest (or among the top 2–3) of the session so far. Thin-volume breakouts fail at high rates.
- **Catalyst present**: News, protocol upgrade, token listing, ETF approval, macro event, or earnings-analog. No catalyst = reduced conviction, smaller sizing.
- Higher timeframe (daily/weekly) must not show immediate heavy overhead resistance within 0.5 ATR of the breakout level.
- Broader market (BTC for altcoins) must be neutral to bullish. Do not take altcoin ORBs when BTC is in an intraday downtrend.
- Optional amplifiers that justify larger size: (a) prior day closed strong / near highs, (b) stock-in-play scan showing top 3 RVOL, (c) multiple session aligns (e.g., EU range also broken), (d) short interest / negative funding rate available to fuel squeeze.

## Entry trigger

**Primary (ORB break):** Enter long on a candle that **closes** above the opening range high (ORH) with expanding volume. Never enter on a price touch alone — wait for the bar close or confirmed skip (price jumps over the level with no fills = institutional urgency).

**Tape-confirmation filter (for scalp precision):** Watch the order book or time-and-sales at ORH. Enter when:
1. Offers at ORH are **lifted** repeatedly with no significant pullback, AND
2. Bids **stack above** the prior offer level (control flip), OR
3. Price **skips** the level — bid/ask spread blows out and bids pile up high above the resistance.

Do NOT pre-enter in anticipation of the breakout. Enter only after the tape confirms buyers are winning the battle.

**Gap-Give-Go variant (entries after initial flush):**
- If the asset gaps up on catalyst, then pulls back (the "give") in an orderly fashion (no panic selling, volume contracting on the pullback), wait for the "go":
  - Entry on break of the 5-min high after the pullback low is confirmed (higher low vs. opening print).
  - Orderly give = pullback on light volume, bids step up. Panic give (wide spreads, aggressive offers) = setup is broken, stand aside.

**RB-ORB variant (pre-market range + ORB):** When both a pre-market range AND an ORB are established, break of ORB high (while above pre-market range high) gives a dual-range confirmation. Stop at the "buyer zone" — first identifiable area inside the range where buyers stepped in — not the full range low.

## Invalidation

- Candle **closes back inside** the opening range after the breakout (immediate failure). Exit at market.
- Bids disappear on the tape at the breakout level; large offer wall refreshes above with no buyer absorption.
- Broader market (BTC) breaks a key intraday support level simultaneously.
- Volume does not confirm: breakout bar volume is average or below — this is a high-probability false breakout. Do not add; reduce or exit.
- VWAP fails as support after breakout with aggressive selling volume.
- Stop placement: a few ticks/cents below the breakout candle low (tight), or below the buyer zone inside the range, never at the full range low (that is too wide for scalp sizing).

## Targets

- **T1:** Measured move = opening range height added to the breakout level. Take 33–50% off here.
- **T2:** 1 ATR above breakout level or next obvious daily resistance level. Take another 25–33% off.
- **Runner (T3):** Trail using the 9 EMA or 21 EMA on the 2-min or 5-min chart. Exit on first close below the trailing EMA. On confirmed trend days (VOLD > 3:1, ADD pinned, cumulative TICK trending), hold the runner to end of session.
- Scale-up signal: When price bursts through T1 with expanding volume, increase position to 75–100% of max size at the breakout level re-test (if the level now acts as support).

## Sizing notes

- Base size: 50% of maximum for standard ORB setups.
- Upgrade to 75–100% when all of the following stack: (a) RVOL > 3×, (b) confirmed catalyst ≥ 8/10 strength, (c) HTF aligned (daily/weekly breakout context), (d) market internals supportive.
- Downgrade to 25% or skip when: (a) conflicting signals (long signal but BTC downtrending), (b) low RVOL (< 1.5×), (c) thin pre-market / no catalyst.
- Use `core/allocator.py` for all sizing. This file only provides guidance on when to pass A vs B vs C grade to the allocator.
- A-grade ORB (all preconditions met, strong catalyst, high RVOL): allocator grade = A.
- B-grade (partial confirmation, moderate RVOL 1.5–2.5×): allocator grade = B.
- C-grade (technical only, no catalyst): skip or C-grade.

## Crypto adaptation notes

**Session translation:**
- "Opening range" in equities (9:30–9:45 ET) maps to:
  - **US session ORB:** 13:30–14:00 UTC. Highest liquidity on Hyperliquid. Use this for BTC, ETH, and top liquid alts.
  - **Daily ORB:** 00:00–00:30 UTC for the 24h candle open range. Relevant for setups referencing daily levels.
  - **Asia session ORB:** 00:00–01:00 UTC. Lower liquidity; require larger RVOL multiple (> 2×) to compensate for noise.
  - **EU session ORB:** 08:00–08:30 UTC. Medium liquidity; often sets direction before NY open.
- **Pre-market range equivalent:** On 24/7 crypto, the **Asian session range** (00:00–08:00 UTC) serves as the pre-market range for the US session. A break above the Asian session high with RVOL at 13:30 UTC = standard pre-market high breakout.
- **Tape reading on Hyperliquid:** Use the Level 2 order book and trades feed. Watch for:
  - Offers being lifted aggressively at ORH (large market buys).
  - Bid wall forming above ORH (buyers front-running the break).
  - "Skip" in price: if ask jumps from $X to $X+0.5% with no fill at intermediate prices — institutional urgency, enter on the next bid.
- **Volume confirmation:** Use 20-day ADV from Binance/Hyperliquid API. RVOL ≥ 1.5× is the floor; prefer ≥ 3× for high-confidence sizing.
- **VWAP:** Use 24h session VWAP or session VWAP (anchored to 13:30 UTC for US session). VWAP hold after breakout = add signal. VWAP loss = exit signal.
- **Funding rate awareness:** Positive funding during an ORB long = crowd is long = momentum confirmation but eventual reversion risk. If funding > 0.1% per 8h, plan to scale out faster. Negative funding on an ORB long = excellent (shorts will be squeezed).
- Avoid ORB long setups at major round-number resistances (e.g., BTC $100k) without confirmed high-volume acceptance above.

## Common mistakes (from review transcripts)

1. **Chasing the initial breakout** instead of waiting for the first pull-in to the breakout level (the retest). The retest at former ORH (now support) is the lower-risk entry. — *The_Juicy_Breakout_Trade_Mistake.transcript.md*
2. **Entering before the range is fully formed.** The ORB is not complete until the first 15–30 minutes close. Entering at 9:31 ET (13:31 UTC) is not an ORB trade — the range has not been established. Win rate is materially lower before 9:45 ET equivalent. — *The_ORB_Strategy_High_Odds_Breakout_Technique.transcript.md*
3. **Ignoring market context.** A technically valid ORB in the wrong market context (BTC downtrending, broad red day) loses. Always check market internals first. — *A_Losing_Breakout_Trade_You_Dont_Want_to_Make.transcript.md*
4. **Trading too many sub-setups** on a strong ORB day instead of sizing the one A-grade trade and holding it. — *One_Common_Trading_Mistake_New_Traders_Need_to_Eliminate.transcript.md*
5. **Selling the first pullback on a trend day.** On confirmed trend days, the first pullback to VWAP after ORB is the add point, not the exit. — *What_two_traders_did_to_stop_selling_too_early.transcript.md*
6. **Not using tape confirmation.** Price alone at the ORH is insufficient. Watch whether bids are absorbing or sellers are refreshing. — *How_to_Read_the_Tape_on_a_Breakout.transcript.md*
7. **Misplacing the stop.** Stop at "the bottom of the range" is too wide; place at the first buyer zone inside the range. Wide stops force reduced size and poor R:R. — *My_Incredibly_Easy_Trading_Strategy.transcript.md*

## Example(s)

**Example 1 — BTC US Session ORB (template):**
- 13:30 UTC: BTC opens at $97,500 after CPI comes in softer than expected (catalyst).
- 13:30–14:00 UTC: BTC ranges $97,200–$97,800 (ORH = $97,800; ORL = $97,200; range height = $600).
- RVOL at 13:45 UTC: 2.8× 20-day average.
- 14:03 UTC: BTC prints a 5-min bar closing at $97,900, above ORH. Volume on this bar is highest of session. Tape shows offers at $97,800 lifted cleanly, bids stack at $97,820.
- Entry: $97,920 (above the breakout bar high) or at the close of the breakout bar.
- Stop: $97,650 (first buyer zone inside the range from the 13:45 UTC bar low).
- T1: $97,800 + $600 = $98,400. Take 40% off. (Risk = $270; T1 reward = $480 → 1.8:1)
- T2: $99,000 (next key resistance). Take 40% off. Remaining 20% trails 21 EMA on 2-min.

**Example 2 — Day-1 Catalyst ORB (token listing, Hyperliquid):**
- New DeFi token lists on Hyperliquid at 13:30 UTC after major protocol partnership announcement.
- First 15-min range: $1.20–$1.35 (ORH = $1.35; range = $0.15).
- RVOL = 5× 7-day average. Tape: large bids at $1.32 absorbing all offers.
- Entry on break of $1.35 with skip to $1.37; stop at $1.28 (buyer zone inside range).
- T1: $1.35 + $0.15 = $1.50. Scale 50% off.
- T2: $1.65 (1 ATR above breakout). Trail remainder on 9 EMA 2-min.

**Example 3 — Gap-Give-Go variant (ETH, EU session):**
- ETH protocol upgrade goes live at 06:00 UTC. ETH gaps up from $3,800 to $3,950.
- 08:00 UTC EU session open: ETH pulls back to $3,880 on light volume (orderly give, volume < 0.5× prior spike volume).
- 08:15 UTC: $3,880 holds, higher low forms vs. $3,860 pre-pull-back low. Volume picks up.
- Entry on break of 08:05 5-min high ($3,910); stop at $3,855 (pullback low).
- T1: $3,950 (gap high, prior ORH). Take 50% off. Runner targets $4,100 (1 ATR), trail 21 EMA 5-min.
