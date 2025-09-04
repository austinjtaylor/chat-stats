import warnings

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

import os
from typing import Any

from config import config
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from stats_chat_system import get_stats_system

# Initialize FastAPI app
app = FastAPI(title="Sports Statistics Chat System", root_path="")

# Add trusted host middleware for proxy
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Enable CORS with proper settings for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize Stats Chat System
stats_system = get_stats_system(config)


# Pydantic models for request/response
class QueryRequest(BaseModel):
    """Request model for sports statistics queries"""

    query: str
    session_id: str | None = None


class DataPoint(BaseModel):
    """Model for statistical data points"""

    label: str
    value: Any
    context: str | None = None


class QueryResponse(BaseModel):
    """Response model for sports statistics queries"""

    answer: str
    data: list[dict[str, Any]]
    session_id: str


class StatsResponse(BaseModel):
    """Response model for sports statistics summary"""

    total_players: int
    total_teams: int
    total_games: int
    seasons: list[str]
    team_standings: list[dict[str, Any]]


class PlayerSearchResponse(BaseModel):
    """Response model for player search"""

    players: list[dict[str, Any]]
    count: int


class TeamSearchResponse(BaseModel):
    """Response model for team search"""

    teams: list[dict[str, Any]]
    count: int


# API Endpoints


@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {"message": "Sports Statistics Chat System API", "version": "1.0.0"}


@app.post("/api/query", response_model=QueryResponse)
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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
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
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/players/search", response_model=PlayerSearchResponse)
async def search_players(q: str):
    """Search for players by name"""
    try:
        players = stats_system.search_player(q)
        return PlayerSearchResponse(players=players, count=len(players))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teams/search", response_model=TeamSearchResponse)
async def search_teams(q: str):
    """Search for teams by name or abbreviation"""
    try:
        teams = stats_system.search_team(q)
        return TeamSearchResponse(teams=teams, count=len(teams))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/games/recent")
