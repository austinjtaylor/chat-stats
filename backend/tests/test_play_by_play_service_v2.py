"""
Tests for the play-by-play service v2.
"""

from unittest.mock import Mock

import pytest
from services.play_by_play_service_v2 import calculate_play_by_play


class TestPlayByPlayServiceV2:
    """Test suite for play-by-play service v2 functionality."""

    @pytest.fixture
    def mock_stats_system(self):
        """Mock stats system with database."""
        mock_system = Mock()
        mock_system.db = Mock()
        return mock_system

    @pytest.fixture
    def sample_game_info(self):
        """Sample game information."""
        return [
            {
                "home_team_id": "MIN",
                "away_team_id": "BOS",
                "year": 2024,
                "home_city": "Minnesota",
                "home_name": "Wind Chill",
                "away_city": "Boston",
                "away_name": "Glory",
            }
        ]

    @pytest.fixture
    def sample_events(self):
        """Sample game events for testing."""
        return [
            # Pull and goal events
            {
                "event_index": 1,
                "team": "home",
                "event_type": 1,  # Home pulls (D-point for home)
                "event_time": 0,
                "thrower_id": None,
                "receiver_id": None,
                "defender_id": None,
                "puller_id": 101,
                "thrower_x": None,
                "thrower_y": None,
                "receiver_x": None,
                "receiver_y": None,
                "turnover_x": None,
                "turnover_y": None,
                "pull_x": 60,
                "pull_y": 80,
                "pull_ms": 3500,
                "line_players": "[101, 102, 103, 104, 105, 106, 107]",
                "thrower_name": None,
                "thrower_last": None,
                "receiver_name": None,
                "receiver_last": None,
                "defender_name": None,
                "defender_last": None,
                "puller_name": "John Smith",
                "puller_last": "Smith",
                "next_pull_time": 120,
            },
            {
                "event_index": 2,
                "team": "away",
                "event_type": 18,  # Pass
                "event_time": 10,
                "thrower_id": 201,
                "receiver_id": 202,
                "defender_id": None,
                "puller_id": None,
                "thrower_x": 50,
                "thrower_y": 40,
                "receiver_x": 50,
                "receiver_y": 60,
                "turnover_x": None,
                "turnover_y": None,
                "pull_x": None,
                "pull_y": None,
                "pull_ms": None,
                "line_players": None,
                "thrower_name": "Bob Johnson",
                "thrower_last": "Johnson",
                "receiver_name": "Alice Brown",
                "receiver_last": "Brown",
                "defender_name": None,
                "defender_last": None,
                "puller_name": None,
                "puller_last": None,
                "next_pull_time": None,
            },
            {
                "event_index": 3,
                "team": "away",
                "event_type": 19,  # Goal (away scores)
                "event_time": 30,
                "thrower_id": 202,
                "receiver_id": 203,
                "defender_id": None,
                "puller_id": None,
                "thrower_x": 50,
                "thrower_y": 60,
                "receiver_x": 50,
                "receiver_y": 100,
                "turnover_x": None,
                "turnover_y": None,
                "pull_x": None,
                "pull_y": None,
                "pull_ms": None,
                "line_players": None,
                "thrower_name": "Alice Brown",
                "thrower_last": "Brown",
                "receiver_name": "Charlie Davis",
                "receiver_last": "Davis",
                "defender_name": None,
                "defender_last": None,
                "puller_name": None,
                "puller_last": None,
                "next_pull_time": 120,
            },
        ]

    def test_calculate_play_by_play_basic(
        self, mock_stats_system, sample_game_info, sample_events
    ):
        """Test basic play-by-play calculation."""
        mock_stats_system.db.execute_query.side_effect = [
            sample_game_info,  # Game info query
            sample_events,  # Events query
            [{"last_name": "Smith"}],  # Line players query
        ]

        result = calculate_play_by_play(mock_stats_system, "test_game")

        assert len(result) > 0
        assert result[0]["point_number"] == 1
        assert result[0]["quarter"] == 1
        assert result[0]["pulling_team"] == "home"
        assert result[0]["receiving_team"] == "away"
        assert result[0]["scoring_team"] == "away"

    def test_calculate_play_by_play_no_game(self, mock_stats_system):
        """Test handling when game doesn't exist."""
        mock_stats_system.db.execute_query.return_value = []

        result = calculate_play_by_play(mock_stats_system, "nonexistent_game")

        assert result == []

    def test_calculate_play_by_play_no_events(
        self, mock_stats_system, sample_game_info
    ):
        """Test handling when game has no events."""
        mock_stats_system.db.execute_query.side_effect = [
            sample_game_info,
            [],  # No events
        ]

        result = calculate_play_by_play(mock_stats_system, "test_game")

        assert result == []

    def test_calculate_play_by_play_turnovers(
        self, mock_stats_system, sample_game_info
    ):
        """Test handling of turnover events."""
        events = [
            {
                "event_index": 1,
                "team": "home",
                "event_type": 1,
                "event_time": 0,
                "thrower_id": None,
                "receiver_id": None,
                "defender_id": None,
                "puller_id": 101,
                "thrower_x": None,
                "thrower_y": None,
                "receiver_x": None,
                "receiver_y": None,
                "turnover_x": None,
                "turnover_y": None,
                "pull_x": None,
                "pull_y": None,
                "pull_ms": None,
                "line_players": None,
                "thrower_name": None,
                "thrower_last": None,
                "receiver_name": None,
                "receiver_last": None,
                "defender_name": None,
                "defender_last": None,
                "puller_name": "Smith",
                "puller_last": "Smith",
                "next_pull_time": None,
            },
            {
                "event_index": 2,
                "team": "away",
                "event_type": 22,  # Throwaway
                "event_time": 15,
                "thrower_id": 201,
                "receiver_id": None,
                "defender_id": None,
                "puller_id": None,
                "thrower_x": 50,
                "thrower_y": 50,
                "receiver_x": None,
                "receiver_y": None,
                "turnover_x": 50,
                "turnover_y": 70,
                "pull_x": None,
                "pull_y": None,
                "pull_ms": None,
                "line_players": None,
                "thrower_name": "Johnson",
                "thrower_last": "Johnson",
                "receiver_name": None,
                "receiver_last": None,
                "defender_name": None,
                "defender_last": None,
                "puller_name": None,
                "puller_last": None,
                "next_pull_time": None,
            },
            {
                "event_index": 3,
                "team": "home",
                "event_type": 11,  # Block
                "event_time": 25,
                "thrower_id": None,
                "receiver_id": None,
                "defender_id": 102,
                "puller_id": None,
                "thrower_x": None,
                "thrower_y": None,
                "receiver_x": None,
                "receiver_y": None,
                "turnover_x": 50,
                "turnover_y": 40,
                "pull_x": None,
                "pull_y": None,
                "pull_ms": None,
                "line_players": None,
                "thrower_name": None,
                "thrower_last": None,
                "receiver_name": None,
                "receiver_last": None,
                "defender_name": "Williams",
                "defender_last": "Williams",
                "puller_name": None,
                "puller_last": None,
                "next_pull_time": None,
            },
        ]

        mock_stats_system.db.execute_query.side_effect = [sample_game_info, events]

        result = calculate_play_by_play(mock_stats_system, "test_game")

        # Check that turnovers are properly processed in events
        assert len(result) > 0
        point_events = result[0]["events"]

        # Should have throwaway and block events
        throwaway_events = [e for e in point_events if e["type"] == "throwaway"]
        block_events = [e for e in point_events if e["type"] == "block"]

        assert len(throwaway_events) > 0 or len(block_events) > 0

    def test_calculate_play_by_play_quarter_transitions(
        self, mock_stats_system, sample_game_info
    ):
        """Test handling of quarter end events."""
        events = [
            {
                "event_index": 1,
                "team": "home",
                "event_type": 1,
                "event_time": 0,
                "thrower_id": None,
                "receiver_id": None,
                "defender_id": None,
                "puller_id": None,
                "thrower_x": None,
                "thrower_y": None,
                "receiver_x": None,
                "receiver_y": None,
                "turnover_x": None,
                "turnover_y": None,
                "pull_x": None,
                "pull_y": None,
                "pull_ms": None,
                "line_players": None,
                "thrower_name": None,
                "thrower_last": None,
                "receiver_name": None,
                "receiver_last": None,
                "defender_name": None,
                "defender_last": None,
                "puller_name": None,
                "puller_last": None,
                "next_pull_time": None,
            },
            {
                "event_index": 2,
                "team": "home",
                "event_type": 28,  # End of Q1
                "event_time": 720,
                "thrower_id": None,
                "receiver_id": None,
                "defender_id": None,
                "puller_id": None,
                "thrower_x": None,
                "thrower_y": None,
                "receiver_x": None,
                "receiver_y": None,
                "turnover_x": None,
                "turnover_y": None,
                "pull_x": None,
                "pull_y": None,
                "pull_ms": None,
                "line_players": None,
                "thrower_name": None,
                "thrower_last": None,
                "receiver_name": None,
                "receiver_last": None,
                "defender_name": None,
                "defender_last": None,
                "puller_name": None,
                "puller_last": None,
                "next_pull_time": None,
            },
            {
                "event_index": 3,
                "team": "home",
                "event_type": 1,
                "event_time": 0,  # Q2 starts
                "thrower_id": None,
                "receiver_id": None,
                "defender_id": None,
                "puller_id": None,
                "thrower_x": None,
                "thrower_y": None,
                "receiver_x": None,
                "receiver_y": None,
                "turnover_x": None,
                "turnover_y": None,
                "pull_x": None,
                "pull_y": None,
                "pull_ms": None,
                "line_players": None,
                "thrower_name": None,
                "thrower_last": None,
                "receiver_name": None,
                "receiver_last": None,
                "defender_name": None,
                "defender_last": None,
                "puller_name": None,
                "puller_last": None,
                "next_pull_time": None,
            },
        ]

        mock_stats_system.db.execute_query.side_effect = [sample_game_info, events]

        result = calculate_play_by_play(mock_stats_system, "test_game")

        # Should have points in different quarters
        quarters = [p["quarter"] for p in result]
        assert 1 in quarters
        assert 2 in quarters

    def test_calculate_play_by_play_duration_calculation(
        self, mock_stats_system, sample_game_info, sample_events
    ):
        """Test point duration calculation."""
        mock_stats_system.db.execute_query.side_effect = [
            sample_game_info,
            sample_events,
            [{"last_name": "Smith"}],
        ]

        result = calculate_play_by_play(mock_stats_system, "test_game")

        assert len(result) > 0
        # Check that duration is calculated
        assert "duration" in result[0]
        assert "duration_seconds" in result[0]
        assert "time" in result[0]  # Time remaining in quarter

    def test_calculate_play_by_play_pass_distance_calculation(
        self, mock_stats_system, sample_game_info, sample_events
    ):
        """Test pass distance and direction calculation."""
        mock_stats_system.db.execute_query.side_effect = [
            sample_game_info,
            sample_events,
            [{"last_name": "Smith"}],
        ]

        result = calculate_play_by_play(mock_stats_system, "test_game")

        # Find pass events
        for point in result:
            for event in point.get("events", []):
                if event["type"] == "pass":
                    # Should have distance in description
                    assert "y" in event["description"]  # Distance in yards
                    # May have direction if coordinates available
                    if "direction" in event:
                        assert isinstance(event["direction"], (int, float))
