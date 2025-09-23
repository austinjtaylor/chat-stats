"""
SQL query building helpers and data conversion utilities.
"""


def get_sort_column(sort_key, is_career=False, per_game=False, team=None):
    """Map sort keys to actual database columns with proper table prefixes"""

    if is_career:
        # For career stats, use the actual SQL expressions, not aliases
        career_columns = {
            "full_name": "p.full_name",
            "total_goals": "SUM(pss.total_goals)",
            "total_assists": "SUM(pss.total_assists)",
            "total_blocks": "SUM(pss.total_blocks)",
            "calculated_plus_minus": "(SUM(pss.total_goals) + SUM(pss.total_assists) + SUM(pss.total_blocks) - SUM(pss.total_throwaways) - SUM(pss.total_drops))",
            "completion_percentage": "CASE WHEN SUM(pss.total_throw_attempts) > 0 THEN ROUND(SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts), 1) ELSE 0 END",
            "total_completions": "SUM(pss.total_completions)",
            "total_yards_thrown": "SUM(pss.total_yards_thrown)",
            "total_yards_received": "SUM(pss.total_yards_received)",
            "total_hockey_assists": "SUM(pss.total_hockey_assists)",
            "total_throwaways": "SUM(pss.total_throwaways)",
            "total_stalls": "SUM(pss.total_stalls)",
            "total_drops": "SUM(pss.total_drops)",
            "total_callahans": "SUM(pss.total_callahans)",
            "total_hucks_completed": "SUM(pss.total_hucks_completed)",
            "total_hucks_attempted": "SUM(pss.total_hucks_attempted)",
            "total_pulls": "SUM(pss.total_pulls)",
            "total_o_points_played": "SUM(pss.total_o_points_played)",
            "total_d_points_played": "SUM(pss.total_d_points_played)",
            "total_seconds_played": "SUM(pss.total_seconds_played)",
            "games_played": "games_played",
            "possessions": "SUM(pss.total_o_opportunities)",
            "score_total": "(SUM(pss.total_goals) + SUM(pss.total_assists))",
            "total_points_played": "(SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played))",
            "total_yards": "(SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received))",
            "minutes_played": "ROUND(SUM(pss.total_seconds_played) / 60.0, 0)",
            "huck_percentage": "CASE WHEN SUM(pss.total_hucks_attempted) > 0 THEN ROUND(SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted), 1) ELSE 0 END",
            "offensive_efficiency": "CASE WHEN SUM(pss.total_o_opportunities) >= 20 THEN ROUND(SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities), 1) ELSE NULL END",
            "yards_per_turn": "CASE WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0 THEN ROUND((SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 1) ELSE NULL END",
        }
        base_column = career_columns.get(sort_key, f"SUM(pss.{sort_key})")

        # If per_game mode and sorting by a counting stat, divide by games_played
        if per_game and sort_key not in [
            "full_name",
            "completion_percentage",
            "huck_percentage",
            "offensive_efficiency",
            "yards_per_turn",
            "games_played",
        ]:
            # Use the full games_played subquery for career stats
            team_filter = (
                f" AND pgs_sub.team_id = '{team}'" if team and team != "all" else ""
            )
            games_played_expr = f"""(SELECT COUNT(DISTINCT pgs_sub.game_id) 
                 FROM player_game_stats pgs_sub 
                 JOIN games g_sub ON pgs_sub.game_id = g_sub.game_id
                 WHERE pgs_sub.player_id = pss.player_id 
                 AND (pgs_sub.o_points_played > 0 OR pgs_sub.d_points_played > 0 OR pgs_sub.seconds_played > 0 OR pgs_sub.goals > 0 OR pgs_sub.assists > 0){team_filter})"""
            return f"CASE WHEN {games_played_expr} > 0 THEN CAST({base_column} AS REAL) / {games_played_expr} ELSE 0 END"

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
        return f"CASE WHEN {games_played_col} > 0 THEN CAST({base_column} AS REAL) / {games_played_col} ELSE 0 END"

    return base_column


def convert_to_per_game_stats(players):
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
