# Opening Range Breakdown Short

**Category:** opening_range_breakout  **Timeframe:** scalp/intraday  **Confidence:** high  **Venues:** Hyperliquid perps, Binance USDⓈ-M futures
**Adapted from:** Do_this_one_thing_to_increase_your_trading_profits.transcript.md, How_Independent_Trader_MelanieNix1_is_Improving_Her_Trading_Ex_Opening_Drive_MU.transcript.md, One_Tape_Reading_Exit_Strategy_Every_Trader_Must_Add.transcript.md, SMB_Setups_Make_Them_Yours.transcript.md, The_ORB_Strategy_High_Odds_Breakout_Technique.transcript.md, How_to_trade_the_open.transcript.md, The_Ultimate_Trend_Day_Trading_Course_For_Beginners_Developing_Traders.transcript.md, livefromthefloorsept30thflv.transcript.md, The_Overlooked_Signal_That_Catches_Massive_Downside_Moves.transcript.md, How_to_spot_scalping_opportunities_in_these_markets.transcript.md, Quick_profits_on_the_open_from_Tape_Reading.transcript.md, Trading_from_today_SPY_VXX_SBUX_CODX.transcript.md, Trader_Missing_Key_Ingredient_to_Make_Money.transcript.md

## Preconditions

- Asset has a quantifiable **opening range** defined in the first 15–30 minutes of a major session open (same session definitions as the long playbook).
- **Catalyst or relative weakness driver present**: news miss, token unlock, leadership departure, regulatory action, strong BTC downtrend dragging the asset, or sector-wide selling.
- **Market context confirms short bias**: BTC intraday downtrend OR broad crypto breadth negative (majority of top 100 coins down). Do NOT short an individual altcoin that is breaking down if BTC is in a strong uptrend — avoid fighting the tide.
- **Relative weakness confirmed**: The asset should be breaking down while its correlated basket holds or is less weak. If BTC drops 1% and the target drops 3%, that is meaningful relative weakness — ideal for the short.
- RVOL ≥ 1.5× confirms participation; low-volume breakdowns are traps (short-sellers get squeezed).
- HTF (daily/weekly) must show no immediate major support within 0.5 ATR of the ORL; otherwise target compression kills the trade.

## Entry trigger

**Primary (ORL break):** Enter short on a candle that **closes** below the opening range low (ORL) with expanding volume. Do not short a price touch — wait for the bar close below the level.

**Tape-confirmation filter:**
1. At the ORL: bids **drop away** — the bid wall that was holding the level disappears without refreshing.
2. Tape shows **offer cascade**: consecutive prints at the bid, spread widens on the downside (sellers are urgently hitting bids).
3. "Bid pull" signal: a large identified bid at the support level (e.g., $38.90 in the MU example from MelanieNix1 transcript) stops refreshing → that is the trigger, not the price alone.

**Opening drive short (gap-down variant):** If the asset **gaps down** at the open and bids drop immediately on the first print:
- Enter short at market on the first candle if tape shows immediate bid-dropping with no absorption.
- This is the highest-urgency entry — "the best entry happens right on the open" — but requires pre-defined stop placement before the candle closes.
- If the first print holds (bids absorb) — do NOT short; the setup has failed before it started.

**If-Then execution (pre-defined):** Before the session open, define the ORL level. IF price breaks below ORL on first 5-min close AND tape shows sellers in control THEN enter short with 1/3 initial size, reserve 2/3 for adds on confirmed continuation.

## Invalidation

- Price **reclaims** the ORL (closes above it) after the break — immediate cover. This is the highest-probability false-breakdown signal.
- Bids **re-appear** at the ORL level with size and price immediately bounces — a "flush-and-rebid" reverse setup; do not add short, cover and re-assess.
- Broader market (BTC) reverses to the upside during the trade.
- Tape shows large buyer absorption below ORL (large block buys hitting the offer at the breakdown level — institutional accumulation, not capitulation).
- Volume dries up on the continuation lower (breakdown on thin volume = likely to be bought).
- Stop: placed above the ORL (a few ticks above the breakout bar high for aggressive entry) or above the first failed re-test of ORL from below.

## Targets

- **T1:** Measured move = opening range height subtracted from ORL. Cover 25–33% here.
- **T2:** 1 ATR below ORL or next major daily support. Cover another 25–33%.
- **Runner:** Trail with 9 EMA on 1-min or 5-min chart. Exit on first close **above** the trailing EMA (price recovered momentum). On confirmed bear trend days (VOLD < 0.33:1, ADD pinned negative, cumulative TICK trending down), hold the runner to end of session.
- **Scale-add on re-test:** If price bounces to the ORL from below and fails to reclaim it (re-test of former support, now resistance), add to the short at that level. This is the second-best entry — lower risk than the initial breakdown.
- **Exit early if:** Decline becomes parabolic (near-vertical drop, multiple ATR in minutes). Parabolic drops exhaust fast; cover into the acceleration. — *One_Tape_Reading_Exit_Strategy.transcript.md*: "Too steep means exit — if the drop becomes parabolic you cover."

## Sizing notes

- Base size: 50% of maximum for standard ORL breakdowns.
- Upgrade to 75–100% when: (a) RVOL > 3×, (b) clear negative catalyst ≥ 7/10 severity, (c) HTF breakdown context (daily/weekly support broken), (d) market internals confirm (BTC downtrend + negative breadth), (e) relative weakness vs. BTC strong (e.g., alt down 4% when BTC flat).
- Downgrade or skip when: (a) breakdown on thin volume, (b) BTC in uptrend, (c) no catalyst driving the breakdown, (d) stock near major historical support (HTF).
- Use `core/allocator.py` for all sizing. Grade the trade and pass to allocator.
- A-grade: all preconditions met, strong catalyst, high RVOL, market aligned → allocator grade = A.
- B-grade: partial confirmation → B.
- Avoid: technical-only breakdown against the BTC trend.

