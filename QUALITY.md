# Code Quality Standards

This document outlines the code quality tools and standards used in this project.

## Tools Overview

### Black — Code Formatter
- **Purpose**: Automatically formats Python code for consistency
- **Configuration**: 100-character line length, targets Python 3.11+
- **Why**: Reduces code review friction by removing style debates

### Ruff — Fast Python Linter
- **Purpose**: Checks for common errors, style issues, and imports
- **Rules Enabled**:
  - `E/W` — pycodestyle errors and warnings
  - `F` — Pyflakes (undefined names, unused imports)
  - `I` — isort (import sorting)
  - `B` — flake8-bugbear (common bugs)
  - `C4` — flake8-comprehensions (optimization)
- **Why**: Catches bugs early and enforces consistent import ordering

### Pytest — Testing Framework
- **Purpose**: Runs the test suite to verify functionality
- **Test Location**: `backend/tests/`
- **Configuration**: Uses `backend/` as pythonpath for imports

## Development Workflow

### Pre-commit Quality Checks
Before committing code, run the quality checks:

```bash
bash scripts/quality.sh
```

This runs:
1. **Format check** — Verifies Black formatting
2. **Linting** — Runs Ruff checks
3. **Tests** — Executes the test suite

### Individual Quality Tools

#### Format Code (Make Changes)
```bash
bash scripts/format.sh
```
Automatically formats all Python code. Use this to fix formatting errors reported by `check-format.sh`.

#### Check Formatting (No Changes)
```bash
bash scripts/check-format.sh
```
Validates that code matches Black's style without modifying files. Good for CI/CD pipelines.

#### Run Linter
```bash
bash scripts/lint.sh
```
Checks for code quality issues using Ruff. Many issues can be auto-fixed with:
```bash
bash scripts/lint-fix.sh
```

#### Run Tests
```bash
bash scripts/test.sh
```
Executes all tests in `backend/tests/`.

## Configuration

All tool configurations are in `pyproject.toml`:

```toml
[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4"]
ignore = ["E501"]  # Black handles line length
```

## Common Issues & Fixes

### ❌ "Formatting check failed"
Black formatting doesn't match the standard:
```bash
bash scripts/format.sh  # Auto-fix formatting
```

### ❌ "Lint checks failed"
Ruff found code quality issues. View details:
```bash
bash scripts/lint.sh  # See detailed errors
```

Most import and unused variable issues can be auto-fixed:
```bash
source .venv/bin/activate
python -m ruff check backend main.py --fix
```

### ❌ Exception handling issues (B904)
When raising exceptions in an `except` block, always chain them:

❌ **Wrong**:
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

✅ **Correct**:
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e)) from e
```

This preserves the original exception context for debugging.

### ❌ Unused imports
Remove imports not used in the code. Ruff can auto-fix these:
```bash
source .venv/bin/activate
python -m ruff check backend main.py --fix
```

## Manual Tool Usage

If you prefer to run tools directly without scripts:

```bash
# Install dev tools (if not already installed)
uv sync --group dev

# Format with Black
uv run black backend main.py --line-length 100

# Check formatting without changes
uv run black backend main.py --check

# Run Ruff linter
uv run ruff check backend main.py

# Auto-fix linting issues
uv run ruff check backend main.py --fix

# Run tests
cd backend
uv run pytest tests/ -v
```

## CI/CD Integration

For automated quality checks in CI/CD pipelines, run:

```bash
bash scripts/quality.sh
```

This provides a clear pass/fail status and detailed error messages.

## Standards

- **Code Style**: Black (100 character lines)
- **Imports**: Sorted by Ruff's isort rules
- **Errors**: No unused imports, undefined names, or obvious bugs
- **Exceptions**: Chained with `from e` for proper tracebacks
- **Tests**: All tests must pass before merging
