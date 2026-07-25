"""The single public entry point. Pure: no I/O, no clock, no network.

`compute()` answers one question: given everything known up to `asof`, what
state is the episode in and what orders should be resting at the exchange?
Everything else in `engine/` is an implementation detail of that answer.

THE DAILY-RUN MODEL — one convention, four boundaries
-----------------------------------------------------
The cron runs **after the UTC daily close** (CLAUDE.md), so `compute(asof=D)`
sees D's completed bar and the tuple it returns is what rests **during D+1**.
Every date boundary below falls out of that single convention, and each one is a
place where the module signatures cannot help — they take no dates:

1. **A trigger week must be settled before it arms anything.** Weekly RSI-14 is
   not knowable until the week's Sunday close, so `compute` builds its weekly
   series from *settled* weeks only (`week_end(monday) <= asof`). Measured on
   the frozen series, reading partial weeks is not a theoretical lookahead: it
   arms a **phantom EP7** on 2025-11-21/22 off two days of the unsettled
   2025-11-17 week (RSI recovers by that Sunday and no such episode exists in
   the record), and it arms EP5 a week early on the 2022-05-09 LUNA week and
   then silently *moves* the trigger to 2022-05-16. Both would have rested three
   accumulation buy-limits on structure that does not exist.
2. **Accumulation may not rest inside the trigger week.** This needs no separate
   guard once (1) holds: the earliest `asof` that detects a trigger is its
   Sunday, so the earliest day a tranche can rest is the following Monday —
   exactly §11's recorded first fills (EP3 2018-11-26, EP4 2020-03-16).
3. **The BoS week must be settled before the ladder and the breakout exist.**
   §5 prices the ladder off the BoS-*week* high and fires the breakout "after
   the BoS week", and `desired_orders` rests the breakout the moment the status
   is CONFIRMED. Under §14 OQ-3 that breakout carries 21 units, not 14, so one
   premature run buys the entire book at the running top of the very week that
   broke structure. `compute` therefore suppresses the rungs and the breakout
   until `asof >= week_end(BoS week)`. G1 is the check: the ladder first rests
   2015-02-02, which is where §13.3 records the 0.5 rung gap-filling.
   The **stop is not suppressed** — EL* froze at the BoS and is priceable
   immediately; withholding it would leave a live position naked for a week.
4. **A mirror signal must post-date arming** (§6.2), and the fallback deadline
   is measured in calendar days from the signal, not in bars.

WHAT THIS FUNCTION IS NOT
-------------------------
- **It does not catch `ValueError`.** `engine/orders.py` raises rather than
  emitting a smaller order set, because the daily run is a desired-state
  *reconciler*: a short tuple is an instruction to cancel, and the order most
  likely to be dropped by a missing input is the stop. Those guards are only
  protective if the exception propagates out of here. A failed run changes
  nothing and never cancels.
- **It is stateless.** The whole episode is reconstructed from `bars` every run,
  which is what makes the daily job idempotent and self-healing after a crashed
  or skipped run. `prior_state` is consulted only when there is nothing to
  compute (no bars at or before `asof`); it is returned untouched rather than
  overwritten with a fabricated IDLE.
- **It does not track fills.** `filled_purposes` and `held_units` are inputs, fed
  in M2 from venue trade history. Their defaults (nothing filled, nothing held)
  make every sell-side order inert by construction — the right posture for an
  engine that cannot yet know what it holds.

KNOWN LIMITS, STATED RATHER THAN IMPLIED
----------------------------------------
- **`CLOSED` and `EXPIRED` are unreachable.** CLOSED needs fill tracking (M2).
  EXPIRED is never a *current* state: §1 bounds expiry by the next episode's
  trigger, and the moment that trigger prints, the next episode is the one
  reported. EP1 therefore reads WATCHING throughout its own life.
- **Only the latest episode is reported** — §14 OQ-1's concurrent-episode case.
  EP3 is still fully positioned when EP4 triggers in March 2020, and from that
  day EP3 is invisible here. Their exits coincide (2021-04-28 @ 55,892) so the
  record is not lost, but an engine that must manage two live books is an M2/§9
  question, not a wiring detail.
- **The mirror detector uses `find_swing_lows`' shipped confirmation reading,
  which does not reproduce EP5's Exit 2** — SPEC §14 OQ-7(b). It exits
  2025-01-15 @ 98,804.845 against the reference's 2025-03-02 @ 93,923.26; the
  alternative reading reproduces all four. That is an owner decision under §9,
  not something to work around in the wiring, so what is wired here is what
  exists. EP2 and EP4 reproduce exactly.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date as _date
from decimal import Decimal

from engine.bars import monday_of, to_weeks, week_end
from engine.levels import extension_1272, mirror_target
from engine.lifecycle import (chain_episodes, find_triggers, freeze_el,
                              prior_cycle_ath, running_low)
from engine.lines import lines_for
from engine.orders import desired_orders
from engine.rsi import wilder_rsi
from engine.structure import find_swing_lows, operative_lh
from engine.types import (Bar, DesiredOrder, EngineResult, EpisodeState,
                          EpisodeStatus, OnChain, OrderPurpose)

#: SPEC §6.2 — "no 50% bounce within 8 weeks of the signal -> sell at market".
MIRROR_FALLBACK_DAYS = 56
#: Priced off the BoS-*week* high, so none of them can exist until that week has
#: closed (SPEC §5, and the caller contract in `orders.desired_orders`).
UNPRICEABLE_UNTIL_BOS_WEEK_CLOSES = frozenset({
    OrderPurpose.LADDER_050, OrderPurpose.LADDER_062, OrderPurpose.LADDER_0786,
    OrderPurpose.BREAKOUT})


def _days_between(start: str, end: str) -> int:
    """Calendar days, not bars. A data gap must not postpone §6.2's deadline."""
    return (_date.fromisoformat(end) - _date.fromisoformat(start)).days


