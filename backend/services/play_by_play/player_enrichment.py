"""
Player enrichment service for fetching and enriching event data with player names.
"""

import json


class PlayerEnrichment:
    """Handles player data fetching and event enrichment."""

    @staticmethod
    def collect_player_ids(events: list[dict]) -> set[str]:
        """
        Collect all unique player IDs from events.

        Args:
            events: List of game events

        Returns:
            Set of unique player IDs
        """
        all_player_ids = set()

        for event in events:
            # Add player IDs from event columns
            if event.get("thrower_id"):
                all_player_ids.add(event["thrower_id"])
            if event.get("receiver_id"):
                all_player_ids.add(event["receiver_id"])
            if event.get("defender_id"):
                all_player_ids.add(event["defender_id"])
            if event.get("puller_id"):
                all_player_ids.add(event["puller_id"])

            # Add player IDs from line_players JSON
            if event.get("line_players"):
                try:
                    player_ids = json.loads(event["line_players"])
                    if player_ids:
                        all_player_ids.update(player_ids)
                except Exception:
                    pass

        return all_player_ids

    @staticmethod
    def fetch_players(db, player_ids: set[str], year: int) -> dict[str, dict[str, str]]:
        """
        Fetch player data from database.

        Args:
            db: Database instance
            player_ids: Set of player IDs to fetch
            year: Game year

        Returns:
            Dictionary mapping player_id to {full_name, last_name}
        """
        if not player_ids:
            return {}

        player_ids_list = list(player_ids)
        placeholders = ", ".join([f":p{i}" for i in range(len(player_ids_list))])
        players_query = f"""
        SELECT DISTINCT player_id, full_name, last_name
        FROM players
        WHERE player_id IN ({placeholders})
          AND year = :year
        """

        params = {f"p{i}": pid for i, pid in enumerate(player_ids_list)}
        params["year"] = year

        player_results = db.execute_query(players_query, params)

        return {
            p["player_id"]: {
                "full_name": p.get("full_name"),
                "last_name": p.get("last_name"),
            }
            for p in player_results
            if p and p.get("player_id")
        }

    @staticmethod
    def enrich_events(
        events: list[dict], player_lookup: dict[str, dict[str, str]]
    ) -> None:
        """
        Enrich events with player names from lookup.

        Args:
            events: List of events to enrich (modified in place)
            player_lookup: Player lookup dictionary
        """
        for event in events:
            # Enrich thrower
            if event.get("thrower_id") and event["thrower_id"] in player_lookup:
                event["thrower_name"] = player_lookup[event["thrower_id"]]["full_name"]
                event["thrower_last"] = player_lookup[event["thrower_id"]]["last_name"]
            else:
                event["thrower_name"] = None
                event["thrower_last"] = None

            # Enrich receiver
            if event.get("receiver_id") and event["receiver_id"] in player_lookup:
                event["receiver_name"] = player_lookup[event["receiver_id"]][
                    "full_name"
                ]
                event["receiver_last"] = player_lookup[event["receiver_id"]][
                    "last_name"
                ]
            else:
                event["receiver_name"] = None
                event["receiver_last"] = None

            # Enrich defender
            if event.get("defender_id") and event["defender_id"] in player_lookup:
                event["defender_name"] = player_lookup[event["defender_id"]][
                    "full_name"
                ]
                event["defender_last"] = player_lookup[event["defender_id"]][
                    "last_name"
                ]
            else:
                event["defender_name"] = None
                event["defender_last"] = None

            # Enrich puller
            if event.get("puller_id") and event["puller_id"] in player_lookup:
                event["puller_name"] = player_lookup[event["puller_id"]]["full_name"]
                event["puller_last"] = player_lookup[event["puller_id"]]["last_name"]
            else:
                event["puller_name"] = None
                event["puller_last"] = None
