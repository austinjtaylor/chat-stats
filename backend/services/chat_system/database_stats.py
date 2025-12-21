"""
Database statistics and health check service.
"""

import datetime
from typing import Any

from data.cache import cache_key_for_endpoint, get_cache


class DatabaseStatsService:
    """Service for database statistics, health checks, and analytics."""

    def __init__(self, db, config):
        """
        Initialize the database stats service.

        Args:
            db: Database instance
            config: Configuration object
        """
        self.db = db
        self.config = config

    def get_stats_summary(self) -> dict[str, Any]:
        """
        Get a summary of available statistics in the database.

        Returns:
            Dictionary with counts and summary information
        """
        # Check cache first if enabled
        cache = get_cache() if self.config.ENABLE_CACHE else None
        cache_key = cache_key_for_endpoint("stats_summary")

        if cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        summary = {
            "total_players": self.db.get_row_count("players"),
            "total_teams": self.db.get_row_count("teams"),
            "total_games": self.db.get_row_count("games"),
            "total_player_stats": self.db.get_row_count("player_game_stats"),
            "seasons": [],
            "team_standings": [],
        }

        # Get available seasons/years (UFA schema, excluding All Star games)
        seasons_query = """
        SELECT DISTINCT year
        FROM games
        WHERE game_type != 'allstar'
          AND LOWER(game_id) NOT LIKE '%allstar%'
          AND LOWER(home_team_id) NOT LIKE '%allstar%'
          AND LOWER(away_team_id) NOT LIKE '%allstar%'
        ORDER BY year DESC
        """
        try:
            seasons_result = self.db.execute_query(seasons_query)
            summary["seasons"] = [str(row["year"]) for row in seasons_result]
        except Exception as e:
            print(f"Could not get seasons: {e}")
            summary["seasons"] = []

        # Get team standings (UFA schema) - Show all teams from all years
        if summary["seasons"]:
            # Get most recent year for determining "current" teams
            current_year = int(summary["seasons"][0]) if summary["seasons"] else 2025

            # Get all teams with their standings from all years - simplified approach
            all_teams_query = """
            WITH team_years AS (
                -- Get each team's most recent year (excluding All Stars)
                SELECT
                    team_id,
                    name,
                    MAX(full_name) as full_name,
                    MAX(year) as last_year
                FROM teams
                WHERE LOWER(team_id) NOT LIKE '%allstar%'
                  AND LOWER(name) NOT LIKE '%all%star%'
                GROUP BY team_id, name
            ),
            team_list AS (
                SELECT
                    ty.team_id,
                    ty.name,
                    ty.full_name,
                    ty.last_year,
                    CASE WHEN ty.last_year = :current_year THEN 1 ELSE 0 END as is_current,
                    -- Get stats from team_season_stats first, then fallback to teams table
                    COALESCE(tss.wins, t.wins, 0) as wins,
                    COALESCE(tss.losses, t.losses, 0) as losses,
                    COALESCE(tss.ties, t.ties, 0) as ties,
                    COALESCE(tss.standing, t.standing, 999) as standing
                FROM team_years ty
                LEFT JOIN team_season_stats tss ON ty.team_id = tss.team_id AND ty.last_year = tss.year
                LEFT JOIN teams t ON ty.team_id = t.team_id AND ty.last_year = t.year
            )
            SELECT
                team_id,
                name,
                full_name,
                last_year,
                is_current,
                wins,
                losses,
                ties,
                standing
            FROM team_list
            ORDER BY
                is_current DESC,  -- Current teams first
                CASE WHEN is_current = 1 THEN name ELSE NULL END ASC,  -- Current teams alphabetically
                CASE WHEN is_current = 0 THEN last_year ELSE NULL END DESC,  -- Historical teams by most recent year
                name ASC  -- Then alphabetically within same year
            """

            try:
                teams = self.db.execute_query(
                    all_teams_query, {"current_year": current_year}
                )

                # Format teams for API response
                summary["team_standings"] = [
                    {
                        "team_id": team["team_id"],
                        "name": team["name"],
                        "full_name": team["full_name"] or team["name"],
                        "is_current": bool(team["is_current"]),
                        "last_year": team["last_year"],
                        "wins": team["wins"] if team["is_current"] else None,
                        "losses": team["losses"] if team["is_current"] else None,
                        "ties": team["ties"] if team["is_current"] else None,
                        "standing": (
                            team["standing"]
                            if team["is_current"] and team["standing"] != 999
                            else None
                        ),
                    }
                    for team in teams
                ]
            except Exception as e:
                print(f"Could not get teams: {e}")
                summary["team_standings"] = []

        # Cache the result if caching is enabled
        if cache:
            cache.set(cache_key, summary, ttl=300)  # 5 minutes TTL

        return summary

    def get_database_stats(self) -> dict[str, Any]:
        """
        Get comprehensive database statistics.

        Returns:
            Dictionary with database statistics and counts
        """
        # Check cache first if enabled
        cache = get_cache() if self.config.ENABLE_CACHE else None
        cache_key = cache_key_for_endpoint("database_stats")

        if cache:
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        try:
            # Get basic counts
            total_players_query = "SELECT COUNT(*) as count FROM players"
            total_teams_query = "SELECT COUNT(*) as count FROM teams"
            total_games_query = "SELECT COUNT(*) as count FROM games"

            players_result = self.db.execute_query(total_players_query)
            teams_result = self.db.execute_query(total_teams_query)
            games_result = self.db.execute_query(total_games_query)

            # Get top scorers (goals + assists for total offensive contribution)
            top_scorers_query = """
            SELECT p.full_name as player_name,
                   SUM(pss.total_goals + pss.total_assists) as total_scores
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id
            GROUP BY p.player_id, p.full_name
            ORDER BY total_scores DESC
            LIMIT 5
            """
            top_scorers_result = self.db.execute_query(top_scorers_query)

            result = {
                "total_players": players_result[0]["count"],
                "total_teams": teams_result[0]["count"],
                "total_games": games_result[0]["count"],
                "top_scorers": top_scorers_result,
            }

            # Cache the result if caching is enabled
            if cache:
                cache.set(cache_key, result, ttl=300)  # 5 minutes TTL

            return result
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {
                "total_players": 0,
                "total_teams": 0,
                "total_games": 0,
                "top_scorers": [],
            }

    def get_database_info(self) -> dict[str, list[str]]:
        """
        Get information about database tables and columns.

        Returns:
            Dictionary mapping table names to column lists
        """
        return self.db.get_table_info()

    def get_system_health(self, ai_generator, session_manager) -> dict[str, Any]:
        """
        Get system health check status.

        Args:
            ai_generator: AI generator instance to check
            session_manager: Session manager instance to check

        Returns:
            Dictionary with health status of various components
        """
        health = {
            "timestamp": datetime.datetime.now().isoformat(),
            "database": {"status": "unknown"},
            "ai_generator": {"status": "unknown"},
            "session_manager": {"status": "unknown"},
        }

        # Test database connection
        try:
            test_query = "SELECT 1 as test"
            result = self.db.execute_query(test_query)
            if result and result[0]["test"] == 1:
                health["database"] = {"status": "healthy"}
            else:
                health["database"] = {"status": "unhealthy", "error": "Query failed"}
        except Exception as e:
            health["database"] = {"status": "unhealthy", "error": str(e)}

        # Test AI generator (basic check)
        try:
            if hasattr(ai_generator, "client") and ai_generator.client:
                health["ai_generator"] = {"status": "healthy"}
            else:
                health["ai_generator"] = {"status": "unhealthy", "error": "No client"}
        except Exception as e:
            health["ai_generator"] = {"status": "unhealthy", "error": str(e)}

        # Test session manager
        try:
            if hasattr(session_manager, "sessions"):
                health["session_manager"] = {"status": "healthy"}
            else:
                health["session_manager"] = {
                    "status": "unhealthy",
                    "error": "No sessions",
                }
        except Exception as e:
            health["session_manager"] = {"status": "unhealthy", "error": str(e)}

        return health
