"""
Player statistics API endpoint with complex query logic.
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from utils.query import convert_to_per_game_stats, get_sort_column
from data.cache import get_cache, cache_key_for_endpoint


def build_having_clause(custom_filters: list, per_game: bool = False, table_prefix: str = "", alias_mapping: dict = None) -> str:
    """
    Build a HAVING clause from custom filters.

    Args:
        custom_filters: List of filter dicts with 'field', 'operator', and 'value'
        per_game: Whether to apply per-game conversion to counting stats
        table_prefix: Prefix for field names (e.g., 'tcs.' for team_career_stats CTE)
        alias_mapping: Optional dict mapping field aliases to full SQL expressions (for season stats)

    Returns:
        HAVING clause string (without "HAVING" keyword) or empty string
    """
    if not custom_filters:
        return ""

    # Valid operators for security
    valid_operators = {'>', '<', '>=', '<=', '='}

    # Stats that should not be divided (already percentages/ratios or special fields)
    non_counting_stats = {
        "completion_percentage", "huck_percentage", "offensive_efficiency",
        "yards_per_turn", "yards_per_completion", "yards_per_reception",
        "assists_per_turnover", "games_played", "full_name"
    }

    conditions = []
    for f in custom_filters:
        field = f.get('field', '')
        operator = f.get('operator', '')
        value = f.get('value', 0)

        # Validate operator
        if operator not in valid_operators:
            continue

        # Validate field (basic SQL injection protection)
        if not field or not field.replace('_', '').isalnum():
            continue

        # Build field reference
        # Check if this field has an alias mapping (for calculated columns in season stats)
        if alias_mapping and field in alias_mapping:
            # Use the full SQL expression from the mapping
            field_ref = alias_mapping[field]
        elif per_game and field not in non_counting_stats:
            # For per-game filters on counting stats, divide by games_played
            if table_prefix:
                field_ref = f"CASE WHEN COALESCE(gc.games_played, 0) > 0 THEN CAST({table_prefix}{field} AS NUMERIC) / gc.games_played ELSE 0 END"
            else:
                field_ref = f"CASE WHEN games_played > 0 THEN CAST({field} AS NUMERIC) / games_played ELSE 0 END"
        else:
            field_ref = f"{table_prefix}{field}" if table_prefix else field

        # Build condition
        try:
            # Ensure value is numeric
            numeric_value = float(value)
            conditions.append(f"{field_ref} {operator} {numeric_value}")
        except (ValueError, TypeError):
            continue

    return " AND ".join(conditions) if conditions else ""


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
        "yards_per_completion",
        "yards_per_reception",
        "assists_per_turnover",
        "games_played",
    ]

    # If per_game mode and this is a counting stat, divide by games_played
    if per_game and sort_key not in non_counting_stats:
        # Use COALESCE to handle the LEFT JOIN case where gc.games_played might be NULL
        return f"CASE WHEN COALESCE(gc.games_played, 0) > 0 THEN CAST(tcs.{sort_key} AS NUMERIC) / gc.games_played ELSE 0 END"

    # Otherwise use the column directly from team_career_stats CTE
    return f"tcs.{sort_key}"


def calculate_global_percentiles(conn, players, seasons=None, teams=None):
    """
    Calculate global percentile rankings for each player's stats.

    Args:
        conn: Database connection
        players: List of player dicts to calculate percentiles for
        seasons: List of season years to filter by (None or ["career"] = all seasons)
        teams: List of team IDs to filter by (None or ["all"] = all teams)

    Returns a dictionary mapping full_name to percentile values for each stat.
    Percentiles are calculated across all players in the filtered dataset (0-100 scale).
    """
    if not players:
        return {}

    # Default to career mode if not specified
    if seasons is None or (isinstance(seasons, list) and "career" in seasons):
        seasons = None
        is_career_mode = True
    else:
        is_career_mode = False

    # Default to all teams if not specified
    if teams is None or (isinstance(teams, list) and "all" in teams):
        teams = None

    # List of all stat fields to calculate percentiles for
    stat_fields = [
        "total_goals", "total_assists", "total_hockey_assists", "total_blocks",
        "calculated_plus_minus", "total_completions", "completion_percentage",
        "total_yards_thrown", "total_yards_received", "total_throwaways",
        "total_stalls", "total_drops", "total_callahans", "total_hucks_completed",
        "total_hucks_attempted", "total_hucks_received", "total_pulls",
        "total_o_points_played", "total_d_points_played", "total_seconds_played",
        "total_o_opportunities", "total_d_opportunities", "total_o_opportunity_scores",
        "games_played", "possessions", "score_total", "total_points_played",
        "total_yards", "minutes_played", "huck_percentage", "offensive_efficiency",
        "yards_per_turn", "yards_per_completion", "yards_per_reception",
        "assists_per_turnover"
    ]

    # Extract full names for filtering
    full_names = [p["full_name"] for p in players]
    names_str = ",".join([f"'{name.replace(chr(39), chr(39)*2)}'" for name in full_names])

    # Build CUME_DIST() expressions for all stats
    percentile_expressions = []
    for field in stat_fields:
        # For stats where lower is better (turnovers, etc.), invert the percentile
        invert_stats = ["total_throwaways", "total_stalls", "total_drops"]
        if field in invert_stats:
            expr = f"ROUND(CAST((1 - CUME_DIST() OVER (ORDER BY {field})) * 100 AS NUMERIC), 0) as {field}_percentile"
        else:
            expr = f"ROUND(CAST(CUME_DIST() OVER (ORDER BY {field}) * 100 AS NUMERIC), 0) as {field}_percentile"
        percentile_expressions.append(expr)

    # Build WHERE clause filters for seasons and teams
    season_where = ""
    team_where = ""

    if not is_career_mode and seasons:
        if len(seasons) == 1:
            season_where = f" AND pss.year = {seasons[0]}"
        else:
            season_years_str = ",".join(str(s) for s in seasons)
            season_where = f" AND pss.year IN ({season_years_str})"

    if teams:
        if len(teams) == 1:
            team_where = f" AND pss.team_id = '{teams[0]}'"
        else:
            team_ids_str = ",".join([f"'{t}'" for t in teams])
            team_where = f" AND pss.team_id IN ({team_ids_str})"

    # Calculate global percentiles based on the appropriate data source
    if is_career_mode:
        # For career stats, aggregate across all seasons (filtered by team if specified)
        percentiles_sql = f"""
        WITH aggregated_career_stats AS (
            SELECT
                p.full_name,
                SUM(pss.total_goals) as total_goals,
                SUM(pss.total_assists) as total_assists,
                SUM(pss.total_hockey_assists) as total_hockey_assists,
                SUM(pss.total_blocks) as total_blocks,
                (SUM(pss.total_goals) + SUM(pss.total_assists) + SUM(pss.total_blocks) -
                 SUM(pss.total_throwaways) - SUM(pss.total_drops)) as calculated_plus_minus,
                SUM(pss.total_completions) as total_completions,
                CASE
                    WHEN SUM(pss.total_throw_attempts) > 0
                    THEN SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts)
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
                COUNT(DISTINCT CASE
                    WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0
                          OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                    THEN pgs.game_id
                    ELSE NULL
                END) as games_played,
                SUM(pss.total_o_opportunities) as possessions,
                (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
                (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
                (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
                SUM(pss.total_seconds_played) / 60.0 as minutes_played,
                CASE WHEN SUM(pss.total_hucks_attempted) > 0
                    THEN SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted)
                    ELSE 0 END as huck_percentage,
                CASE
                    WHEN SUM(pss.total_o_opportunities) >= 20
                    THEN SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities)
                    ELSE NULL
                END as offensive_efficiency,
                CASE
                    WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                    THEN (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0 /
                         (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops))
                    ELSE NULL
                END as yards_per_turn,
                CASE
                    WHEN SUM(pss.total_completions) > 0
                    THEN SUM(pss.total_yards_thrown) * 1.0 / SUM(pss.total_completions)
                    ELSE NULL
                END as yards_per_completion,
                CASE
                    WHEN SUM(pss.total_catches) > 0
                    THEN SUM(pss.total_yards_received) * 1.0 / SUM(pss.total_catches)
                    ELSE NULL
                END as yards_per_reception,
                CASE
                    WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                    THEN SUM(pss.total_assists) * 1.0 /
                         (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops))
                    ELSE NULL
                END as assists_per_turnover
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
            LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.team_id = pgs.team_id AND pss.year = pgs.year
            WHERE 1=1{team_where}
            GROUP BY p.full_name
        ),
        global_stats AS (
            SELECT
                full_name,
                {','.join(percentile_expressions)}
            FROM aggregated_career_stats
        )
        SELECT *
        FROM global_stats
        WHERE full_name IN ({names_str})
        """
    else:
        # For season-specific stats, use filtered season data
        # When multiple seasons are selected, aggregate them
        percentiles_sql = f"""
        WITH season_stats AS (
            SELECT
                p.full_name,
                SUM(pss.total_goals) as total_goals,
                SUM(pss.total_assists) as total_assists,
                SUM(pss.total_hockey_assists) as total_hockey_assists,
                SUM(pss.total_blocks) as total_blocks,
                (SUM(pss.total_goals) + SUM(pss.total_assists) + SUM(pss.total_blocks) -
                 SUM(pss.total_throwaways) - SUM(pss.total_drops)) as calculated_plus_minus,
                SUM(pss.total_completions) as total_completions,
                CASE
                    WHEN SUM(pss.total_throw_attempts) > 0
                    THEN SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts)
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
                COUNT(DISTINCT CASE
                    WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0
                          OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                    THEN pgs.game_id
                    ELSE NULL
                END) as games_played,
                SUM(pss.total_o_opportunities) as possessions,
                (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
                (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
                (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
                SUM(pss.total_seconds_played) / 60.0 as minutes_played,
                CASE WHEN SUM(pss.total_hucks_attempted) > 0
                    THEN SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted)
                    ELSE 0 END as huck_percentage,
                CASE
                    WHEN SUM(pss.total_o_opportunities) >= 20
                    THEN SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities)
                    ELSE NULL
                END as offensive_efficiency,
                CASE
                    WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                    THEN (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0 /
                         (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops))
                    ELSE NULL
                END as yards_per_turn,
                CASE
                    WHEN SUM(pss.total_completions) > 0
                    THEN SUM(pss.total_yards_thrown) * 1.0 / SUM(pss.total_completions)
                    ELSE NULL
                END as yards_per_completion,
                CASE
                    WHEN SUM(pss.total_catches) > 0
                    THEN SUM(pss.total_yards_received) * 1.0 / SUM(pss.total_catches)
                    ELSE NULL
                END as yards_per_reception,
                CASE
                    WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                    THEN SUM(pss.total_assists) * 1.0 /
                         (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops))
                    ELSE NULL
                END as assists_per_turnover
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
            LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.team_id = pgs.team_id AND pss.year = pgs.year
            WHERE 1=1{season_where}{team_where}
            GROUP BY p.full_name
        ),
        global_stats AS (
            SELECT
                full_name,
                {','.join(percentile_expressions)}
            FROM season_stats
        )
        SELECT *
        FROM global_stats
        WHERE full_name IN ({names_str})
        """

    try:
        result = conn.execute(text(percentiles_sql))
        percentiles_map = {}

        for row in result:
            full_name = row[0]
            percentiles = {}
            # Map all percentile values (skip the first column which is full_name)
            for i, field in enumerate(stat_fields):
                percentiles[field] = row[i + 1] if row[i + 1] is not None else 0
            percentiles_map[full_name] = percentiles

        return percentiles_map
    except Exception as e:
        print(f"Error calculating percentiles: {e}")
        import traceback
        traceback.print_exc()
        return {}


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
            seasons = []
            teams = []
            is_career_mode = season == "career"

            if is_career_mode:
                seasons = ["career"]
            else:
                # Parse comma-separated seasons
                seasons = [s.strip() for s in season.split(',') if s.strip()]
                if not seasons:
                    seasons = ["career"]
                    is_career_mode = True

            # Parse comma-separated teams
            if team == "all":
                teams = ["all"]
            else:
                teams = [t.strip() for t in team.split(',') if t.strip()]
                if not teams:
                    teams = ["all"]

            # Parse custom filters
            filters_list = []
            if custom_filters:
                try:
                    filters_list = json.loads(custom_filters)
                except json.JSONDecodeError:
                    filters_list = []

            # Check cache first (use sorted arrays for consistent cache keys)
            cache = get_cache()
            sorted_seasons = sorted(seasons)
            sorted_teams = sorted(teams)
            cache_key = cache_key_for_endpoint(
                'player_stats',
                season=','.join(str(s) for s in sorted_seasons),
                team=','.join(sorted_teams),
                page=page,
                per_page=per_page,
                sort=sort,
                order=order,
                per=per,
                custom_filters=custom_filters
            )

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Build SQL filters using IN clauses for multi-select
            # Team filter
            if teams[0] == "all":
                team_filter = ""
            elif len(teams) == 1:
                team_filter = f" AND pss.team_id = '{teams[0]}'"
            else:
                team_ids_str = ",".join([f"'{t}'" for t in teams])
                team_filter = f" AND pss.team_id IN ({team_ids_str})"

            # Season filter
            if is_career_mode:
                season_filter = ""
            elif len(seasons) == 1:
                season_filter = f" AND pss.year = {seasons[0]}"
            else:
                season_years_str = ",".join(seasons)
                season_filter = f" AND pss.year IN ({season_years_str})"

            # Build HAVING clause for custom filters
            per_game_mode = (per == "game")
            having_clause_career_team = build_having_clause(filters_list, per_game=per_game_mode, table_prefix="tcs.")
            having_clause_career = build_having_clause(filters_list, per_game=per_game_mode, table_prefix="")

            # Alias mapping for season stats - maps calculated column aliases to their full SQL expressions
            # This is needed because PostgreSQL can't reference SELECT aliases in HAVING clauses
            season_stats_alias_mapping = {
                "games_played": "COUNT(DISTINCT CASE WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0) THEN pgs.game_id ELSE NULL END)",
                "possessions": "pss.total_o_opportunities",
                "score_total": "(pss.total_goals + pss.total_assists)",
                "total_points_played": "(pss.total_o_points_played + pss.total_d_points_played)",
                "total_yards": "(pss.total_yards_thrown + pss.total_yards_received)",
                "minutes_played": "ROUND(pss.total_seconds_played / 60.0, 0)",
                "huck_percentage": "CASE WHEN pss.total_hucks_attempted > 0 THEN ROUND(pss.total_hucks_completed * 100.0 / pss.total_hucks_attempted, 1) ELSE 0 END",
                "offensive_efficiency": "CASE WHEN pss.total_o_opportunities >= 20 THEN ROUND(pss.total_o_opportunity_scores * 100.0 / pss.total_o_opportunities, 1) ELSE NULL END",
                "yards_per_turn": "CASE WHEN (pss.total_throwaways + pss.total_stalls + pss.total_drops) > 0 THEN ROUND((pss.total_yards_thrown + pss.total_yards_received) * 1.0 / (pss.total_throwaways + pss.total_stalls + pss.total_drops), 1) WHEN (pss.total_yards_thrown + pss.total_yards_received) > 0 THEN (pss.total_yards_thrown + pss.total_yards_received) * 1.0 ELSE NULL END",
                "yards_per_completion": "CASE WHEN pss.total_completions > 0 THEN ROUND(pss.total_yards_thrown * 1.0 / pss.total_completions, 1) ELSE NULL END",
                "yards_per_reception": "CASE WHEN pss.total_catches > 0 THEN ROUND(pss.total_yards_received * 1.0 / pss.total_catches, 1) ELSE NULL END",
                "assists_per_turnover": "CASE WHEN (pss.total_throwaways + pss.total_stalls + pss.total_drops) > 0 THEN ROUND(pss.total_assists * 1.0 / (pss.total_throwaways + pss.total_stalls + pss.total_drops), 2) ELSE NULL END",
            }

            having_clause_season = build_having_clause(filters_list, per_game=per_game_mode, table_prefix="", alias_mapping=season_stats_alias_mapping)

            # When team filter is active with career stats, we need to aggregate
            # season stats for that specific team (not use pre-computed career stats
            # which include all teams)
            if is_career_mode and teams[0] != "all":
                # Aggregate career stats for specific team(s) across all seasons
                # Optimized version without expensive LEFT JOINs
                team_filter_for_query = team_filter.replace(" AND ", "")  # Remove leading " AND "
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
                            WHEN (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) > 0
                            THEN (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0
                            ELSE NULL
                        END as yards_per_turn,
                        CASE
                            WHEN SUM(pss.total_completions) > 0
                            THEN ROUND(SUM(pss.total_yards_thrown) * 1.0 / SUM(pss.total_completions), 1)
                            ELSE NULL
                        END as yards_per_completion,
                        CASE
                            WHEN SUM(pss.total_catches) > 0
                            THEN ROUND(SUM(pss.total_yards_received) * 1.0 / SUM(pss.total_catches), 1)
                            ELSE NULL
                        END as yards_per_reception,
                        CASE
                            WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                            THEN ROUND(SUM(pss.total_assists) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 2)
                            ELSE NULL
                        END as assists_per_turnover
                    FROM player_season_stats pss
                    WHERE {team_filter_for_query}
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
                    WHERE {team_filter_for_query}
                    ORDER BY pss.player_id, pss.year DESC
                ),
                games_count AS (
                    SELECT
                        pgs.player_id,
                        COUNT(DISTINCT pgs.game_id) as games_played
                    FROM player_game_stats pgs
                    WHERE {team_filter_for_query.replace('pss.', 'pgs.')}
                      AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                    GROUP BY pgs.player_id
                ),
                team_info AS (
                    SELECT DISTINCT ON (t.team_id)
                        t.team_id,
                        t.name,
                        t.full_name
                    FROM teams t
                    WHERE {team_filter_for_query.replace('pss.', 't.')}
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
                    tcs.yards_per_turn,
                    tcs.yards_per_completion,
                    tcs.yards_per_reception,
                    tcs.assists_per_turnover
                FROM team_career_stats tcs
                JOIN player_info pi ON tcs.player_id = pi.player_id
                LEFT JOIN games_count gc ON tcs.player_id = gc.player_id
                CROSS JOIN team_info ti
                {"WHERE " + having_clause_career_team if having_clause_career_team else ""}
                ORDER BY {get_team_career_sort_column(sort, per_game=(per == "game"))} {order.upper()} NULLS LAST
                LIMIT {per_page} OFFSET {(page-1) * per_page}
                """
            elif is_career_mode:
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
                    yards_per_turn,
                    yards_per_completion,
                    yards_per_reception,
                    assists_per_turnover
                FROM player_career_stats
                WHERE 1=1
                {" AND " + having_clause_career if having_clause_career else ""}
                ORDER BY {get_sort_column(sort, is_career=True, per_game=(per == "game"), team=team)} {order.upper()} NULLS LAST
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
                        WHEN (pss.total_yards_thrown + pss.total_yards_received) > 0
                        THEN (pss.total_yards_thrown + pss.total_yards_received) * 1.0
                        ELSE NULL
                    END as yards_per_turn,
                    CASE
                        WHEN pss.total_completions > 0
                        THEN ROUND(pss.total_yards_thrown * 1.0 / pss.total_completions, 1)
                        ELSE NULL
                    END as yards_per_completion,
                    CASE
                        WHEN pss.total_catches > 0
                        THEN ROUND(pss.total_yards_received * 1.0 / pss.total_catches, 1)
                        ELSE NULL
                    END as yards_per_reception,
                    CASE
                        WHEN (pss.total_throwaways + pss.total_stalls + pss.total_drops) > 0
                        THEN ROUND(pss.total_assists * 1.0 / (pss.total_throwaways + pss.total_stalls + pss.total_drops), 2)
                        ELSE NULL
                    END as assists_per_turnover
                FROM player_season_stats pss
                JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
                LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
                LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
                LEFT JOIN games g ON pgs.game_id = g.game_id AND g.year = pss.year
                WHERE 1=1{season_filter}{team_filter}
                GROUP BY pss.player_id, pss.team_id, pss.year, p.full_name, p.first_name, p.last_name, p.team_id,
                         pss.total_goals, pss.total_assists, pss.total_hockey_assists, pss.total_blocks, pss.calculated_plus_minus,
                         pss.total_completions, pss.completion_percentage, pss.total_yards_thrown, pss.total_yards_received,
                         pss.total_catches, pss.total_throwaways, pss.total_stalls, pss.total_drops, pss.total_callahans,
                         pss.total_hucks_completed, pss.total_hucks_attempted, pss.total_hucks_received, pss.total_pulls,
                         pss.total_o_points_played, pss.total_d_points_played, pss.total_seconds_played,
                         pss.total_o_opportunities, pss.total_d_opportunities, pss.total_o_opportunity_scores,
                         t.name, t.full_name
                {"HAVING " + having_clause_season if having_clause_season else ""}
                ORDER BY {get_sort_column(sort, per_game=(per == "game"))} {order.upper()} NULLS LAST
                LIMIT {per_page} OFFSET {(page-1) * per_page}
                """

            # Get total count for pagination
            # Note: For filters that use HAVING clause, we need to run the full query to count accurately
            # This is less efficient but necessary for correct pagination with custom filters
            if filters_list:
                # When custom filters are present, we need to count the filtered results
                # We'll use a subquery approach
                if is_career_mode and teams[0] != "all":
                    # Reuse the main query structure but just count
                    # Build team filter for WHERE clauses
                    team_filter_for_count = team_filter.replace(" AND ", "")  # Remove leading " AND "
                    count_query = f"""
                    WITH team_career_stats AS (
                        SELECT
                            pss.player_id,
                            SUM(pss.total_goals) as total_goals,
                            SUM(pss.total_assists) as total_assists,
                            SUM(pss.total_completions) as total_completions,
                            SUM(pss.total_throwaways) as total_throwaways,
                            SUM(pss.total_stalls) as total_stalls,
                            SUM(pss.total_drops) as total_drops,
                            (SUM(pss.total_goals) + SUM(pss.total_assists) + SUM(pss.total_blocks) -
                             SUM(pss.total_throwaways) - SUM(pss.total_drops)) as calculated_plus_minus,
                            SUM(pss.total_o_opportunities) as possessions,
                            (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
                            (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
                            (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
                            SUM(pss.total_blocks) as total_blocks,
                            CASE WHEN SUM(pss.total_throw_attempts) > 0 THEN ROUND(SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts), 1) ELSE 0 END as completion_percentage,
                            CASE WHEN SUM(pss.total_hucks_attempted) > 0 THEN ROUND(SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted), 1) ELSE 0 END as huck_percentage,
                            CASE WHEN SUM(pss.total_o_opportunities) >= 20 THEN ROUND(SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities), 1) ELSE NULL END as offensive_efficiency,
                            CASE WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0 THEN ROUND((SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 1) ELSE NULL END as yards_per_turn,
                            CASE WHEN SUM(pss.total_completions) > 0 THEN ROUND(SUM(pss.total_yards_thrown) * 1.0 / SUM(pss.total_completions), 1) ELSE NULL END as yards_per_completion,
                            CASE WHEN SUM(pss.total_catches) > 0 THEN ROUND(SUM(pss.total_yards_received) * 1.0 / SUM(pss.total_catches), 1) ELSE NULL END as yards_per_reception,
                            CASE WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0 THEN ROUND(SUM(pss.total_assists) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 2) ELSE NULL END as assists_per_turnover,
                            ROUND(SUM(pss.total_seconds_played) / 60.0, 0) as minutes_played,
                            SUM(pss.total_o_points_played) as total_o_points_played,
                            SUM(pss.total_d_points_played) as total_d_points_played,
                            SUM(pss.total_hockey_assists) as total_hockey_assists
                        FROM player_season_stats pss
                        WHERE {team_filter_for_count}
                        GROUP BY pss.player_id
                    ),
                    games_count AS (
                        SELECT
                            pgs.player_id,
                            COUNT(DISTINCT pgs.game_id) as games_played
                        FROM player_game_stats pgs
                        WHERE {team_filter_for_count.replace('pss.', 'pgs.')}
                          AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                        GROUP BY pgs.player_id
                    )
                    SELECT COUNT(*) as total
                    FROM team_career_stats tcs
                    LEFT JOIN games_count gc ON tcs.player_id = gc.player_id
                    {"WHERE " + having_clause_career_team if having_clause_career_team else "WHERE 1=1"}
                    """
                else:
                    # For other cases with filters, use simpler approach
                    count_query = f"""
                    SELECT COUNT(*) FROM (
                        {query.replace(f'LIMIT {per_page} OFFSET {(page-1) * per_page}', '')}
                    ) AS filtered_results
                    """
            else:
                # No custom filters - use original optimized count queries
                if is_career_mode and teams[0] != "all":
                    # Career mode with team filter(s)
                    team_filter_for_count = team_filter.replace(" AND ", "")  # Remove leading " AND "
                    count_query = f"""
                    SELECT COUNT(DISTINCT pss.player_id) as total
                    FROM player_season_stats pss
                    WHERE {team_filter_for_count}
                    """
                elif is_career_mode:
                    # Career mode without team filter
                    count_query = f"""
                    SELECT COUNT(*) as total
                    FROM player_career_stats
                    WHERE 1=1
                    """
                else:
                    # Specific season(s) query
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
                        "yards_per_completion": row[39] if row[39] is not None else None,
                        "yards_per_reception": row[40] if row[40] is not None else None,
                        "assists_per_turnover": row[41] if row[41] is not None else None,
                    }
                    players.append(player)

            # Convert to per-game stats if requested
            if per == "game":
                players = convert_to_per_game_stats(players)

            # Calculate global percentiles for all players (filtered by selected seasons/teams)
            percentiles = {}
            if players:
                with stats_system.db.engine.connect() as conn:
                    percentiles = calculate_global_percentiles(
                        conn,
                        players,
                        seasons=seasons if not is_career_mode else None,
                        teams=teams if teams[0] != "all" else None
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
