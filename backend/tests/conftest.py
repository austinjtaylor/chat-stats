"""
Test fixtures and configuration for the sports statistics system.
Provides common test data, mocks, and utilities for all test modules.
"""

import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any
from fastapi.testclient import TestClient
from datetime import datetime

# Add backend to path so we can import modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sql_database import SQLDatabase
from stats_processor import StatsProcessor
from stats_tools import StatsToolManager
from ai_generator import AIGenerator
from stats_chat_system import StatsChatSystem
from session_manager import SessionManager, Message
from config import Config
from models import Team, Player, Game, PlayerGameStats, PlayerSeasonStats, TeamSeasonStats


# ===== CONFIGURATION FIXTURES =====

@pytest.fixture
def mock_config():
    """Mock configuration with proper test values for sports system"""
    config = Mock(spec=Config)
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
    config.DATABASE_PATH = "./test_sports_stats.db"
    config.MAX_RESULTS = 10
    config.MAX_HISTORY = 5
    config.MAX_TOOL_ROUNDS = 3
    return config


@pytest.fixture
def temp_db_path():
    """Create a temporary database file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        temp_path = tmp.name
    yield temp_path
    if os.path.exists(temp_path):
        os.unlink(temp_path)


# ===== SAMPLE SPORTS DATA FIXTURES =====

@pytest.fixture
def sample_teams():
    """Sample team data for testing"""
    return [
        {
            "team_id": "LAL",
            "name": "Los Angeles Lakers",
            "city": "Los Angeles", 
            "abbreviation": "LAL",
            "division": "Pacific",
            "conference": "Western",
            "year": 2024
        },
        {
            "team_id": "BOS",
            "name": "Boston Celtics",
            "city": "Boston",
            "abbreviation": "BOS",
            "division": "Atlantic", 
            "conference": "Eastern",
            "year": 2024
        },
        {
            "team_id": "GSW",
            "name": "Golden State Warriors",
            "city": "San Francisco",
            "abbreviation": "GSW",
            "division": "Pacific",
            "conference": "Western", 
            "year": 2024
        }
    ]


@pytest.fixture
def sample_players():
    """Sample player data for testing"""
    return [
        {
            "player_id": "lebron-james",
            "name": "LeBron James",
            "first_name": "LeBron",
            "last_name": "James", 
            "team_id": "LAL",
            "position": "Forward",
            "jersey_number": 23,
            "height": 81,  # inches
            "weight": 250,
            "years_pro": 21,
            "year": 2024
        },
        {
            "player_id": "jayson-tatum",
            "name": "Jayson Tatum",
            "first_name": "Jayson",
            "last_name": "Tatum",
            "team_id": "BOS", 
            "position": "Forward",
            "jersey_number": 0,
            "height": 80,
            "weight": 210,
            "years_pro": 7,
            "year": 2024
        },
        {
            "player_id": "stephen-curry",
            "name": "Stephen Curry",
            "first_name": "Stephen",
            "last_name": "Curry",
            "team_id": "GSW",
            "position": "Guard", 
            "jersey_number": 30,
            "height": 74,
            "weight": 185,
            "years_pro": 15,
            "year": 2024
        }
    ]


@pytest.fixture  
def sample_games():
    """Sample game data for testing"""
    return [
        {
            "game_id": "lal-vs-bos-2024-01-15",
            "game_date": "2024-01-15",
            "home_team_id": "LAL",
            "away_team_id": "BOS",
            "home_score": 110,
            "away_score": 105,
            "venue": "Crypto.com Arena",
            "season": "2023-24",
            "game_type": "regular"
        },
        {
            "game_id": "gsw-vs-lal-2024-01-20", 
            "game_date": "2024-01-20",
            "home_team_id": "GSW",
            "away_team_id": "LAL",
            "home_score": 120,
            "away_score": 115,
            "venue": "Chase Center",
            "season": "2023-24",
            "game_type": "regular"
        }
    ]


@pytest.fixture
def sample_player_game_stats():
    """Sample player game statistics"""
    return [
        {
            "game_id": "lal-vs-bos-2024-01-15",
            "player_id": "lebron-james",
            "team_id": "LAL",
            "minutes_played": 36,
            "points": 28,
            "rebounds": 8,
            "assists": 9,
            "steals": 2,
            "blocks": 1,
            "turnovers": 3,
            "field_goals_made": 11,
            "field_goals_attempted": 20,
            "three_pointers_made": 3,
            "three_pointers_attempted": 7,
            "free_throws_made": 3,
            "free_throws_attempted": 4
        },
        {
            "game_id": "lal-vs-bos-2024-01-15",
            "player_id": "jayson-tatum", 
            "team_id": "BOS",
            "minutes_played": 38,
            "points": 32,
            "rebounds": 6,
            "assists": 5,
            "steals": 1,
            "blocks": 2,
            "turnovers": 4,
            "field_goals_made": 12,
            "field_goals_attempted": 22,
            "three_pointers_made": 5,
            "three_pointers_attempted": 10,
            "free_throws_made": 3,
            "free_throws_attempted": 3
        }
    ]


@pytest.fixture
def sample_player_season_stats():
    """Sample player season statistics"""
    return [
        {
            "player_id": "lebron-james",
            "season": "2023-24",
            "team_id": "LAL",
            "games_played": 70,
            "minutes_per_game": 35.2,
            "points_per_game": 25.1,
            "rebounds_per_game": 7.8,
            "assists_per_game": 6.9,
            "steals_per_game": 1.3,
            "blocks_per_game": 0.5,
            "turnovers_per_game": 3.8,
            "field_goal_percentage": 54.0,
            "three_point_percentage": 41.2,
            "free_throw_percentage": 75.0
        },
        {
            "player_id": "jayson-tatum",
            "season": "2023-24", 
            "team_id": "BOS",
            "games_played": 74,
            "minutes_per_game": 36.9,
            "points_per_game": 26.9,
            "rebounds_per_game": 8.1,
            "assists_per_game": 4.9,
            "steals_per_game": 1.0,
            "blocks_per_game": 0.6,
            "turnovers_per_game": 2.9,
            "field_goal_percentage": 47.1,
            "three_point_percentage": 37.6,
            "free_throw_percentage": 83.3
        }
    ]


# ===== UFA DATA FIXTURES =====

@pytest.fixture
def sample_ufa_teams():
    """Sample UFA team data for testing"""
    return [
        {
            "teamID": "ATL",
            "name": "Atlanta Hustle",
            "city": "Atlanta",
            "abbrev": "ATL",
            "wins": 12,
            "losses": 4,
            "standing": 1,
            "division": {
                "divisionID": "south", 
                "name": "South Division"
            }
        },
        {
            "teamID": "BOS",
            "name": "Boston Glory",
            "city": "Boston", 
            "abbrev": "BOS",
            "wins": 10,
            "losses": 6,
            "standing": 2,
            "division": {
                "divisionID": "east",
                "name": "East Division"
            }
        }
    ]


@pytest.fixture
def sample_ufa_players():
    """Sample UFA player data for testing"""
    return [
        {
            "playerID": "player1",
            "firstName": "John",
            "lastName": "Doe",
            "teams": [
                {
                    "teamID": "ATL",
                    "active": True,
                    "year": 2024,
                    "jerseyNumber": 7
                }
            ]
        },
        {
            "playerID": "player2",
            "firstName": "Jane", 
            "lastName": "Smith",
            "teams": [
                {
                    "teamID": "BOS",
                    "active": True,
                    "year": 2024,
                    "jerseyNumber": 23
                }
            ]
        }
    ]


@pytest.fixture
def sample_ufa_games():
    """Sample UFA game data for testing"""
    return [
        {
            "gameID": "atl-vs-bos-2024",
            "homeTeam": "ATL",
            "awayTeam": "BOS",
            "homeScore": 15,
            "awayScore": 12,
            "status": "Final",
            "startTimestamp": "2024-06-15T19:00:00Z",
            "week": "Week 1"
        }
    ]


# ===== MOCK FIXTURES =====

@pytest.fixture
def mock_db():
    """Mock SQLDatabase for testing"""
    mock = Mock(spec=SQLDatabase)
    mock.execute_query.return_value = []
    mock.insert_data.return_value = 1
    return mock


@pytest.fixture
def mock_stats_processor():
    """Mock StatsProcessor for testing"""
    mock = Mock(spec=StatsProcessor)
    mock.import_teams.return_value = 0
    mock.import_players.return_value = 0
    mock.import_game.return_value = None
    mock.import_player_game_stats.return_value = 0
    return mock


@pytest.fixture
def mock_stats_tool_manager():
    """Mock StatsToolManager for testing"""
    mock = Mock(spec=StatsToolManager)
    mock.get_tool_schemas.return_value = [
        {
            "name": "get_player_stats",
            "description": "Get player statistics",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {"type": "string"}
                }
            }
        }
    ]
    mock.get_player_stats.return_value = '[]'
    mock.get_team_stats.return_value = '[]'
    mock.get_game_results.return_value = '[]'
    return mock


@pytest.fixture  
def mock_ai_generator():
    """Mock AIGenerator for testing"""
    mock = Mock(spec=AIGenerator)
    mock.generate_response.return_value = (
        "This is a test response from the AI generator.",
        []
    )
    return mock


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for testing"""
    mock = Mock(spec=SessionManager)
    mock.get_history.return_value = []
    mock.add_message.return_value = None
    return mock


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    mock_client = Mock()
    
    # Mock response for direct text responses
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a test response")]
    mock_response.stop_reason = "end_turn"
    
    mock_client.messages.create.return_value = mock_response
    return mock_client


