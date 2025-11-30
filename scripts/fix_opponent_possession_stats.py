#!/usr/bin/env python3
"""
Fix opponent OLC% and DLC% stats for 2014-2019 seasons.

The UFA API doesn't have game_events for 2014-2019, so we manually update
the opp_o_line_conversion and opp_d_line_conversion columns with data from WatchUFA.
"""

import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# Data extracted from WatchUFA opponent stats screenshots
# Format: team_name: (opp_olc%, opp_dlc%)
WATCHUFA_OPP_DATA = {
    2014: {
        "Spiders": (41.67, 26.64),
        "Rush": (34.25, 36.97),
        "Radicals": (34.19, 28.33),
        "Empire": (34.74, 40.19),
        "FlameThrowers": (36.17, 35.16),
        "Breeze": (45.10, 44.85),
        "AlleyCats": (45.13, 39.11),
        "Union": (37.24, 34.98),
        "Riptide": (39.27, 40.91),
        "Wind Chill": (42.68, 41.92),
        "Royal": (43.31, 46.50),
        "Revolution": (49.14, 44.04),
        "Cascades": (38.85, 41.76),
        "Phoenix": (49.87, 48.31),
        "Dragons": (52.25, 46.01),
        "Lions": (49.58, 52.69),
        "Mechanix": (51.81, 48.54),
    },
    2015: {
        "Radicals": (37.85, 30.54),
        "Rush": (37.48, 35.98),
        "Spiders": (46.68, 38.17),
        "Thunderbirds": (42.64, 32.97),
        "Empire": (35.78, 39.30),
        "Flyers": (44.54, 39.44),
        "Cannons": (48.10, 37.72),
        "Hustle": (44.23, 41.71),
        "Cascades": (47.62, 40.08),
        "Royal": (42.86, 42.50),
        "FlameThrowers": (42.57, 42.64),
        "Union": (35.49, 33.33),
        "AlleyCats": (43.84, 44.50),
        "Breeze": (44.67, 43.27),
        "Growlers": (51.75, 46.49),
        "Outlaws": (45.51, 38.62),
        "Wind Chill": (37.66, 41.04),
        "Aviators": (47.88, 47.56),
        "Riptide": (54.38, 49.15),
        "Express": (53.09, 48.95),
        "Nightwatch": (50.33, 42.24),
        "Revolution": (53.63, 46.49),
        "Dragons": (49.27, 51.52),
        "Phoenix": (48.86, 49.04),
        "Mechanix": (58.77, 59.84),
    },
    2016: {
        "Legion": (38.57, 27.93),
        "Radicals": (31.44, 31.21),
        "Rush": (37.46, 38.22),
        "Cascades": (48.62, 47.27),
        "Breeze": (41.43, 37.86),
        "FlameThrowers": (44.76, 40.53),
        "Thunderbirds": (40.03, 39.29),
        "Aviators": (46.06, 52.63),
        "Flyers": (46.77, 38.78),
        "Wind Chill": (47.00, 38.72),
        "AlleyCats": (42.32, 41.67),
        "Hustle": (48.75, 45.75),
        "Empire": (38.74, 41.70),
        "Outlaws": (44.04, 41.96),
        "Sol": (45.40, 36.86),
        "Riptide": (53.50, 43.48),
        "Royal": (46.28, 42.00),
        "Cannons": (52.31, 43.83),
        "Spiders": (51.49, 48.18),
        "Express": (49.76, 44.14),
        "Mechanix": (40.78, 45.43),
        "Union": (43.12, 36.27),
        "Nightwatch": (58.71, 48.97),
        "Growlers": (52.14, 48.69),
        "Phoenix": (55.00, 50.79),
        "Revolution": (51.70, 40.61),
    },
    2017: {
        "FlameThrowers": (44.93, 38.50),
        "Flyers": (46.16, 37.72),
        "Legion": (48.15, 41.05),
        "Radicals": (46.89, 39.44),
        "Rush": (49.02, 41.67),
        "Breeze": (47.48, 41.52),
        "Wind Chill": (48.04, 45.45),
        "Aviators": (48.50, 41.45),
        "Cannons": (49.62, 40.96),
        "Thunderbirds": (47.91, 43.56),
        "Royal": (47.44, 47.17),
        "Spiders": (54.81, 51.85),
        "Cascades": (49.15, 40.00),
        "Growlers": (48.74, 40.38),
        "Empire": (47.77, 44.29),
        "AlleyCats": (50.94, 43.75),
        "Hustle": (55.92, 51.56),
        "Phoenix": (50.67, 46.34),
        "Sol": (54.73, 53.85),
        "Union": (48.50, 46.15),
        "Outlaws": (49.59, 48.45),
        "Mechanix": (48.15, 51.43),
        "Riptide": (47.17, 45.00),
        "Nightwatch": (54.55, 54.35),
    },
    2018: {
        "Legion": (43.17, 34.20),
        "Radicals": (41.18, 38.67),
        "Rush": (40.22, 31.25),
        "AlleyCats": (46.21, 26.96),
        "Aviators": (46.47, 41.26),
        "Flyers": (47.00, 43.08),
        "Empire": (50.37, 42.44),
        "Breeze": (46.87, 38.49),
        "Wind Chill": (47.58, 38.61),
        "Growlers": (50.82, 44.07),
        "Hustle": (57.64, 46.03),
        "Royal": (50.00, 42.59),
        "Sol": (50.86, 45.02),
        "Spiders": (48.29, 40.00),
        "Cascades": (55.53, 36.43),
        "FlameThrowers": (54.24, 37.35),
        "Phoenix": (45.64, 43.86),
        "Union": (51.99, 37.76),
        "Cannons": (52.05, 48.94),
        "Thunderbirds": (53.55, 46.13),
        "Nightwatch": (56.26, 47.46),
        "Outlaws": (48.66, 47.64),
        "Mechanix": (55.85, 50.84),
    },
    2019: {
        "Empire": (50.78, 36.67),
        "Growlers": (50.23, 47.26),
        "Flyers": (51.04, 40.85),
        "Legion": (47.31, 43.41),
        "AlleyCats": (50.86, 42.00),
        "Aviators": (52.08, 37.50),
        "Thunderbirds": (47.98, 43.31),
        "Rush": (46.88, 39.53),
        "Breeze": (49.75, 42.14),
        "Union": (49.87, 47.97),
        "Radicals": (46.29, 41.38),
        "Wind Chill": (49.73, 40.63),
        "Hustle": (55.02, 46.21),
        "Cannons": (50.44, 51.10),
        "Phoenix": (51.30, 36.22),
        "Royal": (55.13, 37.79),
        "Outlaws": (52.82, 41.83),
        "Sol": (50.00, 40.59),
        "Spiders": (59.94, 48.17),
        "Cascades": (58.50, 52.75),
        "Mechanix": (57.63, 46.84),
    },
}


