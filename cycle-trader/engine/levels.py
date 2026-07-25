"""Retracement ladder, the 1.272 extension, and the walk-forward mirror
target — SPEC §5 and §6.

Decimal-context convention (decided in Task 8, deferred from Task 1)
--------------------------------------------------------------------
Unlike the on-chain lines, every function here multiplies by a fraction
(0.5 / 0.62 / 0.786 / 1.272), and `decimal` rounds each such result to the
*ambient* context precision — process-global mutable state that any other
module in the serverless bundle can change. Measured against a prec=50
baseline on the G1 ladder, all four episode extensions and the G4 mirror
target:

    prec >= 10   exact (zero deviation)
    prec  7..9   <= 0.002 absolute
    prec  6      0.028 absolute   -> breaks the +-0.01 test assertions
    prec  3      0.55% relative   -> breaks SPEC §10's +-0.5% gate tolerance

The default of 28 is therefore safe by a wide margin, but "safe unless
someone else changes it" is not good enough for a module whose entire
purpose is reproducing frozen gates. These functions run in the engine-wide
pinned context `engine.context.CTX` (prec=34 — IEEE decimal128, ~3x the 10
digits needed here — ROUND_HALF_EVEN, default traps), so a caller cannot
perturb a level by lowering precision, changing the rounding mode, or
arming the Inexact trap. See `engine/context.py` for the convention and for
the same measurement applied to `rsi.py` and `structure.py`.

Values are **not** quantised. SPEC records 231.15 / 212.25 / 186.10 and
83,558.53, but 186.10 is really 186.105 and 83,558.53 is 83,558.528 (§13.1
itself writes the latter as "83,558.5"); §10 compares at +-0.5%. The 2dp is
presentational, not normative, so the engine returns the exact arithmetic
and each surface formats it.
"""
from __future__ import annotations
from decimal import Decimal, localcontext
from engine.context import CTX

LADDER = {"0.5": Decimal("0.5"), "0.62": Decimal("0.62"), "0.786": Decimal("0.786")}
LADDER_UNITS = {"0.5": Decimal(2), "0.62": Decimal(4), "0.786": Decimal(8)}
EXT = Decimal("1.272")


def ladder_levels(el_star: Decimal, bos_week_high: Decimal) -> dict[str, Decimal]:
    """price = BoS-week high - level x (BoS-week high - EL*). 0.328 is skipped."""
    with localcontext(CTX):
        leg = bos_week_high - el_star
        return {name: bos_week_high - frac * leg for name, frac in LADDER.items()}


def extension_1272(el_star: Decimal, prior_ath: Decimal) -> Decimal:
    """SPEC §6.1 Exit 1: EL* + 1.272 x (prior ATH - EL*)."""
    with localcontext(CTX):
        return el_star + EXT * (prior_ath - el_star)


def mirror_target(top_high: Decimal, low_so_far: Decimal) -> Decimal:
    """50% of the decline leg, recomputed walk-forward as the low falls."""
    with localcontext(CTX):
        return (top_high + low_so_far) / Decimal(2)
