"""
Point builder for managing point state and construction.
"""

import json
from typing import Any


class PointBuilder:
    """Builds and manages point state during play-by-play processing."""

    def __init__(self):
        """Initialize the point builder."""
        self.current_score = {"home": 0, "away": 0}
        self.quarter = 1
        self.quarter_offset = 0
        self.point_number = 0

    def create_point(
        self, event: dict, team: str, player_lookup: dict[str, dict[str, str]]
    ) -> dict[str, Any]:
        """
        Create a new point from a pull event.

        Args:
            event: Pull event data
            team: Team ('home' or 'away')
            player_lookup: Player lookup dictionary

        Returns:
            New point dictionary
        """
        self.point_number += 1
        event_type = event["event_type"]

        point_start_time = (
            (self.quarter_offset + event["event_time"])
            if event["event_time"] is not None
            else self.quarter_offset
        )

        # Determine line type and who pulls/receives
        if team == "home":
            if event_type == 1:  # Home pulls (D-point)
                line_type = "D-Line"
                pulling_team = "home"
                receiving_team = "away"
            else:  # Home receives (O-point)
                line_type = "O-Line"
                pulling_team = "away"
                receiving_team = "home"
        else:  # team == "away"
            if event_type == 1:  # Away pulls (D-point)
                line_type = "D-Line"
                pulling_team = "away"
                receiving_team = "home"
            else:  # Away receives (O-point)
                line_type = "O-Line"
                pulling_team = "home"
                receiving_team = "away"

        # Get line players
        line_players = self._get_line_players(event, player_lookup)

        return {
            "point_number": self.point_number,
            "quarter": self.quarter,
            "score": f"{self.current_score['away']}-{self.current_score['home']}",
            "home_score": self.current_score["home"],
            "away_score": self.current_score["away"],
            "team": team,
            "line_type": line_type,
            "start_time": point_start_time,
            "end_time": None,
            "duration_seconds": 0,
            "players": line_players,
            "pulling_team": pulling_team,
            "receiving_team": receiving_team,
            "scoring_team": None,
        }

    def _get_line_players(
        self, event: dict, player_lookup: dict[str, dict[str, str]]
    ) -> list[str]:
        """
        Extract line players from event data.

        Args:
            event: Event data with line_players field
            player_lookup: Player lookup dictionary

        Returns:
            List of player last names
        """
        line_players = []
        if event.get("line_players"):
            try:
                player_ids = json.loads(event["line_players"])
                if player_ids and len(player_ids) > 0:
                    line_players = [
                        player_lookup[pid]["last_name"]
                        for pid in player_ids
                        if pid in player_lookup and player_lookup[pid].get("last_name")
                    ]
            except Exception as e:
                print(f"Error parsing line players: {e}")

        return line_players

    def update_score_for_goal(self, team: str, current_point: dict | None) -> None:
        """
        Update score when a goal is scored.

        Args:
            team: Team that scored
            current_point: Current point being built
        """
        if team == "home":
            self.current_score["home"] += 1
        else:
            self.current_score["away"] += 1

        if current_point:
            current_point["scoring_team"] = team
            current_point["score"] = (
                f"{self.current_score['away']}-{self.current_score['home']}"
            )
            current_point["home_score"] = self.current_score["home"]
            current_point["away_score"] = self.current_score["away"]

    def update_score_for_opponent_goal(
        self, team: str, current_point: dict | None
    ) -> str:
        """
        Update score when opponent scores.

        Args:
            team: Team processing the event (not the one that scored)
            current_point: Current point being built

        Returns:
            Team that scored
        """
        if team == "home":
            self.current_score["away"] += 1
            scoring_team = "away"
        else:
            self.current_score["home"] += 1
            scoring_team = "home"

        if current_point:
            current_point["scoring_team"] = scoring_team
            current_point["score"] = (
                f"{self.current_score['away']}-{self.current_score['home']}"
            )
            current_point["home_score"] = self.current_score["home"]
            current_point["away_score"] = self.current_score["away"]

        return scoring_team

    def finalize_point(
        self, current_point: dict, end_time: int | None = None
    ) -> None:
        """
        Finalize a point with end time and duration.

        Args:
            current_point: Point to finalize
            end_time: End time in seconds (None to use default)
        """
        if end_time is not None:
            current_point["end_time"] = end_time
            if current_point["start_time"] is not None:
                current_point["duration_seconds"] = max(
                    0, end_time - current_point["start_time"]
                )
        elif not current_point.get("end_time"):
            # Default to 90 seconds if no end time provided
            if current_point["start_time"] is not None:
                current_point["end_time"] = current_point["start_time"] + 90
                current_point["duration_seconds"] = 90
            else:
                current_point["duration_seconds"] = 0

    def update_quarter(self, event_type: int) -> None:
        """
        Update quarter and offset based on quarter-end event.

        Args:
            event_type: Event type (28=Q1, 29=Half, 30=Q3, 31=Regulation)
        """
        if event_type == 28:  # End of Q1
            self.quarter = 2
            self.quarter_offset = 720
        elif event_type == 29:  # Halftime
            self.quarter = 3
            self.quarter_offset = 1440
        elif event_type == 30:  # End of Q3
            self.quarter = 4
            self.quarter_offset = 2160

    def get_quarter_end_time(self, event_type: int) -> int | None:
        """
        Get the end time for a quarter-end event.

        Args:
            event_type: Event type (28-31)

        Returns:
            Quarter end time in seconds, or None
        """
        if event_type == 28:  # End of Q1
            return 720
        elif event_type == 29:  # Halftime
            return 1440
        elif event_type == 30:  # End of Q3
            return 2160
        elif event_type == 31:  # End of regulation
            return 2880
        return None

    @staticmethod
    def format_point_times(points: list[dict[str, Any]]) -> None:
        """
        Add formatted time and duration to each point.

        Args:
            points: List of points to format (modified in place)
        """
        for point in points:
            # Format duration
            minutes = (
                point["duration_seconds"] // 60 if point["duration_seconds"] else 0
            )
            seconds = point["duration_seconds"] % 60 if point["duration_seconds"] else 0

            if minutes > 0:
                point["duration"] = f"{minutes}m{seconds:02d}s"
            else:
                point["duration"] = f"{seconds}s"

            # Format time remaining
            if point["end_time"] is not None:
                quarter = point["quarter"]
                time_in_quarter = point["end_time"] - ((quarter - 1) * 720)
                time_remaining = 720 - time_in_quarter

                if time_remaining >= 0:
                    mins = int(time_remaining // 60)
                    secs = int(time_remaining % 60)
                    point["time"] = f"{mins:02d}:{secs:02d}"
                else:
                    point["time"] = "00:00"
            else:
                point["time"] = "00:00"
