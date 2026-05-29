#!/usr/bin/env python3
"""Wrapper to run distribution sweep with env vars loaded from ~/.profile"""
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from scripts.lib.env import load_profile_env  # noqa: E402

if __name__ == "__main__":
    # Load env vars
    load_profile_env()

    # Re-exec with loaded environment
    script = Path(__file__).parent / "distribution_sweep.py"
    os.execvp("python3", ["python3", str(script)] + sys.argv[1:])
