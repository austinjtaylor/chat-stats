"""
User and subscription data models for API requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserProfile(BaseModel):
    """User profile information."""

    user_id: str
    email: EmailStr
    created_at: datetime


class UserPreferences(BaseModel):
    """User preferences and settings."""

    full_name: str | None = None
    theme: str = "light"  # 'light', 'dark', 'auto'
    default_season: int | None = None
    notifications_enabled: bool = True
    email_digest_frequency: str = "weekly"  # 'daily', 'weekly', 'monthly', 'never'
    favorite_stat_categories: list[str] = Field(default_factory=list)


class UpdateUserPreferences(BaseModel):
    """Request model for updating user preferences."""

    full_name: str | None = None
    theme: str | None = None
    default_season: int | None = None
    notifications_enabled: bool | None = None
    email_digest_frequency: str | None = None
    favorite_stat_categories: list[str] | None = None


class SavedQuery(BaseModel):
    """Saved query/conversation."""

    id: int
    query: str
    response: str
    session_id: str | None = None
    is_favorite: bool = False
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class CreateSavedQuery(BaseModel):
    """Request model for saving a query."""

    query: str
    response: str
    session_id: str | None = None
    is_favorite: bool = False
    tags: list[str] = Field(default_factory=list)


class FavoritePlayer(BaseModel):
    """Favorite player."""

    id: int
    player_id: str
    notes: str | None = None
    created_at: datetime


class AddFavoritePlayer(BaseModel):
    """Request model for adding favorite player."""

    player_id: str
    notes: str | None = None


class FavoriteTeam(BaseModel):
    """Favorite team."""

    id: int
    team_id: str
    notes: str | None = None
    created_at: datetime


class AddFavoriteTeam(BaseModel):
    """Request model for adding favorite team."""

    team_id: str
    notes: str | None = None
