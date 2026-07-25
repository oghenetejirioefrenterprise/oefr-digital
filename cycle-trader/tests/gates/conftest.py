import pytest
from data.loaders import load_bars, load_onchain, load_cy1_reference
from engine.bars import to_weeks
from engine.rsi import wilder_rsi


@pytest.fixture(scope="session")
def bars():
    return load_bars()


@pytest.fixture(scope="session")
def weeks(bars):
    return to_weeks(bars)


@pytest.fixture(scope="session")
def weekly_rsi(weeks):
    return wilder_rsi([w.close for w in weeks])


@pytest.fixture(scope="session")
def onchain():
    return load_onchain()


@pytest.fixture(scope="session")
def cy1():
    return load_cy1_reference()


@pytest.fixture(scope="session")
def episode_scope(bars, weeks, weekly_rsi):
    """Derive (trigger, D) per episode FROM THE ENGINE, chaining activations.

    Each episode's scope window starts at the PREVIOUS episode's activation
    (its BoS), so episodes must be processed in trigger order: EP2's BoS feeds
    EP3's window, and so on. This chain is also what makes EP4 come out right
    (D = June-2019 13,970, not the Dec-2017 ATH).

    Never hard-code dates: the reference JSONs label weeks by Sunday close and
    this codebase labels by ISO Monday, so pasted dates are off by six days.
    """
    from engine.lifecycle import downtrend_anchor, find_triggers
    from engine.structure import find_lh_candidates, first_bos

    triggers = find_triggers(weeks, weekly_rsi)
    # trigger -> (D_monday, bos_date|None, broken_LH_price|None)
    scopes: dict[str, tuple[str, str | None, object]] = {}
    window_start = weeks[0].monday            # data start; EP1 has no predecessor
    data_end = bars[-1].date

    for trigger, nxt in zip(triggers, triggers[1:] + [None]):
        era_end = nxt or data_end             # BoS must print before the next trigger
        # D is bounded at the episode's OWN trigger — bounding at era_end leaks
        # the next bull run into D (EP2 -> Dec-2017, EP4 -> Nov-2021; both wrong).
        _d_price, d_week = downtrend_anchor(weeks, window_start, asof=trigger)
        cands = find_lh_candidates(weeks, bars, scope_start=d_week,
                                   trigger_monday=trigger)
        # Walk-forward BoS against the THEN-operative LH. Asking for the
        # operative LH at era_end instead returns None — the BoS killed it —
        # and the whole chain silently records every episode as expired.
        #
        # `broken` — WHICH candidate was broken — is carried through, not
        # discarded. A BoS date alone does not say the engine broke the right
        # structure: `return b.date, candidates[0]` produces every correct date
        # off the wrong LH, and that LH is what the §5 leg and the §6.1
        # extension hang off. The gates already know the answer, so they assert
        # it.
        bos, broken = first_bos(bars, cands, start=trigger, end=era_end)
        scopes[trigger] = (d_week, bos, broken.price if broken else None)
        if bos is not None:
            window_start = bos                # next episode's window starts here

    return {"triggers": triggers, "scopes": scopes}
