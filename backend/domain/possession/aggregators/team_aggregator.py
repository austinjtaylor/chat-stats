"""
Team statistics aggregator for possession and redzone metrics.
Combines multiple statistics sources and calculates percentages.
"""

from typing import Any

from utils.stats import calculate_percentage

from ..calculators.possession_calculator import PossessionCalculator
from ..calculators.redzone_calculator import RedzoneCalculator


class TeamStatsAggregator:
    """Aggregates possession and redzone statistics for teams."""

    def __init__(self, db):
        """
        Initialize the aggregator.

        Args:
            db: Database connection
        """
        self.db = db
        self.possession_calc = PossessionCalculator(db)
        self.redzone_calc = RedzoneCalculator(db)

    def calculate_combined_stats(
        self, game_id: str, team_id: str, is_home_team: bool
    ) -> dict[str, Any]:
        """
        Calculate both possession and redzone statistics in a single operation.
        Optimized to minimize database queries.

        Args:
            game_id: Game identifier
            team_id: Team identifier
            is_home_team: Whether this is the home team

        Returns:
            Dictionary containing both possession and redzone statistics
        """
        possession_stats = self.possession_calc.calculate_for_game(
            game_id, team_id, is_home_team
        )
        redzone_stats = self.redzone_calc.calculate_for_team(
            game_id, team_id, is_home_team
        )

        return {"possession": possession_stats, "redzone": redzone_stats}

    @staticmethod
    def calculate_team_percentages(
        stats: dict[str, Any], opponent_stats: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Calculate various percentage statistics for a team.

        Args:
            stats: Team statistics dictionary
            opponent_stats: Optional opponent statistics for relative calculations

        Returns:
            Updated stats dictionary with calculated percentages
        """
        if not stats:
            return stats

        # Basic percentages with fractions
        if stats.get("total_attempts", 0) > 0:
            pct, display = calculate_percentage(
                stats["total_completions"], stats["total_attempts"]
            )
            stats["completion_percentage"] = pct
            stats["completion_percentage_display"] = display
        else:
            stats["completion_percentage"] = 0
            stats["completion_percentage_display"] = "0% (0/0)"

        if stats.get("total_hucks_attempted", 0) > 0:
            pct, display = calculate_percentage(
                stats["total_hucks_completed"], stats["total_hucks_attempted"]
            )
            stats["huck_percentage"] = pct
            stats["huck_percentage_display"] = display
        else:
            stats["huck_percentage"] = 0
            stats["huck_percentage_display"] = "0% (0/0)"

        # Check if we have valid possession data from game events
        has_valid_possession_data = (
            "o_line_points" in stats
            and stats.get("o_line_points", 0) > 0
            and stats.get("d_line_points", 0) > 0
        )

        if has_valid_possession_data:
            # UFA-exact possession-based statistics
            # Hold % = O-line scores / O-line points
            if stats["o_line_points"] > 0:
                pct, display = calculate_percentage(
                    stats["o_line_scores"], stats["o_line_points"]
                )
                stats["hold_percentage"] = pct
                stats["hold_percentage_display"] = display
            else:
                stats["hold_percentage"] = 0
                stats["hold_percentage_display"] = "0% (0/0)"

            # O-Line Conversion % = O-line scores / O-line possessions
            if stats.get("o_line_possessions", 0) > 0:
                pct, display = calculate_percentage(
                    stats["o_line_scores"], stats["o_line_possessions"]
                )
                stats["o_conversion"] = pct
                stats["o_conversion_display"] = display
            else:
                stats["o_conversion"] = 0
                stats["o_conversion_display"] = "0% (0/0)"

            # Break % = D-line scores / D-line points
            if stats["d_line_points"] > 0:
                pct, display = calculate_percentage(
                    stats["d_line_scores"], stats["d_line_points"]
                )
                stats["break_percentage"] = pct
                stats["break_percentage_display"] = display
            else:
                stats["break_percentage"] = 0
                stats["break_percentage_display"] = "0% (0/0)"

            # D-Line Conversion % = D-line scores / D-line conversions
            if stats.get("d_line_conversions", 0) > 0:
                pct, display = calculate_percentage(
                    stats["d_line_scores"], stats["d_line_conversions"]
                )
                stats["d_conversion"] = pct
                stats["d_conversion_display"] = display
            else:
                stats["d_conversion"] = 0
                stats["d_conversion_display"] = "0% (0/0)"

        else:
            # Fallback to player_game_stats calculation when game_events data not available
            if stats.get("total_o_points", 0) > 0:
                pct, display = calculate_percentage(
                    stats["total_o_scores"], stats["total_o_points"]
                )
                stats["hold_percentage"] = pct
                stats["hold_percentage_display"] = display
                stats["o_conversion"] = pct
                stats["o_conversion_display"] = display
            else:
                stats["hold_percentage"] = 0
                stats["hold_percentage_display"] = "0% (0/0)"
                stats["o_conversion"] = 0
                stats["o_conversion_display"] = "0% (0/0)"

            if stats.get("total_d_points", 0) > 0:
                pct, display = calculate_percentage(
                    stats["total_d_scores"], stats["total_d_points"]
                )
                stats["break_percentage"] = pct
                stats["break_percentage_display"] = display
                stats["d_conversion"] = pct
                stats["d_conversion_display"] = display
            else:
                stats["break_percentage"] = 0
                stats["break_percentage_display"] = "0% (0/0)"
                stats["d_conversion"] = 0
                stats["d_conversion_display"] = "0% (0/0)"

        return stats
