"""
User and subscription data models for API requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    """User profile information."""

    user_id: str
    email: EmailStr
    created_at: datetime


class UserPreferences(BaseModel):
    """User preferences and settings."""

    theme: str = "light"  # 'light', 'dark', 'auto'
    default_season: Optional[int] = None
    notifications_enabled: bool = True
    email_digest_frequency: str = "weekly"  # 'daily', 'weekly', 'monthly', 'never'
    favorite_stat_categories: list[str] = Field(default_factory=list)


class UpdateUserPreferences(BaseModel):
    """Request model for updating user preferences."""

    theme: Optional[str] = None
    default_season: Optional[int] = None
    notifications_enabled: Optional[bool] = None
    email_digest_frequency: Optional[str] = None
    favorite_stat_categories: Optional[list[str]] = None


class SavedQuery(BaseModel):
    """Saved query/conversation."""

    id: int
    query: str
    response: str
    session_id: Optional[str] = None
    is_favorite: bool = False
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class CreateSavedQuery(BaseModel):
    """Request model for saving a query."""

    query: str
    response: str
    session_id: Optional[str] = None
    is_favorite: bool = False
    tags: list[str] = Field(default_factory=list)


class FavoritePlayer(BaseModel):
    """Favorite player."""

    id: int
    player_id: str
    notes: Optional[str] = None
    created_at: datetime


class AddFavoritePlayer(BaseModel):
    """Request model for adding favorite player."""

    player_id: str
    notes: Optional[str] = None


class FavoriteTeam(BaseModel):
    """Favorite team."""

    id: int
    team_id: str
    notes: Optional[str] = None
    created_at: datetime


class AddFavoriteTeam(BaseModel):
    """Request model for adding favorite team."""

    team_id: str
    notes: Optional[str] = None
