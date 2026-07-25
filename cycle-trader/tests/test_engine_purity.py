"""`engine/` is pure: stdlib-only, no I/O, no clock — enforced by AST, not grep.

CLAUDE.md's constraint has three parts (no pandas/numpy, so the serverless
bundle stays small; no I/O, so the engine is a total function of its arguments;
no clock, so a gate replay in 2030 gives the same answer as one today). It was
originally to be checked with two `grep -rnE` passes. Grep cannot express it
soundly — four real constructs in this package break it in both directions:

  `engine/types.py`   `Bar.from_json` — a pure dict-mapper. A grep for `json`
                      flags it; it imports nothing and reads nothing.
  `engine/fills.py`   `bar.open` — an OHLC attribute. A grep for `open\\(` is
                      clean today only because the code never writes
                      `bar.open(`; `max(bar.open, level)` would trip a looser
                      one, and tightening to `\\bopen\\(` would then miss
                      `io.open(`.
  `engine/*.py`       `from datetime import date, timedelta` — legitimate
                      calendar arithmetic. Only *clock reads* are forbidden,
                      and `datetime.date.today()` contains no token the
                      import-line grep looks at.
  `engine/context.py` `from decimal import localcontext` — the pinned-context
                      convention, which a `context`-ish token grep would flag.

A check that a maintainer has to hand-verify around four known exceptions is a
check nobody trusts, so it gets skipped or weakened, and a purity gate that
passes trivially is worse than none. The AST version is both sounder and
shorter: it denies by default.

**Deny by default.** `ALLOWED_IMPORTS` is the complete list of modules `engine/`
may import — five stdlib modules plus its own package. Adding pandas, numpy,
requests, `os`, `json`, `pathlib`, `random` or `data.loaders` (which
`data/loaders.py` forbids in its own docstring) fails without anyone having
predicted that particular import. An allowlist edit is a deliberate act with a
diff; a grep pattern that never learned about `polars` is silent.

`test_the_checker_actually_catches_impurity` is the load-bearing test here: it
feeds the checker the violations AND the four false-positive hazards above, so
this file cannot rot into a gate that passes because it inspects nothing.
"""
from __future__ import annotations

import ast
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "engine"

#: Everything `engine/` may import. Deny-by-default: extending this list is a
#: deliberate change to the purity contract and shows up in review as one.
ALLOWED_IMPORTS = frozenset({"__future__", "dataclasses", "datetime", "decimal",
                             "enum", "engine"})
#: Names whose CALL reads the wall clock. `datetime`/`timedelta` are allowed
#: imports (calendar arithmetic), so the clock has to be caught at the call.
CLOCK_CALLS = frozenset({"now", "utcnow", "today", "fromtimestamp", "monotonic",
                         "perf_counter", "time", "time_ns"})
#: Builtins that touch the outside world or execute untrusted text.
IMPURE_BUILTIN_CALLS = frozenset({"open", "input", "print", "eval", "exec",
                                  "compile", "__import__", "breakpoint"})


def _modules() -> list[Path]:
    return sorted(ENGINE.glob("*.py"))


def _violations(source: str, filename: str) -> list[str]:
    """Every purity violation in `source`, as human-readable strings.

    Attribute *access* is never a violation — only a Call is. That is what
    keeps `bar.open` legal while `open(path)` and `datetime.now()` are not.
    """
    out: list[str] = []
    for node in ast.walk(ast.parse(source, filename)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    out.append(f"{filename}:{node.lineno} imports {alias.name!r}")
        elif isinstance(node, ast.ImportFrom):
            if node.level:                      # relative import
                out.append(f"{filename}:{node.lineno} relative import")
                continue
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                out.append(f"{filename}:{node.lineno} imports from {node.module!r}")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            else:
                continue
            if name in CLOCK_CALLS:
                out.append(f"{filename}:{node.lineno} reads the clock: {name}()")
            elif isinstance(func, ast.Name) and name in IMPURE_BUILTIN_CALLS:
                out.append(f"{filename}:{node.lineno} impure builtin: {name}()")
    return out


def test_engine_modules_exist_to_be_checked():
    """A checker pointed at an empty directory passes vacuously."""
    names = {p.name for p in _modules()}
    assert names >= {"types.py", "bars.py", "rsi.py", "lines.py", "fills.py",
                     "lifecycle.py", "structure.py", "levels.py", "orders.py",
                     "context.py"}


def test_engine_is_pure():
    """The gate itself: zero violations across every engine module."""
    found = [v for p in _modules() for v in _violations(p.read_text(), p.name)]
    assert found == [], "engine/ is not pure:\n  " + "\n  ".join(found)


def test_engine_imports_nothing_outside_the_allowlist():
    """Stated as the positive fact, so the failure message names the import."""
    imported: set[str] = set()
    for path in _modules():
        for node in ast.walk(ast.parse(path.read_text(), path.name)):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
    assert imported <= ALLOWED_IMPORTS, sorted(imported - ALLOWED_IMPORTS)
    # The two named in CLAUDE.md, and the test-only loader that `data/loaders.py`
    # forbids the engine from importing. Spelled out because they are the ones a
    # future contributor is most likely to reach for.
    assert not (imported & {"pandas", "numpy", "requests", "httpx", "data"})


def test_datetime_is_imported_only_for_calendar_arithmetic():
    """`datetime` is on the allowlist, so its clock has to be excluded by name.

    The engine takes ISO date strings and does week arithmetic on them; nothing
    in it may ask what day it is. `date` and `timedelta` are the calendar half.
    """
    names: set[str] = set()
    for path in _modules():
        for node in ast.walk(ast.parse(path.read_text(), path.name)):
            if isinstance(node, ast.ImportFrom) and node.module == "datetime":
                names |= {a.name for a in node.names}
            if isinstance(node, ast.Import):
                assert all(a.name != "datetime" for a in node.names), (
                    f"{path.name}: plain `import datetime` exposes datetime.now; "
                    "import the calendar names explicitly")
    assert names <= {"date", "timedelta"}, sorted(names)


def test_the_checker_actually_catches_impurity():
    """The teeth. Four hazards must NOT trip; four violations must.

    Without this, a checker that silently inspected nothing — a bad glob, an
    ALLOWED_IMPORTS that grew to cover everything — would still show green, and
    the purity gate would be decoration.
    """
    clean = '''
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext
from engine.context import CTX

@dataclass
class Bar:
    open: Decimal
    @staticmethod
    def from_json(row: dict) -> "Bar":
        return Bar(open=Decimal(str(row["o"])))

def fill(bar, level):
    with localcontext(CTX):
        return max(bar.open, level) + timedelta(days=1) + date.fromisoformat("2026-01-01")
'''
    assert _violations(clean, "clean.py") == []

    for bad, marker in [("import pandas as pd", "pandas"),
                        ("import numpy", "numpy"),
                        ("from data.loaders import load_bars", "data.loaders"),
                        ("import json", "json"),
                        ("from pathlib import Path", "pathlib"),
                        ("import random", "random"),
                        ("def f():\n    return open('x').read()", "open"),
                        ("import datetime\ndef f():\n    return datetime.datetime.now()",
                         "now"),
                        ("from datetime import date\ndef f():\n    return date.today()",
                         "today"),
                        ("import time\ndef f():\n    return time.time()", "time"),
                        ("def f(x):\n    print(x)", "print")]:
        found = _violations(bad, "bad.py")
        assert found, f"{marker!r} slipped through the purity checker"
