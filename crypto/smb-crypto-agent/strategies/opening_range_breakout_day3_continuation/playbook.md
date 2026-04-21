# Opening Range Breakout — Day 3 Continuation

**Category:** opening_range_breakout  **Timeframe:** intraday/swing  **Confidence:** high  **Venues:** Hyperliquid perps, Binance spot/futures
**Adapted from:** Elite_Prop_Traders_High_Odds_Breakout_Technique_Step-by-Step_Instructions.transcript.md, How_to_Time_Exact_Entries_Exits_Bar-By-Bar_Analysis.transcript.md, How_This_Trader_Started_Making_7-Figures.transcript.md, Bar_by_Bar_Analysis_of_5_Simple_Trades.transcript.md, Two_Traders_Two_Different_Trades_Same_Stock.transcript.md, The_Opening_Drive_Momentum_Trade_reading_the_tape.transcript.md, Top_10_Gap_Trading_Mistakes_You_Must_Avoid.transcript.md, Scalping_An_Effective_And_Highly_Profitable_Trading_Strategy_part_II.transcript.md, The_Trading_Floor_SMB_Capital_Podcast_Episode_2.transcript.md, Using_Unusual_Trading_Volume_to_Find_a_Profitable_Gap_and_Go.transcript.md

## Preconditions

The Day 3 continuation is a **multi-session pattern** built on three specific day behaviors. It is distinct from the single-session ORB because it requires reading the character of the prior two sessions before entry. All three days must fit the prescribed pattern.

**Day 1 requirements (catalyst day):**
- Strong fundamental catalyst (token listing, protocol upgrade, partnership, macro event).
- Large move: +20% or more preferred (or equivalent in BTC: +3–5% on a single session).
- RVOL on Day 1: typically 5–20× baseline. The higher the better.
- **Close:** Must close in the **top 25–33% of Day 1's range** (strong close = buyers in control going into overnight hold). A weak close (bottom half of day's range) invalidates the Day 3 setup.

**Day 2 requirements (accumulation / inside day):**
- Day 2 is a **low-volume inside day** (consolidation): daily range smaller than Day 1's range, and volume drops to 30–50% of Day 1 volume.
- Price holds above a defined key level from Day 1 (typically Day 1's afternoon support, Day 1 close, or session VWAP).
- This day **traps chasers, gives shorts confidence, and lets institutional buyers accumulate at controlled prices.** The trap is intentional — it creates the fuel for Day 3.
- Do NOT enter on Day 2 even if the setup looks quiet. This is accumulation; the move is not ready yet.

**Day 3 requirements (breakout day):**
- **Gaps higher** than Day 2's high (or at minimum opens above Day 2's close).
- Breaks above **Day 2's high within the first 30 minutes** of the session with volume expansion.
- Day 3 RVOL should reaccelerate vs Day 2 (at minimum 2× Day 2 volume in the first 30 minutes).
- Higher timeframe (weekly chart) resistance is checked but does not invalidate — Day 3 breakouts can blow through HTF resistance on momentum if RVOL is extreme.

## Entry trigger

**Tier 1 — Feeler entry (pre-breakout):**
- At the open of Day 3, price pulls back to a pre-session support level (Day 2 close area, or after-hours support band).
- Buyers step in with tape confirmation (bids absorbing offers at the support level).
- Enter 25% of max intended size as a feeler. Stop: Day 3 session low.

**Tier 2 — Primary entry (volume-confirmed breakout above Day 2 high):**
- Break above Day 2 high on the **highest-volume bar of Day 3's session so far**.
- Tape confirms: offers at Day 2 high are lifted aggressively; price skips levels above the breakout.
- Add to 75–100% of intended size at this point. Stop adjusts to: Day 3 session low or 1% below Day 2 high (use the tighter of the two).

**Tier 3 — Consolidation add (Big-Dog wedge):**
- After the initial break of Day 2 high, price often consolidates in a tight ascending wedge or flag above VWAP.
- When this consolidation breaks to the upside with volume (Big-Dog consolidation breakout), add another 25% if not at max size.
- This is typically the 11:30 AM–1:00 PM ET (17:30–19:00 UTC) consolidation on US session setups.
- "Big-Dog consolidation add: when a stock breaks out and then consolidates in a tight range (wedge) above VWAP and the Day 2 breakout level, that consolidation is a low-risk add point." — *How_This_Trader_Started_Making_7-Figures.transcript.md*

**Timing rule:** "One entry, one stop, and you leave the position alone and let it work." Once the primary entry is established on the Day 2 high break, do not constantly re-evaluate — manage with the trail stop only.

