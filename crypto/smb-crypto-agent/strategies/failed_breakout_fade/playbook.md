# Failed Breakout Fade — Trapped Trader Reversal
**Category:** liquidity_sweep  **Timeframe:** intraday  **Confidence:** high  **Venues:** Hyperliquid, Binance, Bybit
**Adapted from:** Do_You_Love_Failure_Patterns.transcript.md, The_ONE_Strategy_for_Beginner_Traders_Based_on_20_years_of_Prop_Trading_Experience.transcript.md, Forex_tip_How_to_recognize_a_fake_break_down.transcript.md, Trading_BOX.transcript.md, Trading_from_today_in_AXON_QQQ_SJM_VKTX.transcript.md, Round-number_break_fade (Feeling_when_its_different_reading_the_tape.transcript.md), Connor_FITB_Morning_Meeting_Leve_2_of_2.transcript.md, It_Feels_Like_Everyone_on_the_Street_is_Waiting_for_this_Trade_GENE.transcript.md, Trading_Kodak_and_why_not_to_trade_Delta.transcript.md, Trading_Oracle.transcript.md, Trading_Risk_Management.transcript.md, Trade_Review_With_A_Year-3_Proprietary_Trader.transcript.md, Understand_MORE_than_just_price_action.transcript.md

## Preconditions
- A key structural level is identified via volume profile (POC), VWAP, or prior day's high/low/close — not just "a line on a chart" but a level with observable market structure
- The asset has a directional hypothesis (hypo) — two scenarios pre-planned: bull case (breaks and holds) and bear case (fails and reverses)
- Price approaches the level and appears to break through — triggering breakout buyers (or breakdown shorts) who enter in the expected breakout direction
- The breakout/breakdown attempt shows one or more failure signals:
  - Volume is lower on the breakout attempt than on the prior approaches (conviction absent)
  - Tape/order flow shows the break was absorbed: large passive order wall at or just beyond the level was not lifted
  - Price quickly returns inside the prior range without building above/below the level
  - Speed of the lift or drop changes — noticeably slower or more hesitant than prior approaches (the "feels different" tape read)
- Two groups now trapped in the wrong direction: (1) breakout buyers who entered above the level, now holding losing longs; (2) covering shorts whose buys at the break added fuel but are now the selling pressure as they unwind

## Entry trigger
- Fade the failure: enter in the opposite direction of the failed breakout once price closes back inside the prior range
- Specific triggers (in order of conviction):
  1. Candle closes back inside the range on the same 1-minute bar as the breakout — strongest signal
  2. Failed hold: price breaks the level, consolidates for 1–3 candles, then a candle closes back below/above — enter on that close
  3. For offer-wall / VWAP tape variant: short when price approaches resistance for 2nd+ failed attempt, bid fades and price rolls back; entry on failed push, not on prior candle's break
  4. For pin bar / hammer variant: long on the confirmation candle after the hammer at key support — stop below the hammer low
- Rate the level quality 0–10 before entry: levels at confluence of VWAP + round number + prior swing = highest rating; do not trade sub-6 levels

## Invalidation
- Price holds and builds above/below the failed breakout level convincingly — 2+ candles closing on the other side with expanding volume
- The attempted direction resumes with a volume surge — the breakout was not a fake, it was a retest
- Stop: above the swing high of the failed breakout candle (for short fade); below the wick low (for long fade)
- If the level was pre-rated below 6/10 in quality, the setup is not taken regardless of the pattern

## Targets
- T1: VWAP (for mean reversion); rotate to here first (cover 33–50%)
- T2: Opposite extreme of the day's range (the far side of the structure) — the trapped traders provide continuous pressure toward this target (cover 25–33%)
- T3: Next major structural level in the fading direction (trail remainder)
- For offer-wall / VWAP variants: Low of day or prior consolidation support (below) as first target; measured move below consolidation range

