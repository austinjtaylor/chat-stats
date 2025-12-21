"""
Player data importer.
"""

from typing import Any

from models.db import Player


class PlayerImporter:
    """Handles player data import operations."""

    def __init__(self, db):
        """
        Initialize the player importer.

        Args:
            db: Database instance
        """
        self.db = db

    def import_players(self, players_data: list[dict[str, Any]]) -> int:
        """
        Import player data into the database.

        Args:
            players_data: List of player dictionaries

        Returns:
            Number of players imported
        """
        count = 0
        for player_dict in players_data:
            try:
                # Skip None values
                if not player_dict:
                    continue

                # Check if player already exists
                existing = self.db.execute_query(
                    "SELECT id FROM players WHERE name = :name",
                    {"name": player_dict.get("name")},
                )

                if not existing:
                    # Get team_id if team name is provided
                    if "team_name" in player_dict:
                        team_result = self.db.execute_query(
                            "SELECT id FROM teams WHERE name = :name",
                            {"name": player_dict["team_name"]},
                        )
                        if team_result:
                            player_dict["team_id"] = team_result[0]["id"]
                        player_dict.pop("team_name", None)

                    player = Player(**player_dict)
                    player_data = player.dict(exclude_none=True, exclude={"id"})
                    self.db.insert_data("players", player_data)
                    count += 1
            except Exception as e:
                # Log error and continue with next player
                print(f"Error importing player {player_dict}: {e}")
                continue

        return count
