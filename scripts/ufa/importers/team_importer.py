#!/usr/bin/env python3
"""
Team importer for UFA data.
"""

from typing import Any

from .base_importer import BaseImporter


class TeamImporter(BaseImporter):
    """Handles importing team data from UFA API"""

    def import_teams(
        self, teams_data: list[dict[str, Any]], years: list[int] = None
    ) -> int:
        """
        Import teams from API data using batch insert

        Args:
            teams_data: List of team dictionaries from API
            years: List of years being imported (unused, kept for consistency)

        Returns:
            Number of teams imported
        """
        teams_batch = []
        for team in teams_data:
            team_data = {
                "team_id": team.get("teamID", ""),
                "year": team.get("year", 2025),
                "city": team.get("city", ""),
                "name": team.get("name", ""),
                "full_name": team.get("name", ""),
                "abbrev": team.get("abbrev", team.get("teamID", "")),
                "wins": team.get("wins", 0),
                "losses": team.get("losses", 0),
                "ties": team.get("ties", 0),
                "standing": team.get("standing", 0),
                "division_id": team.get("divisionID", ""),
                "division_name": team.get("divisionName", ""),
            }
            teams_batch.append(team_data)

        # Batch insert all teams at once
        count = self.batch_insert(
            table="teams",
            columns=[
                "team_id",
                "year",
                "city",
                "name",
                "full_name",
                "abbrev",
                "wins",
                "losses",
                "ties",
                "standing",
                "division_id",
                "division_name",
            ],
            data=teams_batch,
        )

        self.logger.info(f"  Imported {count} team records")
        return count
