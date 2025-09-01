#!/usr/bin/env python3
"""
Database setup script for Sports Statistics Chat System.
Creates the database, initializes tables, and loads sample data.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

import json
import random
from datetime import datetime, timedelta

from sql_database import SQLDatabase
from stats_processor import StatsProcessor


def create_sample_data():
    """Create sample sports data for testing."""

    # Sample teams
    teams = [
        {
            "name": "Los Angeles Lakers",
            "city": "Los Angeles",
            "abbreviation": "LAL",
            "division": "Pacific",
            "conference": "Western",
        },
        {
            "name": "Boston Celtics",
            "city": "Boston",
            "abbreviation": "BOS",
            "division": "Atlantic",
            "conference": "Eastern",
        },
        {
            "name": "Golden State Warriors",
            "city": "San Francisco",
            "abbreviation": "GSW",
            "division": "Pacific",
            "conference": "Western",
        },
        {
            "name": "Miami Heat",
            "city": "Miami",
            "abbreviation": "MIA",
            "division": "Southeast",
            "conference": "Eastern",
        },
        {
            "name": "Milwaukee Bucks",
            "city": "Milwaukee",
            "abbreviation": "MIL",
            "division": "Central",
            "conference": "Eastern",
        },
        {
            "name": "Phoenix Suns",
            "city": "Phoenix",
            "abbreviation": "PHX",
            "division": "Pacific",
            "conference": "Western",
        },
        {
            "name": "Philadelphia 76ers",
            "city": "Philadelphia",
            "abbreviation": "PHI",
            "division": "Atlantic",
            "conference": "Eastern",
        },
        {
            "name": "Dallas Mavericks",
            "city": "Dallas",
            "abbreviation": "DAL",
            "division": "Southwest",
            "conference": "Western",
        },
        {
            "name": "Denver Nuggets",
            "city": "Denver",
            "abbreviation": "DEN",
            "division": "Northwest",
            "conference": "Western",
        },
        {
            "name": "Brooklyn Nets",
            "city": "Brooklyn",
            "abbreviation": "BKN",
            "division": "Atlantic",
            "conference": "Eastern",
        },
    ]

    # Sample players
    players = [
        {
            "name": "LeBron James",
            "first_name": "LeBron",
            "last_name": "James",
            "team_name": "Los Angeles Lakers",
            "position": "Forward",
            "jersey_number": 23,
            "height": "6-9",
            "weight": 250,
            "years_pro": 21,
        },
        {
            "name": "Stephen Curry",
            "first_name": "Stephen",
            "last_name": "Curry",
            "team_name": "Golden State Warriors",
            "position": "Guard",
            "jersey_number": 30,
            "height": "6-2",
            "weight": 185,
            "years_pro": 15,
        },
        {
            "name": "Kevin Durant",
            "first_name": "Kevin",
            "last_name": "Durant",
            "team_name": "Phoenix Suns",
            "position": "Forward",
            "jersey_number": 35,
            "height": "6-10",
            "weight": 240,
            "years_pro": 16,
        },
        {
            "name": "Giannis Antetokounmpo",
            "first_name": "Giannis",
            "last_name": "Antetokounmpo",
            "team_name": "Milwaukee Bucks",
            "position": "Forward",
            "jersey_number": 34,
            "height": "6-11",
            "weight": 242,
            "years_pro": 11,
        },
        {
            "name": "Jayson Tatum",
            "first_name": "Jayson",
            "last_name": "Tatum",
            "team_name": "Boston Celtics",
            "position": "Forward",
            "jersey_number": 0,
            "height": "6-8",
            "weight": 210,
            "years_pro": 7,
        },
        {
            "name": "Luka Doncic",
            "first_name": "Luka",
            "last_name": "Doncic",
            "team_name": "Dallas Mavericks",
            "position": "Guard",
            "jersey_number": 77,
            "height": "6-7",
            "weight": 230,
            "years_pro": 6,
        },
        {
            "name": "Joel Embiid",
            "first_name": "Joel",
            "last_name": "Embiid",
            "team_name": "Philadelphia 76ers",
            "position": "Center",
            "jersey_number": 21,
            "height": "7-0",
            "weight": 280,
            "years_pro": 8,
        },
        {
            "name": "Nikola Jokic",
            "first_name": "Nikola",
            "last_name": "Jokic",
            "team_name": "Denver Nuggets",
            "position": "Center",
            "jersey_number": 15,
            "height": "6-11",
            "weight": 284,
            "years_pro": 9,
        },
        {
            "name": "Jimmy Butler",
            "first_name": "Jimmy",
            "last_name": "Butler",
            "team_name": "Miami Heat",
            "position": "Forward",
            "jersey_number": 22,
            "height": "6-7",
            "weight": 230,
            "years_pro": 13,
        },
        {
            "name": "Damian Lillard",
            "first_name": "Damian",
            "last_name": "Lillard",
            "team_name": "Milwaukee Bucks",
            "position": "Guard",
            "jersey_number": 0,
            "height": "6-2",
            "weight": 195,
            "years_pro": 12,
        },
        {
            "name": "Anthony Davis",
            "first_name": "Anthony",
            "last_name": "Davis",
            "team_name": "Los Angeles Lakers",
            "position": "Forward-Center",
            "jersey_number": 3,
            "height": "6-10",
            "weight": 253,
            "years_pro": 12,
        },
        {
            "name": "Kawhi Leonard",
            "first_name": "Kawhi",
            "last_name": "Leonard",
            "team_name": "Los Angeles Lakers",
            "position": "Forward",
            "jersey_number": 2,
            "height": "6-7",
            "weight": 225,
            "years_pro": 12,
        },
        {
            "name": "Devin Booker",
            "first_name": "Devin",
            "last_name": "Booker",
            "team_name": "Phoenix Suns",
            "position": "Guard",
            "jersey_number": 1,
            "height": "6-5",
            "weight": 206,
            "years_pro": 9,
        },
        {
            "name": "Kyrie Irving",
            "first_name": "Kyrie",
            "last_name": "Irving",
            "team_name": "Dallas Mavericks",
            "position": "Guard",
            "jersey_number": 11,
            "height": "6-2",
            "weight": 195,
            "years_pro": 13,
        },
        {
            "name": "Paul George",
            "first_name": "Paul",
            "last_name": "George",
            "team_name": "Philadelphia 76ers",
            "position": "Forward",
            "jersey_number": 13,
            "height": "6-8",
            "weight": 220,
            "years_pro": 14,
        },
    ]

    # Generate some sample games
    season = "2023-24"
    games = []
    player_stats = []

    # Create 20 sample games
    base_date = datetime(2024, 1, 1)
    game_id = 1

    for i in range(20):
        game_date = base_date + timedelta(days=i * 2)

        # Pick two random teams
        team_indices = random.sample(range(len(teams)), 2)
        home_team = teams[team_indices[0]]["name"]
        away_team = teams[team_indices[1]]["name"]

        home_score = random.randint(95, 130)
        away_score = random.randint(95, 130)

        games.append(
            {
                "game_date": game_date.date().isoformat(),
                "season": season,
                "game_type": "regular",
                "home_team_name": home_team,
                "away_team_name": away_team,
                "home_score": home_score,
                "away_score": away_score,
                "overtime": abs(home_score - away_score) <= 5 and random.random() > 0.7,
                "attendance": random.randint(15000, 20000),
                "venue": f"{home_team} Arena",
            }
        )

        # Generate player stats for this game
        # Get players from both teams
        home_players = [p for p in players if p["team_name"] == home_team]
        away_players = [p for p in players if p["team_name"] == away_team]

        for player in (
            home_players[:5] + away_players[:5]
        ):  # Top 5 players from each team
            stats = {
                "player_name": player["name"],
                "game_id": game_id,
                "team_id": 1,  # Will be replaced with actual ID
                "minutes_played": random.randint(20, 38),
                "points": random.randint(8, 35),
                "goals": random.randint(0, 12),
                "assists": random.randint(1, 12),
                "blocks": random.randint(0, 3),
                "steals": random.randint(0, 3),
                "turnovers": random.randint(0, 5),
                "field_goals_made": random.randint(3, 12),
                "field_goals_attempted": random.randint(8, 22),
                "three_pointers_made": random.randint(0, 6),
                "three_pointers_attempted": random.randint(0, 10),
                "free_throws_made": random.randint(0, 8),
                "free_throws_attempted": random.randint(0, 10),
                "offensive_rebounds": random.randint(0, 3),
                "defensive_rebounds": random.randint(1, 8),
                "total_rebounds": 0,  # Will calculate
                "personal_fouls": random.randint(0, 5),
            }
            stats["total_rebounds"] = (
                stats["offensive_rebounds"] + stats["defensive_rebounds"]
            )
            stats["plus_minus"] = random.randint(-15, 15)

            player_stats.append(stats)

        game_id += 1

    return {
        "teams": teams,
        "players": players,
        "games": games,
        "player_stats": player_stats,
        "season": season,
    }


def setup_database():
    """Set up the database with schema and sample data."""
    print("Setting up Sports Statistics Database...")

    # Initialize database connection
    db = SQLDatabase()
    processor = StatsProcessor(db)

    # The schema is automatically created by SQLDatabase initialization
    print("✓ Database schema created")

    # Create sample data
    print("Creating sample data...")
    sample_data = create_sample_data()

    # Import teams
    print(f"Importing {len(sample_data['teams'])} teams...")
    teams_imported = processor.import_teams(sample_data["teams"])
    print(f"✓ Imported {teams_imported} teams")

    # Import players
    print(f"Importing {len(sample_data['players'])} players...")
    players_imported = processor.import_players(sample_data["players"])
    print(f"✓ Imported {players_imported} players")

    # Import games
    print(f"Importing {len(sample_data['games'])} games...")
    games_imported = 0
    for game in sample_data["games"]:
        if processor.import_game(game):
            games_imported += 1
    print(f"✓ Imported {games_imported} games")

    # Import player stats
    print(f"Importing {len(sample_data['player_stats'])} player game stats...")
    stats_imported = processor.import_player_game_stats(sample_data["player_stats"])
    print(f"✓ Imported {stats_imported} player game stats")

    # Calculate season statistics
    print(f"Calculating season statistics for {sample_data['season']}...")
    processor.calculate_season_stats(sample_data["season"])
    print("✓ Season statistics calculated")

    # Verify the setup
    print("\nDatabase setup complete! Summary:")
    print(f"- Teams: {db.get_row_count('teams')}")
    print(f"- Players: {db.get_row_count('players')}")
    print(f"- Games: {db.get_row_count('games')}")
    print(f"- Player Game Stats: {db.get_row_count('player_game_stats')}")
    print(f"- Player Season Stats: {db.get_row_count('player_season_stats')}")
    print(f"- Team Season Stats: {db.get_row_count('team_season_stats')}")

    # Save sample data to JSON for reference
    sample_data_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "sample_stats.json"
    )
    os.makedirs(os.path.dirname(sample_data_path), exist_ok=True)

    with open(sample_data_path, "w") as f:
        # Convert date objects to strings for JSON serialization
        json_data = sample_data.copy()
        json.dump(json_data, f, indent=2, default=str)
    print(f"\n✓ Sample data saved to {sample_data_path}")

    db.close()
    print("\n✅ Database setup completed successfully!")


if __name__ == "__main__":
    setup_database()
