# BoS-FVG-RSI Reversal — usage

1. TradingView → Pine Editor → paste `bos_fvg_rsi.pine` → "Add to chart".
2. Costs & position size: Settings → **Properties** tab (commission 0.045% + 2-tick slippage are pre-set defaults).
3. Works on any symbol/timeframe — the logic uses only the chart interval.
4. What you'll see: green line = the minor interim high (your BoS line) while a setup is armed; teal dashed = running impulse high (TP1); green box = FVG entry zone; L2/BoS markers; top-right table counts setups skipped for having no FVG.
5. **Entry (default): fib scale-in** — three equal limit orders at the 50% / 61.8% / 78.6% retracements of the breaking leg (levels are inputs; three blue lines on the chart). Total size = `Total position % equity` input (default 10%, split ×3). Unfilled tranches keep working while the trade runs (true scale-in) until structure fails or the entry window times out. FVG single-entry modes remain available under `Entry mode` for comparison.
6. Tune first (in this order): `RSI threshold` 30/35/40 → `Stop mode` last_low/zone/atr (zone = deepest fib) → `Runner exit` supertrend vs MA → fib levels themselves → `TP1 %`.
6. Shorts are OFF by default (`Enable shorts` mirrors everything).

Known limitations (also in the file header): pivots confirm `pivotLen` bars late (no lookahead — honest but laggy); one position at a time; setups without an FVG are skipped and counted; the protective stop activates at the close of the fill bar (standard bar-based backtest caveat).

If the Pine editor throws ANY compile error, paste it back to Trinity — immediate fix round with Grok.
Next step when you're happy with the tuned params: port to the v4 paper forward-test harness with a fresh pre-registered gate (the FB-1-replacement path).
