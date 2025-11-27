"""
Player statistics API route handler.
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from utils.query import convert_to_per_game_stats, convert_to_per_possession_stats
from data.cache import get_cache, cache_key_for_endpoint
from .query_builder import PlayerStatsQueryBuilder
from .percentile_calculator import calculate_global_percentiles


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
        custom_filters: Optional[str] = None,
    ):
        """Get paginated player statistics with filtering and sorting"""
        try:
            # Parse comma-separated season and team parameters
            seasons, teams, is_career_mode = _parse_filters(season, team)

            # Parse custom filters
            filters_list = _parse_custom_filters(custom_filters)

            # Check cache first
            cache = get_cache()
            sorted_seasons = sorted(seasons)
            sorted_teams = sorted(teams)
            cache_key = cache_key_for_endpoint(
                "player_stats",
                season=",".join(str(s) for s in sorted_seasons),
                team=",".join(sorted_teams),
                page=page,
                per_page=per_page,
                sort=sort,
                order=order,
                per=per,
                custom_filters=custom_filters,
            )

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Build queries using query builder
            per_game_mode = per == "game"
            per_possession_mode = per == "possession"
            query_builder = PlayerStatsQueryBuilder(
                seasons=seasons,
                teams=teams,
                is_career_mode=is_career_mode,
                filters_list=filters_list,
                per_game_mode=per_game_mode,
                per_possession_mode=per_possession_mode,
                sort=sort,
                order=order,
                page=page,
                per_page=per_page,
            )

            main_query = query_builder.build_main_query()
            count_query = query_builder.build_count_query()

            # Execute queries
            with stats_system.db.engine.connect() as conn:
                # Get total count
                count_result = conn.execute(text(count_query)).fetchone()
                total = count_result[0] if count_result else 0

                # Get players
                result = conn.execute(text(main_query))
                players = [_row_to_player_dict(row) for row in result]

            # Convert to per-game stats if requested
            if per == "game":
                players = convert_to_per_game_stats(players)
            elif per == "possession":
                players = convert_to_per_possession_stats(players)

            # Calculate global percentiles for all players
            percentiles = {}
            if players:
                with stats_system.db.engine.connect() as conn:
                    percentiles = calculate_global_percentiles(
                        conn,
                        players,
                        seasons=seasons if not is_career_mode else None,
                        teams=teams if teams[0] != "all" else None,
                    )

            total_pages = (total + per_page - 1) // per_page

            result = {
                "players": players,
                "percentiles": percentiles,
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


def _parse_filters(season: str, team: str) -> tuple[list, list, bool]:
    """
    Parse season and team filter parameters.

    Returns:
        Tuple of (seasons list, teams list, is_career_mode boolean)
    """
    seasons = []
    teams = []
    is_career_mode = season == "career"

    if is_career_mode:
        seasons = ["career"]
    else:
        # Parse comma-separated seasons
        seasons = [s.strip() for s in season.split(",") if s.strip()]
        if not seasons:
            seasons = ["career"]
            is_career_mode = True

    # Parse comma-separated teams
    if team == "all":
        teams = ["all"]
    else:
        teams = [t.strip() for t in team.split(",") if t.strip()]
        if not teams:
            teams = ["all"]

    return seasons, teams, is_career_mode


def _parse_custom_filters(custom_filters: Optional[str]) -> list:
    """Parse JSON custom filters string."""
    if not custom_filters:
        return []

    try:
        return json.loads(custom_filters)
    except json.JSONDecodeError:
        return []


def _row_to_player_dict(row) -> dict:
    """Convert a database row to a player dictionary."""
    return {
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
        "total_throw_attempts": row[11] or 0,
        "completion_percentage": row[12] or 0,
        "total_yards_thrown": row[13] or 0,
        "total_yards_received": row[14] or 0,
        "total_throwaways": row[15] or 0,
        "total_stalls": row[16] or 0,
        "total_drops": row[17] or 0,
        "total_callahans": row[18] or 0,
        "total_hucks_completed": row[19] or 0,
        "total_hucks_attempted": row[20] or 0,
        "total_hucks_received": row[21] or 0,
        "total_pulls": row[22] or 0,
        "total_o_points_played": row[23] or 0,
        "total_d_points_played": row[24] or 0,
        "total_seconds_played": row[25] or 0,
        "total_o_opportunities": row[26] or 0,
        "total_d_opportunities": row[27] or 0,
        "total_o_opportunity_scores": row[28] or 0,
        "team_name": row[29],
        "team_full_name": row[30],
        "games_played": row[31] or 0,
        "possessions": row[32] or 0,
        "score_total": row[33] or 0,
        "total_points_played": row[34] or 0,
        "total_yards": row[35] or 0,
        "minutes_played": row[36] or 0,
        "huck_percentage": row[37] or 0,
        "offensive_efficiency": row[38] if row[38] is not None else None,
        "yards_per_turn": row[39] if row[39] is not None else None,
        "yards_per_completion": row[40] if row[40] is not None else None,
        "yards_per_reception": row[41] if row[41] is not None else None,
        "assists_per_turnover": row[42] if row[42] is not None else None,
    }
