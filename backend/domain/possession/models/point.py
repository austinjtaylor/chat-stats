"""
Data models for possession tracking in Ultimate Frisbee.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Point:
    """
    Represents a single point in an Ultimate Frisbee game.

    A point runs from pull to goal, tracking which team pulls, receives,
    and scores, as well as possession changes during the point.
    """

    pulling_team: str  # 'home' or 'away'
    receiving_team: str  # 'home' or 'away'
    scoring_team: Optional[str] = None  # 'home', 'away', or None
    team_possessions: int = 0
    opponent_possessions: int = 0

    def is_o_line_point(self, team_type: str) -> bool:
        """Check if this is an O-line point for the given team."""
        return self.receiving_team == team_type

    def is_d_line_point(self, team_type: str) -> bool:
        """Check if this is a D-line point for the given team."""
        return self.pulling_team == team_type

    def did_team_score(self, team_type: str) -> bool:
        """Check if the given team scored this point."""
        return self.scoring_team == team_type


@dataclass
class RedzonePossession:
    """
    Represents a single possession for redzone tracking.

    Tracks whether a team reached the redzone (80-100 yards) and scored
    during a possession.
    """

    point: int  # Point number
    reached_redzone: bool = False
    scored: bool = False


@dataclass
class PossessionStats:
    """
    Aggregated possession statistics for a team.
    """

    o_line_points: int = 0
    o_line_scores: int = 0
    o_line_possessions: int = 0
    d_line_points: int = 0
    d_line_scores: int = 0
    d_line_possessions: int = 0
    d_line_conversions: int = 0  # Same as d_line_possessions for compatibility

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "o_line_points": self.o_line_points,
            "o_line_scores": self.o_line_scores,
            "o_line_possessions": self.o_line_possessions,
            "d_line_points": self.d_line_points,
            "d_line_scores": self.d_line_scores,
            "d_line_possessions": self.d_line_possessions,
            "d_line_conversions": self.d_line_conversions,
        }


@dataclass
class RedzoneStats:
    """
    Aggregated redzone statistics for a team.
    """

    redzone_possessions: int = 0
    redzone_goals: int = 0
    redzone_attempts: int = 0  # Possessions that reached redzone

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "redzone_possessions": self.redzone_possessions,
            "redzone_goals": self.redzone_goals,
            "redzone_attempts": self.redzone_attempts,
        }


@dataclass
class EventProcessorState:
    """
    Tracks state during event processing.
    """

    # Possession tracking
    points: list[Point] = field(default_factory=list)
    current_point: Optional[Point] = None
    current_possession: Optional[str] = None
    point_had_action: bool = False

    # Redzone tracking
    redzone_possessions: list[RedzonePossession] = field(default_factory=list)
    current_redzone_possession: Optional[RedzonePossession] = None
    in_possession: bool = False
    point_num: int = 0

    def finalize_current_point(self) -> None:
        """Save current point if it had action."""
        if self.current_point and self.point_had_action:
            self.points.append(self.current_point)

    def finalize_current_redzone_possession(self) -> None:
        """Save current redzone possession if it exists."""
        if self.current_redzone_possession:
            self.redzone_possessions.append(self.current_redzone_possession)
