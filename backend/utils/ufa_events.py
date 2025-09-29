"""
UFA Event Type Constants
Based on UFA API Documentation
"""

# Event type ID to name mapping
EVENT_TYPES = {
    1: "START_D_POINT",  # Team starts on defense (pulls)
    2: "START_O_POINT",  # Team starts on offense (receives)
    3: "TIMEOUT_MID_RECORDING",
    4: "TIMEOUT_BETWEEN_RECORDING",
    5: "TIMEOUT_MID_OPPOSING",
    6: "TIMEOUT_BETWEEN_OPPOSING",
    7: "PULL_INBOUNDS",
    8: "PULL_OUT_OF_BOUNDS",
    9: "OFFSIDES_RECORDING",
    10: "OFFSIDES_OPPOSING",
    11: "BLOCK",
    12: "CALLAHAN_BY_OPPOSING",
    13: "THROWAWAY_BY_OPPOSING",
    14: "STALL_ON_OPPOSING",
    15: "SCORE_BY_OPPOSING",  # Opponent scores
    16: "PENALTY_ON_RECORDING",
    17: "PENALTY_ON_OPPOSING",
    18: "PASS",
    19: "GOAL",  # Recording team scores
    20: "DROP",
    21: "DROPPED_PULL",
    22: "THROWAWAY",
    23: "CALLAHAN",
    24: "STALL",
    25: "INJURY",
    26: "PLAYER_MISCONDUCT",
    27: "PLAYER_EJECTED",
    28: "END_FIRST_QUARTER",
    29: "HALFTIME",
    30: "END_THIRD_QUARTER",
    31: "END_REGULATION",
    32: "END_FIRST_OT",
    33: "END_SECOND_OT",
    34: "DELAYED",
    35: "POSTPONED",
}

# Reverse mapping for convenience
EVENT_NAMES_TO_IDS = {v: k for k, v in EVENT_TYPES.items()}

# Event categories for easier processing
POINT_START_EVENTS = {1, 2}  # START_D_POINT, START_O_POINT
POINT_END_EVENTS = {15, 19}  # SCORE_BY_OPPOSING, GOAL
TURNOVER_EVENTS = {
    11,
    13,
    20,
    22,
    24,
}  # BLOCK, THROWAWAY_BY_OPP, DROP, THROWAWAY, STALL
POSSESSION_EVENTS = {18, 19}  # PASS, GOAL
QUARTER_END_EVENTS = {28, 29, 30, 31}  # Quarter/half/regulation ends


def get_event_name(event_type_id: int) -> str:
    """Get the name of an event type by its ID"""
    return EVENT_TYPES.get(event_type_id, f"UNKNOWN_{event_type_id}")


def is_point_start(event_type_id: int) -> bool:
    """Check if an event starts a new point"""
    return event_type_id in POINT_START_EVENTS


def is_point_end(event_type_id: int) -> bool:
    """Check if an event ends a point"""
    return event_type_id in POINT_END_EVENTS


def is_turnover(event_type_id: int) -> bool:
    """Check if an event is a turnover"""
    return event_type_id in TURNOVER_EVENTS


def is_possession_event(event_type_id: int) -> bool:
    """Check if an event indicates possession (pass or goal)"""
    return event_type_id in POSSESSION_EVENTS
