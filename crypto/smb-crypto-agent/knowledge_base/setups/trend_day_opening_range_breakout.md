# Trend Day Opening Range Breakout
**Category:** trend_day_continuation  **Timeframe:** intraday  **Confidence:** high  **Venues:** HL perps, Binance futures

**Adapted from:** 10_Steps_to_Trading_Trend_Days_How_to_CRUSH_It.transcript.md, The_Ultimate_Trend_Day_Trading_Course_For_Beginners_Developing_Traders.transcript.md, The_ORB_Strategy_High_Odds_Breakout_Technique.transcript.md, Elite_Prop_Traders_High_Odds_Breakout_Technique_Step-by-Step_Instructions.transcript.md, How_to_trade_a_Gap_and_Go.transcript.md, The_Opening_Drive_Momentum_Trade_reading_the_tape.transcript.md, See_A_Potential_Trend_Day_BEFORE_The_Open.transcript.md, Bar_by_Bar_Analysis_of_High_Probability_Entries_Exits.transcript.md, How_to_Use_Technical_Analysis_Signals_that_Can_Lead_to_Large_Stock_Trading_Gains.transcript.md, Using_Unusual_Trading_Volume_to_Find_a_Profitable_Gap_and_Go_and_PullBack_Trade.transcript.md, Dont_Fade_This.transcript.md, SMB_Trade_of_the_Week_-_SPY.transcript.md, november1stflv.transcript.md, PlayBook_Checkup_Uptrend_Continuation_after_Strong_Opening_Drive_AOL.transcript.md, The_Opening_Drive_Momentum_Trade_reading_the_tape.transcript.md, I_ONLY_Focus_on_These_2_Things_In_Trading.transcript.md

## Preconditions

- Trend day confirmed via internals (see trend_day_recognition_checklist.md): VOLD/breadth/CVD aligned within first 30 minutes
- Macro catalyst or structural breakout driving the directional move
- Pre-market or overnight session has established a clear directional bias:
  - Bull: overnight session broke higher and held key support; pre-market holding above overnight balance high
  - Bear: overnight session broke lower; pre-market holding below overnight balance low
- Elevated volume in pre-market window (AVAL >35% of ADV) confirming institutional interest
- Opening range forms cleanly: first 5-30 minutes create an identifiable high and low with no chaotic whipping
- Higher timeframe (daily/weekly) chart aligned with intraday direction — this is not a counter-trend ORB

**Do NOT enter before the opening range is complete (wait for 5-30 minutes minimum):** "I don't like to take opening range breaks before 9:45 — my win rate is quite low if I jump the gun."

## Entry trigger

**Primary (ORB Break with Highest-Volume-Bar Confirmation):**
- Wait for the opening range to form (5-30 minutes after session open or major catalyst)
- Enter on break ABOVE the opening range high (bull trend day) or BELOW the opening range low (bear trend day)
- The breakout candle should be the highest-volume bar of the session so far — volume confirms institutional commitment
- Enter on the breakout candle close (do not enter mid-candle unless tape is accelerating aggressively)
- Stop: opposite end of the opening range (for tight stops) or below the breakout candle low (for tight momentum entries)

**Secondary (Opening Drive then Retest):**
- Price breaks above the opening range high on volume (opening drive)
- Pulls back to the broken range high (now support) on declining volume
- Tape shows bid absorption at the prior range high; offers stepping back
- Enter on VWAP reclaim or on first green candle off the retest level
- Stop: below the retest low or below VWAP

**Tertiary (Tape-Confirmed Opening Drive Entry):**
- Watch tape from the open: want SLOW tape (tight spread, no acceleration lower) confirming support holds
- When tape begins to ACCELERATE (price starts skipping levels — 20-25 tick jumps instead of 5-tick moves), this is the institutional buy program activating
- Enter on the tape acceleration signal above the key pre-market level
- "Stop predicting, start reading the tape — I don't need to know what happens, I want to see what you're seeing."
- Stop: prior session support level (Day 1 afternoon support)

