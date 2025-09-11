#!/usr/bin/env python3
"""
Game Events Verification Tool.
Extracts and formats game events to match the UFA website display.
"""

import json
import os
import sys
from typing import Any, Dict, List, Tuple

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from backend.data.database import get_db


class GameEventsVerifier:
    """Tool to extract and format game events from the database."""

    def __init__(self):
        self.db = get_db()

        # Event type mappings from UFA API documentation
        self.event_types = {
            1: "Start D Point",
            2: "Start O Point",
            7: "Pull (inbounds)",
            8: "Pull (out of bounds)",
            11: "Block",
            12: "Callahan (thrown by opposing team)",
            13: "Throwaway (thrown by opposing team)",
            18: "Pass",
            19: "Goal",
            20: "Drop",
            22: "Throwaway (thrown by recording team)",
            # Add more as needed
        }

        # Event icons for display
        self.event_icons = {
            7: "➡",  # Pull
            8: "➡",  # Pull OB
            11: "🛡",  # Block
            18: "↗",  # Pass
            19: "⚽",  # Goal
            20: "❌",  # Drop
            22: "❌",  # Throwaway
            13: "❌",  # Throwaway by opposing team
        }

    def get_game_info(self, game_id: str) -> Dict[str, Any]:
        """Get basic game information."""
        query = """
        SELECT g.game_id, g.start_timestamp, g.home_score, g.away_score,
               ht.name as home_team, ht.team_id as home_team_id,
               at.name as away_team, at.team_id as away_team_id
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
        JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
        WHERE g.game_id = :game_id
        """
        result = self.db.execute_query(query, {"game_id": game_id})
        if result:
            row = result[0]  # First row
            return {
                "game_id": row["game_id"],
                "start_timestamp": row["start_timestamp"],
                "home_score": row["home_score"],
                "away_score": row["away_score"],
                "home_team": row["home_team"],
                "home_team_id": row["home_team_id"],
                "away_team": row["away_team"],
                "away_team_id": row["away_team_id"],
            }
        return None

    def get_player_name(self, player_id: str, team_id: str = None) -> str:
        """Get player's full name from player ID."""
        if not player_id:
            return ""

        query = """
        SELECT full_name FROM players 
        WHERE player_id = :player_id AND (team_id = :team_id OR :team_id IS NULL)
        LIMIT 1
        """
        result = self.db.execute_query(
            query, {"player_id": player_id, "team_id": team_id}
        )
        if result:
            row = result[0]
            return row["full_name"] or ""
        return player_id  # Fallback to ID if name not found

    def get_game_events(self, game_id: str, team: str = None) -> List[Dict[str, Any]]:
        """Get all game events for a specific game and optionally a specific team."""
        query = """
        SELECT event_index, team, event_type, event_time,
               thrower_id, receiver_id, defender_id, puller_id,
               thrower_x, thrower_y, receiver_x, receiver_y,
               turnover_x, turnover_y, pull_x, pull_y, pull_ms,
               line_players
        FROM game_events
        WHERE game_id = :game_id {}
        ORDER BY event_index, team
        """.format(
            "AND team = :team" if team else ""
        )

        params = {"game_id": game_id, "team": team} if team else {"game_id": game_id}
        result = self.db.execute_query(query, params)

        events = []
        for row in result:
            event = {
                "event_index": row["event_index"],
                "team": row["team"],
                "event_type": row["event_type"],
                "event_time": row["event_time"],
                "thrower_id": row["thrower_id"],
                "receiver_id": row["receiver_id"],
                "defender_id": row["defender_id"],
                "puller_id": row["puller_id"],
                "thrower_x": row["thrower_x"],
                "thrower_y": row["thrower_y"],
                "receiver_x": row["receiver_x"],
                "receiver_y": row["receiver_y"],
                "turnover_x": row["turnover_x"],
                "turnover_y": row["turnover_y"],
                "pull_x": row["pull_x"],
                "pull_y": row["pull_y"],
                "pull_ms": row["pull_ms"],
                "line_players": (
                    json.loads(row["line_players"]) if row["line_players"] else []
                ),
            }
            events.append(event)

        return events

    def extract_first_point(self, game_id: str) -> Tuple[List[Dict], List[Dict]]:
        """Extract the first point events from both team perspectives."""
        home_events = self.get_game_events(game_id, "home")
        away_events = self.get_game_events(game_id, "away")

        # Find the first point (from start to first goal)
        first_point_home = []
        first_point_away = []

        goal_found = False
        for event in home_events:
            first_point_home.append(event)
            if event["event_type"] == 19:  # Goal
                goal_found = True
                break

        goal_found = False
        for event in away_events:
            first_point_away.append(event)
            if event["event_type"] == 19:  # Goal
                goal_found = True
                break

        return first_point_home, first_point_away

    def format_yard_line(self, y_coord: float) -> str:
        """Convert Y coordinate to yard line description."""
        if y_coord is None:
            return ""

        # Field is 0-120 yards (including 20-yard endzones on each end)
        if y_coord < 20:
            return f"{int(20-y_coord)}y"  # South endzone
        elif y_coord > 100:
            return f"{int(y_coord-100)}y"  # North endzone
        else:
            return f"{int(y_coord)}y"  # Midfield area

    def format_event_description(
        self, event: Dict[str, Any], game_info: Dict[str, Any]
    ) -> str:
        """Format an event into a human-readable description."""
        event_type = event["event_type"]

        if event_type == 7:  # Pull inbounds
            puller = self.get_player_name(event["puller_id"])
            return f"Pull by {puller}"

        elif event_type == 11:  # Block
            defender = self.get_player_name(event["defender_id"])
            return f"Block by {defender}"

        elif event_type == 18:  # Pass
            thrower = self.get_player_name(event["thrower_id"])
            receiver = self.get_player_name(event["receiver_id"])
            return f"Pass from {thrower} to {receiver}"

        elif event_type == 19:  # Goal
            thrower = self.get_player_name(event["thrower_id"])
            receiver = self.get_player_name(event["receiver_id"])
            return f"Score from {thrower} to {receiver}"

        elif event_type == 20:  # Drop
            thrower = self.get_player_name(event["thrower_id"])
            receiver = self.get_player_name(event["receiver_id"])
            return f"Drop from {thrower} to {receiver}"

        elif event_type == 22:  # Throwaway
            thrower = self.get_player_name(event["thrower_id"])
            return (
                f"Huck throwaway from {thrower}"
                if event.get("thrower_y", 0) > 50
                else f"Throwaway from {thrower}"
            )

        elif event_type == 13:  # Throwaway by opposing team
            return (
                f"They scored"
                if event.get("thrower_y", 0) > 50
                else "Throwaway by opposing team"
            )

        elif event_type in [1, 2]:  # Start D/O Point
            line_players = event.get("line_players", [])
            player_names = [
                self.get_player_name(pid) for pid in line_players[:6]
            ]  # Show first 6
            line_type = "O-Line" if event_type == 2 else "D-Line"
            return f"{line_type}: {', '.join(player_names)}"

        else:
            return f"Event type {event_type}"

    def display_first_point_ufa_style(self, game_id: str):
        """Display the first point in UFA website style."""
        game_info = self.get_game_info(game_id)
        if not game_info:
            print(f"Game {game_id} not found")
            return

        home_events, away_events = self.extract_first_point(game_id)

        print(f"Game: {game_info['away_team']} @ {game_info['home_team']}")
        print(f"Final Score: {game_info['away_score']}-{game_info['home_score']}")
        print("=" * 80)

        # Display Away Team Perspective (like MIN in the screenshot)
        print(f"\n{game_info['away_team']} Perspective:")
        print("-" * 40)

        current_score = "0-0"
        for i, event in enumerate(away_events):
            icon = self.event_icons.get(event["event_type"], "•")
            yard_line = self.format_yard_line(
                event.get("receiver_y") or event.get("thrower_y")
            )
            description = self.format_event_description(event, game_info)

            # Add score and line info for first event
            if i == 0 and event["event_type"] in [1, 2]:
                line_type = "O-Line" if event["event_type"] == 2 else "D-Line"
                time_str = (
                    f"{event.get('event_time', 0)}s" if event.get("event_time") else ""
                )
                print(f"▼ {current_score}  {line_type}  {time_str}")
                print(f"    {description}")
            else:
                time_info = (
                    f"{event.get('event_time', '')}s" if event.get("event_time") else ""
                )
                print(f"{icon}  {yard_line}  {description}")

        # Display Home Team Perspective (like BOS in the screenshot)
        print(f"\n{game_info['home_team']} Perspective:")
        print("-" * 40)

        current_score = "0-0"
        for i, event in enumerate(home_events):
            icon = self.event_icons.get(event["event_type"], "•")
            yard_line = self.format_yard_line(
                event.get("receiver_y") or event.get("thrower_y")
            )
            description = self.format_event_description(event, game_info)

            # Add score and line info for first event
            if i == 0 and event["event_type"] in [1, 2]:
                line_type = "O-Line" if event["event_type"] == 2 else "D-Line"
                time_str = (
                    f"{event.get('event_time', 0)}s" if event.get("event_time") else ""
                )
                print(f"▼ {current_score}  {line_type}  {time_str}")
                print(f"    {description}")
            else:
                time_info = (
                    f"{event.get('event_time', '')}s" if event.get("event_time") else ""
                )
                print(f"{icon}  {yard_line}  {description}")


def main():
    """Main function to demonstrate game events verification."""
    if len(sys.argv) < 2:
        print("Usage: python game_events_verifier.py <game_id>")
        print("Example: python game_events_verifier.py 2025-08-23-BOS-MIN")
        sys.exit(1)

    game_id = sys.argv[1]
    verifier = GameEventsVerifier()
    verifier.display_first_point_ufa_style(game_id)


if __name__ == "__main__":
    main()
