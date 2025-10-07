"""
Main orchestrator for the Sports Statistics Chat System.
Replaces the RAG system with direct SQL database queries for sports stats.
"""

from typing import Any

from core.ai_generator import AIGenerator
from core.session_manager import SessionManager
from tools.manager import StatsToolManager
from utils.response import format_game_details_response, should_format_response

from data.cache import cache_key_for_endpoint, get_cache
from data.database import get_db
from data.possession import calculate_possessions, calculate_redzone_stats_for_team
from data.processor import StatsProcessor


class StatsChatSystem:
    """Main orchestrator for the Sports Statistics Chat System"""

    def __init__(self, config):
        """
        Initialize the sports stats chat system.

        Args:
            config: Configuration object with necessary settings
        """
        self.config = config

        # Validate required configuration
        if not hasattr(config, "ANTHROPIC_API_KEY") or not config.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required")

        if not hasattr(config, "ANTHROPIC_MODEL"):
            raise AttributeError("ANTHROPIC_MODEL is required")

        if not hasattr(config, "MAX_HISTORY"):
            config.MAX_HISTORY = 5  # Default value

        # Initialize core components
        self.db = get_db()
        self.stats_processor = StatsProcessor(self.db)
        self.tool_manager = StatsToolManager(self.db)
        self.ai_generator = AIGenerator(
            config.ANTHROPIC_API_KEY, config.ANTHROPIC_MODEL
        )
        self.session_manager = SessionManager(config.MAX_HISTORY)

    def query(
        self, query: str, session_id: str | None = None
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Process a user query about sports statistics.

        Args:
            query: User's question about sports stats
            session_id: Optional session ID for conversation context

        Returns:
            Tuple of (response, sources/data used)
        """
        try:
            # Get conversation history if session exists
            history = None
            if session_id:
                try:
                    history = self.session_manager.get_conversation_history(session_id)
                except Exception as e:
                    print(f"Session error: {e}")
                    history = None

            # Get tool definitions for Claude
            tools = self.tool_manager.get_tool_definitions()

            # Generate response using AI with SQL tools
            response = self.ai_generator.generate_response(
                query=query,
                conversation_history=history,
                tools=tools,
                tool_manager=self.tool_manager,
            )

            # Get any sources/data that were used
            sources = self.tool_manager.get_last_sources()

            # Reset sources for next query
            self.tool_manager.reset_sources()

            # Post-process response if it's a game details query
            if should_format_response(query) and sources:
                # Try to enhance the response with complete statistics
                enhanced_response = format_game_details_response(response, sources)

                # If enhancement didn't work and critical stats are still missing,
                # make an additional tool call to format properly
                if enhanced_response == response:
                    # Check if we're missing critical stats
                    critical_stats = [
                        "O-Line Conversion",
                        "D-Line Conversion",
                        "Red Zone Conversion",
                    ]
                    if any(stat not in response for stat in critical_stats):
                        # The data is available in sources, so format it properly
                        enhanced_response = format_game_details_response(
                            response, sources
                        )

                response = enhanced_response

            # Update conversation history (always add to session, create default if needed)
            if session_id:
                self.session_manager.add_exchange(session_id, query, response)
            else:
                # Add to a default session for testing
                self.session_manager.add_message("default", "user", query)
                self.session_manager.add_message("default", "assistant", response)

            return response, sources

        except Exception as e:
            # Check if it's a rate limit error
            error_msg = str(e)
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                # Return a user-friendly message for rate limits
                error_response = "The system is experiencing high demand. Please wait a moment and try again. Your query will be processed automatically."
            else:
                # Return generic error message for other failures
                error_response = f"I'm sorry, I encountered an error: {error_msg}"
            return error_response, []

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

        # Get available seasons/years (UFA schema)
        seasons_query = """
        SELECT DISTINCT year
        FROM games
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
                -- Get each team's most recent year
                SELECT
                    team_id,
                    name,
                    MAX(full_name) as full_name,
                    MAX(year) as last_year
                FROM teams
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

    def get_popular_queries(self) -> dict[str, Any]:
        """
        Get analytics about popular queries and usage.

        Returns:
            Dictionary with query analytics
        """
        try:
            # Get analytics from session manager if it has the method
            if hasattr(self.session_manager, "get_analytics"):
                return self.session_manager.get_analytics()
            else:
                # Default analytics
                return {"total_sessions": 0, "total_queries": 0, "popular_topics": []}
        except Exception as e:
            print(f"Error getting popular queries: {e}")
            return {"total_sessions": 0, "total_queries": 0, "popular_topics": []}

    def get_system_health(self) -> dict[str, Any]:
        """
        Get system health check status.

        Returns:
            Dictionary with health status of various components
        """
        import datetime

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
            if hasattr(self.ai_generator, "client") and self.ai_generator.client:
                health["ai_generator"] = {"status": "healthy"}
            else:
                health["ai_generator"] = {"status": "unhealthy", "error": "No client"}
        except Exception as e:
            health["ai_generator"] = {"status": "unhealthy", "error": str(e)}

        # Test session manager
        try:
            if hasattr(self.session_manager, "sessions"):
                health["session_manager"] = {"status": "healthy"}
            else:
                health["session_manager"] = {
                    "status": "unhealthy",
                    "error": "No sessions",
                }
        except Exception as e:
            health["session_manager"] = {"status": "unhealthy", "error": str(e)}

        return health

    def import_data(self, data_source: str, data_type: str) -> dict[str, int]:
        """
        Import sports data from various sources.

        Args:
            data_source: Path to data file or API endpoint
            data_type: Type of data ('csv', 'json', 'api')

        Returns:
            Dictionary with import statistics
        """
        if data_type == "csv":
            # Determine what kind of CSV it is based on filename
            if "teams" in data_source.lower():
                count = self.stats_processor.import_from_csv(data_source, "teams")
                return {"teams_imported": count}
            elif "players" in data_source.lower():
                count = self.stats_processor.import_from_csv(data_source, "players")
                return {"players_imported": count}
            elif "games" in data_source.lower():
                count = self.stats_processor.import_from_csv(data_source, "games")
                return {"games_imported": count}
            elif "stats" in data_source.lower():
                count = self.stats_processor.import_from_csv(data_source, "stats")
                return {"stats_imported": count}
        elif data_type == "json":
            return self.stats_processor.import_from_json(data_source)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    def calculate_season_stats(self, season: str):
        """
        Calculate and store aggregated season statistics.

        Args:
            season: Season identifier (e.g., "2023-24")
        """
        self.stats_processor.calculate_season_stats(season)

    def get_database_info(self) -> dict[str, list[str]]:
        """
        Get information about database tables and columns.

        Returns:
            Dictionary mapping table names to column lists
        """
        return self.db.get_table_info()

    def search_player(self, player_name: str) -> list[dict[str, Any]]:
        """
        Quick search for a player by name.

        Args:
            player_name: Player name or partial name

        Returns:
            List of matching players
        """
        query = """
        SELECT p.*, t.name as team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id AND p.year = t.year
        WHERE LOWER(p.full_name) LIKE LOWER(:name)
        ORDER BY p.full_name
        LIMIT 10
        """
        return self.db.execute_query(query, {"name": f"%{player_name}%"})

    def search_team(self, team_name: str) -> list[dict[str, Any]]:
        """
        Quick search for a team by name or abbreviation.

        Args:
            team_name: Team name or abbreviation

        Returns:
            List of matching teams
        """
        query = """
        SELECT * FROM teams
        WHERE LOWER(name) LIKE LOWER(:name)
           OR LOWER(abbrev) = LOWER(:name)
        ORDER BY name
        """
        return self.db.execute_query(query, {"name": f"%{team_name}%"})

    def get_recent_games(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get the most recent games.

        Args:
            limit: Number of games to return

        Returns:
            List of recent games
        """
        query = """
        SELECT g.*,
               ht.name as home_team_name,
               at.name as away_team_name
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
        JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
        ORDER BY g.start_timestamp DESC
        LIMIT :limit
        """
        return self.db.execute_query(query, {"limit": limit})

    def get_comprehensive_team_stats(
        self,
        season: str = "2025",
        view: str = "total",
        perspective: str = "team",
        sort: str = "wins",
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        """
        Get comprehensive team statistics with all UFA-style columns.

        Args:
            season: Season year or 'career' for all-time stats
            view: 'total' or 'per-game' for aggregation type
            perspective: 'team' for team stats or 'opponent' for opponent stats
            sort: Column to sort by
            order: 'asc' or 'desc'

        Returns:
            List of team statistics dictionaries
        """
        # Build WHERE clause for season filter
        season_filter = "AND g.year = :season" if season != "career" else ""
        season_param = int(season) if season.isdigit() else None

        # Determine if we're showing team stats or opponent stats
        is_opponent_view = perspective == "opponent"

        query = f"""
        WITH distinct_teams AS (
            SELECT DISTINCT team_id, MIN(name) as name, MIN(full_name) as full_name
            FROM teams
            GROUP BY team_id
        ),
        team_game_stats AS (
            SELECT
                t.team_id,
                t.name,
                t.full_name,
                -- Basic record stats
                COUNT(DISTINCT CASE WHEN g.game_id IS NOT NULL THEN g.game_id END) as games_played,
                COUNT(DISTINCT CASE WHEN
                    (g.home_team_id = t.team_id AND g.home_score > g.away_score) OR
                    (g.away_team_id = t.team_id AND g.away_score > g.home_score)
                THEN g.game_id END) as wins,
                COUNT(DISTINCT CASE WHEN
                    (g.home_team_id = t.team_id AND g.home_score < g.away_score) OR
                    (g.away_team_id = t.team_id AND g.away_score < g.home_score)
                THEN g.game_id END) as losses,
                -- Scores for and against
                SUM(CASE WHEN g.home_team_id = t.team_id
                    THEN {'g.away_score' if is_opponent_view else 'g.home_score'}
                    ELSE {'g.home_score' if is_opponent_view else 'g.away_score'}
                END) as scores,
                SUM(CASE WHEN g.home_team_id = t.team_id
                    THEN {'g.home_score' if is_opponent_view else 'g.away_score'}
                    ELSE {'g.away_score' if is_opponent_view else 'g.home_score'}
                END) as scores_against
            FROM distinct_teams t
            LEFT JOIN games g ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
            WHERE 1=1 {season_filter}
            GROUP BY t.team_id, t.name, t.full_name
        ),
        {'all_team_stats AS (' if is_opponent_view else 'team_player_stats AS ('}
            SELECT
                {'pgs' if not is_opponent_view else 'pgs'}.team_id,
                SUM(pgs.completions) as total_completions,
                SUM(pgs.throw_attempts) as total_attempts,
                SUM(pgs.throwaways + pgs.drops + pgs.stalls) as total_turnovers,
                SUM(pgs.hucks_completed) as hucks_completed,
                SUM(pgs.hucks_attempted) as hucks_attempted,
                SUM(pgs.blocks) as total_blocks
            FROM player_game_stats pgs
            {'JOIN games g ON pgs.game_id = g.game_id' if season_filter else ''}
            WHERE 1=1 {season_filter}
            GROUP BY pgs.team_id
        ){''',
        team_player_stats AS (
            SELECT
                t.team_id,
                SUM(ats.total_completions) as total_completions,
                SUM(ats.total_attempts) as total_attempts,
                SUM(ats.total_turnovers) as total_turnovers,
                SUM(ats.hucks_completed) as hucks_completed,
                SUM(ats.hucks_attempted) as hucks_attempted,
                SUM(ats.total_blocks) as total_blocks
            FROM distinct_teams t
            JOIN games g ON (g.home_team_id = t.team_id OR g.away_team_id = t.team_id)
            JOIN all_team_stats ats ON ats.team_id = CASE
                WHEN g.home_team_id = t.team_id THEN g.away_team_id
                ELSE g.home_team_id
            END
            WHERE 1=1 ''' + season_filter + '''
            GROUP BY t.team_id
        )''' if is_opponent_view else ''}
        SELECT
            tgs.team_id,
            tgs.name,
            tgs.full_name,
            tgs.games_played,
            tgs.wins,
            tgs.losses,
            tgs.scores,
            tgs.scores_against,
            COALESCE(tps.total_completions, 0) as completions,
            COALESCE(tps.total_turnovers, 0) as turnovers,
            CASE WHEN COALESCE(tps.total_attempts, 0) > 0
                THEN ROUND((CAST(tps.total_completions AS NUMERIC) / tps.total_attempts) * 100, 2)
                ELSE 0
            END as completion_percentage,
            COALESCE(tps.hucks_completed, 0) as hucks_completed,
            CASE WHEN COALESCE(tps.hucks_attempted, 0) > 0
                THEN ROUND((CAST(tps.hucks_completed AS NUMERIC) / tps.hucks_attempted) * 100, 2)
                ELSE 0
            END as huck_percentage,
            COALESCE(tps.total_blocks, 0) as blocks,
            -- Possession stats will be calculated separately
            0.0 as hold_percentage,
            0.0 as o_line_conversion,
            0.0 as break_percentage,
            0.0 as d_line_conversion,
            0.0 as red_zone_conversion
        FROM team_game_stats tgs
        LEFT JOIN team_player_stats tps ON tgs.team_id = tps.team_id
        WHERE tgs.games_played > 0
        ORDER BY
            CASE WHEN :order = 'desc' THEN
                CASE :sort_col
                    -- Basic stats
                    WHEN 'name' THEN NULL  -- Handle name separately for proper string sorting
                    WHEN 'games_played' THEN tgs.games_played
                    WHEN 'wins' THEN tgs.wins
                    WHEN 'losses' THEN tgs.losses
                    WHEN 'scores' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(tgs.scores AS NUMERIC) / tgs.games_played
                            ELSE tgs.scores
                        END
                    WHEN 'scores_against' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(tgs.scores_against AS NUMERIC) / tgs.games_played
                            ELSE tgs.scores_against
                        END
                    -- Core stats
                    WHEN 'completions' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(COALESCE(tps.total_completions, 0) AS NUMERIC) / tgs.games_played
                            ELSE COALESCE(tps.total_completions, 0)
                        END
                    WHEN 'turnovers' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(COALESCE(tps.total_turnovers, 0) AS NUMERIC) / tgs.games_played
                            ELSE COALESCE(tps.total_turnovers, 0)
                        END
                    WHEN 'completion_percentage' THEN (CASE WHEN COALESCE(tps.total_attempts, 0) > 0 THEN (CAST(tps.total_completions AS NUMERIC) / tps.total_attempts) * 100 ELSE 0 END)
                    -- Advanced stats
                    WHEN 'hucks_completed' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(COALESCE(tps.hucks_completed, 0) AS NUMERIC) / tgs.games_played
                            ELSE COALESCE(tps.hucks_completed, 0)
                        END
                    WHEN 'huck_percentage' THEN (CASE WHEN COALESCE(tps.hucks_attempted, 0) > 0 THEN (CAST(tps.hucks_completed AS NUMERIC) / tps.hucks_attempted) * 100 ELSE 0 END)
                    WHEN 'blocks' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(COALESCE(tps.total_blocks, 0) AS NUMERIC) / tgs.games_played
                            ELSE COALESCE(tps.total_blocks, 0)
                        END
                    -- Possession stats (placeholders for now, will be filled later)
                    WHEN 'hold_percentage' THEN 0
                    WHEN 'o_line_conversion' THEN 0
                    WHEN 'break_percentage' THEN 0
                    WHEN 'd_line_conversion' THEN 0
                    WHEN 'red_zone_conversion' THEN 0
                    ELSE tgs.wins
                END
            END DESC,
            CASE WHEN :order = 'asc' THEN
                CASE :sort_col
                    -- Basic stats
                    WHEN 'name' THEN NULL  -- Handle name separately for proper string sorting
                    WHEN 'games_played' THEN tgs.games_played
                    WHEN 'wins' THEN tgs.wins
                    WHEN 'losses' THEN tgs.losses
                    WHEN 'scores' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(tgs.scores AS NUMERIC) / tgs.games_played
                            ELSE tgs.scores
                        END
                    WHEN 'scores_against' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(tgs.scores_against AS NUMERIC) / tgs.games_played
                            ELSE tgs.scores_against
                        END
                    -- Core stats
                    WHEN 'completions' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(COALESCE(tps.total_completions, 0) AS NUMERIC) / tgs.games_played
                            ELSE COALESCE(tps.total_completions, 0)
                        END
                    WHEN 'turnovers' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(COALESCE(tps.total_turnovers, 0) AS NUMERIC) / tgs.games_played
                            ELSE COALESCE(tps.total_turnovers, 0)
                        END
                    WHEN 'completion_percentage' THEN (CASE WHEN COALESCE(tps.total_attempts, 0) > 0 THEN (CAST(tps.total_completions AS NUMERIC) / tps.total_attempts) * 100 ELSE 0 END)
                    -- Advanced stats
                    WHEN 'hucks_completed' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(COALESCE(tps.hucks_completed, 0) AS NUMERIC) / tgs.games_played
                            ELSE COALESCE(tps.hucks_completed, 0)
                        END
                    WHEN 'huck_percentage' THEN (CASE WHEN COALESCE(tps.hucks_attempted, 0) > 0 THEN (CAST(tps.hucks_completed AS NUMERIC) / tps.hucks_attempted) * 100 ELSE 0 END)
                    WHEN 'blocks' THEN
                        CASE WHEN :view = 'per-game' AND tgs.games_played > 0
                            THEN CAST(COALESCE(tps.total_blocks, 0) AS NUMERIC) / tgs.games_played
                            ELSE COALESCE(tps.total_blocks, 0)
                        END
                    -- Possession stats (placeholders for now, will be filled later)
                    WHEN 'hold_percentage' THEN 0
                    WHEN 'o_line_conversion' THEN 0
                    WHEN 'break_percentage' THEN 0
                    WHEN 'd_line_conversion' THEN 0
                    WHEN 'red_zone_conversion' THEN 0
                    ELSE tgs.wins
                END
            END ASC,
            -- Handle name sorting separately
            CASE
                WHEN :sort_col = 'name' AND :order = 'asc' THEN tgs.name
            END ASC,
            CASE
                WHEN :sort_col = 'name' AND :order = 'desc' THEN tgs.name
            END DESC,
            -- Secondary sort by name if not primary sort
            CASE
                WHEN :sort_col != 'name' THEN tgs.name
            END ASC
        """

        params = {
            "season": season_param,
            "sort_col": sort,
            "order": order,
            "view": view,
        }

        teams = self.db.execute_query(query, params)

        # Calculate possession statistics for each team
        for team in teams:
            team_id = team["team_id"]

            # Get all games for this team in the season
            games_query = f"""
            SELECT g.game_id,
                   g.home_team_id,
                   g.away_team_id,
                   CASE WHEN g.home_team_id = :team_id THEN 1 ELSE 0 END as is_home
            FROM games g
            WHERE (g.home_team_id = :team_id OR g.away_team_id = :team_id)
            {season_filter}
            """
            games = self.db.execute_query(
                games_query, {"team_id": team_id, "season": season_param}
            )

            # Aggregate possession stats across all games
            total_o_line_points = 0
            total_o_line_scores = 0
            total_o_line_possessions = 0
            total_d_line_points = 0
            total_d_line_scores = 0
            total_d_line_possessions = 0
            total_redzone_possessions = 0
            total_redzone_goals = 0
            games_with_events = 0

            for game in games:
                game_id = game["game_id"]
                is_home = bool(game["is_home"])

                # For opponent perspective, we want stats for the opposing team
                if is_opponent_view:
                    # Get the opponent's team_id
                    opponent_team_id = (
                        game["away_team_id"] if is_home else game["home_team_id"]
                    )
                    opponent_is_home = not is_home

                    # Calculate possession stats for the opponent
                    poss_stats = calculate_possessions(
                        self.db, game_id, opponent_team_id, opponent_is_home
                    )
                    if poss_stats:
                        games_with_events += 1
                        total_o_line_points += poss_stats["o_line_points"]
                        total_o_line_scores += poss_stats["o_line_scores"]
                        total_o_line_possessions += poss_stats["o_line_possessions"]
                        total_d_line_points += poss_stats["d_line_points"]
                        total_d_line_scores += poss_stats["d_line_scores"]
                        total_d_line_possessions += poss_stats["d_line_possessions"]

                    # Calculate redzone stats for the opponent
                    rz_stats = calculate_redzone_stats_for_team(
                        self.db, game_id, opponent_team_id, opponent_is_home
                    )
                    if rz_stats:
                        total_redzone_possessions += rz_stats["possessions"]
                        total_redzone_goals += rz_stats["goals"]
                else:
                    # Try to calculate possession stats for this game
                    poss_stats = calculate_possessions(
                        self.db, game_id, team_id, is_home
                    )
                    if poss_stats:
                        games_with_events += 1
                        total_o_line_points += poss_stats["o_line_points"]
                        total_o_line_scores += poss_stats["o_line_scores"]
                        total_o_line_possessions += poss_stats["o_line_possessions"]
                        total_d_line_points += poss_stats["d_line_points"]
                        total_d_line_scores += poss_stats["d_line_scores"]
                        total_d_line_possessions += poss_stats["d_line_possessions"]

                    # Try to calculate redzone stats for this game
                    rz_stats = calculate_redzone_stats_for_team(
                        self.db, game_id, team_id, is_home
                    )
                    if rz_stats:
                        total_redzone_possessions += rz_stats["possessions"]
                        total_redzone_goals += rz_stats["goals"]

            # Calculate percentages
            if total_o_line_points > 0:
                team["hold_percentage"] = round(
                    (total_o_line_scores / total_o_line_points) * 100, 1
                )
            else:
                team["hold_percentage"] = 0.0

            if total_o_line_possessions > 0:
                team["o_line_conversion"] = round(
                    (total_o_line_scores / total_o_line_possessions) * 100, 1
                )
            else:
                team["o_line_conversion"] = 0.0

            if total_d_line_points > 0:
                team["break_percentage"] = round(
                    (total_d_line_scores / total_d_line_points) * 100, 1
                )
            else:
                team["break_percentage"] = 0.0

            if total_d_line_possessions > 0:
                team["d_line_conversion"] = round(
                    (total_d_line_scores / total_d_line_possessions) * 100, 1
                )
            else:
                team["d_line_conversion"] = 0.0

            if total_redzone_possessions > 0:
                team["red_zone_conversion"] = round(
                    (total_redzone_goals / total_redzone_possessions) * 100, 1
                )
            else:
                team["red_zone_conversion"] = 0.0

        # Apply per-game calculations if requested
        if view == "per-game":
            for team in teams:
                if team["games_played"] > 0:
                    games = team["games_played"]
                    team["scores"] = round(team["scores"] / games, 2)
                    team["scores_against"] = round(team["scores_against"] / games, 2)
                    team["completions"] = round(team["completions"] / games, 2)
                    team["turnovers"] = round(team["turnovers"] / games, 2)
                    team["hucks_completed"] = round(team["hucks_completed"] / games, 2)
                    team["blocks"] = round(team["blocks"] / games, 2)

        # If sorting by possession stats, apply Python sorting after calculation
        possession_stats = [
            "hold_percentage",
            "o_line_conversion",
            "break_percentage",
            "d_line_conversion",
            "red_zone_conversion",
        ]

        if sort in possession_stats:
            # Sort by the calculated possession stat values
            reverse = order == "desc"
            teams.sort(key=lambda x: x.get(sort, 0), reverse=reverse)

        return teams

    def close(self):
        """Close database connections and cleanup."""
        self.db.close()


# Singleton instance for the application
_system_instance = None


def get_stats_system(config) -> StatsChatSystem:
    """Get the singleton stats system instance."""
    global _system_instance
    if _system_instance is None:
        _system_instance = StatsChatSystem(config)
    return _system_instance
