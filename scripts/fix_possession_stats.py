#!/usr/bin/env python3
"""
Fix OLC% and DLC% stats for 2014-2019 seasons.

The UFA API doesn't have game_events for 2014-2019, so we manually update
the o_line_conversion and d_line_conversion columns with data from WatchUFA.
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch

load_dotenv()

# Data extracted from WatchUFA screenshots
WATCHUFA_DATA = {
    2014: {
        "Spiders": (54.32, 51.61),
        "Rush": (52.03, 52.45),
        "Radicals": (49.88, 49.59),
        "Empire": (46.85, 43.09),
        "FlameThrowers": (43.24, 42.21),
        "Breeze": (44.16, 50.20),
        "AlleyCats": (45.19, 37.75),
        "Union": (49.15, 39.29),
        "Riptide": (45.18, 45.62),
        "Wind Chill": (49.66, 47.89),
        "Royal": (42.50, 47.39),
        "Revolution": (37.65, 36.07),
        "Cascades": (36.97, 35.31),
        "Phoenix": (36.99, 31.87),
        "Dragons": (31.62, 29.81),
        "Lions": (27.75, 22.88),
        "Mechanix": (29.20, 22.89),
    },
    2015: {
        "Radicals": (52.95, 49.60),
        "Rush": (55.75, 49.50),
        "Spiders": (50.92, 42.07),
        "Thunderbirds": (55.44, 52.94),
        "Empire": (43.97, 47.11),
        "Flyers": (51.11, 47.59),
        "Cannons": (49.70, 47.08),
        "Hustle": (53.32, 43.17),
        "Cascades": (51.16, 47.27),
        "Royal": (42.75, 42.70),
        "FlameThrowers": (44.38, 44.74),
        "Union": (44.32, 43.70),
        "AlleyCats": (51.14, 43.28),
        "Breeze": (40.57, 45.22),
        "Growlers": (47.72, 47.24),
        "Outlaws": (46.01, 43.67),
        "Wind Chill": (35.47, 42.91),
        "Aviators": (43.82, 42.72),
        "Riptide": (51.68, 39.49),
        "Express": (39.76, 42.59),
        "Nightwatch": (43.88, 28.10),
        "Revolution": (36.56, 26.82),
        "Dragons": (36.10, 30.89),
        "Phoenix": (36.03, 36.27),
        "Mechanix": (31.75, 24.00),
    },
    2016: {
        "Legion": (58.10, 49.39),
        "Radicals": (53.01, 46.28),
        "Rush": (49.59, 47.44),
        "Cascades": (49.53, 50.91),
        "Breeze": (47.05, 51.14),
        "FlameThrowers": (51.50, 45.67),
        "Thunderbirds": (47.82, 45.65),
        "Aviators": (50.33, 48.06),
        "Flyers": (49.26, 41.95),
        "Wind Chill": (39.21, 40.91),
        "AlleyCats": (49.34, 45.95),
        "Hustle": (50.09, 39.41),
        "Empire": (44.66, 41.06),
        "Outlaws": (45.47, 41.91),
        "Sol": (46.68, 41.55),
        "Riptide": (50.10, 47.09),
        "Royal": (39.77, 40.72),
        "Cannons": (49.80, 40.10),
        "Spiders": (48.41, 43.13),
        "Express": (39.61, 37.77),
        "Mechanix": (35.35, 27.63),
        "Union": (35.97, 35.09),
        "Nightwatch": (44.24, 34.44),
        "Growlers": (43.66, 42.93),
        "Phoenix": (32.03, 22.52),
        "Revolution": (36.60, 25.00),
    },
    2017: {
        "FlameThrowers": (55.98, 47.78),
        "Flyers": (53.29, 50.55),
        "Legion": (53.99, 44.70),
        "Radicals": (52.21, 45.36),
        "Rush": (51.00, 49.85),
        "Breeze": (51.30, 45.48),
        "Wind Chill": (45.03, 40.66),
        "Aviators": (52.21, 48.98),
        "Cannons": (54.62, 45.45),
        "Thunderbirds": (46.41, 41.64),
        "Royal": (43.40, 37.55),
        "Spiders": (56.01, 38.62),
        "Cascades": (52.05, 46.49),
        "Growlers": (49.23, 47.21),
        "Empire": (45.31, 41.88),
        "AlleyCats": (46.20, 44.07),
        "Hustle": (54.89, 40.00),
        "Phoenix": (45.59, 39.70),
        "Sol": (51.10, 36.55),
        "Union": (40.17, 37.14),
        "Outlaws": (42.88, 35.29),
        "Mechanix": (31.28, 26.09),
        "Riptide": (38.89, 33.15),
        "Nightwatch": (40.47, 22.30),
    },
    2018: {
        "Legion": (53.72, 34.67),
        "Radicals": (61.10, 47.80),
        "Rush": (48.57, 47.40),
        "AlleyCats": (52.35, 40.97),
        "Aviators": (53.17, 47.18),
        "Flyers": (55.19, 52.43),
        "Empire": (50.86, 48.80),
        "Breeze": (47.66, 44.49),
        "Wind Chill": (54.36, 43.53),
        "Growlers": (49.40, 47.16),
        "Hustle": (52.75, 52.76),
        "Royal": (45.22, 38.97),
        "Sol": (46.46, 43.06),
        "Spiders": (48.88, 34.85),
        "Cascades": (48.87, 37.20),
        "FlameThrowers": (49.71, 29.91),
        "Phoenix": (47.82, 29.96),
        "Union": (50.78, 44.88),
        "Cannons": (51.24, 46.55),
        "Thunderbirds": (41.68, 34.24),
        "Nightwatch": (46.47, 33.33),
        "Outlaws": (45.65, 38.30),
        "Mechanix": (33.72, 29.59),
    },
    2019: {
        "Empire": (58.85, 49.75),
        "Growlers": (60.57, 46.57),
        "Flyers": (56.41, 53.67),
        "Legion": (52.26, 42.02),
        "AlleyCats": (56.76, 37.63),
        "Aviators": (56.49, 51.06),
        "Thunderbirds": (54.50, 47.42),
        "Rush": (52.30, 41.51),
        "Breeze": (57.62, 39.67),
        "Union": (53.89, 47.19),
        "Radicals": (49.38, 52.00),
        "Wind Chill": (51.78, 40.68),
        "Hustle": (55.76, 45.59),
        "Cannons": (47.27, 39.33),
        "Phoenix": (43.78, 33.54),
        "Royal": (49.45, 39.04),
        "Outlaws": (44.47, 34.23),
        "Sol": (43.49, 39.49),
        "Spiders": (49.75, 48.46),
        "Cascades": (52.36, 39.10),
        "Mechanix": (34.04, 28.71),
    },
}


def get_connection():
    """Get database connection."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url)


