"""
Quarter score service for calculating quarterly game progression.
"""

from typing import Dict, List


def calculate_quarter_scores(stats_system, game_id: str) -> Dict[str, List[int]]:
    """
    Calculate quarter-by-quarter scores from game events.
    Returns cumulative scores at the end of each quarter.
    """
    # For MVP, return simulated quarter scores based on final score
    # In production, this would parse game_events table for actual quarterly progression

    game_query = """
    SELECT home_score, away_score
    FROM games
    WHERE game_id = :game_id
    """

    result = stats_system.db.execute_query(game_query, {"game_id": game_id})
    if not result:
        return {"home": [], "away": []}

    game = result[0]
    home_final = game["home_score"] or 0
    away_final = game["away_score"] or 0

    # Simulate progressive scoring across 4 quarters
    # This is a placeholder - real implementation would use game_events
    home_quarters = []
    away_quarters = []

    if home_final > 0:
        # Distribute scores across quarters (simple distribution for MVP)
        q1_home = max(1, home_final // 4)
        q2_home = max(q1_home + 1, home_final // 2)
        q3_home = max(q2_home + 1, (home_final * 3) // 4)
        q4_home = home_final
        home_quarters = [q1_home, q2_home, q3_home, q4_home]
    else:
        home_quarters = [0, 0, 0, 0]

    if away_final > 0:
        q1_away = max(1, away_final // 4)
        q2_away = max(q1_away + 1, away_final // 2)
        q3_away = max(q2_away + 1, (away_final * 3) // 4)
        q4_away = away_final
        away_quarters = [q1_away, q2_away, q3_away, q4_away]
    else:
        away_quarters = [0, 0, 0, 0]

    return {
        "home": home_quarters,
        "away": away_quarters
    }