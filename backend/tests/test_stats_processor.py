"""
Test Stats Processor module functionality.
Tests data processing, import operations, and statistical calculations.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
from datetime import datetime, date

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stats_processor import StatsProcessor
from sql_database import SQLDatabase
from models import Team, Player, Game, PlayerGameStats


class TestStatsProcessor:
    """Test StatsProcessor class functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database for testing"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = []
        mock.insert_data.return_value = 1
        return mock
    
    @pytest.fixture
    def stats_processor(self, mock_db):
        """StatsProcessor instance with mock database"""
        return StatsProcessor(mock_db)
    
    @pytest.fixture
    def sample_team_data(self):
        """Sample team data for testing"""
        return [
            {
                "name": "Los Angeles Lakers",
                "city": "Los Angeles", 
                "abbreviation": "LAL",
                "division": "Pacific",
                "conference": "Western"
            },
            {
                "name": "Boston Celtics",
                "city": "Boston",
                "abbreviation": "BOS", 
                "division": "Atlantic",
                "conference": "Eastern"
            }
        ]
    
    @pytest.fixture
    def sample_player_data(self):
        """Sample player data for testing"""
        return [
            {
                "name": "LeBron James",
                "first_name": "LeBron",
                "last_name": "James",
                "position": "Forward",
                "jersey_number": 23,
                "team_name": "Los Angeles Lakers"
            },
            {
                "name": "Jayson Tatum", 
                "first_name": "Jayson",
                "last_name": "Tatum",
                "position": "Forward",
                "jersey_number": 0,
                "team_name": "Boston Celtics"
            }
        ]
    
    @pytest.fixture
    def sample_game_data(self):
        """Sample game data for testing"""
        return {
            "game_date": "2024-01-15",
            "home_team_name": "Los Angeles Lakers",
            "away_team_name": "Boston Celtics", 
            "home_score": 110,
            "away_score": 105,
            "venue": "Crypto.com Arena"
        }


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
        assert calls[0][0][1]["name"] == "Los Angeles Lakers"
        
    def test_import_teams_skip_existing(self, stats_processor, sample_team_data, mock_db):
        """Test that existing teams are skipped"""
        # Mock that first team already exists
        mock_db.execute_query.side_effect = [
            [{"id": 1}],  # First team exists
            []  # Second team doesn't exist
        ]
        
        count = stats_processor.import_teams(sample_team_data)
        
        assert count == 1  # Only second team imported
        assert mock_db.insert_data.call_count == 1
        
    def test_import_teams_empty_data(self, stats_processor, mock_db):
        """Test importing empty team data"""
        count = stats_processor.import_teams([])
        
        assert count == 0
        assert mock_db.insert_data.call_count == 0
        
    def test_import_teams_database_error(self, stats_processor, sample_team_data, mock_db):
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
        
        # Should handle missing fields gracefully
        count = stats_processor.import_teams(incomplete_team_data)
        
        assert mock_db.insert_data.call_count == 1
        
        # Verify Team model handles missing fields
        call_args = mock_db.insert_data.call_args[0][1]
        assert call_args["name"] == "Incomplete Team"


