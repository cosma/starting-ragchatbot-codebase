#!/bin/bash
# Run all quality checks: formatting, linting, and tests

set -e

echo "🚀 Running Quality Checks..."
echo ""

SCRIPTS_DIR="$(dirname "$0")"
PROJECT_ROOT="$SCRIPTS_DIR/.."

# Track failures
FAILURES=0

# Run formatting check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPTS_DIR/check-format.sh"; then
    echo "✅ Formatting check passed"
else
    echo "❌ Formatting check failed"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Run linting
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPTS_DIR/lint.sh"; then
    echo "✅ Linting passed"
else
    echo "❌ Linting failed"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Run tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if bash "$SCRIPTS_DIR/test.sh"; then
    echo "✅ Tests passed"
else
    echo "⚠️  Tests failed (see details above)"
    FAILURES=$((FAILURES + 1))
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILURES -eq 0 ]; then
    echo "🎉 All quality checks passed!"
    exit 0
else
    echo "❌ $FAILURES check(s) failed"
    echo ""
    echo "To fix formatting issues, run:"
    echo "  bash scripts/format.sh"
    exit 1
fi