def _settled_weeks(visible: list[Bar], asof: str):
    """Weekly bars whose week has actually closed on or before `asof`.

    The trailing partial week is dropped rather than carried with a running
    close — see boundary (1) in the module docstring for what carrying it does
    to the trigger set on real data.
    """
    return [w for w in to_weeks(visible) if week_end(w.monday) <= asof]


def _mirror_lines(visible: list[Bar], bos: str, armed_since: str,
                  asof: str) -> dict[str, Decimal]:
    """SPEC §6.2's mirror exit, from arming to the resting sell price.

    Scope is the position lifetime — [BoS, asof] — per §6.2 ("only structure
    formed during the episode's uptrend"). The signal is found by walking days
    forward and testing each day against the most recent swing confirmed
    **strictly before** that day, which is what "the most recent confirmed swing
    low" means at the moment of the break. Scanning swings outermost instead
    (newest swing first, then looking for any break) finds a *later* swing's
    break and reports it as the signal even when an earlier swing was broken
    first — and §13.9 is explicit that the position exits at the FIRST armed
    signal and later ones are inert.

    A pre-arming break is not a signal: EP5's Aug-2024 break of the May-2024
    swing predates Exit 1 (2024-11-11) and must produce nothing.

    The fill target is walk-forward, `(top_high + low_so_far) / 2`, and falls
    with the low. `top_high` is the lifetime argmax up to the signal, **not** the
    broken swing's own decline top — substituting the latter breaks all four
    reference episodes (§14 OQ-7(c), and the warning in `find_swing_lows`).

    One convention differs from §6.2 by necessity and is stated rather than
    hidden: §6.2 recomputes the target *intraday* ("low_so_far includes the
    current day's low before testing that day's high"). A resting exchange-side
    order cannot do that — the price that rests during day D+1 can only know
    lows through D. The resting target is therefore never lower than §6.2's, so
    the order fills on the same day or later, never earlier. It is the
    conservative direction, and it reproduces EP2 and EP4 to the cent.
    """
    era_bars = [b for b in visible if b.date >= bos]
    swings = find_swing_lows(to_weeks(era_bars), era_bars)

    signal = None
    for bar in era_bars:
        if bar.date <= armed_since:
            continue
        confirmed = [s for s in swings if s.confirmed_at < bar.date]
        if not confirmed:
            continue
        latest = max(confirmed, key=lambda s: s.week_monday)
        if bar.low < latest.low:
            signal = bar
            break
    if signal is None:
        return {}

    top = max(b.high for b in era_bars if b.date <= signal.date)
    after = [b.low for b in era_bars if b.date > signal.date]
    low_so_far = min([signal.low] + after)
    lines = {"mirror": mirror_target(top, low_so_far)}
    if _days_between(signal.date, asof) > MIRROR_FALLBACK_DAYS:
        lines["mirror_fallback"] = Decimal(1)
    return lines


