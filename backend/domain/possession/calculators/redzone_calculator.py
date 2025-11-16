"""
Redzone calculator for Ultimate Frisbee statistics.
Calculates redzone efficiency and scoring percentages.
"""

from typing import Any, Dict, List, Optional

from ..processors.event_processor import RedzoneEventProcessor


class RedzoneCalculator:
    """Calculates redzone statistics for teams."""

    def __init__(self, db):
        """
        Initialize the calculator.

        Args:
            db: Database connection
        """
        self.db = db

    def calculate_for_team(
        self, game_id: str, team_id: str, is_home_team: bool
    ) -> Dict[str, Any]:
        """
        Calculate redzone statistics for a single team in a game.

        Args:
            game_id: Game identifier
            team_id: Team identifier
            is_home_team: Whether this is the home team

        Returns:
            Dictionary with redzone statistics
        """
        team_type = "home" if is_home_team else "away"
        events = self._fetch_events(game_id, team_type)

        if not events:
            return {
                "redzone_possessions": 0,
                "redzone_scores": 0,
                "redzone_attempts": 0,
            }

        processor = RedzoneEventProcessor(team_type)
        stats = processor.process_events(events)

        return stats.to_dict()

    def calculate_for_game(self, game_id: str) -> Dict[str, Any]:
        """
        Calculate redzone statistics for both teams in a game.

        Args:
            game_id: Game identifier

        Returns:
            Dictionary with stats for both teams
        """

        def analyze_team_redzone(team_type: str) -> Dict[str, Any]:
            """Analyze redzone for a specific team."""
            events = self._fetch_events(game_id, team_type)
            processor = RedzoneEventProcessor(team_type)
            stats = processor.process_events(events)
            return stats.to_dict()

        home_stats = analyze_team_redzone("home")
        away_stats = analyze_team_redzone("away")

        return {"game_id": game_id, "homeTeam": home_stats, "awayTeam": away_stats}

    def calculate_batch(
        self,
        team_ids: List[str],
        season_filter: str = "",
        season_param: Optional[int] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculate redzone statistics for multiple teams in a single batch.

        Args:
            team_ids: List of team IDs
            season_filter: SQL filter for season
            season_param: Season year parameter

        Returns:
            Dictionary mapping team_id to redzone stats
        """
        # Build the query - need receiver_y and thrower_y for redzone tracking
        query = f"""
        SELECT
            g.home_team_id,
            g.away_team_id,
            g.game_id,
            ge.event_index,
            ge.event_type,
            ge.team,
            ge.receiver_y,
            ge.thrower_y
        FROM games g
        JOIN game_events ge ON g.game_id = ge.game_id
        WHERE (g.home_team_id = ANY(:team_ids) OR g.away_team_id = ANY(:team_ids))
        {season_filter}
        ORDER BY g.game_id, ge.event_index,
            CASE
                WHEN ge.event_type IN (19, 15) THEN 0
                WHEN ge.event_type = 1 THEN 1
                ELSE 2
            END
        """

        params = {"team_ids": team_ids}
        if season_param:
            params["season"] = season_param

        all_events = self.db.execute_query(query, params)

        # Group events by game and team
        games_by_team = {}
        for event in all_events:
            home_team = event["home_team_id"]
            away_team = event["away_team_id"]
            game_id = event["game_id"]

            # Initialize team structures
            for team_id in [home_team, away_team]:
                if team_id not in games_by_team:
                    games_by_team[team_id] = {}
                if game_id not in games_by_team[team_id]:
                    games_by_team[team_id][game_id] = {
                        "is_home": team_id == home_team,
                        "events": [],
                    }

            # Add event to appropriate team
            if event["team"] == "home" and home_team in team_ids:
                games_by_team[home_team][game_id]["events"].append(event)
            elif event["team"] == "away" and away_team in team_ids:
                games_by_team[away_team][game_id]["events"].append(event)

        # Process each team's games
        results = {}
        for team_id in team_ids:
            team_stats = {
                "redzone_possessions": 0,
                "redzone_scores": 0,
                "redzone_attempts": 0,
            }

            if team_id in games_by_team:
                for game_data in games_by_team[team_id].values():
                    team_type = "home" if game_data["is_home"] else "away"
                    processor = RedzoneEventProcessor(team_type)
                    game_stats = processor.process_events(game_data["events"])

                    # Aggregate stats
                    team_stats["redzone_possessions"] += game_stats.redzone_possessions
                    team_stats["redzone_scores"] += game_stats.redzone_scores
                    team_stats["redzone_attempts"] += game_stats.redzone_attempts

            results[team_id] = team_stats

        return results

    def _fetch_events(self, game_id: str, team_type: str) -> List[Dict[str, Any]]:
        """
        Fetch events with position data for redzone calculation.

        Args:
            game_id: Game identifier
            team_type: 'home' or 'away'

        Returns:
            List of event dictionaries with receiver_y and thrower_y
        """
        query = """
        SELECT event_index, event_type, team, receiver_y, thrower_y
        FROM game_events
        WHERE game_id = :game_id
          AND team = :team_type
        ORDER BY event_index,
            CASE
                WHEN event_type IN (19, 15) THEN 0
                WHEN event_type = 1 THEN 1
                ELSE 2
            END
        """
        return self.db.execute_query(query, {"game_id": game_id, "team_type": team_type})
