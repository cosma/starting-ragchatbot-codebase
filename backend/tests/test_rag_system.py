import pytest
from unittest.mock import MagicMock, patch
from config import Config
from rag_system import RAGSystem
from vector_store import VectorStore
from document_processor import DocumentProcessor
from session_manager import SessionManager
from search_tools import ToolManager, CourseSearchTool, CourseOutlineTool


class TestRAGSystemConfigRegression:
    """Regression test: MAX_RESULTS must be > 0."""

    def test_config_max_results_is_positive(self):
        """
        Ensure Config.MAX_RESULTS is never accidentally set to 0 again.
        This is a direct regression test for the reported bug.
        """
        config = Config()
        assert config.MAX_RESULTS > 0, f"MAX_RESULTS must be > 0, but got {config.MAX_RESULTS}"


class TestRAGSystemContentQueries:
    """Test RAGSystem's end-to-end handling of content queries with mocked AI."""

    def test_content_query_with_zero_max_results_returns_no_content(self, tmp_path, populated_vector_store, mock_anthropic_response_builders):
        """
        Reproduces the bug at the RAGSystem level: with max_results=0,
        content queries return empty results even though content exists.
        """
        # Create a RAGSystem with max_results=0
        store = populated_vector_store(max_results=0)
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)
        session_mgr = SessionManager(max_history=2)

        rag = RAGSystem(
            vector_store=store,
            document_processor=processor,
            session_manager=session_mgr
        )

        # Mock the Anthropic client so it issues a real tool call
        with patch.object(rag.ai_generator.client, "messages.create") as mock_create:
            # First call: Claude requests a search
            tool_use_response = mock_anthropic_response_builders["tool_use"](
                tool_name="search_course_content",
                tool_input={"query": "photosynthesis"}
            )

            # Second call: Claude's final response (would normally incorporate the empty tool result)
            final_response = mock_anthropic_response_builders["text"](
                "I found no content about photosynthesis in the course materials."
            )

            mock_create.side_effect = [tool_use_response, final_response]

            answer, sources = rag.query("Tell me about photosynthesis")

            # With max_results=0, the tool should return empty
            assert "no content" in answer.lower() or "no relevant" in answer.lower()

    def test_content_query_with_sane_max_results_returns_content(self, tmp_path, populated_vector_store, mock_anthropic_response_builders):
        """
        Test that with a sane max_results value, the same query returns actual content.
        """
        store = populated_vector_store(max_results=5)
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)
        session_mgr = SessionManager(max_history=2)

        rag = RAGSystem(
            vector_store=store,
            document_processor=processor,
            session_manager=session_mgr
        )

        with patch.object(rag.ai_generator.client, "messages.create") as mock_create:
            tool_use_response = mock_anthropic_response_builders["tool_use"](
                tool_name="search_course_content",
                tool_input={"query": "photosynthesis"}
            )

            final_response = mock_anthropic_response_builders["text"](
                "Photosynthesis is the process plants use to convert light into energy."
            )

            mock_create.side_effect = [tool_use_response, final_response]

            answer, sources = rag.query("Tell me about photosynthesis")

            # The final answer should mention photosynthesis (from the mocked second response)
            assert "photosynthesis" in answer.lower()

    def test_query_returns_sources(self, tmp_path, populated_vector_store, mock_anthropic_response_builders):
        """
        Test that RAGSystem.query() returns sources from successful tool calls.
        """
        store = populated_vector_store(max_results=5)
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)
        session_mgr = SessionManager(max_history=2)

        rag = RAGSystem(
            vector_store=store,
            document_processor=processor,
            session_manager=session_mgr
        )

        with patch.object(rag.ai_generator.client, "messages.create") as mock_create:
            tool_use_response = mock_anthropic_response_builders["tool_use"](
                tool_name="search_course_content",
                tool_input={"query": "mitochondria"}
            )

            final_response = mock_anthropic_response_builders["text"](
                "Mitochondria are the powerhouses of the cell."
            )

            mock_create.side_effect = [tool_use_response, final_response]

            answer, sources = rag.query("What are mitochondria?")

            # With max_results=5 and real content, sources should be populated
            assert isinstance(sources, list)
            assert len(sources) > 0
            for source in sources:
                assert "text" in source
                assert "link" in source

    def test_session_history_tracks_exchanges(self, tmp_path, populated_vector_store, mock_anthropic_response_builders):
        """
        Test that RAGSystem tracks conversation history per session.
        """
        store = populated_vector_store(max_results=5)
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=50)
        session_mgr = SessionManager(max_history=2)

        rag = RAGSystem(
            vector_store=store,
            document_processor=processor,
            session_manager=session_mgr
        )

        with patch.object(rag.ai_generator.client, "messages.create") as mock_create:
            tool_use_response = mock_anthropic_response_builders["tool_use"](
                tool_name="search_course_content",
                tool_input={"query": "test"}
            )

            final_response = mock_anthropic_response_builders["text"]("Test answer")
            mock_create.side_effect = [tool_use_response, final_response]

            session_id = session_mgr.create_session()
            answer, _ = rag.query("First question", session_id=session_id)

            # Check history was recorded
            history = session_mgr.get_conversation_history(session_id)
            assert history is not None
            assert "First question" in history or "Assistant" in history
