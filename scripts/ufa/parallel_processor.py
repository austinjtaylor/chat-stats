#!/usr/bin/env python3
"""
Parallel processing for UFA data import operations.
"""

import logging
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any

# Add paths for imports when running as subprocess
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.append(os.path.join(os.path.dirname(__file__), "../..", "backend"))

from backend.data.database import get_db
from scripts.ufa.api_client import UFAAPIClient
from scripts.ufa.importers import StatsImporter, EventsImporter


def process_game_stats_chunk(game_chunk_data: tuple[list[dict], int]) -> dict[str, int]:
    """
    Helper function to import player game stats for a chunk of games.
    This function runs in a separate process for parallel processing.

    Args:
        game_chunk_data: Tuple of (games_list, chunk_number)

    Returns:
        Dictionary with import counts
    """
    games_chunk, chunk_num = game_chunk_data

    # Create new database connection for this process
    db = get_db()
    api_client = UFAAPIClient()
    stats_importer = StatsImporter(db)
    events_importer = EventsImporter(db)

    logger = logging.getLogger(__name__)
    logger.info(f"[Chunk {chunk_num}] Processing {len(games_chunk)} games")

    count = 0
    skipped_allstar = 0

    for _i, game in enumerate(games_chunk, 1):
        game_id = game.get("gameID", "")
        if not game_id:
            continue

        # Skip all-star games
        away_team_id = game.get("awayTeamID", "")
        home_team_id = game.get("homeTeamID", "")
        if stats_importer.is_allstar_game(game_id, away_team_id, home_team_id):
            skipped_allstar += 1
            continue

        try:
            # Get player game stats for this game
            player_stats_data = api_client.get_player_game_stats(game_id)

            for player_stat in player_stats_data:
                try:
                    player_game_stat = stats_importer.import_player_game_stat(
                        player_stat, game_id
                    )
                    stats_importer.insert_player_game_stat(player_game_stat)
                    count += 1
                except Exception as e:
                    logger.warning(
                        f"[Chunk {chunk_num}] Failed to import player game stat for {player_stat.get('player', {}).get('playerID', 'unknown')}: {e}"
                    )

        except Exception as e:
            logger.warning(
                f"[Chunk {chunk_num}] Failed to get player stats for game {game_id}: {e}"
            )

        # Import game events for this game
        try:
            events_data = api_client.get_game_events(game_id)
            if events_data:
                events_count = events_importer.import_game_events(game_id, events_data)
                if events_count > 0:
                    logger.info(
                        f"[Chunk {chunk_num}] Imported {events_count} events for game {game_id}"
                    )
        except Exception as e:
            logger.warning(
                f"[Chunk {chunk_num}] Failed to get events for game {game_id}: {e}"
            )

    if skipped_allstar > 0:
        logger.info(f"[Chunk {chunk_num}] Skipped {skipped_allstar} all-star games")
    logger.info(
        f"[Chunk {chunk_num}] Imported {count} player game stats from {len(games_chunk) - skipped_allstar} regular games"
    )

    return {
        "player_game_stats": count,
        "games_processed": len(games_chunk) - skipped_allstar,
    }


class ParallelProcessor:
    """Handles parallel processing of UFA data imports"""

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the parallel processor

        Args:
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(__name__)

    def import_player_game_stats_parallel(
        self, games_data: list[dict[str, Any]], workers: int
    ) -> int:
        """
        Import player game statistics using parallel processing

        Args:
            games_data: List of game dictionaries
            workers: Number of parallel workers

        Returns:
            Total count of player game stats imported
        """
        total_games = len(games_data)
        chunk_size = max(10, total_games // (workers * 2))

        # Split games into chunks
        chunks = []
        for i in range(0, total_games, chunk_size):
            chunk = games_data[i : i + chunk_size]
            chunks.append((chunk, i // chunk_size + 1))

        self.logger.info(
            f"  Processing {total_games} games in {len(chunks)} chunks with {workers} workers"
        )

        total_count = 0
        completed_chunks = 0

        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all chunks
            future_to_chunk = {
                executor.submit(process_game_stats_chunk, chunk_data): chunk_data[1]
                for chunk_data in chunks
            }

            # Process completed chunks
            for future in as_completed(future_to_chunk):
                chunk_num = future_to_chunk[future]
                try:
                    result = future.result()
                    total_count += result["player_game_stats"]
                    completed_chunks += 1

                    progress = (completed_chunks / len(chunks)) * 100
                    self.logger.info(
                        f"  Progress: {completed_chunks}/{len(chunks)} chunks completed ({progress:.1f}%)"
                    )

                except Exception as e:
                    self.logger.error(f"  Chunk {chunk_num} failed: {e}")

        self.logger.info(
            f"  Imported {total_count} player game stats from {total_games} games"
        )
        return total_count
