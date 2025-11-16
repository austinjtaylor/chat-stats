"""
Event processor for possession and redzone tracking.
Consolidates duplicate event processing logic.
"""

from typing import Any, Dict, List, Optional

from ..models.point import (
    Point,
    RedzonePossession,
    EventProcessorState,
    PossessionStats,
    RedzoneStats,
)


class PossessionEventProcessor:
    """Processes game events to track possession statistics."""

    def __init__(self, team_type: str):
        """
        Initialize the processor.

        Args:
            team_type: 'home' or 'away'
        """
        self.team_type = team_type
        self.opponent_type = "away" if team_type == "home" else "home"

    def process_events(self, events: List[Dict[str, Any]]) -> PossessionStats:
        """
        Process a list of events to calculate possession stats.

        Args:
            events: List of game events (already filtered for this team)

        Returns:
            PossessionStats object with calculated statistics
        """
        if not events:
            return PossessionStats()

        state = EventProcessorState()

        for event in events:
            self._process_single_event(event, state)

        # Finalize any remaining point
        state.finalize_current_point()

        # Calculate statistics from points
        return self._calculate_stats_from_points(state.points)

    def _process_single_event(
        self, event: Dict[str, Any], state: EventProcessorState
    ) -> None:
        """
        Process a single event and update state.

        Args:
            event: Event dictionary
            state: Current processor state
        """
        event_type = event["event_type"]

        if event_type == 1:  # START_D_POINT - Team pulls
            self._handle_d_point_start(state)
        elif event_type == 2:  # START_O_POINT - Team receives
            self._handle_o_point_start(state)
        elif event_type == 19:  # Team goal
            self._handle_team_goal(state)
        elif event_type == 15:  # Opponent goal
            self._handle_opponent_goal(state)
        elif event_type == 18:  # Pass
            self._handle_pass(state)
        elif event_type in [11, 20, 22, 24]:  # Turnovers
            self._handle_turnover(event_type, state)
        elif event_type == 13:  # Opponent throwaway
            self._handle_opponent_turnover(state)

    def _handle_d_point_start(self, state: EventProcessorState) -> None:
        """Handle D-point start (team pulls)."""
        if state.current_point and state.point_had_action:
            state.points.append(state.current_point)

        state.current_point = Point(
            pulling_team=self.team_type,
            receiving_team=self.opponent_type,
            team_possessions=0,
            opponent_possessions=1,
        )
        state.current_possession = self.opponent_type
        state.point_had_action = False

    def _handle_o_point_start(self, state: EventProcessorState) -> None:
        """Handle O-point start (team receives)."""
        if state.current_point and state.point_had_action:
            state.points.append(state.current_point)

        state.current_point = Point(
            pulling_team=self.opponent_type,
            receiving_team=self.team_type,
            team_possessions=1,
            opponent_possessions=0,
        )
        state.current_possession = self.team_type
        state.point_had_action = False

    def _handle_team_goal(self, state: EventProcessorState) -> None:
        """Handle team goal event."""
        if state.current_point:
            state.current_point.scoring_team = self.team_type
            state.point_had_action = True

    def _handle_opponent_goal(self, state: EventProcessorState) -> None:
        """Handle opponent goal event."""
        if state.current_point:
            state.current_point.scoring_team = self.opponent_type
            state.point_had_action = True

    def _handle_pass(self, state: EventProcessorState) -> None:
        """Handle pass event."""
        if state.current_point:
            state.point_had_action = True

    def _handle_turnover(self, event_type: int, state: EventProcessorState) -> None:
        """Handle turnover events."""
        if not state.current_point:
            return

        state.point_had_action = True

        # Determine new possession
        if event_type == 11:  # Block - team gets possession
            new_possession = self.team_type
        else:  # Drop/Throwaway/Stall - team loses possession
            new_possession = self.opponent_type

        # Update possession counts if possession changed
        if new_possession != state.current_possession:
            if new_possession == self.team_type:
                state.current_point.team_possessions += 1
            else:
                state.current_point.opponent_possessions += 1
            state.current_possession = new_possession

    def _handle_opponent_turnover(self, state: EventProcessorState) -> None:
        """Handle opponent turnover (team gains possession)."""
        if not state.current_point:
            return

        state.point_had_action = True
        new_possession = self.team_type

        if new_possession != state.current_possession:
            if new_possession == self.team_type:
                state.current_point.team_possessions += 1
            else:
                state.current_point.opponent_possessions += 1
            state.current_possession = new_possession

    def _calculate_stats_from_points(
        self, points: List[Point]
    ) -> PossessionStats:
        """
        Calculate statistics from processed points.

        Args:
            points: List of Point objects

        Returns:
            PossessionStats object
        """
        stats = PossessionStats()

        for point in points:
            if point.is_o_line_point(self.team_type):
                # We received the pull - O-line point
                stats.o_line_points += 1
                if point.did_team_score(self.team_type):
                    stats.o_line_scores += 1
                stats.o_line_possessions += point.team_possessions

            elif point.is_d_line_point(self.team_type):
                # We pulled - D-line point
                stats.d_line_points += 1
                if point.did_team_score(self.team_type):
                    stats.d_line_scores += 1
                stats.d_line_possessions += point.team_possessions

        stats.d_line_conversions = stats.d_line_possessions  # For compatibility
        return stats


