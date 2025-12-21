"""
Global percentile calculation for player statistics.
"""

from sqlalchemy import text

# List of all stat fields to calculate percentiles for
STAT_FIELDS = [
    "total_goals",
    "total_assists",
    "total_hockey_assists",
    "total_blocks",
    "calculated_plus_minus",
    "total_completions",
    "completion_percentage",
    "total_yards_thrown",
    "total_yards_received",
    "total_throwaways",
    "total_stalls",
    "total_drops",
    "total_callahans",
    "total_hucks_completed",
    "total_hucks_attempted",
    "total_hucks_received",
    "total_pulls",
    "total_o_points_played",
    "total_d_points_played",
    "total_seconds_played",
    "total_o_opportunities",
    "total_d_opportunities",
    "total_o_opportunity_scores",
    "games_played",
    "possessions",
    "score_total",
    "total_points_played",
    "total_yards",
    "minutes_played",
    "huck_percentage",
    "offensive_efficiency",
    "yards_per_turn",
    "yards_per_completion",
    "yards_per_reception",
    "assists_per_turnover",
]

# Stats where lower is better (turnovers, etc.) - percentile should be inverted
INVERT_STATS = ["total_throwaways", "total_stalls", "total_drops"]

# Stats that are already rates/percentages and should NOT be divided by games_played
NON_COUNTING_STATS = [
    "completion_percentage",
    "huck_percentage",
    "offensive_efficiency",
    "yards_per_turn",
    "yards_per_completion",
    "yards_per_reception",
    "assists_per_turnover",
    "games_played",
]


def build_percentile_expressions(per_mode: str = "total") -> list[str]:
    """
    Build CUME_DIST() SQL expressions for all stats.

    Args:
        per_mode: "total" for raw totals, "game" for per-game, "possession" for per-100-possessions

    Returns:
        List of SQL expressions for calculating percentiles
    """
    percentile_expressions = []
    for field in STAT_FIELDS:
        # Determine the value expression based on per_mode
        if per_mode == "game" and field not in NON_COUNTING_STATS:
            # For per-game mode, divide counting stats by games_played
            value_expr = f"CASE WHEN games_played > 0 THEN CAST({field} AS NUMERIC) / games_played ELSE 0 END"
        elif per_mode == "possession" and field not in NON_COUNTING_STATS:
            # For per-possession mode, divide by possessions and multiply by 100
            value_expr = f"CASE WHEN possessions > 0 THEN CAST({field} AS NUMERIC) / possessions * 100 ELSE 0 END"
        else:
            # For total mode or non-counting stats, use raw value
            value_expr = field

        # For stats where lower is better, invert the percentile
        if field in INVERT_STATS:
            expr = f"ROUND(CAST((1 - CUME_DIST() OVER (ORDER BY {value_expr})) * 100 AS NUMERIC), 0) as {field}_percentile"
        else:
            expr = f"ROUND(CAST(CUME_DIST() OVER (ORDER BY {value_expr} NULLS FIRST) * 100 AS NUMERIC), 0) as {field}_percentile"
        percentile_expressions.append(expr)
    return percentile_expressions


