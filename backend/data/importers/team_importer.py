"""
Team data importer.
"""

from typing import Any

from models.db import Team


class TeamImporter:
    """Handles team data import operations."""

    def __init__(self, db):
        """
        Initialize the team importer.

        Args:
            db: Database instance
        """
        self.db = db

    def import_teams(self, teams_data: list[dict[str, Any]]) -> int:
        """
        Import team data into the database.

        Args:
            teams_data: List of team dictionaries

        Returns:
            Number of teams imported
        """
        count = 0
        for team_dict in teams_data:
            try:
                # Skip None values
                if not team_dict:
                    continue

                # Check if team already exists
                existing = self.db.execute_query(
                    "SELECT id FROM teams WHERE name = :name",
                    {"name": team_dict.get("name")},
                )

                if not existing:
                    team = Team(**team_dict)
                    team_data = team.dict(exclude_none=True, exclude={"id"})
                    self.db.insert_data("teams", team_data)
                    count += 1
            except Exception as e:
                # Log error and continue with next team
                print(f"Error importing team {team_dict}: {e}")
                continue

        return count