def calculate_hold_break_from_pgs(cursor, team_id, year):
    """
    Calculate HLD% and BRK% from player_game_stats.
    Returns (hold_pct, break_pct) or (None, None) if no data.
    """
    cursor.execute(
        """
        WITH game_team_stats AS (
            SELECT
                pgs.team_id,
                pgs.game_id,
                MAX(pgs.o_points_played) as o_points,
                MAX(pgs.d_points_played) as d_points,
                MAX(pgs.o_points_scored) as o_scored,
                MAX(pgs.d_points_scored) as d_scored
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id
            WHERE pgs.team_id = %s AND g.year = %s
              AND g.game_type NOT IN ('all-star', 'showcase', 'preseason')
            GROUP BY pgs.team_id, pgs.game_id
        )
        SELECT
            SUM(o_points) as o_line_points,
            SUM(o_scored) as o_line_scores,
            SUM(d_points) as d_line_points,
            SUM(d_scored) as d_line_scores
        FROM game_team_stats
        """,
        (team_id, year),
    )
    row = cursor.fetchone()

    if not row or row[0] is None:
        return None, None

    o_line_points = row[0] or 0
    o_line_scores = row[1] or 0
    d_line_points = row[2] or 0
    d_line_scores = row[3] or 0

    hold_pct = round((o_line_scores / o_line_points) * 100, 2) if o_line_points > 0 else None
    break_pct = round((d_line_scores / d_line_points) * 100, 2) if d_line_points > 0 else None

    return hold_pct, break_pct


def update_possession_stats():
    """Update o_line_conversion and d_line_conversion for 2014-2019."""
    conn = get_connection()
    cursor = conn.cursor()

    total_updated = 0
    total_inserted = 0
    total_not_found = 0
    total_hld_calculated = 0

    for year, teams in WATCHUFA_DATA.items():
        print(f"\nProcessing {year}...")

        for team_name, (olc, dlc) in teams.items():
            # First, get the team_id from the teams table
            cursor.execute(
                """
                SELECT team_id, wins, losses, ties, standing, division_id, division_name
                FROM teams
                WHERE year = %s AND name = %s
                """,
                (year, team_name),
            )
            team_row = cursor.fetchone()

            if not team_row:
                print(f"  NOT FOUND in teams: {team_name} ({year})")
                total_not_found += 1
                continue

            team_id, wins, losses, ties, standing, div_id, div_name = team_row

            # Calculate HLD% and BRK% from player_game_stats if available
            hold_pct, break_pct = calculate_hold_break_from_pgs(cursor, team_id, year)
            if hold_pct is not None:
                total_hld_calculated += 1

            # Check if record exists in team_season_stats
            cursor.execute(
                """
                SELECT id FROM team_season_stats
                WHERE team_id = %s AND year = %s
                """,
                (team_id, year),
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing record with OLC%, DLC%, and HLD%/BRK% if available
                if hold_pct is not None:
                    cursor.execute(
                        """
                        UPDATE team_season_stats
                        SET o_line_conversion = %s, d_line_conversion = %s,
                            hold_percentage = %s, break_percentage = %s
                        WHERE team_id = %s AND year = %s
                        """,
                        (olc, dlc, hold_pct, break_pct, team_id, year),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE team_season_stats
                        SET o_line_conversion = %s, d_line_conversion = %s
                        WHERE team_id = %s AND year = %s
                        """,
                        (olc, dlc, team_id, year),
                    )
                print(f"  Updated {team_name}: OLC={olc}%, DLC={dlc}%" +
                      (f", HLD={hold_pct}%, BRK={break_pct}%" if hold_pct else ""))
                total_updated += 1
            else:
                # Insert new record with basic data + possession stats
                cursor.execute(
                    """
                    INSERT INTO team_season_stats
                    (team_id, year, wins, losses, ties, standing, division_id, division_name,
                     o_line_conversion, d_line_conversion, hold_percentage, break_percentage)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (team_id, year, wins, losses, ties, standing, div_id, div_name,
                     olc, dlc, hold_pct, break_pct),
                )
                print(f"  Inserted {team_name}: OLC={olc}%, DLC={dlc}%" +
                      (f", HLD={hold_pct}%, BRK={break_pct}%" if hold_pct else ""))
                total_inserted += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n{'=' * 50}")
    print(f"Total records updated: {total_updated}")
    print(f"Total records inserted: {total_inserted}")
    print(f"Total teams not found: {total_not_found}")
    print(f"Total teams with HLD/BRK calculated: {total_hld_calculated}")


if __name__ == "__main__":
    print("Fixing OLC% and DLC% stats for 2014-2019...")
    print("Data source: WatchUFA screenshots")
    update_possession_stats()
    print("\nDone!")
