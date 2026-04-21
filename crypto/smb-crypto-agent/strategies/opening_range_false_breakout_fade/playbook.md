# Opening Range False Breakout Fade

**Category:** opening_range_breakout  **Timeframe:** scalp  **Confidence:** high  **Venues:** Hyperliquid perps, Binance USDⓈ-M futures
**Adapted from:** How_I_Avoid_False_Breakouts_My_Secret_Technique.transcript.md, SMB_U_-_The_PlayBook_Check_Up_Breakout_Fade.transcript.md, Every_Trader_Needs_to_Know_This.transcript.md, This_Weeks_Cant-Miss_Swing_Trades.transcript.md, How_To_Avoid_A_Runaway_Freight_Train.transcript.md, The_Overlooked_Signal_That_Catches_Massive_Downside_Moves.transcript.md, Trouble_Deciding_to_Trade_a_Stock_Long_or_Short.transcript.md, What_Im_Trading_This_Week_Prop_Trader_Guide.transcript.md, Bar_by_Bar_Analysis_of_High_Probability_Entries_Exits.transcript.md, Coronavirus_Fears_Trigger_Excellent_Trading_Opportunities.transcript.md

## Preconditions

This setup **exploits the failure of a breakout** rather than its success. It activates when a price break above the ORH (or below the ORL) produces **lethargic or indecisive follow-through** and then reverses back inside the range. The failed breakout itself is the high-conviction signal in the opposite direction.

**Conditions that make a breakout likely to fail:**
- **Lethargic bar sequence after the break:** In the 5 candles immediately following the breakout, classify each bar:
  - *Aggressive:* strong directional close (close in top/bottom 20% of bar range), above-average volume.
  - *Passive:* close near midpoint, moderate volume — indecision.
  - *Lethargic:* small body, wicks both ways, below-average volume — buyers/sellers unable to commit.
  - If the first 2–3 bars after the breakout are passive or lethargic, the breakout is failing. When price then reverses back inside the range, the false breakout fade is triggered.
- **Volume does NOT confirm the breakout:** Breakout bar has average or below-average volume. A true breakout requires the highest-volume bar of the session on the break.
- **Price does NOT accelerate away** from the level: True breakouts skip price levels (gap between bid and ask blows out). If price drifts above the ORH by a small amount without any acceleration, expect failure.
- **Wrong market context:** Breakout upside occurs while BTC is in intraday downtrend, or broader crypto breadth is negative. Technical breakout against the primary trend has very low follow-through.
- **Multi-test resistance / overextension:** The breakout attempts a level that has been tested 4+ times (supply buildup) and the asset is already 2+ ATR from the VWAP. Overextended + heavy resistance = high false-breakout probability.
- **Parabolic backside setup:** For assets that have been parabolic for 3+ days with accelerating ATR and are now showing the blowoff pattern (highest volume bar of the entire move on an up day), the opening range breakdown of the backside day is the fade entry. The false breakout above is often the "spray candle" — wide upper wick, close near low.

## Entry trigger

**Standard false-breakout fade (after lethargic sequence):**
1. Price breaks above ORH (or below ORL) and candle(s) form showing lethargic or passive characteristics.
2. Price reverses back **inside** the opening range.
3. Enter the fade trade as price closes inside the range after the failed breakout:
   - **False breakout to the upside → fade short:** Enter short when price closes a candle below ORH after the lethargic sequence. Stop above the failed breakout high (the actual high made during the false breakout, not the ORH itself).
   - **False breakout to the downside → fade long:** Enter long when price closes a candle above ORL after the lethargic sequence. Stop below the failed breakdown low.

**5-bar classification method (from How_I_Avoid_False_Breakouts):**
- Observe the 5 bars after the breakout attempt and classify each.
- If the sequence shows: *lethargic → lethargic → aggressive (in the OPPOSITE direction)*, this is "false pressure building then real move happening." Enter in the direction of the aggressive reversal bar.
- Do NOT enter on the first lethargic bar — wait for 2+ lethargic/passive bars followed by the confirming aggressive bar in the fade direction.

**Fold / Stand / Add decision:**
- Lethargic bars after breakout → **Fold** (exit any long/short entered on the breakout).
- Indecisive bars → **Stand** (hold but do not add).
- Aggressive bars in SAME direction → **Add** (true breakout confirmed).
- Aggressive bars in OPPOSITE direction after lethargic → **Fade** (this is the false breakout trade entry).

