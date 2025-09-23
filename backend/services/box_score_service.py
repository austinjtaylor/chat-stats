"""
Box score service for calculating team statistics.
"""

from typing import Dict, Any


def calculate_team_stats(stats_system, game_id: str, team_id: str, is_home: bool) -> Dict[str, Any]:
    """
    Calculate team statistics for a single game.

    Args:
        stats_system: The stats system instance
        game_id: Game identifier
        team_id: Team identifier
        is_home: Whether this is the home team

    Returns:
        Dictionary containing all team statistics
    """
    from data.possession import calculate_possessions, calculate_redzone_stats_for_team

    # Get team aggregate stats from player_game_stats
    team_stats_query = """
    SELECT
        SUM(completions) as total_completions,
        SUM(throw_attempts) as total_attempts,
        SUM(hucks_completed) as total_hucks_completed,
        SUM(hucks_attempted) as total_hucks_attempted,
        SUM(blocks) as total_blocks,
        SUM(throwaways) as total_throwaways,
        SUM(stalls) as total_stalls,
        SUM(drops) as total_drops
    FROM player_game_stats
    WHERE game_id = :game_id AND team_id = :team_id
    """

    team_stats_result = stats_system.db.execute_query(
        team_stats_query, {"game_id": game_id, "team_id": team_id}
    )

    if not team_stats_result:
        return {}

    team_stats = team_stats_result[0]

    # Calculate basic percentages
    completions = team_stats["total_completions"] or 0
    attempts = team_stats["total_attempts"] or 0
    completion_pct = round((completions / attempts * 100), 1) if attempts > 0 else 0

    hucks_completed = team_stats["total_hucks_completed"] or 0
    hucks_attempted = team_stats["total_hucks_attempted"] or 0
    huck_pct = round((hucks_completed / hucks_attempted * 100), 1) if hucks_attempted > 0 else 0

    blocks = team_stats["total_blocks"] or 0
    turnovers = (team_stats["total_throwaways"] or 0) + (team_stats["total_stalls"] or 0)

    # Calculate possession stats from game_events
    possession_stats = calculate_possessions(stats_system.db, game_id, team_id, is_home)

    # Calculate red zone stats
    redzone_stats = calculate_redzone_stats_for_team(stats_system.db, game_id, team_id, is_home)

    # Build result dictionary
    result = {
        "completions": {
            "percentage": completion_pct,
            "made": completions,
            "attempted": attempts
        },
        "hucks": {
            "percentage": huck_pct,
            "made": hucks_completed,
            "attempted": hucks_attempted
        },
        "blocks": blocks,
        "turnovers": turnovers
    }

    # Add possession stats if available
    if possession_stats:
        # Hold %
        hold_pct = 0
        hold_made = possession_stats.get("o_line_scores", 0)
        hold_total = possession_stats.get("o_line_points", 0)
        if hold_total > 0:
            hold_pct = round((hold_made / hold_total * 100), 1)

        # O-Line Conversion %
        o_conv_pct = 0
        o_conv_made = possession_stats.get("o_line_scores", 0)
        o_conv_total = possession_stats.get("o_line_possessions", 0)
        if o_conv_total > 0:
            o_conv_pct = round((o_conv_made / o_conv_total * 100), 1)

        # Break %
        break_pct = 0
        break_made = possession_stats.get("d_line_scores", 0)
        break_total = possession_stats.get("d_line_points", 0)
        if break_total > 0:
            break_pct = round((break_made / break_total * 100), 1)

        # D-Line Conversion %
        d_conv_pct = 0
        d_conv_made = possession_stats.get("d_line_scores", 0)
        d_conv_total = possession_stats.get("d_line_possessions", 0)
        if d_conv_total > 0:
            d_conv_pct = round((d_conv_made / d_conv_total * 100), 1)

        result["hold"] = {
            "percentage": hold_pct,
            "made": hold_made,
            "total": hold_total
        }
        result["o_line_conversion"] = {
            "percentage": o_conv_pct,
            "made": o_conv_made,
            "total": o_conv_total
        }
        result["break"] = {
            "percentage": break_pct,
            "made": break_made,
            "total": break_total
        }
        result["d_line_conversion"] = {
            "percentage": d_conv_pct,
            "made": d_conv_made,
            "total": d_conv_total
        }

    # Add red zone stats if available
    if redzone_stats:
        result["redzone_conversion"] = {
            "percentage": redzone_stats.get("percentage", 0),
            "made": redzone_stats.get("goals", 0),
            "total": redzone_stats.get("possessions", 0)
        }

    return result