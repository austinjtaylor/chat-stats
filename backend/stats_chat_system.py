"""
Main orchestrator for the Sports Statistics Chat System.
Replaces the RAG system with direct SQL database queries for sports stats.
"""

from typing import List, Tuple, Optional, Dict, Any
import os
from sql_database import SQLDatabase, get_db
from stats_processor import StatsProcessor
from stats_tools import StatsToolManager
from ai_generator import AIGenerator
from session_manager import SessionManager
from models import Player, Team, Game


class StatsChatSystem:
    """Main orchestrator for the Sports Statistics Chat System"""
    
    def __init__(self, config):
        """
        Initialize the sports stats chat system.
        
        Args:
            config: Configuration object with necessary settings
        """
        self.config = config
        
        # Initialize core components
        self.db = get_db()
        self.stats_processor = StatsProcessor(self.db)
        self.tool_manager = StatsToolManager(self.db)
        self.ai_generator = AIGenerator(
            config.ANTHROPIC_API_KEY,
            config.ANTHROPIC_MODEL
        )
        self.session_manager = SessionManager(config.MAX_HISTORY)
    
    def query(self, query: str, session_id: Optional[str] = None) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Process a user query about sports statistics.
        
        Args:
            query: User's question about sports stats
            session_id: Optional session ID for conversation context
            
        Returns:
            Tuple of (response, sources/data used)
        """
        # Get conversation history if session exists
        history = None
        if session_id:
            history = self.session_manager.get_conversation_history(session_id)
        
        # Get tool definitions for Claude
        tools = self.tool_manager.get_tool_definitions()
        
        # Generate response using AI with SQL tools
        response = self.ai_generator.generate_response(
            query=query,
            conversation_history=history,
            tools=tools,
            tool_manager=self.tool_manager
        )
        
        # Get any sources/data that were used
        sources = self.tool_manager.get_last_sources()
        
        # Reset sources for next query
        self.tool_manager.reset_sources()
        
        # Update conversation history
        if session_id:
            self.session_manager.add_exchange(session_id, query, response)
        
        return response, sources
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """
        Get a summary of available statistics in the database.
        
        Returns:
            Dictionary with counts and summary information
        """
        summary = {
            "total_players": self.db.get_row_count("players"),
            "total_teams": self.db.get_row_count("teams"),
            "total_games": self.db.get_row_count("games"),
            "total_player_stats": self.db.get_row_count("player_game_stats"),
            "seasons": [],
            "team_standings": []
        }
        
        # Get available seasons/years (UFA schema)
        seasons_query = """
        SELECT DISTINCT year 
        FROM games 
        ORDER BY year DESC
        LIMIT 5
        """
        try:
            seasons_result = self.db.execute_query(seasons_query)
            summary["seasons"] = [str(row["year"]) for row in seasons_result]
        except Exception as e:
            print(f"Could not get seasons: {e}")
            summary["seasons"] = []
        
        # Get team standings (UFA schema)
        if summary["seasons"]:
            current_year = int(summary["seasons"][0])
            standings_query = """
            SELECT t.name, t.full_name, tss.wins, tss.losses, tss.ties, tss.standing
            FROM team_season_stats tss
            JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
            WHERE tss.year = :year
            ORDER BY tss.standing ASC
            LIMIT 10
            """
            try:
                standings = self.db.execute_query(standings_query, {"year": current_year})
                summary["team_standings"] = standings
            except Exception as e:
                print(f"Could not get standings: {e}")
                summary["team_standings"] = []
        
        return summary
    
    def import_data(self, data_source: str, data_type: str) -> Dict[str, int]:
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
    
    def get_database_info(self) -> Dict[str, List[str]]:
        """
        Get information about database tables and columns.
        
        Returns:
            Dictionary mapping table names to column lists
        """
        return self.db.get_table_info()
    
    def search_player(self, player_name: str) -> List[Dict[str, Any]]:
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
        LEFT JOIN teams t ON p.team_id = t.id
        WHERE LOWER(p.name) LIKE LOWER(:name)
        ORDER BY p.name
        LIMIT 10
        """
        return self.db.execute_query(query, {"name": f"%{player_name}%"})
    
    def search_team(self, team_name: str) -> List[Dict[str, Any]]:
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
           OR LOWER(abbreviation) = LOWER(:name)
        ORDER BY name
        """
        return self.db.execute_query(query, {"name": f"%{team_name}%"})
    
    def get_recent_games(self, limit: int = 10) -> List[Dict[str, Any]]:
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
        JOIN teams ht ON g.home_team_id = ht.id
        JOIN teams at ON g.away_team_id = at.id
        ORDER BY g.game_date DESC
        LIMIT :limit
        """
        return self.db.execute_query(query, {"limit": limit})
    
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