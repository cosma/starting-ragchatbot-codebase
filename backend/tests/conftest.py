import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
import anthropic.types as types
from vector_store import VectorStore
from document_processor import DocumentProcessor
from config import Config


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
