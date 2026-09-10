#!/bin/bash
# Run the test suite

set -e

echo "🧪 Running tests..."

cd "$(dirname "$0")/.."

# Use uv to run tests (preferred method that handles all dependencies)
cd backend
uv run pytest tests/ -v

echo "✅ All tests passed!"