def compute(bars: list[Bar], onchain: dict[str, OnChain],
            prior_state: EpisodeState, asof: str, *,
            filled_purposes: frozenset[OrderPurpose] = frozenset(),
            held_units: Decimal = Decimal(0)) -> EngineResult:
    """The episode state at `asof` and the orders that should be resting.

    `bars` and `onchain` may run past `asof`; everything after it is discarded,
    so a caller cannot accidentally introduce lookahead by passing the full
    history. `filled_purposes` is what has already executed and `held_units` is
    what the account holds now — both default to "nothing", which is M1's
    position and makes every sell-side order inert.

    Raises `ValueError` for any state that cannot be turned into a coherent
    order set. That is the intended behaviour, not a bug to be caught: see the
    module docstring.
    """
    visible = [b for b in bars if b.date <= asof]
    if not visible:
        return EngineResult(state=prior_state, orders=())

    weeks = _settled_weeks(visible, asof)
    triggers = find_triggers(weeks, wilder_rsi([w.close for w in weeks])) \
        if weeks else []
    if not triggers:
        return EngineResult(state=EpisodeState(status=EpisodeStatus.IDLE),
                            orders=())

    episode = chain_episodes(weeks, visible, triggers,
                             data_end=visible[-1].date)[-1]
    prior_ath, _ath_week = prior_cycle_ath(weeks, episode.trigger)  # exit anchor
    lines: dict[str, Decimal] = {}

    if episode.bos_date is None:
        lh = operative_lh(list(episode.candidates), asof=asof)
        state = EpisodeState(
            status=EpisodeStatus.WATCHING, trigger_date=episode.trigger,
            prior_ath=prior_ath, scope_start=episode.d_week,
            running_low=running_low(visible, episode.d_week, asof),
            operative_lh=lh.price if lh else None,
            lh_confirmed_at=lh.confirmed_at if lh else None,
        )
        row = onchain.get(asof)
        if row is not None:
            t1, t2, t3 = lines_for(row)
            lines = {"t1": t1, "t2": t2, "t3": t3}
        # A missing row leaves `lines` empty and `_watching` refuses — the
        # correct outcome on a dead feed, and the reason there is no `else`.
        return EngineResult(state=state,
                            orders=desired_orders(state, lines, filled_purposes,
                                                  held_units))

    bos = episode.bos_date
    el_star = freeze_el(visible, episode.d_week, bos)
    bos_monday = monday_of(bos)
    bos_week_closed = asof >= week_end(bos_monday)
    # Running while the BoS week is open (never the settled value — that would
    # be a lookahead), frozen from its Sunday onward.
    bos_week_high = max(b.high for b in visible
                        if bos_monday <= b.date <= min(asof, week_end(bos_monday)))
    state = EpisodeState(
        status=EpisodeStatus.CONFIRMED, trigger_date=episode.trigger,
        prior_ath=prior_ath, scope_start=episode.d_week,
        # §13.1: the episode low FREEZES at the BoS. Reporting a still-running
        # minimum here would contradict the stop it prices, and the two differ
        # exactly when it matters — after a post-BoS new low, i.e. a stop-out.
        running_low=el_star, el_star=el_star,
        operative_lh=episode.broken_lh.price,
        lh_confirmed_at=episode.broken_lh.confirmed_at,
        bos_date=bos, bos_week_high=bos_week_high,
    )

    # §6.1. This reconstructs the RECORD — it assumes the plan was followed —
    # and is deliberately independent of whether an Exit 1 order ever rested
    # (which needs `held_units`, i.e. M2). The BoS-day boundary is inert on all
    # four historical episodes; every Exit 1 is years later.
    extension = extension_1272(el_star, prior_ath)
    exit1_date = next((b.date for b in visible
                       if b.date >= bos and b.high >= extension), None)
    if exit1_date is not None:
        state = replace(state, status=EpisodeStatus.DISTRIBUTING, exit1_done=True)
        lines = _mirror_lines(visible, bos, exit1_date, asof)

    # §6.3 as narrowed by §13.1: a touch of the frozen EL*, STRICTLY after the
    # BoS day. Non-strict stops every episode the instant it activates, because
    # EL* is the running low *through* the BoS day and equals that day's low
    # whenever the break and the low print together.
    if any(b.date > bos and b.low <= el_star for b in visible):
        return EngineResult(state=replace(state, status=EpisodeStatus.STOPPED),
                            orders=())

    orders = desired_orders(state, lines, filled_purposes, held_units)
    if not bos_week_closed:
        orders = _drop_unpriceable(orders)
    return EngineResult(state=state, orders=orders)


def _drop_unpriceable(orders: tuple[DesiredOrder, ...]) -> tuple[DesiredOrder, ...]:
    """Boundary (3): the ladder and the breakout do not exist yet.

    Dropping orders from a desired set is normally the failure mode
    `engine/orders.py` exists to prevent, so this is deliberate and narrow: it
    removes only the four levels that are *arithmetically undefined* until the
    BoS week closes, and cancelling an order that should not exist is the
    correct instruction, not a degradation. The stop and Exit 1 pass through.
    """
    return tuple(o for o in orders
                 if o.purpose not in UNPRICEABLE_UNTIL_BOS_WEEK_CLOSES)
