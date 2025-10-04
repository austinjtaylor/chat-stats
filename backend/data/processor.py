"""
Stats processing module for data ingestion and transformation.
Handles importing sports statistics from various sources into the SQL database.
"""

import json
from datetime import date
from typing import Any

import pandas as pd

from data.database import SQLDatabase
from models.db import (
    Game,
    Player,
    PlayerGameStats,
    Team,
)


class StatsProcessor:
    """Processes and imports sports statistics data into the database."""

    def __init__(self, db: SQLDatabase = None):
        """
        Initialize the stats processor.

        Args:
            db: SQLDatabase instance. If None, creates a new one.
        """
        self.db = db or SQLDatabase()

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

    def import_players(self, players_data: list[dict[str, Any]]) -> int:
        """
        Import player data into the database.

        Args:
            players_data: List of player dictionaries

        Returns:
            Number of players imported
        """
        count = 0
        for player_dict in players_data:
            try:
                # Skip None values
                if not player_dict:
                    continue

                # Check if player already exists
                existing = self.db.execute_query(
                    "SELECT id FROM players WHERE name = :name",
                    {"name": player_dict.get("name")},
                )

                if not existing:
                    # Get team_id if team name is provided
                    if "team_name" in player_dict:
                        team_result = self.db.execute_query(
                            "SELECT id FROM teams WHERE name = :name",
                            {"name": player_dict["team_name"]},
                        )
                        if team_result:
                            player_dict["team_id"] = team_result[0]["id"]
                        player_dict.pop("team_name", None)

                    player = Player(**player_dict)
                    player_data = player.dict(exclude_none=True, exclude={"id"})
                    self.db.insert_data("players", player_data)
                    count += 1
            except Exception as e:
                # Log error and continue with next player
                print(f"Error importing player {player_dict}: {e}")
                continue

        return count

    def import_game(self, game_data: dict[str, Any]) -> int | None:
        """
        Import a single game into the database.

        Args:
            game_data: Game dictionary

        Returns:
            Game ID if imported, None if already exists
        """
        # Convert team names to IDs if needed
        if "home_team_name" in game_data:
            home_team = self.db.execute_query(
                "SELECT id FROM teams WHERE name = :name OR abbreviation = :name",
                {"name": game_data["home_team_name"]},
            )
            if home_team:
                game_data["home_team_id"] = home_team[0]["id"]
            game_data.pop("home_team_name", None)

        if "away_team_name" in game_data:
            away_team = self.db.execute_query(
                "SELECT id FROM teams WHERE name = :name OR abbreviation = :name",
                {"name": game_data["away_team_name"]},
            )
            if away_team:
                game_data["away_team_id"] = away_team[0]["id"]
            game_data.pop("away_team_name", None)

        # Check if game already exists
        existing = self.db.execute_query(
            """SELECT id FROM games 
               WHERE game_date = :game_date 
               AND home_team_id = :home_team_id 
               AND away_team_id = :away_team_id""",
            {
                "game_date": game_data.get("game_date"),
                "home_team_id": game_data.get("home_team_id"),
                "away_team_id": game_data.get("away_team_id"),
            },
        )

        if not existing:
            game = Game(**game_data)
            game_dict = game.dict(exclude_none=True, exclude={"id"})
            # Convert date to string for SQLite
            if isinstance(game_dict.get("game_date"), date):
                game_dict["game_date"] = game_dict["game_date"].isoformat()
            return self.db.insert_data("games", game_dict)

        return existing[0]["id"] if existing else None

    def import_player_game_stats(self, stats_data: list[dict[str, Any]]) -> int:
        """
        Import player game statistics.

        Args:
            stats_data: List of player game stats dictionaries

        Returns:
            Number of stats records imported
        """
        count = 0
        for stat_dict in stats_data:
            try:
                # Skip None values
                if not stat_dict:
                    continue

                # Convert player name to ID if needed
                if "player_name" in stat_dict:
                    player = self.db.execute_query(
                        "SELECT id FROM players WHERE name = :name",
                        {"name": stat_dict["player_name"]},
                    )
                    if player:
                        stat_dict["player_id"] = player[0]["id"]
                    stat_dict.pop("player_name", None)

                # Check if stats already exist for this player/game
                existing = self.db.execute_query(
                    """SELECT id FROM player_game_stats 
                       WHERE player_id = :player_id AND game_id = :game_id""",
                    {
                        "player_id": stat_dict.get("player_id"),
                        "game_id": stat_dict.get("game_id"),
                    },
                )

                if not existing:
                    stats = PlayerGameStats(**stat_dict)
                    stats_data = stats.dict(exclude_none=True, exclude={"id"})
                    self.db.insert_data("player_game_stats", stats_data)
                    count += 1
            except Exception as e:
                # Log error and continue with next stat record
                print(f"Error importing player game stats {stat_dict}: {e}")
                continue

        return count

    def calculate_season_stats(self, season):
        """
        Calculate and store aggregated season statistics for all players and teams.

        Args:
            season: Season identifier (year or season string like "2023-24")
        """
        try:
            # Calculate player season stats - use UFA statistics
            player_stats_query = """
            SELECT 
                pgs.player_id,
                pgs.team_id,
                COUNT(DISTINCT pgs.game_id) as games_played,
                SUM(pgs.seconds_played) as total_seconds_played,
                SUM(pgs.goals) as total_goals,
                SUM(pgs.assists) as total_assists,
                SUM(pgs.hockey_assists) as total_hockey_assists,
                SUM(pgs.completions) as total_completions,
                SUM(pgs.throw_attempts) as total_throw_attempts,
                SUM(pgs.throwaways) as total_throwaways,
                SUM(pgs.blocks) as total_blocks,
                SUM(pgs.callahans) as total_callahans,
                SUM(pgs.drops) as total_drops,
                SUM(pgs.stalls) as total_stalls,
                CASE 
                    WHEN SUM(pgs.throw_attempts) > 0 
                    THEN CAST(SUM(pgs.completions) AS FLOAT) / SUM(pgs.throw_attempts) * 100
                    ELSE 0 
                END as completion_percentage
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.id
            WHERE g.year = :year
            GROUP BY pgs.player_id, pgs.team_id
            """

            # Handle both year (int) and season string formats
            year_param = (
                season if isinstance(season, int) else int(str(season).split("-")[0])
            )
            player_results = self.db.execute_query(
                player_stats_query, {"year": year_param}
            )

            # Clear existing season stats first
            self.db.execute_query(
                "DELETE FROM player_season_stats WHERE year = :year",
                {"year": year_param},
            )

            for row in player_results:
                try:
                    # Add year to the row data
                    row["year"] = year_param

                    # Insert new record
                    self.db.insert_data("player_season_stats", row)
                except Exception as e:
                    print(
                        f"Error calculating season stats for player {row.get('player_id')}: {e}"
                    )
                    continue
        except Exception as e:
            print(f"Error in calculate_season_stats: {e}")
            return

            # Calculate team season stats
            try:
                team_stats_query = """
                SELECT 
                    t.id as team_id,
                    COUNT(DISTINCT g.id) as games_played,
                    SUM(CASE 
                        WHEN (g.home_team_id = t.id AND g.home_score > g.away_score) 
                          OR (g.away_team_id = t.id AND g.away_score > g.home_score)
                        THEN 1 ELSE 0 
                    END) as wins,
                    SUM(CASE 
                        WHEN (g.home_team_id = t.id AND g.home_score < g.away_score) 
                          OR (g.away_team_id = t.id AND g.away_score < g.home_score)
                        THEN 1 ELSE 0 
                    END) as losses,
                    SUM(CASE 
                        WHEN g.home_team_id = t.id THEN g.home_score 
                        WHEN g.away_team_id = t.id THEN g.away_score 
                        ELSE 0 
                    END) as points_for,
                    SUM(CASE 
                        WHEN g.home_team_id = t.id THEN g.away_score 
                        WHEN g.away_team_id = t.id THEN g.home_score 
                        ELSE 0 
                    END) as points_against
                FROM teams t
                LEFT JOIN games g ON (g.home_team_id = t.id OR g.away_team_id = t.id) 
                                  AND g.year = :year
                GROUP BY t.id
                """

                team_results = self.db.execute_query(
                    team_stats_query, {"year": year_param}
                )

                # Clear existing team season stats first
                self.db.execute_query(
                    "DELETE FROM team_season_stats WHERE year = :year",
                    {"year": year_param},
                )

                for row in team_results:
                    try:
                        # Calculate derived stats
                        if row.get("games_played") and row["games_played"] > 0:
                            row["avg_points_for"] = (
                                row["points_for"] / row["games_played"]
                            )
                            row["avg_points_against"] = (
                                row["points_against"] / row["games_played"]
                            )
                            row["win_percentage"] = row["wins"] / row["games_played"]
                        else:
                            row["avg_points_for"] = 0
                            row["avg_points_against"] = 0
                            row["win_percentage"] = 0

                        # Add year to the row data
                        row["year"] = year_param

                        # Insert new record
                        self.db.insert_data("team_season_stats", row)
                    except Exception as e:
                        print(
                            f"Error calculating team season stats for team {row.get('team_id')}: {e}"
                        )
                        continue
            except Exception as e:
                print(f"Error in team season stats calculation: {e}")
                return

    def import_from_csv(self, csv_path: str, data_type: str) -> int:
        """
        Import data from a CSV file.

        Args:
            csv_path: Path to CSV file
            data_type: Type of data ('teams', 'players', 'games', 'stats')

        Returns:
            Number of records imported
        """
        df = pd.read_csv(csv_path)

        if data_type == "teams":
            teams_data = df.to_dict("records")
            return self.import_teams(teams_data)
        elif data_type == "players":
            players_data = df.to_dict("records")
            return self.import_players(players_data)
        elif data_type == "games":
            count = 0
            for _, row in df.iterrows():
                if self.import_game(row.to_dict()):
                    count += 1
            return count
        elif data_type == "stats":
            stats_data = df.to_dict("records")
            return self.import_player_game_stats(stats_data)
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def import_from_json(self, json_path: str) -> dict[str, int]:
        """
        Import data from a JSON file containing multiple data types.

        Args:
            json_path: Path to JSON file

        Returns:
            Dictionary with counts of imported records by type
        """
        with open(json_path) as f:
            data = json.load(f)

        results = {}

        if "teams" in data:
            results["teams"] = self.import_teams(data["teams"])

        if "players" in data:
            results["players"] = self.import_players(data["players"])

        if "games" in data:
            results["games"] = 0
            for game in data["games"]:
                if self.import_game(game):
                    results["games"] += 1

        if "player_stats" in data:
            results["player_stats"] = self.import_player_game_stats(
                data["player_stats"]
            )

        if "season" in data:
            self.calculate_season_stats(data["season"])
            results["season_stats_calculated"] = True

        return results
