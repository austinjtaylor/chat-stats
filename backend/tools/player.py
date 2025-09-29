"""
Player-related statistics tools for sports data.
Handles player stats, comparisons, searches, and league leaders.
"""

from typing import Any

from utils.stats import get_current_season


def get_player_stats(
    db: Any,
    player_name: str,
    season: int | None = None,
    stat_type: str = "season",
    game_date: str | None = None,
) -> dict[str, Any]:
    """Get player statistics."""
    # Find player
    player_query = """
    SELECT p.*, t.name as team_name
    FROM players p
    LEFT JOIN teams t ON p.team_id = t.team_id
    WHERE LOWER(p.full_name) LIKE LOWER(:name)
    LIMIT 1
    """
    player_results = db.execute_query(player_query, {"name": f"%{player_name}%"})

    if not player_results:
        return {"error": f"Player '{player_name}' not found"}

    player = player_results[0]

    if stat_type == "season":
        # Get season stats
        if not season:
            season = get_current_season(db)

        stats_query = """
        SELECT pss.*, t.name as team_name
        FROM player_season_stats pss
        JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
        WHERE pss.player_id = :player_id AND pss.year = :season
        """
        stats = db.execute_query(
            stats_query, {"player_id": player["player_id"], "season": season}
        )

        if stats:
            return {"player": player, "season_stats": stats[0], "season": season}
        else:
            return {
                "player": player,
                "message": f"No stats found for {player['full_name']} in season {season}",
            }

    elif stat_type == "game":
        # Get game stats
        game_query = """
        SELECT pgs.*, g.start_timestamp, g.home_score, g.away_score,
               ht.name as home_team, at.name as away_team
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.game_id
        JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
        JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
        WHERE pgs.player_id = :player_id
        """
        params = {"player_id": player["player_id"]}

        if game_date:
            game_query += " AND DATE(g.start_timestamp) = :game_date"
            params["game_date"] = game_date
        else:
            game_query += " ORDER BY g.start_timestamp DESC LIMIT 10"

        games = db.execute_query(game_query, params)

        return {"player": player, "game_stats": games}

    elif stat_type == "career":
        # Get career totals
        career_query = """
        SELECT
            COUNT(DISTINCT year) as seasons_played,
            SUM(total_goals) as career_goals,
            SUM(total_assists) as career_assists,
            SUM(total_blocks) as career_blocks,
            SUM(total_throwaways) as career_throwaways,
            SUM(total_catches) as career_catches,
            SUM(total_completions) as career_completions
        FROM player_season_stats
        WHERE player_id = :player_id
        """
        career = db.execute_query(career_query, {"player_id": player["player_id"]})

        return {"player": player, "career_stats": career[0] if career else {}}

    return {"error": f"Invalid stat_type: {stat_type}"}


def get_league_leaders(
    db: Any, category: str, season: int | None = None, limit: int = 3
) -> dict[str, Any]:
    """Get league leaders in a statistical category."""
    # Get season if not provided
    if not season:
        season = get_current_season(db)

    # Special handling for plus_minus (from calculated field in season stats)
    if category == "plus_minus":
        # Use calculated_plus_minus from player_season_stats
        query = """
        SELECT p.full_name as name, t.name as team_name,
               pss.calculated_plus_minus as value
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
        WHERE pss.year = :season AND pss.calculated_plus_minus IS NOT NULL
        ORDER BY value DESC
        LIMIT :limit
        """

        leaders = db.execute_query(query, {"season": season, "limit": limit})

        # If no results with season filter, try without season filter (for sample data)
        if not leaders:
            query = """
            SELECT p.full_name as name, t.name as team_name,
                   pss.calculated_plus_minus as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id
            JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            WHERE pss.calculated_plus_minus IS NOT NULL
            ORDER BY value DESC
            LIMIT :limit
            """
            leaders = db.execute_query(query, {"limit": limit})

        return {
            "category": category,
            "season": season,
            "leaders": leaders,
            "note": "Plus/minus aggregated from individual games. For worst plus/minus, look at the bottom of the list or explicitly query for ascending order.",
        }

    # Map category to column (Ultimate Frisbee stats)
    category_map = {
        "goals": "total_goals",
        "assists": "total_assists",
        "blocks": "total_blocks",
        "throwaways": "total_throwaways",
        "catches": "total_catches",
        "completions": "total_completions",
        "total_goals": "total_goals",
        "total_assists": "total_assists",
        "total_blocks": "total_blocks",
        "total_throwaways": "total_throwaways",
        "total_catches": "total_catches",
        "total_completions": "total_completions",
        "completion_percentage": "completion_percentage",
    }

    if category not in category_map:
        return {"error": f"Invalid category: {category}"}

    column = category_map[category]

    # Query for Ultimate Frisbee stats
    query = f"""
    SELECT p.full_name as name, t.name as team_name, pss.{column} as value
    FROM player_season_stats pss
    JOIN players p ON pss.player_id = p.player_id
    JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
    WHERE pss.year = :season AND pss.{column} IS NOT NULL
    ORDER BY pss.{column} DESC
    LIMIT :limit
    """

    leaders = db.execute_query(query, {"season": season, "limit": limit})

    return {"category": category, "season": season, "leaders": leaders}


