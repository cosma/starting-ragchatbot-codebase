# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

### Running with Docker

Requires Docker with Compose. You still need a `.env` file at the project root
containing `ANTHROPIC_API_KEY`.

```bash
docker compose up --build
```

The app is served at `http://localhost:8000`. Notes:

- On first startup the container downloads the `all-MiniLM-L6-v2` embedding model
  from HuggingFace (~90 MB). It is cached in the `hf_cache` volume, so subsequent
  starts are offline and fast.
- The ChromaDB vector store is persisted in the `chroma_data` volume.
- `./docs` is mounted into the container; any `.txt`/`.pdf`/`.docx` course files
  placed there are ingested on the next startup.

To run the image directly without Compose:

```bash
docker build -t course-rag .
docker run --rm -p 8000:8000 --env-file .env \
  -v course-rag-chroma:/app/backend/chroma_db \
  -v course-rag-hf:/app/.cache/huggingface \
  course-rag
```

## Code Quality

The project uses modern Python development tools to maintain code quality and consistency.

### Development Tools

- **Black** — Automatic code formatting for consistent style (line length: 100 characters)
- **Ruff** — Fast Python linter for code quality checks (unused imports, style issues, etc.)
- **Pytest** — Testing framework for comprehensive test suite

### Running Quality Checks

Convenient shell scripts are provided in the `scripts/` directory:

#### Format Code with Black
```bash
bash scripts/format.sh
```
Automatically formats all Python code in `backend/` and the project root.

#### Check Formatting (without making changes)
```bash
bash scripts/check-format.sh
```
Verifies that code matches Black's formatting style. Useful in CI/CD pipelines.

#### Run Linter
```bash
bash scripts/lint.sh
```
Runs Ruff to check for style issues, unused imports, and potential bugs.

#### Run Tests
```bash
bash scripts/test.sh
```
Executes the full pytest test suite.

#### Run All Quality Checks
```bash
bash scripts/quality.sh
```
Runs formatting check, linting, and tests in sequence. Provides a comprehensive quality report.

### Manual Quality Tool Usage

If you prefer to run tools directly:

```bash
# Format with Black
uv run black backend main.py

# Format with Black (with custom line length)
uv run black backend main.py --line-length 100

# Check formatting without changes
uv run black backend main.py --check

# Run Ruff linter
uv run ruff check backend main.py

# Fix common linting issues automatically
uv run ruff check backend main.py --fix
```

## Testing

The project includes a comprehensive test suite to verify RAG system functionality and prevent regressions.

### Quick Diagnostic (No Heavy Dependencies)

Run a fast diagnostic that confirms the system configuration and identifies issues:

```bash
python3 backend/tests/test_bug_diagnosis.py
```

This diagnostic:
- Verifies `Config.MAX_RESULTS` is set to a reasonable value (not 0)
- Traces the bug flow end-to-end
- Runs without requiring ChromaDB or heavy ML dependencies

### Full Test Suite (Requires `uv sync`)

Install test dependencies:
```bash
uv add --dev pytest
```

Run all tests:
```bash
cd backend
uv run pytest tests/ -v
```

Run specific test file:
```bash
cd backend
uv run pytest tests/test_search_tools.py -v
```

Run specific test:
```bash
cd backend
uv run pytest tests/test_rag_system.py::TestRAGSystemConfigRegression::test_config_max_results_is_positive -v
```

### Test Suite Overview

| Test File | Purpose |
|-----------|---------|
| `test_search_tools.py` | Unit tests for `CourseSearchTool.execute()` — verifies search returns content when configured correctly |
| `test_ai_generator.py` | Tests `AIGenerator` tool-calling behavior — ensures one-round-trip constraint, correct tool invocation |
| `test_rag_system.py` | End-to-end integration tests with mocked AI — validates complete query flow, includes regression test for `MAX_RESULTS` |
| `test_bug_diagnosis.py` | Static analysis diagnostic — runnable without dependencies, confirms config is correct |

### What the Tests Catch

- ✓ Content queries return empty results when `MAX_RESULTS=0`
- ✓ Content queries return real search results when configured correctly
- ✓ Tool-calling doesn't loop beyond one round (one-round-trip constraint)
- ✓ `CourseSearchTool` populates sources correctly
- ✓ Filtering by course name and lesson number works
- ✓ Session history tracking functions properly

### Known Issue (Already Fixed)

The system was previously broken when `Config.MAX_RESULTS` was set to 0. This caused ChromaDB to be queried with `n_results=0`, always returning empty results. The config has been fixed to `MAX_RESULTS: int = 5` (matching `VectorStore`'s default). The test suite includes a regression test to prevent this bug from being re-introduced.

For details on the investigation, see [`TEST_REPORT.md`](TEST_REPORT.md) and [`TESTING_SUMMARY.md`](TESTING_SUMMARY.md).