**Gap-and-Go variant (strong catalyst + pre-market high hold):**
- Stock/token gaps up 20%+ on major catalyst (FDA, listing, macro)
- Price holds above pre-market support on open (no immediate breakdown)
- Tape shows bids absorbing offers at pre-market support level
- Enter long when first 1-min candle closes above opening range high with elevated volume
- Stop: below pre-market support
- "The best entry happened right on the open — if you weren't ready to take that entry below pre-market support you weren't going to get it again."

## Invalidation

- Breakout fails immediately and price reverses back inside the opening range within 2 bars — false breakout; exit
- Opening range break occurs but volume is NOT the highest bar of the session — low conviction; stay small or pass
- Internals (CVD/breadth) reverse against the ORB direction within 15 minutes of entry — early warning; reduce
- Price returns inside the opening range on expanding volume — clear invalidation; exit full position
- Pre-market support breaks with volume on open (for gap-and-go variant) — thesis invalid before entry

## Targets

- **Trend day + ORB = trade-to-hold:** The ORB is not a scalp on a confirmed trend day. Hold the position through the full session unless invalidation triggers.
- Measured move 1: opening range height added above breakout point — this is the minimum target
- Measured move 2: 1.5-2x the opening range height for high-RVOL (>5) setups or strong catalyst breakouts
- "When RVOL is over five we need to have an imagination — the stock could move two, three, four even five ATRs"
- First partial (25-33%): at 1x opening range height above breakout
- Add on VWAP pullback: if price pulls back to VWAP on light volume after the ORB, add (see trend_day_add_into_strength.md)
- Trail: 9/21 EMA on 2-min chart; exit on first close below (above for shorts) 21 EMA

## Sizing notes

- Full daily risk allocation when: all 3 internals aligned + ORB forms cleanly + highest-volume-bar confirmation
- Reduce to 50-75% size if: only 2 of 3 internals confirm, OR pre-market volume is below threshold
- Gap-and-go catalyst variant: can use conservative leverage (3-5x on Hyperliquid perps) given the tighter stop distance (below pre-market support)
- After entry, move stop to break-even when position is 1:1 in the money — protect against false ORB

## Crypto adaptation notes

**Defining the Opening Range in 24/7 Crypto:**
There is no single "open" in crypto. The relevant "opening range" windows are:

1. **Daily open range (00:00 UTC):** First 15-30 minutes after the 00:00 UTC daily candle reset. This is the most important range for trend day analysis.
2. **US cash session open (13:30 UTC / 09:30 ET):** Second most important opening range. US institutional participation begins here. For macro-driven crypto moves, this is often the highest-conviction ORB window.
3. **Asia session open (21:00 UTC / 17:00 ET prior day):** Relevant for token-specific catalysts originating in Asia (major exchange announcements, regulatory decisions from Asian regulators).
4. **Post-catalyst range:** After a major catalyst hits mid-session, anchor a new "opening range" from the catalyst timestamp. Use the first 15-minute range after the headline as the ORB reference.

**Volume confirmation in crypto:** On Hyperliquid, the "highest volume bar of the session" is observable directly on the chart. On Binance, use relative volume (current bar volume / 20-bar average). A breakout bar with 3-5x the prior bars' average volume = institutional confirmation.

**Pre-market support = prior session support:** In crypto, "pre-market support" translates to the overnight session low (00:00-09:30 ET equivalent). The overnight low is the key level that, if held at the 09:30 ET US open, confirms the gap-and-go setup.

**Tape reading on Hyperliquid:** The equivalent of "tape acceleration" in crypto order books is: price printing multiple consecutive levels in the same direction without reverting (bid lifting through ask levels consecutively). This is visible in the Level 2 order book depth and in the trade tape on Hyperliquid. When BTC starts skipping $50 increments in the same direction without filling back, that is the tape acceleration signal.

