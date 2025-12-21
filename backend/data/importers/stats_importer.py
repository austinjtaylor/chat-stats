"""
Player game statistics importer.
"""

from typing import Any

from models.db import PlayerGameStats


class StatsImporter:
    """Handles player game statistics import operations."""

    def __init__(self, db):
        """
        Initialize the stats importer.

        Args:
            db: Database instance
        """
        self.db = db

    def import_player_game_stats(self, stats_data: list[dict[str, Any]]) -> int:
        """
        Import player game statistics.

        Args:
            stats_data: List of player game stats dictionaries

        Returns:
            Number of stats records imported
        """
        count = 0
        for stat_dict in stats_data:
            try:
                # Skip None values
                if not stat_dict:
                    continue

                # Convert player name to ID if needed
                if "player_name" in stat_dict:
                    player = self.db.execute_query(
                        "SELECT id FROM players WHERE name = :name",
                        {"name": stat_dict["player_name"]},
                    )
                    if player:
                        stat_dict["player_id"] = player[0]["id"]
                    stat_dict.pop("player_name", None)

                # Check if stats already exist for this player/game
                existing = self.db.execute_query(
                    """SELECT id FROM player_game_stats
                       WHERE player_id = :player_id AND game_id = :game_id""",
                    {
                        "player_id": stat_dict.get("player_id"),
                        "game_id": stat_dict.get("game_id"),
                    },
                )

                if not existing:
                    stats = PlayerGameStats(**stat_dict)
                    stats_data = stats.dict(exclude_none=True, exclude={"id"})
                    self.db.insert_data("player_game_stats", stats_data)
                    count += 1
            except Exception as e:
                # Log error and continue with next stat record
                print(f"Error importing player game stats {stat_dict}: {e}")
                continue

        return count
