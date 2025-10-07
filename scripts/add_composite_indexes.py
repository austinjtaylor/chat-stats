#!/usr/bin/env python3
"""
Add composite indexes to improve player stats query performance.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def add_composite_indexes():
    """Add composite indexes for player stats queries."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return

    print(f"🔗 Connecting to database...")
    engine = create_engine(database_url)

    # Composite indexes to optimize player stats queries
    indexes = [
        # Player game stats - optimize JOINs on player_id, year, team_id
        "CREATE INDEX IF NOT EXISTS idx_player_game_stats_composite ON player_game_stats(player_id, year, team_id);",

        # Player season stats - optimize queries filtering by player, year, team
        "CREATE INDEX IF NOT EXISTS idx_player_season_stats_composite ON player_season_stats(player_id, year, team_id);",

        # Player season stats - optimize career queries (all years for a player)
        "CREATE INDEX IF NOT EXISTS idx_player_season_stats_player_year ON player_season_stats(player_id, year);",

        # Games - optimize year-based filtering in JOINs
        "CREATE INDEX IF NOT EXISTS idx_games_year_teams ON games(year, home_team_id, away_team_id);",
    ]

    with engine.connect() as conn:
        for idx, index_sql in enumerate(indexes, 1):
            try:
                print(f"📊 Creating index {idx}/{len(indexes)}...")
                conn.execute(text(index_sql))
                conn.commit()
                print(f"✅ Index {idx} created successfully")
            except Exception as e:
                print(f"⚠️  Index {idx} error (may already exist): {str(e)[:100]}")

    print("\n✅ All composite indexes added successfully!")
    print("\nIndexes created:")
    for i, idx_sql in enumerate(indexes, 1):
        # Extract index name from SQL
        idx_name = idx_sql.split("INDEX IF NOT EXISTS ")[1].split(" ON ")[0]
        print(f"  {i}. {idx_name}")

if __name__ == "__main__":
    add_composite_indexes()
