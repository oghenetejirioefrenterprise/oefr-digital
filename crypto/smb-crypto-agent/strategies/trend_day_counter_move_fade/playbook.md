# Trend Day Counter-Move Fade
**Category:** trend_day_continuation  **Timeframe:** scalp  **Confidence:** high  **Venues:** HL perps, Binance futures

**Adapted from:** Dont_Fade_This.transcript.md, AM_Meeting_March_22nd.transcript.md, AM_Meeting_March_28th.transcript.md, How_to_PROFIT_from_market_crashes_Survive_Thrive.transcript.md, How_to_Trade_a_Market_Sell_Off.transcript.md, SMB_Trade_of_the_Week_-_SPY.transcript.md, SMB_Trade_of_the_Week_-_VPRT.transcript.md, Top_7_Keys_to_Trade_Profitably_during_The_Coronavirus_Fears.transcript.md, How_to_Make_More_on_Market_News_Trades.transcript.md, How_Short_Term_Traders_Can_Survive_Unprecedented_Volatility.transcript.md, middayreviewflv.transcript.md, Expanding_Volatility.transcript.md, Trading_from_today_in_AXON_QQQ_SJM_VKTX.transcript.md, The_Trend_Trend_Trade_WFM.transcript.md, november1stflv.transcript.md, AM_Meeting_October_11th.transcript.md

## Preconditions

- Trend day confirmed and direction established (see trend_day_recognition_checklist.md)
- Trend direction is DOWN (bear trend day): CVD trending negative, breadth <30% positive, funding going negative
- Price is in a sustained downtrend with VWAP acting as resistance (not support)
- Counter-move (bounce) has occurred — price has rallied 0.3-0.75 ATR from the trend low
- Bounce is occurring on LIGHT volume (sellers stepped back but buyers have no follow-through)
- Context: major negative macro catalyst active (CPI miss, regulatory shock, exchange hack, macro selloff), OR multi-day downtrend with VWAP declining

**Equity → Crypto translations for identifying the setup:**
- "SPY breaks below key support → short any VWAP bounce" = BTC perp loses daily VWAP → fade bounces to intraday VWAP
- "VIX spiking from low levels" = funding rate going deeply negative + realized volatility expanding = bear trend day signal
- "Stocks that can't rally when market bounces are your best shorts" = alts failing to bounce when BTC bounces = short the laggard alt

## Entry trigger

**Primary (VWAP Rejection Short):**
- Price bounces toward VWAP on declining volume (sellers stepped back, weak buyers lifting)
- Tape/order book shows offers refreshing at VWAP: asks stacking, bids not aggressive
- Price touches VWAP and shows rejection (lower high vs prior bounce high, or rejection candle)
- Enter short on: (a) first 5-min close below the VWAP-touch candle's low, or (b) tape shows offer stepping down and bids pulling
- Stop: above VWAP (typically 0.3-0.5 ATR above VWAP is the stop level)

**Secondary (5 EMA Rejection):**
- In a clean intraday downtrend, price bounces to the declining 5-period EMA on 1-min or 5-min chart
- Enter short on first rejection candle off the 5 EMA; stop above prior bounce high
- "Short every retracement to 5-period EMA; stop above prior bounce high" — works as long as trend intact

**Tertiary (FOMC/Macro Anchored VWAP Short):**
- Macro catalyst event occurs mid-session (FOMC, CPI print)
- Anchor VWAP from the exact timestamp of the announcement
- BTC loses anchored VWAP from announcement time
- Short the highest-beta relative weakness alt that is underperforming BTC
- Exit when BTC reclaims its anchored VWAP and builds a higher low

**Morning Range Low Break:**
- On confirmed bear trend day: opening range low (first 30-min low) is the key trigger
- When morning low is taken out cleanly (high-volume break, not a wick), get short and hold
- "When our technicals confirmed weakness below the opening range in SPY at 108.60 we got short" — hold until end of session

## Invalidation

- Price reclaims VWAP and holds above it for 2+ consecutive 5-min bars with expanding volume
- CVD reverses and starts trending positive
- Breadth ratio improves sharply toward neutral (bear thesis weakening)
- New positive headline contradicts the catalyst driving the selloff
- Funding rate normalizes from deeply negative (short squeeze risk increases)
- Price forms a higher low vs the prior intraday low — trend structure weakening

## Targets

- **Trade-to-hold on confirmed bear trend days:** Short the VWAP bounce and hold until market close
- Partial 1 (25-33%): at prior session low or round number support below
- Partial 2 (25-33%): at next major structural support level
- Runner: trail with declining 5 EMA or 15-min lower highs; exit on first close above the 5 EMA
- "You can't cover here — you have to let the stock breathe; give it a chance to find lower ground." Hold through normal noise.
- Anchored VWAP short: cover when index reclaims its anchored VWAP