def calculate_global_percentiles(
    conn,
    players: list[dict],
    seasons: list | None = None,
    teams: list | None = None,
    per_mode: str = "total",
) -> dict:
    """
    Calculate global percentile rankings for each player's stats.

    Args:
        conn: Database connection
        players: List of player dicts to calculate percentiles for
        seasons: List of season years to filter by (None or ["career"] = all seasons)
        teams: List of team IDs to filter by (None or ["all"] = all teams)
        per_mode: "total" for raw totals, "game" for per-game, "possession" for per-100-possessions

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
    names_str = ",".join(
        [f"'{name.replace(chr(39), chr(39)*2)}'" for name in full_names]
    )

    # Build CUME_DIST() expressions for all stats
    percentile_expressions = build_percentile_expressions(per_mode)

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
            percentile_expressions, team_where, names_str, per_mode
        )
    else:
        percentiles_sql = _build_season_percentiles_query(
            percentile_expressions, season_where, team_where, names_str, per_mode
        )

    try:
        result = conn.execute(text(percentiles_sql))
        percentiles_map = {}

        for row in result:
            full_name = row[0]
            percentiles = {}
            # Map all percentile values (skip the first column which is full_name)
            for i, field in enumerate(STAT_FIELDS):
                percentiles[field] = row[
                    i + 1
                ]  # Keep None as-is for frontend to show "-"
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
    names_str: str,
    per_mode: str = "total",
) -> str:
    """Build SQL query for career mode percentiles.

    Uses the player_career_stats materialized view to ensure percentiles
    match the displayed stats exactly.
    """
    # For career mode without team filter, use the pre-aggregated view directly
    # This ensures percentiles match the main query exactly
    if not team_where:
        # Build modified percentile expressions that handle 0-turnover edge cases
        # For yards_per_turn and assists_per_turnover, return NULL when turnovers = 0
        modified_expressions = []
        for field in STAT_FIELDS:
            # Determine the value expression based on per_mode
            if per_mode == "game" and field not in NON_COUNTING_STATS:
                value_expr = f"CASE WHEN games_played > 0 THEN CAST({field} AS NUMERIC) / games_played ELSE 0 END"
            elif per_mode == "possession" and field not in NON_COUNTING_STATS:
                value_expr = f"CASE WHEN possessions > 0 THEN CAST({field} AS NUMERIC) / possessions * 100 ELSE 0 END"
            else:
                value_expr = field

            if field in INVERT_STATS:
                expr = f"ROUND(CAST((1 - CUME_DIST() OVER (ORDER BY {value_expr})) * 100 AS NUMERIC), 0) as {field}_percentile"
            elif field == "yards_per_turn":
                # Return NULL percentile when turnovers = 0 (displayed value is total yards, not a ratio)
                expr = f"""CASE WHEN (total_throwaways + total_stalls + total_drops) = 0 THEN NULL
                    ELSE ROUND(CAST(CUME_DIST() OVER (ORDER BY CASE WHEN (total_throwaways + total_stalls + total_drops) > 0 THEN {value_expr} ELSE NULL END NULLS FIRST) * 100 AS NUMERIC), 0)
                END as {field}_percentile"""
            elif field == "assists_per_turnover":
                # Return NULL percentile when turnovers = 0 (displayed value is NULL or not meaningful)
                expr = f"""CASE WHEN (total_throwaways + total_stalls + total_drops) = 0 THEN NULL
                    ELSE ROUND(CAST(CUME_DIST() OVER (ORDER BY CASE WHEN (total_throwaways + total_stalls + total_drops) > 0 THEN {value_expr} ELSE NULL END NULLS FIRST) * 100 AS NUMERIC), 0)
                END as {field}_percentile"""
            elif field == "completion_percentage":
                # Return NULL percentile when throw_attempts < 100 (stat shows "-")
                expr = f"""CASE WHEN {field} IS NULL THEN NULL
                    ELSE ROUND(CAST(CUME_DIST() OVER (ORDER BY {value_expr} NULLS FIRST) * 100 AS NUMERIC), 0)
                END as {field}_percentile"""
            elif field == "offensive_efficiency":
                # Return NULL percentile when o_opportunities < 100 (stat shows "-")
                expr = f"""CASE WHEN {field} IS NULL THEN NULL
                    ELSE ROUND(CAST(CUME_DIST() OVER (ORDER BY {value_expr} NULLS FIRST) * 100 AS NUMERIC), 0)
                END as {field}_percentile"""
            elif field == "yards_per_completion":
                # Return NULL percentile when completions = 0 (stat shows "-")
                expr = f"""CASE WHEN {field} IS NULL THEN NULL
                    ELSE ROUND(CAST(CUME_DIST() OVER (ORDER BY {value_expr} NULLS FIRST) * 100 AS NUMERIC), 0)
                END as {field}_percentile"""
            elif field == "yards_per_reception":
                # Return NULL percentile when catches = 0 (stat shows "-")
                expr = f"""CASE WHEN {field} IS NULL THEN NULL
                    ELSE ROUND(CAST(CUME_DIST() OVER (ORDER BY {value_expr} NULLS FIRST) * 100 AS NUMERIC), 0)
                END as {field}_percentile"""
            else:
                expr = f"ROUND(CAST(CUME_DIST() OVER (ORDER BY {value_expr} NULLS FIRST) * 100 AS NUMERIC), 0) as {field}_percentile"
            modified_expressions.append(expr)

        return f"""
        WITH global_stats AS (
            SELECT
                full_name,
                {','.join(modified_expressions)}
            FROM player_career_stats
            WHERE games_played > 0
        )
        SELECT *
        FROM global_stats
        WHERE full_name IN ({names_str})
        """

    # For career mode with team filter, we need to aggregate from season stats
    # but group by player_id to match the main query behavior
    return f"""
    WITH team_career_stats AS (
        SELECT
            pss.player_id,
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
            SUM(pss.total_o_opportunities) as possessions,
            (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
            (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
            (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
            ROUND(SUM(pss.total_seconds_played) / 60.0, 0) as minutes_played,
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
        WHERE 1=1{team_where}
        GROUP BY pss.player_id
    ),
    games_count AS (
        SELECT
            pgs.player_id,
            COUNT(DISTINCT pgs.game_id) as games_played
        FROM player_game_stats pgs
        WHERE (pgs.o_points_played > 0 OR pgs.d_points_played > 0
               OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
              {team_where.replace("pss.", "pgs.")}
        GROUP BY pgs.player_id
    ),
    player_info AS (
        SELECT DISTINCT ON (pss.player_id)
            pss.player_id,
            p.full_name
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
        WHERE 1=1{team_where}
        ORDER BY pss.player_id, pss.year DESC
    ),
    career_with_names AS (
        SELECT
            pi.full_name,
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
        WHERE COALESCE(gc.games_played, 0) > 0
    ),
    global_stats AS (
        SELECT
            full_name,
            {','.join(percentile_expressions)}
        FROM career_with_names
    )
    SELECT *
    FROM global_stats
    WHERE full_name IN ({names_str})
    """


def _build_season_percentiles_query(
    percentile_expressions: list[str],
    season_where: str,
    team_where: str,
    names_str: str,
    per_mode: str = "total",
) -> str:
    """Build SQL query for season-specific percentiles.

    Groups by player_id to match the main query behavior, then joins to get full_name.
    Note: per_mode is used by percentile_expressions which are passed in pre-built.
    """
    # Build filters for games_count CTE (replace pss. with pgs.)
    games_season_where = season_where.replace("pss.", "pgs.")
    games_team_where = team_where.replace("pss.", "pgs.")

    return f"""
    WITH games_count AS (
        SELECT
            pgs.player_id,
            pgs.year,
            COUNT(DISTINCT pgs.game_id) as games_played
        FROM player_game_stats pgs
        WHERE (pgs.o_points_played > 0 OR pgs.d_points_played > 0
               OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
              {games_season_where}{games_team_where}
        GROUP BY pgs.player_id, pgs.year
    ),
    season_stats_by_player AS (
        SELECT
            pss.player_id,
            pss.year,
            pss.team_id,
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
        WHERE 1=1{season_where}{team_where}
        GROUP BY pss.player_id, pss.year, pss.team_id
    ),
    season_stats AS (
        SELECT
            p.full_name,
            ss.total_goals,
            ss.total_assists,
            ss.total_hockey_assists,
            ss.total_blocks,
            ss.calculated_plus_minus,
            ss.total_completions,
            ss.completion_percentage,
            ss.total_yards_thrown,
            ss.total_yards_received,
            ss.total_throwaways,
            ss.total_stalls,
            ss.total_drops,
            ss.total_callahans,
            ss.total_hucks_completed,
            ss.total_hucks_attempted,
            ss.total_hucks_received,
            ss.total_pulls,
            ss.total_o_points_played,
            ss.total_d_points_played,
            ss.total_seconds_played,
            ss.total_o_opportunities,
            ss.total_d_opportunities,
            ss.total_o_opportunity_scores,
            COALESCE(gc.games_played, 0) as games_played,
            ss.possessions,
            ss.score_total,
            ss.total_points_played,
            ss.total_yards,
            ss.minutes_played,
            ss.huck_percentage,
            ss.offensive_efficiency,
            ss.yards_per_turn,
            ss.yards_per_completion,
            ss.yards_per_reception,
            ss.assists_per_turnover
        FROM season_stats_by_player ss
        JOIN players p ON ss.player_id = p.player_id AND ss.year = p.year
        LEFT JOIN games_count gc ON ss.player_id = gc.player_id AND ss.year = gc.year
        WHERE COALESCE(gc.games_played, 0) > 0
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
