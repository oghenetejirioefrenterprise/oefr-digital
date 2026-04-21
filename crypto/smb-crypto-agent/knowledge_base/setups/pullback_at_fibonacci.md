# Pullback at Fibonacci

**Category:** pullback_in_uptrend  **Timeframe:** intraday  **Confidence:** med  **Venues:** HL perps, Binance spot, Binance futures

**Adapted from:** Forex_lesson_of_the_week.transcript.md, Forex_trade_finding_level_of_support.transcript.md, Forex_trade_When_its_time_to_trade_and_time_not_to_trade.transcript.md, Inside_the_Forex_Classroom_with_Marc_Principato.transcript.md, Live_forex_trade_How_a_swing_trade_is_initiated.transcript.md, Live_from_our_forex_desk_Price_projection_trade.transcript.md, middayreviewflv.transcript.md, High_Accuracy_Swing_Trading_Setups.transcript.md, High-Precision_Swing_Trade_Setups_from_a_Prop_Firm_Trader.transcript.md, Mastering_Swing_Setups_Breakouts_Continuations_and_Reversal_Plays.transcript.md, AM_Meeting_June_6th.transcript.md, SMB_Forex_-_EURUSD_Analysis.transcript.md

## Preconditions

- Clear prior swing: identifiable swing low (A) to swing high (B) on 1h or 4h chart
- The A-B leg is an impulsive move (not a choppy grind) — ideally 3+ large directional candles
- Price is now in a corrective pullback from B toward the Fibonacci retracement levels
- Primary Fibonacci levels to watch: 38.2%, 50%, 61.8% of the A-B swing
- Confluence is required — the Fibonacci level should coincide with at least one of:
  - Prior support/resistance level (prior swing high, round number, range boundary)
  - Rising EMA (20/50 on the same timeframe)
  - Session VWAP or anchored VWAP from a significant event
- Correlated instrument confirmation: BTC showing same Fibonacci support for alts; ETH/BTC holding for DeFi tokens
- Avoid the setup if the pullback has already exceeded the 61.8% level without reversing — deeper pullback suggests trend change

## Entry trigger

**Multi-timeframe cascade (preferred):**
1. Identify Fibonacci levels on 4h chart (primary structure)
2. Zoom to 1h for setup pattern (consolidation, higher low forming near Fibonacci level)
3. Use 15m for precise entry trigger (reversal candle at the Fibonacci level)

**Entry mechanics:**
1. Price reaches the 50% or 61.8% retracement zone (38.2% can be used in very strong trends)
2. A reversal signal forms on the 15m: hammer, bullish engulfing, or 2-bar reversal
3. Confirm with correlated instrument (BTC holding its own Fibonacci support, or sector alt-index green)
4. Enter on the close of the reversal candle or first uptick of the next candle
5. Stop: 3–5 bps below the Fibonacci level itself (tight — this is the key level)

**Fake breakdown variant (higher conviction):**
1. Price briefly dips below the 61.8% level (1–2 candles), then snaps back above it
2. This false break confirms buyers are present below the level and traps shorts
3. Enter on reclaim of the 61.8% with a stop at the false breakdown low

## Invalidation

- Price closes a 1h bar below the 61.8% Fibonacci level — structure suggests continuation of pullback
- C-leg extends below A (makes a new low below the swing start) — trend reversal, not pullback
- Correlated instrument breaks its own Fibonacci support simultaneously
- Volume on the pullback exceeds volume on the impulse leg (distribution, not correction)

## Targets

- T1: 100% of the A-B move reapplied from the entry point (1:1 Fibonacci extension) — take 50% here
- T2: 127.2% extension — take 25% here
- T3: 161.8% extension — trail remainder using prior bar lows
- Minimum required R:R: 4:1 (stop is tight at the Fibonacci level; target is the measured move extension)

## Sizing notes

- Base size only for 38.2% entries (weakest confluence level)
- Standard size for 50% entries with at least one additional confluence factor
- Full size (1.5×) only for 61.8% entries with: fake breakdown reversal + EMA/VWAP confluence + correlated instrument confirmation
- Never size up without all four: Fibonacci level + reversal candle + confluence factor + correlated confirmation

## Crypto adaptation notes

- Fibonacci retracements work in all liquid 24/7 markets — BTC, ETH, SOL, and top-10 alts all respect these levels due to algorithmic trading
- The 50% and 61.8% levels are the most actionable on BTC 4h charts; the 38.2% level only works in extremely strong trends (open interest expansion during impulse)
- Session context for crypto: the 50% Fibonacci retracement during the US session (9:30 AM–4 PM ET) carries more weight than in the overnight session; institutional algo orders are most active during US hours
- Funding rate as Fibonacci enhancer: if BTC pulls back to the 61.8% Fibonacci AND funding is negative (shorts crowded), the probability of reversal is significantly elevated — this is an A+ confluence signal
- For altcoins: use BTC's Fibonacci levels as the macro guide; if BTC holds its 50% Fibonacci, the alt's own Fibonacci level is more likely to hold

## Common mistakes (from review transcripts)

- Shorting the pullback toward a Fibonacci level instead of waiting for the entry — the pullback is the setup, not the trade
- Using Fibonacci without any additional confluence — a lone Fibonacci level is a guide, not a signal; always require one more factor
- Entering on the approach to the level before price arrives — "patiently waiting for the support level to be reached" is the discipline; early entries reduce R:R
- Ignoring the correlated instrument — if BTC breaks its own Fibonacci simultaneously, the alt Fibonacci is invalid
- Using the same Fibonacci settings across all timeframes — measure only from clear impulsive swing lows to swing highs; do not apply to choppy range movements

## Example(s)

**BTC/USDC perp (HL), 4h Fibonacci swing:**
- BTC rallies from $82,000 (A) to $96,000 (B) in a 5-day impulse (clear 4h structure)
- 50% Fibonacci at $89,000; 61.8% at $87,500
- BTC pulls back over 4 days to $89,200; 20 EMA on 4h at $88,800 (confluence)
- 15m shows hammer at $89,000 with a brief wick to $88,600 (fake breakdown) followed by re-bid
- Enter long at $89,200; stop at $88,400 (below false breakdown low)
- T1: $96,000 (100% extension); T2: $101,200 (161.8% extension)
- R:R = ($96,000 - $89,200) / ($89,200 - $88,400) = 8.5:1

**ETH/USDC perp (HL), 1h Fibonacci with BTC correlation:**
- ETH impulse from $3,000 to $3,600; pulls back
- 61.8% Fibonacci at $3,228; anchored VWAP from listing date at $3,220 (confluence)
- BTC simultaneously at its own 50% Fibonacci
- 1h bullish engulfing at $3,225; enter at $3,250; stop $3,180; T1: $3,600; T2: $3,870
