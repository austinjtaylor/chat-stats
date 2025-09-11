"""
Test query helper functions.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.query import convert_to_per_game_stats, get_sort_column


class TestGetSortColumn:
    """Test get_sort_column function"""

    def test_default_sort_by_points(self):
        """Test default sorting by points"""
        column = get_sort_column(None)
        assert column == "(pss.goals + pss.assists)"

    def test_sort_by_goals(self):
        """Test sorting by goals"""
        column = get_sort_column("goals")
        assert column == "pss.goals"

    def test_sort_by_assists(self):
        """Test sorting by assists"""
        column = get_sort_column("assists")
        assert column == "pss.assists"

    def test_sort_by_blocks(self):
        """Test sorting by blocks"""
        column = get_sort_column("blocks")
        assert column == "pss.blocks"

    def test_sort_by_completions(self):
        """Test sorting by completions"""
        column = get_sort_column("completions")
        assert column == "pss.completions"

    def test_sort_by_completion_percentage(self):
        """Test sorting by completion percentage"""
        column = get_sort_column("completion%")
        assert column == "pss.completion_percentage"

        # Also test with full name
        column = get_sort_column("completion_percentage")
        assert column == "pss.completion_percentage"

    def test_sort_by_plus_minus(self):
        """Test sorting by plus/minus"""
        column = get_sort_column("+/-")
        assert column == "pss.plus_minus"

        # Also test with alternative name
        column = get_sort_column("plus_minus")
        assert column == "pss.plus_minus"

    def test_sort_by_turnovers(self):
        """Test sorting by turnovers"""
        column = get_sort_column("turnovers")
        assert column == "pss.turnovers"

    def test_sort_by_throwaways(self):
        """Test sorting by throwaways"""
        column = get_sort_column("throwaways")
        assert column == "pss.throwaways"

    def test_sort_by_points_played(self):
        """Test sorting by points played"""
        column = get_sort_column("points_played")
        assert column == "pss.points_played"

    def test_sort_by_minutes_played(self):
        """Test sorting by minutes played"""
        column = get_sort_column("minutes_played")
        assert column == "pss.minutes_played"

    def test_sort_by_invalid_column(self):
        """Test sorting by invalid column defaults to points"""
        column = get_sort_column("invalid_column")
        assert column == "(pss.goals + pss.assists)"

    def test_sort_case_insensitive(self):
        """Test case-insensitive sorting"""
        column = get_sort_column("GOALS")
        assert column == "pss.goals"

        column = get_sort_column("Assists")
        assert column == "pss.assists"

    def test_sort_with_whitespace(self):
        """Test sorting with whitespace"""
        column = get_sort_column("  goals  ")
        assert column == "pss.goals"


class TestConvertToPerGameStats:
    """Test convert_to_per_game_stats function"""

    def test_convert_single_player(self):
        """Test converting stats for single player"""
        stats = [
            {
                "name": "Test Player",
                "goals": 20,
                "assists": 10,
                "blocks": 5,
                "games_played": 10,
            }
        ]

        result = convert_to_per_game_stats(stats)

        assert len(result) == 1
        assert result[0]["name"] == "Test Player"
        assert result[0]["goals"] == 2.0  # 20/10
        assert result[0]["assists"] == 1.0  # 10/10
        assert result[0]["blocks"] == 0.5  # 5/10

    def test_convert_multiple_players(self):
        """Test converting stats for multiple players"""
        stats = [
            {"name": "Player 1", "goals": 30, "assists": 15, "games_played": 15},
            {"name": "Player 2", "goals": 20, "assists": 20, "games_played": 10},
        ]

        result = convert_to_per_game_stats(stats)

        assert len(result) == 2
        assert result[0]["goals"] == 2.0  # 30/15
        assert result[0]["assists"] == 1.0  # 15/15
        assert result[1]["goals"] == 2.0  # 20/10
        assert result[1]["assists"] == 2.0  # 20/10

    def test_convert_with_zero_games(self):
        """Test handling of zero games played"""
        stats = [{"name": "Test Player", "goals": 10, "assists": 5, "games_played": 0}]

        result = convert_to_per_game_stats(stats)

        # Should handle division by zero gracefully
        assert result[0]["goals"] == 0
        assert result[0]["assists"] == 0

    def test_convert_missing_games_played(self):
        """Test handling of missing games_played field"""
        stats = [{"name": "Test Player", "goals": 10, "assists": 5}]

        result = convert_to_per_game_stats(stats)

        # Should return original values if games_played is missing
        assert result[0]["goals"] == 10
        assert result[0]["assists"] == 5

    def test_convert_preserves_non_numeric_fields(self):
        """Test that non-numeric fields are preserved"""
        stats = [
            {
                "name": "Test Player",
                "team": "Test Team",
                "position": "Cutter",
                "goals": 10,
                "games_played": 5,
            }
        ]

        result = convert_to_per_game_stats(stats)

        assert result[0]["name"] == "Test Player"
        assert result[0]["team"] == "Test Team"
        assert result[0]["position"] == "Cutter"
        assert result[0]["goals"] == 2.0

    def test_convert_rounds_to_two_decimals(self):
        """Test that per-game stats are rounded to 2 decimals"""
        stats = [{"name": "Test Player", "goals": 7, "assists": 10, "games_played": 3}]

        result = convert_to_per_game_stats(stats)

        assert result[0]["goals"] == 2.33  # 7/3 rounded to 2 decimals
        assert result[0]["assists"] == 3.33  # 10/3 rounded to 2 decimals

    def test_empty_stats_list(self):
        """Test handling of empty stats list"""
        stats = []

        result = convert_to_per_game_stats(stats)

        assert result == []

    def test_convert_with_null_values(self):
        """Test handling of null values"""
        stats = [
            {"name": "Test Player", "goals": None, "assists": 5, "games_played": 10}
        ]

        result = convert_to_per_game_stats(stats)

        assert result[0]["goals"] == 0  # None should be treated as 0
        assert result[0]["assists"] == 0.5

    def test_convert_all_stat_fields(self):
        """Test conversion of all statistical fields"""
        stats = [
            {
                "name": "Test Player",
                "goals": 20,
                "assists": 15,
                "blocks": 10,
                "completions": 100,
                "throwaways": 5,
                "turnovers": 8,
                "touches": 150,
                "hockey_assists": 12,
                "callahans": 2,
                "drops": 3,
                "games_played": 10,
            }
        ]

        result = convert_to_per_game_stats(stats)

        assert result[0]["goals"] == 2.0
        assert result[0]["assists"] == 1.5
        assert result[0]["blocks"] == 1.0
        assert result[0]["completions"] == 10.0
        assert result[0]["throwaways"] == 0.5
        assert result[0]["turnovers"] == 0.8
        assert result[0]["touches"] == 15.0
        assert result[0]["hockey_assists"] == 1.2
        assert result[0]["callahans"] == 0.2
        assert result[0]["drops"] == 0.3
