"""Episode lifecycle: trigger detection, 26-quiet-week clustering, downtrend
scope, the running low, and the EL* freeze at BoS (SPEC §1 and §13.1)."""
from __future__ import annotations
from decimal import Decimal
from engine.bars import monday_of
from engine.types import Bar, Week

RSI_TRIGGER = Decimal("35")
QUIET_WEEKS = 26


def find_triggers(weeks: list[Week], rsi: list[Decimal | None]) -> list[str]:
    """Return the Monday of each episode-starting armed week.

    A week is 'armed' when weekly RSI-14 < 35 and 'quiet' otherwise. Armed weeks
    cluster into one episode while fewer than 26 consecutive quiet weeks separate
    them; 26+ quiet weeks after the last armed week closes the window.

    `weeks` and `rsi` are parallel lists — the caller builds `rsi` as
    ``wilder_rsi([w.close for w in weeks])``, so entry *i* of one describes
    entry *i* of the other. That join is load-bearing (a one-slot offset arms
    the episode on the wrong week) and `zip` truncates a mismatch in silence,
    so the lengths are checked rather than trusted.

    **The returned Monday is a week LABEL, not an actionable date.** It names
    the armed week; that week's RSI is not knowable until its Sunday close, so
    treating the Monday as "the trigger day" is a one-week lookahead. SPEC §11
    records accumulation fills starting the Monday *after* the trigger week —
    EP3 wk 2018-11-19 fills 2018-11-26, EP4 wk 2020-03-09 fills 2020-03-16 —
    and §13.6 dates line lifetime from that first actionable day. Callers that
    need a date must advance to the following Monday; callers comparing weeks
    (§13.3's `monday(D) < trigger_week` guard) use the label as-is.
    """
    if len(weeks) != len(rsi):
        raise ValueError(
            f"weeks and rsi must be parallel lists; got {len(weeks)} and {len(rsi)}"
        )
    triggers: list[str] = []
    quiet_run = 0
    open_episode = False
    for week, value in zip(weeks, rsi):
        armed = value is not None and value < RSI_TRIGGER
        if armed:
            if not open_episode:
                triggers.append(week.monday)
                open_episode = True
            quiet_run = 0
        else:
            quiet_run += 1
            if open_episode and quiet_run >= QUIET_WEEKS:
                open_episode = False
    return triggers


def prior_cycle_ath(weeks: list[Week], trigger_monday: str) -> tuple[Decimal, str]:
    """Highest weekly high strictly preceding the trigger week, full history.
    Returns (price, that week's Monday).

    EXIT ANCHOR ONLY — feeds §6.1's 1.272 extension. It does NOT define the
    downtrend scope, the freshness window, or the episode low; those come from
    downtrend_anchor (D). The two differ in EP4: exit anchor 19,798.68,
    D = 13,970 (SPEC §13.3 v1.2.1)."""
    prior = [w for w in weeks if w.monday < trigger_monday]
    if not prior:
        raise ValueError("no weeks precede the trigger")
    best = max(prior, key=lambda w: w.high)
    return best.high, best.monday


def running_low(bars: list[Bar], scope_start: str, upto: str) -> Decimal:
    """Lowest daily low from scope_start through `upto` inclusive."""
    lows = [b.low for b in bars if scope_start <= b.date <= upto]
    if not lows:
        raise ValueError("no bars in scope")
    return min(lows)


def downtrend_anchor(weeks: list[Week], window_start: str,
                     asof: str) -> tuple[Decimal, str]:
    """D — the argmax-high week of [window_start, asof], walk-forward.

    window_start = the PREVIOUS episode's activation (BoS date; data start if
    none). D anchors the LH scan scope, the freshness window, the trigger
    guard and the episode low (SPEC §13.3 v1.2.1). NOT the exit anchor —
    that is prior_cycle_ath(), and they differ in EP4.

    **Both bounds accept any day and both ends are week-INCLUSIVE.** SPEC §13.3
    names them in mixed units — window_start is a BoS *date*, asof is the
    *trigger week* — while `weeks` are keyed by Monday. A mid-week
    `window_start` compared against Mondays raw would silently drop the BoS's
    own week, so it is normalised here rather than left as every caller's
    problem; `monday_of` is idempotent, so Monday arguments are unaffected.
    `asof` needs no such normalisation and deliberately gets none: no week's
    Monday falls strictly between `monday_of(asof)` and `asof`, so `<= asof`
    already admits the asof week and nothing later.

    Inclusivity is load-bearing on real data: EP1's D *is* its own trigger week
    (15.00 @ 2011-11-21), which an exclusive `asof` would push back to
    11.85 @ 2011-08-15 — flipping §13.3's `monday(D) < trigger_week` guard from
    failing to passing, so EP1 would stop expiring as §11 requires.
    """
    window_start = monday_of(window_start)
    window = [w for w in weeks if window_start <= w.monday <= asof]
    if not window:
        raise ValueError("empty anchor window")
    best = max(window, key=lambda w: w.high)
    return best.high, best.monday


def freeze_el(bars: list[Bar], scope_start: str, bos_date: str) -> Decimal:
    """EL* — the running low frozen at the BoS day (SPEC §13.1). From the BoS
    onward this is the stop level; before the BoS it is only an anchor.
    scope_start is D's Monday (downtrend_anchor), not the prior-ATH week."""
    return running_low(bars, scope_start, bos_date)
