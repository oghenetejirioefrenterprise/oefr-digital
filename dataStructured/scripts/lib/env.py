"""Load environment variables from ``~/.profile``.

Consolidates the ~13 divergent ``load_profile_env`` copies that were scattered
across scripts. Parses ``export KEY=value`` lines (double-quoted, single-quoted,
or bare) and expands ``$VAR`` / ``${VAR}`` references against the current
environment so composed values (e.g. ``export FOO=$BAR/x``) resolve correctly.

This is the single source of truth — scripts should ``from scripts.lib.env
import load_profile_env`` rather than re-implementing the parse.
"""
import os
import re
from pathlib import Path
from typing import Optional

# Anchored to end-of-line (line is pre-stripped) so the final export is captured
# even without a trailing newline. Group 2 is the optional matching quote.
_EXPORT = re.compile(r"""export\s+(\w+)=(['"]?)(.*?)\2\s*$""")


def load_profile_env(path: Optional[Path] = None, *, override: bool = True) -> dict:
    """Load ``export KEY=value`` lines from ``~/.profile`` into ``os.environ``.

    Args:
        path: profile file to read; defaults to ``~/.profile``.
        override: when True (default), values overwrite any pre-set environment
            variables, matching ``source ~/.profile`` semantics. Pass False to
            preserve values already present in ``os.environ``.

    Returns:
        Dict of the keys that were set (empty if the file is missing).
    """
    profile = Path(path) if path else Path.home() / ".profile"
    if not profile.exists():
        return {}

    loaded: dict = {}
    for line in profile.read_text().splitlines():
        line = line.strip()
        if not line.startswith("export "):
            continue
        m = _EXPORT.match(line)
        if not m:
            continue
        key = m.group(1)
        if not override and key in os.environ:
            continue
        value = os.path.expandvars(m.group(3))
        os.environ[key] = value
        loaded[key] = value
    return loaded
