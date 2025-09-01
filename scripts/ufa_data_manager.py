#!/usr/bin/env python3
"""
Unified UFA (Ultimate Frisbee Association) Data Manager.
This script consolidates all UFA data operations for direct API-to-database import.
"""

import logging
import os
import sys
import time
from datetime import datetime
from typing import Any

import requests

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from backend.sql_database import get_db
from backend.stats_processor import StatsProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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


class UFADataManager:
    """Unified manager for UFA data import operations."""

    def __init__(self):
        self.api_client = UFAAPIClient()
        self.db = get_db()
        self.stats_processor = StatsProcessor(self.db)

    def import_from_api(
        self, years: list[int] | None = None, clear_existing: bool = True
    ) -> dict[str, int]:
        """
        Import UFA data directly from API into the database.

        Args:
            years: List of years to import. If None, imports 2012-2025 (excluding 2020)
            clear_existing: Whether to clear existing data first

        Returns:
            Dictionary with counts of imported data
        """
        if years is None:
            years = [y for y in range(2012, 2026) if y != 2020]

        logger.info(f"Starting direct API import for years: {years}")

        counts = {"teams": 0, "players": 0, "games": 0}

        try:
            if clear_existing:
                logger.info("Clearing existing data...")
                self._clear_database()

            # Import teams
            logger.info("Fetching and importing teams...")
            teams_data = self.api_client.get_teams(years=years)
            if teams_data:
                counts["teams"] = self._import_teams_from_api(teams_data, years)

            # Import players
            logger.info("Fetching and importing players...")
            players_data = self.api_client.get_players(years=years)
            if players_data:
                counts["players"] = self._import_players_from_api(players_data)

            # Import games
            logger.info("Fetching and importing games...")
            games_data = self.api_client.get_games(years=years)
            if games_data:
                counts["games"] = self._import_games_from_api(games_data)

            logger.info(f"Import complete. Total: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Error during import: {e}")
            raise

    # ===== DATABASE OPERATIONS =====

    def _clear_database(self):
        """Clear all UFA data from the database."""
        tables = [
            "player_game_stats",
            "player_season_stats",
            "team_season_stats",
            "games",
            "players",
            "teams",
        ]
        for table in tables:
            try:
                self.db.execute_query(f"DELETE FROM {table}")
                logger.info(f"  Cleared {table}")
            except Exception as e:
                logger.warning(f"  Failed to clear {table}: {e}")

    # ===== PRIVATE IMPORT HELPERS =====

    def _import_teams_from_api(
        self, teams_data: list[dict[str, Any]], years: list[int]
    ) -> int:
        """Import teams from API data."""
        count = 0
        for team in teams_data:
            try:
                # Add year information if not present
                for year in years:
                    team_data = {
                        "team_id": team.get("teamID", ""),
                        "year": year,
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

                    # Insert team using database schema structure
                    self.db.execute_query(
                        """
                        INSERT OR IGNORE INTO teams 
                        (team_id, year, city, name, full_name, abbrev, wins, losses, ties, standing, division_id, division_name)
                        VALUES (:team_id, :year, :city, :name, :full_name, :abbrev, :wins, :losses, :ties, :standing, :division_id, :division_name)
                    """,
                        team_data,
                    )
                    count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to import team {team.get('name', 'unknown')}: {e}"
                )

        logger.info(f"  Imported {count} team records")
        return count

    def _import_players_from_api(self, players_data: list[dict[str, Any]]) -> int:
        """Import players from API data."""
        count = 0
        for player in players_data:
            try:
                player_data = {
                    "player_id": player.get("playerID", ""),
                    "first_name": player.get("firstName", ""),
                    "last_name": player.get("lastName", ""),
                    "full_name": player.get("fullName", ""),
                    "team_id": player.get("teamID", ""),
                    "active": player.get("active", True),
                    "year": player.get("year"),
                    "jersey_number": player.get("jerseyNumber"),
                }

                # Insert player using database schema structure
                self.db.execute_query(
                    """
                    INSERT OR IGNORE INTO players 
                    (player_id, first_name, last_name, full_name, team_id, active, year, jersey_number)
                    VALUES (:player_id, :first_name, :last_name, :full_name, :team_id, :active, :year, :jersey_number)
                """,
                    player_data,
                )
                count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to import player {player.get('fullName', 'unknown')}: {e}"
                )

        logger.info(f"  Imported {count} players")
        return count

    def _import_games_from_api(self, games_data: list[dict[str, Any]]) -> int:
        """Import games from API data."""
        count = 0
        for game in games_data:
            try:
                game_data = {
                    "game_id": game.get("gameID", ""),
                    "away_team_id": game.get("awayTeam", ""),
                    "home_team_id": game.get("homeTeam", ""),
                    "away_score": game.get("awayScore"),
                    "home_score": game.get("homeScore"),
                    "status": game.get("status", ""),
                    "start_timestamp": game.get("startTimestamp"),
                    "start_timezone": game.get("startTimezone"),
                    "streaming_url": game.get("streamingUrl"),
                    "update_timestamp": game.get("updateTimestamp"),
                    "week": game.get("week"),
                    "location": game.get("location"),
                }

                # Insert game using database schema structure
                self.db.execute_query(
                    """
                    INSERT OR IGNORE INTO games 
                    (game_id, away_team_id, home_team_id, away_score, home_score, status, 
                     start_timestamp, start_timezone, streaming_url, update_timestamp, week, location)
                    VALUES (:game_id, :away_team_id, :home_team_id, :away_score, :home_score, :status,
                            :start_timestamp, :start_timezone, :streaming_url, :update_timestamp, :week, :location)
                """,
                    game_data,
                )
                count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to import game {game.get('gameID', 'unknown')}: {e}"
                )

        logger.info(f"  Imported {count} games")
        return count


def main():
    """Main function to run UFA data operations based on command line arguments."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ufa_data_manager.py import-api [years...]")
        print("")
        print("Examples:")
        print(
            "  python ufa_data_manager.py import-api          # Import all years (2012-2025, excluding 2020)"
        )
        print("  python ufa_data_manager.py import-api 2023     # Import only 2023")
        print(
            "  python ufa_data_manager.py import-api 2022 2023 2024  # Import specific years"
        )
        sys.exit(1)

    manager = UFADataManager()
    command = sys.argv[1]

    # Parse years if provided
    years = None
    if len(sys.argv) > 2:
        try:
            years = [int(y) for y in sys.argv[2:]]
        except ValueError:
            print("Error: Years must be integers")
            sys.exit(1)

    try:
        if command == "import-api":
            result = manager.import_from_api(years)
            print(f"Successfully imported: {result}")

        else:
            print(f"Unknown command: {command}")
            print("Only 'import-api' is supported. Use --help for usage information.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
