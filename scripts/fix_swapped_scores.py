#!/usr/bin/env python3
"""
One-time migration script to fix swapped home/away scores in the database.
The UFA API was returning scores in the wrong fields, causing home_score and away_score to be swapped.
"""

import logging
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from backend.data.database import get_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_swapped_scores():
    """Fix all swapped scores in the games table."""
    db = get_db()

    try:
        # First, let's verify the issue exists by checking a known game
        test_query = """
        SELECT game_id, home_team_id, away_team_id, home_score, away_score 
        FROM games 
        WHERE game_id = '2025-08-23-BOS-MIN'
        """

        result = db.execute_query(test_query)
        if result:
            game = result[0]
            logger.info(
                f"Before fix - Game {game['game_id']}: "
                f"{game['home_team_id']} (home) {game['home_score']} - "
                f"{game['away_score']} {game['away_team_id']} (away)"
            )

        # Swap all scores in the games table
        logger.info("Swapping home_score and away_score for all games...")

        swap_query = """
        UPDATE games 
        SET home_score = away_score,
            away_score = home_score
        """

        db.execute_query(swap_query)
        logger.info("Scores swapped successfully!")

        # Verify the fix
        result = db.execute_query(test_query)
        if result:
            game = result[0]
            logger.info(
                f"After fix - Game {game['game_id']}: "
                f"{game['home_team_id']} (home) {game['home_score']} - "
                f"{game['away_score']} {game['away_team_id']} (away)"
            )

        # Show some recent games to verify
        verify_query = """
        SELECT g.game_id, 
               ht.name as home_team_name, g.home_score,
               at.name as away_team_name, g.away_score
        FROM games g
        JOIN teams ht ON ht.team_id = g.home_team_id AND g.year = ht.year
        JOIN teams at ON at.team_id = g.away_team_id AND g.year = at.year
        WHERE g.game_type <> 'allstar'
        ORDER BY g.start_timestamp DESC
        LIMIT 5
        """

        recent_games = db.execute_query(verify_query)
        logger.info("\nRecent games after fix:")
        for game in recent_games:
            logger.info(
                f"  {game['away_team_name']} @ {game['home_team_name']}: "
                f"{game['away_score']}-{game['home_score']}"
            )

        return True

    except Exception as e:
        logger.error(f"Error fixing scores: {e}")
        return False


if __name__ == "__main__":
    logger.info("Starting score fix migration...")
    if fix_swapped_scores():
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        sys.exit(1)
