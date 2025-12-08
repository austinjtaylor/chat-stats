"""
Comprehensive team statistics service.
"""

from typing import Any


class TeamStatsService:
    """Service for comprehensive team statistics queries."""

    def __init__(self, db):
        """
        Initialize the team stats service.

        Args:
            db: Database instance
        """
        self.db = db

    def get_comprehensive_team_stats(
        self,
        season: str = "2025",
        view: str = "total",
        perspective: str = "team",
        sort: str = "wins",
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        """
        Get comprehensive team statistics with all UFA-style columns.
        Now using pre-aggregated team_season_stats table for instant performance.

        Args:
            season: Season year or 'career' for all-time stats
            view: 'total' or 'per-game' for aggregation type
            perspective: 'team' for team stats or 'opponent' for opponent stats
            sort: Column to sort by (handled client-side now)
            order: 'asc' or 'desc' (handled client-side now)

        Returns:
            List of team statistics dictionaries
        """
        # Determine parameters
        season_param = int(season) if season.isdigit() else None
        is_opponent_view = perspective == "opponent"

        # Build query based on season and perspective
        if season == "career":
            query = self._build_career_stats_query(is_opponent_view)
            params = {}
        else:
            query = self._build_season_stats_query(is_opponent_view)
            params = {"season": season_param}

        teams = self.db.execute_query(query, params)

        # Apply per-game calculations if requested
        if view == "per-game":
            teams = self._apply_per_game_calculations(teams)

        # Note: Sorting is now handled client-side for instant performance
        # The 'sort' and 'order' parameters are ignored here but kept for API compatibility

        return teams

    def _build_career_stats_query(self, is_opponent_view: bool) -> str:
        """
        Build SQL query for career (aggregated) team stats.

        Args:
            is_opponent_view: Whether to show opponent stats

        Returns:
            SQL query string
        """
        if is_opponent_view:
            return """
            SELECT
                tss.team_id,
                MIN(t.name) as name,
                MIN(t.full_name) as full_name,
                SUM(tss.games_played) as games_played,
                SUM(tss.wins) as wins,
                SUM(tss.losses) as losses,
                SUM(tss.scores) as scores,
                SUM(tss.scores_against) as scores_against,
                SUM(tss.opp_completions) as completions,
                SUM(tss.opp_turnovers) as turnovers,
                CASE WHEN SUM(tss.opp_throw_attempts) > 0
                    THEN ROUND((CAST(SUM(tss.opp_completions) AS NUMERIC) / SUM(tss.opp_throw_attempts)) * 100, 2)
                    ELSE 0
                END as completion_percentage,
                SUM(tss.opp_hucks_completed) as hucks_completed,
                SUM(COALESCE(tss.opp_hucks_attempted, 0)) as hucks_attempted,
                SUM(CASE WHEN tss.year >= 2021 THEN tss.games_played ELSE 0 END) as games_with_huck_stats,
                CASE WHEN SUM(tss.opp_hucks_attempted) > 0
                    THEN ROUND((CAST(SUM(tss.opp_hucks_completed) AS NUMERIC) / SUM(tss.opp_hucks_attempted)) * 100, 2)
                    ELSE 0
                END as huck_percentage,
                SUM(tss.opp_blocks) as blocks,
                SUM(COALESCE(tss.opp_o_line_scores, 0)) as o_line_scores,
                SUM(COALESCE(tss.opp_d_line_scores, 0)) as d_line_scores,
                SUM(CASE WHEN tss.year >= 2014 THEN tss.games_played ELSE 0 END) as games_with_possession_stats,
                -- Use games-weighted average for opponent possession stats (2014-2019 don't have accurate raw counts)
                CASE WHEN SUM(CASE WHEN tss.opp_hold_percentage > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.opp_hold_percentage > 0 THEN tss.opp_hold_percentage * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.opp_hold_percentage > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as hold_percentage,
                CASE WHEN SUM(CASE WHEN tss.opp_o_line_conversion > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.opp_o_line_conversion > 0 THEN tss.opp_o_line_conversion * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.opp_o_line_conversion > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as o_line_conversion,
                CASE WHEN SUM(CASE WHEN tss.opp_break_percentage > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.opp_break_percentage > 0 THEN tss.opp_break_percentage * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.opp_break_percentage > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as break_percentage,
                CASE WHEN SUM(CASE WHEN tss.opp_d_line_conversion > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.opp_d_line_conversion > 0 THEN tss.opp_d_line_conversion * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.opp_d_line_conversion > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as d_line_conversion,
                CASE WHEN SUM(CASE WHEN tss.opp_red_zone_conversion > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.opp_red_zone_conversion > 0 THEN tss.opp_red_zone_conversion * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.opp_red_zone_conversion > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as red_zone_conversion
            FROM team_season_stats tss
            JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
            GROUP BY tss.team_id
            """
        else:
            return """
            SELECT
                tss.team_id,
                MIN(t.name) as name,
                MIN(t.full_name) as full_name,
                SUM(tss.games_played) as games_played,
                SUM(tss.wins) as wins,
                SUM(tss.losses) as losses,
                SUM(tss.scores) as scores,
                SUM(tss.scores_against) as scores_against,
                SUM(tss.completions) as completions,
                SUM(tss.turnovers) as turnovers,
                CASE WHEN SUM(tss.throw_attempts) > 0
                    THEN ROUND((CAST(SUM(tss.completions) AS NUMERIC) / SUM(tss.throw_attempts)) * 100, 2)
                    ELSE 0
                END as completion_percentage,
                SUM(tss.hucks_completed) as hucks_completed,
                SUM(COALESCE(tss.hucks_attempted, 0)) as hucks_attempted,
                SUM(CASE WHEN tss.year >= 2021 THEN tss.games_played ELSE 0 END) as games_with_huck_stats,
                CASE WHEN SUM(tss.hucks_attempted) > 0
                    THEN ROUND((CAST(SUM(tss.hucks_completed) AS NUMERIC) / SUM(tss.hucks_attempted)) * 100, 2)
                    ELSE 0
                END as huck_percentage,
                SUM(tss.blocks) as blocks,
                SUM(COALESCE(tss.o_line_scores, 0)) as o_line_scores,
                SUM(COALESCE(tss.d_line_scores, 0)) as d_line_scores,
                SUM(CASE WHEN tss.year >= 2014 THEN tss.games_played ELSE 0 END) as games_with_possession_stats,
                -- Use games-weighted average for possession stats (2014-2019 don't have accurate raw counts)
                CASE WHEN SUM(CASE WHEN tss.hold_percentage > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.hold_percentage > 0 THEN tss.hold_percentage * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.hold_percentage > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as hold_percentage,
                CASE WHEN SUM(CASE WHEN tss.o_line_conversion > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.o_line_conversion > 0 THEN tss.o_line_conversion * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.o_line_conversion > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as o_line_conversion,
                CASE WHEN SUM(CASE WHEN tss.break_percentage > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.break_percentage > 0 THEN tss.break_percentage * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.break_percentage > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as break_percentage,
                CASE WHEN SUM(CASE WHEN tss.d_line_conversion > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.d_line_conversion > 0 THEN tss.d_line_conversion * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.d_line_conversion > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as d_line_conversion,
                CASE WHEN SUM(CASE WHEN tss.red_zone_conversion > 0 THEN tss.games_played ELSE 0 END) > 0
                    THEN ROUND(
                        SUM(CASE WHEN tss.red_zone_conversion > 0 THEN tss.red_zone_conversion * tss.games_played ELSE 0 END) /
                        SUM(CASE WHEN tss.red_zone_conversion > 0 THEN tss.games_played ELSE 0 END)
                    , 2)
                    ELSE 0
                END as red_zone_conversion
            FROM team_season_stats tss
            JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
            GROUP BY tss.team_id
            """

    def _build_season_stats_query(self, is_opponent_view: bool) -> str:
        """
        Build SQL query for single season team stats.

        Args:
            is_opponent_view: Whether to show opponent stats

        Returns:
            SQL query string
        """
        if is_opponent_view:
            return """
            SELECT
                tss.team_id,
                t.name,
                t.full_name,
                tss.games_played,
                tss.wins,
                tss.losses,
                tss.scores,
                tss.scores_against,
                tss.opp_completions as completions,
                tss.opp_turnovers as turnovers,
                CASE WHEN tss.opp_throw_attempts > 0
                    THEN ROUND((CAST(tss.opp_completions AS NUMERIC) / tss.opp_throw_attempts) * 100, 2)
                    ELSE 0
                END as completion_percentage,
                tss.opp_hucks_completed as hucks_completed,
                COALESCE(tss.opp_hucks_attempted, 0) as hucks_attempted,
                CASE WHEN tss.year >= 2021 THEN tss.games_played ELSE 0 END as games_with_huck_stats,
                CASE WHEN tss.opp_hucks_attempted > 0
                    THEN ROUND((CAST(tss.opp_hucks_completed AS NUMERIC) / tss.opp_hucks_attempted) * 100, 2)
                    ELSE 0
                END as huck_percentage,
                tss.opp_blocks as blocks,
                COALESCE(tss.opp_o_line_scores, 0) as o_line_scores,
                COALESCE(tss.opp_d_line_scores, 0) as d_line_scores,
                CASE WHEN tss.year >= 2014 THEN tss.games_played ELSE 0 END as games_with_possession_stats,
                tss.opp_hold_percentage as hold_percentage,
                tss.opp_o_line_conversion as o_line_conversion,
                tss.opp_break_percentage as break_percentage,
                tss.opp_d_line_conversion as d_line_conversion,
                tss.opp_red_zone_conversion as red_zone_conversion
            FROM team_season_stats tss
            JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
            WHERE tss.year = :season
            """
        else:
            return """
            SELECT
                tss.team_id,
                t.name,
                t.full_name,
                tss.games_played,
                tss.wins,
                tss.losses,
                tss.scores,
                tss.scores_against,
                tss.completions,
                tss.turnovers,
                CASE WHEN tss.throw_attempts > 0
                    THEN ROUND((CAST(tss.completions AS NUMERIC) / tss.throw_attempts) * 100, 2)
                    ELSE 0
                END as completion_percentage,
                tss.hucks_completed,
                COALESCE(tss.hucks_attempted, 0) as hucks_attempted,
                CASE WHEN tss.year >= 2021 THEN tss.games_played ELSE 0 END as games_with_huck_stats,
                CASE WHEN tss.hucks_attempted > 0
                    THEN ROUND((CAST(tss.hucks_completed AS NUMERIC) / tss.hucks_attempted) * 100, 2)
                    ELSE 0
                END as huck_percentage,
                tss.blocks,
                COALESCE(tss.o_line_scores, 0) as o_line_scores,
                COALESCE(tss.d_line_scores, 0) as d_line_scores,
                CASE WHEN tss.year >= 2014 THEN tss.games_played ELSE 0 END as games_with_possession_stats,
                tss.hold_percentage,
                tss.o_line_conversion,
                tss.break_percentage,
                tss.d_line_conversion,
                tss.red_zone_conversion
            FROM team_season_stats tss
            JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
            WHERE tss.year = :season
            """

    def _apply_per_game_calculations(
        self, teams: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Apply per-game calculations to team stats.

        Args:
            teams: List of team statistics

        Returns:
            Teams with per-game statistics
        """
        for team in teams:
            if team["games_played"] > 0:
                games = team["games_played"]
                # Divide totals by games played
                team["scores"] = round(team["scores"] / games, 2)
                team["scores_against"] = round(team["scores_against"] / games, 2)
                team["completions"] = round(team["completions"] / games, 2)
                team["turnovers"] = round(team["turnovers"] / games, 2)

                # Use games_with_possession_stats for possession columns (2014+ only)
                possession_games = team.get("games_with_possession_stats", 0)
                if possession_games > 0:
                    team["blocks"] = round(team["blocks"] / possession_games, 2)
                    team["o_line_scores"] = round(
                        team["o_line_scores"] / possession_games, 2
                    )
                    team["d_line_scores"] = round(
                        team["d_line_scores"] / possession_games, 2
                    )
                else:
                    # No possession stats available for this team
                    team["blocks"] = None
                    team["o_line_scores"] = None
                    team["d_line_scores"] = None

                # Use games_with_huck_stats for huck columns (2021+ only)
                huck_games = team.get("games_with_huck_stats", 0)
                if huck_games > 0:
                    team["hucks_completed"] = round(
                        team["hucks_completed"] / huck_games, 2
                    )
                    team["hucks_attempted"] = round(
                        team["hucks_attempted"] / huck_games, 2
                    )
                else:
                    # No huck stats available for this team
                    team["hucks_completed"] = None
                    team["hucks_attempted"] = None

                # Note: Percentages stay the same in per-game view

        return teams
