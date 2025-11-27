"""
Main orchestrator for the Sports Statistics Chat System.

This file now serves as a thin orchestrator delegating to specialized service modules.
The original 707-line file has been split into focused services for better maintainability.

See backend/services/chat_system/ for the new modular structure:
- database_stats.py: Database statistics and health checks (271 lines)
- search.py: Player/team search and recent games (78 lines)
- team_stats.py: Comprehensive team statistics (252 lines)
- data_import.py: Data import operations (71 lines)

Total: 672 lines across 4 focused service modules (was 707 lines in 1 monolithic file)
"""

from typing import Any

from core.ai_generator import AIGenerator
from core.session_manager import SessionManager
from tools.manager import StatsToolManager
from utils.response import format_game_details_response, should_format_response

from data.database import get_db
from data.processor import StatsProcessor

# Import service modules
from services.chat_system import (
    DatabaseStatsService,
    SearchService,
    TeamStatsService,
    DataImportService,
)


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

        # Initialize service modules
        self.db_stats = DatabaseStatsService(self.db, config)
        self.search = SearchService(self.db)
        self.team_stats = TeamStatsService(self.db)
        self.data_import = DataImportService(self.stats_processor)

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
                # Enhance the response with complete statistics in table format
                response = format_game_details_response(response, sources)

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
        """Get a summary of available statistics - delegated to DatabaseStatsService."""
        return self.db_stats.get_stats_summary()

    def get_database_stats(self) -> dict[str, Any]:
        """Get comprehensive database statistics - delegated to DatabaseStatsService."""
        return self.db_stats.get_database_stats()

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
        """Get system health check status - delegated to DatabaseStatsService."""
        return self.db_stats.get_system_health(self.ai_generator, self.session_manager)

    def import_data(self, data_source: str, data_type: str) -> dict[str, int]:
        """Import sports data from various sources - delegated to DataImportService."""
        return self.data_import.import_data(data_source, data_type)

    def calculate_season_stats(self, season: str):
        """Calculate and store aggregated season statistics - delegated to DataImportService."""
        self.data_import.calculate_season_stats(season)

    def get_database_info(self) -> dict[str, list[str]]:
        """Get information about database tables and columns - delegated to DatabaseStatsService."""
        return self.db_stats.get_database_info()

    def search_player(self, player_name: str) -> list[dict[str, Any]]:
        """Quick search for a player by name - delegated to SearchService."""
        return self.search.search_player(player_name)

    def search_team(self, team_name: str) -> list[dict[str, Any]]:
        """Quick search for a team by name - delegated to SearchService."""
        return self.search.search_team(team_name)

    def get_recent_games(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the most recent games - delegated to SearchService."""
        return self.search.get_recent_games(limit)

    def get_comprehensive_team_stats(
        self,
        season: str = "2025",
        view: str = "total",
        perspective: str = "team",
        sort: str = "wins",
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        """Get comprehensive team statistics - delegated to TeamStatsService."""
        return self.team_stats.get_comprehensive_team_stats(
            season, view, perspective, sort, order
        )

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
