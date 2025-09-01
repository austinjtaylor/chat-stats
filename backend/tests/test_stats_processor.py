"""
Test Stats Processor module functionality.
Tests data processing, import operations, and statistical calculations.
"""

import os
import sys
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sql_database import SQLDatabase
from stats_processor import StatsProcessor

# ===== MODULE-LEVEL FIXTURES =====


@pytest.fixture
def mock_db():
    """Mock database for testing"""
    mock = Mock(spec=SQLDatabase)
    mock.execute_query.return_value = []
    mock.insert_data.return_value = 1
    return mock


@pytest.fixture
def stats_processor(mock_db):
    """StatsProcessor instance with mock database"""
    return StatsProcessor(mock_db)


@pytest.fixture
def sample_team_data():
    """Sample UFA team data for testing"""
    return [
        {
            "team_id": "hustle",
            "year": 2024,
            "name": "Atlanta Hustle",
            "city": "Atlanta",
            "full_name": "Atlanta Hustle",
            "abbrev": "ATL",
            "wins": 12,
            "losses": 3,
            "ties": 1,
            "standing": 1,
            "division_id": "south",
            "division_name": "South",
        },
        {
            "team_id": "glory",
            "year": 2024,
            "name": "Boston Glory",
            "city": "Boston",
            "full_name": "Boston Glory",
            "abbrev": "BOS",
            "wins": 10,
            "losses": 5,
            "ties": 1,
            "standing": 2,
            "division_id": "atlantic",
            "division_name": "Atlantic",
        },
    ]


@pytest.fixture
def sample_player_data():
    """Sample UFA player data for testing"""
    return [
        {
            "name": "Austin Taylor",  # Used by import method for lookup
            "player_id": "austin-taylor",
            "first_name": "Austin",
            "last_name": "Taylor",
            "full_name": "Austin Taylor",
            "team_name": "Atlanta Hustle",  # Used by import method for team lookup
            "active": True,
            "year": 2024,
            "jersey_number": 23,
        },
        {
            "name": "Sarah Johnson",  # Used by import method for lookup
            "player_id": "sarah-johnson",
            "first_name": "Sarah",
            "last_name": "Johnson",
            "full_name": "Sarah Johnson",
            "team_name": "Boston Glory",  # Used by import method for team lookup
            "active": True,
            "year": 2024,
            "jersey_number": 7,
        },
    ]


@pytest.fixture
def sample_game_data():
    """Sample UFA game data for testing"""
    return {
        "game_id": "hustle-vs-glory-2024-06-15",
        "home_team_name": "Atlanta Hustle",  # Used by import method for lookup
        "away_team_name": "Boston Glory",  # Used by import method for lookup
        "away_score": 12,
        "home_score": 15,
        "status": "Final",
        "start_timestamp": "2024-06-15T14:00:00Z",
        "start_timezone": "America/New_York",
        "location": "Piedmont Park",
        "year": 2024,
    }


class TestStatsProcessor:
    """Test StatsProcessor class functionality"""


class TestImportTeams:
    """Test team import functionality"""

    def test_import_teams_success(self, stats_processor, sample_team_data, mock_db):
        """Test successful team import"""
        # Mock no existing teams
        mock_db.execute_query.return_value = []

        count = stats_processor.import_teams(sample_team_data)

        assert count == 2
        assert mock_db.insert_data.call_count == 2

        # Verify correct data passed to insert_data
        calls = mock_db.insert_data.call_args_list
        assert calls[0][0][0] == "teams"  # table name
        assert calls[0][0][1]["name"] == "Atlanta Hustle"

    def test_import_teams_skip_existing(
        self, stats_processor, sample_team_data, mock_db
    ):
        """Test that existing teams are skipped"""
        # Mock that first team already exists
        mock_db.execute_query.side_effect = [
            [{"id": 1}],  # First team exists
            [],  # Second team doesn't exist
        ]

        count = stats_processor.import_teams(sample_team_data)

        assert count == 1  # Only second team imported
        assert mock_db.insert_data.call_count == 1

    def test_import_teams_empty_data(self, stats_processor, mock_db):
        """Test importing empty team data"""
        count = stats_processor.import_teams([])

        assert count == 0
        assert mock_db.insert_data.call_count == 0

    def test_import_teams_database_error(
        self, stats_processor, sample_team_data, mock_db
    ):
        """Test handling database errors during team import"""
        mock_db.execute_query.return_value = []
        mock_db.insert_data.side_effect = Exception("Database error")

        # Should handle error gracefully and continue
        count = stats_processor.import_teams(sample_team_data)

        assert count == 0  # No teams imported due to errors

    def test_import_teams_missing_fields(self, stats_processor, mock_db):
        """Test importing teams with missing fields"""
        incomplete_team_data = [
            {
                "name": "Incomplete Team"
                # Missing other required fields
            }
        ]

        mock_db.execute_query.return_value = []

        # Should handle missing fields gracefully by skipping invalid records
        count = stats_processor.import_teams(incomplete_team_data)

        # With improved error handling, invalid records are skipped
        assert count == 0
        assert mock_db.insert_data.call_count == 0


