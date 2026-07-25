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

**An allowlisted module is not an allowlisted module.** Two of the five stdlib
modules carry, alongside the thing `engine/` needs, the exact thing the purity
rule forbids — and in both cases the import that reaches it is legal:

  `datetime`  `date` and `timedelta` are calendar arithmetic;
              `datetime.datetime` is the clock. `from datetime import datetime`
              passed the allowlist, and the clock was caught only at the call.
  `decimal`   `localcontext` is the pinned-context convention;
              `setcontext` / `getcontext().prec = N` are its negation — they
              replace or mutate the THREAD-GLOBAL context that
              `engine/context.py` exists to make irrelevant, for the whole
              serverless bundle, invisibly to CI's clean process.

So `ALLOWED_FROM_IMPORTS` narrows `datetime` to its calendar names and
`GLOBAL_STATE_CALLS` denies `decimal`'s two mutators. Both live inside
`_violations` rather than in a test of their own, because `_violations` is the
reusable checker: anything else that consumes it (the recursion test, a future
pre-commit hook, M2's own package) would otherwise inherit a hole that this
file's green did not show.

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
#: Calls that mutate PROCESS-GLOBAL state. `decimal` is allowlisted because the
#: pinned-context convention needs `localcontext`, and the allowlist alone
#: cannot tell that convention apart from its own negation: `setcontext(CTX)`
#: at module scope, or `getcontext().prec = N`, replaces or mutates the
#: thread's context for the whole bundle. That is exactly what
#: `engine/context.py` exists to defend against, it is a plausible tidy-up of
#: the nine `with localcontext(CTX):` blocks, and it changes nothing in CI —
#: which runs the gates in a clean process. Denied by name, both spellings.
#: See `test_the_pinned_context_may_not_be_installed_globally`.
GLOBAL_STATE_CALLS = frozenset({"setcontext", "getcontext"})
#: `datetime` is allowlisted for calendar arithmetic, so the half of it that
#: reads the clock has to be excluded by NAME at the import. `datetime.datetime`
#: is the class carrying `now`/`utcnow`/`fromtimestamp`; `date` and `timedelta`
#: carry no clock. A plain `import datetime` binds the whole module and is
#: refused for the same reason.
ALLOWED_FROM_IMPORTS = {"datetime": frozenset({"date", "timedelta"})}


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
                elif root in ALLOWED_FROM_IMPORTS:
                    # The module object exposes every name, including the ones
                    # the from-import allowlist below exists to withhold.
                    out.append(f"{filename}:{node.lineno} imports the whole "
                               f"{alias.name!r} module; import the allowed "
                               f"names explicitly")
        elif isinstance(node, ast.ImportFrom):
            if node.level:                      # relative import
                out.append(f"{filename}:{node.lineno} relative import")
                continue
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                out.append(f"{filename}:{node.lineno} imports from {node.module!r}")
            else:
                permitted = ALLOWED_FROM_IMPORTS.get(root)
                if permitted is not None:
                    for alias in node.names:
                        if alias.name not in permitted:
                            out.append(
                                f"{filename}:{node.lineno} imports "
                                f"{root}.{alias.name} — only "
                                f"{sorted(permitted)} carry no clock")
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
            elif name in GLOBAL_STATE_CALLS:
                out.append(f"{filename}:{node.lineno} mutates process-global "
                           f"decimal state: {name}()")
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

    `_violations` now enforces this too (`ALLOWED_FROM_IMPORTS`), so this is a
    second angle rather than the only one — kept because it states the rule as
    the positive fact and names the offending module in the failure, and
    because `test_engine_is_pure` would otherwise be the sole reporter of a
    regression it describes only as "not pure".
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
        # the clock half of an ALLOWED module, refused at the import itself
        ("from datetime import datetime", "datetime.datetime", 1),
        ("from datetime import *", "datetime.*", 1),
        # clock reads, including off imports that are themselves legal.
        # `import datetime` scores twice: binding the module is its own
        # violation (it exposes every name), and the call is a second.
        ("import datetime\ndef f():\n    return datetime.datetime.now()", "now", 2),
        ("from datetime import date\ndef f():\n    return date.today()", "today", 1),
        ("import datetime\ndef f():\n    return datetime.datetime.utcnow()",
         "utcnow", 2),
        # process-global decimal state, off an ALLOWED import (see
        # test_the_pinned_context_may_not_be_installed_globally)
        ("from decimal import setcontext\nsetcontext(None)", "setcontext", 1),
        ("from decimal import getcontext\ndef f():\n    getcontext().prec = 1",
         "getcontext", 1),
        # `time` is both a forbidden import and a clock call: two distinct hits
        ("import time\ndef f():\n    return time.time()", "time", 2),
        ("import time\ndef f():\n    return time.monotonic()", "monotonic", 2),
    ]
    for bad, marker, expected in cases:
        found = _violations(bad, "bad.py")
        assert found, f"{marker!r} slipped through the purity checker"
        assert len(found) == expected, f"{marker!r}: {found}"
        assert any(marker in v for v in found), f"{marker!r} not named in {found}"


