# Enhanced Testing Framework for RAG System

This document describes the comprehensive testing infrastructure added to the RAG system project.

## Overview

The testing framework now includes:
- **API Endpoint Tests** — Test FastAPI endpoints with proper request/response validation
- **Enhanced Fixtures** — Shared fixtures for mocking and test data setup
- **Pytest Configuration** — Optimized pytest settings in `pyproject.toml`
- **Test Markers** — Categorize tests by type (unit, integration, api)

## Test Structure

```
backend/tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_api_endpoints.py          # API endpoint tests (NEW)
├── test_ai_generator.py           # AIGenerator unit tests
├── test_search_tools.py           # Search tools unit tests
├── test_rag_system.py             # RAGSystem integration tests
├── test_bug_diagnosis.py          # Diagnostic tests
└── README_TESTING.md              # This file
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
uv sync
```

### Run All Tests
```bash
uv run pytest
```

### Run Tests by Category

```bash
# Only unit tests
uv run pytest -m unit

# Only integration tests
uv run pytest -m integration

# Only API tests
uv run pytest -m api

# Run all except slow tests
uv run pytest -m "not slow"
```

### Run Specific Test Files
```bash
# Test API endpoints
uv run pytest backend/tests/test_api_endpoints.py -v

# Test AI generator
uv run pytest backend/tests/test_ai_generator.py -v

# Test search tools
uv run pytest backend/tests/test_search_tools.py -v

# Test RAG system
uv run pytest backend/tests/test_rag_system.py -v
```

### Run Specific Test Class or Function
```bash
# Test query endpoint
uv run pytest backend/tests/test_api_endpoints.py::TestQueryEndpoint -v

# Test specific function
uv run pytest backend/tests/test_api_endpoints.py::TestQueryEndpoint::test_query_with_new_session -v
```

### Verbose Output
```bash
uv run pytest -v                    # Verbose
uv run pytest -vv                   # Very verbose with full diff
uv run pytest -s                    # Show print statements
uv run pytest -x                    # Stop on first failure
```

## Test Fixtures (conftest.py)

### Vector Store Fixtures

**`tiny_course_text`**
- Provides a small course in standard ingestion format for testing
- Used by other fixtures to create test data

**`populated_vector_store`**
- Factory fixture that creates a VectorStore with test data
- Automatically ingests `tiny_course_text` using DocumentProcessor
- Accepts `max_results` parameter to customize behavior
- Usage: `def test_something(populated_vector_store): store = populated_vector_store(max_results=5)`

### Anthropic Mocking Fixtures

**`mock_anthropic_response_builders`**
- Dictionary with builder functions: `"text"` and `"tool_use"`
- `mock_anthropic_text_response(text)` — Creates mock Anthropic Message with text response
- `mock_anthropic_tool_use_response(tool_name, tool_input)` — Creates mock with tool_use
- Returns properly structured MagicMock objects matching Anthropic API format

### FastAPI Testing Fixtures

**`test_app`**
- Creates a test FastAPI app with all API endpoints but NO static file mounting
- Avoids import errors from missing `frontend/` directory
- Includes all Pydantic request/response models
- Has placeholder for `app.rag_system` that tests inject

**`test_client`**
- FastAPI TestClient for making HTTP requests to `test_app`
- Use for simple tests without mocking RAG system

**`mock_rag_system`**
- Mocked RAGSystem with sensible defaults
- `create_session()` returns `"test-session-123"`
- `query()` returns `("Test answer", [{"text": "Test source", "link": "..."}])`
- `get_course_analytics()` returns `{"total_courses": 1, "course_titles": ["Biology 101"]}`

**`app_with_rag_system`**
- Returns tuple: `(test_app, mock_rag_system)` with system already injected
- For tests that need to configure the mock after setup

**`client_with_rag_system`**
- TestClient with mock_rag_system already injected into the app
- **Most common fixture for API tests** — use this for testing endpoints

### Sample Data Fixtures

**`sample_query_request`**
- Dictionary with sample query data: `{"query": "...", "session_id": None}`

**`sample_query_response`**
- Dictionary with sample response data including answer, sources, and session_id

## API Endpoint Tests (test_api_endpoints.py)

### TestQueryEndpoint

Tests the `POST /api/query` endpoint:

- `test_query_with_new_session()` — Query without session_id creates new session
- `test_query_with_existing_session()` — Query with session_id uses that session
- `test_query_with_empty_query_string()` — Handles empty queries gracefully
- `test_query_response_structure()` — Response has required fields (answer, sources, session_id)
- `test_query_sources_have_correct_structure()` — Each source has text and optional link

