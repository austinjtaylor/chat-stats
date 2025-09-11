"""
Game-related statistics tools for sports data.
Handles game results, searches, and basic game information.
"""

from typing import Any, Optional


def get_game_results(
    db, date: Optional[str] = None, team_name: Optional[str] = None, include_stats: bool = False
) -> dict[str, Any]:
    """Get game results."""
    query = """
    SELECT g.*,
           ht.name as home_team_name, ht.abbrev as home_team_abbr,
           at.name as away_team_name, at.abbrev as away_team_abbr
    FROM games g
    LEFT JOIN teams ht ON ht.team_id = g.home_team_id AND g.year = ht.year
    LEFT JOIN teams at ON at.team_id = g.away_team_id AND g.year = at.year
    WHERE 1=1
    """
    params = {}

    if date:
        query += " AND DATE(g.start_timestamp) = :date"
        params["date"] = date

    if team_name:
        query += """ AND (LOWER(ht.name) LIKE LOWER(:team_name)
                     OR LOWER(at.name) LIKE LOWER(:team_name)
                     OR LOWER(ht.abbrev) = LOWER(:team_name)
                     OR LOWER(at.abbrev) = LOWER(:team_name))"""
        params["team_name"] = f"%{team_name}%"

    if not date and not team_name:
        query += " ORDER BY g.start_timestamp DESC LIMIT 10"
    else:
        query += " ORDER BY g.start_timestamp DESC"

    games = db.execute_query(query, params)

    result = {"games": games}

    if include_stats and games:
        # Get top performers for each game
        for game in games:
            stats_query = """
            SELECT p.full_name as name, pgs.goals, pgs.assists, pgs.blocks,
                   t.name as team_name
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.player_id
            JOIN teams t ON pgs.team_id = t.team_id AND pgs.year = t.year
            WHERE pgs.game_id = :game_id
            ORDER BY pgs.goals DESC
            LIMIT 5
            """
            top_performers = db.execute_query(
                stats_query, {"game_id": game["game_id"]}
            )
            game["top_performers"] = top_performers

    return result