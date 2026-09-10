#!/bin/bash
# Run Ruff linter checks

set -e

echo "🔎 Running Ruff linter checks..."

cd "$(dirname "$0")/.."

# Activate virtual environment and run Ruff
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run Ruff
python -m ruff check backend main.py

echo "✅ Lint checks passed!"
