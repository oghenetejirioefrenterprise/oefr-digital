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

**Decimal context.** Every unit computation in this module is pinned, via
`with localcontext(CTX):` or the `_total` helper. The generalisation that got
this wrong twice is worth stating plainly: **`decimal` rounds every result that
exceeds the context precision, whether or not the operation is exact.** So
"this operation is exact" is never on its own a reason to leave it unpinned —
only "this result cannot exceed `prec` digits" is, and unit counts are order
sizes, so being wrong about that is an over- or under-order rather than a
display artifact. Concretely, at an ambient `prec` of 1:

- `roll_unfilled`'s division by the total weight is genuinely inexact for six of
  the eight reachable pools (14+1 … 14+6);
- the running sum of rolled rung sizes that becomes the `BREAKOUT` quantity is
  three 34-digit values totalling `3E+1` — 30 units against a 15-unit pool;
- `ladder_units + acc_unfilled_units` (`14 + 1`) gives `2E+1`, and
  `total_units - ACC_TOTAL` (`21 - 7`) gives `1E+1`. Both addends exact, both
  results wrong;
- Exit 1's halving of `held_units` returns `1` against a true `1.0714…`.

That last one was excused in this module's first issue because `/2` terminates
in base 10. It does — but termination gives exactness only while the halved
coefficient still fits in `prec`, and `held_units` is plausibly a 34-digit
rolled rung size (a filled 0.5 rung on a 15-unit pool is exactly
`2.142857…143`). At prec 2 it returns `1.1`, a 2.7% over-sell. Everything
outside those is comparison, selection or dict lookup.
"""
from __future__ import annotations

from decimal import Decimal, localcontext

from engine.context import CTX
from engine.levels import LADDER_UNITS, extension_1272, ladder_levels
from engine.types import (DesiredOrder, EpisodeState, EpisodeStatus, OrderKind,
                          OrderPurpose, OrderSide)

def _total(values) -> Decimal:
    """Sum Decimals under the pinned context.

    `sum()` at ambient precision is not safe here even though every addend is
    exact: `decimal` rounds *every* result that exceeds the context precision,
    exact or not (see `engine/context.py`'s closing paragraph). At an ambient
    `prec` of 1, `Decimal(14) + Decimal(1)` is `2E+1`. Unit counts are order
    sizes, so that is a 33% over-order, not a display artifact.
    """
    with localcontext(CTX):
        total = Decimal(0)
        for value in values:
            total += value
        return total


#: SPEC §2 — accumulation weighted 1 : 2 : 4 across T1 : T2 : T3 (1/7, 2/7, 4/7).
ACC_UNITS = {OrderPurpose.T1: Decimal(1),
             OrderPurpose.T2: Decimal(2),
             OrderPurpose.T3: Decimal(4)}
ACC_TOTAL = _total(ACC_UNITS.values())                   # 7
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
#: Which side each purpose trades. The taxonomy lives here, next to the code
#: that emits every one of them, so adding a purpose puts the maintainer in
#: front of the classification instead of leaving a new name silently
#: unclassified. Completeness is asserted in
#: `tests/test_engine.py::test_every_order_purpose_is_classified_by_side`.
#:
#: `compute()` uses these to cross-check its two ledger inputs — see
#: `desired_orders`' note on why that check is NOT here.
BUY_PURPOSES = frozenset({OrderPurpose.T1, OrderPurpose.T2, OrderPurpose.T3,
                          OrderPurpose.LADDER_050, OrderPurpose.LADDER_062,
                          OrderPurpose.LADDER_0786, OrderPurpose.BREAKOUT})
SELL_PURPOSES = frozenset({OrderPurpose.EXIT1, OrderPurpose.MIRROR,
                           OrderPurpose.STOP})
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
    total_weight = _total(LADDER_UNITS.values())
    with localcontext(CTX):
        pool = ladder_units + acc_unfilled_units
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

    **Caller contract — `bos_week_high` must be the FINALISED BoS-week high.**
    This function has no date input and no clock, so it rests the breakout
    buy-stop as soon as the status is `CONFIRMED`. SPEC §5 scopes the fallback
    to *"the first daily trade above the BoS-week high **after the BoS week**"*,
    and that "after" is delegated entirely to the caller. Pass a *running*
    weekly high while the BoS week is still open and the buy-stop fills on any
    new high inside that week — buying the top of the very week that broke
    structure. The gates would catch it (G1 and G3 fill at exactly 309.90 and
    25,250, which only the settled-week reading reproduces), but they run in CI,
    not in front of the venue. `compute()` must not call this with `CONFIRMED`
    until the BoS week has closed.

    **`filled_purposes` and `held_units` are taken as independent ground truth
    here, and are NOT cross-checked.** They can contradict each other — a
    21-unit ladder (nothing filled) resting alongside a 7-unit stop (seven units
    held) is accepted without complaint, and that combination is the most likely
    way a caller loses money on correct-looking engine code. The check exists,
    but one layer up in `engine.engine.compute`, for two reasons. First, the
    contradiction is not a fact about *this* state object the way the inverted
    leg and the sub-`EL*` exit anchor are — those are checkable from a single
    order-set computation and are why an order set would be arithmetically
    wrong. It is a fact about the caller's *ledger reconstruction*: whether its
    trade history and its order book agree. `compute()` owns that contract
    because `compute()` is what M2 calls. Second, this function's own tests
    deliberately vary one axis at a time ("does the stop rest when we hold
    units?" does not involve `filled_purposes` at all), and a cross-axis guard
    here would make that impossible to ask.

    **A caller that reaches this function without going through `compute()` is
    responsible for that check itself** — `BUY_PURPOSES` / `SELL_PURPOSES` above
    are exported for exactly that.

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

    # The breakout fallback deploys the ENTIRE remaining pool (SPEC §5), so once
    # it has filled the buy side of this episode is finished — no rung and no
    # second breakout. Re-resting either would spend capital already deployed,
    # and the breakout is the worse of the two: after it fills, spot is above
    # bos_week_high, so a buy-stop re-placed there triggers ON PLACEMENT, every
    # run, until the quote balance is exhausted. Nothing else gates it —
    # a filled breakout *raises* held_units — and it is the branch all four
    # historical episodes took (§14 OQ-3). Suppression must be keyed on
    # BREAKOUT's own fill, never on callers marking the rungs filled: they were
    # not filled, and the journal must not say they were.
    if OrderPurpose.BREAKOUT not in filled_purposes:
        # OQ-3 leg 1 — accumulation that never filled joins the ladder pool.
        acc_unfilled = _total(units for purpose, units in ACC_UNITS.items()
                              if purpose not in filled_purposes)
        with localcontext(CTX):
            ladder_pool = total_units - ACC_TOTAL
        pool = roll_unfilled(acc_unfilled, ladder_pool)
        levels = ladder_levels(state.el_star, state.bos_week_high)

        unfilled_ladder = Decimal(0)
        for name, price in levels.items():
            purpose = LADDER_PURPOSE[name]
            if purpose in filled_purposes:
                continue
            units = pool[name]
            # Summing rolled rung sizes is inexact: on a 15-unit pool each is a
            # 34-digit expansion, and at an ambient prec of 1 the total rounds to
            # 3E+1 — 30 units ordered against a 15-unit pool.
            with localcontext(CTX):
                unfilled_ladder += units
            out.append(DesiredOrder(purpose=purpose, side=OrderSide.BUY,
                                    kind=OrderKind.LIMIT, price=price, units=units))

        # OQ-3 leg 2 — ladder rungs still unfilled join the breakout fallback.
        # Buy-STOP at the BoS-week high, not a limit: §13.2 and §5 both, and
        # G1/G3 fill it *at* 309.90 / 25,250, which only max(level, open) gives.
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
            # `/2` terminates in base 10, but termination gives exactness only
            # while the halved coefficient still fits in `prec`, and held_units
            # is plausibly a 34-digit rolled rung size. At an ambient prec of 2
            # the halving returns 1.1 against a true 1.0714... — a 2.7% over-sell.
            with localcontext(CTX):
                exit1_units = held_units / Decimal(2)
            out.append(DesiredOrder(purpose=OrderPurpose.EXIT1, side=OrderSide.SELL,
                                    kind=OrderKind.LIMIT,
                                    price=extension_1272(state.el_star, state.prior_ath),
                                    units=exit1_units))
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
            if lines["mirror"] <= 0:
                # §13.2: a sell-limit below market fills at max(level, open), so
                # a collapsed target dumps the whole remainder at market. The
                # realistic fault is a corrupt top_high feeding mirror_target,
                # which produces a plausible-looking number, not an absurd one.
                raise ValueError(
                    f"mirror target must be positive, got {lines['mirror']}")
            out.append(DesiredOrder(purpose=OrderPurpose.MIRROR, side=OrderSide.SELL,
                                    kind=OrderKind.LIMIT, price=lines["mirror"],
                                    units=held_units))
    return tuple(out)
