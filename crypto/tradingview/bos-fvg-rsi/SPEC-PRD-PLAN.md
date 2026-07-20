# BoS-FVG-RSI Reversal — TradingView Strategy (TJ's variant)

Owner: TJ · Author/judge: Trinity (Claude) · Implementer: Grok 4.5 (CLI) · Date: 2026-07-20
Deliverable: `bos_fvg_rsi.pine` — Pine Script **v6** `strategy()` for TradingView backtesting.

---

## 1. SPEC — the strategy, exactly as traded

Long-reversal strategy ("somewhat ICT, not exactly"). All rules mechanical. Works on ANY symbol and ANY chart timeframe (no `request.security`, everything on chart TF).

### 1.1 Structure state machine (long side)
1. **Pivots**: swing highs/lows via `ta.pivothigh/ta.pivotlow` with `pivotLen` left/right bars (input, default 3). Pivots confirm `pivotLen` bars late — accepted, never look ahead.
2. **Bearish context**: two consecutive confirmed pivot lows L1 then L2 with **L2 < L1** (lower low). The confirmed pivot high between L1 and L2 is **H_int — "the green line"** (minor interim high).
3. **RSI qualification (the trigger filter)**: RSI(`rsiLen`, default 14) at L2's bar must be **< `rsiThresh` (input, default 35)**. If RSI at the L2 bar ≥ threshold, the setup is void. (Use the RSI value on the actual pivot bar, i.e. `rsi[pivotLen]` at confirmation.)
4. **Break of Structure**: a candle **closes above H_int** while the setup is armed. BoS bar noted. Setup arming expires if price closes below L2 first (structure failed) or after `armTimeout` bars (input, default 50) without a BoS.
5. **Impulse leg & high**: from the BoS bar onward, track `impulseHigh = ta.max(high)` until entry triggers or setup cancels. TP1 anchors to the running impulse high at entry time ("the high that caused the BoS").