### TestCourseStatsEndpoint

Tests the `GET /api/courses` endpoint:

- `test_courses_endpoint_success()` — Returns course statistics
- `test_courses_response_structure()` — Response has total_courses and course_titles
- `test_courses_endpoint_with_no_courses()` — Handles empty course list

### TestSessionManagementEndpoint

Tests the `DELETE /api/session/{session_id}` endpoint:

- `test_delete_session_success()` — Successfully deletes a session
- `test_delete_nonexistent_session()` — Handles missing sessions gracefully

### TestErrorHandling

Tests error conditions:

- `test_query_endpoint_without_rag_system()` — Proper error when RAG system not initialized
- `test_courses_endpoint_without_rag_system()` — Error handling for courses endpoint
- `test_query_endpoint_with_rag_error()` — Catches and reports RAG system exceptions

### TestEndpointIntegration

Integration tests across multiple endpoints:

- `test_full_query_workflow()` — Query → check courses → use same session
- `test_multiple_queries_different_sessions()` — Multiple concurrent queries
- `test_session_cleanup_workflow()` — Create and delete session lifecycle

## Pytest Configuration

Configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["backend"]                                    # Import modules from backend/
testpaths = ["backend/tests"]                              # Test discovery path
python_files = ["test_*.py", "*_test.py"]                  # Test file patterns
python_classes = ["Test*"]                                  # Test class patterns
python_functions = ["test_*"]                              # Test function patterns
addopts = "-v --tb=short --strict-markers"                 # Verbose + short tracebacks
markers = [
    "unit: Unit tests for individual components",
    "integration: Integration tests for multiple components",
    "api: API endpoint tests",
    "slow: Slow running tests",
]
minversion = "8.0"
```

### Pytest Flags Explained

- `-v` — Verbose output (shows each test name)
- `--tb=short` — Shorter tracebacks (less clutter)
- `--strict-markers` — Enforce declared markers (prevents typos)

## Test Markers

All tests are marked with one of:

```python
pytestmark = pytest.mark.unit           # Unit tests
pytestmark = pytest.mark.integration    # Integration tests
pytestmark = pytest.mark.api            # API endpoint tests
```

Example usage:
```bash
uv run pytest -m unit              # Only unit tests
uv run pytest -m "not slow"        # All except slow
uv run pytest -m "unit or api"     # Unit or API tests
```

## Handling Static Files in Tests

The production `app.py` mounts static files:
```python
app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")
```

The test app avoids this by:
1. Creating endpoints directly without mounting StaticFiles
2. Defining all Pydantic models inline
3. Injecting mock RAGSystem via `app.rag_system`

This allows tests to run without needing the `frontend/` directory present.

## Example: Writing a New API Test

```python
def test_query_returns_sources_with_links(client_with_rag_system):
    """Test that query responses include source links."""
    response = client_with_rag_system.post(
        "/api/query",
        json={"query": "What is photosynthesis?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify sources have links
    for source in data["sources"]:
        assert "link" in source
        assert source["link"].startswith("https://")
```

## Example: Testing with Custom Mock

```python
def test_query_with_many_results(test_app, mock_rag_system):
    """Test query with large number of results."""
    # Customize the mock
    mock_rag_system.query.return_value = (
        "Answer",
        [{"text": f"Source {i}", "link": f"https://example.com/{i}"} for i in range(100)]
    )
    test_app.rag_system = mock_rag_system
    
    client = TestClient(test_app)
    response = client.post("/api/query", json={"query": "test"})
    
    assert len(response.json()["sources"]) == 100
```

## Continuous Integration

For CI/CD pipelines, run tests with:
```bash
uv run pytest --tb=short --junit-xml=test-results.xml
```

This generates an XML report for integration with CI systems.

## Common Issues

### ImportError: No module named 'fastapi'
- Run `uv sync` to install dependencies

### Test discovery not finding tests
- Ensure test files match pattern `test_*.py` or `*_test.py`
- Ensure test classes start with `Test`
- Ensure test functions start with `test_`

### Fixture not found
- Check that fixture is defined in `conftest.py`
- Check function parameter name matches fixture name exactly
- Fixtures must be defined at module level or in `conftest.py`

### Mock not being called
- Use `mock.assert_called_with(...)` or `mock.assert_called_once()`
- Check that mock is passed to function being tested
- Print mock.call_args to debug

## Next Steps

1. Run the test suite to verify everything works
2. Add tests for any new endpoints added to `app.py`
3. Keep test fixtures up-to-date as API changes
4. Monitor test coverage and add tests for edge cases
