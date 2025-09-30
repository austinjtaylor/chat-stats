#!/usr/bin/env python
"""
Database optimization script to add performance indexes.
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "sports_stats.db"


def add_indexes():
    """Add performance indexes to the database."""

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Dictionary of index name -> CREATE INDEX statement
    indexes = {
        # Player season stats indexes for common queries
        "idx_pss_calculated_plus_minus":
            "CREATE INDEX IF NOT EXISTS idx_pss_calculated_plus_minus ON player_season_stats(calculated_plus_minus DESC)",

        "idx_pss_year_team":
            "CREATE INDEX IF NOT EXISTS idx_pss_year_team ON player_season_stats(year, team_id)",

        "idx_pss_team_year":
            "CREATE INDEX IF NOT EXISTS idx_pss_team_year ON player_season_stats(team_id, year)",

        # Common sort columns
        "idx_pss_total_goals":
            "CREATE INDEX IF NOT EXISTS idx_pss_total_goals ON player_season_stats(total_goals DESC)",

        "idx_pss_total_assists":
            "CREATE INDEX IF NOT EXISTS idx_pss_total_assists ON player_season_stats(total_assists DESC)",

        "idx_pss_score_total":
            "CREATE INDEX IF NOT EXISTS idx_pss_score_total ON player_season_stats((total_goals + total_assists) DESC)",

        # Player game stats indexes
        "idx_pgs_player_year_team":
            "CREATE INDEX IF NOT EXISTS idx_pgs_player_year_team ON player_game_stats(player_id, year, team_id)",

        "idx_pgs_game_player":
            "CREATE INDEX IF NOT EXISTS idx_pgs_game_player ON player_game_stats(game_id, player_id)",

        # Games indexes
        "idx_games_year":
            "CREATE INDEX IF NOT EXISTS idx_games_year ON games(year)",

        # Players indexes
        "idx_players_year":
            "CREATE INDEX IF NOT EXISTS idx_players_year ON players(year)",

        # Teams indexes
        "idx_teams_year":
            "CREATE INDEX IF NOT EXISTS idx_teams_year ON teams(year)",
    }

    print(f"\nAdding {len(indexes)} performance indexes...")

    for index_name, create_statement in indexes.items():
        try:
            print(f"  Creating {index_name}...", end="")
            start_time = time.time()
            cursor.execute(create_statement)
            elapsed = time.time() - start_time
            print(f" ✓ ({elapsed:.2f}s)")
        except sqlite3.Error as e:
            print(f" ✗ Error: {e}")

    # Commit changes
    conn.commit()

    # Run ANALYZE to update SQLite's query planner statistics
    print("\nUpdating query planner statistics...")
    cursor.execute("ANALYZE")
    conn.commit()

    # Show current indexes
    print("\nCurrent indexes on player_season_stats:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='player_season_stats'")
    for row in cursor.fetchall():
        print(f"  - {row[0]}")

    conn.close()
    print("\n✅ Database optimization complete!")


def check_performance():
    """Run a sample query to check performance."""
    print("\n📊 Testing query performance...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Test the default career stats query
    query = """
    SELECT COUNT(DISTINCT player_id) as player_count
    FROM player_season_stats
    WHERE 1=1
    """

    start_time = time.time()
    cursor.execute(query)
    result = cursor.fetchone()
    elapsed = time.time() - start_time

    print(f"  Total players: {result[0]}")
    print(f"  Query time: {elapsed:.3f}s")

    # Test a complex aggregation
    query = """
    SELECT
        COUNT(*) as rows,
        SUM(total_goals) as goals,
        SUM(total_assists) as assists
    FROM player_season_stats
    WHERE year >= 2020
    """

    start_time = time.time()
    cursor.execute(query)
    result = cursor.fetchone()
    elapsed = time.time() - start_time

    print(f"\n  Recent seasons aggregation:")
    print(f"    Rows: {result[0]}, Goals: {result[1]}, Assists: {result[2]}")
    print(f"    Query time: {elapsed:.3f}s")

    conn.close()


if __name__ == "__main__":
    add_indexes()
    check_performance()