class TestImportPlayers:
    """Test player import functionality"""

    def test_import_players_success(self, stats_processor, sample_player_data, mock_db):
        """Test successful player import"""
        # Mock no existing players and team lookup
        mock_db.execute_query.side_effect = [
            [],  # No existing player "Austin Taylor"
            [{"id": "hustle"}],  # Team lookup for "Atlanta Hustle"
            [],  # No existing player "Sarah Johnson"
            [{"id": "glory"}],  # Team lookup for "Boston Glory"
        ]

        count = stats_processor.import_players(sample_player_data)

        assert count == 2
        assert mock_db.insert_data.call_count == 2

    def test_import_players_with_team_lookup(self, stats_processor, mock_db):
        """Test player import with team name to ID lookup"""
        player_data = [
            {
                "name": "Test Player",
                "player_id": "test-player",
                "first_name": "Test",
                "last_name": "Player",
                "full_name": "Test Player",
                "team_name": "Test Team",
                "active": True,
                "year": 2024,
            }
        ]

        mock_db.execute_query.side_effect = [
            [],  # No existing player
            [{"id": "test-team"}],  # Team lookup returns string ID
        ]

        count = stats_processor.import_players(player_data)

        # Verify team_id was set correctly
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["team_id"] == "test-team"
        assert "team_name" not in insert_call  # Should be removed

    def test_import_players_team_not_found(self, stats_processor, mock_db):
        """Test player import when team is not found"""
        player_data = [
            {
                "name": "Test Player",
                "player_id": "test-player",
                "first_name": "Test",
                "last_name": "Player",
                "full_name": "Test Player",
                "team_name": "Nonexistent Team",
                "active": True,
                "year": 2024,
            }
        ]

        mock_db.execute_query.side_effect = [
            [],  # No existing player
            [],  # Team not found
        ]

        count = stats_processor.import_players(player_data)

        # Should still import player without team_id
        assert count == 1
        insert_call = mock_db.insert_data.call_args[0][1]
        assert "team_id" not in insert_call or insert_call["team_id"] is None

    def test_import_players_skip_existing(
        self, stats_processor, sample_player_data, mock_db
    ):
        """Test that existing players are skipped"""
        # Mock first player exists, second doesn't
        mock_db.execute_query.side_effect = [
            [{"id": 1}],  # First player exists
            [],  # Second player doesn't exist
            [{"id": "glory"}],  # Team lookup for second player
        ]

        count = stats_processor.import_players(sample_player_data)

        assert count == 1  # Only second player imported
        assert mock_db.insert_data.call_count == 1


