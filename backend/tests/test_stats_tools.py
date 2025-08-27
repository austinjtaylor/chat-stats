"""
Test Stats Tools module functionality.
Tests all SQL query tools used by the AI system for sports statistics.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stats_tools import StatsToolManager
from sql_database import SQLDatabase


class TestStatsToolManager:
    """Test StatsToolManager class functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database for testing"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = []
        return mock
    
    @pytest.fixture
    def tool_manager(self, mock_db):
        """StatsToolManager instance with mock database"""
        return StatsToolManager(mock_db)
    
    def test_init(self, mock_db):
        """Test StatsToolManager initialization"""
        manager = StatsToolManager(mock_db)
        
        assert manager.db is mock_db
        assert hasattr(manager, 'get_player_stats')
        assert hasattr(manager, 'get_team_stats')
        assert hasattr(manager, 'get_game_results')
        
    def test_get_tool_schemas(self, tool_manager):
        """Test getting tool schemas for AI"""
        schemas = tool_manager.get_tool_schemas()
        
        assert isinstance(schemas, list)
        assert len(schemas) > 0
        
        # Check that all expected tools are present
        tool_names = [schema["name"] for schema in schemas]
        expected_tools = [
            "get_player_stats",
            "get_team_stats", 
            "get_game_results",
            "get_league_leaders",
            "compare_players",
            "search_players",
            "get_standings"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
            
        # Verify schema structure
        for schema in schemas:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema
            assert "type" in schema["parameters"]
            assert schema["parameters"]["type"] == "object"


class TestGetPlayerStats:
    """Test get_player_stats tool functionality"""
    
    @pytest.fixture
    def mock_db_with_player_data(self):
        """Mock database with player stats data"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = [
            {
                "player_id": 1,
                "name": "LeBron James",
                "team_name": "Los Angeles Lakers",
                "position": "Forward",
                "games_played": 70,
                "points_per_game": 25.2,
                "rebounds_per_game": 7.8,
                "assists_per_game": 6.9,
                "field_goal_percentage": 54.1
            }
        ]
        return mock
    
    def test_get_player_stats_by_name(self, mock_db_with_player_data):
        """Test getting player stats by name"""
        tool_manager = StatsToolManager(mock_db_with_player_data)
        
        result = tool_manager.get_player_stats(player_name="LeBron James")
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data) == 1
        assert result_data[0]["name"] == "LeBron James"
        assert result_data[0]["points_per_game"] == 25.2
        
        # Verify correct SQL query was called
        mock_db_with_player_data.execute_query.assert_called_once()
        call_args = mock_db_with_player_data.execute_query.call_args
        assert "LeBron James" in str(call_args)
        
    def test_get_player_stats_by_team(self, mock_db_with_player_data):
        """Test getting player stats by team"""
        tool_manager = StatsToolManager(mock_db_with_player_data)
        
        result = tool_manager.get_player_stats(team_name="Los Angeles Lakers")
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data) == 1
        assert result_data[0]["team_name"] == "Los Angeles Lakers"
        
    def test_get_player_stats_season_filter(self, mock_db_with_player_data):
        """Test getting player stats with season filter"""
        tool_manager = StatsToolManager(mock_db_with_player_data)
        
        result = tool_manager.get_player_stats(
            player_name="LeBron James",
            season=2024
        )
        
        # Verify season filter was applied in query
        call_args = mock_db_with_player_data.execute_query.call_args
        assert "2024" in str(call_args)
        
    def test_get_player_stats_stat_type_game(self, mock_db_with_player_data):
        """Test getting individual game stats"""
        # Mock game stats data
        mock_db_with_player_data.execute_query.return_value = [
            {
                "game_date": "2024-01-15",
                "opponent": "Boston Celtics",
                "points": 28,
                "rebounds": 9,
                "assists": 7,
                "minutes_played": 38
            }
        ]
        
        tool_manager = StatsToolManager(mock_db_with_player_data)
        
        result = tool_manager.get_player_stats(
            player_name="LeBron James",
            stat_type="game"
        )
        
        result_data = json.loads(result)
        assert result_data[0]["points"] == 28
        assert result_data[0]["opponent"] == "Boston Celtics"
        
    def test_get_player_stats_no_results(self, mock_db):
        """Test getting player stats when no data found"""
        mock_db.execute_query.return_value = []
        tool_manager = StatsToolManager(mock_db)
        
        result = tool_manager.get_player_stats(player_name="Unknown Player")
        
        result_data = json.loads(result)
        assert result_data == []
        
    def test_get_player_stats_database_error(self, mock_db):
        """Test handling database errors in get_player_stats"""
        mock_db.execute_query.side_effect = Exception("Database connection error")
        tool_manager = StatsToolManager(mock_db)
        
        result = tool_manager.get_player_stats(player_name="LeBron James")
        
        # Should return error message or empty result
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert "error" in result_data or result_data == []


class TestGetTeamStats:
    """Test get_team_stats tool functionality"""
    
    @pytest.fixture
    def mock_db_with_team_data(self):
        """Mock database with team stats data"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = [
            {
                "team_id": 1,
                "name": "Los Angeles Lakers", 
                "wins": 45,
                "losses": 37,
                "win_percentage": 54.9,
                "points_per_game": 115.2,
                "points_allowed_per_game": 112.8,
                "conference": "Western",
                "division": "Pacific"
            }
        ]
        return mock
    
    def test_get_team_stats_by_name(self, mock_db_with_team_data):
        """Test getting team stats by name"""
        tool_manager = StatsToolManager(mock_db_with_team_data)
        
        result = tool_manager.get_team_stats(team_name="Los Angeles Lakers")
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data) == 1
        assert result_data[0]["name"] == "Los Angeles Lakers"
        assert result_data[0]["wins"] == 45
        
    def test_get_team_stats_roster_info(self, mock_db_with_team_data):
        """Test getting team stats with roster information"""
        # Mock roster data
        mock_db_with_team_data.execute_query.return_value = [
            {
                "player_name": "LeBron James",
                "position": "Forward",
                "jersey_number": 23,
                "points_per_game": 25.2
            },
            {
                "player_name": "Anthony Davis",
                "position": "Forward-Center", 
                "jersey_number": 3,
                "points_per_game": 22.1
            }
        ]
        
        tool_manager = StatsToolManager(mock_db_with_team_data)
        
        result = tool_manager.get_team_stats(
            team_name="Los Angeles Lakers",
            include_roster=True
        )
        
        result_data = json.loads(result)
        assert len(result_data) == 2  # Two players
        assert result_data[0]["player_name"] == "LeBron James"
        
    def test_get_team_stats_season_filter(self, mock_db_with_team_data):
        """Test getting team stats with season filter"""
        tool_manager = StatsToolManager(mock_db_with_team_data)
        
        result = tool_manager.get_team_stats(
            team_name="Los Angeles Lakers",
            season=2024
        )
        
        # Verify season filter was applied
        call_args = mock_db_with_team_data.execute_query.call_args
        assert "2024" in str(call_args)


