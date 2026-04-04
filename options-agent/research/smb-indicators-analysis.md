# SMB Capital Indicators — Deep Analysis for Options Agent Integration
## Date: 2026-04-04

---

## VIDEO SUMMARY
**Source:** "Top 3 Indicators Every New Trader Needs" — SMB Capital (Mike Bellafiore/Garrett)
**URL:** https://youtu.be/J2CP9pO5avE

Three indicators: Volume Z-Score, VWAP, Tape Reading (Level 2 + Time & Sales)

---

## 1. VOLUME Z-SCORE

### Formula
```
Z = (Current Volume - Average Volume) / Standard Deviation
```
- Lookback: 20 trading days
- Bar size: 5-minute (intraday) or daily
- TIME-OF-DAY NORMALIZATION IS CRITICAL: Compare current 5-min bar to the average for THAT SAME TIME SLOT over lookback

### Thresholds
- Z > 2.0: Unusually high volume (SMB's primary alert threshold, ~97.7th percentile)
- Z > 3.0: Extreme institutional activity
- Z > 1.0: Elevated (white bars in SMB's color coding)
- Z < 0: Below average (gray — meaningless noise)

### SMB Color Coding
- Cyan (up) / Magenta (down) / Yellow (directionless): Z > 2.0
- White: Above average but < 2 std dev
- Dark gray: Below average

### Daily Volume Cycle (critical context)
- Surge at open (9:30-10:30): Institutional price discovery
- Drop at lunch (11:30-1:30): Low participation
- Surge into close (3:00-4:00): Close auction, institutional rebalancing
- A few 2-std-dev bars at open and close is NORMAL
- Unusual = high z-score bars OUTSIDE these windows

### Application to Options Agent
**For premium selling (put credit spreads):**
- Volume z-score > 1.5 on SPX/SPY + elevated IV Rank > 40 = optimal entry window
- High volume spikes accompany fear-driven selloffs → IV expansion → rich premiums
- IV mean-reverts after volume spikes = favorable for short premium
- Tastytrade research: entries during high IV Rank (correlated with volume spikes) improve win rates by 10-20%

**Volume as regime filter:**
- High volume + price decline (z > 2): "Capitulation" → excellent for selling puts
- High volume + price advance: "Breakout" → caution on selling calls
- Declining volume with price rise: Weakening trend → favorable for iron condors
- Expanding volume in a range: Breakout imminent → avoid iron condors

---

## 2. VWAP (Volume Weighted Average Price)

### Formula
```
VWAP = Σ(Price × Volume) / Σ(Volume)
```
Cumulative from anchor point (typically 9:30 open for intraday)

### Core Rules (SMB Internal)
1. **Above VWAP = buyers in control** → favor longs/put credit spreads
2. **Below VWAP = sellers in control** → favor shorts/call credit spreads
3. **Chopping around VWAP = no one in control** → range-bound or battle
4. **Failure to reclaim VWAP after losing it = key short trigger**

### SMB Internal Rule (from the video)
One of their top traders (7-8 figure earner) was hemorrhaging money shorting above intraday VWAP. They made it a FIRM RULE: different risk parameters when shorting above VWAP. Now applied firm-wide.

### VWAP Setups
- **VWAP Hold Long:** Stock pulls back TO VWAP + holds + volume fades on pullback + tape shows absorption → buy
- **VWAP Hold Short:** Stock fails to reclaim VWAP from below + volume spikes on rejection → short
- **VWAP Breakdown:** Stock loses VWAP on high volume → consolidates below → failed retest → short

### Anchored VWAP (Brian Shannon)
- Anchor from significant events: earnings, FOMC, major pivot, high-volume day
- AVWAP from a low = SUPPORT (participants are profitable above)
- AVWAP from a high = RESISTANCE (participants are underwater below)
- Multiple AVWAPs converging = STRONG level
- Book: "Maximum Trading Gains with Anchored VWAP" (2023)

### VWAP Standard Deviation Bands
- ±1 SD: 68% of volume transacted here ("value area")
- Price at upper band: favorable for call credit spreads (overextended)
- Price at lower band: favorable for put credit spreads (oversold vs volume)
- Price within bands: favorable for iron condors (range-bound)

### Application to Options Agent
**For put credit spreads:**
- Only sell puts when SPX price > daily VWAP (buyers in control, bullish bias confirmed)
- When price pulls back to VWAP from above during uptrend → optimal PCS entry timing
- Institutional buying emerges at/below VWAP → natural support

**For iron condors / non-directional:**
- Price within VWAP ±1 SD bands = range-bound regime → ideal for selling strangles/condors
- Price outside ±2 SD = trending → dangerous for condors

---

## 3. TAPE READING (Level 2 + Time & Sales)

### Components
1. **Level 2 (Order Book):** Passive orders sitting in market. Shows bids/offers and depth.
2. **Time & Sales (Print):** Aggressive orders being executed. Real-time transactions.

### Mental Model
- Time & Sales = water pressure
- Level 2 bids/offers = river dam
- Enough pressure (aggressive orders) breaks the dam (takes all size on bid/offer) → price moves to next level

### Two Categories (SMB)
1. **Tape Events:** Specific moment at specific price level
   - Example: Huge bid getting hit ferociously → decrementing → dam about to break → short entry
   - Example: Capitulation selling absorbed by a bid that won't drop → reversal signal

2. **Tape Environments:** How a stock trades ALL DAY
   - Strong environment: Bids refresh, buying takes out offers consistently
   - Weak environment: Offers refresh, selling takes out bids
   - This informs trade management more than entry timing

### Wyckoff's Three Laws (Foundation)
1. **Supply/Demand:** Price moves when imbalanced
2. **Cause/Effect:** Bigger preparation = bigger move
3. **Effort vs Result:** Volume (effort) should confirm price movement (result)
   - High volume + small price move = DISHARMONY → reversal likely
   - High volume + large price move = HARMONY → continuation likely

### Application to Options Agent
**Direct tape reading isn't available via IBKR API for automated trading**, but the PRINCIPLES translate:

**Order Flow Proxies Available:**
1. **GEX (Gamma Exposure):**
   - Positive GEX = market makers long gamma = buy dips/sell rallies = RANGE-BOUND → ideal for premium sellers
   - Negative GEX = market makers short gamma = sell into declines/buy rallies = TRENDING → dangerous
   - GEX flip from negative to positive = optimal entry window for iron condors

2. **DIX (Dark Index):**
   - DIX > 45% = institutional dark pool buying → bullish → good for PCS
   - DIX < 40% = institutional selling → avoid aggressive premium selling

3. **Put/Call Ratio:**
   - P/C > 1.0 = elevated fear → rich put premiums → favorable for PCS

4. **Volume-at-Price Analysis:**
   - High open interest strikes act as magnets (max pain theory)
   - Select short strikes near high OI clusters for additional support/resistance

---

## 4. ACADEMIC SUPPORT

### Variance Risk Premium (VRP)
- IV consistently overstates realized volatility by 2-4 vol points (Carr & Wu 2009)
- VRP is LARGER after high-volume market dislocations → best premium selling opportunities
- Options agent already uses VRP as entry gate (VRP > 2) ✓

### Volume-Volatility Relationship
- Mixture of Distributions Hypothesis: volume and volatility jointly driven by information arrival
- High volume predicts continued high vol short-term but MEAN REVERSION over longer horizons
- This is exactly why selling premium after volume spikes works

### Empirical Results
- Goyal & Saretto (2009): 1-3% monthly returns for volatility-filtered short options
- Tastytrade: IV Rank > 50 entries improve win rates 10-20%
- CBOE PUT index: Matched S&P 500 returns with lower volatility since 1986

---

## 5. OPTIONS AGENT INTEGRATION PLAN

### Current State (gaps)
- ❌ No VWAP calculation anywhere
- ❌ No intraday volume analysis (only daily volume in SMB scorer)
- ❌ No cumulative delta / order flow analysis
- ❌ No relative volume metric
- ❌ SMB scorer's volume_moment and clean_tape are rudimentary (daily bars only)
- ✅ Already has: IV Rank, HV20, VRP, RSI, Bollinger Bands, Black-Scholes

### New Module: indicators.py
Create `~/apps/options-agent/indicators.py`:
- `calculate_vwap(bars)` — from intraday 1-min/5-min bars
- `calculate_vwap_bands(bars, num_std=1)` — VWAP ± N standard deviations
- `calculate_volume_zscore(bars, lookback=20)` — with time-of-day normalization
- `calculate_relative_volume(today_vol, avg_vol)` — RVOL ratio
- `get_volume_regime(zscore, price_change)` — classify: capitulation/breakout/quiet/expanding

### Insertion Points
1. **broker.py:** Add `get_intraday_bars()` method using `reqHistoricalData(barSizeSetting="5 mins", whatToShow="TRADES")`
2. **agent.py scan_for_entries():** After VRP filter (line 343), add volume/VWAP pre-filter
3. **Strategy-level should_enter():**
   - put_credit_spread.py: Require price > VWAP for entry
   - bb_mean_rev.py: Require volume z-score > 1.5 for higher conviction
   - zero_dte_pcs.py: Require minimum relative volume (avoid thin markets)
4. **smb_scorer.py:** Enhance volume_moment and clean_tape with intraday data
5. **config.py:** New VolumeConfig dataclass
6. **sizing.py:** Volume-aware sizing (thin volume = reduce size)

### Recommended Filter Stack (from research synthesis)
For each new entry, check:
1. Volume Z-Score > 1.5 on underlying (20-day lookback with time-of-day normalization)
2. IV Rank > 40 (already exists ✓)
3. Price position relative to VWAP (above for PCS, within bands for condors)
4. VRP > 2 (already exists ✓)
5. Volume regime classification (capitulation = aggressive entry, quiet = skip)

### Expected Edge
- 5-15% improvement in win rate vs unfiltered entries
- Better risk-adjusted returns (selling richer premium after volume spikes)
- Reduced exposure to adverse trending moves (via volume regime filter)
- More aggressive sizing during high-conviction setups (capitulation + high VRP + below VWAP)

---

## 6. BOOKS REFERENCED
1. "Maximum Trading Gains with Anchored VWAP" — Brian Shannon (2023)
2. "Studies in Tape Reading" — Richard Wyckoff (1910)
3. "One Good Trade" — Mike Bellafiore (2010)
4. "The PlayBook" — Mike Bellafiore (2013)
5. "Technical Analysis Using Multiple Timeframes" — Brian Shannon (2008)
