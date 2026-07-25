"""The engine's pinned decimal arithmetic context.

`decimal`'s context is process-global mutable state (thread-local, but shared by
everything on the thread). Any co-resident library in the Vercel bundle can lower
`prec`, change the rounding mode, or arm `traps[Inexact]`, and every inexact
computation in `engine/` would silently move — or raise — with CI, which runs the
gates in a clean process, never seeing it. A package whose purpose is reproducing
frozen gates must not carry a correctness precondition it cannot observe.

So every function in `engine/` that performs **inexact** arithmetic runs its
arithmetic inside ``with localcontext(CTX):``. This is not a purity violation: it
removes a dependency on ambient state that is not an argument, which is precisely
what the purity rule exists to prevent.

Measured effect of a lowered ambient precision on real decisions (frozen series,
5,451 daily bars / 780 weeks, 2011-08-15 → 2026-07-20):

| module | inexact op | what it feeds | ambient-dependent from |
|---|---|---|---|
| `types.py` | `OnChain.midpoint` = `(realized + balanced) / 2` | the T2 **fill price** | prec ≤ 10 |
| `levels.py` | x 0.5 / 0.62 / 0.786 / 1.272, `/2` | ladder + exit **prices** | prec ≤ 9 |
| `rsi.py` | `/period`, `100/(1+rs)` | strict `rsi < 35` trigger | prec ≤ 2 (flip) |
| `structure.py` | rally % | strict `rally < R_e=15` | prec = 1 (flip) |

Threshold-feeding computations get a second number, because "the output moved"
and "a decision changed" are different questions:

| module | tightest real margin to its threshold | error clears it from |
|---|---|---|
| `rsi.py` | 0.0373 RSI pts (2012-02-13 @ 35.0373) | prec ≥ 5 |
| `structure.py` | 0.4988 pts (wk 2025-11-24 @ +15.4988%) | prec ≥ 4 |

An RSI flip at prec ≤ 2 moves EP5's trigger to 2022-05-09 and EP6's to
2025-12-22; a rally flip at prec 1 drops EP6 from 12 candidates to 8 and EP4
from 25 to 24. Price-producing computations have no threshold and so no margin —
any deviation is simply a wrong price.

`prec=34` is IEEE decimal128, above every requirement here. The two that bind:
`levels.py` needs **prec >= 10** for its levels to be exact, and `types.py`'s
`midpoint` needs **28, or 29 when the sum carries** — the CoinMetrics-derived
`realized` arrives with 28 significant digits, so the sum needs 28 or 29 and the
halving adds none. (Below that the midpoint is merely *rounded*, not wrong: at
prec 28 the worst deviation measured over the full history is 5e-28 relative,
which is why pinning it changed no historical fill.) `ROUND_HALF_EVEN` is `decimal`'s own
default, pinned so the context is fully specified rather than half-inherited;
at prec 34 no result here rounds, so the mode is currently unobservable. Default
traps, so an ambient `traps[Inexact]` cannot turn a level into an exception.

Modules needing **no** pin, because they perform no inexact arithmetic:

- `bars.py` — `min`/`max`/selection over raw OHLC plus `datetime`; no Decimal ops.
- `fills.py` — `min`/`max` of two exact values, and comparisons.
- `lifecycle.py` — `min`/`max`/argmax selection and comparisons only. Its
  `RSI_TRIGGER` comparison is exact; the *input* is what needed pinning, hence
  `rsi.py`.
- `lines.py` — pure delegation: it selects and returns `oc.realized`,
  `oc.midpoint` and `oc.balanced`. Two are stored fields; **`midpoint` is
  computed**, and it is pinned at its definition in `types.py` rather than here,
  so every caller of the property is covered rather than only this one.

`types.py` is a **mixed** case and was misfiled in this list until 2026-07-25:
its `_dec` coercion is `Decimal(str(v))` *construction*, which by design is
unaffected by context precision, but `OnChain.midpoint` is *arithmetic* and is
pinned. Construction being context-free does not clear a module that also
computes.

Exact arithmetic (`+`, `-`, `*`, and `/` that terminates) is only rounded when the
result exceeds the context precision, which is why `levels.py` still needs the pin
while `fills.py` does not: multiplying by 0.786 grows the digit count, comparing
two prices does not.

**The test for this list is "does the module compute?", not "does it look like a
value object?"** Both original misfilings — `types.py` and `lines.py` — came from
classifying by a module's apparent role instead of by its operations. Anything
added to `engine/` should be checked expression by expression.

**Note for M2 (data adapters).** `data/loaders.py` derives realized price as
`mc / mv / sp`, unpinned, and that is why `OnChain.realized` arrives carrying
whatever the ambient precision was — 28 digits by default — which then feeds
`midpoint` above. `midpoint`'s pin makes the *midpoint* deterministic given its
inputs; it cannot make the inputs deterministic. The loader is test-only today
(its docstring forbids `engine/` importing it) and M2 replaces it, so the real
adapters must adopt `CTX` for the full chain to be reproducible.
"""
from __future__ import annotations
from decimal import Context, ROUND_HALF_EVEN

#: Pinned engine-wide. See the module docstring for the measurements behind it.
CTX = Context(prec=34, rounding=ROUND_HALF_EVEN)
