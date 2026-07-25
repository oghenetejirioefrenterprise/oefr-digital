"""The desired order set for an episode state — SPEC §3, §5, §6, §13.1, §13.2,
and §14 OQ-3 (resolved by the owner 2026-07-24).

This is the layer where computed levels become **instructions to spend money**.
Everything below it is arithmetic; everything above it is I/O. Two consequences
shape the whole module.

**1. Refuse; never emit a partial set.**
The daily run is a desired-state *reconciler* (v2 design §4): it diffs this
tuple against what is resting at the venue and cancels whatever is not here. So
"return fewer orders" is not a conservative degradation — it is an instruction
to cancel, and the order most likely to be dropped by a missing input is the
stop. The project's stated safe failure mode is the opposite: *a failed run
changes nothing and never cancels — resting orders are the safe state when the
system is blind.* Every incoherent input therefore raises `ValueError` rather
than producing a smaller set. That includes the fallthrough for an unrecognised
`EpisodeStatus`: an implicit `return ()` there would read as "cancel
everything" the day a status is added.

**2. The inverted-leg guard.**
`levels.ladder_levels` is deliberately unvalidated arithmetic — it is pure
retracement maths and Task 8 left it that way. Fed `el_star=100000,
bos_week_high=90000` it returns 95,000 / 96,200 / 97,860, i.e. every rung
*above* the BoS high, without complaint. Those become resting **buy-limits**,
and a buy-limit above market fills immediately at market: the system would spend
the entire ladder pool instantly, at the worst available price, having been
asked to buy dips. The ordering is structurally guaranteed upstream
(`bos_week_high >= BoS-day high > operative LH > fresh low >= EL*`) and the
gates would catch a violation loudly on historical data — but the gates cannot
catch a bad live print in 2027, and this function is what that print reaches
first. The guard is strict (`<=` refused, not just `<`): a zero-length leg
collapses all three rungs onto the BoS high *and* onto the stop, which is not a
harmless boundary. The sell side gets the mirror-image guard: a 1.272 extension
priced at or below `EL*` is a sell-limit under market, which fills instantly at
`max(level, open)` (§13.2).

**Sell-side sizing rule (2026-07-24 review).** Every sell order is sized from
`held_units` — what the account actually holds — never from the capital plan. A
stop for 21 units against a 7-unit position is an order to sell BTC that does
not exist; the venue rejects it and the guard aborts the run. With
`held_units == 0` nothing sell-side may rest. M1 has no fill tracking, so
callers pass 0; M2 feeds it from venue trade history.

**Decimal context.** `roll_unfilled` divides by the ladder's total weight and
that division is genuinely inexact for six of the eight reachable pools (14+1
through 14+6), so it runs inside `with localcontext(CTX):` per the engine-wide
convention in `engine/context.py` — an ambient `prec` change would otherwise
resize every rolled rung. Exit 1's halving is *not* inexact (`/2` terminates in
base 10 for any finite Decimal) and is left unpinned; it would round only if
`held_units` carried more than `prec` significant digits, which a venue balance
does not. Everything else here is comparison, selection and dict lookup.
"""
from __future__ import annotations

from decimal import Decimal, localcontext

from engine.context import CTX
from engine.levels import LADDER_UNITS, extension_1272, ladder_levels
from engine.types import (DesiredOrder, EpisodeState, EpisodeStatus, OrderKind,
                          OrderPurpose, OrderSide)

#: SPEC §2 — accumulation weighted 1 : 2 : 4 across T1 : T2 : T3 (1/7, 2/7, 4/7).
ACC_UNITS = {OrderPurpose.T1: Decimal(1),
             OrderPurpose.T2: Decimal(2),
             OrderPurpose.T3: Decimal(4)}
ACC_TOTAL = sum(ACC_UNITS.values(), Decimal(0))          # 7
#: Which key of the daily `lines` dict prices each tranche (SPEC §3).
ACC_LINE_KEY = {OrderPurpose.T1: "t1", OrderPurpose.T2: "t2", OrderPurpose.T3: "t3"}
#: Joined to `LADDER_UNITS` / `ladder_levels` BY KEY. `LADDER_UNITS.keys() ==
#: LADDER.keys()` is asserted upstream but their *order* is not, so zipping the
#: two would be silently wrong the day either dict is reordered.
LADDER_PURPOSE = {"0.5": OrderPurpose.LADDER_050,
                  "0.62": OrderPurpose.LADDER_062,
                  "0.786": OrderPurpose.LADDER_0786}
#: SPEC §14 OQ-3: 21 units = 7 accumulation + 14 ladder. Gate-passing constants.
TOTAL_UNITS = Decimal(21)
#: Nothing rests: no episode, or the episode is over and the reconciler clears.
NO_ORDERS = (EpisodeStatus.IDLE, EpisodeStatus.CLOSED, EpisodeStatus.STOPPED,
             EpisodeStatus.EXPIRED)


