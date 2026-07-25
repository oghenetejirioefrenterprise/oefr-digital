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


def _modules(root: Path = ENGINE) -> list[Path]:
    """Every module under `root`, **recursively**.

    `glob` (non-recursive) was the first version and it was blind by one
    character: a file at `engine/sub/adapter.py` importing pandas and calling
    `os.listdir` produced zero violations and the gate stayed green. `engine/`
    is flat today, but this gate exists to survive M2/M3 — when it will not be —
    and `test_engine_modules_exist_to_be_checked` asserts a *superset* of known
    names, so it could never have noticed either.
    """
    return sorted(root.rglob("*.py"))


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


def test_the_scan_recurses_into_subpackages(tmp_path):
    """Pins `rglob`, the one character this gate was blind by.

    Built in a tmp tree rather than by writing into `engine/`, so a crashed run
    cannot leave an impure file behind in the package under test. Both halves
    matter: the nested module must be *found*, and its violation *reported*.
    """
    (tmp_path / "flat.py").write_text("from decimal import Decimal\n")
    nested = tmp_path / "sub" / "deeper"
    nested.mkdir(parents=True)
    (nested / "adapter.py").write_text("import pandas\n\n\ndef go():\n    return 1\n")

    found = _modules(tmp_path)
    assert sorted(p.name for p in found) == ["adapter.py", "flat.py"], \
        "a non-recursive glob sees only flat.py and the gate goes green"
    violations = [v for p in found for v in _violations(p.read_text(), p.name)]
    assert len(violations) == 1 and "pandas" in violations[0]


def test_the_checker_actually_catches_impurity():
    """The teeth. The four hazards must NOT trip; sixteen violations must.

    Without this, a checker that silently inspected nothing — a bad glob, an
    ALLOWED_IMPORTS that grew to cover everything — would still show green, and
    the purity gate would be decoration.

    Each case asserts the *count* and the *text* of what came back, not merely
    that something did: a checker that reported one generic violation for every
    input would otherwise pass. The awkward cases are deliberate — an import
    hidden inside a function body or a `try/except ImportError`, a star-import,
    `time.time()` (which is both a forbidden import and a clock read, hence two
    violations), and `date.today()` off an import that is itself legal.
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

    cases = [
        # third-party and forbidden-stdlib imports
        ("import pandas as pd", "pandas", 1),
        ("import numpy", "numpy", 1),
        ("import polars", "polars", 1),          # never named anywhere: deny-by-default
        ("from data.loaders import load_bars", "data.loaders", 1),
        ("import json", "json", 1),
        ("from pathlib import Path", "pathlib", 1),
        ("import random", "random", 1),
        ("from os import *", "os", 1),
        ("from . import types", "relative", 1),
        # imports that a line-oriented check would not be looking at
        ("def f():\n    import numpy\n    return numpy", "numpy", 1),
        ("try:\n    import numpy\nexcept ImportError:\n    numpy = None",
         "numpy", 1),
        # I/O and code execution
        ("def f():\n    return open('x').read()", "open", 1),
        ("def f(s):\n    return compile(s, '<s>', 'exec')", "compile", 1),
        ("def f(x):\n    print(x)", "print", 1),
        # clock reads, including off imports that are themselves legal
        ("import datetime\ndef f():\n    return datetime.datetime.now()", "now", 1),
        ("from datetime import date\ndef f():\n    return date.today()", "today", 1),
        ("import datetime\ndef f():\n    return datetime.datetime.utcnow()",
         "utcnow", 1),
        # `time` is both a forbidden import and a clock call: two distinct hits
        ("import time\ndef f():\n    return time.time()", "time", 2),
        ("import time\ndef f():\n    return time.monotonic()", "monotonic", 2),
    ]
    for bad, marker, expected in cases:
        found = _violations(bad, "bad.py")
        assert found, f"{marker!r} slipped through the purity checker"
        assert len(found) == expected, f"{marker!r}: {found}"
        assert any(marker in v for v in found), f"{marker!r} not named in {found}"