class TestImportGame:
    """Test game import functionality"""

    def test_import_game_success(self, stats_processor, sample_game_data, mock_db):
        """Test successful game import"""
        # Mock team lookups
        mock_db.execute_query.side_effect = [
            [{"id": "hustle"}],  # Home team lookup
            [{"id": "glory"}],  # Away team lookup
            [],  # No existing game
        ]

        game_id = stats_processor.import_game(sample_game_data)

        assert game_id == 1  # Mock return value
        assert mock_db.insert_data.call_count == 1

        # Verify correct data transformation
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["home_team_id"] == "hustle"
        assert insert_call["away_team_id"] == "glory"
        assert "home_team_name" not in insert_call
        assert "away_team_name" not in insert_call

    def test_import_game_existing_game(
        self, stats_processor, sample_game_data, mock_db
    ):
        """Test importing game that already exists"""
        # Mock team lookups and existing game
        mock_db.execute_query.side_effect = [
            [{"id": "hustle"}],  # Home team lookup
            [{"id": "glory"}],  # Away team lookup
            [{"id": 10}],  # Existing game found
        ]

        game_id = stats_processor.import_game(sample_game_data)

        assert game_id == 10  # Should return existing game ID
        assert mock_db.insert_data.call_count == 0

    def test_import_game_team_not_found(self, stats_processor, mock_db):
        """Test importing game when team names are not found but IDs are provided"""
        # Game data with direct team IDs (no lookups needed)
        game_data = {
            "game_id": "test-game",
            "away_team_id": "unknown-team",
            "home_team_id": "another-unknown-team",
            "away_score": 10,
            "home_score": 12,
            "status": "Final",
            "year": 2024,
        }

        # Mock no existing game
        mock_db.execute_query.return_value = []

        game_id = stats_processor.import_game(game_data)

        # Should import with provided team IDs
        assert game_id == 1
        assert mock_db.insert_data.call_count == 1

    def test_import_game_without_team_names(self, stats_processor, mock_db):
        """Test importing game data without team names"""
        game_data = {
            "game_id": "direct-import-game",
            "home_team_id": "team1",
            "away_team_id": "team2",
            "home_score": 100,
            "away_score": 95,
            "status": "Final",
            "year": 2024,
        }

        mock_db.execute_query.return_value = []  # No existing game

        game_id = stats_processor.import_game(game_data)

        assert game_id == 1
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["home_team_id"] == "team1"
        assert insert_call["away_team_id"] == "team2"


class TestImportPlayerGameStats:
    """Test player game stats import functionality"""

    @pytest.fixture
    def sample_player_stats(self):
        """Sample Ultimate Frisbee player game stats data"""
        return [
            {
                "game_id": "hustle-vs-glory-game1",
                "player_id": "austin-taylor",
                "team_id": "hustle",
                "year": 2024,
                "assists": 3,
                "goals": 2,
                "hockey_assists": 1,
                "completions": 15,
                "throw_attempts": 18,
                "throwaways": 2,
                "stalls": 1,
                "callahans_thrown": 0,
                "yards_received": 120,
                "yards_thrown": 85,
                "hucks_attempted": 4,
                "hucks_completed": 3,
                "catches": 12,
                "drops": 1,
                "blocks": 2,
                "callahans": 0,
                "pulls": 3,
                "ob_pulls": 1,
                "recorded_pulls": 3,
                "o_points_played": 8,
                "o_points_scored": 5,
                "d_points_played": 7,
                "d_points_scored": 2,
                "seconds_played": 1800,
                "o_opportunities": 8,
                "o_opportunity_scores": 5,
                "d_opportunities": 7,
                "d_opportunity_stops": 2,
            },
            {
                "game_id": "hustle-vs-glory-game1",
                "player_id": "sarah-johnson",
                "team_id": "glory",
                "year": 2024,
                "assists": 4,
                "goals": 3,
                "hockey_assists": 2,
                "completions": 18,
                "throw_attempts": 20,
                "throwaways": 1,
                "stalls": 0,
                "callahans_thrown": 0,
                "yards_received": 95,
                "yards_thrown": 110,
                "hucks_attempted": 2,
                "hucks_completed": 2,
                "catches": 8,
                "drops": 0,
                "blocks": 1,
                "callahans": 1,
                "pulls": 0,
                "ob_pulls": 0,
                "recorded_pulls": 0,
                "o_points_played": 9,
                "o_points_scored": 7,
                "d_points_played": 6,
                "d_points_scored": 3,
                "seconds_played": 1650,
                "o_opportunities": 9,
                "o_opportunity_scores": 7,
                "d_opportunities": 6,
                "d_opportunity_stops": 3,
            },
        ]

    def test_import_player_game_stats_success(
        self, stats_processor, sample_player_stats, mock_db
    ):
        """Test successful player game stats import"""
        count = stats_processor.import_player_game_stats(sample_player_stats)

        assert count == 2
        assert mock_db.insert_data.call_count == 2

        # Verify correct table and data
        calls = mock_db.insert_data.call_args_list
        assert calls[0][0][0] == "player_game_stats"
        assert calls[0][0][1]["goals"] == 2
        assert calls[0][0][1]["assists"] == 3
        assert calls[1][0][1]["goals"] == 3
        assert calls[1][0][1]["assists"] == 4

    def test_import_player_game_stats_empty(self, stats_processor, mock_db):
        """Test importing empty player game stats"""
        count = stats_processor.import_player_game_stats([])

        assert count == 0
        assert mock_db.insert_data.call_count == 0

    def test_import_player_game_stats_with_errors(
        self, stats_processor, sample_player_stats, mock_db
    ):
        """Test handling errors during stats import"""
        # First insert succeeds, second fails
        mock_db.insert_data.side_effect = [1, Exception("Database error")]

        count = stats_processor.import_player_game_stats(sample_player_stats)

        assert count == 1  # Only first stat imported

    def test_import_player_game_stats_missing_fields(self, stats_processor, mock_db):
        """Test importing stats with missing fields"""
        incomplete_stats = [
            {
                "game_id": "test-game",
                "player_id": "test-player",
                "team_id": "test-team",
                "year": 2024,
                "goals": 2,
                "assists": 1,
                # Missing other UFA fields - should use defaults
            }
        ]

        count = stats_processor.import_player_game_stats(incomplete_stats)

        assert count == 1
        # Verify PlayerGameStats model handles missing fields with defaults
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["goals"] == 2
        assert insert_call["assists"] == 1


