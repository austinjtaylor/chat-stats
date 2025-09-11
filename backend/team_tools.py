"""
Team-related statistics tools for sports data.
Handles team stats, standings, rosters, and playoff history.
"""

from typing import Any, Optional
from stats_utils import get_current_season


def get_team_stats(
    db, team_name: str, season: Optional[str] = None, include_roster: bool = False
) -> dict[str, Any]:
    """Get team statistics."""
    # Find team
    team_query = """
    SELECT * FROM teams
    WHERE LOWER(name) LIKE LOWER(:name)
       OR LOWER(abbrev) = LOWER(:name)
    LIMIT 1
    """
    team_results = db.execute_query(team_query, {"name": f"%{team_name}%"})

    if not team_results:
        return {"error": f"Team '{team_name}' not found"}

    team = team_results[0]

    # Get season if not provided
    if not season:
        season = get_current_season(db)

    # Get team stats
    stats_query = """
    SELECT * FROM team_season_stats
    WHERE team_id = :team_id AND year = :season
    """
    stats = db.execute_query(
        stats_query, {"team_id": team["team_id"], "season": season}
    )

    # Get playoff history for accurate reporting
    playoff_query = """
    SELECT DISTINCT year, COUNT(*) as playoff_games,
           SUM(CASE
               WHEN (home_team_id = :team_id AND home_score > away_score) OR
                    (away_team_id = :team_id AND away_score > home_score) THEN 1
               ELSE 0
           END) as playoff_wins,
           SUM(CASE
               WHEN (home_team_id = :team_id AND home_score < away_score) OR
                    (away_team_id = :team_id AND away_score < home_score) THEN 1
               ELSE 0
           END) as playoff_losses
    FROM games
    WHERE game_type LIKE '%playoff%' AND (home_team_id = :team_id OR away_team_id = :team_id)
    GROUP BY year
    ORDER BY year DESC
    """
    playoff_history = db.execute_query(
        playoff_query, {"team_id": team["team_id"]}
    )

    # Get specific season playoff record if requested
    season_playoff_record = None
    if season:
        season_playoff_query = """
        SELECT COUNT(*) as playoff_games,
               SUM(CASE
                   WHEN (home_team_id = :team_id AND home_score > away_score) OR
                        (away_team_id = :team_id AND away_score > home_score) THEN 1
                   ELSE 0
               END) as playoff_wins,
               SUM(CASE
                   WHEN (home_team_id = :team_id AND home_score < away_score) OR
                        (away_team_id = :team_id AND away_score < home_score) THEN 1
                   ELSE 0
               END) as playoff_losses
        FROM games
        WHERE game_type LIKE '%playoff%' AND (home_team_id = :team_id OR away_team_id = :team_id) AND year = :season
        """
        season_playoff_result = db.execute_query(
            season_playoff_query, {"team_id": team["team_id"], "season": season}
        )
        if season_playoff_result and season_playoff_result[0]["playoff_games"] > 0:
            season_playoff_record = season_playoff_result[0]

    result = {
        "team": team,
        "season_stats": stats[0] if stats else {},
        "season": season,
        "playoff_history": playoff_history,
        "season_playoff_record": season_playoff_record,
    }

    if include_roster:
        roster_query = """
        SELECT p.*, pss.total_goals, pss.total_assists, pss.total_blocks
        FROM players p
        LEFT JOIN player_season_stats pss ON p.player_id = pss.player_id AND pss.year = :season
        WHERE p.team_id = :team_id AND p.active = 1 AND p.year = :season
        ORDER BY pss.total_goals DESC NULLS LAST
        """
        roster = db.execute_query(
            roster_query, {"team_id": team["team_id"], "season": season}
        )
        result["roster"] = roster

    return result


def get_standings(
    db,
    season: Optional[str] = None,
    conference: Optional[str] = None,
    division: Optional[str] = None
) -> dict[str, Any]:
    """Get league standings."""
    # Get season if not provided
    if not season:
        season = get_current_season(db)

    query = """
    SELECT t.name, t.abbrev as abbreviation, t.division_name as division,
           tss.wins, tss.losses, tss.standing
    FROM team_season_stats tss
    JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
    WHERE tss.year = :season
    """
    params = {"season": season}

    if division:
        query += " AND LOWER(t.division_name) = LOWER(:division)"
        params["division"] = division

    query += " ORDER BY tss.standing ASC"

    standings = db.execute_query(query, params)

    return {
        "season": season,
        "standings": standings,
        "filters": {"division": division},
    }