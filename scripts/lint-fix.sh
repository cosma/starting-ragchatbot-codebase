#!/bin/bash
# Auto-fix linting issues with Ruff

set -e

echo "🔧 Auto-fixing Ruff linting issues..."

cd "$(dirname "$0")/.."

# Activate virtual environment and run Ruff with --fix
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run Ruff with fix flag
python -m ruff check backend main.py --fix

echo "✅ Lint fixes applied!"
echo ""
echo "Note: Some issues may require manual fixes. Run 'bash scripts/lint.sh' to see remaining issues."
