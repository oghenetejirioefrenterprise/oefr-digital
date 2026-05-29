#!/bin/bash
# Distribution sweep execution wrapper
# Sources env vars from ~/.profile and runs the posting script

set -e

cd "$(dirname "$0")"

# Source environment
if [ -f ~/.profile ]; then
    set -a  # Export all variables
    source ~/.profile
    set +a
else
    echo "ERROR: ~/.profile not found"
    exit 1
fi

# Verify key env vars are set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set in ~/.profile"
    exit 1
fi

if [ -z "$X_USERNAME" ] || [ -z "$X_PASS" ]; then
    echo "ERROR: X_USERNAME or X_PASS not set in ~/.profile"
    exit 1
fi

if [ -z "$REDDIT_USERNAME" ] || [ -z "$REDDIT_PASSWORD" ]; then
    echo "ERROR: REDDIT_USERNAME or REDDIT_PASSWORD not set in ~/.profile"
    exit 1
fi

# Run the distribution sweep
echo "==================================================================="
echo "Starting distribution sweep..."
echo "==================================================================="
echo ""

exec python3 scripts/post_all.py "$@"
