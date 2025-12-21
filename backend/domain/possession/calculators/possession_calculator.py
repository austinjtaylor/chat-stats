"""
Possession calculator for Ultimate Frisbee statistics.
Calculates O-line and D-line conversion rates and hold percentages.
"""

from typing import Any

from ..processors.event_processor import PossessionEventProcessor


class PossessionCalculator:
    """Calculates possession-based statistics matching UFA methodology."""

    def __init__(self, db):
        """
        Initialize the calculator.

        Args:
            db: Database connection
        """
        self.db = db

    def calculate_for_game(
        self, game_id: str, team_id: str, is_home_team: bool
    ) -> dict[str, Any] | None:
        """
        Calculate possession statistics for a team in a specific game.

        Args:
            game_id: Game identifier
            team_id: Team identifier
            is_home_team: Whether this is the home team

        Returns:
            Dictionary with possession statistics or None if no events
        """
        team_type = "home" if is_home_team else "away"
        events = self._fetch_events(game_id, team_type)

        if not events:
            return None

        processor = PossessionEventProcessor(team_type)
        stats = processor.process_events(events)

        return stats.to_dict()

    def calculate_batch(
        self,
        team_ids: list[str],
        season_filter: str = "",
        season_param: int | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Calculate possession statistics for multiple teams in a single batch.
        Optimized to avoid N+1 query problem.

        Args:
            team_ids: List of team IDs to calculate stats for
            season_filter: SQL filter for season (e.g., "AND SUBSTRING(game_id, 1, 4) = :season")
            season_param: Season year parameter

        Returns:
            Dictionary mapping team_id to possession stats
        """
        # Build the query
        query = f"""
        SELECT
            g.home_team_id,
            g.away_team_id,
            g.game_id,
            ge.event_index,
            ge.event_type,
            ge.team
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

            # Initialize team structures if needed
            for team_id in [home_team, away_team]:
                if team_id not in games_by_team:
                    games_by_team[team_id] = {}
                if game_id not in games_by_team[team_id]:
                    games_by_team[team_id][game_id] = {
                        "is_home": team_id == home_team,
                        "events": [],
                    }

            # Add event to appropriate team (only if it's their team type)
            if event["team"] == "home" and home_team in team_ids:
                games_by_team[home_team][game_id]["events"].append(event)
            elif event["team"] == "away" and away_team in team_ids:
                games_by_team[away_team][game_id]["events"].append(event)

        # Process each team's games
        results = {}
        for team_id in team_ids:
            team_stats = {
                "o_line_points": 0,
                "o_line_scores": 0,
                "o_line_possessions": 0,
                "d_line_points": 0,
                "d_line_scores": 0,
                "d_line_possessions": 0,
            }

            if team_id in games_by_team:
                for game_data in games_by_team[team_id].values():
                    team_type = "home" if game_data["is_home"] else "away"
                    processor = PossessionEventProcessor(team_type)
                    game_stats = processor.process_events(game_data["events"])

                    # Aggregate stats
                    team_stats["o_line_points"] += game_stats.o_line_points
                    team_stats["o_line_scores"] += game_stats.o_line_scores
                    team_stats["o_line_possessions"] += game_stats.o_line_possessions
                    team_stats["d_line_points"] += game_stats.d_line_points
                    team_stats["d_line_scores"] += game_stats.d_line_scores
                    team_stats["d_line_possessions"] += game_stats.d_line_possessions

            results[team_id] = team_stats

        return results

    def _fetch_events(self, game_id: str, team_type: str) -> list[dict[str, Any]]:
        """
        Fetch events for a specific game and team.

        Args:
            game_id: Game identifier
            team_type: 'home' or 'away'

        Returns:
            List of event dictionaries
        """
        query = """
        SELECT event_index, event_type, team
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
        return self.db.execute_query(
            query, {"game_id": game_id, "team_type": team_type}
        )
