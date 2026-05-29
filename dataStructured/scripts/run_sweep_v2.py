#!/usr/bin/env python3
"""Wrapper to run distribution sweep with env vars loaded from ~/.profile"""
import os
import re
import subprocess
import sys
from pathlib import Path

def load_profile_env():
    """Load env vars from ~/.profile into current environment."""
    profile = Path.home() / ".profile"
    if not profile.exists():
        print(f"Warning: {profile} not found")
        return

    content = profile.read_text()
    # Try multiple export patterns
    patterns = [
        r'export\s+(\w+)="([^"]+)"',
        r"export\s+(\w+)='([^']+)'",
        r'export\s+(\w+)=([^\s#]+)',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            key, value = match.groups()
            if key not in os.environ:  # Don't override existing vars
                # Expand $VAR / ${VAR} references (e.g. export PATH=$PATH:/usr/local/bin)
                # against the current environment so composed values resolve correctly
                # instead of being injected as literal "$VAR" text.
                os.environ[key] = os.path.expandvars(value)
                # print(f"Loaded: {key}=***")  # Debug


if __name__ == "__main__":
    # Load env vars into current process
    load_profile_env()

    # Verify key vars are set
    required_vars = ["ANTHROPIC_API_KEY", "X_USERNAME", "X_PASS", "REDDIT_USERNAME", "REDDIT_PASSWORD"]
    missing = [v for v in required_vars if not os.environ.get(v)]
    if missing and "--dry-run" not in sys.argv:
        print(f"Warning: Missing env vars: {', '.join(missing)}")

    # Run distribution sweep in a subprocess with inherited environment
    script = Path(__file__).parent / "distribution_sweep.py"
    result = subprocess.run(
        ["python3", str(script)] + sys.argv[1:],
        env=os.environ.copy()
    )
    sys.exit(result.returncode)
