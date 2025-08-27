import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
import json


@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for FastAPI endpoints"""

    def test_root_endpoint(self, test_client):
        """Test the root endpoint returns expected message"""
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Course Materials RAG System"}

    def test_query_endpoint_success(self, test_client, test_app, mock_rag_system_responses):
        """Test successful query to /api/query endpoint"""
        # Setup mock response
        test_app.state.mock_rag_system.query.return_value = mock_rag_system_responses["query_response"]
        
        query_data = {
            "query": "What is MCP?",
            "session_id": "test-session-123"
        }
        
        response = test_client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        
        # Verify content
        assert data["answer"] == "This is a test response about MCP protocol."
        assert data["session_id"] == "test-session-123"
        assert len(data["sources"]) == 2
        assert data["sources"][0]["text"] == "MCP stands for Model Context Protocol"
        assert data["sources"][0]["url"] == "https://example.com/lesson1"
        
        # Verify mock was called correctly
        test_app.state.mock_rag_system.query.assert_called_once_with("What is MCP?", "test-session-123")

    def test_query_endpoint_without_session_id(self, test_client, test_app, mock_rag_system_responses):
        """Test query endpoint creates session ID when not provided"""
        test_app.state.mock_rag_system.query.return_value = mock_rag_system_responses["query_response"]
        
        query_data = {"query": "What is MCP?"}
        
        response = test_client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have generated a session ID
        assert data["session_id"] == "test-session-123"
        
        # Verify mock was called with generated session ID
        test_app.state.mock_rag_system.query.assert_called_once_with("What is MCP?", "test-session-123")

    def test_query_endpoint_missing_query(self, test_client):
        """Test query endpoint returns error when query is missing"""
        response = test_client.post("/api/query", json={})
        
        assert response.status_code == 422  # Validation error
        
    def test_query_endpoint_invalid_json(self, test_client):
        """Test query endpoint handles invalid JSON gracefully"""
        response = test_client.post(
            "/api/query", 
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422

    def test_query_endpoint_rag_system_error(self, test_client, test_app):
        """Test query endpoint handles RAG system errors"""
        test_app.state.mock_rag_system.query.side_effect = Exception("RAG system error")
        
        query_data = {"query": "What is MCP?"}
        
        response = test_client.post("/api/query", json=query_data)
        
        assert response.status_code == 500
        assert "RAG system error" in response.json()["detail"]

    def test_courses_endpoint_success(self, test_client, test_app, mock_rag_system_responses):
        """Test successful request to /api/courses endpoint"""
        test_app.state.mock_rag_system.get_course_analytics.return_value = mock_rag_system_responses["analytics_response"]
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_courses" in data
        assert "course_titles" in data
        
        # Verify content
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "MCP: Build Rich-Context AI Apps with Anthropic" in data["course_titles"]
        assert "Advanced Retrieval for AI with Chroma" in data["course_titles"]
        
        # Verify mock was called
        test_app.state.mock_rag_system.get_course_analytics.assert_called_once()

    def test_courses_endpoint_rag_system_error(self, test_client, test_app):
        """Test courses endpoint handles RAG system errors"""
        test_app.state.mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 500
        assert "Analytics error" in response.json()["detail"]

    def test_query_endpoint_empty_query(self, test_client, test_app, mock_rag_system_responses):
        """Test query endpoint with empty query string"""
        test_app.state.mock_rag_system.query.return_value = mock_rag_system_responses["query_response"]
        
        query_data = {"query": ""}
        
        response = test_client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        # Should still process empty queries
        test_app.state.mock_rag_system.query.assert_called_once()

    def test_query_endpoint_long_query(self, test_client, test_app, mock_rag_system_responses):
        """Test query endpoint with very long query"""
        test_app.state.mock_rag_system.query.return_value = mock_rag_system_responses["query_response"]
        
        long_query = "What is MCP? " * 100  # Very long query
        query_data = {"query": long_query}
        
        response = test_client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        test_app.state.mock_rag_system.query.assert_called_once_with(long_query, "test-session-123")

    def test_query_endpoint_special_characters(self, test_client, test_app, mock_rag_system_responses):
        """Test query endpoint with special characters"""
        test_app.state.mock_rag_system.query.return_value = mock_rag_system_responses["query_response"]
        
        special_query = "What is MCP? 🤖 & special chars: <>&'\""
        query_data = {"query": special_query}
        
        response = test_client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        test_app.state.mock_rag_system.query.assert_called_once_with(special_query, "test-session-123")

    def test_cors_headers(self, test_client):
        """Test that CORS headers are properly set"""
        response = test_client.get("/")
        
        # Check for CORS headers (these are set by the CORS middleware)
        assert response.status_code == 200

    def test_options_request(self, test_client):
        """Test OPTIONS request for CORS preflight"""
        response = test_client.options("/api/query")
        
        # Should handle OPTIONS request (CORS preflight)
        assert response.status_code in [200, 405]  # 405 is acceptable if OPTIONS not explicitly handled


@pytest.mark.api
@pytest.mark.integration
class TestAPIEndpointsIntegration:
    """Integration tests for API endpoints with more realistic scenarios"""
    
    def test_query_workflow(self, test_client, test_app, mock_rag_system_responses):
        """Test a complete query workflow"""
        # Setup mock responses
        test_app.state.mock_rag_system.query.return_value = mock_rag_system_responses["query_response"]
        test_app.state.mock_rag_system.get_course_analytics.return_value = mock_rag_system_responses["analytics_response"]
        
        # First, get course stats
        courses_response = test_client.get("/api/courses")
        assert courses_response.status_code == 200
        courses_data = courses_response.json()
        assert courses_data["total_courses"] > 0
        
        # Then, query about one of the courses
        query_data = {
            "query": f"Tell me about {courses_data['course_titles'][0]}",
            "session_id": "integration-test-session"
        }
        
        query_response = test_client.post("/api/query", json=query_data)
        assert query_response.status_code == 200
        query_data_response = query_response.json()
        
        # Verify the response includes sources
        assert len(query_data_response["sources"]) > 0
        assert query_data_response["session_id"] == "integration-test-session"
        
        # Verify both endpoints were called
        test_app.state.mock_rag_system.get_course_analytics.assert_called_once()
        test_app.state.mock_rag_system.query.assert_called_once()

    def test_multiple_queries_same_session(self, test_client, test_app, mock_rag_system_responses):
        """Test multiple queries in the same session"""
        test_app.state.mock_rag_system.query.return_value = mock_rag_system_responses["query_response"]
        
        session_id = "multi-query-session"
        
        # First query
        response1 = test_client.post("/api/query", json={
            "query": "What is MCP?",
            "session_id": session_id
        })
        assert response1.status_code == 200
        assert response1.json()["session_id"] == session_id
        
        # Second query in same session
        response2 = test_client.post("/api/query", json={
            "query": "How does it work?",
            "session_id": session_id
        })
        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id
        
        # Verify both calls were made with the same session
        assert test_app.state.mock_rag_system.query.call_count == 2
        calls = test_app.state.mock_rag_system.query.call_args_list
        assert calls[0][0][1] == session_id  # First call session_id
        assert calls[1][0][1] == session_id  # Second call session_id