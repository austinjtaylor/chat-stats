"""
Game data importer.
"""

from datetime import date
from typing import Any

from models.db import Game


class GameImporter:
    """Handles game data import operations."""

    def __init__(self, db):
        """
        Initialize the game importer.

        Args:
            db: Database instance
        """
        self.db = db

    def import_game(self, game_data: dict[str, Any]) -> int | None:
        """
        Import a single game into the database.

        Args:
            game_data: Game dictionary

        Returns:
            Game ID if imported, None if already exists
        """
        # Convert team names to IDs if needed
        if "home_team_name" in game_data:
            home_team = self.db.execute_query(
                "SELECT id FROM teams WHERE name = :name OR abbreviation = :name",
                {"name": game_data["home_team_name"]},
            )
            if home_team:
                game_data["home_team_id"] = home_team[0]["id"]
            game_data.pop("home_team_name", None)

        if "away_team_name" in game_data:
            away_team = self.db.execute_query(
                "SELECT id FROM teams WHERE name = :name OR abbreviation = :name",
                {"name": game_data["away_team_name"]},
            )
            if away_team:
                game_data["away_team_id"] = away_team[0]["id"]
            game_data.pop("away_team_name", None)

        # Check if game already exists
        existing = self.db.execute_query(
            """SELECT id FROM games
               WHERE game_date = :game_date
               AND home_team_id = :home_team_id
               AND away_team_id = :away_team_id""",
            {
                "game_date": game_data.get("game_date"),
                "home_team_id": game_data.get("home_team_id"),
                "away_team_id": game_data.get("away_team_id"),
            },
        )

        if not existing:
            game = Game(**game_data)
            game_dict = game.dict(exclude_none=True, exclude={"id"})
            # Convert date to string for SQLite
            if isinstance(game_dict.get("game_date"), date):
                game_dict["game_date"] = game_dict["game_date"].isoformat()
            return self.db.insert_data("games", game_dict)

        return existing[0]["id"] if existing else None
