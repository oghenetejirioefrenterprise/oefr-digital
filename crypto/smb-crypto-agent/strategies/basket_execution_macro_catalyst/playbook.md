# Macro Catalyst Basket Execution
**Category:** basket_execution  **Timeframe:** scalp/intraday  **Confidence:** high  **Venues:** Hyperliquid perps, Binance USDⓈ-M futures
**Adapted from:** 10_Key_Strategies_to_Trade_an_Economic_News_Release.transcript.md, Creating_a_Basket_of_Stocks_to_Seize_a_Special_Trading_Opportunity.transcript.md, How_to_Trade_a_Fed_Announcement.transcript.md, How_to_Trade_one_of_the_Biggest_Opportunities_in_the_Market.transcript.md, Prop_Trader_Reveals_His_EXACT_Entries_Exits_Bar-by-Bar.transcript.md, SMB_AM_Meeting_Commentary.transcript.md, Trumps_Trade_War_-_How_traders_can_win_it.transcript.md

## Preconditions
- Known macro catalyst imminent: CPI, FOMC, NFP, Fed announcement, major geopolitical headline, trade policy statement.
- Directional bias for each scenario pre-mapped (bull / bear / neutral game plan) before the release.
- Basket pre-built and keyed up: primary asset + correlated assets sized and staged so execution is one action, not a sequence of decisions.
- Morning trend direction known — counter-trend headlines produce the largest dislocations and the sharpest basket entries.
- Crypto basket composition confirmed: BTC perp (primary), ETH perp (secondary), SOL perp or sector ETF proxy (tertiary). Vol proxy (BVIV or implied vol product) staged as a hedged short when available.

## Entry trigger
**Leg 1 — Headline entry:** On headline confirmation, simultaneously enter the full basket within 30 seconds of the print. Direction:
- Risk-on catalyst (rate cut, trade deal, dovish pivot, macro beat): long BTC perp + long ETH perp + short vol proxy.
- Risk-off catalyst (tariff escalation, hawkish surprise, macro miss): short BTC perp + short ETH perp + long vol proxy.

**Leg 2 — VWAP pullback add (intraday only):** After the initial pop/drop, if price pulls back to VWAP on declining volume and then reclaims VWAP on expanding volume within the same session, add risk across the basket. This second leg often provides better average entry and confirms trend day development.

## Invalidation
- Price fails to follow through in the expected direction within 5 minutes of the headline.
- Price reclaims VWAP against thesis (for longs: price breaks VWAP and stays below; for shorts: price reclaims VWAP).
- Contradictory headline negates the original catalyst.
- For Leg 2 add: VWAP reclaim fails to hold on two consecutive 2-min bars.

## Targets
- **Leg 1:** 1–2 ATR initial impulse move; scale out 25% per leg.
- **Leg 2 (trend day development):** Trail with 15-min 20 EMA; hold until trendline break, vertical acceleration exhaustion, or contradicting headline.
- **Scalp-only context:** Close at session highs/lows; exit if no clean trend continuation by 30 minutes post-catalyst.
- On strong trend days (TICK holding directional bias all session): trade to hold, not scalp — hold core through session close.

## Sizing notes
- Basket sizing is set before the event — do not adjust size in the 60 seconds surrounding the release (decision latency = slippage).
- Leg 1: full intended risk deployed simultaneously across all basket legs.
- Leg 2 add: add 50–100% of Leg 1 size if trend day signals confirm (sustained directional order flow, funding rate moving with thesis).
- Hyperliquid perps: account for funding rate spikes post-catalyst — a funding spike in the direction of the trade is a trend confirmation signal, not a reason to reduce.
- Maximum loss defined before entry (total premium / margin at risk across all legs); if market goes wrong-way immediately and holds, exit full basket, do not leg out.

## Crypto adaptation notes
- CPI, FOMC, and NFP move crypto directly and with minimal lag vs equities. BTC, ETH, SOL are the functional equivalent of SPY/QQQ/sector ETFs.
- BTC dominance direction is a real-time intra-basket signal: if BTC dominance rises alongside BTC price, altcoin legs (ETH, SOL) will lag — reduce altcoin sizing relative to BTC leg. If dominance falls while BTC rises, altcoins will outperform — increase altcoin legs.
- Positive funding rate surge post-catalyst on HL perps = confirming signal for trend continuation; do not exit early on funding cost fear during high-conviction trend days.
- Vol proxy: if BVIV or an options product is unavailable, use inverse correlation with a high-beta altcoin position (short a high-beta alt on risk-off, long on risk-on) as a partial vol substitute.
- Simultaneous HL + Binance execution: use HL perps for primary directional exposure (faster fills, lower fees on liquid contracts); use Binance USDⓈ-M for altcoin legs or when HL liquidity is thinner on the chosen asset.
- Token-level news (exchange acquisition, exploit, regulatory action) creates the same risk-arb dynamics as equity M&A: short the acquirer's token, long the target token on announcement.

## Common mistakes (from review transcripts)
- **Waiting for confirmation before executing.** The easy money on basket moves is in the first 30–60 seconds. Waiting for a confirming candle or pattern means entering mid-move at worst risk/reward.
- **Figuring out what to trade when the headline hits.** All basket composition decisions must be made before the event. Any thinking in the moment costs the entry.
- **Being 1–2 minutes late.** Late entries still capture the majority of the catalyst move and are acceptable; being 5+ minutes late chases.
- **Legging out of the basket during the initial move.** The basket should move together. Partial closing of only the strongest leg while holding weak legs creates unintended single-name exposure.
- **Ignoring morning trend direction.** Counter-trend catalyst headlines create the most aggressive moves because trapped traders are forced out. Missing the morning bias = missing sizing opportunity.
- **Exiting the entire position on first profit.** On trend days, the appropriate action is to add (Leg 2), not exit. Scalping a trend day is the most common large missed-profit scenario in the source material.

## Example(s)
**FOMC Dovish Surprise (equity analog → crypto map):**
- Pre-built basket staged: BTC-PERP long 0.5 BTC, ETH-PERP long 3 ETH, vol short (if available).
- Fed headline hits: dovish pivot language. Immediately fill all three legs simultaneously.
- BTC moves +3% in 4 minutes. ETH follows +4%. Vol proxy compresses.
- Leg 1 target reached (1.5 ATR). Scale 25% of each leg.
- VWAP pullback forms 15 minutes later on low volume. Price reclaims VWAP on expanding volume.
- Leg 2 add: increase all legs by 75% of original size. Trail with 15-min 20 EMA.
- Session closes near highs. Exit full basket at session close.

**Trade War Tariff Announcement (risk-off):**
- Morning trend was upward (BTC up 1.2% at 8 AM).
- Tariff escalation headline hits — counter-trend catalyst → expect outsized move.
- Immediately short BTC-PERP + short ETH-PERP. 
- BTC breaks VWAP within 90 seconds. Price holds below VWAP. Thesis intact.
- Scale out 25% at 1 ATR. Hold remainder with trailing stop below 2-min bar highs.
- Exit on any 2-min close back above VWAP.
