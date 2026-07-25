"""The gate suite's fixtures now live in `tests/conftest.py` (project root) so
the unit suite and the gate suite share one session-scoped copy of the frozen
reference series. This file is kept as the marker of that move; adding a
gate-only fixture here is still correct, but `bars` / `weeks` / `weekly_rsi` /
`onchain` / `cy1` / `episode_scope` must not be redefined — a second definition
would shadow the shared one and reload the reference data.
"""
