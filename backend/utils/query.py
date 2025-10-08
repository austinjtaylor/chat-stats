"""
SQL query building helpers and data conversion utilities.
"""

from typing import Any


def get_sort_column(
    sort_key: str,
    is_career: bool = False,
    per_game: bool = False,
    team: str | None = None,
) -> str:
    """Map sort keys to actual database columns with proper table prefixes"""

    if is_career:
        # For pre-computed career stats table, use direct column names
        career_columns = {
            "full_name": "full_name",
            "total_goals": "total_goals",
            "total_assists": "total_assists",
            "total_blocks": "total_blocks",
            "calculated_plus_minus": "calculated_plus_minus",
            "completion_percentage": "completion_percentage",
            "total_completions": "total_completions",
            "total_yards_thrown": "total_yards_thrown",
            "total_yards_received": "total_yards_received",
            "total_hockey_assists": "total_hockey_assists",
            "total_throwaways": "total_throwaways",
            "total_stalls": "total_stalls",
            "total_drops": "total_drops",
            "total_callahans": "total_callahans",
            "total_hucks_completed": "total_hucks_completed",
            "total_hucks_attempted": "total_hucks_attempted",
            "total_hucks_received": "total_hucks_received",
            "total_pulls": "total_pulls",
            "total_o_points_played": "total_o_points_played",
            "total_d_points_played": "total_d_points_played",
            "total_seconds_played": "total_seconds_played",
            "games_played": "games_played",
            "possessions": "possessions",
            "score_total": "score_total",
            "total_points_played": "total_points_played",
            "total_yards": "total_yards",
            "minutes_played": "minutes_played",
            "huck_percentage": "huck_percentage",
            "offensive_efficiency": "offensive_efficiency",
            "yards_per_turn": "yards_per_turn",
        }
        base_column = career_columns.get(sort_key, sort_key)

        # If per_game mode and sorting by a counting stat, divide by games_played
        if per_game and sort_key not in [
            "full_name",
            "completion_percentage",
            "huck_percentage",
            "offensive_efficiency",
            "yards_per_turn",
            "games_played",
        ]:
            # For pre-computed career stats, just use games_played column
            return f"CASE WHEN games_played > 0 THEN CAST({base_column} AS NUMERIC) / games_played ELSE 0 END"

        return base_column

    # For single season stats, use table prefixes
    column_mapping = {
        "full_name": "p.full_name",
        "total_goals": "pss.total_goals",
        "total_assists": "pss.total_assists",
        "total_blocks": "pss.total_blocks",
        "calculated_plus_minus": "pss.calculated_plus_minus",
        "completion_percentage": "pss.completion_percentage",
        "total_completions": "pss.total_completions",
        "total_yards_thrown": "pss.total_yards_thrown",
        "total_yards_received": "pss.total_yards_received",
        "total_hockey_assists": "pss.total_hockey_assists",
        "total_throwaways": "pss.total_throwaways",
        "total_stalls": "pss.total_stalls",
        "total_drops": "pss.total_drops",
        "total_callahans": "pss.total_callahans",
        "total_hucks_completed": "pss.total_hucks_completed",
        "total_hucks_attempted": "pss.total_hucks_attempted",
        "total_hucks_received": "pss.total_hucks_received",
        "total_pulls": "pss.total_pulls",
        "total_o_points_played": "pss.total_o_points_played",
        "total_d_points_played": "pss.total_d_points_played",
        "total_seconds_played": "pss.total_seconds_played",
        "games_played": "COUNT(DISTINCT CASE WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0) THEN pgs.game_id ELSE NULL END)",
        "possessions": "pss.total_o_opportunities",
        "score_total": "(pss.total_goals + pss.total_assists)",
        "total_points_played": "(pss.total_o_points_played + pss.total_d_points_played)",
        "total_yards": "(pss.total_yards_thrown + pss.total_yards_received)",
        "minutes_played": "ROUND(pss.total_seconds_played / 60.0, 0)",
        "huck_percentage": "CASE WHEN pss.total_hucks_attempted > 0 THEN ROUND(pss.total_hucks_completed * 100.0 / pss.total_hucks_attempted, 1) ELSE 0 END",
        "offensive_efficiency": "CASE WHEN pss.total_o_opportunities >= 20 THEN ROUND(pss.total_o_opportunity_scores * 100.0 / pss.total_o_opportunities, 1) ELSE NULL END",
        "yards_per_turn": "CASE WHEN (pss.total_throwaways + pss.total_stalls + pss.total_drops) > 0 THEN ROUND((pss.total_yards_thrown + pss.total_yards_received) * 1.0 / (pss.total_throwaways + pss.total_stalls + pss.total_drops), 1) ELSE NULL END",
    }

    # Get the base column
    base_column = column_mapping.get(sort_key, f"pss.{sort_key}")

    # If per_game mode and sorting by a counting stat, divide by games_played
    if per_game and sort_key not in [
        "full_name",
        "completion_percentage",
        "huck_percentage",
        "offensive_efficiency",
        "yards_per_turn",
        "games_played",
    ]:
        games_played_col = column_mapping["games_played"]
        return f"CASE WHEN {games_played_col} > 0 THEN CAST({base_column} AS NUMERIC) / {games_played_col} ELSE 0 END"

    return base_column


def convert_to_per_game_stats(players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert player statistics to per-game averages."""
    for player in players:
        games = player["games_played"]
        if games > 0:
            # Convert counting stats to per-game averages
            per_game_stats = [
                "total_points_played",
                "possessions",
                "score_total",
                "total_assists",
                "total_goals",
                "total_blocks",
                "total_completions",
                "total_yards",
                "total_yards_thrown",
                "total_yards_received",
                "total_hockey_assists",
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
                "minutes_played",
                "total_o_opportunities",
                "total_d_opportunities",
                "total_o_opportunity_scores",
            ]

            for stat in per_game_stats:
                if stat in player and player[stat] is not None:
                    # Use proper rounding to avoid floating point precision issues
                    value = player[stat] / games
                    # Round to 1 decimal place, ensuring proper precision
                    player[stat] = float(format(value, ".1f"))

            # Plus/minus also needs to be averaged
            if player["calculated_plus_minus"] is not None:
                value = player["calculated_plus_minus"] / games
                player["calculated_plus_minus"] = float(format(value, ".1f"))

    return players
