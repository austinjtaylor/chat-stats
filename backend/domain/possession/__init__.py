"""
Possession and redzone tracking domain module.
Provides calculators, processors, and aggregators for UFA-style statistics.
"""

from .aggregators import TeamStatsAggregator
from .calculators import PossessionCalculator, RedzoneCalculator
from .models import (
    EventProcessorState,
    Point,
    PossessionStats,
    RedzonePossession,
    RedzoneStats,
)
from .processors import PossessionEventProcessor, RedzoneEventProcessor

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
