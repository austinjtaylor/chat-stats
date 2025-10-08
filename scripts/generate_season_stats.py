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


def generate_team_season_stats(engine):
    """Generate team_season_stats by aggregating games and player stats."""
    print("🏈 Generating team_season_stats from games and player stats...")
    print("=" * 60)

    with engine.connect() as conn:
        # Check if we have games data
        games_count = conn.execute(text("SELECT COUNT(*) FROM games")).fetchone()[0]
        print(f"  Games records: {games_count:,}")

        if games_count == 0:
            print("  ❌ No games data to aggregate")
            return

        # First, clear existing team_season_stats to rebuild
        print("  🗑️  Clearing existing team_season_stats...")
        conn.execute(text("DELETE FROM team_season_stats"))
        conn.commit()

        # Aggregate team stats from games and player_game_stats
        print("  🔄 Aggregating team stats...")

        aggregate_query = """
        -- Step 1: Get basic team/year combinations from teams table
        INSERT INTO team_season_stats (
            team_id, year, wins, losses, ties, standing,
            division_id, division_name,
            games_played, scores, scores_against,
            completions, throw_attempts, turnovers,
            completion_percentage,
            hucks_completed, hucks_attempted, huck_percentage,
            blocks,
            opp_completions, opp_throw_attempts, opp_turnovers,
            opp_completion_percentage,
            opp_hucks_completed, opp_hucks_attempted, opp_huck_percentage,
            opp_blocks
        )
        WITH team_game_stats AS (
            -- Home games
            SELECT
                t.team_id,
                t.year,
                COUNT(*) as games,
                SUM(CASE WHEN g.home_score > g.away_score THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN g.home_score < g.away_score THEN 1 ELSE 0 END) as losses,
                SUM(g.home_score) as scores,
                SUM(g.away_score) as scores_against
            FROM teams t
            LEFT JOIN games g ON t.team_id = g.home_team_id AND t.year = g.year
            WHERE g.game_id IS NOT NULL
            GROUP BY t.team_id, t.year

            UNION ALL

            -- Away games
            SELECT
                t.team_id,
                t.year,
                COUNT(*) as games,
                SUM(CASE WHEN g.away_score > g.home_score THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN g.away_score < g.home_score THEN 1 ELSE 0 END) as losses,
                SUM(g.away_score) as scores,
                SUM(g.home_score) as scores_against
            FROM teams t
            LEFT JOIN games g ON t.team_id = g.away_team_id AND t.year = g.year
            WHERE g.game_id IS NOT NULL
            GROUP BY t.team_id, t.year
        ),
        team_player_stats AS (
            SELECT
                pgs.team_id,
                pgs.year,
                SUM(pgs.completions) as total_completions,
                SUM(pgs.throw_attempts) as total_attempts,
                SUM(pgs.throwaways + pgs.drops + pgs.stalls) as total_turnovers,
                SUM(pgs.hucks_completed) as hucks_completed,
                SUM(pgs.hucks_attempted) as hucks_attempted,
                SUM(pgs.blocks) as total_blocks
            FROM player_game_stats pgs
            GROUP BY pgs.team_id, pgs.year
        ),
        opponent_stats AS (
            -- Get opponent stats by joining games and reversing team perspective
            SELECT
                home.team_id,
                home.year,
                SUM(away_stats.total_completions) as opp_completions,
                SUM(away_stats.total_attempts) as opp_attempts,
                SUM(away_stats.total_turnovers) as opp_turnovers,
                SUM(away_stats.hucks_completed) as opp_hucks_completed,
                SUM(away_stats.hucks_attempted) as opp_hucks_attempted,
                SUM(away_stats.total_blocks) as opp_blocks
            FROM teams home
            INNER JOIN games g ON g.home_team_id = home.team_id AND g.year = home.year
            INNER JOIN team_player_stats away_stats ON away_stats.team_id = g.away_team_id AND away_stats.year = g.year
            GROUP BY home.team_id, home.year

            UNION ALL

            SELECT
                away.team_id,
                away.year,
                SUM(home_stats.total_completions) as opp_completions,
                SUM(home_stats.total_attempts) as opp_attempts,
                SUM(home_stats.total_turnovers) as opp_turnovers,
                SUM(home_stats.hucks_completed) as opp_hucks_completed,
                SUM(home_stats.hucks_attempted) as opp_hucks_attempted,
                SUM(home_stats.total_blocks) as opp_blocks
            FROM teams away
            INNER JOIN games g ON g.away_team_id = away.team_id AND g.year = away.year
            INNER JOIN team_player_stats home_stats ON home_stats.team_id = g.home_team_id AND home_stats.year = g.year
            GROUP BY away.team_id, away.year
        ),
        aggregated_team_stats AS (
            SELECT
                t.team_id,
                t.year,
                SUM(tg.games) as total_games,
                SUM(tg.wins) as total_wins,
                SUM(tg.losses) as total_losses,
                SUM(tg.scores) as total_scores,
                SUM(tg.scores_against) as total_scores_against
            FROM teams t
            LEFT JOIN team_game_stats tg ON t.team_id = tg.team_id AND t.year = tg.year
            GROUP BY t.team_id, t.year
        ),
        aggregated_opponent_stats AS (
            SELECT
                team_id,
                year,
                SUM(opp_completions) as total_opp_completions,
                SUM(opp_attempts) as total_opp_attempts,
                SUM(opp_turnovers) as total_opp_turnovers,
                SUM(opp_hucks_completed) as total_opp_hucks_completed,
                SUM(opp_hucks_attempted) as total_opp_hucks_attempted,
                SUM(opp_blocks) as total_opp_blocks
            FROM opponent_stats
            GROUP BY team_id, year
        )
        SELECT
            t.team_id,
            t.year,
            COALESCE(ats.total_wins, 0) as wins,
            COALESCE(ats.total_losses, 0) as losses,
            t.ties,
            t.standing,
            t.division_id,
            t.division_name,
            COALESCE(ats.total_games, 0) as games_played,
            COALESCE(ats.total_scores, 0) as scores,
            COALESCE(ats.total_scores_against, 0) as scores_against,
            COALESCE(tps.total_completions, 0) as completions,
            COALESCE(tps.total_attempts, 0) as throw_attempts,
            COALESCE(tps.total_turnovers, 0) as turnovers,
            CASE
                WHEN COALESCE(tps.total_attempts, 0) > 0
                THEN ROUND((CAST(tps.total_completions AS NUMERIC) / tps.total_attempts) * 100, 2)
                ELSE 0
            END as completion_percentage,
            COALESCE(tps.hucks_completed, 0) as hucks_completed,
            COALESCE(tps.hucks_attempted, 0) as hucks_attempted,
            CASE
                WHEN COALESCE(tps.hucks_attempted, 0) > 0
                THEN ROUND((CAST(tps.hucks_completed AS NUMERIC) / tps.hucks_attempted) * 100, 2)
                ELSE 0
            END as huck_percentage,
            COALESCE(tps.total_blocks, 0) as blocks,
            COALESCE(aos.total_opp_completions, 0) as opp_completions,
            COALESCE(aos.total_opp_attempts, 0) as opp_throw_attempts,
            COALESCE(aos.total_opp_turnovers, 0) as opp_turnovers,
            CASE
                WHEN COALESCE(aos.total_opp_attempts, 0) > 0
                THEN ROUND((CAST(aos.total_opp_completions AS NUMERIC) / aos.total_opp_attempts) * 100, 2)
                ELSE 0
            END as opp_completion_percentage,
            COALESCE(aos.total_opp_hucks_completed, 0) as opp_hucks_completed,
            COALESCE(aos.total_opp_hucks_attempted, 0) as opp_hucks_attempted,
            CASE
                WHEN COALESCE(aos.total_opp_hucks_attempted, 0) > 0
                THEN ROUND((CAST(aos.total_opp_hucks_completed AS NUMERIC) / aos.total_opp_hucks_attempted) * 100, 2)
                ELSE 0
            END as opp_huck_percentage,
            COALESCE(aos.total_opp_blocks, 0) as opp_blocks
        FROM teams t
        LEFT JOIN aggregated_team_stats ats ON t.team_id = ats.team_id AND t.year = ats.year
        LEFT JOIN team_player_stats tps ON t.team_id = tps.team_id AND t.year = tps.year
        LEFT JOIN aggregated_opponent_stats aos ON t.team_id = aos.team_id AND t.year = aos.year
        GROUP BY t.team_id, t.year, t.ties, t.standing, t.division_id, t.division_name,
                 ats.total_wins, ats.total_losses, ats.total_games, ats.total_scores, ats.total_scores_against,
                 tps.total_completions, tps.total_attempts, tps.total_turnovers,
                 tps.hucks_completed, tps.hucks_attempted, tps.total_blocks,
                 aos.total_opp_completions, aos.total_opp_attempts, aos.total_opp_turnovers,
                 aos.total_opp_hucks_completed, aos.total_opp_hucks_attempted, aos.total_opp_blocks
        """

        try:
            result = conn.execute(text(aggregate_query))
            conn.commit()
            print(f"  ✅ Aggregated team season stats successfully")

            # Verify count
            team_stats_count = conn.execute(
                text("SELECT COUNT(*) FROM team_season_stats")
            ).fetchone()[0]
            print(f"  ✅ Team season stats records: {team_stats_count:,}")

            print(f"  ⚠️  Note: Possession stats (hold%, O-line conv, etc.) are set to 0")
            print(f"      These require game_events data and are calculated at query time")

        except Exception as e:
            print(f"  ❌ Error aggregating team stats: {str(e)}")
            conn.rollback()
            sys.exit(1)


