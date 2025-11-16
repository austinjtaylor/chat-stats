"""
Parameter parsing utilities for player stats API.
"""

import json


class ParamParser:
    """Parses and validates API parameters for player stats endpoint."""

    @staticmethod
    def parse_seasons(season: str):
        """
        Parse season parameter into list of seasons and career mode flag.

        Args:
            season: Season string (e.g., "career", "2024", "2023,2024")

        Returns:
            Tuple of (seasons_list, is_career_mode)
        """
        is_career_mode = season == "career"

        if is_career_mode:
            return ["career"], True

        # Parse comma-separated seasons
        seasons = [s.strip() for s in season.split(",") if s.strip()]
        if not seasons:
            return ["career"], True

        return seasons, False

    @staticmethod
    def parse_teams(team: str):
        """
        Parse team parameter into list of team IDs.

        Args:
            team: Team string (e.g., "all", "ATL", "ATL,DAL")

        Returns:
            List of team IDs
        """
        if team == "all":
            return ["all"]

        # Parse comma-separated teams
        teams = [t.strip() for t in team.split(",") if t.strip()]
        if not teams:
            return ["all"]

        return teams

    @staticmethod
    def parse_custom_filters(custom_filters: str | None):
        """
        Parse custom filters JSON string.

        Args:
            custom_filters: JSON string of filters

        Returns:
            List of filter dicts or empty list
        """
        if not custom_filters:
            return []

        try:
            return json.loads(custom_filters)
        except json.JSONDecodeError:
            return []

    @staticmethod
    def build_team_filter(teams: list[str]) -> str:
        """
        Build SQL WHERE clause for team filtering.

        Args:
            teams: List of team IDs

        Returns:
            SQL filter string
        """
        if teams[0] == "all":
            return ""
        elif len(teams) == 1:
            return f" AND pss.team_id = '{teams[0]}'"
        else:
            team_ids_str = ",".join([f"'{t}'" for t in teams])
            return f" AND pss.team_id IN ({team_ids_str})"

    @staticmethod
    def build_season_filter(is_career_mode: bool, seasons: list[str]) -> str:
        """
        Build SQL WHERE clause for season filtering.

        Args:
            is_career_mode: Whether in career mode
            seasons: List of season years

        Returns:
            SQL filter string
        """
        if is_career_mode:
            return ""
        elif len(seasons) == 1:
            return f" AND pss.year = {seasons[0]}"
        else:
            season_years_str = ",".join(seasons)
            return f" AND pss.year IN ({season_years_str})"
