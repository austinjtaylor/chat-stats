"""
API routes for sports statistics endpoints.
"""

from config import config
from fastapi import APIRouter, HTTPException
from models.api import (
    PlayerSearchResponse,
    QueryRequest,
    QueryResponse,
    StatsResponse,
    TeamSearchResponse,
)

from data.cache import get_cache


def create_basic_routes(stats_system):
    """Create basic API routes."""
    router = APIRouter()

    @router.get("/api")
    async def api_root():
        """API root endpoint"""
        return {"message": "Sports Statistics Chat System API", "version": "1.0.0"}

    @router.post("/api/query", response_model=QueryResponse)
    async def query_stats(request: QueryRequest):
        """Process a sports statistics query and return response with data"""
        try:
            # Create session if not provided
            session_id = request.session_id
            if not session_id:
                session_id = stats_system.session_manager.create_session()

            # Process query using stats system
            answer, data = stats_system.query(request.query, session_id)

            return QueryResponse(answer=answer, data=data, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/stats", response_model=StatsResponse)
    async def get_stats_summary():
        """Get sports statistics summary"""
        try:
            summary = stats_system.get_stats_summary()
            return StatsResponse(
                total_players=summary["total_players"],
                total_teams=summary["total_teams"],
                total_games=summary["total_games"],
                seasons=summary["seasons"],
                team_standings=summary["team_standings"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/players/search", response_model=PlayerSearchResponse)
    async def search_players(q: str):
        """Search for players by name"""
        try:
            players = stats_system.search_player(q)
            return PlayerSearchResponse(players=players, count=len(players))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/teams")
    async def get_all_teams(year: int | None = None):
        """Get all teams for dropdowns, optionally filtered by year"""
        try:
            if year:
                query = """
                SELECT DISTINCT
                    t.team_id as id,
                    t.team_id,
                    t.name,
                    t.city,
                    t.full_name,
                    t.year
                FROM teams t
                WHERE t.year = :year
                ORDER BY t.full_name
                """
                teams = stats_system.db.execute_query(query, {"year": year})
            else:
                query = """
                SELECT DISTINCT
                    t.team_id as id,
                    t.team_id,
                    t.name,
                    t.city,
                    t.full_name,
                    t.year
                FROM teams t
                WHERE t.year = (SELECT MAX(year) FROM teams)
                ORDER BY t.full_name
                """
                teams = stats_system.db.execute_query(query)
            return teams
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/teams/search", response_model=TeamSearchResponse)
    async def search_teams(q: str):
        """Search for teams by name or abbreviation"""
        try:
            teams = stats_system.search_team(q)
            return TeamSearchResponse(teams=teams, count=len(teams))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/cache/stats")
    async def get_cache_stats():
        """Get cache statistics including hit rate and memory usage"""
        cache = get_cache()
        stats = cache.get_stats()

        # Add cache configuration
        stats["enabled"] = config.ENABLE_CACHE
        stats["default_ttl"] = config.CACHE_TTL

        return stats

    @router.post("/api/cache/clear")
    async def clear_cache():
        """Clear all cached entries"""
        if not config.ENABLE_CACHE:
            return {"message": "Cache is disabled"}

        cache = get_cache()
        cache.clear()
        return {"message": "Cache cleared successfully"}

    @router.get("/api/games/recent")
    async def get_recent_games(limit: int = 10):
        """Get recent games"""
        try:
            games = stats_system.get_recent_games(limit)
            return {"games": games, "count": len(games)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/database/info")
    async def get_database_info():
        """Get database schema information"""
        try:
            info = stats_system.get_database_info()
            return {"tables": info}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.post("/api/data/import")
    async def import_data(file_path: str, data_type: str = "json"):
        """Import sports data from file"""
        try:
            import os

            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404, detail=f"File not found: {file_path}"
                )

            result = stats_system.import_data(file_path, data_type)
            return {"status": "success", "imported": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/teams/stats")
    async def get_team_stats(
        season: str = "2025",
        view: str = "total",
        perspective: str = "team",
        sort: str = "wins",
        order: str = "desc",
    ):
        """Get comprehensive team statistics with all UFA-style columns"""
        try:
            teams = stats_system.get_comprehensive_team_stats(
                season, view, perspective, sort, order
            )
            return {
                "teams": teams,
                "total": len(teams),
                "season": season,
                "view": view,
                "perspective": perspective,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/games/by-date")
    async def get_games_by_date(year: str = "all", team: str = "all"):
        """Get games grouped by date"""
        try:
            games = stats_system.get_recent_games(100)  # Get more games

            # Filter by year if specified
            if year != "all":
                games = [g for g in games if g.get("year") == int(year)]

            # Filter by team if specified
            if team != "all":
                games = [
                    g
                    for g in games
                    if g.get("home_team_id") == team or g.get("away_team_id") == team
                ]

            # Group by date
            from collections import defaultdict
            from datetime import datetime

            grouped_games = defaultdict(list)

            for game in games:
                try:
                    # Parse the date from start_timestamp
                    if game.get("start_timestamp"):
                        date_obj = datetime.fromisoformat(
                            game["start_timestamp"].replace("Z", "+00:00")
                        )
                        date_key = date_obj.strftime("%A, %B %d, %Y")
                    else:
                        date_key = "Unknown Date"

                    grouped_games[date_key].append(game)
                except:
                    grouped_games["Unknown Date"].append(game)

            # Convert to list format expected by frontend
            games_by_date = []
            for date_str, date_games in sorted(grouped_games.items(), reverse=True):
                games_by_date.append({"date": date_str, "games": date_games})

            return {"games_by_date": games_by_date, "total_games": len(games)}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return (
        router,
        stats_system,
    )  # Return both router and stats_system for player stats endpoint