class RedzoneEventProcessor:
    """Processes game events to track redzone statistics."""

    def __init__(self, team_type: str):
        """
        Initialize the processor.

        Args:
            team_type: 'home' or 'away'
        """
        self.team_type = team_type
        self.opponent_type = "away" if team_type == "home" else "home"

    def process_events(self, events: List[Dict[str, Any]]) -> RedzoneStats:
        """
        Process a list of events to calculate redzone stats.

        Args:
            events: List of game events with receiver_y and thrower_y fields

        Returns:
            RedzoneStats object with calculated statistics
        """
        if not events:
            return RedzoneStats()

        state = EventProcessorState()

        for event in events:
            self._process_single_event(event, state)

        # Finalize any remaining possession
        state.finalize_current_redzone_possession()

        # Calculate statistics
        return self._calculate_stats_from_possessions(state.redzone_possessions)

    def _process_single_event(
        self, event: Dict[str, Any], state: EventProcessorState
    ) -> None:
        """Process a single event for redzone tracking."""
        event_type = event["event_type"]
        receiver_y = event.get("receiver_y")
        thrower_y = event.get("thrower_y")

        if event_type == 1:  # START_D_POINT - Team pulls
            state.point_num += 1
            state.in_possession = False

        elif event_type == 2:  # START_O_POINT - Team receives
            state.point_num += 1
            if state.current_redzone_possession:
                state.redzone_possessions.append(state.current_redzone_possession)
            state.current_redzone_possession = RedzonePossession(point=state.point_num)
            state.in_possession = True

        elif event_type == 19:  # Team goal
            if state.current_redzone_possession:
                state.current_redzone_possession.scored = True
                if thrower_y and 80 <= thrower_y <= 100:
                    state.current_redzone_possession.reached_redzone = True
                state.redzone_possessions.append(state.current_redzone_possession)
                state.current_redzone_possession = None
                state.in_possession = False

        elif event_type == 15:  # Opponent goal
            if state.current_redzone_possession:
                state.redzone_possessions.append(state.current_redzone_possession)
                state.current_redzone_possession = None
                state.in_possession = False

        elif event_type == 18:  # Pass
            # Check for redzone entry
            if not state.in_possession:
                if state.current_redzone_possession:
                    state.redzone_possessions.append(state.current_redzone_possession)
                state.current_redzone_possession = RedzonePossession(
                    point=state.point_num
                )
                state.in_possession = True

            if (
                state.in_possession
                and state.current_redzone_possession
                and receiver_y
                and 80 <= receiver_y <= 100
            ):
                state.current_redzone_possession.reached_redzone = True

        elif event_type == 11:  # Block - we gain possession
            if not state.in_possession:
                if state.current_redzone_possession:
                    state.redzone_possessions.append(state.current_redzone_possession)
                state.current_redzone_possession = RedzonePossession(
                    point=state.point_num
                )
                state.in_possession = True

        elif event_type in [20, 22, 24]:  # We lose possession
            if state.in_possession and state.current_redzone_possession:
                state.redzone_possessions.append(state.current_redzone_possession)
                state.current_redzone_possession = None
                state.in_possession = False

        elif event_type == 13:  # Opponent throwaway - we gain possession
            if not state.in_possession:
                if state.current_redzone_possession:
                    state.redzone_possessions.append(state.current_redzone_possession)
                state.current_redzone_possession = RedzonePossession(
                    point=state.point_num
                )
                state.in_possession = True

    def _calculate_stats_from_possessions(
        self, possessions: List[RedzonePossession]
    ) -> RedzoneStats:
        """Calculate statistics from redzone possessions."""
        stats = RedzoneStats()

        stats.redzone_possessions = len(possessions)
        stats.redzone_attempts = sum(1 for p in possessions if p.reached_redzone)
        stats.redzone_scores = sum(
            1 for p in possessions if p.reached_redzone and p.scored
        )

        return stats