def roll_unfilled(acc_unfilled_units: Decimal,
                  ladder_units: Decimal) -> dict[str, Decimal]:
    """OQ-3 leg 1: unfilled accumulation joins the LADDER pool, keeping 2 : 4 : 8.

    Owner decision 2026-07-24 — *"unfilled accumulation capital goes to the
    ladder and unfulfilled ladder goes to the breakout"* — confirming §3/§5 as
    written against `cy1_lifecycle.json`, which rolls straight to the breakout
    and is the deviation. The weights are ratios applied to whatever the pool
    holds (reserve cash + savings + rolled accumulation), so the split is
    recomputed from the pool rather than added to the base sizes.

    Conservation is exact for all eight reachable pools (14 + 0..7), verified in
    the tests: the three quotients sum back to the pool even where each is a
    34-digit repeating expansion.
    """
    if acc_unfilled_units < 0:
        raise ValueError(f"acc_unfilled_units must not be negative, got {acc_unfilled_units}")
    if ladder_units <= 0:
        raise ValueError(f"ladder_units must be positive, got {ladder_units}")
    pool = ladder_units + acc_unfilled_units
    total_weight = sum(LADDER_UNITS.values(), Decimal(0))
    with localcontext(CTX):
        return {name: pool * weight / total_weight
                for name, weight in LADDER_UNITS.items()}


def desired_orders(state: EpisodeState,
                   lines: dict[str, Decimal],
                   filled_purposes: set[OrderPurpose],
                   held_units: Decimal,
                   total_units: Decimal = TOTAL_UNITS) -> tuple[DesiredOrder, ...]:
    """The complete set of orders that should be resting for `state`.

    Idempotent and stateless: the same arguments always give the same tuple, so
    a skipped or double-fired cron is harmless and a crashed run self-heals on
    the next one.

    `lines` carries the day's accumulation line values under ``"t1"``/``"t2"``/
    ``"t3"`` (SPEC §3) and, in `DISTRIBUTING`, the mirror target under
    ``"mirror"`` plus a truthy ``"mirror_fallback"`` once §6.2's 8-week deadline
    has passed. `filled_purposes` is what has already executed;
    `held_units` is what the account holds *now*.

    Raises `ValueError` on any state that cannot be turned into a coherent order
    set — see the module docstring for why refusing beats emitting a smaller set.
    """
    if held_units < 0:
        raise ValueError(f"held_units must not be negative, got {held_units}")
    if total_units <= ACC_TOTAL:
        raise ValueError(
            f"total_units must exceed the {ACC_TOTAL}-unit accumulation pool "
            f"(the remainder is the ladder pool), got {total_units}")

    if state.status in NO_ORDERS:
        return ()
    if state.status is EpisodeStatus.WATCHING:
        return _watching(state, lines, filled_purposes)
    if state.status is EpisodeStatus.CONFIRMED:
        return _confirmed(state, filled_purposes, held_units, total_units)
    if state.status is EpisodeStatus.DISTRIBUTING:
        return _distributing(state, lines, held_units)
    raise ValueError(
        f"unhandled episode status {state.status!r}: refusing rather than "
        "returning an empty desired set, which the reconciler reads as "
        "'cancel every resting order'")


def _watching(state: EpisodeState, lines: dict[str, Decimal],
              filled_purposes: set[OrderPurpose]) -> tuple[DesiredOrder, ...]:
    """Pre-BoS: the three accumulation buy-limits, re-priced every run as the
    lines move (SPEC §3, walk-forward).

    No stop — SPEC §13.1: before the BoS a new low simply updates the running
    anchor and is not a stop event. No exits either: the 1.272 level drifts down
    with the anchor until the BoS freezes it, so there is nothing stable to rest.
    """
    out: list[DesiredOrder] = []
    for purpose, key in ACC_LINE_KEY.items():
        if purpose in filled_purposes:
            continue                     # a filled tranche is not re-rested
        if key not in lines:
            raise ValueError(
                f"WATCHING episode has no {key!r} accumulation line: refusing "
                "rather than dropping that tranche from the desired set, which "
                "would cancel a live resting order on a dead data feed")
        if lines[key] <= 0:
            raise ValueError(f"accumulation line {key!r} must be positive, got {lines[key]}")
        out.append(DesiredOrder(purpose=purpose, side=OrderSide.BUY,
                                kind=OrderKind.LIMIT, price=lines[key],
                                units=ACC_UNITS[purpose]))
    return tuple(out)