async def get_recent_games(limit: int = 10):
    """Get recent games"""
    try:
        games = stats_system.get_recent_games(limit)
        return {"games": games, "count": len(games)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/database/info")
async def get_database_info():
    """Get database schema information"""
    try:
        info = stats_system.get_database_info()
        return {"tables": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/data/import")
async def import_data(file_path: str, data_type: str = "json"):
    """Import sports data from file"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        result = stats_system.import_data(file_path, data_type)
        return {"status": "success", "imported": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_sort_column(sort_key, is_career=False):
    """Map sort keys to actual database columns with proper table prefixes"""
    
    if is_career:
        # For career stats, use column aliases directly since they're aggregated
        career_columns = {
            'full_name': 'full_name',
            'total_goals': 'total_goals',
            'total_assists': 'total_assists',
            'total_blocks': 'total_blocks',
            'calculated_plus_minus': 'calculated_plus_minus',
            'completion_percentage': 'completion_percentage',
            'total_completions': 'total_completions',
            'total_yards_thrown': 'total_yards_thrown',
            'total_yards_received': 'total_yards_received',
            'total_hockey_assists': 'total_hockey_assists',
            'total_throwaways': 'total_throwaways',
            'total_stalls': 'total_stalls',
            'total_drops': 'total_drops',
            'total_callahans': 'total_callahans',
            'total_hucks_completed': 'total_hucks_completed',
            'total_hucks_attempted': 'total_hucks_attempted',
            'total_pulls': 'total_pulls',
            'total_o_points_played': 'total_o_points_played',
            'total_d_points_played': 'total_d_points_played',
            'total_seconds_played': 'total_seconds_played',
            'games_played': 'games_played',
            'possessions': 'possessions',
            'score_total': 'score_total',
            'total_points_played': 'total_points_played',
            'total_yards': 'total_yards',
            'minutes_played': 'minutes_played',
            'huck_percentage': 'huck_percentage',
            'offensive_efficiency': 'offensive_efficiency'
        }
        return career_columns.get(sort_key, sort_key)
    
    # For single season stats, use table prefixes
    column_mapping = {
        'full_name': 'p.full_name',
        'total_goals': 'pss.total_goals',
        'total_assists': 'pss.total_assists',
        'total_blocks': 'pss.total_blocks',
        'calculated_plus_minus': 'pss.calculated_plus_minus',
        'completion_percentage': 'pss.completion_percentage',
        'total_completions': 'pss.total_completions',
        'total_yards_thrown': 'pss.total_yards_thrown',
        'total_yards_received': 'pss.total_yards_received',
        'total_hockey_assists': 'pss.total_hockey_assists',
        'total_throwaways': 'pss.total_throwaways',
        'total_stalls': 'pss.total_stalls',
        'total_drops': 'pss.total_drops',
        'total_callahans': 'pss.total_callahans',
        'total_hucks_completed': 'pss.total_hucks_completed',
        'total_hucks_attempted': 'pss.total_hucks_attempted',
        'total_pulls': 'pss.total_pulls',
        'total_o_points_played': 'pss.total_o_points_played',
        'total_d_points_played': 'pss.total_d_points_played',
        'total_seconds_played': 'pss.total_seconds_played',
        'games_played': 'COUNT(DISTINCT CASE WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0) THEN pgs.game_id ELSE NULL END)',
        'possessions': 'pss.total_o_opportunities',
        'score_total': '(pss.total_goals + pss.total_assists)',
        'total_points_played': '(pss.total_o_points_played + pss.total_d_points_played)',
        'total_yards': '(pss.total_yards_thrown + pss.total_yards_received)',
        'minutes_played': 'ROUND(pss.total_seconds_played / 60.0, 0)',
        'huck_percentage': 'CASE WHEN pss.total_hucks_attempted > 0 THEN ROUND(pss.total_hucks_completed * 100.0 / pss.total_hucks_attempted, 1) ELSE 0 END',
        'offensive_efficiency': 'CASE WHEN pss.total_o_opportunities >= 20 THEN ROUND(pss.total_o_opportunity_scores * 100.0 / pss.total_o_opportunities, 1) ELSE NULL END'
    }
    return column_mapping.get(sort_key, f'pss.{sort_key}')


@app.get("/api/players/stats")
async def get_player_stats(
    season: str = "2025",
    team: str = "all", 
    page: int = 1,
    per_page: int = 20,
    sort: str = "calculated_plus_minus",
    order: str = "desc"
):
    """Get paginated player statistics with filtering and sorting"""
    try:
        # Query for player season stats directly from database
        team_filter = f" AND pss.team_id = '{team}'" if team != "all" else ""
        season_filter = f" AND pss.year = {season}" if season != "career" else ""
        
        if season == "career":
            # Career stats - aggregate across all years
            query = f"""
            SELECT 
                p.full_name,
                p.first_name,
                p.last_name,
                p.team_id,
                p.max_year as year,
                SUM(pss.total_goals) as total_goals,
                SUM(pss.total_assists) as total_assists,
                SUM(pss.total_hockey_assists) as total_hockey_assists,
                SUM(pss.total_blocks) as total_blocks,
                (SUM(pss.total_goals) + SUM(pss.total_assists) + SUM(pss.total_blocks) - 
                 SUM(pss.total_throwaways) - SUM(pss.total_drops)) as calculated_plus_minus,
                SUM(pss.total_completions) as total_completions,
                CASE 
                    WHEN SUM(pss.total_throw_attempts) > 0 
                    THEN ROUND(SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts), 1)
                    ELSE 0 
                END as completion_percentage,
                SUM(pss.total_yards_thrown) as total_yards_thrown,
                SUM(pss.total_yards_received) as total_yards_received,
                SUM(pss.total_throwaways) as total_throwaways,
                SUM(pss.total_stalls) as total_stalls,
                SUM(pss.total_drops) as total_drops,
                SUM(pss.total_callahans) as total_callahans,
                SUM(pss.total_hucks_completed) as total_hucks_completed,
                SUM(pss.total_hucks_attempted) as total_hucks_attempted,
                SUM(pss.total_pulls) as total_pulls,
                SUM(pss.total_o_points_played) as total_o_points_played,
                SUM(pss.total_d_points_played) as total_d_points_played,
                SUM(pss.total_seconds_played) as total_seconds_played,
                SUM(pss.total_o_opportunities) as total_o_opportunities,
                SUM(pss.total_d_opportunities) as total_d_opportunities,
                SUM(pss.total_o_opportunity_scores) as total_o_opportunity_scores,
                MAX(t.name) as team_name,
                MAX(t.full_name) as team_full_name,
                (SELECT COUNT(DISTINCT pgs_sub.game_id) 
                 FROM player_game_stats pgs_sub 
                 JOIN games g_sub ON pgs_sub.game_id = g_sub.game_id
                 WHERE pgs_sub.player_id = pss.player_id 
                 AND (pgs_sub.o_points_played > 0 OR pgs_sub.d_points_played > 0 OR pgs_sub.seconds_played > 0 OR pgs_sub.goals > 0 OR pgs_sub.assists > 0)
                 AND pgs_sub.team_id NOT IN ('allstars1', 'allstars2')
                 AND (g_sub.home_team_id NOT IN ('allstars1', 'allstars2') AND g_sub.away_team_id NOT IN ('allstars1', 'allstars2'))
                ) as games_played,
                SUM(pss.total_o_opportunities) as possessions,
                (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
                (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
                (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
                ROUND(SUM(pss.total_seconds_played) / 60.0, 0) as minutes_played,
                CASE 
                    WHEN SUM(pss.total_hucks_attempted) > 0 
                    THEN ROUND(SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted), 1) 
                    ELSE 0 
                END as huck_percentage,
                CASE 
                    WHEN SUM(pss.total_o_opportunities) >= 20 
                    THEN ROUND(SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities), 1)
                    ELSE NULL 
                END as offensive_efficiency
            FROM player_season_stats pss
            JOIN (SELECT pss2.player_id,
                         MAX(pss2.year) as max_year,
                         MAX(p.full_name) as full_name,
                         MAX(p.first_name) as first_name,
                         MAX(p.last_name) as last_name,
                         MAX(p.team_id) as team_id
                  FROM player_season_stats pss2
                  JOIN players p ON pss2.player_id = p.player_id AND pss2.year = p.year
                  WHERE pss2.team_id NOT IN ('allstars1', 'allstars2')
                  GROUP BY pss2.player_id) p ON pss.player_id = p.player_id
            LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            WHERE 1=1{team_filter}
            AND pss.team_id NOT IN ('allstars1', 'allstars2')
            GROUP BY pss.player_id
            ORDER BY {get_sort_column(sort, is_career=True)} {order.upper()}
            LIMIT {per_page} OFFSET {(page-1) * per_page}
            """
        else:
            # Single season stats - existing query
            query = f"""
            SELECT 
                p.full_name,
                p.first_name,
                p.last_name,
                p.team_id,
                pss.year,
                pss.total_goals,
                pss.total_assists,
                pss.total_hockey_assists,
                pss.total_blocks,
                pss.calculated_plus_minus,
                pss.total_completions,
                pss.completion_percentage,
                pss.total_yards_thrown,
                pss.total_yards_received,
                pss.total_throwaways,
                pss.total_stalls,
                pss.total_drops,
                pss.total_callahans,
                pss.total_hucks_completed,
                pss.total_hucks_attempted,
                pss.total_pulls,
                pss.total_o_points_played,
                pss.total_d_points_played,
                pss.total_seconds_played,
                pss.total_o_opportunities,
                pss.total_d_opportunities,
                pss.total_o_opportunity_scores,
                t.name as team_name,
                t.full_name as team_full_name,
                COUNT(DISTINCT CASE 
                    WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                    THEN pgs.game_id 
                    ELSE NULL 
                END) as games_played,
                pss.total_o_opportunities as possessions,
                (pss.total_goals + pss.total_assists) as score_total,
                (pss.total_o_points_played + pss.total_d_points_played) as total_points_played,
                (pss.total_yards_thrown + pss.total_yards_received) as total_yards,
                ROUND(pss.total_seconds_played / 60.0, 0) as minutes_played,
                CASE WHEN pss.total_hucks_attempted > 0 THEN ROUND(pss.total_hucks_completed * 100.0 / pss.total_hucks_attempted, 1) ELSE 0 END as huck_percentage,
                CASE 
                    WHEN pss.total_o_opportunities >= 20 
                    THEN ROUND(pss.total_o_opportunity_scores * 100.0 / pss.total_o_opportunities, 1)
                    ELSE NULL 
                END as offensive_efficiency
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
            LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
            LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
            LEFT JOIN games g ON pgs.game_id = g.game_id
            WHERE 1=1{season_filter}{team_filter}
            AND pss.team_id NOT IN ('allstars1', 'allstars2')
            AND (g.home_team_id NOT IN ('allstars1', 'allstars2') AND g.away_team_id NOT IN ('allstars1', 'allstars2'))
            GROUP BY pss.player_id, pss.team_id, pss.year
            ORDER BY {get_sort_column(sort)} {order.upper()}
            LIMIT {per_page} OFFSET {(page-1) * per_page}
            """
        
        # Get total count for pagination
        if season == "career":
            count_query = f"""
            SELECT COUNT(DISTINCT pss.player_id) as total
            FROM player_season_stats pss
            LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
            LEFT JOIN games g ON pgs.game_id = g.game_id
            WHERE 1=1{team_filter}
            AND (g.home_team_id NOT IN ('allstars1', 'allstars2') AND g.away_team_id NOT IN ('allstars1', 'allstars2'))
            """
        else:
            count_query = f"""
            SELECT COUNT(*) as total
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
            LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
            LEFT JOIN games g ON pgs.game_id = g.game_id
            WHERE 1=1{season_filter}{team_filter}
            AND (g.home_team_id NOT IN ('allstars1', 'allstars2') AND g.away_team_id NOT IN ('allstars1', 'allstars2'))
            """
        
        # Execute queries using the stats system database connection
        from sqlalchemy import text
        
        with stats_system.db.engine.connect() as conn:
            # Get total count
            count_result = conn.execute(text(count_query)).fetchone()
            total = count_result[0] if count_result else 0
            
            # Get players
            result = conn.execute(text(query))
            players = []
            
            for row in result:
                player = {
                    'full_name': row[0],
                    'first_name': row[1], 
                    'last_name': row[2],
                    'team_id': row[3],
                    'year': row[4],
                    'total_goals': row[5] or 0,
                    'total_assists': row[6] or 0,
                    'total_hockey_assists': row[7] or 0,
                    'total_blocks': row[8] or 0,
                    'calculated_plus_minus': row[9] or 0,
                    'total_completions': row[10] or 0,
                    'completion_percentage': row[11] or 0,
                    'total_yards_thrown': row[12] or 0,
                    'total_yards_received': row[13] or 0,
                    'total_throwaways': row[14] or 0,
                    'total_stalls': row[15] or 0,
                    'total_drops': row[16] or 0,
                    'total_callahans': row[17] or 0,
                    'total_hucks_completed': row[18] or 0,
                    'total_hucks_attempted': row[19] or 0,
                    'total_pulls': row[20] or 0,
                    'total_o_points_played': row[21] or 0,
                    'total_d_points_played': row[22] or 0,
                    'total_seconds_played': row[23] or 0,
                    'total_o_opportunities': row[24] or 0,
                    'total_d_opportunities': row[25] or 0,
                    'total_o_opportunity_scores': row[26] or 0,
                    'team_name': row[27],
                    'team_full_name': row[28],
                    'games_played': row[29] or 0,
                    'possessions': row[30] or 0,
                    'score_total': row[31] or 0,
                    'total_points_played': row[32] or 0,
                    'total_yards': row[33] or 0,
                    'minutes_played': row[34] or 0,
                    'huck_percentage': row[35] or 0,
                    'offensive_efficiency': row[36] if row[36] is not None else None
                }
                players.append(player)
        
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "players": players,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }
        
    except Exception as e:
        print(f"Error in get_player_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teams/stats") 
async def get_team_stats(season: str = "2025", view: str = "total"):
    """Get team statistics"""
    try:
        summary = stats_system.get_stats_summary()
        teams = summary.get("team_standings", [])
        
        return {
            "teams": teams,
            "total": len(teams),
            "season": season,
            "view": view
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/games/by-date")
async def get_games_by_date(year: str = "all", team: str = "all"):
    """Get games grouped by date"""
    try:
        games = stats_system.get_recent_games(100)  # Get more games
        
        # Filter by year if specified
        if year != "all":
            games = [g for g in games if g.get("year") == int(year)]
            
        # Filter by team if specified  
        if team != "all":
            games = [g for g in games if 
                    g.get("home_team_id") == team or 
                    g.get("away_team_id") == team]
        
        # Group by date
        from collections import defaultdict
        from datetime import datetime
        
        grouped_games = defaultdict(list)
        
        for game in games:
            try:
                # Parse the date from start_timestamp
                if game.get("start_timestamp"):
                    date_obj = datetime.fromisoformat(game["start_timestamp"].replace("Z", "+00:00"))
                    date_key = date_obj.strftime("%A, %B %d, %Y")
                else:
                    date_key = "Unknown Date"
                
                grouped_games[date_key].append(game)
            except:
                grouped_games["Unknown Date"].append(game)
        
        # Convert to list format expected by frontend
        games_by_date = []
        for date_str, date_games in sorted(grouped_games.items(), reverse=True):
            games_by_date.append({
                "date": date_str,
                "games": date_games
            })
        
        return {
            "games_by_date": games_by_date,
            "total_games": len(games)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/games/{game_id}/details")
async def get_game_details(game_id: str):
    """Get detailed game statistics"""
    try:
        # This would need to be implemented based on your database schema
        # For now, return a placeholder response
        return {
            "game_id": game_id,
            "message": "Game details endpoint - to be implemented with player game stats"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Initialize database and load sample data on startup"""
    print("Starting Sports Statistics Chat System...")

    # Check if sample data exists
    sample_data_path = "../data/sample_stats.json"
    if os.path.exists(sample_data_path):
        try:
            print("Loading sample sports data...")
            result = stats_system.import_data(sample_data_path, "json")
            print(f"Loaded sample data: {result}")
        except Exception as e:
            print(f"Could not load sample data: {e}")

    # Get database info
    info = stats_system.get_database_info()
    print(f"Database initialized with tables: {list(info.keys())}")

    # Get stats summary
    summary = stats_system.get_stats_summary()
    print(
        f"Database contains: {summary['total_players']} players, {summary['total_teams']} teams, {summary['total_games']} games"
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down Sports Statistics Chat System...")
    stats_system.close()


# Custom static file handler with no-cache headers for development

from fastapi.responses import FileResponse


class DevStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            # Add no-cache headers for development
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


# Serve static files for the frontend - MUST be after all route definitions
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/", DevStaticFiles(directory=frontend_path, html=True), name="static")
else:
    print(f"Warning: Frontend directory not found at {frontend_path}")
