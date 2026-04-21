# Pullback at VWAP

**Category:** pullback_in_uptrend  **Timeframe:** scalp  **Confidence:** high  **Venues:** HL perps, Binance spot, Binance futures

**Adapted from:** 3_trade_examples_using_our_most_effective_trading_indicator_-_Reading_the_Tape.transcript.md, AM_Meeting_March_6th.transcript.md, AM_Meeting_March_9th.transcript.md, AM_Meeting_May_3rd.transcript.md, Dip_Rip_Trading_Strategy_On_Disney_DIS_Stock.transcript.md, Every_Trader_Faces_THIS_Issue_how_to_overcome_it.transcript.md, How_to_Buy_Market_Pullbacks.transcript.md, How_To_Translate_A_Trade_Idea_Into_A_Profitable_Plan.transcript.md, How_to_use_VWAP_to_buy_a_Pullback_in_a_Meme_Stock.transcript.md, How_to_use_a_key_piece_of_information_Institutional_Ownership_when_stock_trading.transcript.md, How_This_Independent_Retail_Trader_Went_From_Losing_Money_To_Trading_Profitably.transcript.md, How_to_profit_from_oversold_stocks_reading_the_tape.transcript.md, How_to_Scalp_Like_an_Elite_Prop_Trader_Inside_Look.transcript.md, Learn_how_to_use_two_effective_trading_indicators_VWAP_AVWAP.transcript.md, Moving_Average_Trading_Tutorial_For_Day_Trading.transcript.md, PlayBook_Checkup_Uptrend_Continuation_after_Strong_Opening_Drive_AOL.transcript.md, Seasoned_Prop_Traders_Secret_Indicator.transcript.md, The_Biggest_Hidden_Key_In_Trading.transcript.md, This_Weeks_Best_Stock_Trades_from_the_SMB_Capital_Desk.transcript.md, Trading_Volatile_Markets_Is_Hard_Until_You_See_This.transcript.md, Two_Essential_Indicators_For_Trading_SPY_With_Edge.transcript.md, Using_the_VIX_to_Position_Size_a_VWAP_Trade.transcript.md, Using_Unusual_Trading_Volume_to_Find_a_Profitable_Gap_and_Go_and_PullBack_Trade.transcript.md, Why_Did_One_Trader_Make_200_and_Another_2000_on_the_Same_Setup.transcript.md, Why_Simple_Strategies_Are_Money_Machines.transcript.md, amzn_and_fb.transcript.md, SMB_Futures_Morning_Trading_Webcast_February_22nd.transcript.md

## Preconditions

- Primary trend is up on the reference timeframe (5m/15m for scalp; daily for swing)
- VWAP is sloped upward — flat or declining VWAP disqualifies the setup
- Asset has made an opening drive or a clear momentum leg above VWAP
- Pullback to VWAP is on contracting volume (healthy, not distribution)
- In crypto: funding rate neutral-to-positive; not spiking against trade direction
- Institutional ownership proxy (whale wallets, large on-chain bids) supportive for spot plays

## Entry trigger

1. Price touches or micro-penetrates VWAP and immediately re-bids (the "stuff-and-rubber-band" turn)
2. Tape confirmation on HL order book: bids stepping up at VWAP, offer side thinning
3. First green 1m/5m bar that closes back above VWAP after the touch
4. For meme/high-beta assets: require relative strength vs BTC ≥ 3% as additional filter
5. Enter at the re-bid level; do not wait for the next candle to confirm — momentum entries lose R on delay

## Invalidation

- Price closes a 5m bar below VWAP with expanding volume (sellers in control)
- VWAP angle flattens or turns down
- Two consecutive 5m closes below VWAP
- Tape shows persistent offer hits with no bid absorption at VWAP

## Targets

- T1: Intraday high / high of day (50–60% of position off here)
- T2: Prior swing high or 1–1.5 ATR above entry (trail remainder)
- Trail using 9 EMA on 1m or 5m once T1 is hit
- VIX/IV-scaled sizing: base size × (30-day BTC IV / 10) for perp position

## Sizing notes

- Standard size on VWAP pullback with catalyst present
- Reduce to 50% size on low RVOL days (RVOL < 1.2×)
- Full conviction size (1.5–2× base) only when: catalyst + VWAP slope up + tape absorption + relative strength vs BTC all confirm simultaneously
- Risk is the VWAP level itself (stop 2–5 bps below VWAP low), allowing larger notional size for same dollar risk

## Crypto adaptation notes

- VWAP resets at midnight UTC for daily session; for multi-session continuity use anchored VWAP from the catalyst date (listing, protocol upgrade, ETF approval) via TradingView
- US crypto session: 9:30 AM–4 PM ET; Asia session: 8 PM–4 AM ET; EU session: 3 AM–10 AM ET — each session has its own VWAP; pullbacks to the current session VWAP are the most reliable
- Hyperliquid order book: look for bid-side refresh at VWAP level with consistent ticket sizes — institutional sign; erratic small bids = retail noise
- Cumulative delta divergence: if price is at VWAP but delta is trending negative, skip the long
- Negative funding during pullback to VWAP = crowded short = higher-probability long (shorts paying)

## Common mistakes (from review transcripts)

- Entering during the pullback leg itself (buying the give, not the go) — wait for the re-bid signal
- Taking full profit at VWAP touch instead of letting T1/T2 run — use 60/40 or 50/50 partial exit rule
- Ignoring VWAP slope: flat VWAP = range, not trend — do not use this setup in range-bound markets
- Chasing after price is already 0.5+ ATR above VWAP — the entry is at VWAP, not above it
- Over-trading: 3-strike rule — after three failed VWAP bounces on same instrument in one session, stop trading it

## Example(s)

**BTC/USDC perp (HL), trend day post-ETF approval:**
- BTC gaps up at session open; opening drive to 104,500; VWAP established around 103,200
- Price pulls back to 103,200 on 30% lower volume than the drive leg
- HL order book shows 5 bids refreshing at 103,150–103,200 totaling 8 BTC each tick
- First 5m green candle closes at 103,300 — enter long at 103,280, stop 103,000 (below VWAP low)
- T1: 104,500 (intraday high) — exit 60%
- Trail 9 EMA on 1m for remainder; exit when 9 EMA breaks below close

**CLOV/USDC perp (HL), high relative strength day:**
- CLOV showing +3% vs BTC on the same 1h candle
- VWAP at 0.085; price dips to 0.0848 on low volume
- Re-bid appears; first green 5m bar closes at 0.0852 — enter
- Stop: 0.0840 (below VWAP wick); T1: prior HOD 0.0920