# ===== MESSAGE AND SESSION FIXTURES =====

@pytest.fixture
def sample_messages():
    """Sample messages for session testing"""
    return [
        {
            "role": "user",
            "content": "What are LeBron James' stats this season?"
        },
        {
            "role": "assistant", 
            "content": "LeBron James is averaging 25.1 points, 7.8 rebounds, and 6.9 assists per game this season."
        },
        {
            "role": "user",
            "content": "How does he compare to Jayson Tatum?"
        }
    ]


@pytest.fixture
def sample_message_objects():
    """Sample Message objects for testing"""
    return [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there!"),
        Message(role="user", content="How are you?")
    ]


# ===== API FIXTURES =====

@pytest.fixture
def test_app():
    """Create a FastAPI test app for sports stats API"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional
    
    # Define API models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class DataPoint(BaseModel):
        label: str
        value: float
        category: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Any]]
        session_id: str

    class StatsResponse(BaseModel):
        total_players: int
        total_teams: int
        total_games: int
        top_scorers: List[DataPoint]
        recent_games: List[Dict[str, Any]]

    class PlayerSearchResponse(BaseModel):
        players: List[Dict[str, Any]]
        count: int

    class TeamSearchResponse(BaseModel):
        teams: List[Dict[str, Any]]
        count: int
    
    # Create test app
    app = FastAPI(title="Sports Statistics API Test")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mock chat system that will be injected during tests
    mock_chat_system = Mock()
    
    @app.post("/api/query", response_model=QueryResponse)
    async def query_stats(request: QueryRequest):
        try:
            session_id = request.session_id or "test-session-123"
            answer, sources = mock_chat_system.query(request.query, session_id)
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/stats", response_model=StatsResponse)
    async def get_stats():
        try:
            stats = mock_chat_system.get_database_stats()
            return StatsResponse(**stats)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/players/search", response_model=PlayerSearchResponse)
    async def search_players(q: str):
        # Mock player search
        return PlayerSearchResponse(players=[], count=0)

    @app.get("/api/teams/search", response_model=TeamSearchResponse) 
    async def search_teams(q: str):
        # Mock team search
        return TeamSearchResponse(teams=[], count=0)
    
    @app.get("/")
    async def read_root():
        return {"message": "Sports Statistics API"}
    
    # Store the mock for easy access in tests
    app.state.mock_chat_system = mock_chat_system
    
    return app


@pytest.fixture
def test_client(test_app):
    """Create a test client for the FastAPI app"""
    return TestClient(test_app)


# ===== RESPONSE FIXTURES =====

@pytest.fixture
def mock_api_responses():
    """Mock API responses for testing"""
    return {
        "query_response": (
            "LeBron James is averaging 25.1 points per game this season.",
            [
                {
                    "source": "player_stats",
                    "data": {"player": "LeBron James", "ppg": 25.1}
                }
            ]
        ),
        "database_stats": {
            "total_players": 500,
            "total_teams": 30,
            "total_games": 1230,
            "top_scorers": [
                {"label": "LeBron James", "value": 25.1, "category": "points"},
                {"label": "Jayson Tatum", "value": 26.9, "category": "points"}
            ],
            "recent_games": [
                {
                    "game_id": "lal-vs-bos-2024-01-15",
                    "home_team": "Lakers",
                    "away_team": "Celtics",
                    "home_score": 110,
                    "away_score": 105
                }
            ]
        }
    }


# ===== UTILITY FIXTURES =====

@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def current_season():
    """Current season for testing"""
    return "2023-24"


@pytest.fixture
def current_year():
    """Current year for testing"""
    return 2024