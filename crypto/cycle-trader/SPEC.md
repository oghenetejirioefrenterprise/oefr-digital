# SPEC — CY-1 BTC Cycle System, v1.1 (frozen)

**Normative.** This document is the complete rule set. Where prose and a
verification gate (§10) disagree, the gate wins — an implementation that fails any
gate is wrong regardless of how reasonable its reading of the prose is.
**Lineage:** frozen 2026-07-22, Amendment 1 (fresh-low lower highs) 2026-07-23;
hash-anchored in `auto-research-trader-v4/config/preregistration.json` (gate CY-1,
spec blobs d0b2f3a → 46d3527). Rules may never loosen; amendment-by-addition only,
owner-approved, all prior gates must keep passing.

---

## 0. Data conventions

- **Daily bars**: UTC OHLC. History: Bitstamp 2011-08-18 → spliced to Binance at
  2017-08-17 (splice verified <2% divergence). Reference dataset:
  `auto-research-trader-v4/docs/superpowers/research/2026-07-21-owner-cycle-system/dashboard-data/btc_daily_full.json`.
- **Weekly bars**: aggregated from daily, weeks anchored **Monday** (ISO), UTC.
  A "week's high/low" = max/min of its daily highs/lows. "Intraweek trade above X"
  = any daily high > X.
- **Weekly RSI-14**: Wilder smoothing on weekly closes.
- **Costs** (backtest/shadow accounting): 20 bps round-trip, spot, no funding.
- Known data warts: EP1's trigger week contains a suspect Bitstamp $15 wick;
  2011–2012 is thin-market. (EP1 is expired under v1.1 anyway — see §11.)

## 1. Episode lifecycle

States: `idle → watching (triggered) → accumulating/confirmed → distributing → closed | expired | stopped`.

- **Trigger**: weekly RSI-14 < 35 arms an episode ("watching"). Armed weeks within
  26 quiet weeks cluster into one episode; a trigger ≥26 quiet weeks after the last
  armed week starts a new episode.
- **Downtrend scope**: from the prior cycle ATH (the all-time-high weekly high
  preceding the trigger) to the present. "Episode low" = lowest daily low since the
  scope began, updated walk-forward.
- **Prior-bear leg** (for exit anchors): prior cycle ATH → episode low.
- An episode **expires** if no valid BoS ever prints (bounded by the next episode's
  trigger); it is **stopped** on an episode-low touch while positioned (§6).

## 2. Capital plan

Two pools, spot BTC only, **no leverage ever**:

1. **Capital on hand at trigger** → bottom-accumulation ladder (§3), weighted
   **1 : 2 : 4** across T1 : T2 : T3 (i.e., 1/7, 2/7, 4/7).
2. **New savings ≈ $2,000/month from trigger** accrue as cash; deployed at the
   BoS-retracement ladder (§5) together with any accumulation capital whose line
   never filled.

## 3. Bottom accumulation (on-chain floor lines)

Three limit-style tranches, evaluated **walk-forward against each day's current
line value** (the lines move daily):

- **T1 (1/7)** at **realized price** = CoinMetrics `CapMrktCurUSD / CapMVRVCur / SplyCur`
  (the community CSV/API lacks CapRealUSD; this derivation is the reference).
- **T3 (4/7)** at **balanced price** (Puell) = realized price − transferred price.
  Reference series: checkonchain full-history (2010-07 →), sanity-anchored at the
  FTX week (2022-11-09: balanced 17,191 vs price 15,863). The bitcoin-data.com
  `/v1/balanced-price` endpoint is REJECTED (4-year window + different transferred
  convention). Fallback when the reference is unreachable: balanced ≈ realized ×
  last-known ratio (0.735 as of 2026-07), flagged stale in every surface using it.
- **T2 (2/7)** at **midpoint(realized, balanced)**.

Fill semantics: a tranche fills the first day (post-trigger) that BTC's daily low ≤
that day's line value; fill price = min(line value, day's open) — i.e., if the day
opens below the line, fill at the open (gap fill). If the trigger day opens below
all lines, all three fill that day (this happened in 2018). Tranches that never
fill roll their capital into §5's deployment.