def populate_possession_stats_from_events(engine):
    """Populate possession statistics using game_events data."""
    print("\n🏈 Populating Possession-Based Statistics...")
    print("=" * 60)

    # Import the populate function from populate_possession_stats
    sys.path.insert(0, os.path.dirname(__file__))
    from populate_possession_stats import populate_possession_stats, DatabaseWrapper

    try:
        db_wrapper = DatabaseWrapper(engine)
        populate_possession_stats(db_wrapper)
    except ImportError:
        print("  ⚠️  Could not import possession stats module")
        print("  ℹ️  Run 'uv run python scripts/populate_possession_stats.py' manually")
    except Exception as e:
        print(f"  ❌ Error populating possession stats: {str(e)}")
        print("  ℹ️  You can run 'uv run python scripts/populate_possession_stats.py' separately")


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
            os.path.dirname(__file__), "..", "backend", "db", "sports_stats.db"
        )
        print(f"📁 SQLite database: {sqlite_db_path}")

        if not os.path.exists(sqlite_db_path):
            print(f"❌ SQLite database not found at {sqlite_db_path}")
            sys.exit(1)

        engine = create_engine(f"sqlite:///{sqlite_db_path}")

    generate_player_season_stats(engine)
    generate_team_season_stats(engine)

    # Populate possession stats from game_events
    populate_possession_stats_from_events(engine)

    print("\n" + "=" * 60)
    print("✅ SEASON STATS GENERATION COMPLETE!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("  - Player season stats: Ready for use")
    print("  - Team season stats: Ready for use (including possession stats!)")


if __name__ == "__main__":
    main()
