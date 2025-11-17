"""
Possession and redzone calculation utilities for Ultimate Frisbee statistics.
Implements UFA-style possession tracking and conversion percentages.

This module now serves as a thin wrapper around the refactored domain modules
for backward compatibility.
"""

from typing import Any, Dict, List, Optional

from domain.possession import (
    PossessionCalculator,
    RedzoneCalculator,
    TeamStatsAggregator,
    PossessionEventProcessor,
    RedzoneEventProcessor,
)


# ===== PUBLIC API FUNCTIONS =====
# These functions maintain backward compatibility with the original API


def calculate_possessions(
    db, game_id: str, team_id: str, is_home_team: bool
) -> Optional[Dict[str, Any]]:
    """
    Calculate possession-based statistics matching UFA methodology exactly.

    Args:
        db: Database connection
        game_id: Game identifier
        team_id: Team identifier
        is_home_team: Whether this is the home team

    Returns:
        Dictionary with possession statistics or None if no events
    """
    calculator = PossessionCalculator(db)
    return calculator.calculate_for_game(game_id, team_id, is_home_team)


def calculate_team_stats_combined(
    db, game_id: str, team_id: str, is_home_team: bool
) -> Dict[str, Any]:
    """
    Calculate both possession and redzone statistics in a single pass.
    Optimized to fetch game_events once and process both metrics together.

    Args:
        db: Database connection
        game_id: Game identifier
        team_id: Team identifier
        is_home_team: Whether this is the home team

    Returns:
        Dictionary containing both possession and redzone statistics
    """
    aggregator = TeamStatsAggregator(db)
    return aggregator.calculate_combined_stats(game_id, team_id, is_home_team)


def calculate_redzone_stats_for_team(
    db, game_id: str, team_id: str, is_home_team: bool
) -> Dict[str, Any]:
    """
    Calculate redzone statistics for a single team in a game.

    Args:
        db: Database connection
        game_id: Game identifier
        team_id: Team identifier
        is_home_team: Whether this is the home team

    Returns:
        Dictionary with redzone statistics
    """
    calculator = RedzoneCalculator(db)
    return calculator.calculate_for_team(game_id, team_id, is_home_team)


def calculate_team_percentages(
    stats: Dict[str, Any], opponent_stats: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Calculate various percentage statistics for a team.

    Args:
        stats: Team statistics dictionary
        opponent_stats: Optional opponent statistics for relative calculations

    Returns:
        Updated stats dictionary with calculated percentages
    """
    return TeamStatsAggregator.calculate_team_percentages(stats, opponent_stats)


def calculate_redzone_stats(game_id: str) -> dict:
    """
    Calculate red zone conversion statistics for both teams in a game.

    Args:
        game_id: Game identifier

    Returns:
        Dictionary with redzone stats for both home and away teams
    """
    from data.database import get_db

    db = get_db()
    calculator = RedzoneCalculator(db)
    return calculator.calculate_for_game(game_id)


def _process_possession_events(
    events: List[Dict[str, Any]], team_type: str, opponent_type: str
) -> Dict[str, Any]:
    """
    Process a list of events to calculate possession stats.
    Extracted core logic for reuse in batch processing.

    Args:
        events: List of game events (already filtered for this team)
        team_type: 'home' or 'away'
        opponent_type: 'away' or 'home'

    Returns:
        Dictionary with possession statistics
    """
    processor = PossessionEventProcessor(team_type)
    stats = processor.process_events(events)
    return stats.to_dict()


def calculate_possessions_batch(
    db, team_ids: List[str], season_filter: str = "", season_param: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate possession statistics for multiple teams in a single batch query.
    Optimized to avoid N+1 query problem.

    Args:
        db: Database connection
        team_ids: List of team IDs to calculate stats for
        season_filter: SQL filter for season
        season_param: Season year parameter

    Returns:
        Dictionary mapping team_id to possession stats
    """
    calculator = PossessionCalculator(db)
    return calculator.calculate_batch(team_ids, season_filter, season_param)


def _process_redzone_events(
    events: List[Dict[str, Any]], team_type: str, opponent_type: str
) -> Dict[str, Any]:
    """
    Process a list of events to calculate redzone stats.
    Extracted core logic for reuse in batch processing.

    Args:
        events: List of game events with position data
        team_type: 'home' or 'away'
        opponent_type: 'away' or 'home'

    Returns:
        Dictionary with redzone statistics
    """
    processor = RedzoneEventProcessor(team_type)
    stats = processor.process_events(events)
    return stats.to_dict()


def calculate_redzone_stats_batch(
    db, team_ids: List[str], season_filter: str = "", season_param: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate redzone statistics for multiple teams in a single batch query.

    Args:
        db: Database connection
        team_ids: List of team IDs
        season_filter: SQL filter for season
        season_param: Season year parameter

    Returns:
        Dictionary mapping team_id to redzone stats
    """
    calculator = RedzoneCalculator(db)
    return calculator.calculate_batch(team_ids, season_filter, season_param)


# ===== BACKWARD COMPATIBILITY EXPORTS =====
# Export all public functions for backward compatibility

__all__ = [
    "calculate_possessions",
    "calculate_team_stats_combined",
    "calculate_redzone_stats_for_team",
    "calculate_team_percentages",
    "calculate_redzone_stats",
    "calculate_possessions_batch",
    "calculate_redzone_stats_batch",
    "_process_possession_events",
    "_process_redzone_events",
]
