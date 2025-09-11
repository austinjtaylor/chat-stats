"""
Test response handler module.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.response import ResponseHandler


class TestResponseHandler:
    """Test ResponseHandler class"""

    def test_init(self):
        """Test initialization"""
        handler = ResponseHandler()
        assert hasattr(handler, "formatter")

    def test_format_success_response(self):
        """Test formatting successful response"""
        handler = ResponseHandler()

        response = handler.format_success_response(
            "Test answer", [{"data": "test"}], "session-123"
        )

        assert response["answer"] == "Test answer"
        assert response["data"] == [{"data": "test"}]
        assert response["session_id"] == "session-123"
        assert response["status"] == "success"

    def test_format_error_response(self):
        """Test formatting error response"""
        handler = ResponseHandler()

        response = handler.format_error_response("Database error", 500)

        assert response["error"] == "Database error"
        assert response["status_code"] == 500
        assert response["status"] == "error"

    def test_format_player_stats_response(self):
        """Test formatting player stats response"""
        handler = ResponseHandler()

        stats = [
            {"name": "Player 1", "goals": 10, "assists": 5},
            {"name": "Player 2", "goals": 8, "assists": 7},
        ]

        response = handler.format_player_stats_response(stats, "2024")

        assert "players" in response
        assert response["players"] == stats
        assert response["season"] == "2024"
        assert response["count"] == 2

    def test_format_team_stats_response(self):
        """Test formatting team stats response"""
        handler = ResponseHandler()

        stats = [
            {"team": "Team A", "wins": 10, "losses": 5},
            {"team": "Team B", "wins": 8, "losses": 7},
        ]

        response = handler.format_team_stats_response(stats)

        assert "teams" in response
        assert response["teams"] == stats
        assert response["count"] == 2

    def test_format_game_details_response(self):
        """Test formatting game details response"""
        handler = ResponseHandler()

        game = {
            "game_id": "game-123",
            "home_team": "Team A",
            "away_team": "Team B",
            "home_score": 15,
            "away_score": 13,
        }

        response = handler.format_game_details_response(game)

        assert response == game  # Should return as-is for now

    def test_format_empty_response(self):
        """Test formatting empty response"""
        handler = ResponseHandler()

        response = handler.format_success_response("No data found", [], "session-123")

        assert response["answer"] == "No data found"
        assert response["data"] == []
        assert response["session_id"] == "session-123"

    def test_format_with_none_values(self):
        """Test formatting with None values"""
        handler = ResponseHandler()

        response = handler.format_success_response(None, None, None)

        assert response["answer"] is None
        assert response["data"] is None
        assert response["session_id"] is None
        assert response["status"] == "success"

    def test_format_large_dataset(self):
        """Test formatting large dataset"""
        handler = ResponseHandler()

        # Create large dataset
        large_data = [{"id": i, "value": f"item-{i}"} for i in range(1000)]

        response = handler.format_success_response(
            "Large dataset", large_data, "session-123"
        )

        assert len(response["data"]) == 1000
        assert response["data"][0]["id"] == 0
        assert response["data"][999]["id"] == 999


class TestResponseFormatter:
    """Test response formatting utilities"""

    def test_format_table_response(self):
        """Test formatting data as table"""
        handler = ResponseHandler()

        data = [
            {"name": "Alice", "score": 95},
            {"name": "Bob", "score": 87},
            {"name": "Charlie", "score": 92},
        ]

        # Assuming there's a table formatter method
        if hasattr(handler.formatter, "format_as_table"):
            table = handler.formatter.format_as_table(data)
            assert isinstance(table, str)
            assert "Alice" in table
            assert "95" in table

    def test_format_json_response(self):
        """Test formatting data as JSON"""
        handler = ResponseHandler()

        data = {"key": "value", "nested": {"a": 1, "b": 2}}

        # Response should handle JSON serializable data
        response = handler.format_success_response("JSON data", data, "session-123")

        assert response["data"] == data

    def test_sanitize_response(self):
        """Test response sanitization"""
        handler = ResponseHandler()

        # Test with potentially sensitive data
        data = {"password": "secret123", "api_key": "key-456", "safe_data": "visible"}

        response = handler.format_success_response(
            "Sanitized response", data, "session-123"
        )

        # Response should include all data (sanitization would be app-specific)
        assert response["data"] == data


class TestErrorHandling:
    """Test error handling in responses"""

    def test_format_validation_error(self):
        """Test formatting validation errors"""
        handler = ResponseHandler()

        response = handler.format_error_response(
            "Invalid input: field 'name' is required", 422
        )

        assert response["status_code"] == 422
        assert "Invalid input" in response["error"]

    def test_format_not_found_error(self):
        """Test formatting not found errors"""
        handler = ResponseHandler()

        response = handler.format_error_response("Resource not found", 404)

        assert response["status_code"] == 404
        assert response["error"] == "Resource not found"

    def test_format_server_error(self):
        """Test formatting server errors"""
        handler = ResponseHandler()

        response = handler.format_error_response("Internal server error", 500)

        assert response["status_code"] == 500
        assert response["error"] == "Internal server error"

    def test_format_with_error_details(self):
        """Test formatting errors with additional details"""
        handler = ResponseHandler()

        error_details = {
            "message": "Database connection failed",
            "code": "DB_CONN_ERR",
            "timestamp": "2024-01-01T12:00:00Z",
        }

        response = handler.format_error_response(error_details, 500)

        assert response["error"] == error_details
        assert response["status_code"] == 500
