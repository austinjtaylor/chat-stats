"""
Tests for the box score service.
"""

from unittest.mock import Mock

import pytest
from services.box_score_service import calculate_team_stats


class TestBoxScoreService:
    """Test suite for box score service functionality."""

    @pytest.fixture
    def mock_stats_system(self):
        """Mock stats system with database."""
        mock_system = Mock()
        mock_system.db = Mock()
        return mock_system

    @pytest.fixture
    def sample_game_data(self):
        """Sample game data for testing."""
        return {
            "game_id": "2024-REG-01-BOS-MIN",
            "home_team_id": "MIN",
            "away_team_id": "BOS",
            "home_score": 20,
            "away_score": 25,
        }

    @pytest.fixture
    def sample_player_stats(self):
        """Sample player stats data."""
        return [
            {
                "team_id": "BOS",
                "full_name": "John Doe",
                "o_possessions": 10,
                "o_scores": 8,
                "d_possessions": 5,
                "d_scores": 2,
                "goals": 3,
                "assists": 5,
                "blocks": 2,
                "turnovers": 1,
                "plus_minus": 7,
            },
            {
                "team_id": "BOS",
                "full_name": "Jane Smith",
                "o_possessions": 8,
                "o_scores": 6,
                "d_possessions": 7,
                "d_scores": 3,
                "goals": 2,
                "assists": 4,
                "blocks": 3,
                "turnovers": 2,
                "plus_minus": 5,
            },
            {
                "team_id": "MIN",
                "full_name": "Bob Johnson",
                "o_possessions": 12,
                "o_scores": 9,
                "d_possessions": 4,
                "d_scores": 1,
                "goals": 4,
                "assists": 3,
                "blocks": 1,
                "turnovers": 3,
                "plus_minus": 3,
            },
        ]

    def test_calculate_team_stats_basic(self, mock_stats_system, sample_game_data):
        """Test basic team stats calculation."""
        # Setup mock database responses
        mock_stats_system.db.execute_query.return_value = [
            {
                "team_id": "BOS",
                "o_possessions": 18,
                "o_scores": 14,
                "d_possessions": 12,
                "d_scores": 5,
                "goals": 5,
                "assists": 9,
                "blocks": 5,
                "turnovers": 3,
            },
            {
                "team_id": "MIN",
                "o_possessions": 12,
                "o_scores": 9,
                "d_possessions": 18,
                "d_scores": 4,
                "goals": 4,
                "assists": 3,
                "blocks": 1,
                "turnovers": 3,
            },
        ]

        result = calculate_team_stats(mock_stats_system, sample_game_data["game_id"])

        assert "home_team" in result
        assert "away_team" in result
        assert result["home_team"]["o_possessions"] == 12
        assert result["away_team"]["o_possessions"] == 18

    def test_calculate_team_stats_with_percentages(self, mock_stats_system):
        """Test team stats calculation with percentage calculations."""
        mock_stats_system.db.execute_query.return_value = [
            {
                "team_id": "BOS",
                "o_possessions": 20,
                "o_scores": 15,
                "d_possessions": 10,
                "d_scores": 3,
                "goals": 15,
                "assists": 12,
                "blocks": 4,
                "turnovers": 5,
            }
        ]

        result = calculate_team_stats(mock_stats_system, "test_game")

        # Check O-line conversion percentage (15/20 = 75%)
        assert result["away_team"]["o_line_conversion"] == 75.0
        # Check D-line conversion percentage (3/10 = 30%)
        assert result["away_team"]["d_line_conversion"] == 30.0

    def test_calculate_team_stats_empty_result(self, mock_stats_system):
        """Test handling of empty database results."""
        mock_stats_system.db.execute_query.return_value = []

        result = calculate_team_stats(mock_stats_system, "nonexistent_game")

        assert result["home_team"]["o_possessions"] == 0
        assert result["away_team"]["o_possessions"] == 0

    def test_calculate_team_stats_with_zero_possessions(self, mock_stats_system):
        """Test handling of zero possessions to avoid division by zero."""
        mock_stats_system.db.execute_query.return_value = [
            {
                "team_id": "BOS",
                "o_possessions": 0,
                "o_scores": 0,
                "d_possessions": 0,
                "d_scores": 0,
                "goals": 0,
                "assists": 0,
                "blocks": 0,
                "turnovers": 0,
            }
        ]

        result = calculate_team_stats(mock_stats_system, "test_game")

        # Should return 0 instead of division by zero error
        assert result["away_team"]["o_line_conversion"] == 0
        assert result["away_team"]["d_line_conversion"] == 0

    def test_calculate_team_stats_with_null_values(self, mock_stats_system):
        """Test handling of null values in database results."""
        mock_stats_system.db.execute_query.return_value = [
            {
                "team_id": "BOS",
                "o_possessions": None,
                "o_scores": None,
                "d_possessions": 10,
                "d_scores": 5,
                "goals": 10,
                "assists": None,
                "blocks": 3,
                "turnovers": None,
            }
        ]

        result = calculate_team_stats(mock_stats_system, "test_game")

        # Should handle None values gracefully
        assert result["away_team"]["o_possessions"] == 0
        assert result["away_team"]["o_scores"] == 0
        assert result["away_team"]["assists"] == 0
        assert result["away_team"]["turnovers"] == 0

    def test_calculate_team_stats_query_structure(self, mock_stats_system):
        """Test that the correct SQL query is executed."""
        mock_stats_system.db.execute_query.return_value = []
        game_id = "2024-REG-01-BOS-MIN"

        calculate_team_stats(mock_stats_system, game_id)

        # Verify the query was called with correct parameters
        mock_stats_system.db.execute_query.assert_called_once()
        args = mock_stats_system.db.execute_query.call_args
        assert args[0][1] == {"game_id": game_id}

        # Verify the query contains expected fields
        query = args[0][0]
        assert "SUM(o_possessions)" in query
        assert "SUM(o_scores)" in query
        assert "SUM(d_possessions)" in query
        assert "SUM(d_scores)" in query
        assert "GROUP BY team_id" in query
