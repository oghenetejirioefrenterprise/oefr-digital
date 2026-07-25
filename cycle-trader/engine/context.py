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

| module | inexact op | tightest real margin | flips at | safe by margin |
|---|---|---|---|---|
| `levels.py` | x fraction | ±0.5% gate tolerance (SPEC §10) | prec ≤ 3 | prec ≥ 10 (exact) |
| `rsi.py` | `/period`, `100/(1+rs)` | 0.0373 RSI pts (2012-02-13 @ 35.037) | prec ≤ 2 | prec ≥ 5 |
| `structure.py` | rally % | 0.4988 pts (2025-11-24 @ +15.4988%) | prec = 1 | prec ≥ 4 |

`prec=34` is IEEE decimal128 — 3x the widest requirement (`levels.py` needs 10)
and far above every flip threshold above. `ROUND_HALF_EVEN` is `decimal`'s own
default, pinned so the context is fully specified rather than half-inherited;
at prec 34 no result here rounds, so the mode is currently unobservable. Default
traps, so an ambient `traps[Inexact]` cannot turn a level into an exception.

Modules needing **no** pin, because they perform no inexact arithmetic:

- `bars.py` — `min`/`max`/selection over raw OHLC plus `datetime`; no Decimal ops.
- `lines.py` — returns stored fields unchanged.
- `fills.py` — `min`/`max` of two exact values, and comparisons.
- `lifecycle.py` — `min`/`max`/argmax selection and comparisons only. Its
  `RSI_TRIGGER` comparison is exact; the *input* is what needed pinning, hence
  `rsi.py`.
- `types.py` — `Decimal(str(v))` construction, which by design is unaffected by
  context precision.

Exact arithmetic (`+`, `-`, `*`, and `/` that terminates) is only rounded when the
result exceeds the context precision, which is why `levels.py` still needs the pin
while `fills.py` does not: multiplying by 0.786 grows the digit count, comparing
two prices does not.
"""
from __future__ import annotations
from decimal import Context, ROUND_HALF_EVEN

#: Pinned engine-wide. See the module docstring for the measurements behind it.
CTX = Context(prec=34, rounding=ROUND_HALF_EVEN)
