#!/usr/bin/env python
"""
Create and populate a pre-computed career stats table for faster queries.
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "sports_stats.db"


def create_career_stats_table():
    """Create the player_career_stats table."""

    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing table if it exists
    cursor.execute("DROP TABLE IF EXISTS player_career_stats")

    # Create the table
    print("Creating player_career_stats table...")
    cursor.execute("""
        CREATE TABLE player_career_stats (
            player_id TEXT PRIMARY KEY,
            full_name TEXT,
            first_name TEXT,
            last_name TEXT,
            most_recent_team_id TEXT,
            most_recent_team_name TEXT,
            most_recent_team_full_name TEXT,
            games_played INTEGER,
            total_goals INTEGER,
            total_assists INTEGER,
            total_hockey_assists INTEGER,
            total_blocks INTEGER,
            calculated_plus_minus INTEGER,
            total_completions INTEGER,
            completion_percentage REAL,
            total_yards_thrown INTEGER,
            total_yards_received INTEGER,
            total_yards INTEGER,
            total_throwaways INTEGER,
            total_stalls INTEGER,
            total_drops INTEGER,
            total_callahans INTEGER,
            total_hucks_completed INTEGER,
            total_hucks_attempted INTEGER,
            total_hucks_received INTEGER,
            huck_percentage REAL,
            total_pulls INTEGER,
            total_o_points_played INTEGER,
            total_d_points_played INTEGER,
            total_points_played INTEGER,
            total_seconds_played INTEGER,
            minutes_played INTEGER,
            total_o_opportunities INTEGER,
            total_d_opportunities INTEGER,
            total_o_opportunity_scores INTEGER,
            offensive_efficiency REAL,
            possessions INTEGER,
            score_total INTEGER,
            yards_per_turn REAL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes
    print("Creating indexes on career stats table...")
    indexes = [
        "CREATE INDEX idx_career_calculated_plus_minus ON player_career_stats(calculated_plus_minus DESC)",
        "CREATE INDEX idx_career_score_total ON player_career_stats(score_total DESC)",
        "CREATE INDEX idx_career_total_goals ON player_career_stats(total_goals DESC)",
        "CREATE INDEX idx_career_total_assists ON player_career_stats(total_assists DESC)",
        "CREATE INDEX idx_career_team ON player_career_stats(most_recent_team_id)",
    ]

    for idx_query in indexes:
        cursor.execute(idx_query)

    conn.commit()
    conn.close()
    print("✅ Career stats table created!")


def populate_career_stats():
    """Populate the career stats table with aggregated data."""

    print("\n📊 Populating career stats table...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    start_time = time.time()

    # Insert aggregated career stats
    cursor.execute("""
        INSERT INTO player_career_stats
        SELECT
            pss.player_id,
            p.full_name,
            p.first_name,
            p.last_name,
            p.most_recent_team_id,
            p.most_recent_team_name,
            p.most_recent_team_full_name,
            (SELECT COUNT(DISTINCT pgs_sub.game_id)
             FROM player_game_stats pgs_sub
             JOIN games g_sub ON pgs_sub.game_id = g_sub.game_id
             WHERE pgs_sub.player_id = pss.player_id
             AND (pgs_sub.o_points_played > 0 OR pgs_sub.d_points_played > 0 OR pgs_sub.seconds_played > 0 OR pgs_sub.goals > 0 OR pgs_sub.assists > 0)
            ) as games_played,
            SUM(pss.total_goals) as total_goals,
            SUM(pss.total_assists) as total_assists,
            SUM(pss.total_hockey_assists) as total_hockey_assists,
            SUM(pss.total_blocks) as total_blocks,
            (SUM(pss.total_goals) + SUM(pss.total_assists) + SUM(pss.total_blocks) -
             SUM(pss.total_throwaways) - SUM(pss.total_drops)) as calculated_plus_minus,
            SUM(pss.total_completions) as total_completions,
            CASE
                WHEN SUM(pss.total_throw_attempts) > 0
                THEN ROUND(SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts), 1)
                ELSE 0
            END as completion_percentage,
            SUM(pss.total_yards_thrown) as total_yards_thrown,
            SUM(pss.total_yards_received) as total_yards_received,
            (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
            SUM(pss.total_throwaways) as total_throwaways,
            SUM(pss.total_stalls) as total_stalls,
            SUM(pss.total_drops) as total_drops,
            SUM(pss.total_callahans) as total_callahans,
            SUM(pss.total_hucks_completed) as total_hucks_completed,
            SUM(pss.total_hucks_attempted) as total_hucks_attempted,
            SUM(pss.total_hucks_received) as total_hucks_received,
            CASE
                WHEN SUM(pss.total_hucks_attempted) > 0
                THEN ROUND(SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted), 1)
                ELSE 0
            END as huck_percentage,
            SUM(pss.total_pulls) as total_pulls,
            SUM(pss.total_o_points_played) as total_o_points_played,
            SUM(pss.total_d_points_played) as total_d_points_played,
            (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
            SUM(pss.total_seconds_played) as total_seconds_played,
            ROUND(SUM(pss.total_seconds_played) / 60.0, 0) as minutes_played,
            SUM(pss.total_o_opportunities) as total_o_opportunities,
            SUM(pss.total_d_opportunities) as total_d_opportunities,
            SUM(pss.total_o_opportunity_scores) as total_o_opportunity_scores,
            CASE
                WHEN SUM(pss.total_o_opportunities) >= 20
                THEN ROUND(SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities), 1)
                ELSE NULL
            END as offensive_efficiency,
            SUM(pss.total_o_opportunities) as possessions,
            (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
            CASE
                WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                THEN ROUND((SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 1)
                ELSE NULL
            END as yards_per_turn,
            CURRENT_TIMESTAMP
        FROM player_season_stats pss
        JOIN (SELECT DISTINCT pss2.player_id,
                     FIRST_VALUE(pl.full_name) OVER (PARTITION BY pss2.player_id ORDER BY pss2.year DESC) as full_name,
                     FIRST_VALUE(pl.first_name) OVER (PARTITION BY pss2.player_id ORDER BY pss2.year DESC) as first_name,
                     FIRST_VALUE(pl.last_name) OVER (PARTITION BY pss2.player_id ORDER BY pss2.year DESC) as last_name,
                     FIRST_VALUE(pss2.team_id) OVER (PARTITION BY pss2.player_id ORDER BY pss2.year DESC) as most_recent_team_id,
                     FIRST_VALUE(t2.name) OVER (PARTITION BY pss2.player_id ORDER BY pss2.year DESC) as most_recent_team_name,
                     FIRST_VALUE(t2.full_name) OVER (PARTITION BY pss2.player_id ORDER BY pss2.year DESC) as most_recent_team_full_name
              FROM player_season_stats pss2
              JOIN players pl ON pss2.player_id = pl.player_id AND pss2.year = pl.year
              LEFT JOIN teams t2 ON pss2.team_id = t2.team_id AND pss2.year = t2.year) p ON pss.player_id = p.player_id
        GROUP BY pss.player_id, p.full_name, p.first_name, p.last_name, p.most_recent_team_id, p.most_recent_team_name, p.most_recent_team_full_name
    """)

    conn.commit()

    # Get count of records
    cursor.execute("SELECT COUNT(*) FROM player_career_stats")
    count = cursor.fetchone()[0]

    elapsed = time.time() - start_time
    print(f"  Inserted {count} player career records in {elapsed:.2f}s")

    conn.close()
    print("✅ Career stats populated!")


def test_performance():
    """Test query performance with the new table."""

    print("\n⚡ Testing performance with career stats table...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Test original complex query
    query_original = """
    SELECT COUNT(*) FROM (
        SELECT
            p.full_name,
            SUM(pss.total_goals) as total_goals
        FROM player_season_stats pss
        JOIN (SELECT DISTINCT pss2.player_id,
                     FIRST_VALUE(pl.full_name) OVER (PARTITION BY pss2.player_id ORDER BY pss2.year DESC) as full_name
              FROM player_season_stats pss2
              JOIN players pl ON pss2.player_id = pl.player_id AND pss2.year = pl.year) p ON pss.player_id = p.player_id
        GROUP BY pss.player_id, p.full_name
        ORDER BY SUM(pss.total_goals) DESC
        LIMIT 20
    )
    """

    start_time = time.time()
    cursor.execute(query_original)
    result = cursor.fetchone()
    elapsed_original = time.time() - start_time

    print(f"  Original complex query: {elapsed_original:.3f}s")

    # Test new simple query
    query_new = """
    SELECT COUNT(*) FROM (
        SELECT full_name, total_goals
        FROM player_career_stats
        ORDER BY total_goals DESC
        LIMIT 20
    )
    """

    start_time = time.time()
    cursor.execute(query_new)
    result = cursor.fetchone()
    elapsed_new = time.time() - start_time

    print(f"  New simple query: {elapsed_new:.3f}s")
    print(f"  🚀 Speed improvement: {elapsed_original/elapsed_new:.1f}x faster!")

    conn.close()


if __name__ == "__main__":
    create_career_stats_table()
    populate_career_stats()
    test_performance()