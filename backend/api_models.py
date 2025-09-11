"""
Pydantic models for API request and response validation.
"""

from typing import Any
from pydantic import BaseModel


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