### 1.2 Entry — retrace into FVG
6. **FVG detection**: bullish 3-candle FVG (`low > high[2]`) formed in the breaking leg — bars from L2's bar through the BoS bar *inclusive of bars up to 3 after BoS* (the impulse often completes the gap after the close-through). Use the **most recent (highest) bullish FVG** in that leg. Zone = [gap bottom = `high[2]` of the gap, gap top = `low` of the gap bar].
7. **Entry order**: limit at **FVG top edge** (`entryMode` input: "FVG top" default | "FVG midpoint"). Entry valid while: no close below L2, and within `entryTimeout` bars of BoS (input, default 30). If price runs to TP1 level without filling → cancel (missed trade). No FVG found in the leg → no trade (count skipped setups via a label/counter for the owner's info).
8. One position at a time. `pyramiding=0`.

### 1.3 Exits
9. **Stop (default)**: `stopMode` input:
   - `"last_low"` (DEFAULT): below L2 by `stopBufPct` (input, default 0.1%).
   - `"zone"`: below the entry FVG bottom by the buffer.
   - `"atr"`: entry − `atrMult` (default 1.5) × ATR(`atrLen`, default 14).
10. **TP1**: at `impulseHigh` — close `tp1Pct` (input, default 50%) of the position. After TP1 fills, optionally move stop to breakeven (`beAfterTp1` input, default true).
11. **Final exit (runner)**: `exitMode` input:
    - `"supertrend"` (DEFAULT): exit remaining on Supertrend(`stAtrLen` 10, `stMult` 3.0) flip to bearish.
    - `"ma"`: exit on close below MA(`maType` EMA|SMA default EMA, `maLen` default 20).
    - Hard stop always active alongside the runner exit.

### 1.4 Shorts
12. `enableShorts` input, default **false**. When true: exact mirror (higher high → interim low = red line → RSI > 100−rsiThresh at the pivot high → close below interim low = BoS down → bearish FVG retrace → stop above last high → TP1 at impulse low → runner mirrored).

### 1.5 Backtest hygiene (non-negotiable)
13. **No repainting**: pivots only used after confirmation; no `lookahead`; no `request.security`; `calc_on_order_fills=false`; `process_orders_on_close=false` (default intrabar fills on limits are fine).
14. **Costs modeled**: `commission_type=strategy.commission.percent`, `commission_value` input default 0.045 (HL taker-ish); `slippage` input default 2 ticks. `default_qty_type=strategy.percent_of_equity`, `default_qty_value` input default 10.
15. **Date range filter** inputs (from/to) gating entries.
16. **Visuals**: green line (H_int) while armed; impulse-high line; FVG box (entry zone); entry/SL/TP1 lines while in trade; small marker on qualified L2 (RSI-passed) and on BoS bar; optional RSI value label. Keep drawing objects bounded (`max_boxes_count`/`max_lines_count` set, delete stale).

## 2. PRD
- **Goal**: TJ can paste ONE file into TradingView's Pine editor, hit "Add to chart", and backtest his exact rules on any symbol/TF, tuning: RSI threshold/length, pivot length, stop mode, entry mode, TP1 %, runner (Supertrend vs MA), shorts on/off, costs.
- **Non-goals (v1)**: alerts/webhooks, multi-TF confluence, liquidity-sweep or killzone logic (explicitly excluded by owner), live execution.
- **Acceptance criteria** (judge checklist):
  A1 compiles clean as Pine **v6** strategy; A2 zero repaint vectors (checklist §1.5); A3 every rule in §1.1–1.4 implemented and traceable to named code; A4 all listed inputs exist with stated defaults, grouped sensibly; A5 state machine cannot wedge (armed setups always expire/cancel/consume; verified by reading all state transitions); A6 visuals render and are bounded; A7 costs + date filter wired into results; A8 header comment documents each rule → code mapping + known limitations (pivot lag; single position; FVG-absent setups skipped).
- **Success measure**: owner reproduces his chart's setup visually on TV and gets a trade list; later, tuned params → candidate for the v4 paper-harness port with a pre-registered gate (SEPARATE follow-up project, not this deliverable).

## 3. PLAN
- **T1** (Claude): this document. ✅
- **T2** (Grok, via `grok` CLI): implement `bos_fvg_rsi.pine` from §1 verbatim. Prompt = full SPEC + Pine v6 pitfalls list.
- **T3** (Claude, judge): static review against A1–A8 (line-by-line vs spec; Pine v6 API misuse; repaint audit; state-machine walk). Findings → Grok fix round. Iterate ≤3 rounds; if still failing, Claude patches directly and notes it.
- **T4**: deliver file + 10-line usage note (how to load, what to tune first: rsiThresh 30/35/40 × stopMode × exitMode) to TJ; commit to `~/apps/crypto/tradingview/bos-fvg-rsi/`.
- **T5** (deferred, owner-gated): port tuned rules into the v4 paper forward-test harness with a new pre-registered gate (amendment-by-addition), per the FB-1-replacement path.
- **Judging limitation, stated honestly**: no local Pine compiler exists — A1 is finally proven only when TJ pastes it into TV. The review de-risks it; any compile error TJ hits comes back for an immediate fix round.

---
## AMENDMENT 1 (2026-07-20, owner): Fib scale-in entry
§1.2 replaced as DEFAULT entry: after BoS, place THREE equal limit orders at the 50%, 61.8%, 78.6% retracements of the breaking leg (impulseHigh → L2: price_k = impulseHigh − fib_k × (impulseHigh − L2)); fib levels are inputs (defaults 0.5/0.618/0.786). Levels track the RUNNING impulse high while flat (limits amended each bar). Total position = posPct input (% equity, default 10) split equally; contract qty computed per tranche. pyramiding=3. Tranches 2/3 stay working after earlier fills (scaling in through TRADE state) until: structure fail, position fully closed, or entryTimeout → cancel remaining. Exits WITHOUT from_entry (cover aggregate): "L-TP1" (qty_percent=tp1Pct, limit=TP1, stop) + "L-RUN" (stop always); BE reprices L-RUN. Missed-trade cancel anchors to the 50% (shallowest) level. FVG single-entry modes retained as alternates (entryMode input: "Fib scale-in" default | "FVG top" | "FVG midpoint"); no-FVG skip counter applies only to FVG modes. Shorts mirrored.
