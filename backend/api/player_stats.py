"""
Player statistics API endpoint with complex query logic.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from utils.query import convert_to_per_game_stats, get_sort_column
from data.cache import get_cache, cache_key_for_endpoint


def get_team_career_sort_column(sort_key: str, per_game: bool = False) -> str:
    """
    Get the sort column for team career stats queries.
    Handles per-game sorting by dividing counting stats by games_played.
    """
    # Stats that should not be divided (already percentages/ratios or special fields)
    non_counting_stats = [
        "full_name",
        "completion_percentage",
        "huck_percentage",
        "offensive_efficiency",
        "yards_per_turn",
        "games_played",
    ]

    # If per_game mode and this is a counting stat, divide by games_played
    if per_game and sort_key not in non_counting_stats:
        # Use COALESCE to handle the LEFT JOIN case where gc.games_played might be NULL
        return f"CASE WHEN COALESCE(gc.games_played, 0) > 0 THEN CAST(tcs.{sort_key} AS NUMERIC) / gc.games_played ELSE 0 END"

    # Otherwise use the column directly from team_career_stats CTE
    return f"tcs.{sort_key}"


def create_player_stats_route(stats_system):
    """Create the player statistics endpoint."""
    router = APIRouter()

    @router.get("/api/players/stats")
    async def get_player_stats(
        season: str = "career",
        team: str = "all",
        page: int = 1,
        per_page: int = 20,
        sort: str = "calculated_plus_minus",
        order: str = "desc",
        per: str = "total",
    ):
        """Get paginated player statistics with filtering and sorting"""
        try:
            # Check cache first
            cache = get_cache()
            cache_key = cache_key_for_endpoint(
                'player_stats',
                season=season,
                team=team,
                page=page,
                per_page=per_page,
                sort=sort,
                order=order,
                per=per
            )

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            # Query for player season stats directly from database
            team_filter = f" AND pss.team_id = '{team}'" if team != "all" else ""
            season_filter = f" AND pss.year = {season}" if season != "career" else ""

            # When team filter is active with career stats, we need to aggregate
            # season stats for that specific team (not use pre-computed career stats
            # which include all teams)
            if season == "career" and team != "all":
                # Aggregate career stats for specific team across all seasons
                # Optimized version without expensive LEFT JOINs
                query = f"""
                WITH team_career_stats AS (
                    SELECT
                        pss.player_id,
                        pss.team_id,
                        MAX(pss.year) as most_recent_year,
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
                        SUM(pss.total_throwaways) as total_throwaways,
                        SUM(pss.total_stalls) as total_stalls,
                        SUM(pss.total_drops) as total_drops,
                        SUM(pss.total_callahans) as total_callahans,
                        SUM(pss.total_hucks_completed) as total_hucks_completed,
                        SUM(pss.total_hucks_attempted) as total_hucks_attempted,
                        SUM(pss.total_hucks_received) as total_hucks_received,
                        SUM(pss.total_pulls) as total_pulls,
                        SUM(pss.total_o_points_played) as total_o_points_played,
                        SUM(pss.total_d_points_played) as total_d_points_played,
                        SUM(pss.total_seconds_played) as total_seconds_played,
                        SUM(pss.total_o_opportunities) as total_o_opportunities,
                        SUM(pss.total_d_opportunities) as total_d_opportunities,
                        SUM(pss.total_o_opportunity_scores) as total_o_opportunity_scores,
                        SUM(pss.total_o_opportunities) as possessions,
                        (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
                        (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
                        (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
                        ROUND(SUM(pss.total_seconds_played) / 60.0, 0) as minutes_played,
                        CASE WHEN SUM(pss.total_hucks_attempted) > 0 THEN ROUND(SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted), 1) ELSE 0 END as huck_percentage,
                        CASE
                            WHEN SUM(pss.total_o_opportunities) >= 20
                            THEN ROUND(SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities), 1)
                            ELSE NULL
                        END as offensive_efficiency,
                        CASE
                            WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                            THEN ROUND((SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 1)
                            ELSE NULL
                        END as yards_per_turn
                    FROM player_season_stats pss
                    WHERE pss.team_id = '{team}'
                    GROUP BY pss.player_id, pss.team_id
                ),
                player_info AS (
                    SELECT DISTINCT ON (pss.player_id)
                        pss.player_id,
                        p.full_name,
                        p.first_name,
                        p.last_name
                    FROM player_season_stats pss
                    JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
                    WHERE pss.team_id = '{team}'
                    ORDER BY pss.player_id, pss.year DESC
                ),
                games_count AS (
                    SELECT
                        pgs.player_id,
                        COUNT(DISTINCT pgs.game_id) as games_played
                    FROM player_game_stats pgs
                    WHERE pgs.team_id = '{team}'
                      AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                    GROUP BY pgs.player_id
                ),
                team_info AS (
                    SELECT DISTINCT ON (t.team_id)
                        t.team_id,
                        t.name,
                        t.full_name
                    FROM teams t
                    WHERE t.team_id = '{team}'
                    ORDER BY t.team_id, t.year DESC
                )
                SELECT
                    pi.full_name,
                    pi.first_name,
                    pi.last_name,
                    tcs.team_id,
                    NULL as year,
                    tcs.total_goals,
                    tcs.total_assists,
                    tcs.total_hockey_assists,
                    tcs.total_blocks,
                    tcs.calculated_plus_minus,
                    tcs.total_completions,
                    tcs.completion_percentage,
                    tcs.total_yards_thrown,
                    tcs.total_yards_received,
                    tcs.total_throwaways,
                    tcs.total_stalls,
                    tcs.total_drops,
                    tcs.total_callahans,
                    tcs.total_hucks_completed,
                    tcs.total_hucks_attempted,
                    tcs.total_hucks_received,
                    tcs.total_pulls,
                    tcs.total_o_points_played,
                    tcs.total_d_points_played,
                    tcs.total_seconds_played,
                    tcs.total_o_opportunities,
                    tcs.total_d_opportunities,
                    tcs.total_o_opportunity_scores,
                    ti.name as team_name,
                    ti.full_name as team_full_name,
                    COALESCE(gc.games_played, 0) as games_played,
                    tcs.possessions,
                    tcs.score_total,
                    tcs.total_points_played,
                    tcs.total_yards,
                    tcs.minutes_played,
                    tcs.huck_percentage,
                    tcs.offensive_efficiency,
                    tcs.yards_per_turn
                FROM team_career_stats tcs
                JOIN player_info pi ON tcs.player_id = pi.player_id
                LEFT JOIN games_count gc ON tcs.player_id = gc.player_id
                CROSS JOIN team_info ti
                ORDER BY {get_team_career_sort_column(sort, per_game=(per == "game"))} {order.upper()}
                LIMIT {per_page} OFFSET {(page-1) * per_page}
                """
            elif season == "career":
                # Use pre-computed career stats table for much faster queries (no team filter)
                query = f"""
                SELECT
                    full_name,
                    first_name,
                    last_name,
                    most_recent_team_id as team_id,
                    NULL as year,
                    total_goals,
                    total_assists,
                    total_hockey_assists,
                    total_blocks,
                    calculated_plus_minus,
                    total_completions,
                    completion_percentage,
                    total_yards_thrown,
                    total_yards_received,
                    total_throwaways,
                    total_stalls,
                    total_drops,
                    total_callahans,
                    total_hucks_completed,
                    total_hucks_attempted,
                    total_hucks_received,
                    total_pulls,
                    total_o_points_played,
                    total_d_points_played,
                    total_seconds_played,
                    total_o_opportunities,
                    total_d_opportunities,
                    total_o_opportunity_scores,
                    most_recent_team_name as team_name,
                    most_recent_team_full_name as team_full_name,
                    games_played,
                    possessions,
                    score_total,
                    total_points_played,
                    total_yards,
                    minutes_played,
                    huck_percentage,
                    offensive_efficiency,
                    yards_per_turn
                FROM player_career_stats
                WHERE 1=1
                ORDER BY {get_sort_column(sort, is_career=True, per_game=(per == "game"), team=team)} {order.upper()}
                LIMIT {per_page} OFFSET {(page-1) * per_page}
                """
            else:
                # Single season stats - existing query
                query = f"""
                SELECT
                    p.full_name,
                    p.first_name,
                    p.last_name,
                    p.team_id,
                    pss.year,
                    pss.total_goals,
                    pss.total_assists,
                    pss.total_hockey_assists,
                    pss.total_blocks,
                    pss.calculated_plus_minus,
                    pss.total_completions,
                    pss.completion_percentage,
                    pss.total_yards_thrown,
                    pss.total_yards_received,
                    pss.total_throwaways,
                    pss.total_stalls,
                    pss.total_drops,
                    pss.total_callahans,
                    pss.total_hucks_completed,
                    pss.total_hucks_attempted,
                    pss.total_hucks_received,
                    pss.total_pulls,
                    pss.total_o_points_played,
                    pss.total_d_points_played,
                    pss.total_seconds_played,
                    pss.total_o_opportunities,
                    pss.total_d_opportunities,
                    pss.total_o_opportunity_scores,
                    t.name as team_name,
                    t.full_name as team_full_name,
                    COUNT(DISTINCT CASE
                        WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                        THEN pgs.game_id
                        ELSE NULL
                    END) as games_played,
                    pss.total_o_opportunities as possessions,
                    (pss.total_goals + pss.total_assists) as score_total,
                    (pss.total_o_points_played + pss.total_d_points_played) as total_points_played,
                    (pss.total_yards_thrown + pss.total_yards_received) as total_yards,
                    ROUND(pss.total_seconds_played / 60.0, 0) as minutes_played,
                    CASE WHEN pss.total_hucks_attempted > 0 THEN ROUND(pss.total_hucks_completed * 100.0 / pss.total_hucks_attempted, 1) ELSE 0 END as huck_percentage,
                    CASE
                        WHEN pss.total_o_opportunities >= 20
                        THEN ROUND(pss.total_o_opportunity_scores * 100.0 / pss.total_o_opportunities, 1)
                        ELSE NULL
                    END as offensive_efficiency,
                    CASE
                        WHEN (pss.total_throwaways + pss.total_stalls + pss.total_drops) > 0
                        THEN ROUND((pss.total_yards_thrown + pss.total_yards_received) * 1.0 / (pss.total_throwaways + pss.total_stalls + pss.total_drops), 1)
                        ELSE NULL
                    END as yards_per_turn
                FROM player_season_stats pss
                JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
                LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
                LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
                LEFT JOIN games g ON pgs.game_id = g.game_id AND g.year = pss.year
                WHERE 1=1{season_filter}{team_filter}
                GROUP BY pss.player_id, pss.team_id, pss.year, p.full_name, p.first_name, p.last_name, p.team_id,
                         pss.total_goals, pss.total_assists, pss.total_hockey_assists, pss.total_blocks, pss.calculated_plus_minus,
                         pss.total_completions, pss.completion_percentage, pss.total_yards_thrown, pss.total_yards_received,
                         pss.total_throwaways, pss.total_stalls, pss.total_drops, pss.total_callahans,
                         pss.total_hucks_completed, pss.total_hucks_attempted, pss.total_hucks_received, pss.total_pulls,
                         pss.total_o_points_played, pss.total_d_points_played, pss.total_seconds_played,
                         pss.total_o_opportunities, pss.total_d_opportunities, pss.total_o_opportunity_scores,
                         t.name, t.full_name
                ORDER BY {get_sort_column(sort, per_game=(per == "game"))} {order.upper()}
                LIMIT {per_page} OFFSET {(page-1) * per_page}
                """

            # Get total count for pagination
            if season == "career" and team != "all":
                # Count players who played for this specific team (simplified - no EXISTS check)
                count_query = f"""
                SELECT COUNT(DISTINCT pss.player_id) as total
                FROM player_season_stats pss
                WHERE pss.team_id = '{team}'
                """
            elif season == "career":
                # Count all career players
                count_query = f"""
                SELECT COUNT(*) as total
                FROM player_career_stats
                WHERE 1=1
                """
            else:
                # Simplified count - just count from player_season_stats without expensive EXISTS check
                count_query = f"""
                SELECT COUNT(DISTINCT pss.player_id || '-' || pss.team_id || '-' || pss.year) as total
                FROM player_season_stats pss
                WHERE 1=1{season_filter}{team_filter}
                """

            # Execute queries using the stats system database connection
            with stats_system.db.engine.connect() as conn:
                # Get total count
                count_result = conn.execute(text(count_query)).fetchone()
                total = count_result[0] if count_result else 0

                # Get players
                result = conn.execute(text(query))
                players = []

                for row in result:
                    player = {
                        "full_name": row[0],
                        "first_name": row[1],
                        "last_name": row[2],
                        "team_id": row[3],
                        "year": row[4],
                        "total_goals": row[5] or 0,
                        "total_assists": row[6] or 0,
                        "total_hockey_assists": row[7] or 0,
                        "total_blocks": row[8] or 0,
                        "calculated_plus_minus": row[9] or 0,
                        "total_completions": row[10] or 0,
                        "completion_percentage": row[11] or 0,
                        "total_yards_thrown": row[12] or 0,
                        "total_yards_received": row[13] or 0,
                        "total_throwaways": row[14] or 0,
                        "total_stalls": row[15] or 0,
                        "total_drops": row[16] or 0,
                        "total_callahans": row[17] or 0,
                        "total_hucks_completed": row[18] or 0,
                        "total_hucks_attempted": row[19] or 0,
                        "total_hucks_received": row[20] or 0,
                        "total_pulls": row[21] or 0,
                        "total_o_points_played": row[22] or 0,
                        "total_d_points_played": row[23] or 0,
                        "total_seconds_played": row[24] or 0,
                        "total_o_opportunities": row[25] or 0,
                        "total_d_opportunities": row[26] or 0,
                        "total_o_opportunity_scores": row[27] or 0,
                        "team_name": row[28],
                        "team_full_name": row[29],
                        "games_played": row[30] or 0,
                        "possessions": row[31] or 0,
                        "score_total": row[32] or 0,
                        "total_points_played": row[33] or 0,
                        "total_yards": row[34] or 0,
                        "minutes_played": row[35] or 0,
                        "huck_percentage": row[36] or 0,
                        "offensive_efficiency": (
                            row[37] if row[37] is not None else None
                        ),
                        "yards_per_turn": row[38] if row[38] is not None else None,
                    }
                    players.append(player)

            # Convert to per-game stats if requested
            if per == "game":
                players = convert_to_per_game_stats(players)

            total_pages = (total + per_page - 1) // per_page

            result = {
                "players": players,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }

            # Cache the result
            cache.set(cache_key, result, ttl=300)  # 5 minute TTL

            return result

        except Exception as e:
            print(f"Error in get_player_stats: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    return router
