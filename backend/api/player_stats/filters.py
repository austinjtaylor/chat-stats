"""
Filter building and validation for player statistics queries.
"""

from typing import Optional


def build_having_clause(
    custom_filters: list,
    per_game: bool = False,
    per_possession: bool = False,
    table_prefix: str = "",
    alias_mapping: Optional[dict] = None
) -> str:
    """
    Build a HAVING clause from custom filters.

    Args:
        custom_filters: List of filter dicts with 'field', 'operator', and 'value'
        per_game: Whether to apply per-game conversion to counting stats
        per_possession: Whether to apply per-100-possession conversion to counting stats
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
        elif per_possession and field not in non_counting_stats:
            # For per-possession filters on counting stats, divide by possessions and multiply by 100
            if table_prefix:
                field_ref = f"CASE WHEN COALESCE({table_prefix}total_o_opportunities, 0) > 0 THEN CAST({table_prefix}{field} AS NUMERIC) / {table_prefix}total_o_opportunities * 100 ELSE 0 END"
            else:
                field_ref = f"CASE WHEN total_o_opportunities > 0 THEN CAST({field} AS NUMERIC) / total_o_opportunities * 100 ELSE 0 END"
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


def get_team_career_sort_column(sort_key: str, per_game: bool = False, per_possession: bool = False) -> str:
    """
    Get the sort column for team career stats queries.
    Handles per-game sorting by dividing counting stats by games_played.
    Handles per-possession sorting by dividing counting stats by possessions and multiplying by 100.

    Args:
        sort_key: The stat field to sort by
        per_game: Whether to apply per-game conversion
        per_possession: Whether to apply per-100-possession conversion

    Returns:
        SQL expression for the sort column
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

    # If per_possession mode and this is a counting stat, divide by possessions and multiply by 100
    if per_possession and sort_key not in non_counting_stats:
        # Use COALESCE to handle NULL total_o_opportunities
        return f"CASE WHEN COALESCE(tcs.total_o_opportunities, 0) > 0 THEN CAST(tcs.{sort_key} AS NUMERIC) / tcs.total_o_opportunities * 100 ELSE 0 END"

    # If per_game mode and this is a counting stat, divide by games_played
    if per_game and sort_key not in non_counting_stats:
        # Use COALESCE to handle the LEFT JOIN case where gc.games_played might be NULL
        return f"CASE WHEN COALESCE(gc.games_played, 0) > 0 THEN CAST(tcs.{sort_key} AS NUMERIC) / gc.games_played ELSE 0 END"

    # Otherwise use the column directly from team_career_stats CTE
    return f"tcs.{sort_key}"


# Alias mapping for season stats - maps calculated column aliases to their full SQL expressions
# This is needed because PostgreSQL can't reference SELECT aliases in HAVING clauses
SEASON_STATS_ALIAS_MAPPING = {
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
