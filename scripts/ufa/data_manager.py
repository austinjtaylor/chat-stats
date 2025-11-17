#!/usr/bin/env python3
"""
Unified UFA (Ultimate Frisbee Association) Data Manager.
Orchestrates import operations using specialized importers.
"""

import logging
import os
import sys
from multiprocessing import cpu_count
from typing import Any

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../..", "backend"))

from backend.data.database import get_db
from backend.data.processor import StatsProcessor

from scripts.ufa.api_client import UFAAPIClient
from scripts.ufa.importers import (
    TeamImporter,
    PlayerImporter,
    GameImporter,
    StatsImporter,
    EventsImporter,
)
from scripts.ufa.parallel_processor import ParallelProcessor


logger = logging.getLogger(__name__)


class UFADataManager:
    """Unified manager for UFA data import operations."""

    def __init__(self):
        self.api_client = UFAAPIClient()
        self.db = get_db()
        self.stats_processor = StatsProcessor(self.db)

        # Initialize importers
        self.team_importer = TeamImporter(self.db, logger)
        self.player_importer = PlayerImporter(self.db, logger)
        self.game_importer = GameImporter(self.db, logger)
        self.stats_importer = StatsImporter(self.db, logger)
        self.events_importer = EventsImporter(self.db, logger)
        self.parallel_processor = ParallelProcessor(logger)

    def import_from_api(
        self, years: list[int] | None = None, clear_existing: bool = True
    ) -> dict[str, int]:
        """
        Import UFA data directly from API into the database.

        Args:
            years: List of years to import. If None, imports 2012-2025 (excluding 2020)
            clear_existing: Whether to clear existing data first

        Returns:
            Dictionary with counts of imported data
        """
        if years is None:
            years = [y for y in range(2012, 2026) if y != 2020]

        logger.info(f"Starting direct API import for years: {years}")

        counts = {
            "teams": 0,
            "players": 0,
            "games": 0,
            "player_game_stats": 0,
            "player_season_stats": 0,
        }

        try:
            if clear_existing:
                logger.info("Clearing existing data...")
                self._clear_database()

            # Import teams
            logger.info("Fetching and importing teams...")
            teams_data = self.api_client.get_teams(years=years)
            if teams_data:
                counts["teams"] = self.team_importer.import_teams(teams_data, years)

            # Import players
            logger.info("Fetching and importing players...")
            players_data = self.api_client.get_players(years=years)
            if players_data:
                counts["players"] = self.player_importer.import_players(players_data)

            # Import games
            logger.info("Fetching and importing games...")
            games_data = self.api_client.get_games(years=years)
            if games_data:
                counts["games"] = self.game_importer.import_games(games_data)

            # Import player game stats for each game (sequential)
            if games_data:
                logger.info("Importing player game statistics...")
                counts["player_game_stats"] = self._import_player_game_stats_sequential(
                    games_data
                )

            # Import player season stats
            if players_data:
                logger.info("Importing player season statistics...")
                counts["player_season_stats"] = self._import_player_season_stats(
                    players_data, years
                )

            logger.info(f"Import complete. Total: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Error during import: {e}")
            raise

    def import_from_api_parallel(
        self,
        years: list[int] | None = None,
        clear_existing: bool = True,
        workers: int = None,
    ) -> dict[str, int]:
        """
        Import UFA data directly from API into the database with parallel processing.

        Args:
            years: List of years to import. If None, imports 2012-2025 (excluding 2020)
            clear_existing: Whether to clear existing data first
            workers: Number of parallel workers. If None, uses CPU count

        Returns:
            Dictionary with counts of imported data
        """
        if years is None:
            years = [y for y in range(2012, 2026) if y != 2020]

        if workers is None:
            workers = min(cpu_count(), 8)  # Limit to avoid overwhelming API

        logger.info(
            f"Starting parallel API import for years: {years} with {workers} workers"
        )

        counts = {
            "teams": 0,
            "players": 0,
            "games": 0,
            "player_game_stats": 0,
            "player_season_stats": 0,
        }

        try:
            if clear_existing:
                logger.info("Clearing existing data...")
                self._clear_database()

            # Import teams (fast, no need to parallelize)
            logger.info("Fetching and importing teams...")
            teams_data = self.api_client.get_teams(years=years)
            if teams_data:
                counts["teams"] = self.team_importer.import_teams(teams_data, years)

            # Import players (fast, no need to parallelize)
            logger.info("Fetching and importing players...")
            players_data = self.api_client.get_players(years=years)
            if players_data:
                counts["players"] = self.player_importer.import_players(players_data)

            # Import games (relatively fast)
            logger.info("Fetching and importing games...")
            games_data = self.api_client.get_games(years=years)
            if games_data:
                counts["games"] = self.game_importer.import_games(games_data)

            # Import player game stats in parallel (this is the slow part)
            if games_data:
                logger.info(
                    f"Importing player game statistics in parallel with {workers} workers..."
                )
                counts["player_game_stats"] = (
                    self.parallel_processor.import_player_game_stats_parallel(
                        games_data, workers
                    )
                )

            # Import player season stats
            if players_data:
                logger.info("Importing player season statistics...")
                counts["player_season_stats"] = self._import_player_season_stats(
                    players_data, years
                )

            logger.info(f"Parallel import complete. Total: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Error during parallel import: {e}")
            raise

    def complete_missing_imports(
        self, years: list[int] | None = None
    ) -> dict[str, int]:
        """
        Complete missing imports (games and season stats) without clearing existing data.
        Use this to finish a partially completed import.

        Args:
            years: List of years to import. If None, imports 2012-2025 (excluding 2020)

        Returns:
            Dictionary with counts of imported data
        """
        if years is None:
            years = [y for y in range(2012, 2026) if y != 2020]

        logger.info(f"Completing missing imports for years: {years}")

        counts = {"games": 0, "player_season_stats": 0}

        try:
            # Check what we already have
            existing_games = self.db.get_row_count("games")
            existing_stats = self.db.get_row_count("player_game_stats")
            existing_season = self.db.get_row_count("player_season_stats")

            logger.info(
                f"Current status: {existing_games} games, {existing_stats} game stats, {existing_season} season stats"
            )

            # Import games if missing
            if existing_games == 0:
                logger.info("Importing games data...")
                games_data = self.api_client.get_games(years=years)
                if games_data:
                    counts["games"] = self.game_importer.import_games(games_data)
            else:
                logger.info(f"Games already imported ({existing_games} records)")

            # Import player season stats if missing
            if existing_season == 0:
                logger.info("Importing player season statistics...")
                players_data = self.api_client.get_players(years=years)
                if players_data:
                    counts["player_season_stats"] = self._import_player_season_stats(
                        players_data, years
                    )
            else:
                logger.info(
                    f"Season stats already imported ({existing_season} records)"
                )

            logger.info(f"Missing imports complete. Imported: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Error completing missing imports: {e}")
            raise

    # ===== PRIVATE HELPER METHODS =====

    def _clear_database(self):
        """Clear all UFA data from the database."""
        tables = [
            "player_game_stats",
            "player_season_stats",
            "team_season_stats",
            "games",
            "players",
            "teams",
        ]
        for table in tables:
            try:
                self.db.execute_query(f"DELETE FROM {table}")
                logger.info(f"  Cleared {table}")
            except Exception as e:
                logger.warning(f"  Failed to clear {table}: {e}")

    def _import_player_game_stats_sequential(
        self, games_data: list[dict[str, Any]]
    ) -> int:
        """Import player game statistics for all games (sequential processing)."""
        count = 0
        skipped_allstar = 0
        total_games = len(games_data)

        for i, game in enumerate(games_data, 1):
            game_id = game.get("gameID", "")
            if not game_id:
                continue

            # Skip all-star games
            away_team_id = game.get("awayTeamID", "")
            home_team_id = game.get("homeTeamID", "")
            if self.stats_importer.is_allstar_game(game_id, away_team_id, home_team_id):
                skipped_allstar += 1
                continue

            try:
                # Get player game stats for this game
                player_stats_data = self.api_client.get_player_game_stats(game_id)

                for player_stat in player_stats_data:
                    try:
                        player_game_stat = self.stats_importer.import_player_game_stat(
                            player_stat, game_id
                        )
                        self.stats_importer.insert_player_game_stat(player_game_stat)
                        count += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to import player game stat for {player_stat.get('player', {}).get('playerID', 'unknown')}: {e}"
                        )

                # Import game events for this game
                try:
                    events_data = self.api_client.get_game_events(game_id)
                    if events_data:
                        events_count = self.events_importer.import_game_events(
                            game_id, events_data
                        )
                        if events_count > 0:
                            logger.info(
                                f"  Imported {events_count} events for game {game_id}"
                            )
                except Exception as e:
                    logger.warning(f"Failed to import events for game {game_id}: {e}")

                if i % 100 == 0:
                    logger.info(
                        f"  Processed {i}/{total_games} games, imported {count} player game stats so far"
                    )

            except Exception as e:
                logger.warning(f"Failed to get player stats for game {game_id}: {e}")

        if skipped_allstar > 0:
            logger.info(f"  Skipped {skipped_allstar} all-star games")
        logger.info(
            f"  Imported {count} player game stats from {total_games - skipped_allstar} regular games"
        )
        return count

    def _import_player_season_stats(
        self, players_data: list[dict[str, Any]], years: list[int]
    ) -> int:
        """Import player season statistics."""
        # Extract all unique player IDs
        player_ids = []
        for player in players_data:
            player_id = player.get("playerID", "")
            if player_id and player_id not in player_ids:
                player_ids.append(player_id)

        logger.info(
            f"  Fetching season stats for {len(player_ids)} players across {len(years)} years"
        )

        # Get season stats from API
        season_stats_data = self.api_client.get_player_stats(player_ids, years)

        # Import using stats importer
        return self.stats_importer.import_player_season_stats(
            season_stats_data, players_data
        )
