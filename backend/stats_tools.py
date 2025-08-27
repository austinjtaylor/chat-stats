"""
Sports statistics tools for Claude AI function calling.
Defines tools that Claude can use to query the SQL database for sports statistics.
"""

from typing import Dict, List, Any, Optional
from sql_database import SQLDatabase
from sqlalchemy import text
import json


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
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Get all tool definitions for Claude.
        
        Returns:
            List of tool definition dictionaries
        """
        # Generic SQL executor tool for maximum flexibility
        return [
            {
                "name": "execute_custom_query",
                "description": "Execute custom SQL query to retrieve any sports statistics data. Use this for complex queries involving multiple tables, aggregations, or specific filtering criteria.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL SELECT query to execute. Must be a SELECT statement only."
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Optional parameters for the query as key-value pairs (e.g., {'season': '2023', 'limit': 10})"
                        },
                        "explanation": {
                            "type": "string",
                            "description": "Brief explanation of what this query retrieves and why"
                        }
                    },
                    "required": ["query", "explanation"]
                }
            }
        ]
        
        # Specialized tools (temporarily disabled for testing generic SQL)
        return_disabled = [
            {
                "name": "get_player_stats",
                "description": "Retrieve player statistics for a specific player, including season averages, game logs, or career totals",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "player_name": {
                            "type": "string",
                            "description": "The name of the player (partial match supported)"
                        },
                        "season": {
                            "type": "string",
                            "description": "Optional season (e.g., '2023-24'). If not specified, returns current season"
                        },
                        "stat_type": {
                            "type": "string",
                            "enum": ["season", "game", "career"],
                            "description": "Type of statistics to retrieve (default: season)"
                        },
                        "game_date": {
                            "type": "string",
                            "description": "Optional specific game date in YYYY-MM-DD format"
                        }
                    },
                    "required": ["player_name"]
                }
            },
            {
                "name": "get_team_stats",
                "description": "Retrieve team statistics, standings, and performance metrics",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "team_name": {
                            "type": "string",
                            "description": "The name or abbreviation of the team"
                        },
                        "season": {
                            "type": "string",
                            "description": "Optional season (e.g., '2023-24'). If not specified, returns current season"
                        },
                        "include_roster": {
                            "type": "boolean",
                            "description": "Include team roster in the response (default: false)"
                        }
                    },
                    "required": ["team_name"]
                }
            },
            {
                "name": "get_game_results",
                "description": "Get game scores, box scores, and detailed game information",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Game date in YYYY-MM-DD format"
                        },
                        "team_name": {
                            "type": "string",
                            "description": "Optional team name to filter games"
                        },
                        "include_stats": {
                            "type": "boolean",
                            "description": "Include player statistics for the games (default: false)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_league_leaders",
                "description": "Get league leaders in various statistical categories",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["points", "assists", "rebounds", "goals", "blocks", "steals", "field_goal_percentage", "three_point_percentage", "plus_minus", "total_assists", "total_goals", "total_points"],
                            "description": "Statistical category to rank by (use 'total_' prefix for season totals instead of per-game averages)"
                        },
                        "season": {
                            "type": "string",
                            "description": "Optional season (e.g., '2023-24'). If not specified, returns current season"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top players to return (default: 10)"
                        }
                    },
                    "required": ["category"]
                }
            },
            {
                "name": "compare_players",
                "description": "Compare statistics between two or more players",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "player_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of player names to compare (2-5 players)"
                        },
                        "season": {
                            "type": "string",
                            "description": "Optional season for comparison. If not specified, uses current season"
                        },
                        "categories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional specific stat categories to compare. If not specified, shows main stats"
                        }
                    },
                    "required": ["player_names"]
                }
            },
            {
                "name": "search_players",
                "description": "Search for players by name, team, or position",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "Search term for player name (partial match)"
                        },
                        "team_name": {
                            "type": "string",
                            "description": "Optional team name to filter by"
                        },
                        "position": {
                            "type": "string",
                            "description": "Optional position to filter by"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_standings",
                "description": "Get current league standings and playoff picture",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "season": {
                            "type": "string",
                            "description": "Optional season (e.g., '2023-24'). If not specified, returns current season"
                        },
                        "conference": {
                            "type": "string",
                            "description": "Optional conference filter (e.g., 'Eastern', 'Western')"
                        },
                        "division": {
                            "type": "string",
                            "description": "Optional division filter"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_worst_performers",
                "description": "Get players with the worst performance in various statistical categories (e.g., worst plus/minus, most turnovers)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": ["plus_minus", "turnovers", "field_goal_percentage"],
                            "description": "Statistical category to find worst performers"
                        },
                        "season": {
                            "type": "string",
                            "description": "Optional season (e.g., '2023'). If not specified, returns current season"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of worst performers to return (default: 10)"
                        }
                    },
                    "required": ["category"]
                }
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
            "get_league_leaders": self._get_league_leaders,
            "compare_players": self._compare_players,
            "search_players": self._search_players,
            "get_standings": self._get_standings,
            "get_worst_performers": self._get_worst_performers
        }
        
        if tool_name not in tool_methods:
            return f"Error: Unknown tool '{tool_name}'"
        
        try:
            result = tool_methods[tool_name](**kwargs)
            # Store sources for later retrieval
            if isinstance(result, dict) and "sources" in result:
                self.last_sources = result["sources"]
            # Convert result to string for Claude
            import json
            return json.dumps(result, indent=2, default=str)
        except Exception as e:
            return f"Error executing tool: {str(e)}"
    
    def _execute_custom_query(self, query: str, parameters: Dict[str, Any] = None,
                            explanation: str = None) -> Dict[str, Any]:
        """
        Execute a custom SQL query with safety checks.
        
        Args:
            query: SQL SELECT query to execute
            parameters: Optional parameters for parameterized queries
            explanation: Explanation of what the query does
            
        Returns:
            Query results as a dictionary
        """
        # Safety check: Only allow SELECT statements
        query_upper = query.strip().upper()
        if not query_upper.startswith('SELECT'):
            return {
                "error": "Only SELECT queries are allowed for safety",
                "query": query
            }
        
        # Prevent potentially dangerous operations
        dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {
                    "error": f"Query contains forbidden keyword: {keyword}",
                    "query": query
                }
        
        try:
            # Execute the query
            if parameters:
                # Use parameterized query if parameters provided
                results = self.db.execute_query(query, parameters)
            else:
                # Direct query execution
                results = self.db.execute_query(query)
            
            # Limit results if too many rows
            max_rows = 100
            if len(results) > max_rows:
                results = results[:max_rows]
                return {
                    "explanation": explanation or "Custom query results",
                    "query": query,
                    "parameters": parameters,
                    "results": results,
                    "row_count": len(results),
                    "note": f"Results limited to first {max_rows} rows"
                }
            
            return {
                "explanation": explanation or "Custom query results",
                "query": query,
                "parameters": parameters,
                "results": results,
                "row_count": len(results)
            }
            
        except Exception as e:
            return {
                "error": f"Query execution failed: {str(e)}",
                "query": query,
                "parameters": parameters,
                "explanation": explanation
            }
    
    def _get_player_stats(self, player_name: str, season: str = None, 
                         stat_type: str = "season", game_date: str = None) -> Dict[str, Any]:
        """Get player statistics."""
        # Find player
        player_query = """
        SELECT p.*, t.name as team_name 
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE LOWER(p.name) LIKE LOWER(:name)
        LIMIT 1
        """
        player_results = self.db.execute_query(player_query, {"name": f"%{player_name}%"})
        
        if not player_results:
            return {"error": f"Player '{player_name}' not found"}
        
        player = player_results[0]
        
        if stat_type == "season":
            # Get season stats
            if not season:
                season_query = "SELECT MAX(season) as current_season FROM player_season_stats"
                season_result = self.db.execute_query(season_query)
                season = season_result[0]["current_season"] if season_result and season_result[0]["current_season"] else "2025"
            
            stats_query = """
            SELECT pss.*, t.name as team_name
            FROM player_season_stats pss
            JOIN teams t ON pss.team_id = t.id
            WHERE pss.player_id = :player_id AND pss.season = :season
            """
            stats = self.db.execute_query(stats_query, 
                                         {"player_id": player["id"], "season": season})
            
            if stats:
                return {
                    "player": player,
                    "season_stats": stats[0],
                    "season": season
                }
            else:
                return {
                    "player": player,
                    "message": f"No stats found for {player['name']} in season {season}"
                }
        
        elif stat_type == "game":
            # Get game stats
            game_query = """
            SELECT pgs.*, g.game_date, g.home_score, g.away_score,
                   ht.name as home_team, at.name as away_team
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.id
            JOIN teams ht ON g.home_team_id = ht.id
            JOIN teams at ON g.away_team_id = at.id
            WHERE pgs.player_id = :player_id
            """
            params = {"player_id": player["id"]}
            
            if game_date:
                game_query += " AND g.game_date = :game_date"
                params["game_date"] = game_date
            else:
                game_query += " ORDER BY g.game_date DESC LIMIT 10"
            
            games = self.db.execute_query(game_query, params)
            
            return {
                "player": player,
                "game_stats": games
            }
        
        elif stat_type == "career":
            # Get career totals
            career_query = """
            SELECT 
                COUNT(DISTINCT season) as seasons_played,
                SUM(games_played) as total_games,
                SUM(total_points) as career_points,
                SUM(total_assists) as career_assists,
                SUM(total_rebounds) as career_rebounds,
                AVG(avg_points_per_game) as career_ppg,
                AVG(avg_assists_per_game) as career_apg,
                AVG(avg_rebounds_per_game) as career_rpg
            FROM player_season_stats
            WHERE player_id = :player_id
            """
            career = self.db.execute_query(career_query, {"player_id": player["id"]})
            
            return {
                "player": player,
                "career_stats": career[0] if career else {}
            }
        
        return {"error": f"Invalid stat_type: {stat_type}"}
    
    def _get_team_stats(self, team_name: str, season: str = None, 
                       include_roster: bool = False) -> Dict[str, Any]:
        """Get team statistics."""
        # Find team
        team_query = """
        SELECT * FROM teams
        WHERE LOWER(name) LIKE LOWER(:name) 
           OR LOWER(abbreviation) = LOWER(:name)
        LIMIT 1
        """
        team_results = self.db.execute_query(team_query, {"name": f"%{team_name}%"})
        
        if not team_results:
            return {"error": f"Team '{team_name}' not found"}
        
        team = team_results[0]
        
        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(season) as current_season FROM team_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_season"] if season_result else "2023-24"
        
        # Get team stats
        stats_query = """
        SELECT * FROM team_season_stats
        WHERE team_id = :team_id AND season = :season
        """
        stats = self.db.execute_query(stats_query, {"team_id": team["id"], "season": season})
        
        result = {
            "team": team,
            "season_stats": stats[0] if stats else {},
            "season": season
        }
        
        if include_roster:
            roster_query = """
            SELECT p.*, pss.avg_points_per_game, pss.avg_assists_per_game, pss.avg_rebounds_per_game
            FROM players p
            LEFT JOIN player_season_stats pss ON p.id = pss.player_id AND pss.season = :season
            WHERE p.team_id = :team_id AND p.status = 'active'
            ORDER BY pss.avg_points_per_game DESC NULLS LAST
            """
            roster = self.db.execute_query(roster_query, 
                                          {"team_id": team["id"], "season": season})
            result["roster"] = roster
        
        return result
    
    def _get_game_results(self, date: str = None, team_name: str = None, 
                         include_stats: bool = False) -> Dict[str, Any]:
        """Get game results."""
        query = """
        SELECT g.*, 
               ht.name as home_team_name, ht.abbreviation as home_team_abbr,
               at.name as away_team_name, at.abbreviation as away_team_abbr
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        WHERE 1=1
        """
        params = {}
        
        if date:
            query += " AND g.game_date = :date"
            params["date"] = date
        
        if team_name:
            query += """ AND (LOWER(ht.name) LIKE LOWER(:team_name) 
                         OR LOWER(at.name) LIKE LOWER(:team_name)
                         OR LOWER(ht.abbreviation) = LOWER(:team_name)
                         OR LOWER(at.abbreviation) = LOWER(:team_name))"""
            params["team_name"] = f"%{team_name}%"
        
        if not date and not team_name:
            query += " ORDER BY g.game_date DESC LIMIT 10"
        else:
            query += " ORDER BY g.game_date DESC"
        
        games = self.db.execute_query(query, params)
        
        result = {"games": games}
        
        if include_stats and games:
            # Get top performers for each game
            for game in games:
                stats_query = """
                SELECT p.name, pgs.points, pgs.assists, pgs.total_rebounds,
                       t.name as team_name
                FROM player_game_stats pgs
                JOIN players p ON pgs.player_id = p.id
                JOIN teams t ON pgs.team_id = t.id
                WHERE pgs.game_id = :game_id
                ORDER BY pgs.points DESC
                LIMIT 5
                """
                top_performers = self.db.execute_query(stats_query, {"game_id": game["id"]})
                game["top_performers"] = top_performers
        
        return result
    
    def _get_league_leaders(self, category: str, season: str = None, 
                           limit: int = 10) -> Dict[str, Any]:
        """Get league leaders in a statistical category."""
        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(season) as current_season FROM player_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_season"] if season_result else "2023-24"
        
        # Special handling for plus_minus (aggregate from game stats)
        if category == "plus_minus":
            # Try with games join first
            query = """
            SELECT p.name, t.name as team_name, 
                   COUNT(pgs.id) as games_played,
                   SUM(pgs.plus_minus) as value
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            JOIN games g ON pgs.game_id = g.id
            WHERE g.season = :season AND pgs.plus_minus IS NOT NULL
            GROUP BY p.id, p.name, t.name
            ORDER BY value DESC
            LIMIT :limit
            """
            
            leaders = self.db.execute_query(query, {"season": season, "limit": limit})
            
            # If no results with season filter, try without season filter (for sample data)
            if not leaders:
                query = """
                SELECT p.name, t.name as team_name, 
                       COUNT(pgs.id) as games_played,
                       SUM(pgs.plus_minus) as value
                FROM player_game_stats pgs
                JOIN players p ON pgs.player_id = p.id
                JOIN teams t ON p.team_id = t.id
                WHERE pgs.plus_minus IS NOT NULL
                GROUP BY p.id, p.name, t.name
                ORDER BY value DESC
                LIMIT :limit
                """
                leaders = self.db.execute_query(query, {"limit": limit})
            
            return {
                "category": category,
                "season": season,
                "leaders": leaders,
                "note": "Plus/minus aggregated from individual games. For worst plus/minus, look at the bottom of the list or explicitly query for ascending order."
            }
        
        # Map category to column
        category_map = {
            "points": "avg_points_per_game",
            "assists": "avg_assists_per_game",
            "rebounds": "avg_rebounds_per_game",
            "goals": "total_goals",
            "blocks": "total_blocks",
            "steals": "total_steals",
            "total_assists": "total_assists",
            "total_goals": "total_goals",
            "total_points": "total_points",
            "field_goal_percentage": "field_goal_percentage",
            "three_point_percentage": "three_point_percentage"
        }
        
        if category not in category_map:
            return {"error": f"Invalid category: {category}"}
        
        column = category_map[category]
        
        # For total stats, include games_played for context
        if category.startswith("total_"):
            query = f"""
            SELECT p.name, t.name as team_name, pss.games_played, pss.{column} as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.id
            JOIN teams t ON pss.team_id = t.id
            WHERE pss.season = :season AND pss.{column} IS NOT NULL
            ORDER BY pss.{column} DESC
            LIMIT :limit
            """
        else:
            query = f"""
            SELECT p.name, t.name as team_name, pss.games_played, pss.{column} as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.id
            JOIN teams t ON pss.team_id = t.id
            WHERE pss.season = :season AND pss.{column} IS NOT NULL AND pss.games_played > 0
            ORDER BY pss.{column} DESC
            LIMIT :limit
            """
        
        leaders = self.db.execute_query(query, {"season": season, "limit": limit})
        
        return {
            "category": category,
            "season": season,
            "leaders": leaders
        }
    
    def _compare_players(self, player_names: List[str], season: str = None, 
                        categories: List[str] = None) -> Dict[str, Any]:
        """Compare multiple players."""
        if len(player_names) < 2 or len(player_names) > 5:
            return {"error": "Please provide 2-5 player names for comparison"}
        
        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(season) as current_season FROM player_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_season"] if season_result else "2023-24"
        
        # Default categories if not specified
        if not categories:
            categories = ["avg_points_per_game", "avg_assists_per_game", "avg_rebounds_per_game",
                         "field_goal_percentage", "three_point_percentage"]
        
        comparison = []
        
        for player_name in player_names:
            # Find player
            player_query = """
            SELECT p.id, p.name, t.name as team_name
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE LOWER(p.name) LIKE LOWER(:name)
            LIMIT 1
            """
            player_results = self.db.execute_query(player_query, {"name": f"%{player_name}%"})
            
            if player_results:
                player = player_results[0]
                
                # Get stats
                stats_query = """
                SELECT * FROM player_season_stats
                WHERE player_id = :player_id AND season = :season
                """
                stats = self.db.execute_query(stats_query, 
                                             {"player_id": player["id"], "season": season})
                
                if stats:
                    player_data = {
                        "name": player["name"],
                        "team": player["team_name"]
                    }
                    for cat in categories:
                        if cat in stats[0]:
                            player_data[cat] = stats[0][cat]
                    comparison.append(player_data)
        
        return {
            "season": season,
            "categories": categories,
            "comparison": comparison
        }
    
    def _search_players(self, search_term: str = None, team_name: str = None, 
                       position: str = None) -> Dict[str, Any]:
        """Search for players."""
        query = """
        SELECT p.*, t.name as team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE p.status = 'active'
        """
        params = {}
        
        if search_term:
            query += " AND LOWER(p.name) LIKE LOWER(:search_term)"
            params["search_term"] = f"%{search_term}%"
        
        if team_name:
            query += """ AND (LOWER(t.name) LIKE LOWER(:team_name) 
                         OR LOWER(t.abbreviation) = LOWER(:team_name))"""
            params["team_name"] = f"%{team_name}%"
        
        if position:
            query += " AND LOWER(p.position) = LOWER(:position)"
            params["position"] = position
        
        query += " ORDER BY p.name LIMIT 50"
        
        players = self.db.execute_query(query, params)
        
        return {"players": players, "count": len(players)}
    
    def _get_standings(self, season: str = None, conference: str = None, 
                      division: str = None) -> Dict[str, Any]:
        """Get league standings."""
        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(season) as current_season FROM team_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_season"] if season_result else "2023-24"
        
        query = """
        SELECT t.name, t.abbreviation, t.conference, t.division,
               tss.wins, tss.losses, tss.win_percentage, tss.playoff_seed,
               tss.points_for, tss.points_against
        FROM team_season_stats tss
        JOIN teams t ON tss.team_id = t.id
        WHERE tss.season = :season
        """
        params = {"season": season}
        
        if conference:
            query += " AND LOWER(t.conference) = LOWER(:conference)"
            params["conference"] = conference
        
        if division:
            query += " AND LOWER(t.division) = LOWER(:division)"
            params["division"] = division
        
        query += " ORDER BY tss.win_percentage DESC, tss.wins DESC"
        
        standings = self.db.execute_query(query, params)
        
        return {
            "season": season,
            "standings": standings,
            "filters": {
                "conference": conference,
                "division": division
            }
        }
    
    def _get_worst_performers(self, category: str, season: str = None,
                             limit: int = 10) -> Dict[str, Any]:
        """Get players with worst performance in a category."""
        # Get season if not provided
        if not season:
            season_query = "SELECT MAX(season) as current_season FROM player_season_stats"
            season_result = self.db.execute_query(season_query)
            season = season_result[0]["current_season"] if season_result and season_result[0]["current_season"] else "2025"
        
        if category == "plus_minus":
            # Get worst plus/minus (most negative)
            # Try with games join first
            query = """
            SELECT p.name, t.name as team_name, 
                   COUNT(pgs.id) as games_played,
                   SUM(pgs.plus_minus) as value
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.id
            JOIN teams t ON p.team_id = t.id
            JOIN games g ON pgs.game_id = g.id
            WHERE g.season = :season AND pgs.plus_minus IS NOT NULL
            GROUP BY p.id, p.name, t.name
            ORDER BY value ASC
            LIMIT :limit
            """
            
            worst = self.db.execute_query(query, {"season": season, "limit": limit})
            
            # If no results with season filter, try without season filter (for sample data)
            if not worst:
                query = """
                SELECT p.name, t.name as team_name, 
                       COUNT(pgs.id) as games_played,
                       SUM(pgs.plus_minus) as value
                FROM player_game_stats pgs
                JOIN players p ON pgs.player_id = p.id
                JOIN teams t ON p.team_id = t.id
                WHERE pgs.plus_minus IS NOT NULL
                GROUP BY p.id, p.name, t.name
                ORDER BY value ASC
                LIMIT :limit
                """
                worst = self.db.execute_query(query, {"limit": limit})
            
            return {
                "category": f"worst_{category}",
                "season": season,
                "worst_performers": worst,
                "note": "Players with the worst (most negative) plus/minus"
            }
        
        elif category == "turnovers":
            # Get most turnovers
            query = """
            SELECT p.name, t.name as team_name,
                   pss.games_played, pss.total_turnovers as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.id
            JOIN teams t ON pss.team_id = t.id
            WHERE pss.season = :season AND pss.total_turnovers IS NOT NULL
            ORDER BY pss.total_turnovers DESC
            LIMIT :limit
            """
            
            worst = self.db.execute_query(query, {"season": season, "limit": limit})
            
            return {
                "category": f"most_{category}",
                "season": season,
                "worst_performers": worst
            }
        
        elif category == "field_goal_percentage":
            # Get worst field goal percentage (minimum games played)
            query = """
            SELECT p.name, t.name as team_name,
                   pss.games_played, pss.field_goal_percentage as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.id
            JOIN teams t ON pss.team_id = t.id
            WHERE pss.season = :season 
                AND pss.field_goal_percentage IS NOT NULL
                AND pss.games_played >= 5
            ORDER BY pss.field_goal_percentage ASC
            LIMIT :limit
            """
            
            worst = self.db.execute_query(query, {"season": season, "limit": limit})
            
            return {
                "category": f"worst_{category}",
                "season": season,
                "worst_performers": worst,
                "note": "Minimum 5 games played"
            }
        
        return {"error": f"Invalid category: {category}"}
    
    def get_last_sources(self) -> List[str]:
        """Get the last sources used in tool execution."""
        return self.last_sources
    
    def reset_sources(self):
        """Reset the sources list."""
        self.last_sources = []