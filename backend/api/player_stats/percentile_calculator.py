"""
Global percentile calculation for player statistics.
"""

from typing import Optional
from sqlalchemy import text


# List of all stat fields to calculate percentiles for
STAT_FIELDS = [
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

# Stats where lower is better (turnovers, etc.) - percentile should be inverted
INVERT_STATS = ["total_throwaways", "total_stalls", "total_drops"]


def build_percentile_expressions() -> list[str]:
    """
    Build CUME_DIST() SQL expressions for all stats.

    Returns:
        List of SQL expressions for calculating percentiles
    """
    percentile_expressions = []
    for field in STAT_FIELDS:
        # For stats where lower is better, invert the percentile
        if field in INVERT_STATS:
            expr = f"ROUND(CAST((1 - CUME_DIST() OVER (ORDER BY {field})) * 100 AS NUMERIC), 0) as {field}_percentile"
        else:
            expr = f"ROUND(CAST(CUME_DIST() OVER (ORDER BY {field}) * 100 AS NUMERIC), 0) as {field}_percentile"
        percentile_expressions.append(expr)
    return percentile_expressions


def calculate_global_percentiles(
    conn,
    players: list[dict],
    seasons: Optional[list] = None,
    teams: Optional[list] = None
) -> dict:
    """
    Calculate global percentile rankings for each player's stats.

    Args:
        conn: Database connection
        players: List of player dicts to calculate percentiles for
        seasons: List of season years to filter by (None or ["career"] = all seasons)
        teams: List of team IDs to filter by (None or ["all"] = all teams)

    Returns:
        Dictionary mapping full_name to percentile values for each stat.
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

    # Extract full names for filtering
    full_names = [p["full_name"] for p in players]
    names_str = ",".join([f"'{name.replace(chr(39), chr(39)*2)}'" for name in full_names])

    # Build CUME_DIST() expressions for all stats
    percentile_expressions = build_percentile_expressions()

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
        percentiles_sql = _build_career_percentiles_query(
            percentile_expressions, team_where, names_str
        )
    else:
        percentiles_sql = _build_season_percentiles_query(
            percentile_expressions, season_where, team_where, names_str
        )

    try:
        result = conn.execute(text(percentiles_sql))
        percentiles_map = {}

        for row in result:
            full_name = row[0]
            percentiles = {}
            # Map all percentile values (skip the first column which is full_name)
            for i, field in enumerate(STAT_FIELDS):
                percentiles[field] = row[i + 1] if row[i + 1] is not None else 0
            percentiles_map[full_name] = percentiles

        return percentiles_map
    except Exception as e:
        print(f"Error calculating percentiles: {e}")
        import traceback
        traceback.print_exc()
        return {}


def _build_career_percentiles_query(
    percentile_expressions: list[str],
    team_where: str,
    names_str: str
) -> str:
    """Build SQL query for career mode percentiles."""
    return f"""
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
                WHEN SUM(pss.total_throw_attempts) >= 100
                THEN SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts)
                ELSE NULL
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
                WHEN SUM(pss.total_o_opportunities) >= 100
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


def _build_season_percentiles_query(
    percentile_expressions: list[str],
    season_where: str,
    team_where: str,
    names_str: str
) -> str:
    """Build SQL query for season-specific percentiles."""
    return f"""
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
                WHEN SUM(pss.total_throw_attempts) >= 100
                THEN SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts)
                ELSE NULL
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
                WHEN SUM(pss.total_o_opportunities) >= 100
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
