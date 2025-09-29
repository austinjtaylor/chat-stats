#!/usr/bin/env python3
"""
Simple script to calculate and populate hucks_received statistics directly.
A huck is defined as a completed pass of 40+ vertical yards.
"""

import logging
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Calculate hucks received and update database directly"""

    # Connect to database
    db_path = Path(__file__).parent.parent / "db" / "sports_stats.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Starting hucks received calculation...")

    # Reset all hucks_received to 0
    logger.info("Resetting hucks_received values...")
    cursor.execute("UPDATE player_game_stats SET hucks_received = 0")
    cursor.execute("UPDATE player_season_stats SET total_hucks_received = 0")
    conn.commit()

    # Get all games with event data
    cursor.execute(
        """
        SELECT DISTINCT game_id
        FROM game_events
        WHERE thrower_y IS NOT NULL AND receiver_y IS NOT NULL
        ORDER BY game_id
    """
    )
    games = cursor.fetchall()
    logger.info(f"Found {len(games)} games with yardage data")

    # Process each game
    for idx, (game_id,) in enumerate(games, 1):
        if idx % 100 == 0:
            logger.info(f"Processing game {idx}/{len(games)}...")

        # Calculate hucks received for this game
        cursor.execute(
            """
            SELECT receiver_id, COUNT(*) as hucks_count
            FROM game_events
            WHERE game_id = ?
                AND event_type IN (18, 19)
                AND receiver_id IS NOT NULL
                AND thrower_y IS NOT NULL
                AND receiver_y IS NOT NULL
                AND ABS(receiver_y - thrower_y) >= 40
            GROUP BY receiver_id
        """,
            (game_id,),
        )

        hucks_data = cursor.fetchall()

        # Update player_game_stats for each player
        for receiver_id, hucks_count in hucks_data:
            cursor.execute(
                """
                UPDATE player_game_stats
                SET hucks_received = ?
                WHERE game_id = ? AND player_id = ?
            """,
                (hucks_count, game_id, receiver_id),
            )

    conn.commit()
    logger.info("Game-level hucks received updated")

    # Update season statistics
    logger.info("Updating season statistics...")
    cursor.execute(
        """
        UPDATE player_season_stats
        SET total_hucks_received = (
            SELECT SUM(hucks_received)
            FROM player_game_stats
            WHERE player_game_stats.player_id = player_season_stats.player_id
                AND player_game_stats.year = player_season_stats.year
        )
        WHERE EXISTS (
            SELECT 1
            FROM player_game_stats
            WHERE player_game_stats.player_id = player_season_stats.player_id
                AND player_game_stats.year = player_season_stats.year
                AND player_game_stats.hucks_received > 0
        )
    """
    )
    conn.commit()

    # Validate the calculation
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM game_events
        WHERE event_type IN (18, 19)
            AND receiver_id IS NOT NULL
            AND thrower_y IS NOT NULL
            AND receiver_y IS NOT NULL
            AND ABS(receiver_y - thrower_y) >= 40
    """
    )
    total_events = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(hucks_received) FROM player_game_stats")
    total_recorded = cursor.fetchone()[0] or 0

    logger.info("\nValidation Results:")
    logger.info(f"Total huck events: {total_events}")
    logger.info(f"Total hucks received recorded: {total_recorded}")
    logger.info(f"Match: {total_events == total_recorded}")

    # Get top receivers for 2024
    cursor.execute(
        """
        SELECT p.full_name, t.name, pss.total_hucks_received
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
        JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
        WHERE pss.year = 2024 AND pss.total_hucks_received > 0
        ORDER BY pss.total_hucks_received DESC
        LIMIT 10
    """
    )

    top_2024 = cursor.fetchall()
    logger.info("\nTop 10 Hucks Receivers for 2024:")
    for name, team, hucks in top_2024:
        logger.info(f"  {name} ({team}): {hucks}")

    # Get all-time top receivers
    cursor.execute(
        """
        SELECT p.full_name, SUM(pss.total_hucks_received) as total
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
        WHERE pss.total_hucks_received > 0
        GROUP BY p.player_id, p.full_name
        ORDER BY total DESC
        LIMIT 10
    """
    )

    top_all_time = cursor.fetchall()
    logger.info("\nTop 10 All-Time Hucks Receivers:")
    for name, hucks in top_all_time:
        logger.info(f"  {name}: {hucks}")

    conn.close()
    logger.info("\nHucks received calculation completed!")


if __name__ == "__main__":
    main()
