#!/usr/bin/env python3
"""
Unified UFA (Ultimate Frisbee Association) Data Manager.
This script consolidates all UFA data operations for direct API-to-database import.
"""

import json
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from multiprocessing import cpu_count
from typing import Any

import requests

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from data.database import get_db
from data.processor import StatsProcessor


def _import_game_stats_chunk(game_chunk_data: tuple[list[dict], int]) -> dict[str, int]:
    """
    Helper function to import player game stats for a chunk of games.
    This function runs in a separate process for parallel processing.

    Args:
        game_chunk_data: Tuple of (games_list, chunk_number)

    Returns:
        Dictionary with import counts
    """
    games_chunk, chunk_num = game_chunk_data

    # Create new database connection for this process
    db = get_db()
    api_client = UFAAPIClient()

    logger = logging.getLogger(__name__)
    logger.info(f"[Chunk {chunk_num}] Processing {len(games_chunk)} games")

    count = 0
    skipped_allstar = 0
    for i, game in enumerate(games_chunk, 1):
        game_id = game.get("gameID", "")
        if not game_id:
            continue

        # Skip all-star games
        away_team_id = game.get("awayTeamID", "")
        home_team_id = game.get("homeTeamID", "")
        if (
            "allstar" in game_id.lower()
            or "allstar" in away_team_id.lower()
            or "allstar" in home_team_id.lower()
        ):
            skipped_allstar += 1
            continue

        try:
            # Get player game stats for this game
            player_stats_data = api_client.get_player_game_stats(game_id)

            for player_stat in player_stats_data:
                try:
                    # Extract year from game_id or use current year
                    year = int(game_id.split("-")[0]) if "-" in game_id else 2025

                    player_game_stat = {
                        "player_id": player_stat["player"]["playerID"],
                        "game_id": game_id,
                        "team_id": player_stat.get("teamID", ""),
                        "year": year,
                        "assists": player_stat.get("assists", 0),
                        "goals": player_stat.get("goals", 0),
                        "hockey_assists": player_stat.get("hockeyAssists", 0),
                        "completions": player_stat.get("completions", 0),
                        "throw_attempts": player_stat.get("throwAttempts", 0),
                        "throwaways": player_stat.get("throwaways", 0),
                        "stalls": player_stat.get("stalls", 0),
                        "callahans_thrown": player_stat.get("callahansThrown", 0),
                        "yards_received": player_stat.get("yardsReceived", 0),
                        "yards_thrown": player_stat.get("yardsThrown", 0),
                        "hucks_attempted": player_stat.get("hucksAttempted", 0),
                        "hucks_completed": player_stat.get("hucksCompleted", 0),
                        "catches": player_stat.get("catches", 0),
                        "drops": player_stat.get("drops", 0),
                        "blocks": player_stat.get("blocks", 0),
                        "callahans": player_stat.get("callahans", 0),
                        "pulls": player_stat.get("pulls", 0),
                        "ob_pulls": player_stat.get("obPulls", 0),
                        "recorded_pulls": player_stat.get("recordedPulls", 0),
                        "recorded_pulls_hangtime": player_stat.get(
                            "recordedPullsHangtime"
                        ),
                        "o_points_played": player_stat.get("oPointsPlayed", 0),
                        "o_points_scored": player_stat.get("oPointsScored", 0),
                        "d_points_played": player_stat.get("dPointsPlayed", 0),
                        "d_points_scored": player_stat.get("dPointsScored", 0),
                        "seconds_played": player_stat.get("secondsPlayed", 0),
                        "o_opportunities": player_stat.get("oOpportunities", 0),
                        "o_opportunity_scores": player_stat.get(
                            "oOpportunityScores", 0
                        ),
                        "d_opportunities": player_stat.get("dOpportunities", 0),
                        "d_opportunity_stops": player_stat.get("dOpportunityStops", 0),
                    }

                    # Insert player game stats
                    db.execute_query(
                        """
                        INSERT OR IGNORE INTO player_game_stats (
                            player_id, game_id, team_id, year,
                            assists, goals, hockey_assists, completions, throw_attempts, throwaways, stalls,
                            callahans_thrown, yards_received, yards_thrown, hucks_attempted, hucks_completed,
                            catches, drops, blocks, callahans, pulls, ob_pulls, recorded_pulls, recorded_pulls_hangtime,
                            o_points_played, o_points_scored, d_points_played, d_points_scored, seconds_played,
                            o_opportunities, o_opportunity_scores, d_opportunities, d_opportunity_stops
                        ) VALUES (
                            :player_id, :game_id, :team_id, :year,
                            :assists, :goals, :hockey_assists, :completions, :throw_attempts, :throwaways, :stalls,
                            :callahans_thrown, :yards_received, :yards_thrown, :hucks_attempted, :hucks_completed,
                            :catches, :drops, :blocks, :callahans, :pulls, :ob_pulls, :recorded_pulls, :recorded_pulls_hangtime,
                            :o_points_played, :o_points_scored, :d_points_played, :d_points_scored, :seconds_played,
                            :o_opportunities, :o_opportunity_scores, :d_opportunities, :d_opportunity_stops
                        )
                        """,
                        player_game_stat,
                    )
                    count += 1
                except Exception as e:
                    logger.warning(
                        f"[Chunk {chunk_num}] Failed to import player game stat for {player_stat.get('player', {}).get('playerID', 'unknown')}: {e}"
                    )

        except Exception as e:
            logger.warning(
                f"[Chunk {chunk_num}] Failed to get player stats for game {game_id}: {e}"
            )

        # Import game events for this game
        try:
            events_data = api_client.get_game_events(game_id)
            if events_data:
                # Create a temporary manager instance to use the helper method
                temp_manager = UFADataManager()
                temp_manager.db = db  # Use the same db connection
                events_count = temp_manager._import_single_game_events(
                    game_id, events_data
                )

                if events_count > 0:
                    logger.info(
                        f"[Chunk {chunk_num}] Imported {events_count} events for game {game_id}"
                    )

        except Exception as e:
            logger.warning(
                f"[Chunk {chunk_num}] Failed to get events for game {game_id}: {e}"
            )

    if skipped_allstar > 0:
        logger.info(f"[Chunk {chunk_num}] Skipped {skipped_allstar} all-star games")
    logger.info(
        f"[Chunk {chunk_num}] Imported {count} player game stats from {len(games_chunk) - skipped_allstar} regular games"
    )
    return {
        "player_game_stats": count,
        "games_processed": len(games_chunk) - skipped_allstar,
    }


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

        counts = {
            "teams": 0,
            "players": 0,
            "games": 0,
            "player_game_stats": 0,
            "player_season_stats": 0,
        }

        try:
            if clear_existing:
                logger.info("Clearing existing data...")
                self._clear_database()

            # Import teams
            logger.info("Fetching and importing teams...")
            teams_data = self.api_client.get_teams(years=years)
            if teams_data:
                counts["teams"] = self._import_teams_from_api(teams_data)

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

            # Import player game stats for each game
            if games_data:
                logger.info("Importing player game statistics...")
                counts["player_game_stats"] = self._import_player_game_stats_from_api(
                    games_data
                )

            # Import player season stats
            if players_data:
                logger.info("Importing player season statistics...")
                counts["player_season_stats"] = (
                    self._import_player_season_stats_from_api(players_data, years)
                )

            logger.info(f"Import complete. Total: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Error during import: {e}")
            raise

    def import_from_api_parallel(
        self,
        years: list[int] | None = None,
        clear_existing: bool = True,
        workers: int = None,
    ) -> dict[str, int]:
        """
        Import UFA data directly from API into the database with parallel processing.

        Args:
            years: List of years to import. If None, imports 2012-2025 (excluding 2020)
            clear_existing: Whether to clear existing data first
            workers: Number of parallel workers. If None, uses CPU count

        Returns:
            Dictionary with counts of imported data
        """
        if years is None:
            years = [y for y in range(2012, 2026) if y != 2020]

        if workers is None:
            workers = min(cpu_count(), 8)  # Limit to avoid overwhelming API

        logger.info(
            f"Starting parallel API import for years: {years} with {workers} workers"
        )

        counts = {
            "teams": 0,
            "players": 0,
            "games": 0,
            "player_game_stats": 0,
            "player_season_stats": 0,
        }

        try:
            if clear_existing:
                logger.info("Clearing existing data...")
                self._clear_database()

            # Import teams (fast, no need to parallelize)
            logger.info("Fetching and importing teams...")
            teams_data = self.api_client.get_teams(years=years)
            if teams_data:
                counts["teams"] = self._import_teams_from_api(teams_data)

            # Import players (fast, no need to parallelize)
            logger.info("Fetching and importing players...")
            players_data = self.api_client.get_players(years=years)
            if players_data:
                counts["players"] = self._import_players_from_api(players_data)

            # Import games (relatively fast)
            logger.info("Fetching and importing games...")
            games_data = self.api_client.get_games(years=years)
            if games_data:
                counts["games"] = self._import_games_from_api(games_data)

            # Import player game stats in parallel (this is the slow part)
            if games_data:
                logger.info(
                    f"Importing player game statistics in parallel with {workers} workers..."
                )
                counts["player_game_stats"] = self._import_player_game_stats_parallel(
                    games_data, workers
                )

            # Import player season stats
            if players_data:
                logger.info("Importing player season statistics...")
                counts["player_season_stats"] = (
                    self._import_player_season_stats_from_api(players_data, years)
                )

            logger.info(f"Parallel import complete. Total: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Error during parallel import: {e}")
            raise

    def _import_player_game_stats_parallel(
        self, games_data: list[dict[str, Any]], workers: int
    ) -> int:
        """Import player game statistics using parallel processing."""
        total_games = len(games_data)
        chunk_size = max(
            10, total_games // (workers * 2)
        )  # Ensure reasonable chunk size

        # Split games into chunks
        chunks = []
        for i in range(0, total_games, chunk_size):
            chunk = games_data[i : i + chunk_size]
            chunks.append((chunk, i // chunk_size + 1))

        logger.info(
            f"  Processing {total_games} games in {len(chunks)} chunks with {workers} workers"
        )

        total_count = 0
        completed_chunks = 0

        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all chunks
            future_to_chunk = {
                executor.submit(_import_game_stats_chunk, chunk_data): chunk_data[1]
                for chunk_data in chunks
            }

            # Process completed chunks
            for future in as_completed(future_to_chunk):
                chunk_num = future_to_chunk[future]
                try:
                    result = future.result()
                    total_count += result["player_game_stats"]
                    completed_chunks += 1

                    progress = (completed_chunks / len(chunks)) * 100
                    logger.info(
                        f"  Progress: {completed_chunks}/{len(chunks)} chunks completed ({progress:.1f}%)"
                    )

                except Exception as e:
                    logger.error(f"  Chunk {chunk_num} failed: {e}")

        logger.info(
            f"  Imported {total_count} player game stats from {total_games} games"
        )
        return total_count

    def complete_missing_imports(
        self, years: list[int] | None = None
    ) -> dict[str, int]:
        """
        Complete missing imports (games and season stats) without clearing existing data.
        Use this to finish a partially completed import.

        Args:
            years: List of years to import. If None, imports 2012-2025 (excluding 2020)

        Returns:
            Dictionary with counts of imported data
        """
        if years is None:
            years = [y for y in range(2012, 2026) if y != 2020]

        logger.info(f"Completing missing imports for years: {years}")

        counts = {"games": 0, "player_season_stats": 0}

        try:
            # Check what we already have
            existing_games = self.db.get_row_count("games")
            existing_stats = self.db.get_row_count("player_game_stats")
            existing_season = self.db.get_row_count("player_season_stats")

            logger.info(
                f"Current status: {existing_games} games, {existing_stats} game stats, {existing_season} season stats"
            )

            # Import games if missing
            if existing_games == 0:
                logger.info("Importing games data...")
                games_data = self.api_client.get_games(years=years)
                if games_data:
                    counts["games"] = self._import_games_from_api(games_data)
            else:
                logger.info(f"Games already imported ({existing_games} records)")

            # Import player season stats if missing
            if existing_season == 0:
                logger.info("Importing player season statistics...")
                players_data = self.api_client.get_players(years=years)
                if players_data:
                    counts["player_season_stats"] = (
                        self._import_player_season_stats_from_api(players_data, years)
                    )
            else:
                logger.info(
                    f"Season stats already imported ({existing_season} records)"
                )

            logger.info(f"Missing imports complete. Imported: {counts}")
            return counts

        except Exception as e:
            logger.error(f"Error completing missing imports: {e}")
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
        self, teams_data: list[dict[str, Any]], years: list[int] = None
    ) -> int:
        """Import teams from API data."""
        count = 0
        for team in teams_data:
            try:
                team_data = {
                    "team_id": team.get("teamID", ""),
                    "year": team.get("year", 2025),  # Use actual year from team data
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
        skipped_allstar = 0
        for game in games_data:
            try:
                # Extract year from game_id or use current year
                game_id = game.get("gameID", "")
                year = int(game_id.split("-")[0]) if "-" in game_id else 2025

                # Skip all-star games
                away_team_id = game.get("awayTeamID", "")
                home_team_id = game.get("homeTeamID", "")
                if (
                    "allstar" in game_id.lower()
                    or "allstar" in away_team_id.lower()
                    or "allstar" in home_team_id.lower()
                ):
                    skipped_allstar += 1
                    continue

                game_data = {
                    "game_id": game_id,
                    "away_team_id": away_team_id,
                    "home_team_id": home_team_id,
                    "away_score": game.get("awayScore"),
                    "home_score": game.get("homeScore"),
                    "status": game.get("status", ""),
                    "start_timestamp": game.get("startTimestamp"),
                    "start_timezone": game.get("startTimezone"),
                    "streaming_url": game.get("streamingUrl"),
                    "update_timestamp": game.get("updateTimestamp"),
                    "week": game.get("week"),
                    "location": game.get("location"),
                    "year": year,
                }

                # Insert game using database schema structure
                self.db.execute_query(
                    """
                    INSERT OR IGNORE INTO games 
                    (game_id, away_team_id, home_team_id, away_score, home_score, status, 
                     start_timestamp, start_timezone, streaming_url, update_timestamp, week, location, year)
                    VALUES (:game_id, :away_team_id, :home_team_id, :away_score, :home_score, :status,
                            :start_timestamp, :start_timezone, :streaming_url, :update_timestamp, :week, :location, :year)
                """,
                    game_data,
                )
                count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to import game {game.get('gameID', 'unknown')}: {e}"
                )

        if skipped_allstar > 0:
            logger.info(f"  Skipped {skipped_allstar} all-star games")
        logger.info(f"  Imported {count} games")
        return count

    def _import_player_game_stats_from_api(
        self, games_data: list[dict[str, Any]]
    ) -> int:
        """Import player game statistics for all games."""
        count = 0
        skipped_allstar = 0
        total_games = len(games_data)

        for i, game in enumerate(games_data, 1):
            game_id = game.get("gameID", "")
            if not game_id:
                continue

            # Skip all-star games
            away_team_id = game.get("awayTeamID", "")
            home_team_id = game.get("homeTeamID", "")
            if (
                "allstar" in game_id.lower()
                or "allstar" in away_team_id.lower()
                or "allstar" in home_team_id.lower()
            ):
                skipped_allstar += 1
                continue

            try:
                # Get player game stats for this game
                player_stats_data = self.api_client.get_player_game_stats(game_id)

                for player_stat in player_stats_data:
                    try:
                        # Extract year from game_id or use current year
                        year = int(game_id.split("-")[0]) if "-" in game_id else 2025

                        player_game_stat = {
                            "player_id": player_stat["player"]["playerID"],
                            "game_id": game_id,
                            "team_id": player_stat.get("teamID", ""),
                            "year": year,
                            "assists": player_stat.get("assists", 0),
                            "goals": player_stat.get("goals", 0),
                            "hockey_assists": player_stat.get("hockeyAssists", 0),
                            "completions": player_stat.get("completions", 0),
                            "throw_attempts": player_stat.get("throwAttempts", 0),
                            "throwaways": player_stat.get("throwaways", 0),
                            "stalls": player_stat.get("stalls", 0),
                            "callahans_thrown": player_stat.get("callahansThrown", 0),
                            "yards_received": player_stat.get("yardsReceived", 0),
                            "yards_thrown": player_stat.get("yardsThrown", 0),
                            "hucks_attempted": player_stat.get("hucksAttempted", 0),
                            "hucks_completed": player_stat.get("hucksCompleted", 0),
                            "catches": player_stat.get("catches", 0),
                            "drops": player_stat.get("drops", 0),
                            "blocks": player_stat.get("blocks", 0),
                            "callahans": player_stat.get("callahans", 0),
                            "pulls": player_stat.get("pulls", 0),
                            "ob_pulls": player_stat.get("obPulls", 0),
                            "recorded_pulls": player_stat.get("recordedPulls", 0),
                            "recorded_pulls_hangtime": player_stat.get(
                                "recordedPullsHangtime"
                            ),
                            "o_points_played": player_stat.get("oPointsPlayed", 0),
                            "o_points_scored": player_stat.get("oPointsScored", 0),
                            "d_points_played": player_stat.get("dPointsPlayed", 0),
                            "d_points_scored": player_stat.get("dPointsScored", 0),
                            "seconds_played": player_stat.get("secondsPlayed", 0),
                            "o_opportunities": player_stat.get("oOpportunities", 0),
                            "o_opportunity_scores": player_stat.get(
                                "oOpportunityScores", 0
                            ),
                            "d_opportunities": player_stat.get("dOpportunities", 0),
                            "d_opportunity_stops": player_stat.get(
                                "dOpportunityStops", 0
                            ),
                        }

                        # Insert player game stats
                        self.db.execute_query(
                            """
                            INSERT OR IGNORE INTO player_game_stats (
                                player_id, game_id, team_id, year,
                                assists, goals, hockey_assists, completions, throw_attempts, throwaways, stalls,
                                callahans_thrown, yards_received, yards_thrown, hucks_attempted, hucks_completed,
                                catches, drops, blocks, callahans, pulls, ob_pulls, recorded_pulls, recorded_pulls_hangtime,
                                o_points_played, o_points_scored, d_points_played, d_points_scored, seconds_played,
                                o_opportunities, o_opportunity_scores, d_opportunities, d_opportunity_stops
                            ) VALUES (
                                :player_id, :game_id, :team_id, :year,
                                :assists, :goals, :hockey_assists, :completions, :throw_attempts, :throwaways, :stalls,
                                :callahans_thrown, :yards_received, :yards_thrown, :hucks_attempted, :hucks_completed,
                                :catches, :drops, :blocks, :callahans, :pulls, :ob_pulls, :recorded_pulls, :recorded_pulls_hangtime,
                                :o_points_played, :o_points_scored, :d_points_played, :d_points_scored, :seconds_played,
                                :o_opportunities, :o_opportunity_scores, :d_opportunities, :d_opportunity_stops
                            )
                            """,
                            player_game_stat,
                        )
                        count += 1
                    except Exception as e:
                        logger.warning(
                            f"Failed to import player game stat for {player_stat.get('player', {}).get('playerID', 'unknown')}: {e}"
                        )

                # Import game events for this game (same as parallel version)
                try:
                    events_data = self.api_client.get_game_events(game_id)
                    if events_data:
                        events_count = self._import_single_game_events(
                            game_id, events_data
                        )
                        if events_count > 0:
                            logger.info(
                                f"  Imported {events_count} events for game {game_id}"
                            )
                except Exception as e:
                    logger.warning(f"Failed to import events for game {game_id}: {e}")

                if i % 100 == 0:
                    logger.info(
                        f"  Processed {i}/{total_games} games, imported {count} player game stats so far"
                    )

            except Exception as e:
                logger.warning(f"Failed to get player stats for game {game_id}: {e}")

        if skipped_allstar > 0:
            logger.info(f"  Skipped {skipped_allstar} all-star games")
        logger.info(
            f"  Imported {count} player game stats from {total_games - skipped_allstar} regular games"
        )
        return count

    def _import_player_season_stats_from_api(
        self, players_data: list[dict[str, Any]], years: list[int]
    ) -> int:
        """Import player season statistics."""
        count = 0

        # Extract all unique player IDs
        player_ids = []
        for player in players_data:
            player_id = player.get("playerID", "")
            if player_id and player_id not in player_ids:
                player_ids.append(player_id)

        logger.info(
            f"  Fetching season stats for {len(player_ids)} players across {len(years)} years"
        )

        # Get season stats from API
        season_stats_data = self.api_client.get_player_stats(player_ids, years)

        for stat in season_stats_data:
            try:
                player_season_stat = {
                    "player_id": stat["player"]["playerID"],
                    "team_id": stat.get("teamID", ""),  # May need to derive this
                    "year": stat.get("year"),
                    "total_assists": stat.get("assists", 0),
                    "total_goals": stat.get("goals", 0),
                    "total_hockey_assists": stat.get("hockeyAssists", 0),
                    "total_completions": stat.get("completions", 0),
                    "total_throw_attempts": stat.get("throwAttempts", 0),
                    "total_throwaways": stat.get("throwaways", 0),
                    "total_stalls": stat.get("stalls", 0),
                    "total_callahans_thrown": stat.get("callahansThrown", 0),
                    "total_yards_received": stat.get("yardsReceived", 0),
                    "total_yards_thrown": stat.get("yardsThrown", 0),
                    "total_hucks_attempted": stat.get("hucksAttempted", 0),
                    "total_hucks_completed": stat.get("hucksCompleted", 0),
                    "total_catches": stat.get("catches", 0),
                    "total_drops": stat.get("drops", 0),
                    "total_blocks": stat.get("blocks", 0),
                    "total_callahans": stat.get("callahans", 0),
                    "total_pulls": stat.get("pulls", 0),
                    "total_ob_pulls": stat.get("obPulls", 0),
                    "total_recorded_pulls": stat.get("recordedPulls", 0),
                    "total_recorded_pulls_hangtime": stat.get("recordedPullsHangtime"),
                    "total_o_points_played": stat.get("oPointsPlayed", 0),
                    "total_o_points_scored": stat.get("oPointsScored", 0),
                    "total_d_points_played": stat.get("dPointsPlayed", 0),
                    "total_d_points_scored": stat.get("dPointsScored", 0),
                    "total_seconds_played": stat.get("secondsPlayed", 0),
                    "total_o_opportunities": stat.get("oOpportunities", 0),
                    "total_o_opportunity_scores": stat.get("oOpportunityScores", 0),
                    "total_d_opportunities": stat.get("dOpportunities", 0),
                    "total_d_opportunity_stops": stat.get("dOpportunityStops", 0),
                }

                # Calculate completion percentage
                if player_season_stat["total_throw_attempts"] > 0:
                    player_season_stat["completion_percentage"] = round(
                        player_season_stat["total_completions"]
                        * 100.0
                        / player_season_stat["total_throw_attempts"],
                        2,
                    )
                else:
                    player_season_stat["completion_percentage"] = 0

                # Find team_id for this player/year combination from players data
                for player in players_data:
                    if player.get("playerID") == stat["player"][
                        "playerID"
                    ] and player.get("year") == stat.get("year"):
                        player_season_stat["team_id"] = player.get("teamID", "")
                        break

                # Insert player season stats
                self.db.execute_query(
                    """
                    INSERT OR IGNORE INTO player_season_stats (
                        player_id, team_id, year,
                        total_assists, total_goals, total_hockey_assists, total_completions, total_throw_attempts,
                        total_throwaways, total_stalls, total_callahans_thrown, total_yards_received, total_yards_thrown,
                        total_hucks_attempted, total_hucks_completed, total_catches, total_drops, total_blocks,
                        total_callahans, total_pulls, total_ob_pulls, total_recorded_pulls, total_recorded_pulls_hangtime,
                        total_o_points_played, total_o_points_scored, total_d_points_played, total_d_points_scored,
                        total_seconds_played, total_o_opportunities, total_o_opportunity_scores, total_d_opportunities,
                        total_d_opportunity_stops, completion_percentage
                    ) VALUES (
                        :player_id, :team_id, :year,
                        :total_assists, :total_goals, :total_hockey_assists, :total_completions, :total_throw_attempts,
                        :total_throwaways, :total_stalls, :total_callahans_thrown, :total_yards_received, :total_yards_thrown,
                        :total_hucks_attempted, :total_hucks_completed, :total_catches, :total_drops, :total_blocks,
                        :total_callahans, :total_pulls, :total_ob_pulls, :total_recorded_pulls, :total_recorded_pulls_hangtime,
                        :total_o_points_played, :total_o_points_scored, :total_d_points_played, :total_d_points_scored,
                        :total_seconds_played, :total_o_opportunities, :total_o_opportunity_scores, :total_d_opportunities,
                        :total_d_opportunity_stops, :completion_percentage
                    )
                    """,
                    player_season_stat,
                )
                count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to import season stat for {stat.get('player', {}).get('playerID', 'unknown')}: {e}"
                )

        logger.info(f"  Imported {count} player season stats")
        return count

    def _import_single_game_events(self, game_id: str, events_data: dict) -> int:
        """Import game events for a single game (helper method to avoid duplication)."""
        count = 0

        # Process home events
        for idx, event in enumerate(events_data.get("homeEvents", [])):
            try:
                event_record = {
                    "game_id": game_id,
                    "event_index": idx,
                    "team": "home",
                    "event_type": event.get("type", 0),
                    "event_time": event.get("time"),
                    "thrower_id": event.get("thrower"),
                    "receiver_id": event.get("receiver"),
                    "defender_id": event.get("defender"),
                    "puller_id": event.get("puller"),
                    "thrower_x": event.get("throwerX"),
                    "thrower_y": event.get("throwerY"),
                    "receiver_x": event.get("receiverX"),
                    "receiver_y": event.get("receiverY"),
                    "turnover_x": event.get("turnoverX"),
                    "turnover_y": event.get("turnoverY"),
                    "pull_x": event.get("pullX"),
                    "pull_y": event.get("pullY"),
                    "pull_ms": event.get("pullMs"),
                    "line_players": (
                        json.dumps(event.get("line", [])) if event.get("line") else None
                    ),
                }

                self.db.execute_query(
                    """
                    INSERT OR IGNORE INTO game_events (
                        game_id, event_index, team, event_type, event_time,
                        thrower_id, receiver_id, defender_id, puller_id,
                        thrower_x, thrower_y, receiver_x, receiver_y,
                        turnover_x, turnover_y, pull_x, pull_y, pull_ms, line_players
                    ) VALUES (
                        :game_id, :event_index, :team, :event_type, :event_time,
                        :thrower_id, :receiver_id, :defender_id, :puller_id,
                        :thrower_x, :thrower_y, :receiver_x, :receiver_y,
                        :turnover_x, :turnover_y, :pull_x, :pull_y, :pull_ms, :line_players
                    )
                    """,
                    event_record,
                )
                count += 1
            except Exception:
                pass  # Silently skip individual event errors

        # Process away events
        for idx, event in enumerate(events_data.get("awayEvents", [])):
            try:
                event_record = {
                    "game_id": game_id,
                    "event_index": idx,
                    "team": "away",
                    "event_type": event.get("type", 0),
                    "event_time": event.get("time"),
                    "thrower_id": event.get("thrower"),
                    "receiver_id": event.get("receiver"),
                    "defender_id": event.get("defender"),
                    "puller_id": event.get("puller"),
                    "thrower_x": event.get("throwerX"),
                    "thrower_y": event.get("throwerY"),
                    "receiver_x": event.get("receiverX"),
                    "receiver_y": event.get("receiverY"),
                    "turnover_x": event.get("turnoverX"),
                    "turnover_y": event.get("turnoverY"),
                    "pull_x": event.get("pullX"),
                    "pull_y": event.get("pullY"),
                    "pull_ms": event.get("pullMs"),
                    "line_players": (
                        json.dumps(event.get("line", [])) if event.get("line") else None
                    ),
                }

                self.db.execute_query(
                    """
                    INSERT OR IGNORE INTO game_events (
                        game_id, event_index, team, event_type, event_time,
                        thrower_id, receiver_id, defender_id, puller_id,
                        thrower_x, thrower_y, receiver_x, receiver_y,
                        turnover_x, turnover_y, pull_x, pull_y, pull_ms, line_players
                    ) VALUES (
                        :game_id, :event_index, :team, :event_type, :event_time,
                        :thrower_id, :receiver_id, :defender_id, :puller_id,
                        :thrower_x, :thrower_y, :receiver_x, :receiver_y,
                        :turnover_x, :turnover_y, :pull_x, :pull_y, :pull_ms, :line_players
                    )
                    """,
                    event_record,
                )
                count += 1
            except Exception:
                pass  # Silently skip individual event errors

        return count

    def _import_game_events_from_api(self, game_id: str) -> int:
        """Import game events from API data for a specific game."""
        # Skip all-star games
        if "allstar" in game_id.lower():
            return 0

        try:
            # Get game events from API
            events_data = self.api_client.get_game_events(game_id)

            if not events_data:
                return 0

            count = self._import_single_game_events(game_id, events_data)

            if count > 0:
                logger.info(f"  Imported {count} game events for {game_id}")

            return count

        except Exception as e:
            logger.warning(f"Failed to import game events for {game_id}: {e}")
            return 0