def _confirmed(state: EpisodeState, filled_purposes: set[OrderPurpose],
               held_units: Decimal,
               total_units: Decimal) -> tuple[DesiredOrder, ...]:
    """Post-BoS: the retracement ladder, the breakout fallback, the stop, and
    Exit 1 (SPEC §5, §6.1, §6.3).

    Accumulation is *not* re-rested here: §13.6 kills the lines at the BoS day
    inclusive, and their unfilled capital rolls rather than their orders
    surviving.
    """
    if state.el_star is None or state.bos_week_high is None:
        raise ValueError(
            "CONFIRMED episode needs both el_star and bos_week_high "
            f"(got el_star={state.el_star!r}, bos_week_high={state.bos_week_high!r}); "
            "refusing rather than resting a ladder with no stop behind it")
    if state.bos_week_high <= state.el_star:
        raise ValueError(
            f"inverted BoS leg: bos_week_high {state.bos_week_high} <= el_star "
            f"{state.el_star}. Every ladder rung would price at or above the "
            "breakout level, and a resting buy-limit above market fills "
            "immediately at market — the whole ladder pool spent at the worst "
            "price. Refusing the run leaves existing orders untouched.")

    out: list[DesiredOrder] = []

    # OQ-3 leg 1 — accumulation that never filled joins the ladder pool.
    acc_unfilled = sum((units for purpose, units in ACC_UNITS.items()
                        if purpose not in filled_purposes), Decimal(0))
    pool = roll_unfilled(acc_unfilled, total_units - ACC_TOTAL)
    levels = ladder_levels(state.el_star, state.bos_week_high)

    unfilled_ladder = Decimal(0)
    for name, price in levels.items():
        purpose = LADDER_PURPOSE[name]
        if purpose in filled_purposes:
            continue
        units = pool[name]
        unfilled_ladder += units
        out.append(DesiredOrder(purpose=purpose, side=OrderSide.BUY,
                                kind=OrderKind.LIMIT, price=price, units=units))

    # OQ-3 leg 2 — ladder rungs still unfilled join the breakout fallback.
    # Buy-STOP at the BoS-week high, not a limit: §13.2 and §5 both, and G1/G3
    # fill it *at* 309.90 / 25,250, which only max(level, open) reproduces.
    if unfilled_ladder > 0:
        out.append(DesiredOrder(purpose=OrderPurpose.BREAKOUT, side=OrderSide.BUY,
                                kind=OrderKind.STOP_MARKET,
                                price=state.bos_week_high, units=unfilled_ladder))

    if held_units > 0:
        # §6.3 as narrowed by §13.1: a touch of the frozen EL*, from the BoS
        # onward. Stop-market rather than stop-limit — a stop-limit can be
        # jumped in a fast breakdown, defeating the only protection CY-1 has.
        out.append(DesiredOrder(purpose=OrderPurpose.STOP, side=OrderSide.SELL,
                                kind=OrderKind.STOP_MARKET, price=state.el_star,
                                units=held_units))
        if not state.exit1_done and OrderPurpose.EXIT1 not in filled_purposes:
            if state.prior_ath is None:
                raise ValueError(
                    "CONFIRMED episode holds units but has no prior_ath: Exit 1's "
                    "1.272 extension cannot be priced")
            if state.prior_ath <= state.el_star:
                raise ValueError(
                    f"exit anchor {state.prior_ath} at or below el_star "
                    f"{state.el_star}: the 1.272 extension would price at or "
                    "under the stop, and a sell-limit below market fills "
                    "immediately at max(level, open)")
            out.append(DesiredOrder(purpose=OrderPurpose.EXIT1, side=OrderSide.SELL,
                                    kind=OrderKind.LIMIT,
                                    price=extension_1272(state.el_star, state.prior_ath),
                                    units=held_units / Decimal(2)))
    return tuple(out)


def _distributing(state: EpisodeState, lines: dict[str, Decimal],
                  held_units: Decimal) -> tuple[DesiredOrder, ...]:
    """Armed after Exit 1: the stop over the remainder, and the mirror exit once
    §6.2's signal has fired.

    `held_units` here is the post-Exit-1 remainder, from venue trade history.
    The mirror target does not exist before a signal, so nothing sell-side but
    the stop rests until `compute()` supplies one; the fallback *replaces* the
    limit rather than joining it, since both resting would sell the remainder
    twice.
    """
    if state.el_star is None:
        raise ValueError(
            "DISTRIBUTING episode has no el_star: the stop cannot be priced, and "
            "an order set without it would cancel the live stop")

    out: list[DesiredOrder] = []
    if held_units > 0:
        out.append(DesiredOrder(purpose=OrderPurpose.STOP, side=OrderSide.SELL,
                                kind=OrderKind.STOP_MARKET, price=state.el_star,
                                units=held_units))
        if lines.get("mirror_fallback"):
            # §6.2: 8 weeks past the signal with no 50% bounce -> sell at market.
            # Truthiness, not membership: a caller that always supplies the key
            # as a 0/1 flag must not trip the fallback while it reads 0.
            out.append(DesiredOrder(purpose=OrderPurpose.MIRROR, side=OrderSide.SELL,
                                    kind=OrderKind.MARKET, price=None,
                                    units=held_units))
        elif "mirror" in lines:
            # Present only once the mirror SIGNAL has fired (armed + swing-low
            # break, confirmation strictly preceding the break). compute() gates
            # this; no signal, no resting mirror sell (SPEC §6.2).
            out.append(DesiredOrder(purpose=OrderPurpose.MIRROR, side=OrderSide.SELL,
                                    kind=OrderKind.LIMIT, price=lines["mirror"],
                                    units=held_units))
    return tuple(out)
