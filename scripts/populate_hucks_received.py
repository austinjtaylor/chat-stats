#!/usr/bin/env python3
"""
Populate hucks_received in player_game_stats from game_events data.

A huck is defined as a completed pass (PASS or GOAL event) with 40+ vertical yards.
This stat is NOT provided by the UFA API and must be calculated from game event coordinates.

Run this via: uv run python scripts/populate_hucks_received.py
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()


def populate_hucks_received(engine):
    """
    Calculate and populate hucks_received for all player game stats.

    Logic:
    - Query game_events for PASS (18) and GOAL (19) events
    - For each event, calculate vertical_yards = receiver_y - thrower_y
    - If vertical_yards >= 40, it's a huck received for that receiver
    - Update player_game_stats.hucks_received
    """
    print("🏈 Populating Hucks Received from Game Events")
    print("=" * 70)

    with engine.connect() as conn:
        # Check if we have game events data
        events_count = conn.execute(
            text("SELECT COUNT(*) FROM game_events WHERE event_type IN (18, 19)")
        ).fetchone()[0]
        print(f"  📊 Pass/Goal events to analyze: {events_count:,}")

        if events_count == 0:
            print(
                "  ❌ No pass/goal events found - hucks_received cannot be calculated"
            )
            return

        # Check current state
        current_hucks = (
            conn.execute(
                text("SELECT SUM(hucks_received) FROM player_game_stats")
            ).fetchone()[0]
            or 0
        )
        print(f"  📈 Current total hucks_received: {current_hucks:,}")

        # Reset hucks_received to 0 before recalculating
        print("\n  🔄 Resetting hucks_received to 0...")
        conn.execute(text("UPDATE player_game_stats SET hucks_received = 0"))
        conn.commit()
        print("  ✅ Reset complete")

        # Calculate hucks received using a batch UPDATE with subquery
        # A huck is a completed pass/goal with 40+ vertical yards
        print("\n  🔄 Calculating hucks received (40+ yard completions)...")

        update_query = """
        UPDATE player_game_stats pgs
        SET hucks_received = huck_counts.count
        FROM (
            SELECT
                ge.game_id,
                ge.receiver_id,
                COUNT(*) as count
            FROM game_events ge
            WHERE ge.event_type IN (18, 19)  -- PASS or GOAL
              AND ge.receiver_id IS NOT NULL
              AND ge.receiver_y IS NOT NULL
              AND ge.thrower_y IS NOT NULL
              AND (ge.receiver_y - ge.thrower_y) >= 40  -- 40+ vertical yards = huck
            GROUP BY ge.game_id, ge.receiver_id
        ) AS huck_counts
        WHERE pgs.game_id = huck_counts.game_id
          AND pgs.player_id = huck_counts.receiver_id
        """

        try:
            result = conn.execute(text(update_query))
            conn.commit()
            rows_updated = result.rowcount
            print(f"  ✅ Updated {rows_updated:,} player-game records")

            # Verify the update
            new_total = (
                conn.execute(
                    text("SELECT SUM(hucks_received) FROM player_game_stats")
                ).fetchone()[0]
                or 0
            )
            print(f"  ✅ New total hucks_received: {new_total:,}")

            # Show some sample data
            print("\n  📊 Sample players with hucks received:")
            sample_query = """
            SELECT
                p.full_name,
                g.game_id,
                pgs.hucks_received,
                pgs.hucks_completed
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.player_id AND pgs.year = p.year
            JOIN games g ON pgs.game_id = g.game_id
            WHERE pgs.hucks_received > 0
            ORDER BY pgs.hucks_received DESC
            LIMIT 10
            """
            samples = conn.execute(text(sample_query)).fetchall()

            print("     " + "-" * 66)
            print(f"     {'Player':<25} {'Game':<20} {'HR':>5} {'HCK':>5}")
            print("     " + "-" * 66)
            for row in samples:
                game_short = row[1][:17] + "..." if len(row[1]) > 20 else row[1]
                print(f"     {row[0]:<25} {game_short:<20} {row[2]:>5} {row[3]:>5}")

        except Exception as e:
            print(f"  ❌ Error updating hucks_received: {e}")
            conn.rollback()
            sys.exit(1)


def main():
    """Main function."""
    print("🚀 Starting Hucks Received Population")
    print("=" * 70)

    # Determine database connection
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("   Please set it in your .env file")
        sys.exit(1)

    print(f"🐘 PostgreSQL database: {database_url.split('@')[1].split('/')[0]}")
    engine = create_engine(database_url)

    populate_hucks_received(engine)

    print("\n" + "=" * 70)
    print("✅ HUCKS RECEIVED POPULATION COMPLETE!")
    print("=" * 70)
    print("\n📝 Next steps:")
    print("  1. Run: uv run python scripts/generate_season_stats.py")
    print("     This will aggregate hucks_received into player_season_stats")
    print("  2. Check the player stats page - HR column should now show values!")


if __name__ == "__main__":
    main()
