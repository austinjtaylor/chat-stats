"""
Tests for the quarter score service.
"""

from unittest.mock import Mock

import pytest
from services.quarter_score_service import calculate_quarter_scores


class TestQuarterScoreService:
    """Test suite for quarter score calculation functionality."""

    @pytest.fixture
    def mock_stats_system(self):
        """Mock stats system with database."""
        mock_system = Mock()
        mock_system.db = Mock()
        return mock_system

    @pytest.fixture
    def sample_event_data(self):
        """Sample game events data for testing."""
        return [
            # Q1 events
            {
                "event_index": 1,
                "event_type": 1,
                "team": "home",
                "event_time": 0,
            },  # Pull start
            {
                "event_index": 2,
                "event_type": 19,
                "team": "home",
                "event_time": 45,
            },  # Home goal
            {
                "event_index": 3,
                "event_type": 2,
                "team": "away",
                "event_time": 60,
            },  # Pull start
            {
                "event_index": 4,
                "event_type": 15,
                "team": "away",
                "event_time": 120,
            },  # Away goal
            {
                "event_index": 5,
                "event_type": 28,
                "team": "home",
                "event_time": 720,
            },  # End Q1
            # Q2 events
            {
                "event_index": 6,
                "event_type": 1,
                "team": "home",
                "event_time": 0,
            },  # Pull start
            {
                "event_index": 7,
                "event_type": 19,
                "team": "home",
                "event_time": 30,
            },  # Home goal
            {
                "event_index": 8,
                "event_type": 19,
                "team": "home",
                "event_time": 90,
            },  # Home goal
            {
                "event_index": 9,
                "event_type": 15,
                "team": "away",
                "event_time": 150,
            },  # Away goal
            {
                "event_index": 10,
                "event_type": 29,
                "team": "home",
                "event_time": 720,
            },  # Halftime
            # Q3 events
            {
                "event_index": 11,
                "event_type": 2,
                "team": "away",
                "event_time": 0,
            },  # Pull start
            {
                "event_index": 12,
                "event_type": 15,
                "team": "away",
                "event_time": 40,
            },  # Away goal
            {
                "event_index": 13,
                "event_type": 15,
                "team": "away",
                "event_time": 100,
            },  # Away goal
            {
                "event_index": 14,
                "event_type": 15,
                "team": "away",
                "event_time": 200,
            },  # Away goal
            {
                "event_index": 15,
                "event_type": 30,
                "team": "home",
                "event_time": 720,
            },  # End Q3
            # Q4 events
            {
                "event_index": 16,
                "event_type": 1,
                "team": "home",
                "event_time": 0,
            },  # Pull start
            {
                "event_index": 17,
                "event_type": 19,
                "team": "home",
                "event_time": 60,
            },  # Home goal
            {
                "event_index": 18,
                "event_type": 19,
                "team": "home",
                "event_time": 180,
            },  # Home goal
            {
                "event_index": 19,
                "event_type": 31,
                "team": "home",
                "event_time": 720,
            },  # End regulation
        ]

    def test_calculate_quarter_scores_basic(self, mock_stats_system, sample_event_data):
        """Test basic quarter score calculation."""
        mock_stats_system.db.execute_query.return_value = sample_event_data

        result = calculate_quarter_scores(mock_stats_system, "test_game")

        assert len(result) == 4  # Should have 4 quarters
        assert result[0]["quarter"] == 1
        assert result[0]["home_score"] == 1
        assert result[0]["away_score"] == 1
        assert result[1]["quarter"] == 2
        assert result[1]["home_score"] == 2
        assert result[1]["away_score"] == 1
        assert result[2]["quarter"] == 3
        assert result[2]["home_score"] == 0
        assert result[2]["away_score"] == 3
        assert result[3]["quarter"] == 4
        assert result[3]["home_score"] == 2
        assert result[3]["away_score"] == 0

    def test_calculate_quarter_scores_empty_events(self, mock_stats_system):
        """Test handling of empty events."""
        mock_stats_system.db.execute_query.return_value = []

        result = calculate_quarter_scores(mock_stats_system, "test_game")

        assert result == []

    def test_calculate_quarter_scores_incomplete_game(self, mock_stats_system):
        """Test handling of incomplete game (missing quarters)."""
        events = [
            {"event_index": 1, "event_type": 1, "team": "home", "event_time": 0},
            {"event_index": 2, "event_type": 19, "team": "home", "event_time": 45},
            {
                "event_index": 3,
                "event_type": 28,
                "team": "home",
                "event_time": 720,
            },  # End Q1 only
        ]
        mock_stats_system.db.execute_query.return_value = events

        result = calculate_quarter_scores(mock_stats_system, "test_game")

        assert len(result) == 1
        assert result[0]["quarter"] == 1
        assert result[0]["home_score"] == 1
        assert result[0]["away_score"] == 0

    def test_calculate_quarter_scores_overtime(self, mock_stats_system):
        """Test handling of overtime periods."""
        events = [
            # Regular quarters (simplified)
            {"event_index": 1, "event_type": 19, "team": "home", "event_time": 45},
            {"event_index": 2, "event_type": 28, "team": "home", "event_time": 720},
            {"event_index": 3, "event_type": 19, "team": "home", "event_time": 45},
            {"event_index": 4, "event_type": 29, "team": "home", "event_time": 720},
            {"event_index": 5, "event_type": 15, "team": "away", "event_time": 45},
            {"event_index": 6, "event_type": 30, "team": "home", "event_time": 720},
            {"event_index": 7, "event_type": 15, "team": "away", "event_time": 45},
            {"event_index": 8, "event_type": 31, "team": "home", "event_time": 720},
            # Overtime
            {"event_index": 9, "event_type": 19, "team": "home", "event_time": 45},
            {
                "event_index": 10,
                "event_type": 34,
                "team": "home",
                "event_time": 180,
            },  # End OT
        ]
        mock_stats_system.db.execute_query.return_value = events

        result = calculate_quarter_scores(mock_stats_system, "test_game")

        assert len(result) == 5  # 4 quarters + OT
        assert result[4]["quarter"] == 5  # OT is quarter 5
        assert result[4]["home_score"] == 1
        assert result[4]["away_score"] == 0

    def test_calculate_quarter_scores_different_goal_types(self, mock_stats_system):
        """Test handling of different goal event types."""
        events = [
            {
                "event_index": 1,
                "event_type": 19,
                "team": "home",
                "event_time": 45,
            },  # Home goal
            {
                "event_index": 2,
                "event_type": 15,
                "team": "home",
                "event_time": 90,
            },  # Away goal (from home perspective)
            {
                "event_index": 3,
                "event_type": 19,
                "team": "away",
                "event_time": 120,
            },  # Away goal (from away perspective)
            {"event_index": 4, "event_type": 28, "team": "home", "event_time": 720},
        ]
        mock_stats_system.db.execute_query.return_value = events

        result = calculate_quarter_scores(mock_stats_system, "test_game")

        assert result[0]["home_score"] == 1  # One home goal (type 19 from home)
        assert (
            result[0]["away_score"] == 2
        )  # Two away goals (type 15 from home + type 19 from away)

    def test_calculate_quarter_scores_query_structure(self, mock_stats_system):
        """Test that the correct SQL query is executed."""
        mock_stats_system.db.execute_query.return_value = []
        game_id = "2024-REG-01-BOS-MIN"

        calculate_quarter_scores(mock_stats_system, game_id)

        # Verify the query was called with correct parameters
        mock_stats_system.db.execute_query.assert_called_once()
        args = mock_stats_system.db.execute_query.call_args
        assert args[0][1] == {"game_id": game_id}

        # Verify the query contains expected fields
        query = args[0][0]
        assert "event_index" in query
        assert "event_type" in query
        assert "event_time" in query
        assert "team" in query
        assert "FROM game_events" in query
        assert "ORDER BY event_index" in query

    def test_calculate_quarter_scores_with_null_event_time(self, mock_stats_system):
        """Test handling of null event times."""
        events = [
            {"event_index": 1, "event_type": 19, "team": "home", "event_time": None},
            {"event_index": 2, "event_type": 15, "team": "home", "event_time": 90},
            {"event_index": 3, "event_type": 28, "team": "home", "event_time": 720},
        ]
        mock_stats_system.db.execute_query.return_value = events

        result = calculate_quarter_scores(mock_stats_system, "test_game")

        # Should handle None event_time gracefully
        assert result[0]["home_score"] == 1
        assert result[0]["away_score"] == 1
