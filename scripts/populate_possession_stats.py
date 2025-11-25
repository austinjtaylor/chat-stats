#!/usr/bin/env python3
"""
Populate possession-based statistics in team_season_stats table.

This script calculates and stores possession stats (hold%, break%, conversions, etc.)
by processing game_events data once and storing results in the database for instant API access.

Run this via: uv run python scripts/populate_possession_stats.py
"""

import os
import sys
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from data.possession import calculate_possessions_batch, calculate_redzone_stats_batch

load_dotenv()


class DatabaseWrapper:
    """Wrapper class that provides execute_query() method for compatibility."""

    def __init__(self, engine):
        self.engine = engine

    def execute_query(self, query, params=None):
        """Execute a query and return results as list of dicts"""
        with self.engine.connect() as conn:
            if isinstance(query, str):
                from sqlalchemy import text

                query = text(query)
            result = conn.execute(query, params or {})
            if result.returns_rows:
                columns = result.keys()
                return [dict(zip(columns, row)) for row in result.fetchall()]
            return []


def populate_possession_stats(db):
    """
    Calculate and populate possession statistics for all team-season records.

    Processes game_events data using batch functions and stores results in team_season_stats.
    This converts a slow on-demand calculation (3-8 seconds) into instant DB reads (10-50ms).

    Args:
        db: Database wrapper object with execute_query() and engine attributes
    """
    print("🏈 Populating Possession-Based Statistics")
    print("=" * 70)

    # Get the underlying engine for connection
    engine = getattr(db, 'engine', db)

    with engine.connect() as conn:
        # Get count of game events for context
        events_count = conn.execute(text("SELECT COUNT(*) FROM game_events")).fetchone()[0]
        print(f"  📊 Total game events to process: {events_count:,}")

        if events_count == 0:
            print("  ❌ No game_events data found - possession stats cannot be calculated")
            return

        # Get all unique team-season combinations
        print("\n  🔍 Finding team-season records...")
        team_seasons = conn.execute(text("""
            SELECT team_id, year
            FROM team_season_stats
            ORDER BY year DESC, team_id
        """)).fetchall()

        print(f"  ✅ Found {len(team_seasons)} team-season records\n")

        if not team_seasons:
            print("  ❌ No team_season_stats records found")
            return

        # Process by year for better progress tracking and memory management
        years = sorted(set(ts[1] for ts in team_seasons), reverse=True)

        total_updated = 0
        total_errors = 0

        for year in years:
            year_teams = [ts[0] for ts in team_seasons if ts[1] == year]
            print(f"\n  📅 Processing {year} ({len(year_teams)} teams)...")
            print("  " + "-" * 66)

            try:
                # Calculate possession stats for all teams in this year (batch operation)
                print(f"     🔄 Calculating possession stats...")
                possession_stats = calculate_possessions_batch(
                    db,  # Pass db wrapper for execute_query() access
                    year_teams,
                    season_filter="AND g.year = :season",
                    season_param=year
                )

                # Calculate red zone stats for all teams in this year (batch operation)
                print(f"     🔄 Calculating red zone stats...")
                redzone_stats = calculate_redzone_stats_batch(
                    db,
                    year_teams,
                    season_filter="AND g.year = :season",
                    season_param=year
                )

                # Calculate opponent stats for each team (game-by-game, not season totals)
                print(f"     🔄 Calculating opponent stats (per-game)...")
                opponent_stats_map = {}

                # Build a mapping of game_id -> {home_team_id, away_team_id, home_stats, away_stats}
                # by processing game events for this year
                from domain.possession import PossessionEventProcessor, RedzoneEventProcessor

                # Fetch all game events for this year with game info
                events_query = text("""
                    SELECT
                        g.game_id,
                        g.home_team_id,
                        g.away_team_id,
                        ge.event_index,
                        ge.event_type,
                        ge.team,
                        ge.receiver_y,
                        ge.thrower_y
                    FROM games g
                    JOIN game_events ge ON g.game_id = ge.game_id
                    WHERE g.year = :year
                        AND g.game_type NOT IN ('all-star', 'showcase')
                    ORDER BY g.game_id, ge.event_index,
                        CASE
                            WHEN ge.event_type IN (19, 15) THEN 0
                            WHEN ge.event_type = 1 THEN 1
                            ELSE 2
                        END
                """)
                all_events = conn.execute(events_query, {'year': year}).fetchall()

                # Group events by game and team type
                game_events = {}
                for event in all_events:
                    game_id = event[0]
                    home_team = event[1]
                    away_team = event[2]
                    team_type = event[5]  # 'home' or 'away'

                    if game_id not in game_events:
                        game_events[game_id] = {
                            'home_team_id': home_team,
                            'away_team_id': away_team,
                            'home_events': [],
                            'away_events': []
                        }

                    event_dict = {
                        'event_index': event[3],
                        'event_type': event[4],
                        'team': team_type,
                        'receiver_y': event[6],
                        'thrower_y': event[7]
                    }

                    if team_type == 'home':
                        game_events[game_id]['home_events'].append(event_dict)
                    else:
                        game_events[game_id]['away_events'].append(event_dict)

                # Calculate per-game stats for each team (home and away)
                game_team_stats = {}  # {(game_id, team_id): {poss_stats, rz_stats}}
                for game_id, game_data in game_events.items():
                    home_team = game_data['home_team_id']
                    away_team = game_data['away_team_id']

                    # Process home team stats
                    if game_data['home_events']:
                        poss_processor = PossessionEventProcessor('home')
                        poss_stats = poss_processor.process_events(game_data['home_events'])
                        rz_processor = RedzoneEventProcessor('home')
                        rz_stats = rz_processor.process_events(game_data['home_events'])
                        game_team_stats[(game_id, home_team)] = {
                            'poss': poss_stats.to_dict(),
                            'rz': rz_stats.to_dict()
                        }

                    # Process away team stats
                    if game_data['away_events']:
                        poss_processor = PossessionEventProcessor('away')
                        poss_stats = poss_processor.process_events(game_data['away_events'])
                        rz_processor = RedzoneEventProcessor('away')
                        rz_stats = rz_processor.process_events(game_data['away_events'])
                        game_team_stats[(game_id, away_team)] = {
                            'poss': poss_stats.to_dict(),
                            'rz': rz_stats.to_dict()
                        }

                # Now calculate opponent stats for each team by summing opponent's per-game stats
                for team_id in year_teams:
                    opp_o_line_points = 0
                    opp_o_line_scores = 0
                    opp_o_line_possessions = 0
                    opp_d_line_points = 0
                    opp_d_line_scores = 0
                    opp_d_line_possessions = 0
                    opp_rz_scores = 0
                    opp_rz_attempts = 0

                    # Find all games this team played and get opponent's stats from THAT GAME
                    for game_id, game_data in game_events.items():
                        opponent_id = None
                        if game_data['home_team_id'] == team_id:
                            opponent_id = game_data['away_team_id']
                        elif game_data['away_team_id'] == team_id:
                            opponent_id = game_data['home_team_id']

                        if opponent_id:
                            # Get opponent's stats from THIS SPECIFIC GAME
                            opp_game_stats = game_team_stats.get((game_id, opponent_id), {})
                            opp_poss = opp_game_stats.get('poss', {})
                            opp_rz = opp_game_stats.get('rz', {})

                            opp_o_line_points += opp_poss.get('o_line_points', 0)
                            opp_o_line_scores += opp_poss.get('o_line_scores', 0)
                            opp_o_line_possessions += opp_poss.get('o_line_possessions', 0)
                            opp_d_line_points += opp_poss.get('d_line_points', 0)
                            opp_d_line_scores += opp_poss.get('d_line_scores', 0)
                            opp_d_line_possessions += opp_poss.get('d_line_possessions', 0)
                            opp_rz_scores += opp_rz.get('redzone_goals', 0)
                            opp_rz_attempts += opp_rz.get('redzone_attempts', 0)

                    # Calculate opponent percentages
                    opp_hold_pct = round((opp_o_line_scores / opp_o_line_points) * 100, 2) if opp_o_line_points > 0 else 0.0
                    opp_o_conv = round((opp_o_line_scores / opp_o_line_possessions) * 100, 2) if opp_o_line_possessions > 0 else 0.0
                    opp_break_pct = round((opp_d_line_scores / opp_d_line_points) * 100, 2) if opp_d_line_points > 0 else 0.0
                    opp_d_conv = round((opp_d_line_scores / opp_d_line_possessions) * 100, 2) if opp_d_line_possessions > 0 else 0.0
                    opp_rz_conv = round((opp_rz_scores / opp_rz_attempts) * 100, 2) if opp_rz_attempts > 0 else 0.0

                    opponent_stats_map[team_id] = {
                        'opp_o_line_points': opp_o_line_points,
                        'opp_o_line_scores': opp_o_line_scores,
                        'opp_o_line_possessions': opp_o_line_possessions,
                        'opp_d_line_points': opp_d_line_points,
                        'opp_d_line_scores': opp_d_line_scores,
                        'opp_d_line_possessions': opp_d_line_possessions,
                        'opp_rz_scores': opp_rz_scores,
                        'opp_rz_attempts': opp_rz_attempts,
                        'opp_hold_pct': opp_hold_pct,
                        'opp_o_conv': opp_o_conv,
                        'opp_break_pct': opp_break_pct,
                        'opp_d_conv': opp_d_conv,
                        'opp_rz_conv': opp_rz_conv,
                    }

                # Update each team's stats in the database
                print(f"     💾 Updating database...")
                for team_id in year_teams:
                    poss = possession_stats.get(team_id, {})
                    rz = redzone_stats.get(team_id, {})
                    opp = opponent_stats_map.get(team_id, {})

                    # Get team raw counts
                    o_line_points = poss.get('o_line_points', 0)
                    o_line_scores = poss.get('o_line_scores', 0)
                    o_line_possessions = poss.get('o_line_possessions', 0)
                    d_line_points = poss.get('d_line_points', 0)
                    d_line_scores = poss.get('d_line_scores', 0)
                    d_line_possessions = poss.get('d_line_possessions', 0)
                    rz_scores = rz.get('redzone_goals', 0)
                    rz_attempts = rz.get('redzone_attempts', 0)

                    # Calculate team percentages
                    hold_pct = round((o_line_scores / o_line_points) * 100, 2) if o_line_points > 0 else 0.0
                    o_conv = round((o_line_scores / o_line_possessions) * 100, 2) if o_line_possessions > 0 else 0.0
                    break_pct = round((d_line_scores / d_line_points) * 100, 2) if d_line_points > 0 else 0.0
                    d_conv = round((d_line_scores / d_line_possessions) * 100, 2) if d_line_possessions > 0 else 0.0
                    rz_conv = round((rz_scores / rz_attempts) * 100, 2) if rz_attempts > 0 else 0.0

                    update_query = text("""
                        UPDATE team_season_stats
                        SET
                            o_line_points = :o_line_points,
                            o_line_scores = :o_line_scores,
                            o_line_possessions = :o_line_possessions,
                            d_line_points = :d_line_points,
                            d_line_scores = :d_line_scores,
                            d_line_possessions = :d_line_possessions,
                            redzone_goals = :rz_goals,
                            redzone_attempts = :rz_attempts,
                            hold_percentage = :hold_pct,
                            o_line_conversion = :o_conv,
                            break_percentage = :break_pct,
                            d_line_conversion = :d_conv,
                            red_zone_conversion = :rz_conv,
                            opp_o_line_points = :opp_o_line_points,
                            opp_o_line_scores = :opp_o_line_scores,
                            opp_o_line_possessions = :opp_o_line_possessions,
                            opp_d_line_points = :opp_d_line_points,
                            opp_d_line_scores = :opp_d_line_scores,
                            opp_d_line_possessions = :opp_d_line_possessions,
                            opp_redzone_goals = :opp_rz_goals,
                            opp_redzone_attempts = :opp_rz_attempts,
                            opp_hold_percentage = :opp_hold_pct,
                            opp_o_line_conversion = :opp_o_conv,
                            opp_break_percentage = :opp_break_pct,
                            opp_d_line_conversion = :opp_d_conv,
                            opp_red_zone_conversion = :opp_rz_conv,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE team_id = :team_id AND year = :year
                    """)

                    conn.execute(update_query, {
                        'o_line_points': o_line_points,
                        'o_line_scores': o_line_scores,
                        'o_line_possessions': o_line_possessions,
                        'd_line_points': d_line_points,
                        'd_line_scores': d_line_scores,
                        'd_line_possessions': d_line_possessions,
                        'rz_goals': rz_scores,
                        'rz_attempts': rz_attempts,
                        'hold_pct': hold_pct,
                        'o_conv': o_conv,
                        'break_pct': break_pct,
                        'd_conv': d_conv,
                        'rz_conv': rz_conv,
                        'opp_o_line_points': opp.get('opp_o_line_points', 0),
                        'opp_o_line_scores': opp.get('opp_o_line_scores', 0),
                        'opp_o_line_possessions': opp.get('opp_o_line_possessions', 0),
                        'opp_d_line_points': opp.get('opp_d_line_points', 0),
                        'opp_d_line_scores': opp.get('opp_d_line_scores', 0),
                        'opp_d_line_possessions': opp.get('opp_d_line_possessions', 0),
                        'opp_rz_goals': opp.get('opp_rz_scores', 0),
                        'opp_rz_attempts': opp.get('opp_rz_attempts', 0),
                        'opp_hold_pct': opp.get('opp_hold_pct', 0.0),
                        'opp_o_conv': opp.get('opp_o_conv', 0.0),
                        'opp_break_pct': opp.get('opp_break_pct', 0.0),
                        'opp_d_conv': opp.get('opp_d_conv', 0.0),
                        'opp_rz_conv': opp.get('opp_rz_conv', 0.0),
                        'team_id': team_id,
                        'year': year
                    })

                conn.commit()
                total_updated += len(year_teams)
                print(f"     ✅ Updated {len(year_teams)} teams for {year}")

            except Exception as e:
                print(f"     ❌ Error processing {year}: {str(e)}")
                total_errors += 1
                conn.rollback()
                continue

        print("\n" + "=" * 70)
        print(f"✅ Possession Stats Population Complete!")
        print(f"   Updated: {total_updated} team-season records")
        if total_errors > 0:
            print(f"   Errors: {total_errors} years failed")
        print("=" * 70)


def main():
    """Main execution function."""
    print("\n🚀 Starting Possession Stats Population")
    print("This will pre-compute possession stats for instant API performance\n")

    # Get database connection
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        sys.exit(1)

    print(f"🐘 PostgreSQL database: {database_url.split('@')[1].split('/')[0]}\n")

    engine = create_engine(database_url)
    db_wrapper = DatabaseWrapper(engine)

    # Override engine with wrapper for batch functions
    populate_possession_stats(db_wrapper)

    print("\n📝 Next steps:")
    print("  - Team stats API will now load instantly (10-50ms)")
    print("  - Run this script periodically to refresh stats with new data")
    print("  - Consider adding to a daily/weekly cron job\n")


if __name__ == "__main__":
    main()
