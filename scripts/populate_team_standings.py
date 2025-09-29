#!/usr/bin/env python3
"""
Script to populate team_season_stats table from teams table data.
The teams table already contains win/loss/standing data from the UFA API.
"""

import logging
import sqlite3
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def populate_team_season_stats(db_path: str = "./db/sports_stats.db") -> int:
    """
    Populate team_season_stats table from teams table data.

    Args:
        db_path: Path to the SQLite database

    Returns:
        Number of records inserted
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Clear existing team_season_stats
        cursor.execute("DELETE FROM team_season_stats")
        logger.info("Cleared existing team_season_stats records")

        # Insert data from teams table (excluding all-star teams)
        insert_query = """
        INSERT INTO team_season_stats
            (team_id, year, wins, losses, ties, standing, division_id, division_name, points_for, points_against)
        SELECT
            team_id,
            year,
            wins,
            losses,
            ties,
            standing,
            division_id,
            division_name,
            0 as points_for,  -- These would need to be calculated from games
            0 as points_against
        FROM teams
        WHERE team_id NOT IN ('allstars1', 'allstars2')
        ORDER BY year DESC, standing ASC
        """

        cursor.execute(insert_query)
        records_inserted = cursor.rowcount

        # Calculate points for/against from games table if available
        update_points_query = """
        WITH team_points AS (
            SELECT
                team_id,
                year,
                SUM(points_for) as total_points_for,
                SUM(points_against) as total_points_against
            FROM (
                -- Home games
                SELECT
                    home_team_id as team_id,
                    year,
                    home_score as points_for,
                    away_score as points_against
                FROM games
                WHERE status = 'Final'

                UNION ALL

                -- Away games
                SELECT
                    away_team_id as team_id,
                    year,
                    away_score as points_for,
                    home_score as points_against
                FROM games
                WHERE status = 'Final'
            )
            GROUP BY team_id, year
        )
        UPDATE team_season_stats
        SET
            points_for = (
                SELECT total_points_for
                FROM team_points tp
                WHERE tp.team_id = team_season_stats.team_id
                AND tp.year = team_season_stats.year
            ),
            points_against = (
                SELECT total_points_against
                FROM team_points tp
                WHERE tp.team_id = team_season_stats.team_id
                AND tp.year = team_season_stats.year
            )
        WHERE EXISTS (
            SELECT 1
            FROM team_points tp
            WHERE tp.team_id = team_season_stats.team_id
            AND tp.year = team_season_stats.year
        )
        """

        cursor.execute(update_points_query)
        records_updated = cursor.rowcount
        logger.info(f"Updated {records_updated} records with points for/against")

        conn.commit()
        logger.info(
            f"Successfully inserted {records_inserted} team season stats records"
        )

        # Verify the data
        cursor.execute("SELECT COUNT(*) FROM team_season_stats")
        total_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT year, COUNT(*) as team_count
            FROM team_season_stats
            GROUP BY year
            ORDER BY year DESC
            LIMIT 5
        """
        )
        year_summary = cursor.fetchall()

        logger.info(f"Total records in team_season_stats: {total_count}")
        logger.info("Team counts by year:")
        for year, count in year_summary:
            logger.info(f"  {year}: {count} teams")

        return records_inserted

    except Exception as e:
        logger.error(f"Error populating team_season_stats: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    """Main entry point."""
    import sys

    # Check if database exists
    db_path = "./db/sports_stats.db"
    if not Path(db_path).exists():
        logger.error(f"Database not found at {db_path}")
        sys.exit(1)

    try:
        records = populate_team_season_stats(db_path)
        logger.info(f"Population complete. {records} team season records created.")
    except Exception as e:
        logger.error(f"Failed to populate team_season_stats: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
