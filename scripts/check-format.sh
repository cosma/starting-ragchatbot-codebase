#!/bin/bash
# Check code formatting with Black (without making changes)

set -e

echo "🔍 Checking Python code formatting..."

cd "$(dirname "$0")/.."

# Activate virtual environment and run Black in check mode
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run Black in check mode
python -m black backend main.py --check --diff --line-length 100

echo "✅ All code properly formatted!"