def compare_players(
    db: Any,
    player_names: list[str],
    season: int | None = None,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Compare multiple players."""
    if len(player_names) < 2 or len(player_names) > 5:
        return {"error": "Please provide 2-5 player names for comparison"}

    # Get season if not provided
    if not season:
        season = get_current_season(db)

    # Default categories if not specified (Ultimate Frisbee stats)
    if not categories:
        categories = [
            "total_goals",
            "total_assists",
            "total_blocks",
            "total_throwaways",
            "completion_percentage",
        ]

    comparison = []

    for player_name in player_names:
        # Find player
        player_query = """
        SELECT p.player_id, p.full_name, t.name as team_name
        FROM players p
        LEFT JOIN teams t ON p.team_id = t.team_id AND p.year = t.year
        WHERE LOWER(p.full_name) LIKE LOWER(:name)
        LIMIT 1
        """
        player_results = db.execute_query(player_query, {"name": f"%{player_name}%"})

        if player_results:
            player = player_results[0]

            # Get stats
            stats_query = """
            SELECT * FROM player_season_stats
            WHERE player_id = :player_id AND year = :season
            """
            stats = db.execute_query(
                stats_query, {"player_id": player["player_id"], "season": season}
            )

            if stats:
                player_data = {
                    "name": player["full_name"],
                    "team": player["team_name"],
                }
                for cat in categories:
                    if cat in stats[0]:
                        player_data[cat] = stats[0][cat]
                comparison.append(player_data)

    return {"season": season, "categories": categories, "comparison": comparison}


def search_players(
    db: Any,
    search_term: str | None = None,
    team_name: str | None = None,
    position: str | None = None,
) -> dict[str, Any]:
    """Search for players."""
    query = """
    SELECT p.*, t.name as team_name
    FROM players p
    LEFT JOIN teams t ON p.team_id = t.team_id AND p.year = t.year
    WHERE p.active = 1
    """
    params = {}

    if search_term:
        query += " AND LOWER(p.full_name) LIKE LOWER(:search_term)"
        params["search_term"] = f"%{search_term}%"

    if team_name:
        query += """ AND (LOWER(t.name) LIKE LOWER(:team_name)
                     OR LOWER(t.abbrev) = LOWER(:team_name))"""
        params["team_name"] = f"%{team_name}%"

    if position:
        query += " AND LOWER(p.position) = LOWER(:position)"
        params["position"] = position

    query += " ORDER BY p.full_name LIMIT 50"

    players = db.execute_query(query, params)

    return {"players": players, "count": len(players)}


def get_worst_performers(
    db: Any, category: str, season: int | None = None, limit: int = 10
) -> dict[str, Any]:
    """Get players with worst performance in a category."""
    # Get season if not provided
    if not season:
        season = get_current_season(db)

    if category == "plus_minus":
        # Get worst plus/minus (most negative calculated value)
        query = """
        SELECT p.full_name as name, t.name as team_name,
               pss.calculated_plus_minus as value
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
        WHERE pss.year = :season AND pss.calculated_plus_minus IS NOT NULL
        ORDER BY value ASC
        LIMIT :limit
        """

        worst = db.execute_query(query, {"season": season, "limit": limit})

        # If no results with season filter, try without season filter (for sample data)
        if not worst:
            query = """
            SELECT p.full_name as name, t.name as team_name,
                   pss.calculated_plus_minus as value
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id
            JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            WHERE pss.calculated_plus_minus IS NOT NULL
            ORDER BY value ASC
            LIMIT :limit
            """
            worst = db.execute_query(query, {"limit": limit})

        return {
            "category": f"worst_{category}",
            "season": season,
            "worst_performers": worst,
            "note": "Players with the worst (most negative) plus/minus",
        }

    elif category == "turnovers":
        # Get most turnovers (throwaways in Ultimate Frisbee)
        query = """
        SELECT p.full_name as name, t.name as team_name,
               pss.total_throwaways as value
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
        WHERE pss.year = :season AND pss.total_throwaways IS NOT NULL
        ORDER BY pss.total_throwaways DESC
        LIMIT :limit
        """

        worst = db.execute_query(query, {"season": season, "limit": limit})

        return {
            "category": f"most_{category}",
            "season": season,
            "worst_performers": worst,
        }

    elif category == "completion_percentage":
        # Get worst completion percentage
        query = """
        SELECT p.full_name as name, t.name as team_name,
               pss.completion_percentage as value
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id
        JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
        WHERE pss.year = :season
            AND pss.completion_percentage IS NOT NULL
        ORDER BY pss.completion_percentage ASC
        LIMIT :limit
        """

        worst = db.execute_query(query, {"season": season, "limit": limit})

        return {
            "category": f"worst_{category}",
            "season": season,
            "worst_performers": worst,
        }

    return {"error": f"Invalid category: {category}"}
