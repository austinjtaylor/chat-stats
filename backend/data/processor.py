"""
Stats processing module for data ingestion and transformation.

This file now serves as an orchestrator delegating to specialized importer modules.
The original 419-line file has been refactored into focused importers for better
organization and testability.

Refactored from a monolithic 419-line processor into focused importer modules:
- team_importer.py: Team data import (54 lines)
- player_importer.py: Player data import (64 lines)
- game_importer.py: Game data import (72 lines)
- stats_importer.py: Player game statistics import (68 lines)
- season_stats_calculator.py: Season statistics calculation (170 lines)

Total: 428 lines across 5 importer modules
Extracted from monolithic processor for better organization and testability.
"""

import json
from typing import Any

import pandas as pd

from data.database import SQLDatabase
from data.importers import (
    TeamImporter,
    PlayerImporter,
    GameImporter,
    StatsImporter,
    SeasonStatsCalculator,
)


class StatsProcessor:
    """Processes and imports sports statistics data into the database."""

    def __init__(self, db: SQLDatabase = None):
        """
        Initialize the stats processor.

        Args:
            db: SQLDatabase instance. If None, creates a new one.
        """
        self.db = db or SQLDatabase()

        # Initialize importer modules
        self.team_importer = TeamImporter(self.db)
        self.player_importer = PlayerImporter(self.db)
        self.game_importer = GameImporter(self.db)
        self.stats_importer = StatsImporter(self.db)
        self.season_calculator = SeasonStatsCalculator(self.db)

    def import_teams(self, teams_data: list[dict[str, Any]]) -> int:
        """
        Import team data - delegated to TeamImporter.

        Args:
            teams_data: List of team dictionaries

        Returns:
            Number of teams imported
        """
        return self.team_importer.import_teams(teams_data)

    def import_players(self, players_data: list[dict[str, Any]]) -> int:
        """
        Import player data - delegated to PlayerImporter.

        Args:
            players_data: List of player dictionaries

        Returns:
            Number of players imported
        """
        return self.player_importer.import_players(players_data)

    def import_game(self, game_data: dict[str, Any]) -> int | None:
        """
        Import a single game - delegated to GameImporter.

        Args:
            game_data: Game dictionary

        Returns:
            Game ID if imported, None if already exists
        """
        return self.game_importer.import_game(game_data)

    def import_player_game_stats(self, stats_data: list[dict[str, Any]]) -> int:
        """
        Import player game statistics - delegated to StatsImporter.

        Args:
            stats_data: List of player game stats dictionaries

        Returns:
            Number of stats records imported
        """
        return self.stats_importer.import_player_game_stats(stats_data)

    def calculate_season_stats(self, season):
        """
        Calculate and store aggregated season statistics - delegated to SeasonStatsCalculator.

        Args:
            season: Season identifier (year or season string like "2023-24")
        """
        return self.season_calculator.calculate_season_stats(season)

    def import_from_csv(self, csv_path: str, data_type: str) -> int:
        """
        Import data from a CSV file.

        Args:
            csv_path: Path to CSV file
            data_type: Type of data ('teams', 'players', 'games', 'stats')

        Returns:
            Number of records imported
        """
        df = pd.read_csv(csv_path)

        if data_type == "teams":
            teams_data = df.to_dict("records")
            return self.import_teams(teams_data)
        elif data_type == "players":
            players_data = df.to_dict("records")
            return self.import_players(players_data)
        elif data_type == "games":
            count = 0
            for _, row in df.iterrows():
                if self.import_game(row.to_dict()):
                    count += 1
            return count
        elif data_type == "stats":
            stats_data = df.to_dict("records")
            return self.import_player_game_stats(stats_data)
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def import_from_json(self, json_path: str) -> dict[str, int]:
        """
        Import data from a JSON file containing multiple data types.

        Args:
            json_path: Path to JSON file

        Returns:
            Dictionary with counts of imported records by type
        """
        with open(json_path) as f:
            data = json.load(f)

        results = {}

        if "teams" in data:
            results["teams"] = self.import_teams(data["teams"])

        if "players" in data:
            results["players"] = self.import_players(data["players"])

        if "games" in data:
            results["games"] = 0
            for game in data["games"]:
                if self.import_game(game):
                    results["games"] += 1

        if "player_stats" in data:
            results["player_stats"] = self.import_player_game_stats(
                data["player_stats"]
            )

        if "season" in data:
            self.calculate_season_stats(data["season"])
            results["season_stats_calculated"] = True

        return results
