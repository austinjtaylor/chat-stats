"""
Sports statistics tools for Claude AI function calling.
Defines tools that Claude can use to query the SQL database for sports statistics.
"""

from typing import Any

from cache_manager import cache_key_for_query, get_cache
from config import config
from sql_database import SQLDatabase


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
            }
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
                source_entry = {
                    "tool": tool_name,
                    "parameters": kwargs,
                    "data": result
                }
                self.last_sources.append(source_entry)
            
            # Convert result to string for Claude
            import json
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    def _execute_custom_query(
        self, query: str, parameters: dict[str, Any] = None, explanation: str = None
    ) -> dict[str, Any]:
        """
        Execute a custom SQL query with safety checks.

        Args:
            query: SQL SELECT query to execute
            parameters: Optional parameters for parameterized queries
            explanation: Explanation of what the query does

        Returns:
            Query results as a dictionary
        """

        # Safety check: Only allow SELECT statements (including WITH CTEs)
        query_upper = query.strip().upper()
        if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
            # Query validation failed - not a SELECT or WITH statement
            return {
                "error": "Only SELECT queries (including WITH clauses) are allowed for safety",
                "query": query,
            }

        # Prevent potentially dangerous operations
        dangerous_keywords = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
        ]
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {
                    "error": f"Query contains forbidden keyword: {keyword}",
                    "query": query,
                }

        try:
            # Execute the query
            if parameters:
                # Use parameterized query if parameters provided
                results = self.db.execute_query(query, parameters)
            else:
                # Direct query execution
                results = self.db.execute_query(query)

            # Format numeric values - only show decimal when needed
            formatted_results = []
            for row in results:
                formatted_row = {}
                for key, value in row.items():
                    if isinstance(value, float):
                        # For percentages and efficiency metrics, use more precision
                        if (
                            "percentage" in key.lower()
                            or "per_" in key.lower()
                            or "efficiency" in key.lower()
                        ):
                            rounded = round(value, 3) if value < 1 else round(value, 1)
                            # Only show decimal if needed
                            formatted_row[key] = (
                                int(rounded) if rounded == int(rounded) else rounded
                            )
                        else:
                            # Round to 1 decimal place
                            rounded = round(value, 1)
                            # Only show decimal if the value actually has a fractional part
                            formatted_row[key] = (
                                int(rounded) if rounded == int(rounded) else rounded
                            )
                    else:
                        formatted_row[key] = value
                formatted_results.append(formatted_row)

            # Limit results if too many rows
            max_rows = 100
            if len(formatted_results) > max_rows:
                formatted_results = formatted_results[:max_rows]
                return {
                    "explanation": explanation or "Custom query results",
                    "query": query,
                    "parameters": parameters,
                    "results": formatted_results,
                    "row_count": len(formatted_results),
                    "note": f"Results limited to first {max_rows} rows",
                }

            return {
                "explanation": explanation or "Custom query results",
                "query": query,
                "parameters": parameters,
                "results": formatted_results,
                "row_count": len(formatted_results),
            }

        except Exception as e:
            return {
                "error": f"Query execution failed: {str(e)}",
                "query": query,
                "parameters": parameters,
                "explanation": explanation,
            }

    def _get_player_stats(
        self,
        player_name: str,
        season: str = None,
        stat_type: str = "season",
        game_date: str = None,
    ) -> dict[str, Any]:
        """Get player statistics."""
        # Find player
        player_query = """
        SELECT p.*, t.name as team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id
        WHERE LOWER(p.full_name) LIKE LOWER(:name)
        LIMIT 1
        """
        player_results = self.db.execute_query(
            player_query, {"name": f"%{player_name}%"}
        )

        if not player_results:
            return {"error": f"Player '{player_name}' not found"}

        player = player_results[0]

        if stat_type == "season":
            # Get season stats
            if not season:
                season_query = (
                    "SELECT MAX(year) as current_year FROM player_season_stats"
                )
                season_result = self.db.execute_query(season_query)
                season = (
                    season_result[0]["current_year"]
                    if season_result and season_result[0]["current_year"]
                    else 2025
                )

            stats_query = """
            SELECT pss.*, t.name as team_name
            FROM player_season_stats pss
            JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            WHERE pss.player_id = :player_id AND pss.year = :season
            """
            stats = self.db.execute_query(
                stats_query, {"player_id": player["player_id"], "season": season}
            )

            if stats:
                return {"player": player, "season_stats": stats[0], "season": season}
            else:
                return {
                    "player": player,
                    "message": f"No stats found for {player['full_name']} in season {season}",
                }

        elif stat_type == "game":
            # Get game stats
            game_query = """
            SELECT pgs.*, g.start_timestamp, g.home_score, g.away_score,
                   ht.name as home_team, at.name as away_team
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
            JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
            WHERE pgs.player_id = :player_id
            """
            params = {"player_id": player["player_id"]}

            if game_date:
                game_query += " AND DATE(g.start_timestamp) = :game_date"
                params["game_date"] = game_date
            else:
                game_query += " ORDER BY g.start_timestamp DESC LIMIT 10"

            games = self.db.execute_query(game_query, params)

            return {"player": player, "game_stats": games}

        elif stat_type == "career":
            # Get career totals
            career_query = """
            SELECT
                COUNT(DISTINCT year) as seasons_played,
                SUM(total_goals) as career_goals,
                SUM(total_assists) as career_assists,
                SUM(total_blocks) as career_blocks,
                SUM(total_throwaways) as career_throwaways,
                SUM(total_catches) as career_catches,
                SUM(total_completions) as career_completions
            FROM player_season_stats
            WHERE player_id = :player_id
            """
            career = self.db.execute_query(
                career_query, {"player_id": player["player_id"]}
            )

            return {"player": player, "career_stats": career[0] if career else {}}

        return {"error": f"Invalid stat_type: {stat_type}"}

    def _get_team_stats(
        self, team_name: str, season: str = None, include_roster: bool = False
    ) -> dict[str, Any]:
        """Get team statistics."""
        # Find team
        team_query = """
        SELECT * FROM teams
        WHERE LOWER(name) LIKE LOWER(:name)
           OR LOWER(abbrev) = LOWER(:name)
        LIMIT 1
        """
        team_results = self.db.execute_query(team_query, {"name": f"%{team_name}%"})

        if not team_results:
            return {"error": f"Team '{team_name}' not found"}

        team = team_results[0]

        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(year) as current_year FROM team_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_year"] if season_result else 2025

        # Get team stats
        stats_query = """
        SELECT * FROM team_season_stats
        WHERE team_id = :team_id AND year = :season
        """
        stats = self.db.execute_query(
            stats_query, {"team_id": team["team_id"], "season": season}
        )

        # Get playoff history for accurate reporting
        playoff_query = """
        SELECT DISTINCT year, COUNT(*) as playoff_games,
               SUM(CASE
                   WHEN (home_team_id = :team_id AND home_score > away_score) OR
                        (away_team_id = :team_id AND away_score > home_score) THEN 1
                   ELSE 0
               END) as playoff_wins,
               SUM(CASE
                   WHEN (home_team_id = :team_id AND home_score < away_score) OR
                        (away_team_id = :team_id AND away_score < home_score) THEN 1
                   ELSE 0
               END) as playoff_losses
        FROM games
        WHERE game_type LIKE '%playoff%' AND (home_team_id = :team_id OR away_team_id = :team_id)
        GROUP BY year
        ORDER BY year DESC
        """
        playoff_history = self.db.execute_query(
            playoff_query, {"team_id": team["team_id"]}
        )

        # Get specific season playoff record if requested
        season_playoff_record = None
        if season:
            season_playoff_query = """
            SELECT COUNT(*) as playoff_games,
                   SUM(CASE
                       WHEN (home_team_id = :team_id AND home_score > away_score) OR
                            (away_team_id = :team_id AND away_score > home_score) THEN 1
                       ELSE 0
                   END) as playoff_wins,
                   SUM(CASE
                       WHEN (home_team_id = :team_id AND home_score < away_score) OR
                            (away_team_id = :team_id AND away_score < home_score) THEN 1
                       ELSE 0
                   END) as playoff_losses
            FROM games
            WHERE game_type LIKE '%playoff%' AND (home_team_id = :team_id OR away_team_id = :team_id) AND year = :season
            """
            season_playoff_result = self.db.execute_query(
                season_playoff_query, {"team_id": team["team_id"], "season": season}
            )
            if season_playoff_result and season_playoff_result[0]["playoff_games"] > 0:
                season_playoff_record = season_playoff_result[0]

        result = {
            "team": team,
            "season_stats": stats[0] if stats else {},
            "season": season,
            "playoff_history": playoff_history,
            "season_playoff_record": season_playoff_record,
        }

        if include_roster:
            roster_query = """
            SELECT p.*, pss.total_goals, pss.total_assists, pss.total_blocks
            FROM players p
            LEFT JOIN player_season_stats pss ON p.player_id = pss.player_id AND pss.year = :season
            WHERE p.team_id = :team_id AND p.active = 1 AND p.year = :season
            ORDER BY pss.total_goals DESC NULLS LAST
            """
            roster = self.db.execute_query(
                roster_query, {"team_id": team["team_id"], "season": season}
            )
            result["roster"] = roster

        return result

    def _get_game_results(
        self, date: str = None, team_name: str = None, include_stats: bool = False
    ) -> dict[str, Any]:
        """Get game results."""
        query = """
        SELECT g.*,
               ht.name as home_team_name, ht.abbrev as home_team_abbr,
               at.name as away_team_name, at.abbrev as away_team_abbr
        FROM games g
        JOIN teams ht ON LOWER(ht.abbrev) = g.home_team_id AND g.year = ht.year
        JOIN teams at ON LOWER(at.abbrev) = g.away_team_id AND g.year = at.year
        WHERE 1=1
        """
        params = {}

        if date:
            query += " AND DATE(g.start_timestamp) = :date"
            params["date"] = date

        if team_name:
            query += """ AND (LOWER(ht.name) LIKE LOWER(:team_name)
                         OR LOWER(at.name) LIKE LOWER(:team_name)
                         OR LOWER(ht.abbrev) = LOWER(:team_name)
                         OR LOWER(at.abbrev) = LOWER(:team_name))"""
            params["team_name"] = f"%{team_name}%"

        if not date and not team_name:
            query += " ORDER BY g.start_timestamp DESC LIMIT 10"
        else:
            query += " ORDER BY g.start_timestamp DESC"

        games = self.db.execute_query(query, params)

        result = {"games": games}

        if include_stats and games:
            # Get top performers for each game
            for game in games:
                stats_query = """
                SELECT p.full_name as name, pgs.goals, pgs.assists, pgs.blocks,
                       t.name as team_name
                FROM player_game_stats pgs
                JOIN players p ON pgs.player_id = p.player_id
                JOIN teams t ON pgs.team_id = t.team_id AND pgs.year = t.year
                WHERE pgs.game_id = :game_id
                ORDER BY pgs.goals DESC
                LIMIT 5
                """
                top_performers = self.db.execute_query(
                    stats_query, {"game_id": game["game_id"]}
                )
                game["top_performers"] = top_performers

        return result

    def _get_league_leaders(
        self, category: str, season: str = None, limit: int = 3
    ) -> dict[str, Any]:
        """Get league leaders in a statistical category."""
        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(year) as current_year FROM player_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_year"] if season_result else 2025

        # Special handling for plus_minus (from calculated field in season stats)
        if category == "plus_minus":
            # Use calculated_plus_minus from player_season_stats
            query = """
            SELECT p.full_name as name, t.name as team_name,
                   pss.calculated_plus_minus as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id
            JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            WHERE pss.year = :season AND pss.calculated_plus_minus IS NOT NULL
            ORDER BY value DESC
            LIMIT :limit
            """

            leaders = self.db.execute_query(query, {"season": season, "limit": limit})

            # If no results with season filter, try without season filter (for sample data)
            if not leaders:
                query = """
                SELECT p.full_name as name, t.name as team_name,
                       pss.calculated_plus_minus as value
                FROM player_season_stats pss
                JOIN players p ON pss.player_id = p.player_id
                JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
                WHERE pss.calculated_plus_minus IS NOT NULL
                ORDER BY value DESC
                LIMIT :limit
                """
                leaders = self.db.execute_query(query, {"limit": limit})

            return {
                "category": category,
                "season": season,
                "leaders": leaders,
                "note": "Plus/minus aggregated from individual games. For worst plus/minus, look at the bottom of the list or explicitly query for ascending order.",
            }

        # Map category to column (Ultimate Frisbee stats)
        category_map = {
            "goals": "total_goals",
            "assists": "total_assists",
            "blocks": "total_blocks",
            "throwaways": "total_throwaways",
            "catches": "total_catches",
            "completions": "total_completions",
            "total_goals": "total_goals",
            "total_assists": "total_assists",
            "total_blocks": "total_blocks",
            "total_throwaways": "total_throwaways",
            "total_catches": "total_catches",
            "total_completions": "total_completions",
            "completion_percentage": "completion_percentage",
        }

        if category not in category_map:
            return {"error": f"Invalid category: {category}"}

        column = category_map[category]

        # Query for Ultimate Frisbee stats
        query = f"""
        SELECT p.full_name as name, t.name as team_name, pss.{column} as value
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
        WHERE pss.year = :season AND pss.{column} IS NOT NULL
        ORDER BY pss.{column} DESC
        LIMIT :limit
        """

        leaders = self.db.execute_query(query, {"season": season, "limit": limit})

        return {"category": category, "season": season, "leaders": leaders}

    def _compare_players(
        self, player_names: list[str], season: str = None, categories: list[str] = None
    ) -> dict[str, Any]:
        """Compare multiple players."""
        if len(player_names) < 2 or len(player_names) > 5:
            return {"error": "Please provide 2-5 player names for comparison"}

        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(year) as current_year FROM player_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_year"] if season_result else 2025

        # Default categories if not specified (Ultimate Frisbee stats)
        if not categories:
            categories = [
                "total_goals",
                "total_assists",
                "total_blocks",
                "total_throwaways",
                "completion_percentage",
            ]

        comparison = []

        for player_name in player_names:
            # Find player
            player_query = """
            SELECT p.player_id, p.full_name, t.name as team_name
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.team_id AND p.year = t.year
            WHERE LOWER(p.full_name) LIKE LOWER(:name)
            LIMIT 1
            """
            player_results = self.db.execute_query(
                player_query, {"name": f"%{player_name}%"}
            )

            if player_results:
                player = player_results[0]

                # Get stats
                stats_query = """
                SELECT * FROM player_season_stats
                WHERE player_id = :player_id AND year = :season
                """
                stats = self.db.execute_query(
                    stats_query, {"player_id": player["player_id"], "season": season}
                )

                if stats:
                    player_data = {
                        "name": player["full_name"],
                        "team": player["team_name"],
                    }
                    for cat in categories:
                        if cat in stats[0]:
                            player_data[cat] = stats[0][cat]
                    comparison.append(player_data)

        return {"season": season, "categories": categories, "comparison": comparison}

    def _search_players(
        self, search_term: str = None, team_name: str = None, position: str = None
    ) -> dict[str, Any]:
        """Search for players."""
        query = """
        SELECT p.*, t.name as team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id AND p.year = t.year
        WHERE p.active = 1
        """
        params = {}

        if search_term:
            query += " AND LOWER(p.full_name) LIKE LOWER(:search_term)"
            params["search_term"] = f"%{search_term}%"

        if team_name:
            query += """ AND (LOWER(t.name) LIKE LOWER(:team_name)
                         OR LOWER(t.abbrev) = LOWER(:team_name))"""
            params["team_name"] = f"%{team_name}%"

        if position:
            query += " AND LOWER(p.position) = LOWER(:position)"
            params["position"] = position

        query += " ORDER BY p.full_name LIMIT 50"

        players = self.db.execute_query(query, params)

        return {"players": players, "count": len(players)}

    def _get_standings(
        self, season: str = None, conference: str = None, division: str = None
    ) -> dict[str, Any]:
        """Get league standings."""
        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(year) as current_year FROM team_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_year"] if season_result else 2025

        query = """
        SELECT t.name, t.abbrev as abbreviation, t.division_name as division,
               tss.wins, tss.losses, tss.standing
        FROM team_season_stats tss
        JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
        WHERE tss.year = :season
        """
        params = {"season": season}

        if division:
            query += " AND LOWER(t.division_name) = LOWER(:division)"
            params["division"] = division

        query += " ORDER BY tss.standing ASC"

        standings = self.db.execute_query(query, params)

        return {
            "season": season,
            "standings": standings,
            "filters": {"division": division},
        }

    def _get_worst_performers(
        self, category: str, season: str = None, limit: int = 10
    ) -> dict[str, Any]:
        """Get players with worst performance in a category."""
        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(year) as current_year FROM player_season_stats"
            season_result = self.db.execute_query(season_query)
            season = (
                season_result[0]["current_year"]
                if season_result and season_result[0]["current_year"]
                else 2025
            )

        if category == "plus_minus":
            # Get worst plus/minus (most negative calculated value)
            query = """
            SELECT p.full_name as name, t.name as team_name,
                   pss.calculated_plus_minus as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id
            JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            WHERE pss.year = :season AND pss.calculated_plus_minus IS NOT NULL
            ORDER BY value ASC
            LIMIT :limit
            """

            worst = self.db.execute_query(query, {"season": season, "limit": limit})

            # If no results with season filter, try without season filter (for sample data)
            if not worst:
                query = """
                SELECT p.full_name as name, t.name as team_name,
                       pss.calculated_plus_minus as value
                FROM player_season_stats pss
                JOIN players p ON pss.player_id = p.player_id
                JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
                WHERE pss.calculated_plus_minus IS NOT NULL
                ORDER BY value ASC
                LIMIT :limit
                """
                worst = self.db.execute_query(query, {"limit": limit})

            return {
                "category": f"worst_{category}",
                "season": season,
                "worst_performers": worst,
                "note": "Players with the worst (most negative) plus/minus",
            }

        elif category == "turnovers":
            # Get most turnovers (throwaways in Ultimate Frisbee)
            query = """
            SELECT p.full_name as name, t.name as team_name,
                   pss.total_throwaways as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id
            JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            WHERE pss.year = :season AND pss.total_throwaways IS NOT NULL
            ORDER BY pss.total_throwaways DESC
            LIMIT :limit
            """

            worst = self.db.execute_query(query, {"season": season, "limit": limit})

            return {
                "category": f"most_{category}",
                "season": season,
                "worst_performers": worst,
            }

        elif category == "completion_percentage":
            # Get worst completion percentage
            query = """
            SELECT p.full_name as name, t.name as team_name,
                   pss.completion_percentage as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id
            JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            WHERE pss.year = :season
                AND pss.completion_percentage IS NOT NULL
            ORDER BY pss.completion_percentage ASC
            LIMIT :limit
            """

            worst = self.db.execute_query(query, {"season": season, "limit": limit})

            return {
                "category": f"worst_{category}",
                "season": season,
                "worst_performers": worst,
            }

        return {"error": f"Invalid category: {category}"}

    def _get_game_details(self, game_id: str = None, date: str = None, teams: str = None) -> dict[str, Any]:
        """Get comprehensive game details similar to UFA game summary page."""
        
        # First, find the game
        game_query = """
        SELECT g.*,
               ht.name as home_team_name, ht.abbrev as home_team_abbr, ht.standing as home_standing,
               ht.team_id as home_full_team_id,
               at.name as away_team_name, at.abbrev as away_team_abbr, at.standing as away_standing,
               at.team_id as away_full_team_id
        FROM games g
        JOIN teams ht ON LOWER(ht.abbrev) = g.home_team_id AND g.year = ht.year
        JOIN teams at ON LOWER(at.abbrev) = g.away_team_id AND g.year = at.year
        WHERE 1=1
        """
        params = {}
        
        if game_id:
            game_query += " AND g.game_id = :game_id"
            params["game_id"] = game_id
        elif date and teams:
            game_query += " AND DATE(g.start_timestamp) = :date"
            game_query += """ AND (
                (LOWER(ht.abbrev) LIKE LOWER(:team1) AND LOWER(at.abbrev) LIKE LOWER(:team2))
                OR (LOWER(ht.abbrev) LIKE LOWER(:team2) AND LOWER(at.abbrev) LIKE LOWER(:team1))
            )"""
            params["date"] = date
            team_parts = teams.replace("-", " ").replace("vs", " ").replace("@", " ").split()
            if len(team_parts) >= 2:
                params["team1"] = f"%{team_parts[0]}%"
                params["team2"] = f"%{team_parts[1]}%"
        
        game = self.db.execute_query(game_query, params)
        if not game:
            return {"error": "Game not found"}
        
        game = game[0]
        game_id = game["game_id"]
        
        # Get individual leaders (top 1 per category per team)
        leaders = {}
        
        # Helper function to get top player for a stat
        def get_stat_leader(stat_column, stat_name):
            query = f"""
            SELECT p.full_name, pgs.{stat_column} as value, pgs.team_id,
                   t.name as team_name
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.player_id
            JOIN teams t ON pgs.team_id = t.team_id AND pgs.year = t.year
            WHERE pgs.game_id = :game_id
            AND pgs.team_id = :team_id
            AND pgs.{stat_column} > 0
            ORDER BY pgs.{stat_column} DESC
            LIMIT 1
            """
            
            home_leader = self.db.execute_query(query, {
                "game_id": game_id,
                "team_id": game["home_full_team_id"]
            })
            
            away_leader = self.db.execute_query(query, {
                "game_id": game_id,
                "team_id": game["away_full_team_id"]
            })
            
            return {
                "home": home_leader[0] if home_leader else None,
                "away": away_leader[0] if away_leader else None
            }
        
        # Get leaders for each category
        leaders["assists"] = get_stat_leader("assists", "Assists")
        leaders["goals"] = get_stat_leader("goals", "Goals")
        leaders["blocks"] = get_stat_leader("blocks", "Blocks")
        leaders["completions"] = get_stat_leader("completions", "Completions")
        leaders["points_played"] = get_stat_leader("o_points_played + d_points_played", "Points Played")
        
        # Plus/minus requires special handling
        pm_query = """
        SELECT p.full_name, 
               (pgs.goals + pgs.assists + pgs.blocks - pgs.throwaways - pgs.stalls - pgs.drops) as value,
               pgs.team_id, t.name as team_name
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.player_id
        JOIN teams t ON pgs.team_id = t.team_id AND pgs.year = t.year
        WHERE pgs.game_id = :game_id
        AND pgs.team_id = :team_id
        ORDER BY value DESC
        LIMIT 1
        """
        
        home_pm = self.db.execute_query(pm_query, {
            "game_id": game_id,
            "team_id": game["home_full_team_id"]
        })
        
        away_pm = self.db.execute_query(pm_query, {
            "game_id": game_id,
            "team_id": game["away_full_team_id"]
        })
        
        leaders["plus_minus"] = {
            "home": home_pm[0] if home_pm else None,
            "away": away_pm[0] if away_pm else None
        }
        
        # Get team statistics
        team_stats_query = """
        SELECT 
            team_id,
            SUM(completions) as total_completions,
            SUM(throw_attempts) as total_attempts,
            SUM(hucks_completed) as total_hucks_completed,
            SUM(hucks_attempted) as total_hucks_attempted,
            SUM(blocks) as total_blocks,
            SUM(throwaways + stalls + drops) as total_turnovers,
            SUM(o_points_played) as total_o_points,
            SUM(o_points_scored) as total_o_scores,
            SUM(d_points_played) as total_d_points,
            SUM(d_points_scored) as total_d_scores
        FROM player_game_stats
        WHERE game_id = :game_id
        GROUP BY team_id
        """
        
        team_stats = self.db.execute_query(team_stats_query, {"game_id": game_id})
        
        # Organize team stats by team
        home_stats = None
        away_stats = None
        for stat in team_stats:
            if stat["team_id"] == game["home_full_team_id"]:
                home_stats = stat
            elif stat["team_id"] == game["away_full_team_id"]:
                away_stats = stat
        
        # Calculate percentages
        def calculate_percentages(stats):
            if stats:
                stats["completion_percentage"] = round(stats["total_completions"] / stats["total_attempts"] * 100, 1) if stats["total_attempts"] > 0 else 0
                stats["huck_percentage"] = round(stats["total_hucks_completed"] / stats["total_hucks_attempted"] * 100, 1) if stats["total_hucks_attempted"] > 0 else 0
                stats["hold_percentage"] = round(stats["total_o_scores"] / stats["total_o_points"] * 100, 1) if stats["total_o_points"] > 0 else 0
                stats["break_percentage"] = round(stats["total_d_scores"] / stats["total_d_points"] * 100, 1) if stats["total_d_points"] > 0 else 0
                stats["o_conversion"] = round(stats["total_o_scores"] / stats["total_o_points"] * 100, 1) if stats["total_o_points"] > 0 else 0
                stats["d_conversion"] = round((1 - stats["total_d_scores"] / stats["total_d_points"]) * 100, 1) if stats["total_d_points"] > 0 else 0
            return stats
        
        home_stats = calculate_percentages(home_stats)
        away_stats = calculate_percentages(away_stats)
        
        return {
            "game": game,
            "individual_leaders": leaders,
            "team_statistics": {
                "home": home_stats,
                "away": away_stats
            }
        }

    def get_last_sources(self) -> list[str]:
        """Get the last sources used in tool execution."""
        return self.last_sources

    def reset_sources(self):
        """Reset the sources list."""
        self.last_sources = []