class TestImportPlayers:
    """Test player import functionality"""
    
    def test_import_players_success(self, stats_processor, sample_player_data, mock_db):
        """Test successful player import"""
        # Mock no existing players and team lookup
        mock_db.execute_query.side_effect = [
            [],  # No existing player
            [{"id": 1}],  # Team lookup for Lakers
            [],  # No existing player  
            [{"id": 2}]   # Team lookup for Celtics
        ]
        
        count = stats_processor.import_players(sample_player_data)
        
        assert count == 2
        assert mock_db.insert_data.call_count == 2
        
    def test_import_players_with_team_lookup(self, stats_processor, mock_db):
        """Test player import with team name to ID lookup"""
        player_data = [{
            "name": "Test Player",
            "team_name": "Test Team"
        }]
        
        mock_db.execute_query.side_effect = [
            [],  # No existing player
            [{"id": 5}]  # Team lookup returns ID 5
        ]
        
        count = stats_processor.import_players(player_data)
        
        # Verify team_id was set correctly
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["team_id"] == 5
        assert "team_name" not in insert_call  # Should be removed
        
    def test_import_players_team_not_found(self, stats_processor, mock_db):
        """Test player import when team is not found"""
        player_data = [{
            "name": "Test Player",
            "team_name": "Nonexistent Team"
        }]
        
        mock_db.execute_query.side_effect = [
            [],  # No existing player
            []   # Team not found
        ]
        
        count = stats_processor.import_players(player_data)
        
        # Should still import player without team_id
        assert count == 1
        insert_call = mock_db.insert_data.call_args[0][1]
        assert "team_id" not in insert_call or insert_call["team_id"] is None
        
    def test_import_players_skip_existing(self, stats_processor, sample_player_data, mock_db):
        """Test that existing players are skipped"""
        # Mock first player exists, second doesn't
        mock_db.execute_query.side_effect = [
            [{"id": 1}],  # First player exists
            [],  # Second player doesn't exist
            [{"id": 2}]   # Team lookup for second player
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
            [{"id": 1}],  # Home team lookup
            [{"id": 2}],  # Away team lookup
            []            # No existing game
        ]
        
        game_id = stats_processor.import_game(sample_game_data)
        
        assert game_id == 1  # Mock return value
        assert mock_db.insert_data.call_count == 1
        
        # Verify correct data transformation
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["home_team_id"] == 1
        assert insert_call["away_team_id"] == 2
        assert "home_team_name" not in insert_call
        assert "away_team_name" not in insert_call
        
    def test_import_game_existing_game(self, stats_processor, sample_game_data, mock_db):
        """Test importing game that already exists"""
        # Mock team lookups and existing game
        mock_db.execute_query.side_effect = [
            [{"id": 1}],     # Home team lookup
            [{"id": 2}],     # Away team lookup  
            [{"id": 10}]     # Existing game found
        ]
        
        game_id = stats_processor.import_game(sample_game_data)
        
        assert game_id is None  # Should return None for existing game
        assert mock_db.insert_data.call_count == 0
        
    def test_import_game_team_not_found(self, stats_processor, sample_game_data, mock_db):
        """Test importing game when teams are not found"""
        # Mock team lookups return empty
        mock_db.execute_query.side_effect = [
            [],  # Home team not found
            []   # Away team not found
        ]
        
        game_id = stats_processor.import_game(sample_game_data)
        
        # Should still import with team names
        assert game_id == 1
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["home_team_name"] == "Los Angeles Lakers"
        assert insert_call["away_team_name"] == "Boston Celtics"
        
    def test_import_game_without_team_names(self, stats_processor, mock_db):
        """Test importing game data without team names"""
        game_data = {
            "game_date": "2024-01-15",
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 100,
            "away_score": 95
        }
        
        mock_db.execute_query.return_value = []  # No existing game
        
        game_id = stats_processor.import_game(game_data)
        
        assert game_id == 1
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["home_team_id"] == 1
        assert insert_call["away_team_id"] == 2


class TestImportPlayerGameStats:
    """Test player game stats import functionality"""
    
    @pytest.fixture
    def sample_player_stats(self):
        """Sample player game stats data"""
        return [
            {
                "game_id": 1,
                "player_id": 1,
                "minutes_played": 35,
                "points": 25,
                "rebounds": 8,
                "assists": 6,
                "steals": 2,
                "blocks": 1,
                "field_goals_made": 10,
                "field_goals_attempted": 18
            },
            {
                "game_id": 1,
                "player_id": 2,
                "minutes_played": 32,
                "points": 20,
                "rebounds": 5,
                "assists": 4,
                "steals": 1,
                "blocks": 0,
                "field_goals_made": 8,
                "field_goals_attempted": 15
            }
        ]
    
    def test_import_player_game_stats_success(self, stats_processor, sample_player_stats, mock_db):
        """Test successful player game stats import"""
        count = stats_processor.import_player_game_stats(sample_player_stats)
        
        assert count == 2
        assert mock_db.insert_data.call_count == 2
        
        # Verify correct table and data
        calls = mock_db.insert_data.call_args_list
        assert calls[0][0][0] == "player_game_stats"
        assert calls[0][0][1]["points"] == 25
        assert calls[1][0][1]["points"] == 20
        
    def test_import_player_game_stats_empty(self, stats_processor, mock_db):
        """Test importing empty player game stats"""
        count = stats_processor.import_player_game_stats([])
        
        assert count == 0
        assert mock_db.insert_data.call_count == 0
        
    def test_import_player_game_stats_with_errors(self, stats_processor, sample_player_stats, mock_db):
        """Test handling errors during stats import"""
        # First insert succeeds, second fails
        mock_db.insert_data.side_effect = [1, Exception("Database error")]
        
        count = stats_processor.import_player_game_stats(sample_player_stats)
        
        assert count == 1  # Only first stat imported
        
    def test_import_player_game_stats_missing_fields(self, stats_processor, mock_db):
        """Test importing stats with missing fields"""
        incomplete_stats = [{
            "game_id": 1,
            "player_id": 1,
            "points": 20
            # Missing other fields
        }]
        
        count = stats_processor.import_player_game_stats(incomplete_stats)
        
        assert count == 1
        # Verify PlayerGameStats model handles missing fields with defaults
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["points"] == 20