## Crypto adaptation notes

**Session translation (same as long, reversed):**
- **US session ORL breakdown:** Most reliable at 13:30–14:00 UTC. Watch the first 15-min low; if price breaks below it on the 5-min close with volume, short.
- **Asia session breakdown (00:00–01:00 UTC):** Thinner liquidity — require RVOL > 2.5× to compensate for noise and stop hunts.
- **EU session breakdown (08:00–09:00 UTC):** Medium reliability. Often sets the tone before NY open. Can be continuation of Asia breakdown or fresh EU-session catalyst.
- **Pre-market (Asian session) low:** The Asian session low (00:00–08:00 UTC) serves as the pre-market low for the US session. A break below the Asian session low at 13:30–14:00 UTC = opening drive short signal.

**Tape on Hyperliquid for shorts:**
- Watch the order book for bid walls at the ORL. When a large identified bid ($X notional) stops refreshing = entry signal.
- "Offer cascade": sells hitting the bid in rapid succession, spread widens to the downside, no meaningful re-bids.
- Large liquidation prints (visible in trades feed) at ORL = institutional forced selling, not voluntary — momentum will be strong but brief. Cover 50% quickly, hold rest for VWAP.
- **Funding rate check:** If funding is deeply negative (shorts paying longs), the breakdown may reverse sharply as shorts cover simultaneously. Use tighter stops and take profits faster when funding < -0.05% per 8h.

**BTC + alt confirmation:**
- Require BTC to break ITS ORL simultaneously or within 1 candle for maximum confidence on altcoin shorts.
- If BTC is holding/rising but a single altcoin breaks its ORL — this may be idiosyncratic (token-specific catalyst) which can still work but is lower confidence; reduce size by 30%.

**Avoid shorting:**
- Tokens at major psychological support (round numbers: $1, $10, $100) without strong evidence of support failure. These attract heavy buying.
- Tokens with deeply negative funding (> -0.1% per 8h) — the short is already crowded.
- Any asset immediately at a known HTF demand zone visible on the daily/weekly chart.

## Common mistakes (from review transcripts)

1. **Shorting into a runaway downtrend on the open without a defined stop.** Junior traders blow up by taking correct directional shorts at the wrong size. Even if directionally right, overleveraged short positions blow up on adverse intraday bounces. — *A_Profitable_Trade_Two_Junior_Traders_Should_Not_Have_Made.transcript.md*
2. **Using price level as entry trigger instead of tape confirmation.** The entry is triggered by the bid disappearing at the level, not by price alone. — *How_Independent_Trader_MelanieNix1.transcript.md*: "Wait for the 38.90 buyer to disappear on the tape."
3. **Covering too quickly when the decline becomes orderly.** Parabolic drops deserve a quick cover, but steady directional declines should be held to at least T1. Define the exit type before entry (trail EMA or fixed level).
4. **Not sizing down in volatile markets.** In high-VIX / high-crypto-volatility environments, the same setup requires 30–50% reduced size to keep dollar risk constant.
5. **Shorting after the opening drive has already produced 2+ ATR.** By the time the move is obvious, most of it is done. Entry at ORL is the opportunity; entering 2 ATR below ORL is chasing.
6. **Ignoring BTC direction.** Shorting an altcoin breakdown while BTC is in an uptrend is fighting the primary trend. Most such shorts fail or produce small gains.

## Example(s)

**Example 1 — ETH US session ORL breakdown (template):**
- 13:30 UTC: ETH opens at $3,200 after bearish macro headline (CPI hotter than expected).
- 13:30–14:00 UTC: ETH ranges $3,150–$3,250 (ORL = $3,150; ORH = $3,250; range = $100).
- RVOL at 14:00 UTC: 2.2× 20-day average.
- 14:05 UTC: ETH closes a 5-min bar at $3,140, below ORL. Volume on this bar is highest of session. Tape: bid at $3,150 pulls; offer cascade hits $3,140.
- Entry: $3,138 (below breakout bar low) or at close of breakdown bar.
- Stop: $3,165 (a few ticks above ORL; the bid was at $3,150, stop above failed re-test zone).
- T1: $3,150 − $100 = $3,050. Cover 33%. (Risk = $27; T1 reward = $88 → 3.3:1)
- T2: $2,980 (1 ATR below ORL). Cover 33%. Runner trails 9 EMA 1-min.

**Example 2 — Opening drive short, gap-down token (Hyperliquid):**
- Alt token listed on Hyperliquid, token unlock event causing gap-down. Opens at $0.80 after closing prior session at $1.00.
- First tick: bids drop immediately at $0.80. No absorption visible in order book.
- Enter short at $0.798 (first candle). Stop: $0.815 (above opening print).
- T1: $0.75 (prior support). Cover 50%.
- T2: $0.72. Trail remainder on 9 EMA 1-min.

**Example 3 — Pre-market high short (failed open drive, BTC):**
- BTC Asian session range: $97,000–$98,500 (Asian session high = $98,500).
- At 13:30 UTC (NY open), BTC attempts $98,500 and fails — tape shows large offer refreshing.
- First 15-min range forms: $97,800–$98,200 (ORL = $97,800).
- 14:05 UTC: BTC closes below $97,800 on high volume. BTC internals (crypto breadth) confirming.
- Short entry: $97,760. Stop: $98,050 (above ORH). T1: $97,200 (1 ATR). T2: $96,800 (next daily support).