## Sizing notes

- Full size on VWAP rejection short when all conditions align on confirmed bear trend day
- Reduce size by 30-50% in extremely high-volatility environments (VIX analog >80 crypto fear index, BTC daily ATR >5%): "same expectancy with less risk"
- 5 EMA retracement entries: standard size — these are high-frequency setups on trend days
- Anchored VWAP relative weakness short (shorting an alt vs BTC): size the alt short at 0.5-1x the BTC position equivalent

## Crypto adaptation notes

**VWAP as resistance on bear trend days:** On Hyperliquid BTC perp, VWAP is computed from midnight UTC reset. On strong bear trend days, VWAP slopes lower all session. Every bounce that fails to close a 5-min candle above VWAP = short entry. This is the single most consistent bear trend day pattern.

**Funding rate confirmation for shorts:** On bear trend days, funding rate going negative means longs are being paid to hold — this is bearish. Deeply negative funding (below -0.05% per 8h) signals crowded shorts but also confirms bear trend. Do not fade deeply negative funding on a confirmed bear trend day — the trend usually continues. Use funding reversal (from negative back toward zero) as a warning to cover longs into the bounce, not as a long signal.

**Relative weakness alt short:** When BTC bounces 2% but an altcoin stays flat or falls, the altcoin is showing distribution. Short the laggard. Use BTC-denominated chart (ALT/BTC) to identify the weakest performers. On Hyperliquid, look for perps where funding is least negative (meaning longs are trapped and more willing to hold) — these are the best short candidates on the bounce.

**Anchored VWAP from macro catalyst:** When FOMC or CPI hits: anchor a VWAP from the exact candle timestamp on the 5-min chart. BTC/ETH losing this anchored VWAP → short the most beta-correlated alt that is already showing relative weakness. Cover when BTC reclaims the anchored VWAP.

**Bear trend day vs. volatile choppy day:** The key distinction is CVD behavior. On a bear trend day, CVD makes new lows persistently with no meaningful mean-reversion. On a choppy day, CVD oscillates. Only apply this playbook when CVD is clearly trending down.

**Reducing size in extreme volatility:** "During high volatility, prioritize liquidity (ETFs) over individual names." Crypto equivalent: stick to BTC and ETH perps during extreme fear events. Avoid altcoin shorts during liquidation cascades — they can spike violently on covering squeezes.

## Common mistakes (from review transcripts)

- **Buying the dip on a bear trend day:** "This was not the setup for a buy-the-dip day." The most expensive mistake is treating a bear trend day as an opportunity to buy support. Wait for confirmed reversal signals.
- **Covering too early:** "You can't be a wuss here — let the stock breathe." On strong bear trend days, do not cover into the first bounce. Hold the short until end of session or confirmed reversal.
- **Shorting without VWAP confirmation:** Entering short before price has rallied to VWAP (shorting into the hole) results in poor R:R. Wait for the bounce to VWAP before entering.
- **Fighting deeply negative funding:** Deeply negative funding signals crowded shorts but does NOT mean the trend is reversing — it often means weak longs are being shaken out. Continue with trend until CVD reversal is confirmed.
- **Missing the morning range low break signal:** "When morning low is taken out cleanly, that is the signal to press shorts — not buy dips." Missing this entry and waiting for a better price usually results in chasing a much lower price.

## Example(s)

**BTC Bear Trend Day — VWAP Rejection Short:**
- Macro catalyst: Major regulatory enforcement action announced pre-market. BTC gaps down 4%.
- 09:35 ET: Breadth 12/100 positive, CVD making new lows, funding at -0.04%/8h. Bear trend day confirmed.
- 10:15 ET: First bounce — BTC rallies from $62,000 to $63,500 (VWAP for the session). Volume drying on the bounce.
- Tape: offer wall rebuilding at $63,500. No sustained bid absorption visible.
- Entry: short $63,400 (5-min close below VWAP-touch candle low). Stop: $63,800 (above VWAP).
- 11:30 ET: Partial cover 33% at $62,000 (prior session low).
- 14:00 ET: Second VWAP bounce fails at $63,200 (lower high). Add to short.
- 16:00 ET: Cover final at $61,000 near session close. CVD still declining at close.

**ETH Perp — Anchored VWAP Relative Weakness Short:**
- FOMC surprise (hawkish) at 14:00 ET. ETH loses its anchored VWAP (anchored from 14:00).
- SOL/ETH showing relative weakness — SOL flat while ETH trying to bounce.
- Short SOL perp at $135 (SOL's anchored VWAP rejection). Stop: above $138.
- Cover: when ETH reclaims its anchored VWAP at 15:30 ET. SOL covered at $129. ~4.4% gain.
