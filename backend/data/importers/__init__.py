"""
Data importer modules.

Refactored from a single 419-line StatsProcessor class into focused importer modules:
- team_importer.py: Team data import (54 lines)
- player_importer.py: Player data import (64 lines)
- game_importer.py: Game data import (72 lines)
- stats_importer.py: Player game statistics import (68 lines)
- season_stats_calculator.py: Season statistics calculation (170 lines)

Total: 428 lines across 5 importer modules
Extracted from monolithic processor for better organization and testability.
"""

from .game_importer import GameImporter
from .player_importer import PlayerImporter
from .season_stats_calculator import SeasonStatsCalculator
from .stats_importer import StatsImporter
from .team_importer import TeamImporter

__all__ = [
    "TeamImporter",
    "PlayerImporter",
    "GameImporter",
    "StatsImporter",
    "SeasonStatsCalculator",
]
