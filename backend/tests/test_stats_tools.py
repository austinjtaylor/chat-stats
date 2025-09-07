"""
Test Stats Tools module functionality.
Tests StatsToolManager and its tools for sports statistics queries.
"""

import json
import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sql_database import SQLDatabase
from stats_tools import StatsToolManager


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
        assert hasattr(manager, "last_sources")
        assert manager.last_sources == []

    def test_init_without_db(self):
        """Test StatsToolManager initialization without providing database"""
        with patch("stats_tools.SQLDatabase") as mock_sql_db_class:
            mock_db_instance = Mock()
            mock_sql_db_class.return_value = mock_db_instance

            manager = StatsToolManager()

            assert manager.db is mock_db_instance
            mock_sql_db_class.assert_called_once()

    def test_get_tool_definitions(self, tool_manager):
        """Test getting tool definitions for AI"""
        definitions = tool_manager.get_tool_definitions()

        assert isinstance(definitions, list)
        assert len(definitions) == 1  # Currently returns only execute_custom_query

        # Check the custom query tool definition
        custom_query_tool = definitions[0]
        assert custom_query_tool["name"] == "execute_custom_query"
        assert "description" in custom_query_tool
        assert "input_schema" in custom_query_tool

        # Verify schema structure
        schema = custom_query_tool["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "query" in schema["properties"]
        assert "parameters" in schema["properties"]
        assert "explanation" in schema["properties"]
        assert schema["required"] == ["query", "explanation"]

    def test_execute_tool_unknown_tool(self, tool_manager):
        """Test executing unknown tool"""
        result = tool_manager.execute_tool("unknown_tool", param="value")

        assert "Error: Unknown tool 'unknown_tool'" in result

    def test_execute_tool_exception(self, tool_manager):
        """Test execute_tool handles exceptions"""
        # Mock the _execute_custom_query method to raise an exception
        with patch.object(
            tool_manager, "_execute_custom_query", side_effect=Exception("Test error")
        ):
            result = tool_manager.execute_tool(
                "execute_custom_query", query="SELECT 1", explanation="test"
            )

            assert "Error executing tool: Test error" in result


class TestCustomQueryTool:
    """Test execute_custom_query tool functionality"""

    @pytest.fixture
    def mock_db_with_data(self):
        """Mock database with sample data"""
        mock = Mock(spec=SQLDatabase)
        mock.execute_query.return_value = [
            {"id": 1, "name": "Test Player", "points": 25},
            {"id": 2, "name": "Another Player", "points": 20},
        ]
        return mock

    @pytest.fixture
    def tool_manager(self, mock_db_with_data):
        """StatsToolManager instance with mock database"""
        return StatsToolManager(mock_db_with_data)

    def test_execute_custom_query_success(self, tool_manager, mock_db_with_data):
        """Test successful custom query execution"""
        query = "SELECT name, points FROM players WHERE points > 20"
        explanation = "Get players with more than 20 points"

        result = tool_manager.execute_tool(
            "execute_custom_query", query=query, explanation=explanation
        )

        # Result should be JSON string
        parsed_result = json.loads(result)
        assert "results" in parsed_result
        assert "explanation" in parsed_result
        assert "query" in parsed_result
        assert len(parsed_result["results"]) == 2
        assert parsed_result["explanation"] == explanation
        assert parsed_result["query"] == query

        # Verify database was called correctly
        mock_db_with_data.execute_query.assert_called_once()

    def test_execute_custom_query_with_parameters(
        self, tool_manager, mock_db_with_data
    ):
        """Test custom query execution with parameters"""
        query = "SELECT * FROM players WHERE points > :min_points"
        parameters = {"min_points": 20}
        explanation = "Get players with points above threshold"

        result = tool_manager.execute_tool(
            "execute_custom_query",
            query=query,
            parameters=parameters,
            explanation=explanation,
        )

        parsed_result = json.loads(result)
        assert "results" in parsed_result
        assert "parameters" in parsed_result
        assert parsed_result["parameters"] == parameters

    def test_execute_custom_query_invalid_sql(self, tool_manager):
        """Test custom query with invalid SQL (non-SELECT)"""
        query = "DELETE FROM players WHERE id = 1"
        explanation = "Try to delete a player"

        result = tool_manager.execute_tool(
            "execute_custom_query", query=query, explanation=explanation
        )

        parsed_result = json.loads(result)
        assert "error" in parsed_result
        assert "Only SELECT queries" in parsed_result["error"]
        assert "allowed for safety" in parsed_result["error"]

    def test_execute_custom_query_database_error(self, tool_manager, mock_db_with_data):
        """Test custom query handles database errors"""
        mock_db_with_data.execute_query.side_effect = Exception(
            "Database connection failed"
        )

        query = "SELECT * FROM players"
        explanation = "Get all players"

        result = tool_manager.execute_tool(
            "execute_custom_query", query=query, explanation=explanation
        )

        parsed_result = json.loads(result)
        assert "error" in parsed_result
        assert "Database connection failed" in parsed_result["error"]

    def test_execute_custom_query_empty_results(self, tool_manager):
        """Test custom query with empty results"""
        mock_db = Mock(spec=SQLDatabase)
        mock_db.execute_query.return_value = []
        tool_manager.db = mock_db

        query = "SELECT * FROM players WHERE name = 'Nonexistent Player'"
        explanation = "Search for non-existent player"

        result = tool_manager.execute_tool(
            "execute_custom_query", query=query, explanation=explanation
        )

        parsed_result = json.loads(result)
        assert parsed_result["results"] == []
        assert parsed_result["row_count"] == 0


class TestLegacyToolMethods:
    """Test the private tool methods that are called by execute_tool"""

    @pytest.fixture
    def mock_db_with_player_data(self):
        """Mock database with player stats data"""
        mock = Mock(spec=SQLDatabase)

        # Mock different responses based on the query
        def mock_execute_query(query, params=None):
            if "FROM players p" in query and "LIKE" in query:
                # Player lookup query
                return [
                    {
                        "player_id": 1,
                        "full_name": "Test Player",
                        "team_name": "Test Team",
                        "position": "Forward",
                        "jersey_number": 23,
                    }
                ]
            elif "player_season_stats" in query:
                # Season stats query
                return [
                    {
                        "player_id": 1,
                        "year": 2024,
                        "team_name": "Test Team",
                        "total_goals": 15,
                        "total_assists": 8,
                        "total_blocks": 3,
                        "games_played": 20,
                    }
                ]
            elif "status = 'active'" in query:
                # Search players query
                return [
                    {
                        "id": 1,
                        "name": "Test Player",
                        "team_name": "Test Team",
                        "position": "Forward",
                        "jersey_number": 23,
                        "status": "active",
                    }
                ]
            else:
                # Default empty response
                return []

        mock.execute_query.side_effect = mock_execute_query
        return mock

    @pytest.fixture
    def tool_manager(self, mock_db_with_player_data):
        """StatsToolManager instance with mock database"""
        return StatsToolManager(mock_db_with_player_data)

    def test_get_player_stats_tool(self, tool_manager, mock_db_with_player_data):
        """Test get_player_stats tool execution"""
        result = tool_manager.execute_tool(
            "get_player_stats", player_name="Test Player", season="2024"
        )

        parsed_result = json.loads(result)
        assert "player" in parsed_result
        assert "season_stats" in parsed_result
        assert parsed_result["player"]["full_name"] == "Test Player"
        assert parsed_result["season_stats"]["total_goals"] == 15

        # Verify database was called
        mock_db_with_player_data.execute_query.assert_called()

    def test_get_team_stats_tool(self, tool_manager):
        """Test get_team_stats tool execution"""
        # Create a separate mock for team stats
        mock_db = Mock(spec=SQLDatabase)

        def mock_team_execute_query(query, params=None):
            if "FROM teams" in query:
                # Team lookup query
                return [{"team_id": "test-team", "name": "Test Team", "abbrev": "TT"}]
            elif "team_season_stats" in query:
                # Team stats query
                return [
                    {
                        "team_id": "test-team",
                        "year": 2024,
                        "wins": 10,
                        "losses": 5,
                        "points_for": 150,
                        "points_against": 120,
                    }
                ]
            else:
                return []

        mock_db.execute_query.side_effect = mock_team_execute_query
        team_tool_manager = StatsToolManager(mock_db)

        result = team_tool_manager.execute_tool(
            "get_team_stats", team_name="Test Team", season="2024"
        )

        parsed_result = json.loads(result)
        assert "team" in parsed_result
        assert "season_stats" in parsed_result
        assert parsed_result["team"]["name"] == "Test Team"
        assert parsed_result["season_stats"]["wins"] == 10

    def test_search_players_tool(self, tool_manager, mock_db_with_player_data):
        """Test search_players tool execution"""
        result = tool_manager.execute_tool("search_players", search_term="Test")

        parsed_result = json.loads(result)
        assert "players" in parsed_result
        assert len(parsed_result["players"]) == 1


class TestSourcesTracking:
    """Test sources tracking functionality"""

    @pytest.fixture
    def tool_manager(self):
        """StatsToolManager instance with mock database"""
        mock_db = Mock(spec=SQLDatabase)
        return StatsToolManager(mock_db)

    def test_get_last_sources(self, tool_manager):
        """Test getting last sources"""
        sources = tool_manager.get_last_sources()
        assert sources == []

    def test_reset_sources(self, tool_manager):
        """Test resetting sources"""
        tool_manager.last_sources = ["test source"]
        tool_manager.reset_sources()
        assert tool_manager.last_sources == []

    def test_sources_updated_after_tool_execution(self, tool_manager):
        """Test that sources are updated after tool execution"""
        # Mock a method that returns sources
        mock_result = {"data": [{"test": "data"}], "sources": ["query1", "query2"]}

        with patch.object(
            tool_manager, "_execute_custom_query", return_value=mock_result
        ):
            tool_manager.execute_tool(
                "execute_custom_query", query="SELECT 1", explanation="test"
            )

            assert tool_manager.last_sources == ["query1", "query2"]


class TestToolIntegration:
    """Integration tests for tool execution"""

    @pytest.fixture
    def tool_manager_real_db(self):
        """StatsToolManager with real database for integration testing"""
        # Only create if database exists, otherwise skip
        db_path = "./db/sports_stats.db"
        if not os.path.exists(db_path):
            pytest.skip("Test database not available")

        from sql_database import SQLDatabase

        real_db = SQLDatabase(db_path)
        return StatsToolManager(real_db)

    def test_tool_definitions_are_valid(self, tool_manager_real_db):
        """Test that tool definitions are properly formatted for Claude"""
        definitions = tool_manager_real_db.get_tool_definitions()

        for definition in definitions:
            # Verify required fields
            assert "name" in definition
            assert "description" in definition
            assert "input_schema" in definition

            # Verify schema structure
            schema = definition["input_schema"]
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema

    def test_all_tool_methods_exist(self):
        """Test that all tool methods referenced in execute_tool exist"""
        tool_manager = StatsToolManager()

        # Get all tool methods from execute_tool
        tool_methods = {
            "execute_custom_query": tool_manager._execute_custom_query,
            "get_player_stats": tool_manager._get_player_stats,
            "get_team_stats": tool_manager._get_team_stats,
            "get_game_results": tool_manager._get_game_results,
            "get_league_leaders": tool_manager._get_league_leaders,
            "compare_players": tool_manager._compare_players,
            "search_players": tool_manager._search_players,
            "get_standings": tool_manager._get_standings,
            "get_worst_performers": tool_manager._get_worst_performers,
        }

        # Verify all methods exist and are callable
        for tool_name, method in tool_methods.items():
            assert callable(method), f"Method {tool_name} is not callable"
