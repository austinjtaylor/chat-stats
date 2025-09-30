"""
Player statistics API endpoint with complex query logic.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from utils.query import convert_to_per_game_stats, get_sort_column
from data.cache import get_cache, cache_key_for_endpoint


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

            if season == "career":
                # Use pre-computed career stats table for much faster queries
                team_filter_career = f" AND most_recent_team_id = '{team}'" if team != "all" else ""
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
                WHERE 1=1{team_filter_career}
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
                GROUP BY pss.player_id, pss.team_id, pss.year
                ORDER BY {get_sort_column(sort, per_game=(per == "game"))} {order.upper()}
                LIMIT {per_page} OFFSET {(page-1) * per_page}
                """

            # Get total count for pagination
            if season == "career":
                count_query = f"""
                SELECT COUNT(*) as total
                FROM player_career_stats
                WHERE 1=1{team_filter_career if season == "career" else team_filter}
                """
            else:
                count_query = f"""
                SELECT COUNT(DISTINCT pss.player_id || '-' || pss.team_id || '-' || pss.year) as total
                FROM player_season_stats pss
                JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
                LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
                WHERE 1=1{season_filter}{team_filter}
                AND EXISTS (
                    SELECT 1 FROM player_game_stats pgs
                    LEFT JOIN games g ON pgs.game_id = g.game_id AND g.year = pss.year
                    WHERE pgs.player_id = pss.player_id
                    AND pgs.year = pss.year
                    AND pgs.team_id = pss.team_id
                    AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                )
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
