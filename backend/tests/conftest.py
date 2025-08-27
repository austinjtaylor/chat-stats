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