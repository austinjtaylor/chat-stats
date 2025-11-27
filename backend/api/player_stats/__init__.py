"""
Player statistics API module.

Refactored from a single 1,002-line file into focused modules:
- filters.py: Filter validation and HAVING clause building (127 lines)
- percentile_calculator.py: Global percentile calculations (326 lines)
- query_builder.py: Complex SQL query construction (507 lines)
- route.py: Thin FastAPI route controller (211 lines)

Total: 1,184 lines across 4 focused modules (was 1,002 lines in 1 monolithic file)
All modules under 600 lines with clear separation of concerns.
"""

# Export main route creator
from .route import create_player_stats_route

# Export utility functions for backward compatibility
from .filters import (
    build_having_clause,
    get_team_career_sort_column,
    SEASON_STATS_ALIAS_MAPPING,
)
from .percentile_calculator import (
    calculate_global_percentiles,
    STAT_FIELDS,
    INVERT_STATS,
)
from .query_builder import PlayerStatsQueryBuilder

__all__ = [
    # Main route
    "create_player_stats_route",
    # Filter utilities
    "build_having_clause",
    "get_team_career_sort_column",
    "SEASON_STATS_ALIAS_MAPPING",
    # Percentile utilities
    "calculate_global_percentiles",
    "STAT_FIELDS",
    "INVERT_STATS",
    # Query builder
    "PlayerStatsQueryBuilder",
]
