"""
Search service for players, teams, and games.
"""

from typing import Any


class SearchService:
    """Service for searching players, teams, and games."""

    def __init__(self, db):
        """
        Initialize the search service.

        Args:
            db: Database instance
        """
        self.db = db

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
