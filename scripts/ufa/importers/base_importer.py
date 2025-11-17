#!/usr/bin/env python3
"""
Base importer class with shared logic for all UFA data importers.
"""

import logging
from typing import Any

from sqlalchemy import text


class BaseImporter:
    """Base class for all UFA data importers"""

    def __init__(self, db, logger: logging.Logger = None):
        """
        Initialize the base importer

        Args:
            db: Database connection instance
            logger: Logger instance (optional, will create one if not provided)
        """
        self.db = db
        self.logger = logger or logging.getLogger(__name__)

    def batch_insert(
        self, table: str, columns: list[str], data: list[dict[str, Any]]
    ) -> int:
        """
        Perform a batch insert into the database

        Args:
            table: Table name
            columns: List of column names
            data: List of dictionaries containing row data

        Returns:
            Number of rows inserted
        """
        if not data:
            return 0

        columns_str = ", ".join(columns)
        placeholders = ", ".join([f":{col}" for col in columns])

        # Build ON CONFLICT clause based on table
        conflict_clause = self._get_conflict_clause(table)

        sql = f"""
            INSERT INTO {table} ({columns_str})
            VALUES ({placeholders})
            {conflict_clause}
        """

        with self.db.engine.connect() as conn:
            conn.execute(text(sql), data)
            conn.commit()

        return len(data)

    def _get_conflict_clause(self, table: str) -> str:
        """
        Get the ON CONFLICT clause for a specific table

        Args:
            table: Table name

        Returns:
            ON CONFLICT SQL clause
        """
        # Define conflict resolution for each table
        conflict_clauses = {
            "teams": "ON CONFLICT (team_id, year) DO NOTHING",
            "players": "ON CONFLICT (player_id, team_id, year) DO NOTHING",
            "games": "ON CONFLICT (game_id) DO NOTHING",
            "player_game_stats": "ON CONFLICT (player_id, game_id) DO NOTHING",
            "player_season_stats": "ON CONFLICT (player_id, team_id, year) DO NOTHING",
            "game_events": "ON CONFLICT (game_id, event_index, team) DO NOTHING",
        }

        return conflict_clauses.get(table, "")

    def is_allstar_game(self, game_id: str, away_team_id: str = "", home_team_id: str = "") -> bool:
        """
        Check if a game is an all-star game

        Args:
            game_id: Game ID
            away_team_id: Away team ID (optional)
            home_team_id: Home team ID (optional)

        Returns:
            True if it's an all-star game, False otherwise
        """
        return (
            "allstar" in game_id.lower()
            or "allstar" in away_team_id.lower()
            or "allstar" in home_team_id.lower()
        )

    def extract_year_from_game_id(self, game_id: str, default: int = 2025) -> int:
        """
        Extract the year from a game ID

        Args:
            game_id: Game ID in format "YYYY-..."
            default: Default year if extraction fails

        Returns:
            Year as integer
        """
        try:
            if "-" in game_id:
                return int(game_id.split("-")[0])
        except (ValueError, IndexError):
            pass
        return default