class TestGetGameResults:
    """Test get_game_results tool functionality"""
    
    @pytest.fixture  
    def mock_db_with_game_data(self):
        """Mock database with game results data"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = [
            {
                "game_id": 1,
                "game_date": "2024-01-15",
                "home_team": "Los Angeles Lakers",
                "away_team": "Boston Celtics",
                "home_score": 110,
                "away_score": 105,
                "venue": "Crypto.com Arena"
            }
        ]
        return mock
    
    def test_get_game_results_by_team(self, mock_db_with_game_data):
        """Test getting game results by team"""
        tool_manager = StatsToolManager(mock_db_with_game_data)
        
        result = tool_manager.get_game_results(team_name="Los Angeles Lakers")
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data) == 1
        assert result_data[0]["home_team"] == "Los Angeles Lakers"
        assert result_data[0]["home_score"] == 110
        
    def test_get_game_results_by_date(self, mock_db_with_game_data):
        """Test getting game results by date"""
        tool_manager = StatsToolManager(mock_db_with_game_data)
        
        result = tool_manager.get_game_results(date="2024-01-15")
        
        call_args = mock_db_with_game_data.execute_query.call_args
        assert "2024-01-15" in str(call_args)
        
    def test_get_game_results_limit(self, mock_db_with_game_data):
        """Test getting game results with limit"""
        tool_manager = StatsToolManager(mock_db_with_game_data)
        
        result = tool_manager.get_game_results(
            team_name="Los Angeles Lakers",
            limit=5
        )
        
        call_args = mock_db_with_game_data.execute_query.call_args
        assert "LIMIT 5" in str(call_args) or "5" in str(call_args)


class TestGetLeagueLeaders:
    """Test get_league_leaders tool functionality"""
    
    @pytest.fixture
    def mock_db_with_leaders_data(self):
        """Mock database with league leaders data"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = [
            {
                "player_name": "Luka Doncic",
                "team_name": "Dallas Mavericks",
                "stat_value": 32.8,
                "rank": 1
            },
            {
                "player_name": "Joel Embiid", 
                "team_name": "Philadelphia 76ers",
                "stat_value": 30.4,
                "rank": 2
            }
        ]
        return mock
    
    def test_get_league_leaders_points(self, mock_db_with_leaders_data):
        """Test getting league leaders for points"""
        tool_manager = StatsToolManager(mock_db_with_leaders_data)
        
        result = tool_manager.get_league_leaders(stat_category="points")
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data) == 2
        assert result_data[0]["player_name"] == "Luka Doncic"
        assert result_data[0]["stat_value"] == 32.8
        
    def test_get_league_leaders_custom_limit(self, mock_db_with_leaders_data):
        """Test getting league leaders with custom limit"""
        tool_manager = StatsToolManager(mock_db_with_leaders_data)
        
        result = tool_manager.get_league_leaders(
            stat_category="rebounds",
            limit=10
        )
        
        call_args = mock_db_with_leaders_data.execute_query.call_args
        assert "10" in str(call_args)
        
    def test_get_league_leaders_season_filter(self, mock_db_with_leaders_data):
        """Test getting league leaders with season filter"""
        tool_manager = StatsToolManager(mock_db_with_leaders_data)
        
        result = tool_manager.get_league_leaders(
            stat_category="assists",
            season=2024
        )
        
        call_args = mock_db_with_leaders_data.execute_query.call_args
        assert "2024" in str(call_args)


