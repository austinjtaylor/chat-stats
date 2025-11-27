"""
Game box score API endpoint with detailed player and team statistics.
"""

from fastapi import APIRouter, HTTPException
from services.box_score_service import calculate_team_stats
from services.play_by_play_service import calculate_play_by_play
from services.quarter_score_service import calculate_quarter_scores
from data.cache import get_cache, cache_key_for_endpoint


def create_box_score_routes(stats_system):
    """Create game box score API routes."""
    router = APIRouter()

    @router.get("/api/games/{game_id}/box-score")
    async def get_game_box_score(game_id: str):
        """Get complete box score for a game including all player statistics"""
        try:
            # Check cache first
            cache = get_cache()
            cache_key = cache_key_for_endpoint("box_score", game_id=game_id)
            cached_result = cache.get(cache_key)

            if cached_result is not None:
                return cached_result

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
                ht.logo_url as home_team_logo_url,
                at.full_name as away_team_name,
                at.city as away_team_city,
                at.name as away_team_short_name,
                at.logo_url as away_team_logo_url
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
            AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0)
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
                    "turnovers": player["throwaways"],
                    "yards_per_turn": player["yards_per_turn"],
                    "stalls": player["stalls"],
                    "callahans": player["callahans"],
                    "drops": player["drops"],
                }

                if player["team_id"] == game["home_team_id"]:
                    home_players.append(player_data)
                elif player["team_id"] == game["away_team_id"]:
                    away_players.append(player_data)

            # Calculate team statistics
            home_team_stats = calculate_team_stats(
                stats_system, game_id, game["home_team_id"], is_home=True
            )
            away_team_stats = calculate_team_stats(
                stats_system, game_id, game["away_team_id"], is_home=False
            )

            result = {
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
                    "stats": home_team_stats,
                    "logo_url": game.get("home_team_logo_url"),
                },
                "away_team": {
                    "team_id": game["away_team_id"],
                    "name": game["away_team_short_name"],
                    "full_name": game["away_team_name"],
                    "city": game["away_team_city"],
                    "final_score": game["away_score"],
                    "quarter_scores": quarter_scores.get("away", []),
                    "players": away_players,
                    "stats": away_team_stats,
                    "logo_url": game.get("away_team_logo_url"),
                },
            }

            # Cache the result (longer TTL for Final games since they never change)
            ttl = (
                3600 if game["status"] == "Final" else 300
            )  # 1 hour for final, 5 min for in-progress
            cache.set(cache_key, result, ttl=ttl)

            return result

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/games")
    async def get_games(year: int = None, team_id: str = None, limit: int = 500):
        """Get list of games with optional filters - compatible with frontend"""
        try:
            year_filter = f"AND g.year = {year}" if year else ""
            team_filter = (
                f"AND (g.home_team_id = '{team_id}' OR g.away_team_id = '{team_id}')"
                if team_id and team_id != "all"
                else ""
            )

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

            return {"games": games, "total": len(games), "page": 1, "pages": 1}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/games/list")
    async def get_games_list(year: int = None, team_id: str = None, limit: int = 500):
        """Get list of all games for the game selection dropdown"""
        try:
            year_filter = f"AND g.year = {year}" if year else ""
            team_filter = (
                "AND (g.home_team_id = :team_id OR g.away_team_id = :team_id)"
                if team_id
                else ""
            )

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
            WHERE g.status = 'Final'
              AND g.game_type != 'allstar'
              AND LOWER(g.game_id) NOT LIKE '%allstar%'
              AND LOWER(g.home_team_id) NOT LIKE '%allstar%'
              AND LOWER(g.away_team_id) NOT LIKE '%allstar%'
              {year_filter} {team_filter}
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
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/games/{game_id}/play-by-play")
    async def get_game_play_by_play(game_id: str):
        """Get play-by-play data for a game"""
        try:
            # Check cache first
            cache = get_cache()
            cache_key = cache_key_for_endpoint("play_by_play", game_id=game_id)
            cached_result = cache.get(cache_key)

            if cached_result is not None:
                return cached_result

            # Get game status to determine cache TTL
            game_query = "SELECT status FROM games WHERE game_id = :game_id"
            game_result = stats_system.db.execute_query(
                game_query, {"game_id": game_id}
            )

            points = calculate_play_by_play(stats_system, game_id)
            result = {"points": points}

            # Cache the result (longer TTL for Final games since they never change)
            ttl = 3600  # Default 1 hour
            if game_result and game_result[0].get("status") == "Final":
                ttl = 3600  # 1 hour for final games
            else:
                ttl = 300  # 5 minutes for in-progress games

            cache.set(cache_key, result, ttl=ttl)

            return result
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return router


# Functions have been moved to services/play_by_play_service.py and services/quarter_score_service.py
