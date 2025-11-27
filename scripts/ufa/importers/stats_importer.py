#!/usr/bin/env python3
"""
Stats importer for UFA player statistics (game and season).
"""

from typing import Any

from .base_importer import BaseImporter


class StatsImporter(BaseImporter):
    """Handles importing player game stats and season stats from UFA API"""

    def import_player_game_stat(
        self, player_stat: dict[str, Any], game_id: str
    ) -> dict[str, Any]:
        """
        Transform a single player game stat from API format to database format

        Args:
            player_stat: Player stat dictionary from API
            game_id: Game ID

        Returns:
            Dictionary ready for database insertion
        """
        year = self.extract_year_from_game_id(game_id)

        return {
            "player_id": player_stat["player"]["playerID"],
            "game_id": game_id,
            "team_id": player_stat.get("teamID", ""),
            "year": year,
            "assists": player_stat.get("assists", 0),
            "goals": player_stat.get("goals", 0),
            "hockey_assists": player_stat.get("hockeyAssists", 0),
            "completions": player_stat.get("completions", 0),
            "throw_attempts": player_stat.get("throwAttempts", 0),
            "throwaways": player_stat.get("throwaways", 0),
            "stalls": player_stat.get("stalls", 0),
            "callahans_thrown": player_stat.get("callahansThrown", 0),
            "yards_received": player_stat.get("yardsReceived", 0),
            "yards_thrown": player_stat.get("yardsThrown", 0),
            "hucks_attempted": player_stat.get("hucksAttempted", 0),
            "hucks_completed": player_stat.get("hucksCompleted", 0),
            "catches": player_stat.get("catches", 0),
            "drops": player_stat.get("drops", 0),
            "blocks": player_stat.get("blocks", 0),
            "callahans": player_stat.get("callahans", 0),
            "pulls": player_stat.get("pulls", 0),
            "ob_pulls": player_stat.get("obPulls", 0),
            "recorded_pulls": player_stat.get("recordedPulls", 0),
            "recorded_pulls_hangtime": player_stat.get("recordedPullsHangtime"),
            "o_points_played": player_stat.get("oPointsPlayed", 0),
            "o_points_scored": player_stat.get("oPointsScored", 0),
            "d_points_played": player_stat.get("dPointsPlayed", 0),
            "d_points_scored": player_stat.get("dPointsScored", 0),
            "seconds_played": player_stat.get("secondsPlayed", 0),
            "o_opportunities": player_stat.get("oOpportunities", 0),
            "o_opportunity_scores": player_stat.get("oOpportunityScores", 0),
            "d_opportunities": player_stat.get("dOpportunities", 0),
            "d_opportunity_stops": player_stat.get("dOpportunityStops", 0),
        }

    def insert_player_game_stat(self, player_game_stat: dict[str, Any]) -> None:
        """
        Insert a single player game stat record

        Args:
            player_game_stat: Player game stat dictionary
        """
        self.db.execute_query(
            """
            INSERT INTO player_game_stats (
                player_id, game_id, team_id, year,
                assists, goals, hockey_assists, completions, throw_attempts, throwaways, stalls,
                callahans_thrown, yards_received, yards_thrown, hucks_attempted, hucks_completed,
                catches, drops, blocks, callahans, pulls, ob_pulls, recorded_pulls, recorded_pulls_hangtime,
                o_points_played, o_points_scored, d_points_played, d_points_scored, seconds_played,
                o_opportunities, o_opportunity_scores, d_opportunities, d_opportunity_stops
            ) VALUES (
                :player_id, :game_id, :team_id, :year,
                :assists, :goals, :hockey_assists, :completions, :throw_attempts, :throwaways, :stalls,
                :callahans_thrown, :yards_received, :yards_thrown, :hucks_attempted, :hucks_completed,
                :catches, :drops, :blocks, :callahans, :pulls, :ob_pulls, :recorded_pulls, :recorded_pulls_hangtime,
                :o_points_played, :o_points_scored, :d_points_played, :d_points_scored, :seconds_played,
                :o_opportunities, :o_opportunity_scores, :d_opportunities, :d_opportunity_stops
            )
            ON CONFLICT (player_id, game_id) DO NOTHING
            """,
            player_game_stat,
        )

    def import_player_season_stats(
        self,
        season_stats_data: list[dict[str, Any]],
        players_data: list[dict[str, Any]],
    ) -> int:
        """
        Import player season statistics

        Args:
            season_stats_data: List of season stat dictionaries from API
            players_data: List of player data for team_id mapping

        Returns:
            Number of season stats imported
        """
        count = 0

        for stat in season_stats_data:
            try:
                player_season_stat = {
                    "player_id": stat["player"]["playerID"],
                    "team_id": stat.get("teamID", ""),
                    "year": stat.get("year"),
                    "total_assists": stat.get("assists", 0),
                    "total_goals": stat.get("goals", 0),
                    "total_hockey_assists": stat.get("hockeyAssists", 0),
                    "total_completions": stat.get("completions", 0),
                    "total_throw_attempts": stat.get("throwAttempts", 0),
                    "total_throwaways": stat.get("throwaways", 0),
                    "total_stalls": stat.get("stalls", 0),
                    "total_callahans_thrown": stat.get("callahansThrown", 0),
                    "total_yards_received": stat.get("yardsReceived", 0),
                    "total_yards_thrown": stat.get("yardsThrown", 0),
                    "total_hucks_attempted": stat.get("hucksAttempted", 0),
                    "total_hucks_completed": stat.get("hucksCompleted", 0),
                    "total_catches": stat.get("catches", 0),
                    "total_drops": stat.get("drops", 0),
                    "total_blocks": stat.get("blocks", 0),
                    "total_callahans": stat.get("callahans", 0),
                    "total_pulls": stat.get("pulls", 0),
                    "total_ob_pulls": stat.get("obPulls", 0),
                    "total_recorded_pulls": stat.get("recordedPulls", 0),
                    "total_recorded_pulls_hangtime": stat.get("recordedPullsHangtime"),
                    "total_o_points_played": stat.get("oPointsPlayed", 0),
                    "total_o_points_scored": stat.get("oPointsScored", 0),
                    "total_d_points_played": stat.get("dPointsPlayed", 0),
                    "total_d_points_scored": stat.get("dPointsScored", 0),
                    "total_seconds_played": stat.get("secondsPlayed", 0),
                    "total_o_opportunities": stat.get("oOpportunities", 0),
                    "total_o_opportunity_scores": stat.get("oOpportunityScores", 0),
                    "total_d_opportunities": stat.get("dOpportunities", 0),
                    "total_d_opportunity_stops": stat.get("dOpportunityStops", 0),
                }

                # Calculate completion percentage
                if player_season_stat["total_throw_attempts"] > 0:
                    player_season_stat["completion_percentage"] = round(
                        player_season_stat["total_completions"]
                        * 100.0
                        / player_season_stat["total_throw_attempts"],
                        2,
                    )
                else:
                    player_season_stat["completion_percentage"] = 0

                # Find team_id for this player/year combination from players data
                for player in players_data:
                    if player.get("playerID") == stat["player"][
                        "playerID"
                    ] and player.get("year") == stat.get("year"):
                        player_season_stat["team_id"] = player.get("teamID", "")
                        break

                # Insert player season stats
                self.db.execute_query(
                    """
                    INSERT INTO player_season_stats (
                        player_id, team_id, year,
                        total_assists, total_goals, total_hockey_assists, total_completions, total_throw_attempts,
                        total_throwaways, total_stalls, total_callahans_thrown, total_yards_received, total_yards_thrown,
                        total_hucks_attempted, total_hucks_completed, total_catches, total_drops, total_blocks,
                        total_callahans, total_pulls, total_ob_pulls, total_recorded_pulls, total_recorded_pulls_hangtime,
                        total_o_points_played, total_o_points_scored, total_d_points_played, total_d_points_scored,
                        total_seconds_played, total_o_opportunities, total_o_opportunity_scores, total_d_opportunities,
                        total_d_opportunity_stops, completion_percentage
                    ) VALUES (
                        :player_id, :team_id, :year,
                        :total_assists, :total_goals, :total_hockey_assists, :total_completions, :total_throw_attempts,
                        :total_throwaways, :total_stalls, :total_callahans_thrown, :total_yards_received, :total_yards_thrown,
                        :total_hucks_attempted, :total_hucks_completed, :total_catches, :total_drops, :total_blocks,
                        :total_callahans, :total_pulls, :total_ob_pulls, :total_recorded_pulls, :total_recorded_pulls_hangtime,
                        :total_o_points_played, :total_o_points_scored, :total_d_points_played, :total_d_points_scored,
                        :total_seconds_played, :total_o_opportunities, :total_o_opportunity_scores, :total_d_opportunities,
                        :total_d_opportunity_stops, :completion_percentage
                    )
                    ON CONFLICT (player_id, team_id, year) DO NOTHING
                    """,
                    player_season_stat,
                )
                count += 1
            except Exception as e:
                self.logger.warning(
                    f"Failed to import season stat for {stat.get('player', {}).get('playerID', 'unknown')}: {e}"
                )

        self.logger.info(f"  Imported {count} player season stats")
        return count