## Sizing notes
- Standard unit sizing; this is a high-frequency intraday setup — do not oversize individual occurrences
- Can be traded multiple times per session if the level re-establishes as resistance/support — each new test with a different entry is valid
- "Try it three to four times with small size; you just need to be right once" (SMB tape-read principle) — small size on early attempts, increase on the confirmed failure test
- Level quality score matters for sizing: 9–10/10 levels get full size, 6–8/10 get 50–75%, sub-6 not traded

## Crypto adaptation notes
The failed breakout fade is natively powerful in crypto for structural reasons:

1. **Perp-specific liquidity traps.** On Hyperliquid and Binance perps, the order book shows clearly when a large passive order (wall) is absorbing a breakout attempt. When the wall holds and the breakout buyer is trapped, the fade is a direct mechanical trade against their forced unwind.

2. **VWAP as the primary mean-reversion anchor.** In equity markets, VWAP is an intraday tool. In 24/7 crypto markets, use the 24h rolling VWAP or the session-start VWAP (00:00 UTC or NY open). Failed breakouts below VWAP are bearish fades; failed breakouts above VWAP are bullish fades on the downside sweep.

3. **Volume profile / POC.** Crypto trading infrastructure on professional platforms exposes the volume profile in real time. The Point of Control (POC) from prior sessions is a natural target for the fade — price gravitates back toward it after a failed breakout sweep.

4. **Crypto community over-telegraphs setups.** When Crypto Twitter, Discord, and Telegram channels are all talking about the same breakout level, the setup is a high-probability fade candidate. The crowded breakout setup creates the trapped-trader fuel for the reversal. Use social signal density as a secondary confirmation that the fade has maximum trapped-trader pressure.

5. **Descending wedge / ascending wedge below/above VWAP** — after negative news catalyst or gap-down, if price forms a descending wedge below VWAP with sellers refreshing on every bounce, this is the failed bounce at VWAP variant: short each failed reclaim attempt. Applies to exploit disclosures, SEC actions, protocol vulnerability announcements.

## Common mistakes (from review transcripts)
- Not defining the hypothesis in advance — trading "failure patterns" reactively rather than having the two-scenario plan in place leads to chasing reversals after they have already moved
- Shorting the high of the breakout (anticipating the fade before confirmation) — this is the sequence that gets squeezed; wait for the close back inside the range
- Holding through a genuine re-test — if price comes back to test the swept level from the other side and consolidates there, that is accumulation/distribution, not a re-fade opportunity
- Ignoring the "no-trade zone" principle — not every level warrants a trade; define the zone where you will not trade (too close to VWAP, too far from a structural reference) and honor it
- Trading the fake-out without volume/delta confirmation — the failed breakout must show either declining volume on the attempt or a visible rejection signal on the order book; pattern alone is insufficient
- Applying the setup in a trend-day regime — on genuine trend days (5+ consecutive higher highs with consistent internals), failed breakouts are retests, not fades; identify the regime first

## Example(s)
**VWAP offer wall short (source Row 39 — BOX):** Token at resistance ($19.25–$19.35 battle zone). Multiple failed attempts to reclaim VWAP from below. Large offer refreshes each time. Bid thins on each attempt. Short on failed push (enter when price approaches offer wall, bid fades). T1 = low of day. T2 = measured move below consolidation.

**Double top fake-out (source Row 46):** Token at double top. Breaks above the resistance, triggering shorts to cover and breakout longs to buy. Price fails to sustain above. Both groups are now trapped sellers. Short on the close back below the double top level. T1 = neckline of double top. T2 = prior support.

**Round-number break fade (source Row 11):** Token at $3.00 key psychological level. Multiple failed lifts — each bounce slower and less urgent than the prior. Short when the lift speed changes (tape reads "different"). Cover half at VWAP; remainder on break of $3.00 level for second leg.

**Failed VWAP reclaim short (source Rows 42, 43):** After negative catalyst gap-down, token bounces to VWAP (now resistance). Tape shows sellers refreshing on every approach. Descending wedge forms below VWAP. Short on rejection from VWAP with volume. Target: wedge breakdown measured move, prior support below.
