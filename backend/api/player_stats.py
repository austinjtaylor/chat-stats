"""
Player statistics API endpoint with complex query logic.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from utils.query import convert_to_per_game_stats, get_sort_column


def create_player_stats_route(stats_system):
    """Create the player statistics endpoint."""
    router = APIRouter()

    @router.get("/api/players/stats")
    async def get_player_stats(
        season: str = "2025",
        team: str = "all",
        page: int = 1,
        per_page: int = 20,
        sort: str = "calculated_plus_minus",
        order: str = "desc",
        per: str = "total",
    ):
        """Get paginated player statistics with filtering and sorting"""
        try:
            # Query for player season stats directly from database
            team_filter = f" AND pss.team_id = '{team}'" if team != "all" else ""
            season_filter = f" AND pss.year = {season}" if season != "career" else ""

            if season == "career":
                # Career stats - aggregate across all years
                query = f"""
                SELECT 
                    p.full_name,
                    p.first_name,
                    p.last_name,
                    p.team_id,
                    p.max_year as year,
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
                    SUM(pss.total_pulls) as total_pulls,
                    SUM(pss.total_o_points_played) as total_o_points_played,
                    SUM(pss.total_d_points_played) as total_d_points_played,
                    SUM(pss.total_seconds_played) as total_seconds_played,
                    SUM(pss.total_o_opportunities) as total_o_opportunities,
                    SUM(pss.total_d_opportunities) as total_d_opportunities,
                    SUM(pss.total_o_opportunity_scores) as total_o_opportunity_scores,
                    MAX(t.name) as team_name,
                    MAX(t.full_name) as team_full_name,
                    (SELECT COUNT(DISTINCT pgs_sub.game_id) 
                     FROM player_game_stats pgs_sub 
                     JOIN games g_sub ON pgs_sub.game_id = g_sub.game_id
                     WHERE pgs_sub.player_id = pss.player_id 
                     AND (pgs_sub.o_points_played > 0 OR pgs_sub.d_points_played > 0 OR pgs_sub.seconds_played > 0 OR pgs_sub.goals > 0 OR pgs_sub.assists > 0)
                     {team_filter.replace('pss.', 'pgs_sub.')}
                    ) as games_played,
                    SUM(pss.total_o_opportunities) as possessions,
                    (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
                    (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
                    (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
                    ROUND(SUM(pss.total_seconds_played) / 60.0, 0) as minutes_played,
                    CASE 
                        WHEN SUM(pss.total_hucks_attempted) > 0 
                        THEN ROUND(SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted), 1) 
                        ELSE 0 
                    END as huck_percentage,
                    CASE 
                        WHEN SUM(pss.total_o_opportunities) >= 20 
                        THEN ROUND(SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities), 1)
                        ELSE NULL 
                    END as offensive_efficiency
                FROM player_season_stats pss
                JOIN (SELECT pss2.player_id,
                             MAX(pss2.year) as max_year,
                             MAX(p.full_name) as full_name,
                             MAX(p.first_name) as first_name,
                             MAX(p.last_name) as last_name,
                             MAX(p.team_id) as team_id
                      FROM player_season_stats pss2
                      JOIN players p ON pss2.player_id = p.player_id AND pss2.year = p.year
                      GROUP BY pss2.player_id) p ON pss.player_id = p.player_id
                LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
                WHERE 1=1{team_filter}
                GROUP BY pss.player_id
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
                    END as offensive_efficiency
                FROM player_season_stats pss
                JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
                LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
                LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
                LEFT JOIN games g ON pgs.game_id = g.game_id
                WHERE 1=1{season_filter}{team_filter}
                GROUP BY pss.player_id, pss.team_id, pss.year
                ORDER BY {get_sort_column(sort, per_game=(per == "game"))} {order.upper()}
                LIMIT {per_page} OFFSET {(page-1) * per_page}
                """

            # Get total count for pagination
            if season == "career":
                count_query = f"""
                SELECT COUNT(DISTINCT pss.player_id) as total
                FROM player_season_stats pss
                LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
                LEFT JOIN games g ON pgs.game_id = g.game_id
                WHERE 1=1{team_filter}
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
                    LEFT JOIN games g ON pgs.game_id = g.game_id  
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
                        "total_pulls": row[20] or 0,
                        "total_o_points_played": row[21] or 0,
                        "total_d_points_played": row[22] or 0,
                        "total_seconds_played": row[23] or 0,
                        "total_o_opportunities": row[24] or 0,
                        "total_d_opportunities": row[25] or 0,
                        "total_o_opportunity_scores": row[26] or 0,
                        "team_name": row[27],
                        "team_full_name": row[28],
                        "games_played": row[29] or 0,
                        "possessions": row[30] or 0,
                        "score_total": row[31] or 0,
                        "total_points_played": row[32] or 0,
                        "total_yards": row[33] or 0,
                        "minutes_played": row[34] or 0,
                        "huck_percentage": row[35] or 0,
                        "offensive_efficiency": (
                            row[36] if row[36] is not None else None
                        ),
                    }
                    players.append(player)

            # Convert to per-game stats if requested
            if per == "game":
                players = convert_to_per_game_stats(players)

            total_pages = (total + per_page - 1) // per_page

            return {
                "players": players,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
            }

        except Exception as e:
            print(f"Error in get_player_stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