**Down-through-open / opening range failure short (parabolic backside):**
For assets 3+ days parabolic with blowoff volume signals:
- Rally off the open into prior day's close or VWAP fails.
- Price turns back below opening print on above-average volume.
- Enter short on the candle that closes back below the opening print. Stop: high of day.

## Invalidation

- After the fade entry, price reverses again and closes **back above the false breakout high** (for a fade short) with expanding volume — buyers overwhelmed the fade sellers. Exit immediately; the true breakout is now confirmed.
- Volume **picks up in the breakout direction** after 2–3 lethargic bars — the pause was institutional accumulation, not exhaustion. Do not fade; exit fade entry.
- Market context shifts: BTC reverses to strong uptrend during a fade short — cover and reassess.
- Stop: placed above the false breakout high (for fade short) or below the false breakdown low (for fade long). Do not widen the stop — the entire thesis of this setup is that the failed level now acts as strong resistance/support.

## Targets

- **T1:** VWAP or midpoint of the opening range. Cover 40–50% here.
- **T2:** Opposite boundary of the opening range (ORL for a fade short from ORH failure; ORH for a fade long from ORL failure). Cover another 30%.
- **Runner:** Trail via 9 EMA on 1-min or 5-min chart. Exit on first close against the 9 EMA. On multi-day parabolic backside setups, T2 extends to prior day's low and the 5-day moving average.
- **Parabolic backside extended targets:**
  - Prior day's low (cover 33%).
  - 5-day moving average.
  - 2-day VWAP.
  - If second leg forms (consolidation below VWAP → another flush), re-enter for the second leg with 50% of original size.

## Sizing notes

- Base size: 50% of maximum for standard false-breakout fades.
- Upgrade to 75% when: (a) Lethargic sequence is 3+ bars, (b) volume clearly failed to confirm the breakout, (c) market context is opposed to the breakout direction.
- Parabolic backside: 60–75% of max, because the setup has a statistical skew. However, acknowledge that parabolic moves can extend — do not override a fresh catalyst that could restart the move.
- Never full size on a counter-trend fade without: (a) clear lethargic confirmation, (b) defined stop, (c) VWAP target as minimum viable reward.
- Grade: A-grade fade = 3+ lethargic bars + volume failure + wrong market context. B-grade = 1–2 conditions.
- All sizing through `core/allocator.py`.

## Crypto adaptation notes

**Why false breakouts are common in crypto:**
- 24/7 markets without natural session end resets means price often sweeps prior highs/lows before reversing (liquidity grabs). The false breakout fade is one of the most reliable intraday setups in crypto precisely because these sweeps are systematic.
- On Hyperliquid, stop-loss clusters above round numbers and prior highs are visible in open interest data. A break above a heavily-clustered stop level that fails to follow through (lethargic bars) = very high-probability fade.

**Session-specific false breakout patterns:**
- **NY open false breakout (13:30–14:00 UTC):** The most common — assets gap open and immediately reverse. Within the first 5 min if the move is not sustained with volume and tape urgency, fade.
- **Asia session liquidity grab (01:00–03:00 UTC):** Thin liquidity produces frequent false breakouts above/below key levels. Fade these with smaller size (50% of standard) due to potential for further thin-market follow-through.
- **End of day lethargic breakout (22:00–23:59 UTC):** Low-volume breakouts near session end are almost always fades.

**Tape signals for false breakout in crypto:**
- Price breaks above ORH; order book shows offers **refreshing** at each tick up (sellers are adding supply into the breakout, not being absorbed). This is the most reliable false-breakout signal.
- Post-breakout volume drops sharply (visible in 1-min volume bars) after the initial spike — exhaustion of buying pressure.
- Funding rate check: If funding spikes sharply positive on the breakout but price fails to hold, the leveraged longs are now trapped. Fade short with target of funding rate mean reversion.

**Parabolic backside crypto application (from The_Overlooked_Signal):**
- Identify 3+ day accelerating move: each day's candle range larger than prior day; 2–3 consecutive gap-ups.
- Blowoff day = highest volume bar of the entire multi-day move.
- Next day (backside day 1): three entry variants on Hyperliquid perps:
  1. **ORB break:** Range forms in first 30 min; fails to break above pre-market high; enter short on break of range low.
  2. **Down-through-open:** Rally off open into VWAP or pre-market resistance fails; price turns below opening print; enter short.
  3. **Long consolidation rollover:** Price consolidates sideways for 1+ hour below VWAP, frustrating both sides; when price tightens further (bear flag), enter short.
