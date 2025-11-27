#!/usr/bin/env python3
"""
Script to remove All Stars data from the database.

This script removes:
- All Star teams
- All Star games
- Player game stats from All Star games
- Player season stats for All Star teams
- Team season stats for All Star teams
- Game events from All Star games
"""

import sys
from pathlib import Path

# Load environment variables first
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / ".env")

# Add backend to path
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from data.database import get_db


def remove_allstars_data():
    """Remove all All Stars related data from the database."""
    db = get_db()

    try:
        print("Starting All Stars data removal...")
        print("-" * 60)

        # Get counts before deletion
        print("\n📊 Current counts:")

        result = db.execute_query(
            "SELECT COUNT(*) as count FROM teams WHERE LOWER(team_id) LIKE '%allstar%' OR LOWER(name) LIKE '%all%star%'"
        )
        print(f"   All Star teams: {result[0]['count']}")

        result = db.execute_query(
            "SELECT COUNT(*) as count FROM games WHERE game_type = 'allstar' OR LOWER(game_id) LIKE '%allstar%' OR LOWER(home_team_id) LIKE '%allstar%' OR LOWER(away_team_id) LIKE '%allstar%'"
        )
        print(f"   All Star games: {result[0]['count']}")

        result = db.execute_query(
            "SELECT COUNT(*) as count FROM player_game_stats WHERE game_id IN (SELECT game_id FROM games WHERE game_type = 'allstar' OR LOWER(game_id) LIKE '%allstar%' OR LOWER(home_team_id) LIKE '%allstar%' OR LOWER(away_team_id) LIKE '%allstar%')"
        )
        print(f"   Player game stats (All Star games): {result[0]['count']}")

        result = db.execute_query(
            "SELECT COUNT(*) as count FROM player_season_stats WHERE team_id IN (SELECT team_id FROM teams WHERE LOWER(team_id) LIKE '%allstar%' OR LOWER(name) LIKE '%all%star%')"
        )
        print(f"   Player season stats (All Star teams): {result[0]['count']}")

        result = db.execute_query(
            "SELECT COUNT(*) as count FROM team_season_stats WHERE team_id IN (SELECT team_id FROM teams WHERE LOWER(team_id) LIKE '%allstar%' OR LOWER(name) LIKE '%all%star%')"
        )
        print(f"   Team season stats (All Star teams): {result[0]['count']}")

        result = db.execute_query(
            "SELECT COUNT(*) as count FROM game_events WHERE game_id IN (SELECT game_id FROM games WHERE game_type = 'allstar' OR LOWER(game_id) LIKE '%allstar%' OR LOWER(home_team_id) LIKE '%allstar%' OR LOWER(away_team_id) LIKE '%allstar%')"
        )
        print(f"   Game events (All Star games): {result[0]['count']}")

        # Confirm deletion
        print("\n⚠️  This will permanently delete all All Stars data.")
        confirmation = input("Continue? (yes/no): ").strip().lower()

        if confirmation != "yes":
            print("❌ Aborted.")
            return

        print("\n🗑️  Deleting All Stars data...")

        # Use a connection to execute deletions in a transaction
        with db.engine.begin() as conn:
            # Delete in order to respect foreign key constraints

            # 1. Delete game events for All Star games
            result = conn.execute(
                text(
                    """
                DELETE FROM game_events
                WHERE game_id IN (
                    SELECT game_id FROM games
                    WHERE game_type = 'allstar'
                       OR LOWER(game_id) LIKE '%allstar%'
                       OR LOWER(home_team_id) LIKE '%allstar%'
                       OR LOWER(away_team_id) LIKE '%allstar%'
                )
            """
                )
            )
            print(f"   ✓ Deleted {result.rowcount} game events")

            # 2. Delete player game stats for All Star games
            result = conn.execute(
                text(
                    """
                DELETE FROM player_game_stats
                WHERE game_id IN (
                    SELECT game_id FROM games
                    WHERE game_type = 'allstar'
                       OR LOWER(game_id) LIKE '%allstar%'
                       OR LOWER(home_team_id) LIKE '%allstar%'
                       OR LOWER(away_team_id) LIKE '%allstar%'
                )
            """
                )
            )
            print(f"   ✓ Deleted {result.rowcount} player game stats records")

            # 3. Delete All Star games
            result = conn.execute(
                text(
                    """
                DELETE FROM games
                WHERE game_type = 'allstar'
                   OR LOWER(game_id) LIKE '%allstar%'
                   OR LOWER(home_team_id) LIKE '%allstar%'
                   OR LOWER(away_team_id) LIKE '%allstar%'
            """
                )
            )
            print(f"   ✓ Deleted {result.rowcount} All Star games")

            # 4. Delete player season stats for All Star teams
            result = conn.execute(
                text(
                    """
                DELETE FROM player_season_stats
                WHERE team_id IN (
                    SELECT team_id FROM teams
                    WHERE LOWER(team_id) LIKE '%allstar%'
                       OR LOWER(name) LIKE '%all%star%'
                )
            """
                )
            )
            print(f"   ✓ Deleted {result.rowcount} player season stats records")

            # 5. Delete team season stats for All Star teams
            result = conn.execute(
                text(
                    """
                DELETE FROM team_season_stats
                WHERE team_id IN (
                    SELECT team_id FROM teams
                    WHERE LOWER(team_id) LIKE '%allstar%'
                       OR LOWER(name) LIKE '%all%star%'
                )
            """
                )
            )
            print(f"   ✓ Deleted {result.rowcount} team season stats records")

            # 6. Delete All Star teams
            result = conn.execute(
                text(
                    """
                DELETE FROM teams
                WHERE LOWER(team_id) LIKE '%allstar%'
                   OR LOWER(name) LIKE '%all%star%'
            """
                )
            )
            print(f"   ✓ Deleted {result.rowcount} All Star teams")

        print("\n✅ All Stars data removed successfully!")
        print("-" * 60)

        # Show final counts
        print("\n📊 Final counts:")
        result = db.execute_query("SELECT COUNT(*) as count FROM teams")
        print(f"   Total teams remaining: {result[0]['count']}")

        result = db.execute_query("SELECT COUNT(*) as count FROM games")
        print(f"   Total games remaining: {result[0]['count']}")

        result = db.execute_query("SELECT COUNT(*) as count FROM player_game_stats")
        print(f"   Total player game stats remaining: {result[0]['count']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    remove_allstars_data()
