"""
Test API route creation functions.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.routes import create_basic_routes


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
    mock.db = MagicMock()
    return mock


@pytest.fixture
def test_app(mock_stats_system):
    """Create a test FastAPI app with mocked routes"""
    app = FastAPI()
    router, _ = create_basic_routes(mock_stats_system)
    app.include_router(router)
    return app, mock_stats_system


@pytest.fixture
def test_client(test_app):
    """Create a test client"""
    app, mock_stats_system = test_app
    client = TestClient(app)
    client.mock_stats_system = mock_stats_system
    return client


class TestBasicRoutes:
    """Test basic API routes"""

    def test_api_root(self, test_client):
        """Test API root endpoint"""
        response = test_client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Sports Statistics Chat System API"
        assert data["version"] == "1.0.0"

    def test_query_endpoint(self, test_client):
        """Test query endpoint with session"""
        query_data = {
            "query": "Who are the top scorers?",
            "session_id": "test-session-123",
        }

        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Test answer"
        assert data["session_id"] == "test-session-123"
        assert data["data"] == [{"data": "test"}]

        test_client.mock_stats_system.query.assert_called_once_with(
            "Who are the top scorers?", "test-session-123"
        )

    def test_query_without_session(self, test_client):
        """Test query creates new session"""
        query_data = {"query": "Who are the top scorers?"}

        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"

        test_client.mock_stats_system.session_manager.create_session.assert_called_once()

    def test_stats_summary(self, test_client):
        """Test stats summary endpoint"""
        response = test_client.get("/api/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_players"] == 100
        assert data["total_teams"] == 10
        assert data["total_games"] == 50
        assert data["seasons"] == ["2023-24"]

        test_client.mock_stats_system.get_stats_summary.assert_called_once()

    def test_player_search(self, test_client):
        """Test player search endpoint"""
        response = test_client.get("/api/players/search?q=LeBron")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["players"][0]["name"] == "Test Player"

        test_client.mock_stats_system.search_player.assert_called_once_with("LeBron")

    def test_team_search(self, test_client):
        """Test team search endpoint"""
        response = test_client.get("/api/teams/search?q=Lakers")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["teams"][0]["name"] == "Test Team"

        test_client.mock_stats_system.search_team.assert_called_once_with("Lakers")

    def test_recent_games(self, test_client):
        """Test recent games endpoint"""
        response = test_client.get("/api/games/recent")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["games"][0]["game_id"] == "test-game"

        test_client.mock_stats_system.get_recent_games.assert_called_once_with(10)

    def test_recent_games_with_limit(self, test_client):
        """Test recent games with custom limit"""
        response = test_client.get("/api/games/recent?limit=5")

        assert response.status_code == 200
        test_client.mock_stats_system.get_recent_games.assert_called_once_with(5)

    def test_database_info(self, test_client):
        """Test database info endpoint"""
        response = test_client.get("/api/database/info")

        assert response.status_code == 200
        data = response.json()
        assert "tables" in data
        assert "players" in data["tables"]

        test_client.mock_stats_system.get_database_info.assert_called_once()

    def test_data_import(self, test_client):
        """Test data import endpoint"""
        with patch("os.path.exists", return_value=True):
            response = test_client.post(
                "/api/data/import?file_path=/test/data.json&data_type=json"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

            test_client.mock_stats_system.import_data.assert_called_once_with(
                "/test/data.json", "json"
            )

    def test_cache_stats(self, test_client):
        """Test cache stats endpoint"""
        response = test_client.get("/api/cache/stats")

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "default_ttl" in data

    def test_cache_clear(self, test_client):
        """Test cache clear endpoint"""
        response = test_client.post("/api/cache/clear")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestErrorHandling:
    """Test error handling in routes"""

    def test_query_error(self, test_client):
        """Test query endpoint error handling"""
        test_client.mock_stats_system.query.side_effect = Exception("Database error")

        response = test_client.post(
            "/api/query", json={"query": "test", "session_id": "test"}
        )

        assert response.status_code == 500
        assert "Database error" in response.json()["detail"]

    def test_stats_error(self, test_client):
        """Test stats endpoint error handling"""
        test_client.mock_stats_system.get_stats_summary.side_effect = Exception(
            "Stats error"
        )

        response = test_client.get("/api/stats")

        assert response.status_code == 500
        assert "Stats error" in response.json()["detail"]

    def test_player_search_error(self, test_client):
        """Test player search error handling"""
        test_client.mock_stats_system.search_player.side_effect = Exception(
            "Search error"
        )

        response = test_client.get("/api/players/search?q=test")

        assert response.status_code == 500
        assert "Search error" in response.json()["detail"]

    def test_import_file_not_found(self, test_client):
        """Test import with non-existent file"""
        with patch("os.path.exists", return_value=False):
            response = test_client.post("/api/data/import?file_path=/not/found.json")

            assert response.status_code == 500
            assert "File not found" in response.json()["detail"]
