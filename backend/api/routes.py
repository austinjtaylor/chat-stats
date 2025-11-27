"""
API routes for sports statistics endpoints.
"""

from config import config
from data.cache import get_cache, cache_key_for_endpoint
from fastapi import APIRouter, Depends, HTTPException
from models.api import (
    PlayerSearchResponse,
    QueryRequest,
    QueryResponse,
    StatsResponse,
    TeamSearchResponse,
)
from models.user import UpdateUserPreferences
from auth import get_current_user
from services.subscription_service import get_subscription_service
from services.user_profile_service import get_user_profile_service


def create_basic_routes(stats_system):
    """Create basic API routes."""
    router = APIRouter()

    @router.get("/health")
    async def health_check():
        """Health check endpoint for Railway and monitoring"""
        return {"status": "healthy", "service": "chat-stats"}

    @router.get("/api")
    async def api_root():
        """API root endpoint"""
        return {"message": "Sports Statistics Chat System API", "version": "1.0.0"}

    @router.post("/api/query", response_model=QueryResponse)
    async def query_stats(
        request: QueryRequest,
        user: dict = Depends(get_current_user),
    ):
        """
        Process a sports statistics query and return response with data.

        Requires authentication. Query counts against user's monthly quota.
        """
        try:
            user_id = user["user_id"]

            # Get subscription service and check query limit
            subscription_service = get_subscription_service(stats_system.db)
            subscription_service.check_query_limit(user_id)

            # Create session if not provided
            session_id = request.session_id
            if not session_id:
                session_id = stats_system.session_manager.create_session()

            # Process query using stats system
            answer, data = stats_system.query(request.query, session_id)

            # Increment query count only after successful query
            subscription_service.increment_query_count(user_id)

            return QueryResponse(answer=answer, data=data, session_id=session_id)
        except HTTPException:
            # Re-raise HTTP exceptions (like 401, 429) without wrapping
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/subscription/status")
    async def get_subscription_status(user: dict = Depends(get_current_user)):
        """
        Get current user's subscription status and query usage.

        Requires authentication.
        """
        try:
            user_id = user["user_id"]
            subscription_service = get_subscription_service(stats_system.db)
            subscription = subscription_service.get_user_subscription(user_id)

            if not subscription:
                # Return default free tier if no subscription found
                return {
                    "tier": "free",
                    "status": "active",
                    "queries_this_month": 0,
                    "query_limit": 5,
                    "at_query_limit": False,
                }

            return {
                "tier": subscription.tier,
                "status": subscription.status,
                "queries_this_month": subscription.queries_this_month,
                "query_limit": subscription.query_limit,
                "current_period_end": (
                    subscription.current_period_end.isoformat()
                    if subscription.current_period_end
                    else None
                ),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "at_query_limit": subscription.at_query_limit,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.get("/api/user/profile")
    async def get_user_profile(user: dict = Depends(get_current_user)):
        """
        Get current user's profile preferences.

        Requires authentication.
        """
        try:
            user_id = user["user_id"]
            profile_service = get_user_profile_service(stats_system.db)
            preferences = profile_service.get_user_preferences(user_id)

            if not preferences:
                # Return default preferences if none found
                return {
                    "full_name": None,
                    "theme": "light",
                    "default_season": None,
                    "notifications_enabled": True,
                    "email_digest_frequency": "weekly",
                    "favorite_stat_categories": [],
                }

            return preferences.dict()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.patch("/api/user/profile")
    async def update_user_profile(
        updates: UpdateUserPreferences, user: dict = Depends(get_current_user)
    ):
        """
        Update current user's profile preferences.

        Requires authentication.
        """
        try:
            user_id = user["user_id"]
            profile_service = get_user_profile_service(stats_system.db)
            updated_preferences = profile_service.update_user_preferences(
                user_id, updates
            )
            return updated_preferences.dict()
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    @router.delete("/api/user/account")
    async def delete_user_account(user: dict = Depends(get_current_user)):
        """
        Delete current user's account permanently.

        This will:
        1. Cancel any active Stripe subscription
        2. Delete user from Supabase Auth
        3. Cascade delete all user data (subscriptions, queries, favorites, preferences)

        Requires authentication.
        """
        try:
            from supabase_client import supabase_admin
            from services.stripe_service import get_stripe_service
            import logging

            logger = logging.getLogger(__name__)
            user_id = user["user_id"]

            # Get user's subscription to check for Stripe customer
            subscription_service = get_subscription_service(stats_system.db)
            subscription = subscription_service.get_user_subscription(user_id)

            # Cancel Stripe subscription if exists
            if subscription and subscription.stripe_customer_id:
                try:
                    stripe_service = get_stripe_service(stats_system.db)
                    # Cancel subscription immediately (not at period end)
                    stripe_service.cancel_subscription_immediately(
                        subscription.stripe_customer_id
                    )
                    logger.info(f"Canceled Stripe subscription for user {user_id}")
                except Exception as e:
                    logger.error(f"Failed to cancel Stripe subscription: {e}")
                    # Continue with account deletion even if Stripe cancellation fails

            # Delete user from Supabase Auth (this will cascade delete all user data via database triggers)
            try:
                response = supabase_admin.auth.admin.delete_user(user_id)
                logger.info(f"Deleted user {user_id} from Supabase Auth")
            except Exception as e:
                logger.error(f"Failed to delete user from Supabase: {e}")
                raise HTTPException(
                    status_code=500, detail=f"Failed to delete user account: {str(e)}"
                )

            return {"message": "Account successfully deleted"}
        except HTTPException:
            raise
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
                  AND LOWER(t.team_id) NOT LIKE '%allstar%'
                  AND LOWER(t.name) NOT LIKE '%all%star%'
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
                  AND LOWER(t.team_id) NOT LIKE '%allstar%'
                  AND LOWER(t.name) NOT LIKE '%all%star%'
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
    async def clear_cache(user: dict = Depends(get_current_user)):
        """Clear all cached entries (requires authentication)"""
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
    async def import_data(
        file_path: str,
        data_type: str = "json",
        user: dict = Depends(get_current_user),
    ):
        """Import sports data from file (requires authentication)"""
        try:
            import os

            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=404, detail=f"File not found: {file_path}"
                )

            result = stats_system.import_data(file_path, data_type)
            return {"status": "success", "imported": result}
        except HTTPException:
            raise
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
            # Check cache first
            cache = get_cache()
            cache_key = cache_key_for_endpoint(
                "team_stats",
                season=season,
                view=view,
                perspective=perspective,
                sort=sort,
                order=order,
            )

            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            teams = stats_system.get_comprehensive_team_stats(
                season, view, perspective, sort, order
            )

            result = {
                "teams": teams,
                "total": len(teams),
                "season": season,
                "view": view,
                "perspective": perspective,
            }

            # Cache the result with longer TTL since team stats don't change frequently
            cache.set(cache_key, result, ttl=3600)  # 1 hour TTL (was 5 minutes)

            return result

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
