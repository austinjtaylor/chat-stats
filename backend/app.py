import warnings

warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

import os

from api.game import create_game_routes
from api.game_box_score import create_box_score_routes
from api.player_stats import create_player_stats_route

# Import route modules
from api.routes import create_basic_routes
from config import config
from core.chat_system import get_stats_system
from fastapi import FastAPI
from middleware import DevStaticFiles, configure_cors, configure_trusted_host

# Initialize FastAPI app
app = FastAPI(title="Sports Statistics Chat System", root_path="")

# Configure middleware
configure_trusted_host(app)
configure_cors(app)

# Initialize Stats Chat System
stats_system = get_stats_system(config)

# Register route modules
basic_router, _ = create_basic_routes(stats_system)
player_stats_router = create_player_stats_route(stats_system)
game_router = create_game_routes(stats_system)
box_score_router = create_box_score_routes(stats_system)

# Include all routers
app.include_router(basic_router)
app.include_router(player_stats_router)
app.include_router(game_router)
app.include_router(box_score_router)


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


# Serve static files for the frontend - MUST be after all route definitions
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    # Mount components directory first for header access
    components_path = os.path.join(frontend_path, "components")
    if os.path.exists(components_path):
        app.mount("/components", DevStaticFiles(directory=components_path), name="components")
    
    # Mount stats directory
    stats_path = os.path.join(frontend_path, "stats")
    if os.path.exists(stats_path):
        app.mount("/stats", DevStaticFiles(directory=stats_path, html=True), name="stats")
    
    # Mount main frontend last (catch-all)
    app.mount("/", DevStaticFiles(directory=frontend_path, html=True), name="static")
else:
    print(f"Warning: Frontend directory not found at {frontend_path}")