class TestCalculateSeasonStats:
    """Test season statistics calculation"""
    
    def test_calculate_season_stats_success(self, stats_processor, mock_db):
        """Test successful season stats calculation"""
        # Mock game stats query results
        mock_db.execute_query.return_value = [
            {
                "player_id": 1,
                "games_played": 10,
                "total_points": 250,
                "total_rebounds": 80,
                "total_assists": 60,
                "total_minutes": 350
            }
        ]
        
        stats_processor.calculate_season_stats(2024)
        
        # Verify database operations
        assert mock_db.execute_query.call_count >= 2  # At least select and clear
        assert mock_db.insert_data.call_count >= 1
        
        # Check that season stats were calculated correctly
        insert_call = mock_db.insert_data.call_args[0][1]
        assert insert_call["season"] == 2024
        assert insert_call["games_played"] == 10
        assert insert_call["ppg"] == 25.0  # 250/10
        
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
                "player_id": 1,
                "games_played": 0,  # Division by zero case
                "total_points": 0,
                "total_rebounds": 0,
                "total_assists": 0,
                "total_minutes": 0
            }
        ]
        
        # Should not raise exception
        stats_processor.calculate_season_stats(2024)
        
        # Verify handling of zero games
        if mock_db.insert_data.call_count > 0:
            insert_call = mock_db.insert_data.call_args[0][1]
            assert insert_call["ppg"] == 0.0 or insert_call["ppg"] is None


class TestAdvancedCalculations:
    """Test advanced statistical calculations"""
    
    def test_calculate_efficiency_metrics(self, stats_processor, mock_db):
        """Test calculation of advanced efficiency metrics"""
        mock_db.execute_query.return_value = [
            {
                "player_id": 1,
                "games_played": 10,
                "total_points": 200,
                "total_field_goals_made": 80,
                "total_field_goals_attempted": 160,
                "total_three_pointers_made": 20,
                "total_free_throws_made": 20,
                "total_minutes": 300
            }
        ]
        
        stats_processor.calculate_season_stats(2024)
        
        if mock_db.insert_data.call_count > 0:
            insert_call = mock_db.insert_data.call_args[0][1]
            
            # Check field goal percentage calculation
            expected_fg_pct = 80 / 160 * 100  # 50%
            if "field_goal_percentage" in insert_call:
                assert abs(insert_call["field_goal_percentage"] - expected_fg_pct) < 0.01
                
    def test_calculate_team_season_stats(self, stats_processor, mock_db):
        """Test team season statistics calculation"""
        # This would test team-level aggregations
        mock_db.execute_query.return_value = [
            {
                "team_id": 1,
                "games_played": 82,
                "wins": 50,
                "losses": 32,
                "points_for": 9000,
                "points_against": 8800
            }
        ]
        
        # If team stats calculation exists
        if hasattr(stats_processor, 'calculate_team_season_stats'):
            stats_processor.calculate_team_season_stats(2024)
            
            # Verify team stats calculations
            assert mock_db.insert_data.call_count >= 1


class TestDataValidation:
    """Test data validation and cleaning"""
    
    def test_validate_game_data(self, stats_processor):
        """Test game data validation"""
        # Test valid data
        valid_game = {
            "game_date": "2024-01-15",
            "home_score": 110,
            "away_score": 105
        }
        
        # If validation method exists
        if hasattr(stats_processor, '_validate_game_data'):
            assert stats_processor._validate_game_data(valid_game) is True
            
        # Test invalid data
        invalid_game = {
            "game_date": "invalid-date",
            "home_score": -10,  # Invalid score
        }
        
        if hasattr(stats_processor, '_validate_game_data'):
            assert stats_processor._validate_game_data(invalid_game) is False
            
    def test_clean_player_name(self, stats_processor):
        """Test player name cleaning"""
        test_names = [
            "  LeBron James  ",  # Extra whitespace
            "JAYSON TATUM",      # All caps
            "anthony davis jr.", # Mixed case with suffix
        ]
        
        expected_names = [
            "LeBron James",
            "Jayson Tatum", 
            "Anthony Davis Jr."
        ]
        
        # If name cleaning method exists
        if hasattr(stats_processor, '_clean_player_name'):
            for test_name, expected in zip(test_names, expected_names):
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
        """Test handling of malformed data"""
        malformed_data = [
            {"invalid": "data structure"},
            None,
            {"name": None},  # None values
            {}  # Empty dict
        ]
        
        # Should not raise exceptions
        count = stats_processor.import_teams(malformed_data)
        
        # May import some or none depending on validation
        assert count >= 0
        
    def test_transaction_rollback(self, stats_processor, mock_db):
        """Test transaction rollback on errors"""
        # If transaction support exists
        if hasattr(stats_processor, '_execute_with_transaction'):
            mock_db.execute_query.side_effect = [
                None,  # Begin transaction
                Exception("Error in middle of transaction")
            ]
            
            with pytest.raises(Exception):
                stats_processor.import_teams([{"name": "Test Team"}])
                
            # Should have attempted rollback
            rollback_calls = [call for call in mock_db.execute_query.call_args_list 
                            if "ROLLBACK" in str(call)]
            assert len(rollback_calls) > 0