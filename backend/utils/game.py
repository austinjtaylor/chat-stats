"""
Detailed game statistics and analysis tools.
Handles comprehensive game details, individual leaders, and team statistics.
"""

from typing import Any

from data.possession import (
    calculate_possessions,
    calculate_redzone_stats_for_team,
    calculate_team_percentages,
)


def get_game_details(
    db,
    game_id: str | None = None,
    date: str | None = None,
    teams: str | None = None,
) -> dict[str, Any]:
    """Get comprehensive game details similar to UFA game summary page."""

    # First, find the game
    game_query = """
    SELECT g.*,
           ht.name as home_team_name, ht.abbrev as home_team_abbr, ht.standing as home_standing,
           ht.team_id as home_full_team_id,
           at.name as away_team_name, at.abbrev as away_team_abbr, at.standing as away_standing,
           at.team_id as away_full_team_id
    FROM games g
    LEFT JOIN teams ht ON ht.team_id = g.home_team_id AND g.year = ht.year
    LEFT JOIN teams at ON at.team_id = g.away_team_id AND g.year = at.year
    WHERE 1=1
    """
    params = {}

    if game_id:
        game_query += " AND g.game_id = :game_id"
        params["game_id"] = game_id
    elif date and teams:
        game_query += " AND DATE(g.start_timestamp) = :date"
        game_query += """ AND (
            (LOWER(ht.abbrev) LIKE LOWER(:team1) AND LOWER(at.abbrev) LIKE LOWER(:team2))
            OR (LOWER(ht.abbrev) LIKE LOWER(:team2) AND LOWER(at.abbrev) LIKE LOWER(:team1))
        )"""
        params["date"] = date
        team_parts = (
            teams.replace("-", " ").replace("vs", " ").replace("@", " ").split()
        )
        if len(team_parts) >= 2:
            params["team1"] = f"%{team_parts[0]}%"
            params["team2"] = f"%{team_parts[1]}%"

    game = db.execute_query(game_query, params)
    if not game:
        return {"error": "Game not found"}

    game = game[0]
    game_id = game["game_id"]

    # Get individual leaders (top 1 per category per team)
    leaders = get_individual_leaders(db, game_id, game)

    # Get basic team statistics
    team_stats = get_team_statistics(db, game_id)

    # Get possession stats for each team
    home_possessions = calculate_possessions(
        db, game_id, game["home_full_team_id"], True
    )
    away_possessions = calculate_possessions(
        db, game_id, game["away_full_team_id"], False
    )

    # Organize team stats by team and add possession data
    home_stats = None
    away_stats = None
    for stat in team_stats:
        if stat["team_id"] == game["home_full_team_id"]:
            home_stats = stat
        elif stat["team_id"] == game["away_full_team_id"]:
            away_stats = stat

    # Add possession data if available
    if home_stats and home_possessions:
        home_stats.update(home_possessions)
    if away_stats and away_possessions:
        away_stats.update(away_possessions)

    # Calculate percentages with exact UFA formulas
    home_stats = calculate_team_percentages(home_stats, away_stats)
    away_stats = calculate_team_percentages(away_stats, home_stats)

    # Add redzone percentage to stats if available
    if home_stats:
        redzone_data = calculate_redzone_stats_for_team(
            db, game_id, game["home_full_team_id"], is_home_team=True
        )
        if redzone_data is not None:
            home_stats["redzone_percentage"] = redzone_data["percentage"]
            home_stats["redzone_percentage_display"] = (
                f"{redzone_data['percentage']}% ({redzone_data['goals']}/{redzone_data['possessions']})"
            )

    if away_stats:
        redzone_data = calculate_redzone_stats_for_team(
            db, game_id, game["away_full_team_id"], is_home_team=False
        )
        if redzone_data is not None:
            away_stats["redzone_percentage"] = redzone_data["percentage"]
            away_stats["redzone_percentage_display"] = (
                f"{redzone_data['percentage']}% ({redzone_data['goals']}/{redzone_data['possessions']})"
            )

    return {
        "game": game,
        "individual_leaders": leaders,
        "team_statistics": {"home": home_stats, "away": away_stats},
    }


def get_individual_leaders(db, game_id: str, game: dict[str, Any]) -> dict[str, Any]:
    """Get individual stat leaders for a game."""
    leaders = {}

    # Helper function to get top player for a stat
    def get_stat_leader(stat_column, stat_name):
        query = f"""
        SELECT p.full_name, pgs.{stat_column} as value, pgs.team_id,
               t.name as team_name
        FROM player_game_stats pgs
        JOIN players p ON pgs.player_id = p.player_id
        JOIN teams t ON pgs.team_id = t.team_id AND pgs.year = t.year
        WHERE pgs.game_id = :game_id
        AND pgs.team_id = :team_id
        AND pgs.{stat_column} > 0
        ORDER BY pgs.{stat_column} DESC
        LIMIT 1
        """

        home_leader = db.execute_query(
            query, {"game_id": game_id, "team_id": game["home_full_team_id"]}
        )

        away_leader = db.execute_query(
            query, {"game_id": game_id, "team_id": game["away_full_team_id"]}
        )

        return {
            "home": home_leader[0] if home_leader else None,
            "away": away_leader[0] if away_leader else None,
        }

    # Get leaders for each category
    leaders["assists"] = get_stat_leader("assists", "Assists")
    leaders["goals"] = get_stat_leader("goals", "Goals")
    leaders["blocks"] = get_stat_leader("blocks", "Blocks")
    leaders["completions"] = get_stat_leader("completions", "Completions")
    leaders["points_played"] = get_stat_leader(
        "o_points_played + d_points_played", "Points Played"
    )

    # Plus/minus requires special handling
    pm_query = """
    SELECT p.full_name, 
           (pgs.goals + pgs.assists + pgs.blocks - pgs.throwaways - pgs.stalls - pgs.drops) as value,
           pgs.team_id, t.name as team_name
    FROM player_game_stats pgs
    JOIN players p ON pgs.player_id = p.player_id
    JOIN teams t ON pgs.team_id = t.team_id AND pgs.year = t.year
    WHERE pgs.game_id = :game_id
    AND pgs.team_id = :team_id
    ORDER BY value DESC
    LIMIT 1
    """

    home_pm = db.execute_query(
        pm_query, {"game_id": game_id, "team_id": game["home_full_team_id"]}
    )

    away_pm = db.execute_query(
        pm_query, {"game_id": game_id, "team_id": game["away_full_team_id"]}
    )

    leaders["plus_minus"] = {
        "home": home_pm[0] if home_pm else None,
        "away": away_pm[0] if away_pm else None,
    }

    return leaders


def get_team_statistics(db, game_id: str) -> list[dict[str, Any]]:
    """Get basic team statistics for a game."""
    team_stats_query = """
    SELECT 
        team_id,
        SUM(completions) as total_completions,
        SUM(throw_attempts) as total_attempts,
        SUM(hucks_completed) as total_hucks_completed,
        SUM(hucks_attempted) as total_hucks_attempted,
        SUM(blocks) as total_blocks,
        SUM(throwaways + stalls + drops) as total_turnovers,
        SUM(o_points_played) as total_o_points,
        SUM(o_points_scored) as total_o_scores,
        SUM(d_points_played) as total_d_points,
        SUM(d_points_scored) as total_d_scores
    FROM player_game_stats
    WHERE game_id = :game_id
    GROUP BY team_id
    """

    return db.execute_query(team_stats_query, {"game_id": game_id})
