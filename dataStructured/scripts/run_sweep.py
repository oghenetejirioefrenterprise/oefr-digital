#!/usr/bin/env python3
"""Wrapper to run distribution sweep with env vars loaded from ~/.profile"""
import os
import re
import sys
from pathlib import Path

def load_profile_env():
    """Load env vars from ~/.profile into current environment."""
    profile = Path.home() / ".profile"
    if not profile.exists():
        return

    for line in profile.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            # Match: export KEY=value or export KEY="value" or export KEY='value'.
            # Anchored to end-of-line (line is already stripped) so the final export
            # is captured even without a trailing newline.
            match = re.match(r'''export\s+(\w+)=(['"]?)(.*?)\2\s*$''', line)
            if match:
                key = match.group(1)
                # Expand $VAR / ${VAR} references against the current environment,
                # so composed values (e.g. export FOO=$BAR/x) resolve correctly.
                value = os.path.expandvars(match.group(3))
                os.environ[key] = value

if __name__ == "__main__":
    # Load env vars
    load_profile_env()

    # Re-exec with loaded environment
    script = Path(__file__).parent / "distribution_sweep.py"
    os.execvp("python3", ["python3", str(script)] + sys.argv[1:])
