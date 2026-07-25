"""Session fixtures shared by the unit suite and the gate suite.

These used to live in `tests/gates/conftest.py`, which made them invisible to
`tests/test_engine.py` and would have meant a second copy — and a second load —
of the frozen reference snapshots. They are session-scoped precisely so the
2011->2026 series is parsed once per run, so duplicating them is not merely
untidy: it doubles the parse and lets the two copies drift.

`episode_scope` moved with them. It is now a thin adapter over
`engine.lifecycle.chain_episodes` rather than an implementation: the chaining
rule (SPEC §13.3 — each episode's scope window starts at the *previous*
episode's activation) is engine code that ships to Vercel, not test-local
orchestration. Until Task 14 that distinction was doing real damage: the gates
certified a chain that no shipped module contained.
"""
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
    """Derive (trigger, D, BoS, broken LH) per episode FROM THE ENGINE.

    Each episode's scope window starts at the PREVIOUS episode's activation
    (its BoS), so episodes must be processed in trigger order: EP2's BoS feeds
    EP3's window, and so on. This chain is also what makes EP4 come out right
    (D = June-2019 13,970, not the Dec-2017 ATH). D is bounded at the episode's
    OWN trigger — bounding at the era end leaks the next bull run into D
    (EP2 -> Dec-2017, EP4 -> Nov-2021; both wrong).

    All of that now lives in `engine.lifecycle.chain_episodes`, which
    `engine.engine.compute` also calls. One rule, two callers: a mutation of the
    chain has to fail both the gates and `compute`, and can no longer pass the
    gates while shipping something else.

    Never hard-code dates: the reference JSONs label weeks by Sunday close and
    this codebase labels by ISO Monday, so pasted dates are off by six days.
    """
    from engine.lifecycle import chain_episodes, find_triggers

    triggers = find_triggers(weeks, weekly_rsi)
    episodes = chain_episodes(weeks, bars, triggers, data_end=bars[-1].date)
    scopes = {
        ep.trigger: (ep.d_week, ep.bos_date,
                     ep.broken_lh.price if ep.broken_lh else None)
        for ep in episodes
    }
    return {"triggers": triggers, "scopes": scopes, "episodes": episodes}
