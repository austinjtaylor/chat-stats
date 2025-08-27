import warnings

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os

from config import config
from stats_chat_system import StatsChatSystem, get_stats_system

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
    session_id: Optional[str] = None


class DataPoint(BaseModel):
    """Model for statistical data points"""

    label: str
    value: Any
    context: Optional[str] = None


class QueryResponse(BaseModel):
    """Response model for sports statistics queries"""

    answer: str
    data: List[Dict[str, Any]]
    session_id: str


class StatsResponse(BaseModel):
    """Response model for sports statistics summary"""

    total_players: int
    total_teams: int
    total_games: int
    seasons: List[str]
    team_standings: List[Dict[str, Any]]


class PlayerSearchResponse(BaseModel):
    """Response model for player search"""
    
    players: List[Dict[str, Any]]
    count: int


class TeamSearchResponse(BaseModel):
    """Response model for team search"""
    
    teams: List[Dict[str, Any]]
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
            team_standings=summary["team_standings"]
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
    print(f"Database contains: {summary['total_players']} players, {summary['total_teams']} teams, {summary['total_games']} games")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down Sports Statistics Chat System...")
    stats_system.close()


# Custom static file handler with no-cache headers for development
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path


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