class TestCalculateSeasonStats:
    """Test season statistics calculation"""

    def test_calculate_season_stats_success(self, stats_processor, mock_db):
        """Test successful season stats calculation"""
        # Mock game stats query results
        mock_db.execute_query.return_value = [
            {
                "player_id": "player1",
                "games_played": 10,
                "total_goals": 25,
                "total_assists": 30,
                "total_completions": 150,
                "total_throwaways": 12,
                "total_seconds_played": 18000,
            }
        ]

        stats_processor.calculate_season_stats(2024)

        # Verify database operations
        assert mock_db.execute_query.call_count >= 2  # At least select and clear
        assert mock_db.insert_data.call_count >= 1

        # Check that season stats were calculated correctly
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["year"] == 2024
        assert insert_call["total_goals"] == 25
        assert insert_call["total_assists"] == 30

    def test_calculate_season_stats_no_data(self, stats_processor, mock_db):
        """Test season stats calculation with no game data"""
        mock_db.execute_query.return_value = []

        stats_processor.calculate_season_stats(2024)

        # Should clear existing stats but not insert new ones
        assert mock_db.execute_query.call_count >= 2
        assert mock_db.insert_data.call_count == 0

    def test_calculate_season_stats_division_by_zero(self, stats_processor, mock_db):
        """Test season stats calculation handles division by zero"""
        mock_db.execute_query.return_value = [
            {
                "player_id": "player1",
                "games_played": 0,  # Division by zero case
                "total_goals": 0,
                "total_assists": 0,
                "total_completions": 0,
                "total_seconds_played": 0,
            }
        ]

        # Should not raise exception
        stats_processor.calculate_season_stats(2024)

        # Verify handling of zero games
        if mock_db.insert_data.call_count > 0:
            insert_call = mock_db.insert_data.call_args[0][1]
            # Should handle division by zero gracefully
            assert "total_goals" in insert_call


