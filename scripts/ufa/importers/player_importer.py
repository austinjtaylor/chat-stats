#!/usr/bin/env python3
"""
Player importer for UFA data.
"""

from typing import Any

from .base_importer import BaseImporter


class PlayerImporter(BaseImporter):
    """Handles importing player data from UFA API"""

    def import_players(self, players_data: list[dict[str, Any]]) -> int:
        """
        Import players from API data using batch insert

        Args:
            players_data: List of player dictionaries from API

        Returns:
            Number of players imported
        """
        players_batch = []
        for player in players_data:
            # Convert empty string jersey_number to None for PostgreSQL INTEGER column
            jersey_num = player.get("jerseyNumber")
            if jersey_num == "":
                jersey_num = None

            player_data = {
                "player_id": player.get("playerID", ""),
                "first_name": player.get("firstName", ""),
                "last_name": player.get("lastName", ""),
                "full_name": player.get("fullName", ""),
                "team_id": player.get("teamID", ""),
                "active": player.get("active", True),
                "year": player.get("year"),
                "jersey_number": jersey_num,
            }
            players_batch.append(player_data)

        # Batch insert all players at once
        count = self.batch_insert(
            table="players",
            columns=[
                "player_id",
                "first_name",
                "last_name",
                "full_name",
                "team_id",
                "active",
                "year",
                "jersey_number",
            ],
            data=players_batch,
        )

        self.logger.info(f"  Imported {count} players")
        return count