class TestComparePlayers:
    """Test compare_players tool functionality"""
    
    @pytest.fixture
    def mock_db_with_comparison_data(self):
        """Mock database with player comparison data"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = [
            {
                "player_name": "LeBron James",
                "team_name": "Los Angeles Lakers",
                "points_per_game": 25.2,
                "rebounds_per_game": 7.8,
                "assists_per_game": 6.9,
                "field_goal_percentage": 54.1
            },
            {
                "player_name": "Kevin Durant",
                "team_name": "Phoenix Suns", 
                "points_per_game": 28.1,
                "rebounds_per_game": 6.7,
                "assists_per_game": 5.2,
                "field_goal_percentage": 56.3
            }
        ]
        return mock
    
    def test_compare_players_basic(self, mock_db_with_comparison_data):
        """Test basic player comparison"""
        tool_manager = StatsToolManager(mock_db_with_comparison_data)
        
        result = tool_manager.compare_players([
            "LeBron James",
            "Kevin Durant"
        ])
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data) == 2
        
        # Verify both players are in results
        player_names = [player["player_name"] for player in result_data]
        assert "LeBron James" in player_names
        assert "Kevin Durant" in player_names
        
    def test_compare_players_with_season(self, mock_db_with_comparison_data):
        """Test player comparison with season filter"""
        tool_manager = StatsToolManager(mock_db_with_comparison_data)
        
        result = tool_manager.compare_players(
            ["LeBron James", "Kevin Durant"],
            season=2024
        )
        
        call_args = mock_db_with_comparison_data.execute_query.call_args
        assert "2024" in str(call_args)
        
    def test_compare_players_empty_list(self, mock_db):
        """Test compare_players with empty player list"""
        mock_db.execute_query.return_value = []
        tool_manager = StatsToolManager(mock_db)
        
        result = tool_manager.compare_players([])
        
        result_data = json.loads(result)
        assert result_data == []


class TestSearchPlayers:
    """Test search_players tool functionality"""
    
    @pytest.fixture
    def mock_db_with_search_data(self):
        """Mock database with player search data"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = [
            {
                "player_name": "LeBron James",
                "team_name": "Los Angeles Lakers",
                "position": "Forward",
                "jersey_number": 23
            },
            {
                "player_name": "LeBron James Jr.",
                "team_name": "G League",
                "position": "Guard",
                "jersey_number": 0
            }
        ]
        return mock
    
    def test_search_players_by_name(self, mock_db_with_search_data):
        """Test searching players by name"""
        tool_manager = StatsToolManager(mock_db_with_search_data)
        
        result = tool_manager.search_players(name_query="LeBron")
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data) == 2
        assert "LeBron" in result_data[0]["player_name"]
        
    def test_search_players_by_team(self, mock_db_with_search_data):
        """Test searching players by team"""
        tool_manager = StatsToolManager(mock_db_with_search_data)
        
        result = tool_manager.search_players(team_name="Los Angeles Lakers")
        
        call_args = mock_db_with_search_data.execute_query.call_args
        assert "Los Angeles Lakers" in str(call_args)
        
    def test_search_players_by_position(self, mock_db_with_search_data):
        """Test searching players by position"""
        tool_manager = StatsToolManager(mock_db_with_search_data)
        
        result = tool_manager.search_players(position="Forward")
        
        call_args = mock_db_with_search_data.execute_query.call_args
        assert "Forward" in str(call_args)


