"""
Stats processing module for data ingestion and transformation.
Handles importing sports statistics from various sources into the SQL database.
"""

import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import json
from sql_database import SQLDatabase
from models import Player, Team, Game, PlayerGameStats, PlayerSeasonStats, TeamSeasonStats


class StatsProcessor:
    """Processes and imports sports statistics data into the database."""
    
    def __init__(self, db: SQLDatabase = None):
        """
        Initialize the stats processor.
        
        Args:
            db: SQLDatabase instance. If None, creates a new one.
        """
        self.db = db or SQLDatabase()
    
    def import_teams(self, teams_data: List[Dict[str, Any]]) -> int:
        """
        Import team data into the database.
        
        Args:
            teams_data: List of team dictionaries
            
        Returns:
            Number of teams imported
        """
        count = 0
        for team_dict in teams_data:
            # Check if team already exists
            existing = self.db.execute_query(
                "SELECT id FROM teams WHERE name = :name",
                {"name": team_dict.get("name")}
            )
            
            if not existing:
                team = Team(**team_dict)
                team_data = team.dict(exclude_none=True, exclude={"id"})
                self.db.insert_data("teams", team_data)
                count += 1
        
        return count
    
    def import_players(self, players_data: List[Dict[str, Any]]) -> int:
        """
        Import player data into the database.
        
        Args:
            players_data: List of player dictionaries
            
        Returns:
            Number of players imported
        """
        count = 0
        for player_dict in players_data:
            # Check if player already exists
            existing = self.db.execute_query(
                "SELECT id FROM players WHERE name = :name",
                {"name": player_dict.get("name")}
            )
            
            if not existing:
                # Get team_id if team name is provided
                if "team_name" in player_dict:
                    team_result = self.db.execute_query(
                        "SELECT id FROM teams WHERE name = :name",
                        {"name": player_dict["team_name"]}
                    )
                    if team_result:
                        player_dict["team_id"] = team_result[0]["id"]
                    player_dict.pop("team_name", None)
                
                player = Player(**player_dict)
                player_data = player.dict(exclude_none=True, exclude={"id"})
                self.db.insert_data("players", player_data)
                count += 1
        
        return count
    
    def import_game(self, game_data: Dict[str, Any]) -> Optional[int]:
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
                {"name": game_data["home_team_name"]}
            )
            if home_team:
                game_data["home_team_id"] = home_team[0]["id"]
            game_data.pop("home_team_name", None)
        
        if "away_team_name" in game_data:
            away_team = self.db.execute_query(
                "SELECT id FROM teams WHERE name = :name OR abbreviation = :name",
                {"name": game_data["away_team_name"]}
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
                "away_team_id": game_data.get("away_team_id")
            }
        )
        
        if not existing:
            game = Game(**game_data)
            game_dict = game.dict(exclude_none=True, exclude={"id"})
            # Convert date to string for SQLite
            if isinstance(game_dict.get("game_date"), date):
                game_dict["game_date"] = game_dict["game_date"].isoformat()
            return self.db.insert_data("games", game_dict)
        
        return existing[0]["id"] if existing else None
    
    def import_player_game_stats(self, stats_data: List[Dict[str, Any]]) -> int:
        """
        Import player game statistics.
        
        Args:
            stats_data: List of player game stats dictionaries
            
        Returns:
            Number of stats records imported
        """
        count = 0
        for stat_dict in stats_data:
            # Convert player name to ID if needed
            if "player_name" in stat_dict:
                player = self.db.execute_query(
                    "SELECT id FROM players WHERE name = :name",
                    {"name": stat_dict["player_name"]}
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
                    "game_id": stat_dict.get("game_id")
                }
            )
            
            if not existing:
                stats = PlayerGameStats(**stat_dict)
                stats_data = stats.dict(exclude_none=True, exclude={"id"})
                self.db.insert_data("player_game_stats", stats_data)
                count += 1
        
        return count
    
    def calculate_season_stats(self, season: str):
        """
        Calculate and store aggregated season statistics for all players and teams.
        
        Args:
            season: Season identifier (e.g., "2023-24")
        """
        # Calculate player season stats
        player_stats_query = """
        SELECT 
            pgs.player_id,
            pgs.team_id,
            COUNT(DISTINCT pgs.game_id) as games_played,
            SUM(pgs.minutes_played) as total_minutes,
            SUM(pgs.points) as total_points,
            SUM(pgs.goals) as total_goals,
            SUM(pgs.assists) as total_assists,
            SUM(pgs.blocks) as total_blocks,
            SUM(pgs.steals) as total_steals,
            SUM(pgs.turnovers) as total_turnovers,
            SUM(pgs.total_rebounds) as total_rebounds,
            AVG(pgs.points) as avg_points_per_game,
            AVG(pgs.assists) as avg_assists_per_game,
            AVG(pgs.total_rebounds) as avg_rebounds_per_game,
            CASE 
                WHEN SUM(pgs.field_goals_attempted) > 0 
                THEN CAST(SUM(pgs.field_goals_made) AS FLOAT) / SUM(pgs.field_goals_attempted) * 100
                ELSE 0 
            END as field_goal_percentage,
            CASE 
                WHEN SUM(pgs.three_pointers_attempted) > 0 
                THEN CAST(SUM(pgs.three_pointers_made) AS FLOAT) / SUM(pgs.three_pointers_attempted) * 100
                ELSE 0 
            END as three_point_percentage,
            CASE 
                WHEN SUM(pgs.free_throws_attempted) > 0 
                THEN CAST(SUM(pgs.free_throws_made) AS FLOAT) / SUM(pgs.free_throws_attempted) * 100
                ELSE 0 
            END as free_throw_percentage
        FROM player_game_stats pgs
        JOIN games g ON pgs.game_id = g.id
        WHERE g.season = :season
        GROUP BY pgs.player_id, pgs.team_id
        """
        
        player_results = self.db.execute_query(player_stats_query, {"season": season})
        
        for row in player_results:
            # Check if season stats already exist
            existing = self.db.execute_query(
                """SELECT id FROM player_season_stats 
                   WHERE player_id = :player_id AND season = :season""",
                {"player_id": row["player_id"], "season": season}
            )
            
            if existing:
                # Update existing record
                update_query = """
                UPDATE player_season_stats 
                SET games_played = :games_played,
                    total_minutes = :total_minutes,
                    total_points = :total_points,
                    total_goals = :total_goals,
                    total_assists = :total_assists,
                    total_blocks = :total_blocks,
                    total_steals = :total_steals,
                    total_turnovers = :total_turnovers,
                    total_rebounds = :total_rebounds,
                    avg_points_per_game = :avg_points_per_game,
                    avg_assists_per_game = :avg_assists_per_game,
                    avg_rebounds_per_game = :avg_rebounds_per_game,
                    field_goal_percentage = :field_goal_percentage,
                    three_point_percentage = :three_point_percentage,
                    free_throw_percentage = :free_throw_percentage,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
                row["id"] = existing[0]["id"]
                self.db.execute_query(update_query, row)
            else:
                # Insert new record
                row["season"] = season
                self.db.insert_data("player_season_stats", row)
        
        # Calculate team season stats
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
                WHEN g.home_team_id = t.id AND g.home_score > g.away_score 
                THEN 1 ELSE 0 
            END) as home_wins,
            SUM(CASE 
                WHEN g.home_team_id = t.id AND g.home_score < g.away_score 
                THEN 1 ELSE 0 
            END) as home_losses,
            SUM(CASE 
                WHEN g.away_team_id = t.id AND g.away_score > g.home_score 
                THEN 1 ELSE 0 
            END) as away_wins,
            SUM(CASE 
                WHEN g.away_team_id = t.id AND g.away_score < g.home_score 
                THEN 1 ELSE 0 
            END) as away_losses,
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
                          AND g.season = :season
        GROUP BY t.id
        """
        
        team_results = self.db.execute_query(team_stats_query, {"season": season})
        
        for row in team_results:
            if row["games_played"] and row["games_played"] > 0:
                row["avg_points_for"] = row["points_for"] / row["games_played"]
                row["avg_points_against"] = row["points_against"] / row["games_played"]
                row["win_percentage"] = row["wins"] / row["games_played"]
            else:
                row["avg_points_for"] = 0
                row["avg_points_against"] = 0
                row["win_percentage"] = 0
            
            # Check if season stats already exist
            existing = self.db.execute_query(
                """SELECT id FROM team_season_stats 
                   WHERE team_id = :team_id AND season = :season""",
                {"team_id": row["team_id"], "season": season}
            )
            
            if existing:
                # Update existing record
                row["id"] = existing[0]["id"]
                update_cols = [f"{k} = :{k}" for k in row.keys() if k != "id"]
                update_query = f"""
                UPDATE team_season_stats 
                SET {', '.join(update_cols)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                """
                self.db.execute_query(update_query, row)
            else:
                # Insert new record
                row["season"] = season
                self.db.insert_data("team_season_stats", row)
    
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
            teams_data = df.to_dict('records')
            return self.import_teams(teams_data)
        elif data_type == "players":
            players_data = df.to_dict('records')
            return self.import_players(players_data)
        elif data_type == "games":
            count = 0
            for _, row in df.iterrows():
                if self.import_game(row.to_dict()):
                    count += 1
            return count
        elif data_type == "stats":
            stats_data = df.to_dict('records')
            return self.import_player_game_stats(stats_data)
        else:
            raise ValueError(f"Unknown data type: {data_type}")
    
    def import_from_json(self, json_path: str) -> Dict[str, int]:
        """
        Import data from a JSON file containing multiple data types.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Dictionary with counts of imported records by type
        """
        with open(json_path, 'r') as f:
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
            results["player_stats"] = self.import_player_game_stats(data["player_stats"])
        
        if "season" in data:
            self.calculate_season_stats(data["season"])
            results["season_stats_calculated"] = True
        
        return results