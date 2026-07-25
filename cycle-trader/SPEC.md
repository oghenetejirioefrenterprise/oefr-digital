# SPEC — CY-1 BTC Cycle System, v1.2

**Normative.** This document is the complete rule set. Where prose and a
verification gate (§10) disagree, the gate wins — an implementation that fails any
gate is wrong regardless of how reasonable its reading of the prose is.
**Where §§0–11 and §13 disagree, §13 governs** (gates still beat both).

**Lineage & provenance — read this before trusting a number.**

| | |
|---|---|
| Anchored artifact | `auto-research-trader-v4/docs/superpowers/research/2026-07-21-owner-cycle-system/CY-1-FROZEN-SPEC.md` — blob `d0b2f3a` (frozen 2026-07-22) → `46d3527` (Amendment 1, 2026-07-23), registered in v4 `config/preregistration.json` gate `CY-1` |
| **This file** | a **derived restatement**, blob `a1aa74b` at v1.1. **Never hash-registered.** It expands the anchored doc roughly 2× (128 → 239 lines) |
| Reference implementation | `dashboard-data/cy1_lifecycle.json` — the executable CY-1 record |

Content present here but **not** in the anchored artifact — therefore implementer
interpretation, not owner-frozen rule — includes: §1's 26-quiet-week clustering,
§1's downtrend-scope and episode-low definitions, §3's fill/gap semantics, §0's
cost convention, and §11's per-episode fill table. These are load-bearing and
mostly correct, but they were added outside the §9 amendment path and carry no
owner sign-off. §13 marks the ones that conflict with the reference implementation;
§14 lists what only the owner can settle.

v1.2 (2026-07-24) is **editorial**: it adds §13 (clarifications) and §14 (open
items), corrects this lineage block, and inserts `→ §13.x` cross-references into
§§1–11. **No rule text in §§0–11 was altered and no gate output changed.**
Rules may never loosen; amendment-by-addition only, owner-approved, all prior
gates must keep passing.

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

- **Trigger**: weekly RSI-14 < 35 arms an episode ("watching"). **→ §13.5** ("quiet"
  is undefined below). Armed weeks within
  26 quiet weeks cluster into one episode; a trigger ≥26 quiet weeks after the last
  armed week starts a new episode.
- **Downtrend scope**: from the prior cycle ATH (the all-time-high weekly high
  preceding the trigger) to the present. "Episode low" = lowest daily low since the
  scope began, updated walk-forward. **→ §13.1** (freezes at BoS; stop scope)
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
all lines, all three fill that day (this happened in 2018). **→ §13.2** (fill
direction). Tranches that never fill roll their capital into §5's deployment
— **confirmed by owner decision 2026-07-24: into the ladder pool, not straight to
the breakout (→ §13.6, §14 OQ-3 resolved). `cy1_lifecycle.json` deviates here.**

## 4. Structure: lower high & break of structure (v1.1 — Amendment 1)

**→ §13.3 gives the walk-forward algorithm for this section in pseudocode, and
disambiguates the section's anchor language: §4.1's "prior higher week"
(`anchor(i)`, bounding the rally-origin window) and §4.4's "argmax-high week its
fresh low descends from" (`D`, the downtrend anchor governing scope, freshness
and the trigger guard) are two different weeks in general — EP4 proves it.**

**Lower-high candidate (the load-bearing definition):** a weekly high H such that