class TestGetStandings:
    """Test get_standings tool functionality"""
    
    @pytest.fixture
    def mock_db_with_standings_data(self):
        """Mock database with standings data"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = [
            {
                "team_name": "Boston Celtics",
                "wins": 55,
                "losses": 27,
                "win_percentage": 67.1,
                "conference": "Eastern",
                "division": "Atlantic",
                "conference_rank": 1,
                "division_rank": 1
            },
            {
                "team_name": "Denver Nuggets",
                "wins": 50,
                "losses": 32, 
                "win_percentage": 61.0,
                "conference": "Western",
                "division": "Northwest",
                "conference_rank": 1,
                "division_rank": 1
            }
        ]
        return mock
    
    def test_get_standings_all(self, mock_db_with_standings_data):
        """Test getting all standings"""
        tool_manager = StatsToolManager(mock_db_with_standings_data)
        
        result = tool_manager.get_standings()
        
        assert isinstance(result, str)
        result_data = json.loads(result)
        assert len(result_data) == 2
        assert result_data[0]["conference_rank"] == 1
        
    def test_get_standings_by_conference(self, mock_db_with_standings_data):
        """Test getting standings by conference"""
        tool_manager = StatsToolManager(mock_db_with_standings_data)
        
        result = tool_manager.get_standings(conference="Eastern")
        
        call_args = mock_db_with_standings_data.execute_query.call_args
        assert "Eastern" in str(call_args)
        
    def test_get_standings_by_division(self, mock_db_with_standings_data):
        """Test getting standings by division"""
        tool_manager = StatsToolManager(mock_db_with_standings_data)
        
        result = tool_manager.get_standings(division="Atlantic")
        
        call_args = mock_db_with_standings_data.execute_query.call_args
        assert "Atlantic" in str(call_args)


class TestToolIntegration:
    """Test tool integration scenarios"""
    
    def test_multiple_tool_calls(self, mock_db):
        """Test using multiple tools in sequence"""
        mock_db.execute_query.return_value = [
            {"player_name": "LeBron James", "points_per_game": 25.2}
        ]
        
        tool_manager = StatsToolManager(mock_db)
        
        # Call multiple tools
        player_result = tool_manager.get_player_stats(player_name="LeBron James")
        team_result = tool_manager.get_team_stats(team_name="Los Angeles Lakers")
        
        assert isinstance(player_result, str)
        assert isinstance(team_result, str)
        assert mock_db.execute_query.call_count == 2
        
    def test_tool_error_isolation(self, mock_db):
        """Test that errors in one tool don't affect others"""
        # First call fails, second succeeds
        mock_db.execute_query.side_effect = [
            Exception("Database error"),
            [{"team_name": "Lakers", "wins": 45}]
        ]
        
        tool_manager = StatsToolManager(mock_db)
        
        # First tool call should handle error gracefully
        player_result = tool_manager.get_player_stats(player_name="Test Player")
        
        # Second tool call should still work
        team_result = tool_manager.get_team_stats(team_name="Lakers")
        
        # Both should return valid JSON strings
        assert isinstance(player_result, str)
        assert isinstance(team_result, str)
        
        # Verify error handling
        player_data = json.loads(player_result)
        team_data = json.loads(team_result)
        
        assert len(team_data) == 1  # Second call succeeded
        
    def test_parameter_validation(self, mock_db):
        """Test parameter validation in tools"""
        tool_manager = StatsToolManager(mock_db)
        
        # Test with invalid parameters
        result = tool_manager.get_player_stats(
            season="invalid_season"  # Should handle gracefully
        )
        
        assert isinstance(result, str)
        # Should either return error or empty result
        result_data = json.loads(result)
        assert isinstance(result_data, (list, dict))


class TestPerformanceOptimization:
    """Test performance-related functionality"""
    
    def test_query_optimization(self, mock_db):
        """Test that queries are optimized"""
        tool_manager = StatsToolManager(mock_db)
        
        # Call tool that should use indexed columns
        tool_manager.get_player_stats(player_name="LeBron James")
        
        # Verify query uses efficient WHERE clauses
        call_args = mock_db.execute_query.call_args
        query = str(call_args)
        
        # Should use proper indexing hints or efficient WHERE clauses
        assert "WHERE" in query
        
    def test_result_limiting(self, mock_db):
        """Test that results are properly limited"""
        # Mock large result set
        large_result = [{"player": f"Player {i}"} for i in range(1000)]
        mock_db.execute_query.return_value = large_result
        
        tool_manager = StatsToolManager(mock_db)
        
        result = tool_manager.get_league_leaders("points", limit=10)
        
        # Should limit results appropriately
        call_args = mock_db.execute_query.call_args
        query = str(call_args)
        assert "LIMIT" in query or "10" in query