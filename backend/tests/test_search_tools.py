import pytest
from search_tools import CourseSearchTool, ToolManager
from vector_store import VectorStore


pytestmark = pytest.mark.unit


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() behavior with different VectorStore configs."""

    def test_execute_with_max_results_zero_returns_empty(self, populated_vector_store):
        """
        Reproduces the bug: execute() with max_results=0 returns "No relevant content found"
        even though the course exists and contains matching content.
        """
        store = populated_vector_store(max_results=0)
        tool = CourseSearchTool(store)

        result = tool.execute(query="photosynthesis")

        assert "No relevant content found" in result
        assert "photosynthesis" not in result.lower()

    def test_execute_with_sane_max_results_returns_content(self, populated_vector_store):
        """
        Test that execute() returns actual content when max_results is reasonable.
        """
        store = populated_vector_store(max_results=5)
        tool = CourseSearchTool(store)

        result = tool.execute(query="photosynthesis")

        assert "No relevant content found" not in result
        assert "photosynthesis" in result.lower() or "Lesson" in result
        assert "[Biology 101" in result

    def test_execute_populates_sources(self, populated_vector_store):
        """
        Test that execute() populates last_sources with course/lesson links.
        """
        store = populated_vector_store(max_results=5)
        tool = CourseSearchTool(store)

        result = tool.execute(query="mitochondria")

        assert tool.last_sources
        assert len(tool.last_sources) > 0
        for source in tool.last_sources:
            assert "text" in source
            assert "link" in source
            assert isinstance(source["text"], str)
            assert isinstance(source["link"], (str, type(None)))

    def test_execute_with_invalid_course_name(self, populated_vector_store):
        """
        Test that execute() with a course_name that doesn't fuzzy-match
        returns a "No course found" error.
        """
        store = populated_vector_store(max_results=5)
        tool = CourseSearchTool(store)

        result = tool.execute(
            query="photosynthesis",
            course_name="NonexistentCourse XYZ"
        )

        assert "No course found" in result

    def test_execute_with_valid_course_name(self, populated_vector_store):
        """
        Test that execute() with a partial course name that fuzzy-matches
        returns content.
        """
        store = populated_vector_store(max_results=5)
        tool = CourseSearchTool(store)

        result = tool.execute(
            query="photosynthesis",
            course_name="Biology"
        )

        assert "No relevant content found" not in result
        assert "No course found" not in result
        assert "photosynthesis" in result.lower() or "Lesson" in result

    def test_execute_with_lesson_number_filter(self, populated_vector_store):
        """
        Test that execute() with a lesson_number filter correctly limits results
        to that lesson's content.
        """
        store = populated_vector_store(max_results=5)
        tool = CourseSearchTool(store)

        result = tool.execute(
            query="mitochondria",
            lesson_number=1
        )

        # Mitochondria is in lesson 1, so should find it
        assert "No relevant content found" not in result
        assert "Lesson 1" in result or "mitochondria" in result.lower()


class TestToolManager:
    """Test ToolManager's source handling."""

    def test_get_last_sources_empty_initially(self, populated_vector_store):
        """
        Test that get_last_sources() returns empty list when no tool has run yet.
        """
        store = populated_vector_store(max_results=5)
        tool = CourseSearchTool(store)
        manager = ToolManager()
        manager.register_tool(tool)

        sources = manager.get_last_sources()
        assert sources == []

    def test_reset_sources_clears_all_tools(self, populated_vector_store):
        """
        Test that reset_sources() clears last_sources from all tools.
        """
        store = populated_vector_store(max_results=5)
        tool = CourseSearchTool(store)
        manager = ToolManager()
        manager.register_tool(tool)

        tool.execute(query="photosynthesis")
        assert manager.get_last_sources()

        manager.reset_sources()
        assert manager.get_last_sources() == []
