#!/bin/bash
# Format Python code with Black

set -e

echo "🎨 Formatting Python code with Black..."

cd "$(dirname "$0")/.."

# Activate virtual environment and run Black
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run Black on backend and root-level Python files
python -m black backend main.py --line-length 100

echo "✨ Formatting complete!"
