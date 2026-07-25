# CY-1 — Owner BTC Cycle System, Frozen Specification

**Frozen 2026-07-22 by owner instruction ("yes freeze this").**
Criteria may NEVER loosen. Amendment-by-addition only, each amendment owner-approved
and committed. This gate is episode-scale: it is NOT evaluated by the nightly
`monitoring/gate_evaluator.py`; evaluation is manual at episode events.

Validation lineage (all committed in `dashboard-data/`):
`episodes_dashboard.json` (entry rules, 5/5 episodes win, owner 2020+2022 gates
reproduced), `beta_exit_v2.json` (mirror exit, v3 prior-bear arming),
`v4_lifecycle.json` (accumulation + extensions + all-spot variants),
inline 70/30 → 1:2:4 → cash-flow computations (session 2026-07-22).

## Instrument & mode

BTC spot only. **No leverage, ever** (owner: "leverage shd be for short term
trading, not cycle trading"). Personal book — OUT of v4 gate accounting.

## Episode trigger

BTC **weekly RSI-14 < 35** arms an episode ("watching").

## Capital plan

- **Capital on hand at trigger** → bottom accumulation ladder, weights **1 : 2 : 4**:
  - T1 (1/7) at **realized price** (CoinMetrics: CapMrktCurUSD / CapMVRVCur / SplyCur)
  - T2 (2/7) at **midpoint(realized, balanced)**
  - T3 (4/7) at **balanced price** (Puell: realized − transferred; reference series:
    checkonchain full-history, validated vs the FTX-week touch)
  - Lines are evaluated walk-forward at each day's current value. Tranches that
    never fill roll their capital into the BoS-retracement deployment.
- **New savings ≈ $2,000/month from trigger** accrue in cash and deploy at the
  BoS-retracement ladder together with any unfilled accumulation capital.

## Entry structure (frozen from episodes_dashboard.json validation)

- **Lower high**: most recent weekly high preceded by a rally **≥ 25%** (R=25;
  rally-origin window excludes the candidate week's own low), **confirmed by a
  subsequent lower low**; a confirmed LH dies if any later weekly high exceeds it.
  The LH may predate the RSI trigger.
- **BoS**: intraweek trade above the confirmed LH.
- **BoS-retracement ladder** (for reserve cash): fills at **0.5 / 0.62 / 0.786**
  retracement of the leg (episode low → BoS-week high), weighted **2 : 4 : 8**.
  The 0.328 level is **skipped** (owner instruction; historical cost ≈ 0).
  Unfilled ladder units join the **breakout fallback**: buy at the first new high
  above the BoS-week high.

## Exits (frozen)

1. **50% of total position at the 1.272 extension of the prior bear leg**:
   level = episode_low + 1.272 × (prior_cycle_ATH − episode_low).
   (Owner's "~84k" for the 2022 episode = 1.272, printed 2024-11-11 @ 83,559;
   1.272 beat 1.212 in all four clean episodes.)
2. **Remaining 50% at the armed mirror exit**:
   - Arming: the 1.272 level having been crossed (i.e., exit #1 printed).
   - Signal: intraweek trade **below** the most recent confirmed swing low
     (swing low = weekly low preceded by a decline **≥ 10%** [R_down=10],
     confirmed by a subsequent higher high; confirmation strictly precedes the
     break; position-lifetime scope).
   - Fill: BTC's bounce to **50% of the decline leg**, leg = (top high +
     low-so-far)/2 computed **walk-forward** (low-so-far includes the current
     day's low before testing its high; break day excluded).
   - Fallback: if no 50% bounce within **8 weeks**, sell at market.
   - Owner verification gate for the detector (must always reproduce):
     signal week 2025-10-06 breaking the ~107k Aug/Sep-2025 double bottom,
     fill 2025-10-12 @ ~114,100.
3. **Stop, all phases: episode-low touch.** At spot this stop is real everywhere
   (no liquidation line).

## Beta sleeve (linked, personal)

80/20 BTC/beta concept validated (`beta_exit_v2.json` v3): beta bought on BTC's
signal dates, held through BTC's ladder exits, sold ONLY at the armed mirror exit
(same detector/arming) or the episode-low rescue stop. Owner's live intent: SOL,
personal accumulation zone $40+. High-beta mechanical picks can round-trip
(OP −55.5% in-sample) — beta choice is the owner's, not mechanical.

## Historical record under exactly the frozen rules (4 clean episodes, 2014→2025)

- Accumulation-only (1:2:4, hold-through, 1.272+mirror): **+2,417% summed**
- Cash-flow model ($10k at trigger + $2k/mo to BoS): **$106,000 in → $544,798 out
  (blended 5.14x)**; per-episode MOIC 3.91x–7.07x
- Zero stop-outs; worst sit-throughs: −49% (2014 accumulation), −64% MAE (2019
  spot through COVID)
- Rejected variants on file: 3x perp lifecycle (+3,694% but liq line above the
  episode low for the dominant tranche in every episode; two <20% near-misses),
  BoS-sale rotation (loses coins at 1x), 0.328 ladder level (noise), fixed 70/30
  (dominated by cash-flow model), TP1-anchored mirror arming (whipsaws: Jan-2024).

## EP6 live card (state at freeze, 2026-07-22)

- Trigger 2026-02-01 (wRSI 32.4). Watching. Prior ATH 126,200; running low 57,800.
- Confirmed LH: 82,850 (week of 2026-05-10). **BoS trigger: weekly high > 82,850.**
- Accumulation lines (2026-07-19 data): **T1 ≈ 52,848 · T2 ≈ 45,849 · T3 ≈ 38,851**
  (dynamic — tracked by `scripts/cycle_watch.py`). No tranche filled yet.
- Prospective 1.272 exit level if the 57,800 low holds: ≈ 144,800 (moves with the low).

---

## Amendment 1 — 2026-07-23 (owner correction: "have to be precise, otherwise money is left on the table")

**Supersedes the "Lower high" definition in Entry structure. All other rules unchanged.**

- **Lower high (v1.1)**: a weekly high whose rally **originates from a FRESH LOW of the
  episode downtrend** (the origin low undercuts ALL prior lows of the downtrend scope),
  with rally **≥ 15%** (R_e=15 — the unique value passing all owner verification gates),
  **confirmed** by a subsequent low undercutting the origin low. The candidate's
  downtrend anchor (the high its fresh low descends from) must predate the episode
  trigger (guard against latching onto the next cycle's breakdown — required to fix a
  hard EP1 failure). Operative LH = most recent valid candidate; invalidation and BoS
  definition unchanged.
- **Owner verification gates (all reproduce, R_e=15 uniquely)**:
  - NEW: 2014-12-29 wk low 255 < 2014-09-29 wk low 275 → LH 305.00 (wk 2015-01-05,
    +19.6% off fresh 255, confirmed by 152.40) → **BoS wk 2015-01-26 @ 309.90**
  - 2020: LH 10,500 → BoS late-July-2020 (unchanged)
  - 2022: LH 25,211.32 → BoS wk 2023-02-13 (unchanged; Sept/Oct-2022 highs excluded
    because their origins never undercut June's 17,622 — the structural reason, not a
    degree coincidence; R_e also rejects the +11% FTX micro-bounce)
- **Record impact**: EP1-2011 EXPIRED (its 2013 trade was structurally invalid — no
  fresh-low LH; the +54.7%/+4,406% rows are withdrawn, not restated as losses).
  EP2 leg = 152.40 → 309.90; reserve fills 231.15 / 212.25 (0.786 @ 186.10 never
  fills; Aug-2015 low 198.12), breakout 2015-07-12 @ 309.90; CY-1 exits unchanged.
  EP3 BoS moved to wk 2019-04-01, breakout 5,275 (**no owner anchor covered 2019 —
  owner sign-off pending; flagged, not silently adopted**). EP4/EP5 unchanged.
  Clean-episode sum +2,417%; cash-flow model $82k → $470k (5.73x).
- **EP6 live**: operative LH **82,850 — unchanged** (the 2026-06-21 bounce high 67,292
  was +13.8% < 15; newer bounces off 57,800 unconfirmed). BoS trigger stays
  **intraweek trade > 82,850**.
