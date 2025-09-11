#!/usr/bin/env python3
"""
Unified Database Setup and Management Script.
This script handles database initialization, schema creation, and sample data loading.
"""

import json
import logging
import os
import random
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from config import config
from data.database import get_db
from data.processor import StatsProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseSetup:
    """Unified manager for database setup and initialization."""

    def __init__(self):
        self.db = get_db()
        self.stats_processor = StatsProcessor(self.db)
        self.root_dir = os.path.join(os.path.dirname(__file__), "..")
        self.data_dir = os.path.join(self.root_dir, "data")
        self.db_dir = os.path.join(self.root_dir, "db")
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure required directories exist."""
        for directory in [self.data_dir, self.db_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")

    def create_schema(self):
        """Create the complete database schema for sports statistics."""
        logger.info("Creating database schema...")

        schema_file = os.path.join(self.root_dir, "backend", "database_schema.sql")
        if os.path.exists(schema_file):
            with open(schema_file) as f:
                schema_sql = f.read()

            # Split and execute each statement
            statements = schema_sql.split(";")
            for statement in statements:
                statement = statement.strip()
                if statement:
                    try:
                        self.db.execute_query(statement)
                        logger.debug(f"Executed: {statement[:50]}...")
                    except Exception as e:
                        logger.warning(f"Schema statement failed: {e}")

            logger.info("Database schema created successfully")
        else:
            logger.warning(f"Schema file not found: {schema_file}")
            self._create_basic_schema()

    def _create_basic_schema(self):
        """Create a basic schema if the schema file is not found."""
        logger.info("Creating basic schema...")

        basic_schema = """
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id VARCHAR(50),
            name VARCHAR(100) NOT NULL,
            full_name VARCHAR(150),
            city VARCHAR(100),
            abbreviation VARCHAR(10),
            division VARCHAR(50),
            conference VARCHAR(50),
            year INTEGER,
            UNIQUE(team_id, year)
        );
        
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id VARCHAR(50),
            name VARCHAR(100) NOT NULL,
            team_id VARCHAR(50),
            position VARCHAR(20),
            jersey_number INTEGER,
            height INTEGER,
            weight INTEGER,
            year INTEGER,
            UNIQUE(player_id, year)
        );
        
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id VARCHAR(100),
            home_team_id VARCHAR(50),
            away_team_id VARCHAR(50),
            game_date VARCHAR(20),
            home_score INTEGER DEFAULT 0,
            away_score INTEGER DEFAULT 0,
            week VARCHAR(20),
            status VARCHAR(50),
            year INTEGER,
            UNIQUE(game_id)
        );
        
        CREATE TABLE IF NOT EXISTS player_game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id VARCHAR(50),
            game_id VARCHAR(100),
            team_id VARCHAR(50),
            goals INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            blocks INTEGER DEFAULT 0,
            turnovers INTEGER DEFAULT 0,
            catches INTEGER DEFAULT 0,
            completions INTEGER DEFAULT 0,
            throwaways INTEGER DEFAULT 0,
            drops INTEGER DEFAULT 0,
            stalls INTEGER DEFAULT 0,
            year INTEGER,
            UNIQUE(player_id, game_id)
        );
        
        CREATE TABLE IF NOT EXISTS player_season_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id VARCHAR(50),
            team_id VARCHAR(50),
            year INTEGER,
            games_played INTEGER DEFAULT 0,
            total_goals INTEGER DEFAULT 0,
            total_assists INTEGER DEFAULT 0,
            total_blocks INTEGER DEFAULT 0,
            total_turnovers INTEGER DEFAULT 0,
            avg_goals_per_game REAL DEFAULT 0.0,
            avg_assists_per_game REAL DEFAULT 0.0,
            UNIQUE(player_id, year)
        );
        
        CREATE TABLE IF NOT EXISTS team_season_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id VARCHAR(50),
            year INTEGER,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            goals_for INTEGER DEFAULT 0,
            goals_against INTEGER DEFAULT 0,
            goal_differential INTEGER DEFAULT 0,
            standing INTEGER,
            UNIQUE(team_id, year)
        );
        """

        statements = basic_schema.split(";")
        for statement in statements:
            statement = statement.strip()
            if statement:
                try:
                    self.db.execute_query(statement)
                except Exception as e:
                    logger.warning(f"Basic schema statement failed: {e}")

        logger.info("Basic schema created")

    def load_sample_data(self):
        """Load sample data from JSON file."""
        logger.info("Loading sample data...")

        sample_file = os.path.join(self.data_dir, "sample_stats.json")
        if not os.path.exists(sample_file):
            logger.info("Sample data file not found, generating synthetic data...")
            self.generate_synthetic_data()
            return

        try:
            with open(sample_file) as f:
                data = json.load(f)

            # Import using stats processor
            result = self.stats_processor.import_from_json(sample_file)
            logger.info(f"Sample data loaded: {result}")

        except Exception as e:
            logger.error(f"Failed to load sample data: {e}")
            logger.info("Generating synthetic data instead...")
            self.generate_synthetic_data()

    def generate_synthetic_data(self):
        """Generate synthetic sports data for testing."""
        logger.info("Generating synthetic Ultimate Frisbee data...")

        try:
            # Clear existing data
            tables = [
                "player_game_stats",
                "player_season_stats",
                "team_season_stats",
                "games",
                "players",
                "teams",
            ]
            for table in tables:
                self.db.execute_query(f"DELETE FROM {table}")

            # Generate teams
            teams_data = self._generate_teams()
            self._insert_teams(teams_data)

            # Generate players
            players_data = self._generate_players(teams_data)
            self._insert_players(players_data)

            # Generate games
            games_data = self._generate_games(teams_data)
            self._insert_games(games_data)

            # Generate player stats
            self._generate_player_stats(players_data, games_data)

            logger.info("Synthetic data generation complete")

        except Exception as e:
            logger.error(f"Failed to generate synthetic data: {e}")

    def _generate_teams(self):
        """Generate synthetic team data."""
        team_names = [
            ("New York", "Empire", "NYE"),
            ("San Francisco", "FlameThrowers", "SFF"),
            ("Chicago", "Machine", "CHM"),
            ("Boston", "Glory", "BGL"),
            ("Seattle", "Rainiers", "SEA"),
            ("Austin", "Sol", "AUS"),
            ("Philadelphia", "Phoenix", "PHI"),
            ("Los Angeles", "Aviators", "LAA"),
        ]

        teams = []
        for i, (city, name, abbr) in enumerate(team_names, 1):
            teams.append(
                {
                    "team_id": f"team_{i:02d}",
                    "name": name,
                    "full_name": f"{city} {name}",
                    "city": city,
                    "abbreviation": abbr,
                    "division": "East" if i <= 4 else "West",
                    "conference": "UFA",
                    "year": 2024,
                }
            )

        return teams

    def _generate_players(self, teams_data):
        """Generate synthetic player data."""
        first_names = [
            "Alex",
            "Jordan",
            "Taylor",
            "Sam",
            "Casey",
            "Morgan",
            "Avery",
            "Riley",
            "Blake",
            "Drew",
        ]
        last_names = [
            "Smith",
            "Johnson",
            "Williams",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
            "Rodriguez",
            "Martinez",
        ]
        positions = ["Handler", "Cutter", "Hybrid"]

        players = []
        player_id = 1

        for team in teams_data:
            # Generate 20 players per team
            for _ in range(20):
                name = f"{random.choice(first_names)} {random.choice(last_names)}"
                players.append(
                    {
                        "player_id": f"player_{player_id:03d}",
                        "name": name,
                        "team_id": team["team_id"],
                        "position": random.choice(positions),
                        "jersey_number": random.randint(1, 99),
                        "height": random.randint(64, 78),  # inches
                        "weight": random.randint(140, 220),  # pounds
                        "year": 2024,
                    }
                )
                player_id += 1

        return players

    def _generate_games(self, teams_data):
        """Generate synthetic game data."""
        games = []
        game_id = 1

        # Generate regular season games (each team plays others once)
        for i, home_team in enumerate(teams_data):
            for j, away_team in enumerate(teams_data):
                if i != j:  # Don't play against themselves
                    # Generate game date
                    base_date = datetime(2024, 4, 1)
                    game_date = base_date + timedelta(days=random.randint(0, 120))

                    # Generate scores
                    home_score = random.randint(10, 20)
                    away_score = random.randint(10, 20)

                    games.append(
                        {
                            "game_id": f"game_{game_id:03d}",
                            "home_team_id": home_team["team_id"],
                            "away_team_id": away_team["team_id"],
                            "game_date": game_date.strftime("%Y-%m-%d"),
                            "home_score": home_score,
                            "away_score": away_score,
                            "week": f"Week {(game_id - 1) // 4 + 1}",
                            "status": "Final",
                            "year": 2024,
                        }
                    )
                    game_id += 1

        return games

    def _insert_teams(self, teams_data):
        """Insert team data into database."""
        for team in teams_data:
            self.db.execute_query(
                """
                INSERT INTO teams (team_id, name, full_name, city, abbreviation, division, conference, year)
                VALUES (:team_id, :name, :full_name, :city, :abbreviation, :division, :conference, :year)
            """,
                team,
            )
        logger.info(f"Inserted {len(teams_data)} teams")

    def _insert_players(self, players_data):
        """Insert player data into database."""
        for player in players_data:
            self.db.execute_query(
                """
                INSERT INTO players (player_id, name, team_id, position, jersey_number, height, weight, year)
                VALUES (:player_id, :name, :team_id, :position, :jersey_number, :height, :weight, :year)
            """,
                player,
            )
        logger.info(f"Inserted {len(players_data)} players")

    def _insert_games(self, games_data):
        """Insert game data into database."""
        for game in games_data:
            self.db.execute_query(
                """
                INSERT INTO games (game_id, home_team_id, away_team_id, game_date, home_score, away_score, week, status, year)
                VALUES (:game_id, :home_team_id, :away_team_id, :game_date, :home_score, :away_score, :week, :status, :year)
            """,
                game,
            )
        logger.info(f"Inserted {len(games_data)} games")

    def _generate_player_stats(self, players_data, games_data):
        """Generate synthetic player game statistics."""
        stats_count = 0

        for game in games_data:
            # Get players for both teams
            home_players = [
                p for p in players_data if p["team_id"] == game["home_team_id"]
            ]
            away_players = [
                p for p in players_data if p["team_id"] == game["away_team_id"]
            ]

            # Generate stats for 7-14 players per team per game
            for team_players in [home_players, away_players]:
                playing_count = random.randint(7, 14)
                playing_players = random.sample(
                    team_players, min(playing_count, len(team_players))
                )

                for player in playing_players:
                    stats = {
                        "player_id": player["player_id"],
                        "game_id": game["game_id"],
                        "team_id": player["team_id"],
                        "goals": random.randint(0, 5),
                        "assists": random.randint(0, 4),
                        "blocks": random.randint(0, 3),
                        "turnovers": random.randint(0, 4),
                        "catches": random.randint(5, 25),
                        "completions": random.randint(3, 20),
                        "throwaways": random.randint(0, 3),
                        "drops": random.randint(0, 2),
                        "stalls": random.randint(0, 2),
                        "year": 2024,
                    }

                    self.db.execute_query(
                        """
                        INSERT INTO player_game_stats 
                        (player_id, game_id, team_id, goals, assists, blocks, turnovers, 
                         catches, completions, throwaways, drops, stalls, year)
                        VALUES (:player_id, :game_id, :team_id, :goals, :assists, :blocks, :turnovers,
                                :catches, :completions, :throwaways, :drops, :stalls, :year)
                    """,
                        stats,
                    )
                    stats_count += 1

        logger.info(f"Generated {stats_count} player game statistics")

    def get_database_info(self):
        """Get information about the current database."""
        logger.info("Database information:")

        tables = [
            "teams",
            "players",
            "games",
            "player_game_stats",
            "player_season_stats",
            "team_season_stats",
        ]
        for table in tables:
            try:
                count = self.db.get_row_count(table)
                logger.info(f"  {table}: {count} rows")
            except Exception as e:
                logger.info(f"  {table}: Error - {e}")

    def reset_database(self):
        """Complete database reset - recreate schema and load sample data."""
        logger.info("Performing complete database reset...")

        # Delete the database file if it exists
        db_path = config.DATABASE_PATH
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"Deleted existing database: {db_path}")

        # Recreate database connection
        self.db = get_db()

        # Create schema and load data
        self.create_schema()
        self.load_sample_data()
        self.get_database_info()

        logger.info("Database reset complete")


def main():
    """Main function to run database operations based on command line arguments."""
    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  python database_setup.py init          # Initialize database with schema"
        )
        print("  python database_setup.py load-sample   # Load sample data")
        print("  python database_setup.py generate      # Generate synthetic data")
        print("  python database_setup.py info          # Show database info")
        print("  python database_setup.py reset         # Complete reset")
        sys.exit(1)

    setup = DatabaseSetup()
    command = sys.argv[1]

    try:
        if command == "init":
            setup.create_schema()
            setup.get_database_info()

        elif command == "load-sample":
            setup.load_sample_data()
            setup.get_database_info()

        elif command == "generate":
            setup.generate_synthetic_data()
            setup.get_database_info()

        elif command == "info":
            setup.get_database_info()

        elif command == "reset":
            setup.reset_database()

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
