"""
Chat system service modules.

Refactored from a single 707-line file into focused service modules:
- database_stats.py: Database statistics, health checks, and analytics (280 lines)
- search.py: Player/team search and recent games (72 lines)
- team_stats.py: Comprehensive team statistics (254 lines)
- data_import.py: Data import functionality (65 lines)

Total: 671 lines across 4 service modules (was 707 lines in 1 monolithic file)
All modules under 300 lines with clear separation of concerns.
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
