"""
User profile management service.
Handles user preferences and profile updates.
"""

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import text

from data.database import SQLDatabase
from models.user import UserPreferences, UpdateUserPreferences


class UserProfileService:
    """Service for managing user profiles and preferences."""

    def __init__(self, db: SQLDatabase):
        """Initialize user profile service."""
        self.db = db

    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """
        Get a user's preferences.

        Args:
            user_id: User's UUID

        Returns:
            UserPreferences or None if not found
        """
        query = """
        SELECT
            full_name,
            theme,
            default_season,
            notifications_enabled,
            email_digest_frequency,
            favorite_stat_categories
        FROM user_preferences
        WHERE user_id = :user_id
        """

        results = self.db.execute_query(query, {"user_id": user_id})

        if not results:
            return None

        prefs = results[0]
        return UserPreferences(
            full_name=prefs.get("full_name"),
            theme=prefs.get("theme") or "light",
            default_season=prefs.get("default_season"),
            notifications_enabled=(
                prefs.get("notifications_enabled")
                if prefs.get("notifications_enabled") is not None
                else True
            ),
            email_digest_frequency=prefs.get("email_digest_frequency") or "weekly",
            favorite_stat_categories=prefs.get("favorite_stat_categories") or [],
        )

    def update_user_preferences(
        self, user_id: str, updates: UpdateUserPreferences
    ) -> UserPreferences:
        """
        Update a user's preferences.

        Args:
            user_id: User's UUID
            updates: Fields to update

        Returns:
            Updated UserPreferences

        Raises:
            HTTPException: If preferences not found
        """
        # Build update query dynamically based on provided fields
        update_fields = []
        params = {"user_id": user_id}

        if updates.full_name is not None:
            update_fields.append("full_name = :full_name")
            params["full_name"] = updates.full_name

        if updates.theme is not None:
            update_fields.append("theme = :theme")
            params["theme"] = updates.theme

        if updates.default_season is not None:
            update_fields.append("default_season = :default_season")
            params["default_season"] = updates.default_season

        if updates.notifications_enabled is not None:
            update_fields.append("notifications_enabled = :notifications_enabled")
            params["notifications_enabled"] = updates.notifications_enabled

        if updates.email_digest_frequency is not None:
            update_fields.append("email_digest_frequency = :email_digest_frequency")
            params["email_digest_frequency"] = updates.email_digest_frequency

        if updates.favorite_stat_categories is not None:
            update_fields.append("favorite_stat_categories = :favorite_stat_categories")
            params["favorite_stat_categories"] = updates.favorite_stat_categories

        if not update_fields:
            # No fields to update, just return current preferences
            prefs = self.get_user_preferences(user_id)
            if not prefs:
                raise HTTPException(
                    status_code=404, detail="User preferences not found"
                )
            return prefs

        # Execute update
        query = f"""
        UPDATE user_preferences
        SET {', '.join(update_fields)}, updated_at = NOW()
        WHERE user_id = :user_id
        """

        self.db.execute_query(query, params)

        # Return updated preferences
        prefs = self.get_user_preferences(user_id)
        if not prefs:
            raise HTTPException(status_code=404, detail="User preferences not found")

        return prefs


# Singleton instance
_user_profile_service: Optional[UserProfileService] = None


def get_user_profile_service(db: SQLDatabase) -> UserProfileService:
    """Get or create user profile service singleton."""
    global _user_profile_service
    if _user_profile_service is None:
        _user_profile_service = UserProfileService(db)
    return _user_profile_service
