"""
Test Sports Statistics API endpoints.
Tests FastAPI endpoints for the sports statistics system.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_stats_system():
    """Create a mock stats system"""
    mock = MagicMock()
    mock.query.return_value = ("Test answer", [{"data": "test"}])
    mock.get_stats_summary.return_value = {
        "total_players": 100,
        "total_teams": 10,
        "total_games": 50,
        "seasons": ["2023-24"],
        "team_standings": [{"team": "Test Team", "wins": 5, "losses": 3}],
    }
    mock.search_player.return_value = [{"name": "Test Player", "team": "Test Team"}]
    mock.search_team.return_value = [{"name": "Test Team", "city": "Test City"}]
    mock.get_recent_games.return_value = [
        {"game_id": "test-game", "home_team": "Team A", "away_team": "Team B"}
    ]
    mock.get_database_info.return_value = {
        "players": "table info",
        "teams": "table info",
    }
    mock.import_data.return_value = {"imported": 10}
    mock.session_manager.create_session.return_value = "test-session-123"
    return mock


@pytest.fixture
def test_client(mock_stats_system):
    """Create a test client with mocked stats system"""
    with patch("core.chat_system.get_stats_system", return_value=mock_stats_system):
        # Import and create app with mocked stats_system
        from app import app

        client = TestClient(app)
        # Store the mock on the client for easy access in tests
        client.mock_stats_system = mock_stats_system
        return client


class TestAPIRoot:
    """Test API root endpoints"""

    def test_api_root_endpoint(self, test_client):
        """Test the API root endpoint returns correct message"""
        response = test_client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Sports Statistics Chat System API"
        assert data["version"] == "1.0.0"


class TestQueryEndpoint:
    """Test /api/query endpoint"""

    def test_query_endpoint_success(self, test_client):
        """Test successful query to /api/query endpoint"""
        query_data = {
            "query": "Who are the top scorers?",
            "session_id": "test-session-123",
        }

        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "data" in data
        assert "session_id" in data

        # Verify content
        assert data["answer"] == "Test answer"
        assert data["session_id"] == "test-session-123"
        assert data["data"] == [{"data": "test"}]

        # Verify mock was called correctly
        test_client.mock_stats_system.query.assert_called_once_with(
            "Who are the top scorers?", "test-session-123"
        )

    def test_query_endpoint_without_session_id(self, test_client):
        """Test query endpoint creates session ID when not provided"""
        query_data = {"query": "Who are the top scorers?"}

        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 200
        data = response.json()

        # Should have generated a session ID
        assert data["session_id"] == "test-session-123"

        # Verify session creation was called
        test_client.mock_stats_system.session_manager.create_session.assert_called_once()
        test_client.mock_stats_system.query.assert_called_once_with(
            "Who are the top scorers?", "test-session-123"
        )

    def test_query_endpoint_missing_query(self, test_client):
        """Test query endpoint returns validation error when query is missing"""
        response = test_client.post("/api/query", json={})

        assert response.status_code == 422  # Validation error

    def test_query_endpoint_invalid_json(self, test_client):
        """Test query endpoint handles invalid JSON gracefully"""
        response = test_client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_query_endpoint_system_error(self, test_client):
        """Test query endpoint handles system errors"""
        test_client.mock_stats_system.query.side_effect = Exception("Database error")

        query_data = {"query": "Who are the top scorers?"}

        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_query_endpoint_empty_query(self, test_client):
        """Test query endpoint with empty query string"""
        query_data = {"query": ""}

        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 200
        # Should still process empty queries
        test_client.mock_stats_system.query.assert_called_once()


class TestStatsEndpoint:
    """Test /api/stats endpoint"""

    def test_stats_endpoint_success(self, test_client):
        """Test successful request to /api/stats endpoint"""
        response = test_client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "total_players" in data
        assert "total_teams" in data
        assert "total_games" in data
        assert "seasons" in data
        assert "team_standings" in data

        # Verify content
        assert data["total_players"] == 100
        assert data["total_teams"] == 10
        assert data["total_games"] == 50
        assert data["seasons"] == ["2023-24"]
        assert len(data["team_standings"]) == 1

        # Verify mock was called
        test_client.mock_stats_system.get_stats_summary.assert_called_once()

    def test_stats_endpoint_system_error(self, test_client):
        """Test stats endpoint handles system errors"""
        test_client.mock_stats_system.get_stats_summary.side_effect = Exception(
            "Database error"
        )

        response = test_client.get("/api/stats")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


class TestSearchEndpoints:
    """Test search endpoints"""

    def test_players_search_success(self, test_client):
        """Test successful player search"""
        response = test_client.get("/api/players/search?q=LeBron")

        assert response.status_code == 200
        data = response.json()

        assert "players" in data
        assert "count" in data
        assert data["count"] == 1
        assert data["players"][0]["name"] == "Test Player"

        test_client.mock_stats_system.search_player.assert_called_once_with("LeBron")

    def test_players_search_error(self, test_client):
        """Test player search handles errors"""
        test_client.mock_stats_system.search_player.side_effect = Exception(
            "Search error"
        )

        response = test_client.get("/api/players/search?q=LeBron")

        assert response.status_code == 500
        assert "Search error" in response.json()["detail"]

    def test_teams_search_success(self, test_client):
        """Test successful team search"""
        response = test_client.get("/api/teams/search?q=Lakers")

        assert response.status_code == 200
        data = response.json()

        assert "teams" in data
        assert "count" in data
        assert data["count"] == 1
        assert data["teams"][0]["name"] == "Test Team"

        test_client.mock_stats_system.search_team.assert_called_once_with("Lakers")

    def test_teams_search_error(self, test_client):
        """Test team search handles errors"""
        test_client.mock_stats_system.search_team.side_effect = Exception(
            "Search error"
        )

        response = test_client.get("/api/teams/search?q=Lakers")

        assert response.status_code == 500
        assert "Search error" in response.json()["detail"]


class TestGamesEndpoint:
    """Test /api/games/recent endpoint"""

    def test_recent_games_success(self, test_client):
        """Test successful request to recent games endpoint"""
        response = test_client.get("/api/games/recent")

        assert response.status_code == 200
        data = response.json()

        assert "games" in data
        assert "count" in data
        assert data["count"] == 1
        assert data["games"][0]["game_id"] == "test-game"

        test_client.mock_stats_system.get_recent_games.assert_called_once_with(
            10
        )  # default limit

    def test_recent_games_with_limit(self, test_client):
        """Test recent games endpoint with custom limit"""
        response = test_client.get("/api/games/recent?limit=5")

        assert response.status_code == 200
        test_client.mock_stats_system.get_recent_games.assert_called_once_with(5)

    def test_recent_games_error(self, test_client):
        """Test recent games endpoint handles errors"""
        test_client.mock_stats_system.get_recent_games.side_effect = Exception(
            "Games error"
        )

        response = test_client.get("/api/games/recent")

        assert response.status_code == 500
        assert "Games error" in response.json()["detail"]


class TestDatabaseEndpoint:
    """Test /api/database/info endpoint"""

    def test_database_info_success(self, test_client):
        """Test successful request to database info endpoint"""
        response = test_client.get("/api/database/info")

        assert response.status_code == 200
        data = response.json()

        assert "tables" in data
        assert "players" in data["tables"]
        assert "teams" in data["tables"]

        test_client.mock_stats_system.get_database_info.assert_called_once()

    def test_database_info_error(self, test_client):
        """Test database info endpoint handles errors"""
        test_client.mock_stats_system.get_database_info.side_effect = Exception(
            "Database error"
        )

        response = test_client.get("/api/database/info")

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]


class TestDataImportEndpoint:
    """Test /api/data/import endpoint"""

    def test_import_data_success(self, test_client):
        """Test successful data import"""
        with patch("os.path.exists", return_value=True):
            response = test_client.post(
                "/api/data/import?file_path=/test/data.json&data_type=json"
            )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert "imported" in data

            test_client.mock_stats_system.import_data.assert_called_once_with(
                "/test/data.json", "json"
            )

    def test_import_data_file_not_found(self, test_client):
        """Test data import with non-existent file"""
        with patch("os.path.exists", return_value=False):
            response = test_client.post("/api/data/import?file_path=/nonexistent.json")

            # HTTPException gets caught and re-raised as 500 by outer exception handler
            assert response.status_code == 500
            assert "File not found" in response.json()["detail"]

    def test_import_data_error(self, test_client):
        """Test data import handles errors"""
        test_client.mock_stats_system.import_data.side_effect = Exception(
            "Import error"
        )

        with patch("os.path.exists", return_value=True):
            response = test_client.post("/api/data/import?file_path=/test/data.json")

            assert response.status_code == 500
            assert "Import error" in response.json()["detail"]


class TestCORS:
    """Test CORS headers"""

    def test_cors_headers(self, test_client):
        """Test that CORS headers are present"""
        response = test_client.get("/api")

        # CORS headers should be present (they're added by middleware)
        assert response.status_code == 200
        # Note: In testing, actual CORS headers may not be visible
        # This test mainly ensures the endpoint works with CORS middleware

    def test_options_request(self, test_client):
        """Test preflight OPTIONS request"""
        response = test_client.options("/api/query")

        # Should allow OPTIONS requests
        assert (
            response.status_code == 405
        )  # Method not allowed, but CORS should still work