- Target: prior day's low (first), 5-day MA (second).
- Crypto IV (Deribit DVOL) analog: when IV is extremely elevated near the top of a move and then begins declining, that confirms the blowoff phase.

**Multi-touch resistance false breakout:**
- A level tested 4+ times in crypto (visible on 4h chart) **does eventually break** — but the 4th and 5th tests often produce brief false breakouts above that level before the real break. Fade the 5th test unless: (a) volume is 2× the prior tests, (b) catalyst is present.
- Rule from Tricks_of_The_Trade: "Four tests of a level — the fifth test is likely to BREAK it." This means: fade tests 2–4 (false breakouts), but be cautious fading the 5th (the real break may be imminent).

## Common mistakes (from review transcripts)

1. **Fading at the very top without waiting for lethargic confirmation.** The reversal trade is cleaner and easier to hold when you wait for price to confirm the failure (lower high + lower low) rather than fading at the absolute peak. — *SMB_U_-_The_PlayBook_Check_Up_Breakout_Fade.transcript.md*
2. **Not defining the stop.** The stop for a false breakout fade is above the false breakout high — a very specific level. Not defining it before entry leads to holding through a true breakout.
3. **Fading with too much size in low-liquidity sessions.** Asia session fades on thin markets can produce continued extensions before reversing; reduce size 30–50%.
4. **Confusing a pause with lethargic bars.** A brief 1-bar pause on a strong momentum breakout is not a lethargic sequence; wait for 2–3 bars of non-commitment before classifying as false breakout.
5. **Not covering into parabolic drops.** Fades of parabolic blowoffs can produce 2–3 ATR drops in minutes. If the decline becomes near-vertical (each candle's range exceeds prior candle's range), cover 50–70% immediately — these exhaust as fast as they fall.
6. **Holding a fade against a fresh catalyst.** If a new catalyst arrives during a false-breakout fade that validates the original breakout direction, exit the fade immediately. The catalyst overrides the technical setup.

## Example(s)

**Example 1 — BTC false breakout fade (US session):**
- 13:30 UTC: BTC opens at $98,500. Range forms: $98,200–$99,000 (ORH = $99,000).
- 14:05 UTC: BTC prints a 5-min bar closing at $99,100 (break above ORH). Volume: below average for the session (1.1× baseline; the ORH bar should have been 2×+ to confirm).
- Next 3 bars (14:10–14:20 UTC): BTC oscillates $98,900–$99,200. Small bodies, equal wicks up and down. Volume declining on each bar. Classification: 3 lethargic bars.
- 14:25 UTC: BTC prints an aggressive bar closing at $98,600 — back inside the ORH.
- Fade entry: short at $98,550. Stop: $99,250 (above false breakout high). Risk: $700.
- T1: VWAP ($98,200). Cover 40%. T2: ORL ($98,200 = T1 here; extend to $97,800 if volume continues). Runner: trail 9 EMA 1-min. Total potential: $750–$1,200 per contract.

**Example 2 — Altcoin parabolic backside ORB short:**
- Token ran +30%, +25%, +40% over 3 consecutive days. Day 3 (blowoff): highest volume bar of the entire move, closes with upper wick (doji-like).
- Day 4 (backside day): Opens at $4.80. First 30-min range: $4.60–$4.90 (ORH = $4.90).
- Price rallies to $4.92 (breaks ORH) but volume on the breakout bar is 40% lower than the Day 3 blowoff bars. Two lethargic bars follow.
- Fade entry: short at $4.75 (when price returns inside range). Stop: $5.05 (above false breakout high).
- T1: $4.30 (prior day's low). T2: $3.90 (5-day MA). Trail 9 EMA 5-min.

**Example 3 — EU session false breakdown fade long:**
- ETH 08:00 UTC EU open. Range: $3,500–$3,560. ORL = $3,500.
- 08:20 UTC: ETH dips to $3,488 (breaks ORL). No catalyst driving the break; volume on the breakdown bar is 0.9× baseline (below average). Tape: bids immediately appear at $3,490.
- Next 2 bars: ETH holds $3,492–$3,505, volume declining. Classification: 2 passive bars (no follow-through from sellers).
- 08:30 UTC: ETH closes above ORL ($3,508). False breakdown confirmed.
- Fade entry: long at $3,510. Stop: $3,482 (below false breakdown low). T1: $3,540 (VWAP). T2: $3,560 (ORH). Runner trails 9 EMA 3-min.
