#!/usr/bin/env python3
"""
Generate player_season_stats by aggregating player_game_stats.
Run this via Railway: railway run uv run python scripts/generate_season_stats.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def generate_player_season_stats(engine):
    """Generate player_season_stats from player_game_stats aggregation."""
    print("📊 Generating player_season_stats from player_game_stats...")
    print("=" * 60)

    with engine.connect() as conn:
        # Check if player_game_stats has data
        game_stats_count = conn.execute(
            text("SELECT COUNT(*) FROM player_game_stats")
        ).fetchone()[0]
        print(f"  Player game stats records: {game_stats_count:,}")

        if game_stats_count == 0:
            print("  ❌ No player_game_stats data to aggregate")
            return

        # Aggregate player_game_stats into player_season_stats
        print("  🔄 Aggregating player game stats by (player_id, team_id, year)...")

        aggregate_query = """
        INSERT INTO player_season_stats (
            player_id,
            team_id,
            year,
            total_assists,
            total_goals,
            total_hockey_assists,
            total_completions,
            total_throw_attempts,
            total_throwaways,
            total_stalls,
            total_callahans_thrown,
            total_yards_received,
            total_yards_thrown,
            total_hucks_attempted,
            total_hucks_completed,
            total_hucks_received,
            total_catches,
            total_drops,
            total_blocks,
            total_callahans,
            total_pulls,
            total_ob_pulls,
            total_recorded_pulls,
            total_recorded_pulls_hangtime,
            total_o_points_played,
            total_o_points_scored,
            total_d_points_played,
            total_d_points_scored,
            total_seconds_played,
            total_o_opportunities,
            total_o_opportunity_scores,
            total_d_opportunities,
            total_d_opportunity_stops,
            completion_percentage
        )
        SELECT
            player_id,
            team_id,
            year,
            SUM(assists) as total_assists,
            SUM(goals) as total_goals,
            SUM(hockey_assists) as total_hockey_assists,
            SUM(completions) as total_completions,
            SUM(throw_attempts) as total_throw_attempts,
            SUM(throwaways) as total_throwaways,
            SUM(stalls) as total_stalls,
            SUM(callahans_thrown) as total_callahans_thrown,
            SUM(yards_received) as total_yards_received,
            SUM(yards_thrown) as total_yards_thrown,
            SUM(hucks_attempted) as total_hucks_attempted,
            SUM(hucks_completed) as total_hucks_completed,
            SUM(hucks_received) as total_hucks_received,
            SUM(catches) as total_catches,
            SUM(drops) as total_drops,
            SUM(blocks) as total_blocks,
            SUM(callahans) as total_callahans,
            SUM(pulls) as total_pulls,
            SUM(ob_pulls) as total_ob_pulls,
            SUM(recorded_pulls) as total_recorded_pulls,
            SUM(recorded_pulls_hangtime) as total_recorded_pulls_hangtime,
            SUM(o_points_played) as total_o_points_played,
            SUM(o_points_scored) as total_o_points_scored,
            SUM(d_points_played) as total_d_points_played,
            SUM(d_points_scored) as total_d_points_scored,
            SUM(seconds_played) as total_seconds_played,
            SUM(o_opportunities) as total_o_opportunities,
            SUM(o_opportunity_scores) as total_o_opportunity_scores,
            SUM(d_opportunities) as total_d_opportunities,
            SUM(d_opportunity_stops) as total_d_opportunity_stops,
            CASE
                WHEN SUM(completions) + SUM(throwaways) + SUM(drops) > 0
                THEN ROUND((CAST(SUM(completions) AS NUMERIC) / (SUM(completions) + SUM(throwaways) + SUM(drops))) * 100, 2)
                ELSE 0
            END as completion_percentage
        FROM player_game_stats
        GROUP BY player_id, team_id, year
        ON CONFLICT (player_id, team_id, year) DO NOTHING
        """

        try:
            result = conn.execute(text(aggregate_query))
            conn.commit()
            print(f"  ✅ Aggregated season stats successfully")

            # Verify count
            season_stats_count = conn.execute(
                text("SELECT COUNT(*) FROM player_season_stats")
            ).fetchone()[0]
            print(f"  ✅ Player season stats records: {season_stats_count:,}")

        except Exception as e:
            print(f"  ❌ Error aggregating season stats: {str(e)}")
            conn.rollback()
            sys.exit(1)


def main():
    """Main function."""
    print("🚀 Starting Season Stats Generation")
    print("=" * 60)

    # Determine database connection
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        print(f"🐘 PostgreSQL database: {database_url.split('@')[1].split('/')[0]}")
        engine = create_engine(database_url)
    else:
        # Use local SQLite
        sqlite_db_path = os.path.join(
            os.path.dirname(__file__), "..", "db", "sports_stats.db"
        )
        print(f"📁 SQLite database: {sqlite_db_path}")

        if not os.path.exists(sqlite_db_path):
            print(f"❌ SQLite database not found at {sqlite_db_path}")
            sys.exit(1)

        engine = create_engine(f"sqlite:///{sqlite_db_path}")

    generate_player_season_stats(engine)

    print("\n" + "=" * 60)
    print("✅ SEASON STATS GENERATION COMPLETE!")
    print("=" * 60)
    print("\n📝 Next step:")
    print("  Run: REFRESH MATERIALIZED VIEW player_career_stats;")


if __name__ == "__main__":
    main()
