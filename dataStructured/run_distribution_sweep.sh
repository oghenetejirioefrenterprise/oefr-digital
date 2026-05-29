#!/bin/bash
# Distribution sweep runner — sources env vars and runs the Python script

set -e

cd "$(dirname "$0")"

# Source environment variables
source ~/.profile

# Run the distribution sweep
python3 scripts/distribution_sweep.py "$@"
