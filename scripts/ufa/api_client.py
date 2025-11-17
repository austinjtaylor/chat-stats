#!/usr/bin/env python3
"""
UFA API Client for interacting with the UFA Stats API.
"""

import logging
import time
from typing import Any

import requests
from datetime import datetime


class UFAAPIClient:
    """Client for interacting with the UFA Stats API"""

    def __init__(self, base_url: str = "https://www.backend.ufastats.com/api/v1"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "UFA-Stats-Client/1.0", "Accept": "application/json"}
        )
        self.logger = logging.getLogger(__name__)

    def _make_request(
        self, endpoint: str, params: dict = None, retries: int = 3
    ) -> dict:
        """Make API request with error handling and retries"""
        url = f"{self.base_url}/{endpoint}"

        for attempt in range(retries):
            try:
                self.logger.info(f"Making request to {url} with params: {params}")
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()

                data = response.json()
                if "data" in data:
                    self.logger.info(
                        f"Successfully retrieved {len(data['data'])} records"
                    )
                    return data
                else:
                    self.logger.warning(f"Unexpected response format: {data}")
                    return data

            except Exception as e:
                self.logger.warning(
                    f"Request failed (attempt {attempt + 1}/{retries}): {e}"
                )
                if attempt < retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    self.logger.error(f"All {retries} attempts failed for {url}")
                    raise

    def get_teams(
        self,
        years: str | list[int] = "all",
        team_ids: list[str] = None,
        division_ids: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get teams data from the API

        Returns:
            List of team dictionaries
        """
        params = {}

        if isinstance(years, list):
            params["years"] = ",".join(map(str, years))
        else:
            params["years"] = str(years)

        if team_ids:
            params["teamIDs"] = ",".join(team_ids)
        if division_ids:
            params["divisionIDs"] = ",".join(division_ids)

        data = self._make_request("teams", params)

        if "data" in data and data["data"]:
            # Flatten the nested division data
            teams_data = []
            for team in data["data"]:
                team_flat = team.copy()
                if "division" in team and team["division"]:
                    team_flat["divisionID"] = team["division"].get("divisionID")
                    team_flat["divisionName"] = team["division"].get("name")
                    del team_flat["division"]
                teams_data.append(team_flat)

            self.logger.info(f"Retrieved {len(teams_data)} team records")
            return teams_data
        else:
            self.logger.warning("No team data found")
            return []

    def get_players(
        self,
        years: str | list[int] = "all",
        team_ids: list[str] = None,
        player_ids: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get players data from the API

        Returns:
            List of player dictionaries
        """
        params = {}

        if isinstance(years, list):
            params["years"] = ",".join(map(str, years))
        else:
            params["years"] = str(years)

        if team_ids:
            params["teamIDs"] = ",".join(team_ids)
        if player_ids:
            params["playerIDs"] = ",".join(player_ids)

        data = self._make_request("players", params)

        if "data" in data and data["data"]:
            # Flatten the nested player and teams data
            players_data = []
            for player in data["data"]:
                base_player = {
                    "playerID": player.get("playerID"),
                    "firstName": player.get("firstName"),
                    "lastName": player.get("lastName"),
                    "fullName": f"{player.get('firstName', '')} {player.get('lastName', '')}".strip(),
                }

                # If player has team data, create one row per team
                if "teams" in player and player["teams"]:
                    for team in player["teams"]:
                        player_team = base_player.copy()
                        player_team.update(
                            {
                                "teamID": team.get("teamID"),
                                "active": team.get("active"),
                                "year": team.get("year"),
                                "jerseyNumber": team.get("jerseyNumber"),
                            }
                        )
                        players_data.append(player_team)
                else:
                    # Player with no team data
                    players_data.append(base_player)

            self.logger.info(f"Retrieved {len(players_data)} player-team records")
            return players_data
        else:
            self.logger.warning("No player data found")
            return []

    def get_player_game_stats(self, game_id: str) -> list[dict[str, Any]]:
        """Get player game statistics for a specific game."""
        data = self._make_request("playerGameStats", {"gameID": game_id})

        if "data" in data and data["data"]:
            self.logger.info(
                f"Retrieved {len(data['data'])} player game stats records for game {game_id}"
            )
            return data["data"]
        else:
            self.logger.warning(f"No player game stats found for game {game_id}")
            return []

    def get_player_stats(
        self, player_ids: list[str], years: list[int] = None
    ) -> list[dict[str, Any]]:
        """Get season statistics for specific players."""
        # UFA API has a limit of 100 players per request
        all_stats = []

        for i in range(0, len(player_ids), 100):
            chunk = player_ids[i : i + 100]
            params = {"playerIDs": ",".join(chunk)}

            if years:
                params["years"] = ",".join(map(str, years))

            data = self._make_request("playerStats", params)

            if "data" in data and data["data"]:
                self.logger.info(
                    f"Retrieved {len(data['data'])} player season stats records"
                )
                all_stats.extend(data["data"])
            else:
                self.logger.warning(
                    f"No player season stats found for chunk {i//100 + 1}"
                )

        return all_stats

    def get_games(
        self,
        date_range: str = None,
        game_ids: list[str] = None,
        team_ids: list[str] = None,
        statuses: list[str] = None,
        weeks: list[str] = None,
        years: list[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Get games data from the API

        Returns:
            List of game dictionaries
        """
        params = {}

        if date_range:
            params["date"] = date_range
        if game_ids:
            params["gameIDs"] = ",".join(game_ids)
        if team_ids:
            params["teamIDs"] = ",".join(team_ids)
        if statuses:
            params["statuses"] = ",".join(statuses)
        if weeks:
            params["weeks"] = ",".join(weeks)

        # Handle years parameter
        if years:
            if len(years) == 1:
                params["date"] = str(years[0])
            else:
                # For multiple years, we'll need to make separate requests
                all_games = []
                for year in years:
                    year_params = params.copy()
                    year_params["date"] = str(year)
                    year_data = self._make_request("games", year_params)
                    if "data" in year_data and year_data["data"]:
                        all_games.extend(year_data["data"])
                return all_games

        if not date_range and not game_ids and not years:
            # Default to current year if no date or game IDs specified
            current_year = datetime.now().year
            params["date"] = str(current_year)

        data = self._make_request("games", params)

        if "data" in data and data["data"]:
            self.logger.info(f"Retrieved {len(data['data'])} game records")
            return data["data"]
        else:
            self.logger.warning("No game data found")
            return []

    def get_game_events(self, game_id: str) -> dict[str, Any]:
        """
        Get game events with field position data

        Args:
            game_id: The game ID to query

        Returns:
            Dictionary with homeEvents and awayEvents arrays
        """
        params = {"gameID": game_id}
        data = self._make_request("gameEvents", params)

        if "data" in data:
            events = data["data"]
            home_count = len(events.get("homeEvents", []))
            away_count = len(events.get("awayEvents", []))
            self.logger.info(
                f"Retrieved {home_count} home events and {away_count} away events for game {game_id}"
            )
            return events
        else:
            self.logger.warning(f"No event data found for game {game_id}")
            return {"homeEvents": [], "awayEvents": []}