1. **Fresh-low origin**: H's rally originates from a low L₀ that undercut ALL prior
   lows of the downtrend scope at the time it printed (a "fresh low"). The rally
   origin is the lowest low between the prior higher week and the candidate week
   (excluding the candidate week's own low — crash weeks must not fabricate rallies).
2. **Degree**: rally (L₀ → H) ≥ **15%** (R_e = 15; the unique value passing all
   gates — R10 admits the +11% FTX bounce and calls a false Dec-2022 BoS; R20
   rejects the +19.6% Jan-2015 rally and misses the owner's 2015-01-26 BoS).
3. **Confirmation**: a subsequent low undercuts L₀ (strictly before any use of the
   candidate — no lookahead). **→ §13.4** (daily low, strict).
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
  **→ §13.2 — this is wrong for the breakout fallback**, which is a buy-*stop*:
  §3's `min(level, open)` would fill below the breakout price, which is
  unobtainable. G1 (309.90) and G3 (25,250) both fill *at* the BoS-week high.

## 6. Exits & stop

**→ §13.2** — every fill rule below is sell-side; §3's semantics are buy-side only
and do not transfer. **→ §13.9** for arming across repeat signals and for G4's harness.

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
   **→ §13.1 — "all phases" is falsified by the record and by the reference
   implementation** (`cy1_lifecycle.json`: "episode-low stop **post-activation**").
   Read literally, EP5 stops out days after its June-2022 fills.

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

**G4 — mirror-exit detector (2025)** *(**→ §13.9** — run as a standalone detector
fixture; a correct lifecycle engine has no EP5 position open in Oct-2025 and can
never reach this signal, so G4 is unreachable unless its harness is defined
separately)*: signal fires the **week of 2025-10-06**,
breaking the ~107k Aug/Sep-2025 double bottom (107,255/107,350 — 0.09% apart;
either attribution acceptable); walk-forward 50% target fills **2025-10-12 @
≈114,100** (owner: ~$114k). SOL closed ≈$197 that day (beta-sleeve fixture).

**G5 — EP6 live state (as of 2026-07-22 data):** operative LH **82,850** (week of
2026-05-10; +38.1% off fresh 60,000; confirmed 2026-06-07). The June bounce high
67,292 (+13.8%) fails R_e=15 and must NOT be operative. BoS trigger = intraweek
trade > 82,850. Lines: T1 ≈52.9k / T2 ≈45.9k / T3 ≈38.9k; no fills.

## 11. Historical record (regression fixtures, v1.1 rules, frozen exits)

**→ §14 OQ-4: every pnl figure in this table disagrees with the reference
implementation** (`cy1_lifecycle.json`, `acc_only_pnl_pct_1_2_4`) by +0.5 to +1.1
points, and the sum is +2,417% here vs **2,413.9%** there. A P7 harness asserting
this table against the reference outputs fails on all four episodes. The fill
dates/prices, exits, and cash-flow figures below all reconcile exactly.

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

Reference outputs for byte-level comparison live in the v4 repo, but **only
`cy1_lifecycle.json` implements CY-1.** The others are different strategies and
must not be compared against this table:

| File | What it actually contains |
|---|---|
| **`cy1_lifecycle.json`** | **CY-1. The reference implementation.** 1:2:4 acc, 2:4:8 ladder, 1.272 + mirror, 10 bps/side, 21 units |
| `episodes_dashboard.json` | **NOT CY-1** — 0.328 level *included and filled*, exits at 1.212/1.618/2.0 (50/25/25). Entry-rule validation only |
| `v4_lifecycle.json` | **NOT CY-1** — 3x perp lifecycle with BoS spot sale (a §9-rejected variant). Source of the −48.9% MAE quoted above (**→ §14 OQ-2**) |
| `episodes_dashboard_r25_backup.json` | pre-Amendment-1 (R=25), withdrawn |

**Week labelling differs between this doc and every JSON above → §13.10.**

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

---

## 13. Amendment 2 — 2026-07-24 (editorial clarifications, v1.2)

**No rule changes.** Every clause here states what §10's gates and
`cy1_lifecycle.json` already prove; G1–G5 and §11's fill dates/prices are
unchanged. Where §13 and §§0–11 prose disagree, §13 governs. Items requiring an
actual owner decision are in §14, not here.

**v1.2.1 correction (2026-07-24, same day):** review against the raw data showed
the first issue of §13.1/§13.3 used the wrong scope anchor — it measured the
downtrend scope, the episode low, and fresh-low freshness from the **prior-cycle-ATH
week**, which fails G2 and mis-states EP4: under that anchor EP4's origin 6,435 is
not fresh (3,156.26 printed 2018-12-15) and EP4's episode low computes as 3,156.26
instead of the reference's 3,782.13. The corrected anchor below (scope from the
previous episode's activation; **D** = that scope's argmax-high week) reproduces
every gate and every reference value, and matches the rule text
`episodes_dashboard.json` carried all along ("scope starts at the previous
episode's activation"). Gates beat prose — including this section's own first
draft.

### 13.1 Episode low: running anchor, frozen at BoS — and the stop's true scope

`episode_low(t)` = lowest daily low from the start of the **downtrend-anchor week
D** (defined in §13.3 — *not* necessarily the prior-cycle-ATH week) through day
`t` inclusive. It is a **running anchor**, not a stop level.

*(v1.2.1: EP4 is why D, not the prior ATH, is the anchor: from the Dec-2017 ATH
the lowest low is 3,156.26 — EP3's low — but the reference records EP4's episode
low as 3,782.13, which is the minimum from D = the June-2019 argmax week. The
other four episodes agree under either anchor; EP4 disambiguates.)*

- At the BoS (first day whose high > operative LH) the value **freezes**:
  `EL* = episode_low(BoS day)`. `EL*` anchors the §5 leg and the §6.1 extension.
- **The stop is a touch of `EL*`, and applies only from the BoS onward.** Before
  the BoS a new low simply updates the anchor and is *not* a stop event.
- Consequently the §6.1 level drifts down with the anchor pre-BoS (PRD §8's
  "moves with the low") and is fixed thereafter.

*Why this is not a rule change:* §6.3's "all phases" read literally stops EP5 days
after its 2022-06-13/14/18 fills at 23,188/21,261/19,078, since price fell to
15,476 that November — yet §11 records EP5 as a +339% win. The frozen-anchor
reading is confirmed to the cent: `15,476 + 1.272 × (69,000 − 15,476) = 83,558.5`,
and §11's Exit 1 is 83,559. `cy1_lifecycle.json` states "episode-low stop
**post-activation**"; `v4_lifecycle.json` flags "accumulation has no stop (episode
low still forming)". EP3's stop `EL* = 3,156.26` versus the COVID low 3,782.13
gives exactly §11's "survived by 19.8%".

### 13.2 Fill semantics are direction-dependent

§3 defines buy-limit semantics only. Four primitives, all on daily bars:

| Primitive | Touch test | Fill price |
|---|---|---|
| **Buy-limit** (fill on a decline to level) | daily low ≤ level | `min(level, open)` |
| **Buy-stop** (fill on a break upward) | daily high ≥ level | `max(level, open)` |
| **Sell-limit** (fill on a rally to level) | daily high ≥ level | `max(level, open)` |
| **Sell-stop** (fill on a break downward) | daily low ≤ level | `min(level, open)` |

| Event | Primitive |
|---|---|
| §3 accumulation tranches T1/T2/T3 | buy-limit |
| §5 retracement ladder 0.5 / 0.62 / 0.786 | buy-limit |
| **§5 breakout fallback** (level = BoS-week high) | **buy-stop** |
| §6.1 Exit 1 @ 1.272 | sell-limit |
| §6.2 Exit 2 walk-forward 50% bounce | sell-limit, target recomputed each day |
| §6.2 8-week fallback | **close** of the first daily bar on/after signal + 56d |
| §6.3 stop @ `EL*` | sell-stop |

G1 and G3 fill the breakout at 309.90 and 25,250 — the BoS-week high itself, which
only the buy-stop rule reproduces.

### 13.3 Operative-LH algorithm *(v1.2.1 — scope anchor corrected)*

Two distinct anchors, which the doc's prose blurs and v1.2's first draft wrongly
merged:

- **`anchor(i)`** — per candidate week `i`: the most recent week `j < i` with
  `high[j] > high[i]`. This is §4.1's "prior higher week"; it bounds the rally-
  origin window only.
- **`D` (downtrend anchor)** — per episode, walk-forward: the argmax-high week of
  the **scope window**, where the scope window starts at the **previous episode's
  activation** (its BoS; data start if none). This is §4.4's "argmax-high week its
  fresh low descends from". D anchors the downtrend scope, the freshness test,
  the trigger-anchor guard, and §13.1's episode low. D usually *is* the
  prior-cycle-ATH week (EP2/EP3/EP5/EP6) — but not always: EP4's D is the
  June-2019 13,970 week, while its **exit** anchor (§6.1's prior_ATH) remains the
  absolute 19,798.68. Exits and structure use different anchors; EP4 is the
  episode that proves it.

```
window_start = previous episode's activation (BoS date; data start if none)
D = argmax-high week within [window_start, trigger week]
    # Walk-forward-safe: computing D at any candidate week i instead gives the
    # same answer for every gate — a post-trigger weekly high above D's high
    # would invalidate all candidates via §4.5 anyway. Do NOT bound the window
    # at a later date (e.g. the next episode's trigger): that leaks the next
    # bull run into D and destroys EP2 (D becomes Dec-2017) and EP4 (Nov-2021).
    # D freezes at BoS along with EL* (§13.1).

for each week i with monday(i) >= monday(D), walk-forward:
    j    = anchor(i)                       # most recent week with a higher high
    L0   = min(low[j .. i-1])              # rally origin; window INCLUDES the
                                           # anchor week j, EXCLUDES week i's low
    w0   = argmin week of L0

    fresh    = L0 < min(low[D .. w0-1])                 # undercut ALL scope lows
    degree   = (high[i] - L0) / L0 >= 0.15              # R_e = 15
    guard    = monday(D) < trigger_week                 # D predates the trigger
    if not (fresh and degree and guard): continue

    confirmed_at = first DAY after week i whose daily low < L0   # strict; §13.4
    candidate i is usable only from confirmed_at onward          # no lookahead
    candidate i dies at the first later weekly high > high[i]    # §4.5

operative_LH(t) = high of the most recent candidate that is
                  confirmed (confirmed_at <= t) and not yet invalidated
BoS = first day with daily high > operative_LH(t)
```

The guard is what expires EP1: its 2013-era candidates descend from the Dec-2013
ATH, and that D postdates the Nov-2011 trigger.

**The origin window includes the anchor week `j`** (v1.2.2, 2026-07-25 — found by
executing this pseudocode against the raw data). §4.1's prose is precise about
this: it excludes *"the candidate week's own low"* and nothing else. v1.2's
pseudocode wrote `low[j+1 .. i-1]` and thereby dropped the anchor week — which
**fails G1, G3 and G5**, because the fresh low routinely prints in the very week
that made the higher high. G1 is the proof: week 2014-12-29 has high **321.00**
(the anchor, above the 305.00 candidate) and low **255.00** (the origin). With
`j+1` that week's low is invisible, the origin window is empty, and LH 305.00 is
never generated at all. Executed on real data, `j` reproduces every gate; `j+1`
reproduces only G2.

Two further implementation traps this pseudocode implies but does not spell out:

- **The guard tests D, not `anchor(i)`.** `anchor(i)` may legitimately postdate
  the trigger — G3's operative LH (25,211.32, wk 2022-08-15) has `anchor(i)` =
  the wk-2022-06-13 high 26,895.84, three weeks *after* the 2022-05-16 trigger.
  Guarding on `anchor(i)` rejects G3's LH.
- **The BoS kills its own LH (§4.5), so invalidation is day-resolution and the
  candidate is operative *through* its break day.** The BoS-week high exceeds
  the LH by definition, so week-resolution invalidation makes the candidate
  dead on the Monday of the very week that breaks it — a walk-forward scan then
  never sees the break. Likewise, "what is the operative LH today?" returns
  nothing (or stale structure) for any post-BoS date; historical reconstruction
  must find the BoS by walking days against the *then*-operative LH, never by
  breaking today's.

Verified against raw data (2026-07-24): EP2 D = 1,163 (wk of 2013-11-25), 255 fresh
vs window-min 275 · EP4 D = 13,970 (wk 2019-06-24), **6,435 fresh vs window-min
6,515** — under a prior-ATH scope it is *not* fresh (3,156.26 exists) and G2
fails · EP5 D = 69,000, 17,622 fresh vs 26,560, Sept-2022 origin correctly not
fresh · EP6 D = 126,199.63, low-from-D 57,800.19 — both matching PRD §8.

**Executed end-to-end on the frozen data (2026-07-25).** This section is no longer
prose-only: the algorithm above was run against 2011-08-18 → 2026-07-22 and
reproduces the whole record.

| | Trigger (Mon) | D | Operative LH | BoS week | `EL*` |
|---|---|---|---|---|---|
| EP1 | 2011-11-21 | — | none | — | **expired**, as required |
| EP2 | 2014-09-22 | 2013-11-25 | **305.00** (wk 2015-01-05) | **2015-01-26** | 152.40 |
| EP3 | 2018-11-19 | 2017-12-11 | 4,450.38 (rule output, no owner anchor) | **2019-04-01** | 3,156.26 |
| EP4 | 2020-03-09 | 2019-06-24 | **10,500.00** (wk 2020-02-10) | **2020-07-27** | 3,782.13 |
| EP5 | 2022-05-16 | 2021-11-08 | **25,211.32** (wk 2022-08-15) | **2023-02-13** | 15,476.00 |
| EP6 | 2026-01-26 | 2025-10-06 | **82,850.00** (wk 2026-05-04) | none yet | — (running 57,800.19) |

G1's ladder reproduces to the cent (231.15 / 212.25 / 186.10; 0.5 gap-fills
2015-02-02 @ 226.93, 0.62 fills 2015-02-05 @ 212.25, 0.786 never, breakout
2015-07-12 @ 309.90). G4's detector fires the week of 2025-10-06 and fills
2025-10-12 @ 114,099.82. All six triggers and every `EL*` match the reference.

Reproduces every entry gate: G1 `(305−255)/255 = +19.6%` off fresh 255, confirmed
by 152.40 on 2015-01-14, BoS week 2015-01-26 @ 309.90 · G2 `+63.2%` off 6,435, the
~9.2k March high excluded (origin ~8.5k not fresh) · G3 `+43.1%` off 17,622, Sept
22,799 and Oct 20,475 excluded (origins never undercut 17,622), FTX bounce `+11%`
< 15 · G5 `+38.1%` off fresh 60,000, June bounce 67,292 `+13.8%` < 15.
`cy1_lifecycle.json → ep6_operative_by_Re` confirms R10 → 67,292 (wrong), R15 and
R20 → 82,850.

### 13.3a `R_e = 15` is an edge, not a unique point (bisected 2026-07-25)

§4.2 calls 15 "the unique value passing all gates", and CLAUDE.md repeated it.
**Neither is true**, and the two measurements below must be kept apart — an
earlier revision of this section conflated them and had to be corrected.

**What HISTORY constrains.** Two different bands, depending on whether you count
only the owner's chart reads or also §13.3's derived chain table:

| Scope | Passing band | Width | Lower edge set by |
|---|---|---|---|
| **§10 chart reads only** (G1/G2/G3) | `(10.2771, 19.60784]` | **9.33 pts** | **G3** — the FTX bounce's own rally; fails at 10.2770, passes at 10.2772 |
| **+ §13.3's executed chain table** | `(12.0422, 19.60784]` | 7.57 pts | the **chain gate**, via EP3 wk 2018-12-10 (+12.0422% off 3,222.00) |

The upper edge is the same in both and is **G1's own LH rally**
(255.00 → 305.00 = +19.60784%).

Two things follow. First, the owner's actual chart reads bound `R_e` only to a
**9.33-point** band — wider still than the 7.57 quoted before. Second, the
tightening to 12.0422 comes from an **EP3** assertion, and EP3 is precisely the
episode §11 flags as having *no owner anchor* ("owner sign-off pending"). So the
narrower band rests on rule output, not on a chart read.

*(An earlier revision of this section claimed the lower edge "breaks G2 via the
episode chain". That was wrong on both counts and is corrected here: **G2 passes
at every value tested**, down to 10.277; the perturbation at 12.00 changes EP3's
BoS only — 2019-04-02 → 2018-12-18 — and does not propagate, because EP4's D
stays 2019-06-24 with 13,970 still the argmax over the widened window.)*

**What the M1 SUITE constrains** — `(13.78809, 15.00]`, much narrower. But that
narrowness is **self-imposed and carries no historical authority**: the upper edge
comes from `test_degree_is_inclusive_at_exactly_r_e`, a *constructed* exactly-15%
rally, and the lower from `test_rally_below_15_percent_is_rejected`, built on G5's
+13.78809% bounce. So "R_e = 15.01 fails" is a fact about a fixture, not about
Bitcoin.

**Consequences.** §4.2's supporting evidence remains sound as far as it goes —
R10 and R20 do both fail (R10 admits the +11% FTX bounce; R20 rejects Jan-2015's
+19.6% rally and loses G1's BoS). But 15 is the upper edge of a wide historical
band, and the record cannot prefer it to 14, or to 17. This does not make the
engine wrong: 15 is the owner's value and it passes everything.

This is the **second** frozen constant found to be an edge rather than a point —
`QUIET_WEEKS = 26` sits inside a `[10, 57]` plateau (§13.5). Treat both as
owner-chosen values sitting safely inside a passing region. **Do not tune them,
and do not cite them as gate-derived.**

### 13.4 Confirmation resolution

Confirmation (§4.3) is a **daily** low, strictly less than `L₀` — per G1's
"confirmed by 152.40 on 2015-01-14", a daily date. The candidate is unusable
before its confirmation date.

### 13.5 "Quiet week"

A week whose RSI-14 is **≥ 35** (i.e. not armed). §1's clustering: an episode's
armed weeks cluster while gaps stay under 26 quiet weeks; **26 consecutive quiet
weeks** after the last armed week close the window, so the next armed week starts
a new episode. *(Note: the entire clustering rule is absent from the anchored
artifact — see the provenance block.)*

**26 is historically unfalsifiable, but robustly so** (swept `q = 1…119` against
the frozen data, 2026-07-25; figures corrected after a first pass reported them
wrong). **Every** value in `[10, 57]` — 48 consecutive values, a 5.7× span —
produces the identical six triggers. The plateau is contiguous and breaks at
exactly two points:

| | Triggers | What changes |
|---|---|---|
| `q = 9` | 7 | EP6 splits |
| `q ∈ [10, 57]` | **6** | the recorded episode set |
| `q = 58` | 5 | EP4 merges into EP3 |

So 26 sits deep in the interior: the record can neither confirm nor refute it, but
it also cannot be wrong by a little. The defensible claim is "26 is interior to the
plateau" — pin the **edges (9/10 and 57/58)**, not the value. Note the chain gate's
exact six-trigger assertion already pins both edges as a side effect.

### 13.6 Accumulation-line lifetime

Lines are live from the trigger day through the **BoS day inclusive**. After the
BoS, §5 governs and no accumulation fill may occur. Unfilled tranche capital rolls
into the **§5 ladder pool** (not straight to the breakout), deploying with the
ladder's 2 : 4 : 8 proportions; ladder rungs that then go unfilled join the
**breakout fallback**. Owner decision 2026-07-24 — **§14 OQ-3, resolved**.

### 13.7 Savings accrual window

The ≈$2,000/month accrues from the trigger month **to the BoS, inclusive**, and
stops there (§11's parenthetical, lifted to normative). `cy1_lifecycle.json`
confirms `months_in_window` = trigger→BoS: 4 / 4 / 4 / 9 months for EP2–EP5,
totalling the $82,000 contributed.

### 13.8 Costs

**10 bps per side** (§0's 20 bps round-trip). §11's percentages are **net** —
`cy1_lifecycle.json` states "10bps/side" for the run that produced them.

### 13.9 Repeat mirror signals, and G4's harness

- **The position exits at the FIRST armed mirror signal.** Later signals are
  recorded but inert. EP5 therefore exits 2025-03-02 @ 93,923 (signal week
  2025-02-24); the Oct-2025 signal is the second armed instance.
- **G4 is therefore a standalone detector fixture, not a lifecycle assertion.** A
  correct engine holds no EP5 position in Oct-2025, and §6.2's position-lifetime
  scope means it never evaluates that window — so G4 must be run against the
  detector directly, with scope supplied explicitly:

  | G4 harness | |
  |---|---|
  | Input window | 2025-08-01 → 2025-12-31 |
  | Params | `R_down = 10`, walk-forward 50% target, position-lifetime scope **disabled** |
  | Expect signal | week of 2025-10-06, breaking the ~107k double bottom (107,255 / 107,350 — 0.09% apart, either attribution passes) |
  | Expect fill | 2025-10-12 @ ≈114,100 (±0.5%) |

  G4 passing must **not** be taken to imply an open EP5 position in Oct-2025;
  §11's EP5 exit stays 2025-03-02.

### 13.9a `R_down = 10` is a half-line, and its default is untested (measured 2026-07-25)

The **third** frozen constant found to be an edge rather than a point — and the
first found to be wholly unexercised. Measured by varying the argument on G4's
window (varying the *engine default* measures nothing; see the warning below):

| `R_down` | G4's two named lows surviving | Total swings |
|---|---|---|
| 0 … 13.757 | **2 of 2** | 14 → 6 |
| 13.7571 … 13.8334 | 1 of 2 | 6 |
| ≥ 13.8335 | **0 of 2** | 5 |

The two component declines are wk 2025-08-25 = **13.757009%** and wk 2025-09-01 =
**13.833411%**. So history bounds `R_down` **from above only**:

- `≤ 13.757` — both attributions survive, which is what the gate asserts
- `≤ 13.833` — either attribution survives, §10 G4's literal wording

**There is no lower edge at all.** G4's structure is still present at `R_down = 0`,
and at −100. This differs in kind from the other two: `R_e` is a genuine two-sided
band `(10.2771, 19.60784]` (§13.3a) and `QUIET_WEEKS` an interior plateau
`[10, 57]` (§13.5), but `R_down` is a **half-line**. Any value from 0 to 13.75
reproduces G4 identically.

**`R_DOWN_DEFAULT` is dead code.** Setting it to `99` leaves all 212 tests green —
every call site passes `r_down` explicitly. The constant is frozen in the engine
and exercised by nothing, so a future edit to it is invisible to CI while silently
changing the behaviour of any M2 caller that omits the argument.

> **Methodology warning, learned by getting it wrong here.** Sweeping
> `R_DOWN_DEFAULT` shows the gate passing at *every* value — not because the
> constant is unconstrained, but because the gate never reads it. When measuring
> whether a constant is load-bearing, confirm the code under test actually
> consumes the thing being varied.

### 13.10 Week labelling in the reference JSONs

§0 anchors weeks to **ISO Monday** and this doc names a week by its Monday. Every
`dashboard-data/*.json` names the same week by its **Sunday close**. The weeks are
identical; only the labels differ. G1's "BoS week of 2015-01-26" is
`cy1_lifecycle.json`'s `2015-02-01`; its LH "week of 2015-01-05" is `2015-01-11`.
A reproduction harness must normalise labels before comparing, or it will report a
6-day error on every structural date.

**§10 itself mixes conventions** (labels carried from their sources): G1, G3 and
G4 use Mondays, but G2's "week of 2020-02-16" / "week of 2020-08-02" and G5's
"week of 2026-05-10" are Sunday labels — ISO Mondays 2020-02-10, 2020-07-27 and
2026-05-04. An assertion that pastes a §10 label as a Monday fails on G2 and G5.

**Neither G1's nor G5's stated confirmation date is the rule's confirmation
date.** §4.3/§13.4 define confirmation as the **first daily low strictly below
`L₀`** — both gates instead name the *dramatic* low that followed it:

| Gate | §10 prose | Rule's actual output | Why they differ |
|---|---|---|---|
| G1 | "confirmed by 152.40 on 2015-01-14" | **2015-01-13** (low 216.00) | 152.40 is the episode low; the first low under `L₀`=255 came a day earlier |
| G5 | "confirmed 2026-06-07" | **2026-06-05** | 06-07 is a Sunday *label*; the confirming low printed the Friday inside that week |

Both verified by execution against the frozen data. A gate test asserting either
prose date **fails on correct code**. Assert the rule's output, or compare at week
resolution.

---

## 14. Open items — owner decision required (not resolved by v1.2)

These are genuine rule questions. Each needs a decision, then an appended
amendment with a new version + hash; none may be silently adopted.

**Priority, per owner 2026-07-24:** *"the cumulative return is not really relevant,
being able to autonomously execute based on the strategy is the main point."*
Accordingly only questions that change **execution behaviour** block the build.
**OQ-1 blocks live arming. OQ-3 is resolved. OQ-2, OQ-4 and OQ-5 are explicitly
non-blocking** — they concern the accuracy of the historical record, which is
context for reading drawdowns, not a product goal. They stay on file, unresolved,
and are not to be treated as work items unless the owner reopens them.

Consequence for the gate suite: **assert structural facts** — LH prices, BoS weeks,
fill dates, fill prices, exit dates, exit prices — all of which reconcile exactly
with `cy1_lifecycle.json`. Treat derived pnl percentages as informational and
target the reference implementation's values, not §11's transcriptions.

**OQ-1 — Concurrent episodes and capital independence.**
EP3 (trigger 2018-11-25) is still fully positioned when EP4 triggers 2020-03-15;
both exit 2021-04-28, and both draw on the same 19,798.68 prior-cycle ATH. §2 says
"capital on hand at trigger" but never addresses a second live episode. The
cash-flow model gives **each** episode a fresh $10,000 plus its own $2k/mo
(contribution windows happen not to overlap: 18+18+18+28 = $82,000 → $469,911 =
5.73x, which reconciles exactly). The open question is whether a real second $10k
exists at EP4's trigger while EP3's capital sits in BTC — if not, the summed record
overstates. *Decide: independent capitalisation, shared pool, or forbid overlap.*

**OQ-2 — MAE convention (currently unreproducible).**
§11's "2014 accumulation −48.9%" cannot be derived from any stated convention. On
EP2's weighted cost basis of 330.97: daily low → **−53.95%**, daily close →
**−48.21%**, weekly close → **−35.99%**. Nor does the source file reconcile —
`v4_lifecycle.json`'s `acc_value_per_1` of 0.6751 implies 223.4 against a BoS fill
of 226.93 (0.6857). The number also comes from the **3x-perp/BoS-sale** file, a
§9-rejected variant, not from `cy1_lifecycle.json`. PRD P5 makes MAE history a
product requirement, so this must be pinned. *Decide the basis (daily close is
closest at 0.7pt), then recompute all MAE figures from `cy1_lifecycle.json`.*

**OQ-3 — Where unfilled accumulation capital goes. → RESOLVED 2026-07-24.**

**Owner decision:** *"unfilled accumulation capital goes to the ladder and
unfulfilled ladder goes to the breakout."*

This **confirms §3 and §5 as written**; it is `cy1_lifecycle.json` ("unfilled joins
**breakout** [FLAGGED]") that deviates. Normative cascade:

```
accumulation tranche unfilled at BoS  ──►  joins the §5 ladder pool
ladder rung unfilled                  ──►  joins the §5 breakout fallback
```

The rolled capital deploys with the ladder's existing **2 : 4 : 8** proportions
across 0.5 / 0.62 / 0.786 — the weights are ratios, applied to whatever the pool
holds (reserve cash + savings + rolled accumulation). Total remains 21 units
(7 accumulation + 14 ladder), matching `cy1_lifecycle.json`'s `units_filled_of_21`.

**Gate impact: none.** Accumulation filled 3/3 in every historical episode
(EP2/EP3/EP4/EP5), so this branch was never exercised in-sample — which is why it
stayed ambiguous. §11 and G1–G5 are unaffected. The second leg *was* exercised in
all four: EP2 (0.786 unfilled), EP3 and EP4 (all three rungs unfilled), EP5 (0.62,
0.786) — each resolving to a breakout fill.

**Live exposure:** EP6 is on track to be the first episode to exercise the first
leg. No tranche is filled and BTC sits far above T1 (≈52.9k) with BoS at 82,850, so
a break of structure without a revisit to the realized line rolls the **entire**
accumulation pool — a third of total capital — down an untested path. A synthetic
fixture covering it is required before live arming; historical coverage does not
exist.

**OQ-4 — §11's pnl figures do not match the reference implementation.**

| Episode | §11 | `cy1_lifecycle.json` | Δ |
|---|---|---|---|
| EP2-2014 | +480.9% | 480.20 | +0.70 |
| EP3-2018 | +881.0% | 879.89 | +1.11 |
| EP4-2020 | +715.5% | 714.63 | +0.87 |
| EP5-2022 | +339.7% | 339.18 | +0.52 |
| **Sum** | **+2,417%** | **2,413.90** | **+3.10** |

All four are biased the same direction and are too large to be rounding. Fill
dates/prices, exit dates/prices and the cash-flow model all reconcile exactly, so
the discrepancy is isolated to these five numbers. *Either restate §11 from the
reference run, or identify the run that produced these — §9 forbids restating a
record without a reason on file.*

**OQ-6 — EP1's "EXPIRED" rests on a data artifact, and §0/§11 justify each other
in a circle. → RAISED 2026-07-25 by execution, during the M1 build.**

§11 records EP1 as `EXPIRED`, and §13.3's prose attributes that to the
trigger-anchor guard rejecting "its 2013-era candidates descend[ed] from the
Dec-2013 ATH". **Executed against the frozen data, neither part holds.**

What actually expires EP1 is the guard `monday(D) < trigger_week` failing because
D *is* the trigger week — and D is the trigger week only because of the suspect
Bitstamp wick §0 already flags. On 2011-11-25 the bar opens 2.50, closes 2.75 and
prints a **15.00** high; every other day that week tops at 3.00.

Clamp that wick to any sane value (2.75 / 3.00 / 4.00 all give the same result)
and: **D moves to 11.85 @ wk 2011-08-15, the guard passes, the scan yields 12
candidates, and EP1 activates with a BoS on 2011-12-20** — well inside its expiry
bound. It trades.

A per-candidate reading of the guard does not rescue the prose either: all 12
candidates carry anchors between 2011-08-29 and 2011-10-03, every one *strictly
before* the 2011-11-21 trigger. The scan never reaches 2013, so the 2013-era
anchors §13.3 blames are never even evaluated.

**The artifact does double duty — which makes the circularity worse, not better
(refined 2026-07-25 during the M1 gate build).** Bypassing only the *guard*, while
leaving the wick in place, still yields no trade: the scan produces 11 candidates
but every one has `confirmed_at = None`. That is not an independent rule basis —
it is the same artifact acting a second time. Because the wick makes the trigger
week itself the argmax, D lands *after* the real 2011 bottom (2.22, printed
2011-10-20/21), so the scan window is truncated, every rally origin `L₀` collapses
to the minimum of what remains, and confirmation becomes impossible by
construction. Remove the wick and both mechanisms release together.

So EP1's expiry is doubly determined by one bad print. A mutation of the guard
looks "chain-equivalent" on the frozen data, but that means the guard is
**unexercised**, not that it is validated.

**The circularity:** §0 dismisses the wick as a known wart on the grounds that
"EP1 is expired under v1.1 anyway — see §11", while §11's `EXPIRED` row is
produced *solely* by that wick. Neither section carries an independent basis.

**Not currently blocking:** no §10 gate covers EP1, and §11's regression fixtures
run EP2–EP5, so nothing in the M1 suite asserts this. **It must be settled before
EP1's status is quoted as a rule outcome** — and it bears on the honesty of the
record, since an EP1 that trades would add a fifth episode to a record described
as "4 clean episodes".

*Decide: (a) accept the artifact and say so explicitly in §11, (b) clean or
exclude the 2011 thin-market data and accept whatever EP1 then does, or (c) find
the independent rule basis the prose asserts but the algorithm does not apply.*

**OQ-5 — EP3's 2019 BoS still lacks owner sign-off.**
Flagged in Amendment 1 and in §11 ("no owner anchor for 2019 — rule output, owner
sign-off pending"). It contributes +879.89% — **36% of the headline sum**. Until
signed off, +2,417% (or 2,413.9%) is provisional and every surface quoting it
should say so.
