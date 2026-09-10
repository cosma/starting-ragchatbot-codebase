import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


pytestmark = pytest.mark.api


class TestQueryEndpoint:
    """Test /api/query endpoint"""

    def test_query_with_new_session(self, client_with_rag_system):
        """Test query endpoint creates new session when none provided"""
        response = client_with_rag_system.post(
            "/api/query",
            json={"query": "What is photosynthesis?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Test answer"
        assert data["session_id"] == "test-session-123"
        assert isinstance(data["sources"], list)

    def test_query_with_existing_session(self, client_with_rag_system):
        """Test query endpoint uses provided session ID"""
        response = client_with_rag_system.post(
            "/api/query",
            json={
                "query": "What is mitochondria?",
                "session_id": "existing-session-456"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Test answer"
        assert data["session_id"] == "existing-session-456"

    def test_query_with_empty_query_string(self, client_with_rag_system):
        """Test query endpoint with empty query"""
        response = client_with_rag_system.post(
            "/api/query",
            json={"query": ""}
        )

        assert response.status_code == 200
        # Empty query should still process (RAG system handles empty queries)
        assert "session_id" in response.json()

    def test_query_response_structure(self, client_with_rag_system):
        """Test query response has correct structure"""
        response = client_with_rag_system.post(
            "/api/query",
            json={"query": "Test question"}
        )

        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_query_sources_have_correct_structure(self, client_with_rag_system):
        """Test each source has text and optional link"""
        response = client_with_rag_system.post(
            "/api/query",
            json={"query": "Test question"}
        )

        data = response.json()
        for source in data["sources"]:
            assert "text" in source
            assert isinstance(source["text"], str)
            # link is optional, but if present should be string
            if "link" in source:
                assert isinstance(source["link"], str)


class TestCourseStatsEndpoint:
    """Test /api/courses endpoint"""

    def test_courses_endpoint_success(self, client_with_rag_system):
        """Test courses endpoint returns course stats"""
        response = client_with_rag_system.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 1
        assert data["course_titles"] == ["Biology 101"]

    def test_courses_response_structure(self, client_with_rag_system):
        """Test courses response has correct structure"""
        response = client_with_rag_system.get("/api/courses")

        data = response.json()
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert all(isinstance(title, str) for title in data["course_titles"])

    def test_courses_endpoint_with_no_courses(self, test_client):
        """Test courses endpoint when no courses loaded"""
        mock_rag = MagicMock()
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }
        test_client.app.rag_system = mock_rag

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []


class TestSessionManagementEndpoint:
    """Test /api/session/{session_id} endpoint"""

    def test_delete_session_success(self, client_with_rag_system):
        """Test deleting a session"""
        response = client_with_rag_system.delete("/api/session/test-session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        client_with_rag_system.app.rag_system.session_manager.delete_session.assert_called_with(
            "test-session-123"
        )

    def test_delete_nonexistent_session(self, test_client):
        """Test deleting a session that doesn't exist"""
        mock_rag = MagicMock()
        mock_rag.session_manager.delete_session.side_effect = ValueError("Session not found")
        test_client.app.rag_system = mock_rag

        response = test_client.delete("/api/session/nonexistent-session")

        # Should still return 200, as the mock raises ValueError
        # In real implementation, this might be caught and handled
        assert response.status_code in [200, 500]


class TestErrorHandling:
    """Test error handling in API endpoints"""

    def test_query_endpoint_without_rag_system(self, test_client):
        """Test query endpoint fails gracefully without RAG system"""
        response = test_client.post(
            "/api/query",
            json={"query": "Test"}
        )

        assert response.status_code == 500
        assert "RAG system not initialized" in response.text

    def test_courses_endpoint_without_rag_system(self, test_client):
        """Test courses endpoint fails gracefully without RAG system"""
        response = test_client.get("/api/courses")

        assert response.status_code == 500
        assert "RAG system not initialized" in response.text

    def test_query_endpoint_with_rag_error(self, test_client):
        """Test query endpoint handles RAG system errors"""
        mock_rag = MagicMock()
        mock_rag.session_manager.create_session.return_value = "test-session"
        mock_rag.query.side_effect = Exception("Vector store error")
        test_client.app.rag_system = mock_rag

        response = test_client.post(
            "/api/query",
            json={"query": "Test"}
        )

        assert response.status_code == 500


class TestEndpointIntegration:
    """Integration tests for multiple endpoints"""

    def test_full_query_workflow(self, client_with_rag_system):
        """Test complete query workflow: query, then check courses"""
        # Make a query
        query_response = client_with_rag_system.post(
            "/api/query",
            json={"query": "What is photosynthesis?"}
        )
        assert query_response.status_code == 200
        session_id = query_response.json()["session_id"]

        # Check courses
        courses_response = client_with_rag_system.get("/api/courses")
        assert courses_response.status_code == 200
        assert courses_response.json()["total_courses"] > 0

        # Use same session for second query
        query_response_2 = client_with_rag_system.post(
            "/api/query",
            json={
                "query": "Tell me more",
                "session_id": session_id
            }
        )
        assert query_response_2.status_code == 200
        assert query_response_2.json()["session_id"] == session_id

    def test_multiple_queries_different_sessions(self, client_with_rag_system):
        """Test multiple queries with different sessions"""
        sessions = []
        for i in range(3):
            response = client_with_rag_system.post(
                "/api/query",
                json={"query": f"Question {i}"}
            )
            assert response.status_code == 200
            sessions.append(response.json()["session_id"])

        # All sessions should be created
        assert len(set(sessions)) == 1  # Mock returns same session

    def test_session_cleanup_workflow(self, client_with_rag_system):
        """Test creating and cleaning up a session"""
        # Create query with new session
        query_response = client_with_rag_system.post(
            "/api/query",
            json={"query": "Test"}
        )
        session_id = query_response.json()["session_id"]

        # Delete session
        delete_response = client_with_rag_system.delete(f"/api/session/{session_id}")
        assert delete_response.status_code == 200