def test_the_pinned_context_may_not_be_installed_globally():
    """`decimal` is allowlisted, and two of its functions undo the reason it is.

    `engine/context.py` exists because `decimal`'s context is process-global
    mutable state that any co-resident library in the Vercel bundle can move,
    so every inexact computation in `engine/` runs inside
    ``with localcontext(CTX):``. There are nine such blocks. The obvious tidy-up
    is to install the context once at import time instead — and that is the
    exact hazard the module was written to defend against:

        `setcontext(CTX)`        replaces the thread's context wholesale, so the
                                 engine's arithmetic becomes import-order
                                 dependent AND the pinned context leaks out into
                                 everything else sharing the thread.
        `getcontext().prec = N`  mutates the live context in place — same reach,
                                 no assignment to grep for.

    Both read as ordinary `decimal` usage, both would have passed the allowlist
    (the import is legal; only the call is not), and neither changes a single
    number in CI, which runs the gates in a clean process. That combination —
    plausible, invisible locally, global at runtime — is why they are denied by
    name rather than left to review.

    Written as its own test rather than two more rows in the catalogue above
    because the thing being pinned is a refactor a maintainer would consider
    reasonable, and the reasoning has to survive next to it.
    """
    tidied_up = '''
from decimal import Decimal, setcontext
from engine.context import CTX

setcontext(CTX)

def ladder(el_star, high):
    return high - Decimal("0.5") * (high - el_star)
'''
    found = _violations(tidied_up, "levels.py")
    assert len(found) == 1 and "setcontext" in found[0]

    in_place = '''
from decimal import getcontext

def widen():
    getcontext().prec = 50
'''
    found = _violations(in_place, "levels.py")
    assert len(found) == 1 and "getcontext" in found[0]

    # ...and off the module, which is how it is most often written.
    qualified = "import decimal\ndef f():\n    decimal.setcontext(decimal.Context())"
    found = _violations(qualified, "levels.py")
    assert len(found) == 1 and "setcontext" in found[0]

    # The convention these replace must stay legal — a gate that also forbade
    # `localcontext` would force the very global install it is meant to prevent.
    legal = ("from decimal import Decimal, localcontext\n"
             "from engine.context import CTX\n"
             "def f(a, b):\n"
             "    with localcontext(CTX):\n"
             "        return a / b\n")
    assert _violations(legal, "levels.py") == []


def test_datetimes_clock_half_is_denied_by_the_checker_itself():
    """`_violations` is the reusable checker, so the datetime carve-out belongs
    in it.

    `datetime` is on the allowlist for calendar arithmetic, which means
    `from datetime import datetime` — the class carrying `.now()`,
    `.utcnow()` and `.fromtimestamp()` — passed `_violations` cleanly and was
    caught only by `test_datetime_is_imported_only_for_calendar_arithmetic`
    further down this file. That made the checker weaker than its own green
    suggested: anything reusing `_violations` (the recursion test, a future
    pre-commit hook, M2's own package) inherited the hole.

    The clock is now refused at the import as well as at the call, so a module
    that merely *holds* the clock class fails without having to call it.
    """
    assert _violations("from datetime import datetime", "m.py") != []
    assert _violations("import datetime", "m.py") != []
    assert _violations("from datetime import *", "m.py") != []
    # ...and the calendar half stays legal, in both spellings.
    assert _violations("from datetime import date", "m.py") == []
    assert _violations("from datetime import date, timedelta", "m.py") == []
