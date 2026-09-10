import pytest
import tempfile
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
import anthropic.types as types
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vector_store import VectorStore
from document_processor import DocumentProcessor
from config import Config
from rag_system import RAGSystem
from session_manager import SessionManager


TINY_COURSE_TEXT = """Course Title: Biology 101
Course Link: https://example.com/biology
Course Instructor: Dr. Smith

Lesson 0: Introduction to Photosynthesis
Lesson Link: https://example.com/biology/lesson0
Photosynthesis is the process by which plants convert light energy into chemical energy.
This happens in the chloroplasts of plant cells. The photosynthesis process involves two main stages:
the light-dependent reactions and the light-independent reactions. Photosynthesis produces glucose and oxygen.

Lesson 1: The Mitochondria and Cellular Respiration
Lesson Link: https://example.com/biology/lesson1
Mitochondria are the powerhouses of the cell, responsible for producing energy.
Mitochondria contain their own DNA and ribosomes. Cellular respiration occurs in the mitochondria
and converts glucose into ATP. This process is essential for all living organisms.
"""


@pytest.fixture
def tiny_course_text():
    """A small course in standard ingestion format for testing."""
    return TINY_COURSE_TEXT


@pytest.fixture
def populated_vector_store(tmp_path):
    """
    Create and populate a VectorStore with test data using real DocumentProcessor.
    Yields a factory function so tests can override max_results.
    """
    def _create_store(max_results: int = 5) -> VectorStore:
        chroma_path = str(tmp_path / f"chroma_test_{max_results}")
        store = VectorStore(
            chroma_path=chroma_path,
            embedding_model="all-MiniLM-L6-v2",
            max_results=max_results
        )

        # Write course text to temp file and ingest it
        course_file = tmp_path / "test_course.txt"
        course_file.write_text(TINY_COURSE_TEXT)

        processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)
        course = processor.process_course_document(str(course_file))

        if course:
            store.add_course_metadata(course)
            store.add_course_content(course.chunks)

        return store

    return _create_store


def mock_anthropic_text_response(text: str) -> MagicMock:
    """Build a mock anthropic Message with a single text content block."""
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_content = MagicMock()
    mock_content.type = "text"
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


def mock_anthropic_tool_use_response(tool_name: str, tool_input: dict) -> MagicMock:
    """Build a mock anthropic Message with a tool_use content block."""
    mock_response = MagicMock()
    mock_response.stop_reason = "tool_use"
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.id = "test_tool_use_id"
    mock_tool_use.name = tool_name
    mock_tool_use.input = tool_input
    mock_response.content = [mock_tool_use]
    return mock_response


@pytest.fixture
def mock_anthropic_response_builders():
    """Provide builder functions for mocking Anthropic responses."""
    return {
        "text": mock_anthropic_text_response,
        "tool_use": mock_anthropic_tool_use_response,
    }


# FastAPI Testing Fixtures

@pytest.fixture
def test_app():
    """
    Create a test FastAPI app with API endpoints but without static file mounting.
    This avoids issues with missing frontend directory in test environment.
    """
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI(title="Course Materials RAG System (Test)")

    # Pydantic models
    class Source(BaseModel):
        text: str
        link: Optional[str] = None

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Source]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Placeholder RAG system (will be mocked in tests)
    app.rag_system = None

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        if app.rag_system is None:
            raise RuntimeError("RAG system not initialized")
        session_id = request.session_id
        if not session_id:
            session_id = app.rag_system.session_manager.create_session()
        answer, sources = app.rag_system.query(request.query, session_id)
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id
        )

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        if app.rag_system is None:
            raise RuntimeError("RAG system not initialized")
        app.rag_system.session_manager.delete_session(session_id)
        return {"status": "ok"}

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        if app.rag_system is None:
            raise RuntimeError("RAG system not initialized")
        analytics = app.rag_system.get_course_analytics()
        return CourseStats(
            total_courses=analytics["total_courses"],
            course_titles=analytics["course_titles"]
        )

    return app


@pytest.fixture
def test_client(test_app):
    """Create a TestClient for the test FastAPI app."""
    return TestClient(test_app)


@pytest.fixture
def mock_rag_system(populated_vector_store):
    """
    Create a mock RAGSystem for API testing.
    """
    mock_system = MagicMock(spec=RAGSystem)
    mock_system.session_manager = MagicMock(spec=SessionManager)
    mock_system.session_manager.create_session.return_value = "test-session-123"

    # Mock query method
    def mock_query(query: str, session_id: str):
        return (
            "Test answer",
            [{"text": "Test source", "link": "https://example.com"}]
        )

    mock_system.query.side_effect = mock_query

    # Mock analytics
    def mock_analytics():
        return {
            "total_courses": 1,
            "course_titles": ["Biology 101"]
        }

    mock_system.get_course_analytics.side_effect = mock_analytics

    return mock_system


@pytest.fixture
def app_with_rag_system(test_app, mock_rag_system):
    """Inject mock RAG system into test app and return both."""
    test_app.rag_system = mock_rag_system
    return test_app, mock_rag_system


@pytest.fixture
def client_with_rag_system(test_client, mock_rag_system):
    """Inject mock RAG system into test client's app."""
    test_client.app.rag_system = mock_rag_system
    return test_client


@pytest.fixture
def sample_query_request():
    """Sample query request data."""
    return {
        "query": "What is photosynthesis?",
        "session_id": None
    }


@pytest.fixture
def sample_query_response():
    """Sample query response data."""
    return {
        "answer": "Photosynthesis is the process by which plants convert light energy into chemical energy.",
        "sources": [
            {
                "text": "Photosynthesis happens in chloroplasts",
                "link": "https://example.com/lesson0"
            }
        ],
        "session_id": "test-session-123"
    }