def main():
    """Main function to run UFA data operations based on command line arguments."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ufa_data_manager.py import-api [years...]")
        print(
            "  python ufa_data_manager.py import-api-parallel [--workers N] [years...]"
        )
        print("  python ufa_data_manager.py complete-missing [years...]")
        print("")
        print("Examples:")
        print(
            "  python ufa_data_manager.py import-api          # Import all years (sequential)"
        )
        print(
            "  python ufa_data_manager.py import-api 2023     # Import only 2023 (sequential)"
        )
        print(
            "  python ufa_data_manager.py import-api-parallel # Import all years (parallel, auto workers)"
        )
        print(
            "  python ufa_data_manager.py import-api-parallel --workers 4  # Import with 4 workers"
        )
        print(
            "  python ufa_data_manager.py import-api-parallel 2022 2023    # Import specific years (parallel)"
        )
        print(
            "  python ufa_data_manager.py complete-missing    # Complete missing games and season stats"
        )
        sys.exit(1)

    manager = UFADataManager()
    command = sys.argv[1]

    # Parse arguments
    years = None
    workers = None

    if command in ["import-api", "import-api-parallel", "complete-missing"]:
        args = sys.argv[2:]

        # Handle --workers option for parallel command
        if command == "import-api-parallel" and "--workers" in args:
            workers_idx = args.index("--workers")
            if workers_idx + 1 >= len(args):
                print("Error: --workers requires a number")
                sys.exit(1)
            try:
                workers = int(args[workers_idx + 1])
                # Remove --workers and its value from args
                args = args[:workers_idx] + args[workers_idx + 2 :]
            except ValueError:
                print("Error: --workers must be an integer")
                sys.exit(1)

        # Parse remaining arguments as years
        if args:
            try:
                years = [int(y) for y in args]
            except ValueError:
                print("Error: Years must be integers")
                sys.exit(1)

    try:
        if command == "import-api":
            result = manager.import_from_api(years)
            print(f"Successfully imported: {result}")

        elif command == "import-api-parallel":
            result = manager.import_from_api_parallel(years, workers=workers)
            print(f"Successfully imported (parallel): {result}")

        elif command == "complete-missing":
            result = manager.complete_missing_imports(years)
            print(f"Successfully completed missing imports: {result}")

        else:
            print(f"Unknown command: {command}")
            print(
                "Supported commands: 'import-api', 'import-api-parallel', 'complete-missing'"
            )
            sys.exit(1)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
