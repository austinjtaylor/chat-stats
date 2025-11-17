#!/usr/bin/env python3
"""
Game importer for UFA data.
"""

from typing import Any

from .base_importer import BaseImporter


class GameImporter(BaseImporter):
    """Handles importing game data from UFA API"""

    def import_games(self, games_data: list[dict[str, Any]]) -> int:
        """
        Import games from API data using batch insert

        Args:
            games_data: List of game dictionaries from API

        Returns:
            Number of games imported
        """
        games_batch = []
        skipped_allstar = 0

        for game in games_data:
            # Extract year from game_id or use current year
            game_id = game.get("gameID", "")
            year = self.extract_year_from_game_id(game_id)

            # Skip all-star games
            away_team_id = game.get("awayTeamID", "")
            home_team_id = game.get("homeTeamID", "")
            if self.is_allstar_game(game_id, away_team_id, home_team_id):
                skipped_allstar += 1
                continue

            game_data = {
                "game_id": game_id,
                "away_team_id": away_team_id,
                "home_team_id": home_team_id,
                "away_score": game.get("awayScore"),
                "home_score": game.get("homeScore"),
                "status": game.get("status", ""),
                "start_timestamp": game.get("startTimestamp"),
                "start_timezone": game.get("startTimezone"),
                "streaming_url": game.get("streamingUrl"),
                "update_timestamp": game.get("updateTimestamp"),
                "week": game.get("week"),
                "location": game.get("location"),
                "year": year,
            }
            games_batch.append(game_data)

        # Batch insert all games at once
        count = self.batch_insert(
            table="games",
            columns=[
                "game_id",
                "away_team_id",
                "home_team_id",
                "away_score",
                "home_score",
                "status",
                "start_timestamp",
                "start_timezone",
                "streaming_url",
                "update_timestamp",
                "week",
                "location",
                "year",
            ],
            data=games_batch,
        )

        if skipped_allstar > 0:
            self.logger.info(f"  Skipped {skipped_allstar} all-star games")
        self.logger.info(f"  Imported {count} games")
        return count
