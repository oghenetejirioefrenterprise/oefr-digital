"""Test-only data access for the frozen reference snapshots.

Nothing under ``engine/`` may import this package: the engine is a pure
function library with zero I/O, and loading data is the caller's job. In M1
the only caller is the test suite.
"""
