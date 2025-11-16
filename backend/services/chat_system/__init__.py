"""
Chat system service modules.

Refactored from a single 707-line file into focused service modules:
- database_stats.py: Database statistics, health checks, and analytics (271 lines)
- search.py: Player/team search and recent games (78 lines)
- team_stats.py: Comprehensive team statistics (252 lines)
- data_import.py: Data import functionality (71 lines)

Total: 672 lines across 4 service modules (was 707 lines in 1 monolithic file)
All modules under 275 lines with clear separation of concerns.
"""

from .database_stats import DatabaseStatsService
from .search import SearchService
from .team_stats import TeamStatsService
from .data_import import DataImportService

__all__ = [
    "DatabaseStatsService",
    "SearchService",
    "TeamStatsService",
    "DataImportService",
]
