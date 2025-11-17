"""
Possession and redzone tracking domain module.
Provides calculators, processors, and aggregators for UFA-style statistics.
"""

from .calculators import PossessionCalculator, RedzoneCalculator
from .aggregators import TeamStatsAggregator
from .processors import PossessionEventProcessor, RedzoneEventProcessor
from .models import (
    Point,
    RedzonePossession,
    PossessionStats,
    RedzoneStats,
    EventProcessorState,
)

__all__ = [
    # Calculators
    "PossessionCalculator",
    "RedzoneCalculator",
    # Aggregators
    "TeamStatsAggregator",
    # Processors
    "PossessionEventProcessor",
    "RedzoneEventProcessor",
    # Models
    "Point",
    "RedzonePossession",
    "PossessionStats",
    "RedzoneStats",
    "EventProcessorState",
]
