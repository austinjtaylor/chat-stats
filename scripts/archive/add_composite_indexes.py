#!/usr/bin/env python3
"""
Add composite indexes to improve player stats and team stats query performance.

This script adds critical indexes to optimize the following queries:
- Team stats aggregation (get_comprehensive_team_stats)
- Player stats queries
- Game lookups with team filtering

Run this on your production Supabase database to fix slow team stats page load times.
"""

import os
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()


def add_composite_indexes():
    """Add composite indexes for player stats and team stats queries."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        print(
            "   Please set DATABASE_URL in your .env file to point to your Supabase database"
        )
        return

    print(f"🔗 Connecting to database...")
    print(
        f"   Host: {database_url.split('@')[1].split('/')[0] if '@' in database_url else 'unknown'}"
    )
    engine = create_engine(database_url)

    # Composite indexes to optimize player stats and team stats queries
    indexes = [
        # ===== CRITICAL INDEXES FOR TEAM STATS QUERY PERFORMANCE =====
        # Player game stats - team_id is used heavily in aggregations but has no index
        "CREATE INDEX IF NOT EXISTS idx_player_game_stats_team_id ON player_game_stats(team_id);",
        # Player game stats - composite index for team aggregation with year filtering
        "CREATE INDEX IF NOT EXISTS idx_player_game_stats_team_year ON player_game_stats(team_id, year);",
        # Player game stats - composite index for game + team lookups
        "CREATE INDEX IF NOT EXISTS idx_player_game_stats_game_team ON player_game_stats(game_id, team_id);",
        # Games - separate indexes for home_team_id and away_team_id to handle OR conditions
        "CREATE INDEX IF NOT EXISTS idx_games_home_team ON games(home_team_id);",
        "CREATE INDEX IF NOT EXISTS idx_games_away_team ON games(away_team_id);",
        # Games - composite indexes for year-filtered team queries
        "CREATE INDEX IF NOT EXISTS idx_games_year_home_team ON games(year, home_team_id);",
        "CREATE INDEX IF NOT EXISTS idx_games_year_away_team ON games(year, away_team_id);",
        # ===== EXISTING COMPOSITE INDEXES FOR PLAYER STATS =====
        # Player game stats - optimize JOINs on player_id, year, team_id
        "CREATE INDEX IF NOT EXISTS idx_player_game_stats_composite ON player_game_stats(player_id, year, team_id);",
        # Player season stats - optimize queries filtering by player, year, team
        "CREATE INDEX IF NOT EXISTS idx_player_season_stats_composite ON player_season_stats(player_id, year, team_id);",
        # Player season stats - optimize career queries (all years for a player)
        "CREATE INDEX IF NOT EXISTS idx_player_season_stats_player_year ON player_season_stats(player_id, year);",
    ]

    print(f"\n📊 Creating {len(indexes)} indexes...")
    print(f"   This may take several minutes for large tables.\n")

    created = 0
    existed = 0
    errors = 0
    start_time = time.time()

    with engine.connect() as conn:
        for idx, index_sql in enumerate(indexes, 1):
            # Extract index name from SQL
            idx_name = index_sql.split("INDEX IF NOT EXISTS ")[1].split(" ON ")[0]
            table_name = index_sql.split(" ON ")[1].split("(")[0]

            try:
                print(
                    f"  [{idx}/{len(indexes)}] Creating {idx_name} on {table_name}...",
                    end=" ",
                    flush=True,
                )
                index_start = time.time()
                conn.execute(text(index_sql))
                conn.commit()
                index_time = time.time() - index_start
                print(f"✅ ({index_time:.2f}s)")
                created += 1
            except Exception as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower():
                    print(f"⚠️  (already exists)")
                    existed += 1
                else:
                    print(f"❌ Error: {error_msg[:80]}")
                    errors += 1

    elapsed = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"✅ Index creation complete!")
    print(f"{'='*60}")
    print(f"  Created: {created}")
    print(f"  Already existed: {existed}")
    print(f"  Errors: {errors}")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"\n🎉 Team stats query should now be significantly faster!")


if __name__ == "__main__":
    add_composite_indexes()