**Opening drive then retest for crypto:** This is the highest-probability ORB entry variant in crypto because:
- The initial opening drive flushes out weak hands (creates a "false start" perception)
- The retest to the breakout level confirms institutional support
- Tape absorption at the retest = iceberg buyer confirmation
Monitor Hyperliquid order book for large refreshing bids at the breakout level on the retest.

**Bear trend day ORB short:** On confirmed bear trend days, the ORB variant works in reverse. Enter short on the break below the opening range LOW. Use the opening range HIGH as the stop. "When morning low is taken out cleanly, that is the signal to press shorts — not buy dips."

**Leverage guidance:**
- Bull ORB on confirmed trend day: 3-5x leverage on Hyperliquid perps (tight stop at range boundary keeps dollar risk controlled)
- Bear ORB short: same 3-5x, stop above range high
- Gap-and-go: up to 5x leverage if stop is tight (below pre-market support) and catalyst is clear

## Common mistakes (from review transcripts)

- **Jumping the gun before the opening range forms:** Entering before the range completes (< 5 minutes) results in a much lower win rate. Wait for the range to form cleanly.
- **Entering on low-volume breakout:** The highest-volume-bar requirement is not optional. "Volume is the fuel; direction is just the steering wheel." A breakout without the volume bar is a trap.
- **Scalping the ORB on a trend day:** The ORB on a trend day is a trade-to-hold, not a 0.5 ATR scalp. Taking profit too quickly on a trend day ORB is the most common error: "The trader who made $200 vs $2000 on the same setup."
- **Ignoring pre-market internals setup:** If the overnight session has not broken above the balance zone and held, the ORB has less conviction. Always check pre-market context before the open.
- **Not setting alerts at key levels:** "The elite traders are thinking about what to buy, how to buy it, how to add — you can't be figuring this out when it hits." Pre-define the ORB level the night before and set alerts.
- **Holding through contradictory news without adjusting stop:** If a contradictory headline arrives after the ORB entry, tighten the stop to break-even immediately.

## Example(s)

**BTC Bull Trend Day ORB (US Cash Session Open):**
- Context: CPI miss confirms disinflationary trend. Overnight: BTC broke above $67,500 overnight balance high and held.
- 13:30 UTC (09:30 ET): US session opens. First 15-min range forms: low $68,100, high $68,600. Range height = $500.
- Internals: CVD trending positive, top-100 breadth 74/100 positive, funding rising (positive).
- 13:45 UTC: BTC breaks above $68,600 on a volume bar that is 4.2x the prior 15-min bars. ORB confirmed.
- Entry: $68,650 (breakout close). Stop: $68,100 (range low). Risk: $550.
- Measured move T1: $68,100 + $500 = $68,600 (range high) + $500 = $69,100.
- Add: Light-volume VWAP pullback at 14:30 UTC ($68,800). Add 40% more.
- Trail: 21 EMA on 2-min chart. Exit at 19:30 UTC at $71,200 when 21 EMA breaks.
- Total gain on combined position: ~$2,550 from original entry. R:R on initial: 4.6:1.

**BTC Bear Trend Day ORB (Regulatory Shock):**
- Context: SEC enforcement action pre-market. BTC gaps down to $58,000, below prior week's support at $61,000.
- Internals: CVD making new lows, breadth 8/100 positive, funding -0.04%.
- 13:30 UTC: US open. First 30-min range: high $58,800, low $57,900. Range height = $900.
- 14:00 UTC: BTC breaks below $57,900 on the highest volume bar of the session. Short ORB confirmed.
- Entry: short at $57,850. Stop: $58,800 (range high). Risk: $950.
- T1: $57,900 - $900 = $57,000. T2: $56,100. Runner trail via 5 EMA on 5-min.
- Final exit at EOD: $55,200 (CVD still declining at close).
