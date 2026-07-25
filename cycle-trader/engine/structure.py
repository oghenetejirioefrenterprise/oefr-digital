"""Fresh-low lower highs, BoS, and swing lows — SPEC §4, §6.2, §13.3.

Terminology (SPEC §13.3 collapses the doc's three names into one):
  anchor(i) = the most recent week j < i whose high exceeds week i's high.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date as _date, timedelta
from decimal import Decimal, localcontext
from engine.context import CTX
from engine.types import Bar, Week

R_E_DEFAULT = Decimal("15")
R_DOWN_DEFAULT = Decimal("10")


@dataclass(frozen=True, slots=True)
class LHCandidate:
    week_monday: str
    price: Decimal
    origin_low: Decimal
    origin_week: str
    anchor_week: str
    rally_pct: Decimal
    confirmed_at: str | None
    invalidated_at: str | None


def _week_end(monday: str) -> str:
    y, m, d = (int(x) for x in monday.split("-"))
    return (_date(y, m, d) + timedelta(days=6)).isoformat()


def find_lh_candidates(weeks: list[Week], bars: list[Bar], scope_start: str,
                       trigger_monday: str,
                       r_e: Decimal = R_E_DEFAULT) -> list[LHCandidate]:
    # scope_start is monday(D). The trigger-anchor guard (SPEC §13.3) tests D,
    # not anchor(i): if D does not predate the trigger there is no valid
    # downtrend structure at all (this is what expires EP1's 2013 trap).
    if scope_start >= trigger_monday:
        return []
    in_scope = [w for w in weeks if w.monday >= scope_start]
    out: list[LHCandidate] = []

    for i, cand in enumerate(in_scope):
        j = None
        for k in range(i - 1, -1, -1):
            if in_scope[k].high > cand.high:
                j = k
                break
        if j is None:
            continue

        # Window INCLUDES the anchor week j and excludes the candidate's own
        # week i. Using j+1 here fails G1, G3 and G5: the fresh low routinely
        # prints in the very week that made the higher high. G1's proof — week
        # 2014-12-29 has high 321.00 (the anchor) AND low 255.00 (the origin);
        # with j+1 the window is empty and LH 305.00 is never generated.
        between = in_scope[j:i]
        if not between:
            continue
        origin_week = min(between, key=lambda w: w.low)
        l0 = origin_week.low
        if l0 <= 0:
            continue

        before_origin = [w.low for w in in_scope if w.monday < origin_week.monday]
        if before_origin and l0 >= min(before_origin):
            continue  # not a fresh low

        # The one inexact computation in this module, and it feeds a strict
        # threshold (`< r_e`), so it runs in the engine's pinned context —
        # see engine/context.py. The pin is scoped to the expression rather
        # than the function precisely to mark which line is inexact; every
        # other operation here is a comparison or a min/max over raw OHLC.
        # Measured on the frozen series: the candidate set is stable down to
        # prec 3 and flips only at prec 1 (EP6: 8 candidates instead of 12),
        # but the tightest real margin is 0.4988 pts (wk 2025-11-24 rallies
        # +15.4988% against the R_e=15 cutoff), which the error clears only
        # from prec >= 4.
        with localcontext(CTX):
            rally = (cand.high - l0) / l0 * Decimal(100)
        if rally < r_e:
            continue

        # NOTE: no guard on anchor(i) here. The trigger guard tests D — done
        # once, before this loop. anchor(i) may legitimately postdate the
        # trigger: G3's LH 25,211.32 has anchor(i) = wk 2022-06-13 (26,895.84),
        # AFTER the 2022-05-16 trigger. Guarding on anchor(i) fails G3.

        cand_end = _week_end(cand.monday)
        confirmed_at = next((b.date for b in bars if b.date > cand_end and b.low < l0), None)
        # Invalidation is DAY-resolution: the first daily high above the
        # candidate. Week-resolution (a Monday label) kills the candidate at
        # the start of its own break week, and the BoS scan never sees it.
        invalidated_at = next((b.date for b in bars
                               if b.date > cand_end and b.high > cand.high), None)

        out.append(LHCandidate(
            week_monday=cand.monday, price=cand.high, origin_low=l0,
            origin_week=origin_week.monday, anchor_week=in_scope[j].monday,
            rally_pct=rally, confirmed_at=confirmed_at,
            invalidated_at=invalidated_at,
        ))
    return out


def operative_lh(candidates: list[LHCandidate], asof: str) -> LHCandidate | None:
    """Most recent candidate confirmed on or before `asof` and not yet dead.

    A candidate stays operative THROUGH its invalidation day (`>=`): the break
    that invalidates it (§4.5) is the BoS of that structure, printed intraday —
    with `>` the walk-forward scan below could never see its own break.
    """
    live = [c for c in candidates
            if c.confirmed_at is not None and c.confirmed_at <= asof
            and (c.invalidated_at is None or c.invalidated_at >= asof)]
    return max(live, key=lambda c: c.week_monday) if live else None


def find_bos(bars: list[Bar], lh_price: Decimal, after: str) -> str | None:
    """First daily high strictly above a FIXED price, after `after`. Test/gate
    helper for a known LH; historical reconstruction uses first_bos()."""
    return next((b.date for b in bars if b.date > after and b.high > lh_price), None)


def first_bos(bars: list[Bar], candidates: list[LHCandidate], start: str,
              end: str) -> tuple[str, LHCandidate] | tuple[None, None]:
    """Walk-forward BoS: the first day in [start, end] whose high exceeds the
    THEN-operative LH (strictly after that candidate's confirmation).

    This is the only correct way to find a historical BoS. Asking "what is the
    operative LH today?" after a BoS returns nothing — the BoS killed it — so
    reconstruction must walk days against the structure as it stood each day.
    """
    for b in bars:
        if b.date < start or b.date > end:
            continue
        op = operative_lh(candidates, asof=b.date)
        if op is not None and b.date > op.confirmed_at and b.high > op.price:
            return b.date, op
    return None, None