## 4. Structure: lower high & break of structure (v1.1 — Amendment 1)

**Lower-high candidate (the load-bearing definition):** a weekly high H such that

1. **Fresh-low origin**: H's rally originates from a low L₀ that undercut ALL prior
   lows of the downtrend scope at the time it printed (a "fresh low"). The rally
   origin is the lowest low between the prior higher week and the candidate week
   (excluding the candidate week's own low — crash weeks must not fabricate rallies).
2. **Degree**: rally (L₀ → H) ≥ **15%** (R_e = 15; the unique value passing all
   gates — R10 admits the +11% FTX bounce and calls a false Dec-2022 BoS; R20
   rejects the +19.6% Jan-2015 rally and misses the owner's 2015-01-26 BoS).
3. **Confirmation**: a subsequent low undercuts L₀ (strictly before any use of the
   candidate — no lookahead).
4. **Trigger-anchor guard**: the candidate's downtrend anchor (the argmax-high week
   its fresh low descends from) must **predate the episode trigger**. (Without
   this, the 2011 episode latched onto the Dec-2013 post-ATH breakdown — the next
   cycle's bear — and fabricated a trade.)
5. **Invalidation**: a confirmed candidate dies the moment any later weekly high
   exceeds it (that exceedance was the BoS of an older structure).

**Operative LH** = the most recent valid candidate. It may predate the RSI trigger.

**Break of structure (BoS)** = the first **intraweek trade above the operative LH**
(daily high > LH). The **BoS week** is the week containing that trade; the **leg**
= episode low → BoS-week high.

## 5. BoS-retracement ladder (reserve cash + savings + unfilled accumulation)

- Limit fills at retracements of the leg: **0.5 / 0.62 / 0.786**, weighted
  **2 : 4 : 8** (of 14 units). The **0.328 level is skipped** (owner instruction;
  measured cost ±2 pts = noise).
- Retracement price = BoS-week high − level × (BoS-week high − episode low).
- **Breakout fallback**: all unfilled ladder units buy at the first daily trade
  above the BoS-week high after the BoS week.
- Fill semantics as §3 (touch = daily low ≤ level; gap-open handling identical).

## 6. Exits & stop

1. **Exit 1 — 50% of the total position at the 1.272 extension of the prior bear**:
   level = episode_low + **1.272** × (prior_ATH − episode_low).
   (1.272, not 1.212: the owner's "~84k" read for the 2022 episode matched 1.272
   exactly — 83,559 printed 2024-11-11; 1.272 beat 1.212 in all four episodes.)
2. **Exit 2 — remaining 50% at the armed mirror exit**:
   - **Arming**: the 1.272 level has been crossed (Exit 1 printed).
   - **Signal**: intraweek trade **below** the most recent confirmed swing low.
     Swing-low definition mirrors §4 with **R_down = 10**: a weekly low preceded by
     a decline ≥10% (from the argmax high since the prior swing), confirmed by a
     subsequent higher high (confirmation strictly precedes the break);
     position-lifetime scope (only structure formed during the episode's uptrend).
   - **Fill**: sell on BTC's bounce to **50% of the decline leg**, computed
     **walk-forward**: target = (top_high + low_so_far) / 2, where low_so_far
     includes the current day's low *before* testing that day's high; the break day
     itself is excluded from fill checks (its high printed pre-break). If the low
     keeps falling, the target falls with it.
   - **Fallback**: no 50% bounce within **8 weeks** of the signal → sell at market.
   - Rejected alternative on file: fixed-anchor target (top → broken level) — its
     2025 target (116,727) never filled and degraded to a December fallback at 89k.
3. **Stop — episode-low touch, all phases, all pools.** At spot this stop is real
   everywhere (no liquidation line above it).

## 7. Beta sleeve (optional module; validated concept)

- Sizing concept 80/20 BTC/beta. Beta is bought on **BTC's** signal dates (same
  ladder logic), held through BTC's Exit 1, and sold **only** at BTC's armed mirror
  exit (Exit 2's signal/fill) or the episode-low rescue stop.
- Asset choice is the owner's (intended: SOL). The app never picks: the honest
  mechanical highest-beta pick lost in-sample (OP, Feb-2023 selection, −55.5%).
- Validated in-sample (v3 arming): ETH-constant combo 378.3 vs 91.0 BTC-only summed;
  EP5 SOL sleeve +777.5% (exit 2025-03-02 @ BTC 93,923, SOL 178.71).
- Known costs: multi-year unhedged holds (EP3: 23 months, ETH MAE −59%), and
  cross-episode overlap can stack beta exposure (Aug-2020→Apr-2021: 40%).

## 8. Data sources

| Series | Source | Notes |
|---|---|---|
| BTC daily OHLC (history) | Bitstamp → Binance splice @2017-08-17 | reference JSON in v4 repo; live: Binance spot klines |
| Realized price | CoinMetrics community API (`CapMrktCurUSD,CapMVRVCur,SplyCur`) | daily; derive realized = cap/mvrv/supply |
| Balanced price | checkonchain full-history series (build-time snapshot) + ratio fallback | see §3; alert on staleness |
| Weekly RSI | computed | §0 conventions |

## 9. Amendment discipline

- Rules are frozen. Changes are amendments: appended (never edited in place),
  owner-approved, new spec version + hash, and **every existing gate in §10 must
  keep passing**. Historical records are withdrawn (with reason) or appended —
  never restated.
- Superseded/rejected variants, so fresh eyes don't relitigate without new
  evidence: flat R=25 LH filter (missed 2015-01-26; superseded by fresh-low);
  3x perp lifecycle (liq line above stop; 2015 liquidates in-sample); sell-spot-at-
  BoS-and-rebuy at 1x (loses coins every breakout episode); fixed 70/30 split
  (dominated by the cash-flow shape); 0.328 ladder level (noise); 1.212 extension
  (−58 pts vs 1.272); TP1-anchored mirror arming (Jan-2024 whipsaw: exits SOL at
  $101 mid-cycle); R_down=10 for the LH side (false Dec-2022 BoS); no-degree LH
  (fires a week early on wrong structure, 2025).

## 10. Verification gates (executable fixtures — MUST PASS)

The owner's chart reads. Any implementation must reproduce ALL of these from raw
data. Tolerance: dates exact (weekly resolution), prices ±0.5% for feed differences
unless stated.

**G1 — 2015 entry (Amendment 1's anchor):**
2014-09-29 week low 275.00; 2014-12-29 week low 255.00 (lower low);
LH = **305.00** (week of 2015-01-05; rally 255→305 = +19.6% off the fresh low;
confirmed by 152.40 on 2015-01-14); **BoS = week of 2015-01-26** (weekly high
309.90 > 305). Leg 152.40 → 309.90. Ladder: 0.5 → 231.15 and (gap) fills
2015-02-02 open 226.93 region; 0.62 → 212.25 fills 2015-02-05; 0.786 → 186.10
NEVER fills (2015-08-24 week low 198.12); breakout **2015-07-12 @ 309.90**.

**G2 — 2020 entry:** LH = **10,500** (week of 2020-02-16; +63% rally off Dec-2019
6,435; confirmed by the COVID crash). The early-March ~9.2k high is EXCLUDED
(origin ~8.5k was not a fresh low). **BoS = late July 2020** (week of 2020-08-02,
first trade > 10,500). No ladder fills (0.328-era check; under v1.1's ladder the
Sept-2020 dip still misses 0.5); all-in on breakout 2020-08-17.

**G3 — 2022 entry:** LH = **25,211.32** (week of 2022-08-15; +43% off 17,622;
confirmed by the Nov crash). Sept high 22,799 and Oct high 20,475 are EXCLUDED —
their rally origins (~18.1–18.2k) never undercut June's 17,622 (not fresh lows);
the Nov FTX bounce (~+11%) fails R_e=15. **BoS = week of 2023-02-13** (weekly high
~25,250). Ladder 0.5 fills 2023-03-09 @ 20,363; breakout **2023-03-14 @ 25,250**.

**G4 — mirror-exit detector (2025):** signal fires the **week of 2025-10-06**,
breaking the ~107k Aug/Sep-2025 double bottom (107,255/107,350 — 0.09% apart;
either attribution acceptable); walk-forward 50% target fills **2025-10-12 @
≈114,100** (owner: ~$114k). SOL closed ≈$197 that day (beta-sleeve fixture).

**G5 — EP6 live state (as of 2026-07-22 data):** operative LH **82,850** (week of
2026-05-10; +38.1% off fresh 60,000; confirmed 2026-06-07). The June bounce high
67,292 (+13.8%) fails R_e=15 and must NOT be operative. BoS trigger = intraweek
trade > 82,850. Lines: T1 ≈52.9k / T2 ≈45.9k / T3 ≈38.9k; no fills.

## 11. Historical record (regression fixtures, v1.1 rules, frozen exits)

Per-episode accumulation-only (1:2:4, hold-through, Exit 1 @1.272 + Exit 2 mirror):

| Episode | Acc fills (T1/T2/T3) | BoS | Exit 1 (1.272) | Exit 2 (mirror) | pnl (acc-only) |
|---|---|---|---|---|---|
| EP1-2011 | — | — | — | — | **EXPIRED** (no valid fresh-low LH; the old R=25 "2013 trade" was structurally invalid and is withdrawn, not restated) |
| EP2-2014 | 2014-10-04 @ 347/336/325 | wk 2015-01-26 | 1,437.88 (2017-05-02) | 2,405 (2017-07-20) | **+480.9%** |
| EP3-2018 | 2018-11-26 @ 4,089 ×3 (trigger opened below all lines) | wk 2019-04-01 @ 5,275 *(no owner anchor for 2019 — rule output, owner sign-off pending)* | 24,325 (2020-12-25) | 55,892 (2021-04-28) | **+881.0%** |
| EP4-2020 | 2020-03-16 @ 5,360/5,135/4,704 | wk 2020-08-02 | 24,155 (2020-12-19) | 55,892 (2021-04-28) | **+715.5%** |
| EP5-2022 | 2022-06-13/14/18 @ 23,188/21,261/19,078 | wk 2023-02-13 | 83,559 (2024-11-11) | 93,923 (2025-03-02) | **+339.7%** |

**Sums:** acc-only +2,417%; cash-flow model ($10k at trigger + $2k/mo to BoS,
savings deployed at the ladder blend): $82k contributed → ≈$470k (5.73x blended);
per-episode MOIC 3.88–8.33x. **Zero stop-outs.** Worst sit-throughs: 2014
accumulation −48.9%; 2019 spot phase −64% MAE through COVID (stop survived by
19.8%). EP5's mirror exit is the **armed Feb-2025 correction** (2025-03-02 @
93,923), not the Oct-2025 signal — the Oct signal is the second armed instance.

Reference outputs for byte-level comparison live in the v4 repo:
`dashboard-data/episodes_dashboard.json` (v1.1), `cy1_lifecycle.json`,
`beta_exit_v2.json`, `v4_lifecycle.json`, plus the pre-correction backup
(`episodes_dashboard_r25_backup.json`) and diffs.

## 12. Live-tracking requirements (engine-adjacent, normative for the app)

- Accumulation lines refresh at least daily; every alert includes the line values
  and their data as-of date; ratio-fallback balanced values are marked "approx".
- The operative-LH computation re-runs on every new weekly bar (and intraweek for
  the BoS/stop/level touches at ≤1h polling).
- State transitions and every computed level are journaled (SQLite) with inputs,
  so any historical signal can be replayed and audited.
- Alert cooldowns per key (≥12h) so a level chop doesn't spam; a state CHANGE
  always alerts regardless of cooldown.
- Prescribed-vs-actual (shadow ledger): the engine's prescribed fills are recorded
  when levels print; TJ's actual fills are entered manually; both are shown, never
  merged.
