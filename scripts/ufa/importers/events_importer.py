#!/usr/bin/env python3
"""
Events importer for UFA game event data.
"""

import json

from backend.utils.pass_type import classify_pass

from .base_importer import BaseImporter

# Event types that represent throws (PASS=18, GOAL=19)
THROW_EVENT_TYPES = {18, 19}


class EventsImporter(BaseImporter):
    """Handles importing game event data from UFA API"""

    def import_game_events(self, game_id: str, events_data: dict) -> int:
        """
        Import game events for a single game

        Args:
            game_id: Game ID
            events_data: Dictionary with 'homeEvents' and 'awayEvents' arrays

        Returns:
            Number of events imported
        """
        # Skip all-star games
        if self.is_allstar_game(game_id):
            return 0

        if not events_data:
            return 0

        count = 0

        # Process home events
        count += self._import_team_events(
            game_id, events_data.get("homeEvents", []), "home"
        )

        # Process away events
        count += self._import_team_events(
            game_id, events_data.get("awayEvents", []), "away"
        )

        if count > 0:
            self.logger.info(f"  Imported {count} game events for {game_id}")

        return count

    def _import_team_events(self, game_id: str, events: list[dict], team: str) -> int:
        """
        Import events for a single team in a game

        Args:
            game_id: Game ID
            events: List of event dictionaries
            team: Team identifier ('home' or 'away')

        Returns:
            Number of events imported
        """
        count = 0

        for idx, event in enumerate(events):
            try:
                event_type = event.get("type", 0)
                thrower_x = event.get("throwerX")
                thrower_y = event.get("throwerY")
                receiver_x = event.get("receiverX")
                receiver_y = event.get("receiverY")

                # Calculate pass_type for throw events (PASS=18, GOAL=19)
                pass_type = None
                if event_type in THROW_EVENT_TYPES:
                    pass_type = classify_pass(
                        thrower_x, thrower_y, receiver_x, receiver_y
                    )

                event_record = {
                    "game_id": game_id,
                    "event_index": idx,
                    "team": team,
                    "event_type": event_type,
                    "event_time": event.get("time"),
                    "thrower_id": event.get("thrower"),
                    "receiver_id": event.get("receiver"),
                    "defender_id": event.get("defender"),
                    "puller_id": event.get("puller"),
                    "thrower_x": thrower_x,
                    "thrower_y": thrower_y,
                    "receiver_x": receiver_x,
                    "receiver_y": receiver_y,
                    "turnover_x": event.get("turnoverX"),
                    "turnover_y": event.get("turnoverY"),
                    "pull_x": event.get("pullX"),
                    "pull_y": event.get("pullY"),
                    "pull_ms": event.get("pullMs"),
                    "line_players": (
                        json.dumps(event.get("line", [])) if event.get("line") else None
                    ),
                    "pass_type": pass_type,
                }

                self.db.execute_query(
                    """
                    INSERT INTO game_events (
                        game_id, event_index, team, event_type, event_time,
                        thrower_id, receiver_id, defender_id, puller_id,
                        thrower_x, thrower_y, receiver_x, receiver_y,
                        turnover_x, turnover_y, pull_x, pull_y, pull_ms, line_players,
                        pass_type
                    ) VALUES (
                        :game_id, :event_index, :team, :event_type, :event_time,
                        :thrower_id, :receiver_id, :defender_id, :puller_id,
                        :thrower_x, :thrower_y, :receiver_x, :receiver_y,
                        :turnover_x, :turnover_y, :pull_x, :pull_y, :pull_ms, :line_players,
                        :pass_type
                    )
                    ON CONFLICT (game_id, event_index, team) DO NOTHING
                    """,
                    event_record,
                )
                count += 1
            except Exception:
                pass  # Silently skip individual event errors

        return count
