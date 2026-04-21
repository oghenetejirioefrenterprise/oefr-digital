# Liquidity Sweep Below Lows — Long Reversal
**Category:** liquidity_sweep  **Timeframe:** scalp  **Confidence:** high  **Venues:** Hyperliquid, Binance, Bybit
**Adapted from:** AM_Meeting_October_11th.transcript.md, How_To_Catch_Big_Reversal_Trades_Prop_Trading_Technique.transcript.md, How_to_Catch_Monster_Stock_Moves_that_no_one_expects.transcript.md, Prop_Traders_Guide_to_This_Weeks_Best_Stock_Picks.transcript.md, SMB_AM_Meeting_Commentary_EA_and_TWTR.transcript.md, SMB_AM_Meeting_Commentary_TWTR.transcript.md, Scalping_Was_Hard_Until_He_Discovered_This_Little_Trick.transcript.md, When_To_Buy_A_Market_Pull_Back.transcript.md, You_will_never_look_at_scalping_the_same_way_again.transcript.md, How_to_Ride_the_Momentum_from_BIG_Money_Traders_episode_1.transcript.md

## Preconditions
- Asset is at or approaching a significant prior low, round number, or key structural support (daily/4h level preferred)
- Market was in an uptrend or neutral regime before the flush
- Flush bar is sloppy, high-volume, and forced — not a clean trending selldown; implies liquidation cascade or stop-hunt rather than genuine distribution
- On perps: funding rate spikes negatively during or immediately after the flush (forced long liquidations or aggressive short-side momentum traders entering late)
- Optionally: high open interest cluster visible in order book just below key support (liquidation magnet)
- Pre-defined entry level set before the sweep (bounce list built in advance)

## Entry trigger
- Price wicks or closes below the key support level, then snaps back above it within 1–3 candles (15-second to 5-minute chart)
- The seller visibly lifts on tape / order flow: large aggressive sell orders stop printing; bids step back in
- Trend line break to upside on 30-second or 1-minute chart after the forced selldown completes
- On macro flush days (CPI/FOMC/liquidation cascade): buy the reclaim bar — the candle that closes back above the swept level
- Scale: initial position at reclaim, add on VWAP reclaim, core held to measured move

## Invalidation
- Price cannot reclaim the swept level within 5 candles of the flush low — indicates genuine selling pressure, not a sweep
- Continues to make new lows on similar or increasing volume after the first bounce attempt
- Funding rate stays deeply negative and price does not recover (longs being continuously liquidated, not just flushed)
- Stop: at or just below the flush low (the extreme wick)

## Targets
- T1: VWAP for the session (cover 25–33%)
- T2: Prior day close or session open — "undisturbed price" before the catalyst flush (cover 25–33%)
- T3: Measured move equal to the size of the flush below support added to the reclaim level (trail remainder with stop at prior consolidation low)
- Shot clock: expect T1 in roughly half the time it took for the forced sell to play out

## Sizing notes
- Entry size is 50% of planned position at the first reclaim signal; add the second 50% on VWAP hold
- This is a fast entry — pre-position limit orders at the key support level before the flush hits; do not market-order in after the wick
- Max risk per trade: stop at flush low, kept to normal single-trade risk limit
- In high-volatility regimes (BTC down 5%+, VIX equivalent elevated), reduce size by 30–50% — bounces are choppier and reversals can retrace before continuing

## Crypto adaptation notes
Stop hunts below key levels are the most common institutional tactic in 24/7 crypto markets. Perpetual futures markets create explicit liquidation clusters visible in open interest data — when a key level aligns with a known liquidation cluster, the flush-and-reverse probability is significantly higher than in equity markets. Unlike equities where a flush might happen once on the open, crypto flushes occur at any hour and repeat across sessions. Funding rate behavior is the primary confirmation tool not available in equities: a sharp negative funding spike during the flush that then normalizes back toward zero signals forced-cover reversal. The "Bella fade scalp" from SMB maps directly — look for the sloppy liquidation seller to lift, then ride the asset's natural tendency to revert. Always use the ICT/SMB framing: you are buying the stop-run, not buying a breakdown.

## Common mistakes (from review transcripts)
- Entering before the seller lifts — the seller can extend the move 2–3 more ATRs before exhausting; wait for the tape/order-flow signal
- Using a stop inside the flush wick rather than at the actual low — results in being stopped out of a valid trade by the very wick you identified
- Not pre-positioning limit orders and instead market-ordering after the snap-back is visible — executes at 50–70% of the available reward
- Holding full position through T1 (VWAP) trying to capture the measured move in a single leg — probability of a clean single-leg run is low; scaling de-risks while keeping exposure
- Over-trading the setup during high-VIX-equivalent days when correlation is 1.0 across assets — the flush-and-reverse still works but requires wider stops and happens more slowly
- Mistaking a trend continuation for a sweep: if the asset is already in a 3+ day downtrend with no catalyst and the level is not a major structural one, the flush is likely real distribution, not a sweep

## Example(s)
**BTC key support sweep (illustrative):** BTC approaches $82,000 (high open interest, liquidation cluster visible). High-volume wick to $81,400 prints on 1-minute chart — sellers aggressive, funding rate spikes to -0.04%. Within 2 candles, price reclaims $82,000. Funding reverts toward zero. Enter long $82,050 limit, stop $81,350 (just below wick low). T1 at VWAP ($82,800, cover 33%). T2 at prior session close ($83,500, cover 33%). T3 at measured move $84,600 (trail remainder).

**TWTR intraday flush (source Row 31/32):** Stock crushed with steady selling; preferred scenario was vertical acceleration to $30 then bounce to $32. Entry on reclaim of $32 after flush; target $34+ on successful hold.

**NFP macro flush (source Row 47):** On high-impact macro day, BTC sweeps below prior day low on news spike. Candle closes back above swept level within 1–2 bars. Enter long on reclaim bar; T1 = VWAP, T2 = prior high.
