"""
Game box score API endpoint with detailed player statistics.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any


def create_box_score_routes(stats_system):
    """Create game box score API routes."""
    router = APIRouter()

    @router.get("/api/games/{game_id}/box-score")
    async def get_game_box_score(game_id: str):
        """Get complete box score for a game including all player statistics"""
        try:
            # Get game information with quarter scoring
            game_query = """
            SELECT
                g.game_id,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                g.status,
                g.start_timestamp,
                g.location,
                g.year,
                g.week,
                ht.full_name as home_team_name,
                ht.city as home_team_city,
                ht.name as home_team_short_name,
                at.full_name as away_team_name,
                at.city as away_team_city,
                at.name as away_team_short_name
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
            LEFT JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
            WHERE g.game_id = :game_id
            """

            game_info = stats_system.db.execute_query(game_query, {"game_id": game_id})
            if not game_info:
                raise HTTPException(status_code=404, detail="Game not found")

            game = game_info[0]

            # Get quarter-by-quarter scoring from game events
            quarter_scores = calculate_quarter_scores(stats_system, game_id)

            # Get all player statistics for both teams
            player_stats_query = """
            SELECT
                p.full_name,
                p.jersey_number,
                pgs.player_id,
                pgs.team_id,
                pgs.o_points_played,
                pgs.d_points_played,
                (pgs.o_points_played + pgs.d_points_played) as points_played,
                pgs.assists,
                pgs.goals,
                pgs.blocks,
                pgs.completions,
                pgs.throw_attempts,
                CASE
                    WHEN pgs.throw_attempts > 0
                    THEN ROUND((pgs.completions * 100.0 / pgs.throw_attempts), 1)
                    ELSE 0
                END as completion_percentage,
                pgs.throwaways,
                pgs.stalls,
                pgs.drops,
                pgs.callahans,
                pgs.hockey_assists,
                pgs.yards_thrown,
                pgs.yards_received,
                (pgs.yards_thrown + pgs.yards_received) as total_yards,
                pgs.catches,
                pgs.hucks_completed,
                pgs.hucks_attempted,
                pgs.hucks_received,
                CASE
                    WHEN pgs.hucks_attempted > 0
                    THEN ROUND((pgs.hucks_completed * 100.0 / pgs.hucks_attempted), 1)
                    ELSE 0
                END as huck_percentage,
                CASE
                    WHEN (pgs.throwaways + pgs.stalls + pgs.drops) > 0
                    THEN ROUND((pgs.yards_thrown + pgs.yards_received) * 1.0 / (pgs.throwaways + pgs.stalls + pgs.drops), 1)
                    ELSE NULL
                END as yards_per_turn,
                (pgs.goals + pgs.assists + pgs.blocks - pgs.throwaways - pgs.drops - pgs.stalls) as plus_minus
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.player_id AND pgs.year = p.year
            WHERE pgs.game_id = :game_id
            ORDER BY pgs.team_id, (pgs.goals + pgs.assists) DESC, plus_minus DESC
            """

            all_players = stats_system.db.execute_query(
                player_stats_query, {"game_id": game_id}
            )

            # Separate players by team
            home_players = []
            away_players = []

            for player in all_players:
                player_data = {
                    "name": player["full_name"],
                    "jersey_number": player["jersey_number"] or "",
                    "points_played": player["points_played"],
                    "o_points_played": player["o_points_played"],
                    "d_points_played": player["d_points_played"],
                    "assists": player["assists"],
                    "goals": player["goals"],
                    "blocks": player["blocks"],
                    "plus_minus": player["plus_minus"],
                    "yards_received": player["yards_received"],
                    "yards_thrown": player["yards_thrown"],
                    "total_yards": player["total_yards"],
                    "completions": player["completions"],
                    "completion_percentage": player["completion_percentage"],
                    "hockey_assists": player["hockey_assists"],
                    "hucks_completed": player["hucks_completed"],
                    "hucks_received": player["hucks_received"],
                    "huck_percentage": player["huck_percentage"],
                    "turnovers": player["throwaways"] + player["stalls"],
                    "yards_per_turn": player["yards_per_turn"],
                    "stalls": player["stalls"],
                    "callahans": player["callahans"],
                    "drops": player["drops"],
                }

                if player["team_id"] == game["home_team_id"]:
                    home_players.append(player_data)
                elif player["team_id"] == game["away_team_id"]:
                    away_players.append(player_data)

            return {
                "game_id": game["game_id"],
                "status": game["status"],
                "start_timestamp": game["start_timestamp"],
                "location": game["location"],
                "year": game["year"],
                "week": game["week"],
                "home_team": {
                    "team_id": game["home_team_id"],
                    "name": game["home_team_short_name"],
                    "full_name": game["home_team_name"],
                    "city": game["home_team_city"],
                    "final_score": game["home_score"],
                    "quarter_scores": quarter_scores.get("home", []),
                    "players": home_players,
                },
                "away_team": {
                    "team_id": game["away_team_id"],
                    "name": game["away_team_short_name"],
                    "full_name": game["away_team_name"],
                    "city": game["away_team_city"],
                    "final_score": game["away_score"],
                    "quarter_scores": quarter_scores.get("away", []),
                    "players": away_players,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/games")
    async def get_games(year: int = None, team_id: str = None, limit: int = 500):
        """Get list of games with optional filters - compatible with frontend"""
        try:
            year_filter = f"AND g.year = {year}" if year else ""
            team_filter = f"AND (g.home_team_id = '{team_id}' OR g.away_team_id = '{team_id}')" if team_id and team_id != 'all' else ""

            query = f"""
            SELECT
                g.game_id,
                g.game_id as id,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                g.status,
                g.start_timestamp as date,
                g.location as venue,
                g.year,
                g.week,
                ht.full_name as home_team,
                at.full_name as away_team
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
            LEFT JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
            WHERE g.status = 'Final' {year_filter} {team_filter}
            ORDER BY g.start_timestamp DESC
            LIMIT :limit
            """

            games = stats_system.db.execute_query(query, {"limit": limit})

            return {
                "games": games,
                "total": len(games),
                "page": 1,
                "pages": 1
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/games/list")
    async def get_games_list(year: int = None, team_id: str = None, limit: int = 500):
        """Get list of all games for the game selection dropdown"""
        try:
            year_filter = f"AND g.year = {year}" if year else ""
            team_filter = f"AND (g.home_team_id = :team_id OR g.away_team_id = :team_id)" if team_id else ""

            query = f"""
            SELECT
                g.game_id,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                g.status,
                g.start_timestamp,
                g.year,
                g.week,
                ht.full_name as home_team_name,
                ht.city as home_team_city,
                at.full_name as away_team_name,
                at.city as away_team_city
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
            LEFT JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
            WHERE g.status = 'Final' {year_filter} {team_filter}
            ORDER BY g.start_timestamp DESC
            LIMIT :limit
            """

            params = {"limit": limit}
            if team_id:
                params["team_id"] = team_id

            games = stats_system.db.execute_query(query, params)

            return {
                "games": [
                    {
                        "game_id": game["game_id"],
                        "display_name": f"{game['away_team_name']} vs {game['home_team_name']}",
                        "date": game["start_timestamp"],
                        "home_team": game["home_team_name"],
                        "away_team": game["away_team_name"],
                        "home_score": game["home_score"],
                        "away_score": game["away_score"],
                        "year": game["year"],
                        "week": game["week"],
                    }
                    for game in games
                ]
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router


def calculate_quarter_scores(stats_system, game_id: str) -> Dict[str, List[int]]:
    """
    Calculate quarter-by-quarter scores from game events.
    Returns cumulative scores at the end of each quarter.
    """
    # For MVP, return simulated quarter scores based on final score
    # In production, this would parse game_events table for actual quarterly progression

    game_query = """
    SELECT home_score, away_score
    FROM games
    WHERE game_id = :game_id
    """

    result = stats_system.db.execute_query(game_query, {"game_id": game_id})
    if not result:
        return {"home": [], "away": []}

    game = result[0]
    home_final = game["home_score"] or 0
    away_final = game["away_score"] or 0

    # Simulate progressive scoring across 4 quarters
    # This is a placeholder - real implementation would use game_events
    home_quarters = []
    away_quarters = []

    if home_final > 0:
        # Distribute scores across quarters (simple distribution for MVP)
        q1_home = max(1, home_final // 4)
        q2_home = max(q1_home + 1, home_final // 2)
        q3_home = max(q2_home + 1, (home_final * 3) // 4)
        q4_home = home_final
        home_quarters = [q1_home, q2_home, q3_home, q4_home]
    else:
        home_quarters = [0, 0, 0, 0]

    if away_final > 0:
        q1_away = max(1, away_final // 4)
        q2_away = max(q1_away + 1, away_final // 2)
        q3_away = max(q2_away + 1, (away_final * 3) // 4)
        q4_away = away_final
        away_quarters = [q1_away, q2_away, q3_away, q4_away]
    else:
        away_quarters = [0, 0, 0, 0]

    return {
        "home": home_quarters,
        "away": away_quarters
    }