## Invalidation

- Day 3 fails to break Day 2 high within the **first 30 minutes** of the session. If price is still below Day 2 high at the 30-minute mark with declining volume, the Day 3 setup is invalid for that session. Stand aside.
- Day 2 high is tested but **volume does not expand** on the break (volume below Day 2's average bars). This is a false Day-3 break; reduce to feeler only and wait for volume to confirm.
- Price breaks Day 2 high then **immediately reverses** back below it within 1–2 bars. Failed Day 3 setup; exit all positions.
- Session low of Day 3 is violated with volume — stop hit, full exit.
- Higher timeframe check: if the weekly chart shows a major multi-year resistance level within 0.5 ATR of the breakout target, be aware it may stall there. It does not invalidate entry but suggests taking at least 50% off at that level.

## Targets

- **Initial momentum scale:** Sell 25–33% into the first momentum surge after Day 2 high breaks. This locks in profit on the portion with the highest risk.
- **Trail on 2-min 9 EMA:** For the remaining 50–75% of position, trail the 9 EMA on the 2-min chart. Exit on first 5-min close below 9 EMA.
- **Always hold 10–20% as a swing piece:** If Day 3 closes strongly (top 25% of day's range) and RVOL remains elevated, hold the swing piece overnight for Day 4 continuation. Exit the swing piece on VWAP break on Day 4 open.
- **5:1 benchmark:** If initial risk is X (stop distance), the full move target is 5X. Day 3 setups on high-RVOL assets commonly produce 3–8× risk:reward.
- For crypto tokens with very high RVOL (> 10×) and low float (low circulating supply), the Day 3 move can be 3–10× Day 1's initial ATR. Scale exits aggressively above 3× initial risk.

## Sizing notes

- Day 3 is among the highest-conviction setups in this playbook when all three day conditions are met.
- Feeler (Tier 1): 25% of max allocated by `core/allocator.py`.
- Primary (Tier 2): bring to 75–100% of max on confirmed break of Day 2 high with top-2 volume bar.
- Big-Dog add (Tier 3): only if current position is below max allowed; add 25% within max limit.
- If the Week 1 playbook review (backtested on similar tokens) shows Day 3 setups have > 65% win rate on the specific asset class (high-RVOL micro-cap tokens), grade as A-trade for max sizing.
- Grade: A = Day 1 close in top 25% + Day 2 inside/low-volume + RVOL reaccelerates on Day 3. B = 2 of 3 conditions. C = only Day 2 inside day without strong Day 1 catalyst.
- All sizing via `core/allocator.py`.

## Crypto adaptation notes

**Why Day 3 works exceptionally well in crypto:**
- Crypto markets lack overnight halt mechanics. However, the three-day pattern still works because:
  - Day 1 euphoria creates a crowded short-term long position.
  - Day 2 consolidation shakes out weak longs (sells into strength) while smart money accumulates.
  - Day 3 squeeze launches because the combination of accumulated institutional longs + shaken-out weak hands + new catalyst buzz creates explosive buying.
- For crypto, "sessions" can be defined as calendar days (00:00–23:59 UTC) or by major session opens. The three-day pattern is visible most clearly on the **daily chart**.

**Crypto-specific Day 3 triggers:**
| Day 1 catalyst | Day 2 behavior to watch | Day 3 trade |
|---------------|------------------------|-------------|
| CEX listing announcement | Inside candle, RVOL drops 60%+ | Break of Day 2 high in first session candle |
| Protocol mainnet launch | Holds above listing price / Day 1 close | ORB above Day 2 high range |
| BTC halving day | Day 2 choppy/flat | Day 3 ORB with reaccelerating volume |
| ETF approval | Day 2 pullback to 50% retrace holds | Day 3 gap above Day 2 high |
| Treasury strategy (e.g., MSTR analog for protocol) | Day 2 slight fade into Day 1 support | Day 3 break above Day 2 high |

**Session timing for Day 3 break:**
- The "first 30 minutes" rule maps to the **13:30–14:00 UTC window** for US session Day 3 setups.
- For crypto-native 24/7 setups, use the **00:00–00:30 UTC** window (daily candle open) as the equivalent.
- If the break above Day 2 high occurs at 08:00 UTC (EU session) rather than 13:30 UTC, that is still a valid entry — just note it may be thinner liquidity and adjust size by 20%.

**Float / supply analog for crypto:**
- High short interest (equity) maps to: (a) very negative funding rate (heavy short positioning on perps), or (b) high short open interest vs long OI on Coinglass.
- Low float (equity) maps to: low circulating supply tokens (small cap relative to market cap, large treasury / foundation lock-up). These produce the most explosive Day 3 squeezes.
- Verify on Coinglass: if short OI is > 60% of total OI going into Day 3, the squeeze potential is maximum.

**4h and daily timeframe variant:**
For longer-hold setups (swing), use 4h candles instead of daily:
- Day 1 = first 4h candle with catalyst (strong close).
- Day 2 = next 4h inside candle (consolidation).
- Day 3 = third 4h candle breaking above Day 2 candle high.
- Same entry, target, and stop logic applies at the 4h level. Position for 2–5× the 4h ATR.

## Common mistakes (from review transcripts)

1. **Entering on Day 2 because "it looks quiet."** Day 2 is a trap — both sides are getting trapped. Entry on Day 2 is too early. The setup triggers on Day 3. — *Elite_Prop_Traders_High_Odds_Breakout_Technique.transcript.md*: "Day 2 inside/low-volume consolidation traps chasers, gives shorts confidence, lets smart money accumulate."
2. **Not checking the higher timeframe resistance.** Even on valid Day 3 setups, a major weekly resistance level within 0.5 ATR of the target can cap the move. Be aware and plan partial exits before that level.
3. **Not holding any swing piece.** Day 3 setups that work often continue for Day 4. Traders who exit 100% on Day 3 miss the compounding. Always hold 10–20% as the swing runner.
4. **Over-sizing the feeler and under-sizing the primary.** The feeler is de-risking; the real money is in the confirmed break of Day 2 high. Size the primary entry (Tier 2) at 2–3× the feeler.
5. **Confusing Day 2 with an outside day.** If Day 2 has a range LARGER than Day 1, it is NOT a Day 2 inside/accumulation day — that condition is violated. The setup requires Day 2's range to be inside or significantly smaller than Day 1's.
6. **Entering when Day 3 volume does not reaccelerate.** Volume on Day 3 must exceed Day 2's volume. If Day 3 is also a low-volume day, the accumulation cycle has not resolved; wait for Day 4.

## Example(s)

**Example 1 — Token listing Day 3 (Hyperliquid, daily timeframe):**
- Day 1: New DeFi token lists on Hyperliquid. Opens at $1.00, closes at $1.85 (top 20% of day's range). RVOL: 15×.
- Day 2: Opens at $1.85, ranges $1.70–$1.92. Volume drops to 40% of Day 1. Inside day confirmed. Closes at $1.80.
- Day 3: Opens at $1.95 (gap above Day 2 high of $1.92). RVOL reaccelerates to 3× Day 2 volume.
- Feeler entry: $1.90 (pre-session support). 25% size.
- 13:40 UTC: break above Day 2 high $1.92 on highest-volume bar of Day 3. Primary entry: add to 75% total.
- Stop: $1.72 (Day 3 session low).
- T1: $2.20 (first resistance, 33% off). T2: $2.55 (Day 1 range projected). Swing piece: trail 9 EMA 2-min until 5-min close below.

**Example 2 — BTC halving Day 3 setup (4h variant):**
- Halving event occurs. BTC 4h candle at event: +6%, closes at $65,000 (strong close).
- Next 4h candle: inside (ranges $63,500–$65,200 vs prior candle range of $61,000–$65,000). Volume drops 55%.
- Third 4h candle: opens at $65,400, breaks above prior inside candle high ($65,200) on 2.5× volume vs inside candle.
- Entry at $65,300 (feeler) and $65,250 (add on confirmed break). Stop: $63,800 (Day 2 candle low).
- T1: $67,400 (1 ATR from entry). T2: $70,000 (psychological and ATH proximity). Swing runner to next 4h close below 9 EMA.

**Example 3 — Protocol upgrade Day 3 (ETH, US session):**
- Day 1: Major Ethereum upgrade goes live. ETH +8%, closes at $3,800 (top 30% of day range). RVOL: 8×.
- Day 2: ETH ranges $3,680–$3,830 (inside Day 1's range). Volume drops to 35% of Day 1. Closes at $3,760.
- Day 3: ETH opens at $3,870 (above Day 2 high $3,830). 13:40 UTC: 5-min close above $3,830 on highest-volume bar.
- Short OI on Coinglass is 58% of total OI (shorts crowded, squeeze risk high).
- Feeler: $3,850. Primary: $3,840 on confirmed volume. Stop: $3,720 (Day 3 session low). T1: $4,100 (Day 1 range added to Day 2 high). T2: $4,350. Runner: trail 9 EMA 2-min. Swing: hold 15% overnight.
