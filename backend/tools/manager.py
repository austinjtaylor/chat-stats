"""
Sports statistics tools manager for Claude AI function calling.
Main orchestrator that coordinates all stats tool modules.
"""

import json
from typing import Any

from tools.game import get_game_results
from tools.player import (
    compare_players,
    get_league_leaders,
    get_player_stats,
    get_worst_performers,
    search_players,
)
from tools.query import execute_custom_query
from tools.team import get_standings, get_team_stats
from utils.game import get_game_details

from data.database import SQLDatabase


class StatsToolManager:
    """Manages sports statistics tools for Claude AI."""

    def __init__(self, db: SQLDatabase = None):
        """
        Initialize the stats tool manager.

        Args:
            db: SQLDatabase instance. If None, creates a new one.
        """
        self.db = db or SQLDatabase()
        self.last_sources = []

    def get_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get all tool definitions for Claude.

        Returns:
            List of tool definition dictionaries
        """
        return [
            {
                "name": "execute_custom_query",
                "description": "Execute custom SQL query to retrieve any sports statistics data. Use this for complex queries involving multiple tables, aggregations, or specific filtering criteria.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL SELECT query to execute. Must be a SELECT statement only.",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Optional parameters for the query as key-value pairs (e.g., {'season': '2023', 'limit': 10})",
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what this query retrieves and why",
                        },
                    },
                    "required": ["query", "explanation"],
                },
            },
            {
                "name": "get_game_details",
                "description": "Get comprehensive details about a specific game, including individual stat leaders and team statistics. Use this when users ask for detailed information about a specific game.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "game_id": {
                            "type": "string",
                            "description": "The game ID (e.g., '2025-08-23-BOS-MIN')",
                        },
                        "date": {
                            "type": "string",
                            "description": "The game date in YYYY-MM-DD format",
                        },
                        "teams": {
                            "type": "string",
                            "description": "The teams playing (e.g., 'BOS-MIN' or 'Boston vs Minnesota')",
                        },
                    },
                    "required": [],
                },
            },
        ]

    def execute_tool(self, tool_name: str, **kwargs) -> str:
        """
        Execute a tool with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool arguments as keyword arguments

        Returns:
            Tool execution results as a string for Claude
        """
        tool_methods = {
            "execute_custom_query": self._execute_custom_query,
            "get_player_stats": self._get_player_stats,
            "get_team_stats": self._get_team_stats,
            "get_game_results": self._get_game_results,
            "get_game_details": self._get_game_details,
            "get_league_leaders": self._get_league_leaders,
            "compare_players": self._compare_players,
            "search_players": self._search_players,
            "get_standings": self._get_standings,
            "get_worst_performers": self._get_worst_performers,
        }

        if tool_name not in tool_methods:
            return f"Error: Unknown tool '{tool_name}'"

        try:
            result = tool_methods[tool_name](**kwargs)

            # Store the actual result data for later retrieval
            if isinstance(result, dict):
                # Create a source entry with the tool name, parameters, and results
                source_entry = {"tool": tool_name, "parameters": kwargs, "data": result}
                self.last_sources.append(source_entry)

            # Convert result to string for Claude
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    def _execute_custom_query(
        self, query: str, parameters: dict[str, Any] = None, explanation: str = None
    ) -> dict[str, Any]:
        """Execute a custom SQL query with safety checks."""
        return execute_custom_query(self.db, query, parameters, explanation)

    def _get_player_stats(
        self,
        player_name: str,
        season: str = None,
        stat_type: str = "season",
        game_date: str = None,
    ) -> dict[str, Any]:
        """Get player statistics."""
        return get_player_stats(self.db, player_name, season, stat_type, game_date)

    def _get_team_stats(
        self, team_name: str, season: str = None, include_roster: bool = False
    ) -> dict[str, Any]:
        """Get team statistics."""
        return get_team_stats(self.db, team_name, season, include_roster)

    def _get_game_results(
        self, date: str = None, team_name: str = None, include_stats: bool = False
    ) -> dict[str, Any]:
        """Get game results."""
        return get_game_results(self.db, date, team_name, include_stats)

    def _get_league_leaders(
        self, category: str, season: str = None, limit: int = 3
    ) -> dict[str, Any]:
        """Get league leaders in a statistical category."""
        return get_league_leaders(self.db, category, season, limit)

    def _compare_players(
        self, player_names: list[str], season: str = None, categories: list[str] = None
    ) -> dict[str, Any]:
        """Compare multiple players."""
        return compare_players(self.db, player_names, season, categories)

    def _search_players(
        self, search_term: str = None, team_name: str = None, position: str = None
    ) -> dict[str, Any]:
        """Search for players."""
        return search_players(self.db, search_term, team_name, position)

    def _get_standings(
        self, season: str = None, conference: str = None, division: str = None
    ) -> dict[str, Any]:
        """Get league standings."""
        return get_standings(self.db, season, conference, division)

    def _get_worst_performers(
        self, category: str, season: str = None, limit: int = 10
    ) -> dict[str, Any]:
        """Get players with worst performance in a category."""
        return get_worst_performers(self.db, category, season, limit)

    def _get_game_details(
        self, game_id: str = None, date: str = None, teams: str = None
    ) -> dict[str, Any]:
        """Get comprehensive game details similar to UFA game summary page."""
        return get_game_details(self.db, game_id, date, teams)

    def get_last_sources(self) -> list[str]:
        """Get the last sources used in tool execution."""
        return self.last_sources

    def reset_sources(self):
        """Reset the sources list."""
        self.last_sources = []
