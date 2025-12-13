"""
Event handlers for processing different game event types.
"""

import math
from typing import Any

from utils.pass_type import classify_pass, get_display_name


class EventHandlers:
    """Handlers for processing different types of game events."""

    @staticmethod
    def handle_pull_event(
        event: dict, team: str, current_point: dict | None
    ) -> dict[str, Any] | None:
        """
        Handle pull event (initial or detailed).

        Args:
            event: Event data
            team: Team processing the event ('home' or 'away')
            current_point: Current point being built

        Returns:
            Pull event dict or None
        """
        if not current_point or current_point["pulling_team"] != team:
            return None

        puller_name = event.get("puller_last")
        if not puller_name:
            return {"type": "pull", "description": "Pull", "yard_line": None}

        # Calculate pull distance if available
        pull_distance = None
        if event.get("pull_y") is not None:
            pull_distance = int(abs(event["pull_y"] - 20))

        pull_description = f"Pull by {puller_name}"
        if pull_distance:
            pull_description = f"{pull_distance}y {pull_description}"

        return {"type": "pull", "description": pull_description, "yard_line": None}

    @staticmethod
    def handle_pass_event(event: dict) -> dict[str, Any] | None:
        """
        Handle pass event.

        Args:
            event: Event data

        Returns:
            Pass event dict or None
        """
        receiver_last = event.get("receiver_last")
        thrower_last = event.get("thrower_last")

        if not receiver_last or not thrower_last:
            return None

        # Calculate pass details if coordinates available
        thrower_y = event.get("thrower_y")
        receiver_y = event.get("receiver_y")
        thrower_x = event.get("thrower_x")
        receiver_x = event.get("receiver_x")

        if (
            thrower_y is not None
            and receiver_y is not None
            and thrower_x is not None
            and receiver_x is not None
        ):
            vertical_yards = receiver_y - thrower_y
            horizontal_yards = receiver_x - thrower_x
            actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)
            angle_radians = math.atan2(vertical_yards, -horizontal_yards)
            angle_degrees = math.degrees(angle_radians)

            # Classify pass type using utility function
            pass_type_key = classify_pass(thrower_x, thrower_y, receiver_x, receiver_y)
            pass_type_display = get_display_name(pass_type_key)

            return {
                "type": "pass",
                "description": f"{pass_type_display} from {thrower_last} to {receiver_last}",
                "yard_line": int(actual_distance),
                "direction": angle_degrees,
                "pass_type": pass_type_key,
            }
        else:
            return {
                "type": "pass",
                "description": f"Pass from {thrower_last} to {receiver_last}",
                "yard_line": None,
                "pass_type": None,
            }

    @staticmethod
    def handle_goal_event(event: dict) -> dict[str, Any] | None:
        """
        Handle goal event.

        Args:
            event: Event data

        Returns:
            Goal event dict or None
        """
        receiver_last = event.get("receiver_last")
        thrower_last = event.get("thrower_last")

        if not receiver_last or not thrower_last:
            return None

        # Calculate goal details if coordinates available
        thrower_y = event.get("thrower_y")
        receiver_y = event.get("receiver_y")
        thrower_x = event.get("thrower_x")
        receiver_x = event.get("receiver_x")

        if (
            thrower_y is not None
            and receiver_y is not None
            and thrower_x is not None
            and receiver_x is not None
        ):
            vertical_yards = receiver_y - thrower_y
            horizontal_yards = receiver_x - thrower_x
            actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)
            angle_radians = math.atan2(vertical_yards, -horizontal_yards)
            angle_degrees = math.degrees(angle_radians)

            # Classify pass type using utility function
            pass_type_key = classify_pass(thrower_x, thrower_y, receiver_x, receiver_y)
            pass_type_display = get_display_name(pass_type_key)

            return {
                "type": "goal",
                "description": f"{pass_type_display} Score from {thrower_last} to {receiver_last}",
                "yard_line": int(actual_distance),
                "direction": angle_degrees,
                "pass_type": pass_type_key,
            }
        else:
            return {
                "type": "goal",
                "description": f"Score from {thrower_last} to {receiver_last}",
                "yard_line": None,
                "pass_type": None,
            }

    @staticmethod
    def handle_block_event(event: dict) -> dict[str, Any] | None:
        """
        Handle block event.

        Args:
            event: Event data

        Returns:
            Block event dict or None
        """
        defender_last = event.get("defender_last")
        if not defender_last:
            return None

        yard_line = (
            int(event["turnover_y"]) if event.get("turnover_y") is not None else None
        )

        return {
            "type": "block",
            "description": f"Block by {defender_last}",
            "yard_line": yard_line,
        }

    @staticmethod
    def handle_opponent_block_event(event: dict) -> dict[str, Any]:
        """
        Handle opponent block event.

        Args:
            event: Event data

        Returns:
            Opponent turnover event dict
        """
        defender_name = event.get("defender_last")
        yard_line = (
            int(event["turnover_y"]) if event.get("turnover_y") is not None else None
        )

        if defender_name:
            return {
                "type": "opponent_turnover",
                "description": f"Opponent turnover (Blocked by {defender_name})",
                "yard_line": yard_line,
            }
        else:
            return {
                "type": "opponent_turnover",
                "description": "Opponent turnover (Block)",
                "yard_line": yard_line,
            }

    @staticmethod
    def handle_drop_event(event: dict) -> dict[str, Any] | None:
        """
        Handle drop event.

        Args:
            event: Event data

        Returns:
            Drop event dict or None
        """
        receiver_last = event.get("receiver_last")
        if not receiver_last:
            return None

        yard_line = (
            int(event["turnover_y"]) if event.get("turnover_y") is not None else None
        )

        return {
            "type": "drop",
            "description": f"Drop by {receiver_last}",
            "yard_line": yard_line,
        }

    @staticmethod
    def handle_throwaway_event(event: dict) -> dict[str, Any] | None:
        """
        Handle throwaway event.

        Args:
            event: Event data

        Returns:
            Throwaway event dict or None
        """
        thrower_last = event.get("thrower_last")
        if not thrower_last:
            return None

        # Calculate throwaway details if coordinates available
        thrower_y = event.get("thrower_y")
        turnover_y = event.get("turnover_y")
        thrower_x = event.get("thrower_x")
        turnover_x = event.get("turnover_x")

        if (
            thrower_y is not None
            and turnover_y is not None
            and thrower_x is not None
            and turnover_x is not None
        ):
            vertical_yards = turnover_y - thrower_y
            horizontal_yards = turnover_x - thrower_x
            actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)
            angle_radians = math.atan2(vertical_yards, -horizontal_yards)
            angle_degrees = math.degrees(angle_radians)

            throwaway_type = "Huck throwaway" if vertical_yards >= 40 else "Throwaway"

            return {
                "type": "throwaway",
                "description": f"{throwaway_type} by {thrower_last}",
                "yard_line": int(actual_distance),
                "direction": angle_degrees,
            }
        else:
            return {
                "type": "throwaway",
                "description": f"Throwaway by {thrower_last}",
                "yard_line": None,
            }

    @staticmethod
    def handle_stall_event(event: dict) -> dict[str, Any]:
        """
        Handle stall event.

        Args:
            event: Event data

        Returns:
            Stall event dict
        """
        yard_line = (
            int(event["turnover_y"]) if event.get("turnover_y") is not None else None
        )

        return {"type": "stall", "description": "Stall", "yard_line": yard_line}

    @staticmethod
    def handle_opponent_turnover_event(
        event: dict, turnover_type: str
    ) -> dict[str, Any]:
        """
        Handle opponent turnover event (throwaway or stall).

        Args:
            event: Event data
            turnover_type: Type of turnover ('Throwaway' or 'Stall')

        Returns:
            Opponent turnover event dict
        """
        yard_line = (
            int(event["turnover_y"]) if event.get("turnover_y") is not None else None
        )

        return {
            "type": "opponent_turnover",
            "description": f"Opponent turnover ({turnover_type})",
            "yard_line": yard_line,
        }

    @staticmethod
    def handle_opponent_score_event() -> dict[str, Any]:
        """
        Handle opponent score event.

        Returns:
            Opponent score event dict
        """
        return {
            "type": "opponent_score",
            "description": "They scored",
            "yard_line": None,
        }