def get_connection():
    """Get database connection."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url)


def calculate_opp_hold_break_from_pgs(cursor, team_id, year):
    """
    Calculate opponent HLD% and BRK% from player_game_stats.
    This is the opponent's hold/break, which means:
    - Opp HLD% = opponent's o-line scores / opponent's o-line points
    - Opp BRK% = opponent's d-line scores / opponent's d-line points

    Returns (opp_hold_pct, opp_break_pct) or (None, None) if no data.
    """
    # Get opponent stats by looking at the opposing team's player_game_stats for each game
    cursor.execute(
        """
        WITH opponent_game_stats AS (
            -- For games where this team was the home team, get away team stats
            SELECT
                g.home_team_id as team_id,
                g.game_id,
                MAX(pgs.o_points_played) as opp_o_points,
                MAX(pgs.d_points_played) as opp_d_points,
                MAX(pgs.o_points_scored) as opp_o_scored,
                MAX(pgs.d_points_scored) as opp_d_scored
            FROM games g
            JOIN player_game_stats pgs ON g.game_id = pgs.game_id AND g.away_team_id = pgs.team_id
            WHERE g.home_team_id = %s AND g.year = %s
              AND g.game_type NOT IN ('all-star', 'showcase', 'preseason')
            GROUP BY g.home_team_id, g.game_id

            UNION ALL

            -- For games where this team was the away team, get home team stats
            SELECT
                g.away_team_id as team_id,
                g.game_id,
                MAX(pgs.o_points_played) as opp_o_points,
                MAX(pgs.d_points_played) as opp_d_points,
                MAX(pgs.o_points_scored) as opp_o_scored,
                MAX(pgs.d_points_scored) as opp_d_scored
            FROM games g
            JOIN player_game_stats pgs ON g.game_id = pgs.game_id AND g.home_team_id = pgs.team_id
            WHERE g.away_team_id = %s AND g.year = %s
              AND g.game_type NOT IN ('all-star', 'showcase', 'preseason')
            GROUP BY g.away_team_id, g.game_id
        )
        SELECT
            SUM(opp_o_points) as opp_o_line_points,
            SUM(opp_o_scored) as opp_o_line_scores,
            SUM(opp_d_points) as opp_d_line_points,
            SUM(opp_d_scored) as opp_d_line_scores
        FROM opponent_game_stats
        """,
        (team_id, year, team_id, year),
    )
    row = cursor.fetchone()

    if not row or row[0] is None:
        return None, None

    opp_o_line_points = row[0] or 0
    opp_o_line_scores = row[1] or 0
    opp_d_line_points = row[2] or 0
    opp_d_line_scores = row[3] or 0

    opp_hold_pct = (
        round((opp_o_line_scores / opp_o_line_points) * 100, 2)
        if opp_o_line_points > 0
        else None
    )
    opp_break_pct = (
        round((opp_d_line_scores / opp_d_line_points) * 100, 2)
        if opp_d_line_points > 0
        else None
    )

    return opp_hold_pct, opp_break_pct


def update_opponent_possession_stats():
    """Update opp_o_line_conversion and opp_d_line_conversion for 2014-2019."""
    conn = get_connection()
    cursor = conn.cursor()

    total_updated = 0
    total_not_found = 0
    total_opp_hld_calculated = 0

    for year, teams in WATCHUFA_OPP_DATA.items():
        if not teams:
            print(f"\nSkipping {year} - no data provided yet")
            continue

        print(f"\nProcessing {year}...")

        for team_name, (opp_olc, opp_dlc) in teams.items():
            # First, get the team_id from the teams table
            cursor.execute(
                """
                SELECT team_id
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

            team_id = team_row[0]

            # Calculate opponent HLD% and BRK% from player_game_stats if available
            opp_hold_pct, opp_break_pct = calculate_opp_hold_break_from_pgs(
                cursor, team_id, year
            )
            if opp_hold_pct is not None:
                total_opp_hld_calculated += 1

            # Update record with opponent OLC%, DLC%, and HLD%/BRK% if available
            if opp_hold_pct is not None:
                cursor.execute(
                    """
                    UPDATE team_season_stats
                    SET opp_o_line_conversion = %s, opp_d_line_conversion = %s,
                        opp_hold_percentage = %s, opp_break_percentage = %s
                    WHERE team_id = %s AND year = %s
                    """,
                    (opp_olc, opp_dlc, opp_hold_pct, opp_break_pct, team_id, year),
                )
            else:
                cursor.execute(
                    """
                    UPDATE team_season_stats
                    SET opp_o_line_conversion = %s, opp_d_line_conversion = %s
                    WHERE team_id = %s AND year = %s
                    """,
                    (opp_olc, opp_dlc, team_id, year),
                )

            if cursor.rowcount > 0:
                print(
                    f"  Updated {team_name}: Opp OLC={opp_olc}%, Opp DLC={opp_dlc}%"
                    + (
                        f", Opp HLD={opp_hold_pct}%, Opp BRK={opp_break_pct}%"
                        if opp_hold_pct
                        else ""
                    )
                )
                total_updated += 1
            else:
                print(f"  No team_season_stats record for {team_name} ({year})")
                total_not_found += 1

    conn.commit()
    cursor.close()
    conn.close()

    print(f"\n{'=' * 50}")
    print(f"Total records updated: {total_updated}")
    print(f"Total teams not found: {total_not_found}")
    print(f"Total teams with Opp HLD/BRK calculated: {total_opp_hld_calculated}")


if __name__ == "__main__":
    print("Fixing opponent OLC% and DLC% stats for 2014-2019...")
    print("Data source: WatchUFA opponent stats screenshots")
    update_opponent_possession_stats()
    print("\nDone!")