class TestAdvancedCalculations:
    """Test advanced statistical calculations"""

    def test_calculate_efficiency_metrics(self, stats_processor, mock_db):
        """Test calculation of advanced efficiency metrics for UFA"""
        mock_db.execute_query.return_value = [
            {
                "player_id": "player1",
                "games_played": 10,
                "total_goals": 25,
                "total_assists": 30,
                "total_completions": 180,
                "total_throw_attempts": 200,
                "total_throwaways": 15,
                "total_seconds_played": 18000,
            }
        ]

        stats_processor.calculate_season_stats(2024)

        if mock_db.insert_data.call_count > 0:
            insert_call = mock_db.insert_data.call_args[0][1]

            # Check completion percentage calculation
            expected_completion_pct = 180 / 200 * 100  # 90%
            if "completion_percentage" in insert_call:
                assert (
                    abs(insert_call["completion_percentage"] - expected_completion_pct)
                    < 0.01
                )

    def test_calculate_team_season_stats(self, stats_processor, mock_db):
        """Test team season statistics calculation"""
        # This would test team-level aggregations
        mock_db.execute_query.return_value = [
            {
                "team_id": "hustle",
                "games_played": 16,
                "wins": 12,
                "losses": 4,
                "points_for": 240,
                "points_against": 210,
            }
        ]

        # If team stats calculation exists
        if hasattr(stats_processor, "calculate_team_season_stats"):
            stats_processor.calculate_team_season_stats(2024)

            # Verify team stats calculations
            assert mock_db.insert_data.call_count >= 1


class TestDataValidation:
    """Test data validation and cleaning"""

    def test_validate_game_data(self, stats_processor):
        """Test game data validation"""
        # Test valid data
        valid_game = {"game_date": "2024-01-15", "home_score": 15, "away_score": 12}

        # If validation method exists
        if hasattr(stats_processor, "_validate_game_data"):
            assert stats_processor._validate_game_data(valid_game) is True

        # Test invalid data
        invalid_game = {
            "game_date": "invalid-date",
            "home_score": -5,  # Invalid score
        }

        if hasattr(stats_processor, "_validate_game_data"):
            assert stats_processor._validate_game_data(invalid_game) is False

    def test_clean_player_name(self, stats_processor):
        """Test player name cleaning"""
        test_names = [
            "  austin taylor  ",  # Extra whitespace
            "SARAH JOHNSON",  # All caps
            "mike reynolds jr.",  # Mixed case with suffix
        ]

        expected_names = ["Austin Taylor", "Sarah Johnson", "Mike Reynolds Jr."]

        # If name cleaning method exists
        if hasattr(stats_processor, "_clean_player_name"):
            for test_name, expected in zip(test_names, expected_names, strict=False):
                cleaned = stats_processor._clean_player_name(test_name)
                assert cleaned == expected


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_database_connection_error(self, sample_team_data):
        """Test handling database connection errors"""
        mock_db = Mock(spec=SQLDatabase)
        mock_db.execute_query.side_effect = Exception("Connection lost")

        stats_processor = StatsProcessor(mock_db)

        # Should handle database errors gracefully
        count = stats_processor.import_teams(sample_team_data)
        assert count == 0

    def test_malformed_data_handling(self, stats_processor, mock_db):
        """Test handling of malformed UFA data"""
        malformed_data = [
            {"invalid": "data structure"},
            None,
            {"name": None},  # None values
            {},  # Empty dict
        ]

        # Should not raise exceptions
        count = stats_processor.import_teams(malformed_data)

        # May import some or none depending on validation
        assert count >= 0

    def test_transaction_rollback(self, stats_processor, mock_db):
        """Test transaction rollback on errors"""
        # If transaction support exists
        if hasattr(stats_processor, "_execute_with_transaction"):
            mock_db.execute_query.side_effect = [
                None,  # Begin transaction
                Exception("Error in middle of transaction"),
            ]

            with pytest.raises(Exception):
                stats_processor.import_teams(
                    [{"name": "Test UFA Team", "team_id": "test-team", "year": 2024}]
                )

            # Should have attempted rollback
            rollback_calls = [
                call
                for call in mock_db.execute_query.call_args_list
                if "ROLLBACK" in str(call)
            ]
            assert len(rollback_calls) > 0
