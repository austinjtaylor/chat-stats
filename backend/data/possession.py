"""
Possession and redzone calculation utilities for Ultimate Frisbee statistics.
Implements UFA-style possession tracking and conversion percentages.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional

from utils.stats import calculate_percentage
from utils.ufa_events import (
    is_point_end,
    is_point_start,
    is_turnover,
)


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
    # Get events from THIS team's perspective only
    # Each team records their own goals (19) and opponent goals (15)
    events_query = """
    SELECT event_index, event_type, team
    FROM game_events
    WHERE game_id = :game_id
      AND team = :team_type
    ORDER BY event_index, 
        CASE 
            WHEN event_type IN (19, 15) THEN 0  -- Goals first (both team and opponent)
            WHEN event_type = 1 THEN 1          -- Then pulls
            ELSE 2                               -- Then other events
        END
    """
    team_type = "home" if is_home_team else "away"
    opponent_type = "away" if is_home_team else "home"
    events = db.execute_query(events_query, {"game_id": game_id, "team_type": team_type})

    if not events:
        return None

    # Group events by point (between pulls)
    points = []
    current_point = None
    current_possession = None
    point_had_action = False  # Track if point had actual game play

    for event in events:
        event_type = event["event_type"]
        
        # START_D_POINT (1) - This team pulls, opponent receives
        if event_type == 1:  # Team pulls (D-point for team)
            # Save previous point if exists and it had actual game action
            # UFA doesn't count "empty" points (e.g., pull followed immediately by another pull)
            if current_point and point_had_action:
                points.append(current_point)

            # This team is pulling, opponent receives
            current_point = {
                "pulling_team": team_type,
                "receiving_team": opponent_type,
                "scoring_team": None,
                "team_possessions": 0,  # Team starts without possession
                "opponent_possessions": 1,  # Opponent starts with possession
            }
            current_possession = opponent_type
            point_had_action = False  # Reset for new point
            
        # START_O_POINT (2) - This team receives, opponent pulls
        elif event_type == 2:  # Team receives (O-point for team)
            # Save previous point if exists and it had actual game action
            if current_point and point_had_action:
                points.append(current_point)

            # This team receives, opponent pulls
            current_point = {
                "pulling_team": opponent_type,
                "receiving_team": team_type,
                "scoring_team": None,
                "team_possessions": 1,  # Team starts with possession
                "opponent_possessions": 0,
            }
            current_possession = team_type
            point_had_action = False  # Reset for new point

        # Goal ends the current point
        elif event_type == 19 and current_point:  # Team goal
            current_point["scoring_team"] = team_type  # This team scored
            point_had_action = True  # Goals count as game action
            # Don't append here, wait for next pull or end of events
            
        elif event_type == 15 and current_point:  # Opponent goal
            current_point["scoring_team"] = opponent_type  # Opponent scored
            point_had_action = True  # Goals count as game action
            # Don't append here, wait for next pull or end of events
        
        # Pass events indicate actual game play
        elif event_type == 18 and current_point:  # Pass
            point_had_action = True

        # Turnovers change possession
        # Event types: 11=Block, 20=Drop, 22=Throwaway, 24=Stall
        elif event_type in [11, 20, 22, 24] and current_point:
            point_had_action = True  # Turnovers count as game action
            # Determine who gets possession after turnover
            if event_type == 11:  # Block - this team blocks, gets possession
                new_possession = team_type
            else:  # Drop/Throwaway/Stall - this team loses possession
                new_possession = opponent_type

            # If possession changes, increment the appropriate counter
            if new_possession != current_possession:
                if new_possession == team_type:
                    current_point["team_possessions"] += 1
                else:
                    current_point["opponent_possessions"] += 1
                current_possession = new_possession
                
        # Opponent turnovers - Event type 13=Throwaway by opposing team
        elif event_type == 13 and current_point:
            point_had_action = True  # Turnovers count as game action
            # Opponent throws it away, this team gets possession
            new_possession = team_type
            
            if new_possession != current_possession:
                if new_possession == team_type:
                    current_point["team_possessions"] += 1
                else:
                    current_point["opponent_possessions"] += 1
                current_possession = new_possession

    # Add final point if exists and it had actual game action
    if current_point and point_had_action:
        points.append(current_point)

    # Calculate statistics from points
    o_line_points = 0
    o_line_scores = 0
    o_line_possessions = 0
    d_line_points = 0
    d_line_scores = 0
    d_line_possessions = 0

    for point in points:
        if point["receiving_team"] == team_type:
            # We received the pull - O-line point
            o_line_points += 1
            if point["scoring_team"] == team_type:
                o_line_scores += 1
            # Add possessions for this team during O-line points
            o_line_possessions += point["team_possessions"]

        elif point["pulling_team"] == team_type:
            # We pulled - D-line point
            d_line_points += 1
            if point["scoring_team"] == team_type:
                d_line_scores += 1
            # Add possessions (break opportunities) for this team during D-line points
            d_line_possessions += point["team_possessions"]

    return {
        "o_line_points": o_line_points,
        "o_line_scores": o_line_scores,
        "o_line_possessions": o_line_possessions,
        "d_line_points": d_line_points,
        "d_line_scores": d_line_scores,
        "d_line_possessions": d_line_possessions,
        "d_line_conversions": d_line_possessions,
    }


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
        Dictionary containing both possession and redzone statistics:
        {
            'possession': {...},  # Same format as calculate_possessions()
            'redzone': {...}      # Same format as calculate_redzone_stats_for_team()
        }
    """
    team_type = "home" if is_home_team else "away"
    opponent_type = "away" if is_home_team else "home"

    # Fetch events ONCE with all needed columns
    events_query = """
    SELECT event_index, event_type, team, receiver_y, thrower_y
    FROM game_events
    WHERE game_id = :game_id
      AND team = :team_type
    ORDER BY event_index,
        CASE
            WHEN event_type IN (19, 15) THEN 0  -- Goals first
            WHEN event_type = 1 THEN 1          -- Then pulls
            ELSE 2                               -- Then other events
        END
    """
    events = db.execute_query(events_query, {"game_id": game_id, "team_type": team_type})

    if not events:
        return {
            "possession": None,
            "redzone": None
        }

    # Track possession stats
    points = []
    current_point = None
    current_possession = None
    point_had_action = False

    # Track redzone stats
    redzone_possessions = []
    current_redzone_possession = None
    in_possession = False
    point_num = 0

    for event in events:
        event_type = event["event_type"]
        receiver_y = event.get("receiver_y")
        thrower_y = event.get("thrower_y")

        # === POSSESSION TRACKING ===
        if event_type == 1:  # START_D_POINT - Team pulls
            if current_point and point_had_action:
                points.append(current_point)
            current_point = {
                "pulling_team": team_type,
                "receiving_team": opponent_type,
                "scoring_team": None,
                "team_possessions": 0,
                "opponent_possessions": 1,
            }
            current_possession = opponent_type
            point_had_action = False

            # Redzone: D point start
            point_num += 1
            in_possession = False

        elif event_type == 2:  # START_O_POINT - Team receives
            if current_point and point_had_action:
                points.append(current_point)
            current_point = {
                "pulling_team": opponent_type,
                "receiving_team": team_type,
                "scoring_team": None,
                "team_possessions": 1,
                "opponent_possessions": 0,
            }
            current_possession = team_type
            point_had_action = False

            # Redzone: O point start - we have possession
            point_num += 1
            if current_redzone_possession:
                redzone_possessions.append(current_redzone_possession)
            current_redzone_possession = {
                "point": point_num,
                "reached_redzone": False,
                "scored": False,
            }
            in_possession = True

        elif event_type == 19 and current_point:  # Team goal
            current_point["scoring_team"] = team_type
            point_had_action = True

            # Redzone: Our goal
            if current_redzone_possession:
                current_redzone_possession["scored"] = True
                if thrower_y and 80 <= thrower_y <= 100:
                    current_redzone_possession["reached_redzone"] = True
                redzone_possessions.append(current_redzone_possession)
                current_redzone_possession = None
                in_possession = False

        elif event_type == 15 and current_point:  # Opponent goal
            current_point["scoring_team"] = opponent_type
            point_had_action = True

            # Redzone: Opponent scores
            if current_redzone_possession:
                redzone_possessions.append(current_redzone_possession)
                current_redzone_possession = None
                in_possession = False

        elif event_type == 18 and current_point:  # Pass
            point_had_action = True

            # Redzone: Check for redzone entry
            if not in_possession:
                if current_redzone_possession:
                    redzone_possessions.append(current_redzone_possession)
                current_redzone_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True

            if in_possession and current_redzone_possession and receiver_y:
                if 80 <= receiver_y <= 100:
                    current_redzone_possession["reached_redzone"] = True

        elif event_type in [11, 20, 22, 24] and current_point:  # Turnovers
            point_had_action = True

            # Possession tracking
            if event_type == 11:  # Block - we get possession
                new_possession = team_type
            else:  # Drop/Throwaway/Stall - we lose possession
                new_possession = opponent_type

            if new_possession != current_possession:
                if new_possession == team_type:
                    current_point["team_possessions"] += 1
                else:
                    current_point["opponent_possessions"] += 1
                current_possession = new_possession

            # Redzone tracking
            if event_type == 11:  # Block - we gain possession
                if not in_possession:
                    if current_redzone_possession:
                        redzone_possessions.append(current_redzone_possession)
                    current_redzone_possession = {
                        "point": point_num,
                        "reached_redzone": False,
                        "scored": False,
                    }
                    in_possession = True
            elif event_type in [20, 22, 24]:  # We lose possession
                if in_possession and current_redzone_possession:
                    redzone_possessions.append(current_redzone_possession)
                    current_redzone_possession = None
                    in_possession = False

        elif event_type == 13 and current_point:  # Opponent throwaway - we get possession
            point_had_action = True
            new_possession = team_type

            if new_possession != current_possession:
                if new_possession == team_type:
                    current_point["team_possessions"] += 1
                else:
                    current_point["opponent_possessions"] += 1
                current_possession = new_possession

            # Redzone: We gain possession
            if not in_possession:
                if current_redzone_possession:
                    redzone_possessions.append(current_redzone_possession)
                current_redzone_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True

    # Add final point and possession if exists
    if current_point and point_had_action:
        points.append(current_point)
    if current_redzone_possession:
        redzone_possessions.append(current_redzone_possession)

    # Calculate possession statistics
    o_line_points = 0
    o_line_scores = 0
    o_line_possessions = 0
    d_line_points = 0
    d_line_scores = 0
    d_line_possessions = 0

    for point in points:
        if point["receiving_team"] == team_type:
            o_line_points += 1
            if point["scoring_team"] == team_type:
                o_line_scores += 1
            o_line_possessions += point["team_possessions"]
        elif point["pulling_team"] == team_type:
            d_line_points += 1
            if point["scoring_team"] == team_type:
                d_line_scores += 1
            d_line_possessions += point["team_possessions"]

    possession_stats = {
        "o_line_points": o_line_points,
        "o_line_scores": o_line_scores,
        "o_line_possessions": o_line_possessions,
        "d_line_points": d_line_points,
        "d_line_scores": d_line_scores,
        "d_line_possessions": d_line_possessions,
        "d_line_conversions": d_line_possessions,
    } if points else None

    # Calculate redzone statistics
    redzone_opportunities = [p for p in redzone_possessions if p["reached_redzone"]]
    redzone_goals = sum(1 for p in redzone_opportunities if p["scored"])

    redzone_stats = None
    if len(redzone_opportunities) > 0:
        pct = round((redzone_goals / len(redzone_opportunities)) * 100, 1)
        redzone_stats = {
            "percentage": pct,
            "goals": redzone_goals,
            "possessions": len(redzone_opportunities),
        }

    return {
        "possession": possession_stats,
        "redzone": redzone_stats
    }


def calculate_redzone_stats_for_team(
    db, game_id: str, team_id: str, is_home_team: bool
) -> Optional[Dict[str, Any]]:
    """
    Calculate redzone percentage from game events with proper game-long direction tracking.

    Args:
        db: Database connection
        game_id: Game identifier
        team_id: Team identifier
        is_home_team: Whether this is the home team

    Returns:
        Dictionary with redzone statistics or None if no events
    """
    team_type = "home" if is_home_team else "away"

    # Get ONLY this team's events - each team has their own event stream
    events_query = """
    SELECT event_index, event_type, receiver_y, thrower_y
    FROM game_events
    WHERE game_id = :game_id
      AND team = :team_type
    ORDER BY event_index
    """
    events = db.execute_query(
        events_query, {"game_id": game_id, "team_type": team_type}
    )

    if not events:
        return None

    # Track red zone opportunities by POSSESSION, not by point
    possessions = []  # List of possessions with red zone tracking
    current_possession = None
    in_possession = False
    point_num = 0

    for event in events:
        event_type = event["event_type"]
        receiver_y = event.get("receiver_y")

        # Point boundaries
        if is_point_start(event_type):  # Types 1 (D point) or 2 (O point)
            point_num += 1

            # O-line starts with possession
            if event_type == 2:  # START_O_POINT
                # Start new possession
                current_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True
            else:
                in_possession = False

        # New possession when we gain the disc
        elif event_type == 11:  # Block - we get possession
            if not in_possession:
                # Save previous possession if exists
                if current_possession:
                    possessions.append(current_possession)
                # Start new possession
                current_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True

        elif event_type == 13:  # Throwaway by opposing team - we get possession
            if not in_possession:
                # Save previous possession if exists
                if current_possession:
                    possessions.append(current_possession)
                # Start new possession
                current_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True

        elif event_type == 18:  # Pass
            if not in_possession:
                # First pass after not having possession starts new possession
                if current_possession:
                    possessions.append(current_possession)
                current_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True

            # Check for red zone possession
            if in_possession and current_possession and receiver_y:
                # Red zone is 80-100 yards (including goal line at 100)
                if 80 <= receiver_y <= 100:
                    current_possession["reached_redzone"] = True

        # Lose possession on turnover
        elif event_type in [20, 22, 24]:  # Drop, Throwaway, Stall - we lose possession
            if in_possession and current_possession:
                # Save current possession
                possessions.append(current_possession)
                current_possession = None
                in_possession = False

        # Score or opponent scores
        elif event_type == 19:  # Our goal
            if current_possession:
                current_possession["scored"] = True
                # Check if goal was thrown from red zone (even if caught in endzone)
                thrower_y = event.get("thrower_y")
                if thrower_y and 80 <= thrower_y <= 100:
                    current_possession["reached_redzone"] = True
                possessions.append(current_possession)
                current_possession = None
                in_possession = False

        elif event_type == 15:  # Opponent scores
            if current_possession:
                possessions.append(current_possession)
                current_possession = None
                in_possession = False

    # Add final possession if exists
    if current_possession:
        possessions.append(current_possession)

    # Count red zone opportunities and goals
    redzone_possessions = [p for p in possessions if p["reached_redzone"]]
    redzone_goals = sum(1 for p in redzone_possessions if p["scored"])

    if len(redzone_possessions) > 0:
        pct = round((redzone_goals / len(redzone_possessions)) * 100, 1)
        return {
            "percentage": pct,
            "goals": redzone_goals,
            "possessions": len(redzone_possessions),
        }
    return None


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
    if not stats:
        return stats

    # Basic percentages with fractions
    if stats.get("total_attempts", 0) > 0:
        pct, display = calculate_percentage(
            stats["total_completions"], stats["total_attempts"]
        )
        stats["completion_percentage"] = pct
        stats["completion_percentage_display"] = display
    else:
        stats["completion_percentage"] = 0
        stats["completion_percentage_display"] = "0% (0/0)"

    if stats.get("total_hucks_attempted", 0) > 0:
        pct, display = calculate_percentage(
            stats["total_hucks_completed"], stats["total_hucks_attempted"]
        )
        stats["huck_percentage"] = pct
        stats["huck_percentage_display"] = display
    else:
        stats["huck_percentage"] = 0
        stats["huck_percentage_display"] = "0% (0/0)"

    # Check if we have valid possession data from game events
    has_valid_possession_data = (
        "o_line_points" in stats
        and stats.get("o_line_points", 0) > 0
        and stats.get("d_line_points", 0) > 0
    )

    if has_valid_possession_data:
        # UFA-exact possession-based statistics
        # Hold % = O-line scores / O-line points
        if stats["o_line_points"] > 0:
            pct, display = calculate_percentage(
                stats["o_line_scores"], stats["o_line_points"]
            )
            stats["hold_percentage"] = pct
            stats["hold_percentage_display"] = display
        else:
            stats["hold_percentage"] = 0
            stats["hold_percentage_display"] = "0% (0/0)"

        # O-Line Conversion % = O-line scores / O-line possessions
        if stats.get("o_line_possessions", 0) > 0:
            pct, display = calculate_percentage(
                stats["o_line_scores"], stats["o_line_possessions"]
            )
            stats["o_conversion"] = pct
            stats["o_conversion_display"] = display
        else:
            stats["o_conversion"] = 0
            stats["o_conversion_display"] = "0% (0/0)"

        # Break % = D-line scores / D-line points
        if stats["d_line_points"] > 0:
            pct, display = calculate_percentage(
                stats["d_line_scores"], stats["d_line_points"]
            )
            stats["break_percentage"] = pct
            stats["break_percentage_display"] = display
        else:
            stats["break_percentage"] = 0
            stats["break_percentage_display"] = "0% (0/0)"

        # D-Line Conversion % = D-line scores / D-line conversions
        if stats.get("d_line_conversions", 0) > 0:
            pct, display = calculate_percentage(
                stats["d_line_scores"], stats["d_line_conversions"]
            )
            stats["d_conversion"] = pct
            stats["d_conversion_display"] = display
        else:
            stats["d_conversion"] = 0
            stats["d_conversion_display"] = "0% (0/0)"

    else:
        # Fallback to player_game_stats calculation when game_events data not available
        if stats.get("total_o_points", 0) > 0:
            pct, display = calculate_percentage(
                stats["total_o_scores"], stats["total_o_points"]
            )
            stats["hold_percentage"] = pct
            stats["hold_percentage_display"] = display
            stats["o_conversion"] = pct
            stats["o_conversion_display"] = display
        else:
            stats["hold_percentage"] = 0
            stats["hold_percentage_display"] = "0% (0/0)"
            stats["o_conversion"] = 0
            stats["o_conversion_display"] = "0% (0/0)"

        if stats.get("total_d_points", 0) > 0:
            pct, display = calculate_percentage(
                stats["total_d_scores"], stats["total_d_points"]
            )
            stats["break_percentage"] = pct
            stats["break_percentage_display"] = display
            stats["d_conversion"] = pct
            stats["d_conversion_display"] = display
        else:
            stats["break_percentage"] = 0
            stats["break_percentage_display"] = "0% (0/0)"
            stats["d_conversion"] = 0
            stats["d_conversion_display"] = "0% (0/0)"

    return stats


def calculate_redzone_stats(game_id: str) -> dict:
    """
    Calculate red zone conversion statistics for both teams in a game.

    Red zone is defined as within 20 yards of the endzone being attacked.
    - North endzone red zone: 80-100 yards
    - South endzone red zone: 20-40 yards

    Args:
        game_id: The game ID to analyze

    Returns:
        Dictionary with red zone stats for both teams
    """
    from sql_database import SQLDatabase

    db = SQLDatabase()

    # Get game information
    game_query = """
    SELECT home_team_id, away_team_id, home_score, away_score
    FROM games
    WHERE game_id = :game_id
    """
    game_result = db.execute_query(game_query, {"game_id": game_id})
    if not game_result:
        return {"error": "Game not found"}

    game = game_result[0]

    def analyze_team_redzone(team_type):
        """Analyze red zone stats for a team (home or away)"""
        # Get all events for this team's perspective
        events_query = """
        SELECT event_index, event_type, receiver_y, thrower_y
        FROM game_events
        WHERE game_id = :game_id AND team = :team
        ORDER BY event_index
        """

        events = db.execute_query(events_query, {"game_id": game_id, "team": team_type})

        if not events:
            return {
                "redzone_attempts": 0,
                "redzone_goals": 0,
                "redzone_conversion_pct": 0.0,
            }

        # Track points
        points = []
        current_point = None
        current_possession = team_type  # Will be set properly on point start

        for event in events:
            event_type = event["event_type"]

            # Point start events
            if is_point_start(event_type):
                # Save previous point if exists
                if current_point:
                    points.append(current_point)

                # Start new point
                current_point = {
                    "reached_redzone": False,
                    "scored": False,
                    "attacking_north": None,  # Will be determined by first possession
                }

                # Determine initial possession
                if event_type == 2:  # START_O_POINT - team receives
                    current_possession = team_type
                else:  # START_D_POINT - team pulls, opponent has possession
                    current_possession = "opponent"

            # Track possessions and red zone entry
            elif current_point:
                # Check for turnovers
                if is_turnover(event_type):
                    # Switch possession
                    if event_type == 11:  # BLOCK - blocking team gains possession
                        # For blocks, the team recording it gains possession
                        current_possession = team_type
                    else:  # Other turnovers - opponent gains possession
                        current_possession = (
                            "opponent" if current_possession == team_type else team_type
                        )

                # Check for red zone entry (only when team has possession)
                if current_possession == team_type:
                    y_coord = event.get("receiver_y") or event.get("thrower_y")
                    if y_coord:
                        # Determine attacking direction if not set
                        if current_point["attacking_north"] is None:
                            # First possession location determines direction
                            current_point["attacking_north"] = y_coord < 60

                        # Check if in attacking red zone
                        if current_point["attacking_north"] and 80 <= y_coord <= 100:
                            current_point["reached_redzone"] = True
                        elif (
                            not current_point["attacking_north"] and 20 <= y_coord <= 40
                        ):
                            current_point["reached_redzone"] = True

                # Check for scoring
                if event_type == 19:  # GOAL - team scores
                    current_point["scored"] = True
                    # Save point and start new one will happen on next START event
                elif event_type == 15:  # SCORE_BY_OPPOSING - opponent scores
                    # Point ends without team scoring
                    pass

                # Point end events
                if is_point_end(event_type):
                    if current_point:
                        points.append(current_point)
                        current_point = None

        # Add final point if exists
        if current_point:
            points.append(current_point)

        # Count red zone opportunities and goals
        redzone_points = 0
        redzone_goals = 0

        for point in points:
            if point["reached_redzone"]:
                redzone_points += 1
                if point["scored"]:
                    redzone_goals += 1

        # Calculate percentage
        redzone_pct = (
            (redzone_goals / redzone_points * 100) if redzone_points > 0 else 0.0
        )

        return {
            "redzone_attempts": redzone_points,
            "redzone_goals": redzone_goals,
            "redzone_conversion_pct": round(redzone_pct, 1),
        }

    # Calculate for both teams
    home_stats = analyze_team_redzone("home")
    away_stats = analyze_team_redzone("away")

    return {"game_id": game_id, "homeTeam": home_stats, "awayTeam": away_stats}


def _process_possession_events(
    events: List[Dict[str, Any]], team_type: str, opponent_type: str
) -> Dict[str, Any]:
    """
    Process a list of events to calculate possession stats.
    Extracted core logic from calculate_possessions() for reuse in batch processing.

    Args:
        events: List of game events (already filtered for this team)
        team_type: 'home' or 'away'
        opponent_type: 'away' or 'home'

    Returns:
        Dictionary with possession statistics
    """
    if not events:
        return {
            "o_line_points": 0,
            "o_line_scores": 0,
            "o_line_possessions": 0,
            "d_line_points": 0,
            "d_line_scores": 0,
            "d_line_possessions": 0,
        }

    # Group events by point (between pulls)
    points = []
    current_point = None
    current_possession = None
    point_had_action = False

    for event in events:
        event_type = event["event_type"]

        # START_D_POINT (1) - This team pulls, opponent receives
        if event_type == 1:
            if current_point and point_had_action:
                points.append(current_point)
            current_point = {
                "pulling_team": team_type,
                "receiving_team": opponent_type,
                "scoring_team": None,
                "team_possessions": 0,
                "opponent_possessions": 1,
            }
            current_possession = opponent_type
            point_had_action = False

        # START_O_POINT (2) - This team receives, opponent pulls
        elif event_type == 2:
            if current_point and point_had_action:
                points.append(current_point)
            current_point = {
                "pulling_team": opponent_type,
                "receiving_team": team_type,
                "scoring_team": None,
                "team_possessions": 1,
                "opponent_possessions": 0,
            }
            current_possession = team_type
            point_had_action = False

        # Goals end the current point
        elif event_type == 19 and current_point:  # Team goal
            current_point["scoring_team"] = team_type
            point_had_action = True
        elif event_type == 15 and current_point:  # Opponent goal
            current_point["scoring_team"] = opponent_type
            point_had_action = True

        # Pass events indicate actual game play
        elif event_type == 18 and current_point:
            point_had_action = True

        # Turnovers change possession
        elif event_type in [11, 20, 22, 24] and current_point:
            point_had_action = True
            if event_type == 11:  # Block - this team blocks, gets possession
                new_possession = team_type
            else:  # Drop/Throwaway/Stall - this team loses possession
                new_possession = opponent_type

            if new_possession != current_possession:
                if new_possession == team_type:
                    current_point["team_possessions"] += 1
                else:
                    current_point["opponent_possessions"] += 1
                current_possession = new_possession

        # Opponent turnovers
        elif event_type == 13 and current_point:
            point_had_action = True
            new_possession = team_type
            if new_possession != current_possession:
                if new_possession == team_type:
                    current_point["team_possessions"] += 1
                else:
                    current_point["opponent_possessions"] += 1
                current_possession = new_possession

    # Add final point if exists
    if current_point and point_had_action:
        points.append(current_point)

    # Calculate statistics from points
    o_line_points = 0
    o_line_scores = 0
    o_line_possessions = 0
    d_line_points = 0
    d_line_scores = 0
    d_line_possessions = 0

    for point in points:
        if point["receiving_team"] == team_type:
            o_line_points += 1
            if point["scoring_team"] == team_type:
                o_line_scores += 1
            o_line_possessions += point["team_possessions"]
        elif point["pulling_team"] == team_type:
            d_line_points += 1
            if point["scoring_team"] == team_type:
                d_line_scores += 1
            d_line_possessions += point["team_possessions"]

    return {
        "o_line_points": o_line_points,
        "o_line_scores": o_line_scores,
        "o_line_possessions": o_line_possessions,
        "d_line_points": d_line_points,
        "d_line_scores": d_line_scores,
        "d_line_possessions": d_line_possessions,
    }


def calculate_possessions_batch(
    db, team_ids: List[str], season_filter: str = "", season_param: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate possession statistics for multiple teams in a single batch query.
    Optimized to avoid N+1 query problem.

    Args:
        db: Database connection
        team_ids: List of team IDs to calculate stats for
        season_filter: SQL WHERE clause for season filtering (e.g., "AND g.year = :season")
        season_param: Season year value for the filter

    Returns:
        Dictionary mapping team_id to possession statistics:
        {
            "team_123": {
                "o_line_points": 50,
                "o_line_scores": 40,
                "o_line_possessions": 75,
                "d_line_points": 48,
                "d_line_scores": 12,
                "d_line_possessions": 25
            },
            ...
        }
    """
    if not team_ids:
        return {}

    # Fetch ALL game events for all teams in ONE query
    placeholders = ",".join([f":team_{i}" for i in range(len(team_ids))])
    params = {f"team_{i}": team_id for i, team_id in enumerate(team_ids)}
    if season_param:
        params["season"] = season_param

    events_query = f"""
    SELECT
        ge.game_id,
        ge.team,
        ge.event_index,
        ge.event_type,
        g.home_team_id,
        g.away_team_id
    FROM game_events ge
    JOIN games g ON ge.game_id = g.game_id
    WHERE (g.home_team_id IN ({placeholders}) OR g.away_team_id IN ({placeholders}))
    {season_filter}
    ORDER BY ge.game_id, ge.team, ge.event_index,
        CASE
            WHEN ge.event_type IN (19, 15) THEN 0
            WHEN ge.event_type = 1 THEN 1
            ELSE 2
        END
    """

    all_events = db.execute_query(events_query, params)

    if not all_events:
        # Return empty stats for all teams
        return {
            team_id: {
                "o_line_points": 0,
                "o_line_scores": 0,
                "o_line_possessions": 0,
                "d_line_points": 0,
                "d_line_scores": 0,
                "d_line_possessions": 0,
            }
            for team_id in team_ids
        }

    # Group events by (game_id, team)
    events_by_game_team = defaultdict(list)
    game_team_mapping = {}  # (game_id, team_type) -> team_id

    for event in all_events:
        game_id = event["game_id"]
        team = event["team"]  # 'home' or 'away'
        key = (game_id, team)
        events_by_game_team[key].append(event)

        # Map team type to team_id
        if team == "home":
            game_team_mapping[key] = event["home_team_id"]
        else:
            game_team_mapping[key] = event["away_team_id"]

    # Process each (game, team) group and aggregate by team_id
    team_stats = defaultdict(lambda: {
        "o_line_points": 0,
        "o_line_scores": 0,
        "o_line_possessions": 0,
        "d_line_points": 0,
        "d_line_scores": 0,
        "d_line_possessions": 0,
    })

    for (game_id, team_type), events in events_by_game_team.items():
        team_id = game_team_mapping[(game_id, team_type)]
        opponent_type = "away" if team_type == "home" else "home"

        # Process events for this game/team
        game_stats = _process_possession_events(events, team_type, opponent_type)

        # Aggregate into team totals
        for key, value in game_stats.items():
            team_stats[team_id][key] += value

    # Ensure all requested teams have entries (even if 0)
    for team_id in team_ids:
        if team_id not in team_stats:
            team_stats[team_id] = {
                "o_line_points": 0,
                "o_line_scores": 0,
                "o_line_possessions": 0,
                "d_line_points": 0,
                "d_line_scores": 0,
                "d_line_possessions": 0,
            }

    return dict(team_stats)


def _process_redzone_events(
    events: List[Dict[str, Any]], team_type: str
) -> Dict[str, Any]:
    """
    Process a list of events to calculate redzone stats.
    Extracted core logic from calculate_redzone_stats_for_team() for batch processing.

    Args:
        events: List of game events (already filtered for this team)
        team_type: 'home' or 'away'

    Returns:
        Dictionary with redzone statistics
    """
    if not events:
        return {"possessions": 0, "goals": 0}

    # Track red zone opportunities by POSSESSION
    possessions = []
    current_possession = None
    in_possession = False
    point_num = 0

    for event in events:
        event_type = event["event_type"]
        receiver_y = event.get("receiver_y")

        # Point boundaries
        if is_point_start(event_type):
            point_num += 1
            if event_type == 2:  # START_O_POINT
                current_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True
            else:
                in_possession = False

        # New possession when we gain the disc
        elif event_type == 11:  # Block
            if not in_possession:
                if current_possession:
                    possessions.append(current_possession)
                current_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True

        elif event_type == 13:  # Throwaway by opposing team
            if not in_possession:
                if current_possession:
                    possessions.append(current_possession)
                current_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True

        elif event_type == 18:  # Pass
            if not in_possession:
                if current_possession:
                    possessions.append(current_possession)
                current_possession = {
                    "point": point_num,
                    "reached_redzone": False,
                    "scored": False,
                }
                in_possession = True

            # Check for red zone possession
            if in_possession and current_possession and receiver_y:
                if 80 <= receiver_y <= 100:
                    current_possession["reached_redzone"] = True

        # Lose possession on turnover
        elif event_type in [20, 22, 24]:  # Drop, Throwaway, Stall
            if in_possession and current_possession:
                possessions.append(current_possession)
                current_possession = None
                in_possession = False

        # Score or opponent scores
        elif event_type == 19:  # Our goal
            if current_possession:
                current_possession["scored"] = True
                thrower_y = event.get("thrower_y")
                if thrower_y and 80 <= thrower_y <= 100:
                    current_possession["reached_redzone"] = True
                possessions.append(current_possession)
                current_possession = None
                in_possession = False

        elif event_type == 15:  # Opponent scores
            if current_possession:
                possessions.append(current_possession)
                current_possession = None
                in_possession = False

    # Add final possession if exists
    if current_possession:
        possessions.append(current_possession)

    # Count red zone opportunities and goals
    redzone_possessions = [p for p in possessions if p["reached_redzone"]]
    redzone_goals = sum(1 for p in redzone_possessions if p["scored"])

    return {
        "possessions": len(redzone_possessions),
        "goals": redzone_goals,
    }


def calculate_redzone_stats_batch(
    db, team_ids: List[str], season_filter: str = "", season_param: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Calculate redzone statistics for multiple teams in a single batch query.
    Optimized to avoid N+1 query problem.

    Args:
        db: Database connection
        team_ids: List of team IDs to calculate stats for
        season_filter: SQL WHERE clause for season filtering
        season_param: Season year value for the filter

    Returns:
        Dictionary mapping team_id to redzone statistics:
        {
            "team_123": {
                "possessions": 45,
                "goals": 38
            },
            ...
        }
    """
    if not team_ids:
        return {}

    # Fetch ALL game events for all teams in ONE query
    placeholders = ",".join([f":team_{i}" for i in range(len(team_ids))])
    params = {f"team_{i}": team_id for i, team_id in enumerate(team_ids)}
    if season_param:
        params["season"] = season_param

    events_query = f"""
    SELECT
        ge.game_id,
        ge.team,
        ge.event_index,
        ge.event_type,
        ge.receiver_y,
        ge.thrower_y,
        g.home_team_id,
        g.away_team_id
    FROM game_events ge
    JOIN games g ON ge.game_id = g.game_id
    WHERE (g.home_team_id IN ({placeholders}) OR g.away_team_id IN ({placeholders}))
    {season_filter}
    ORDER BY ge.game_id, ge.team, ge.event_index
    """

    all_events = db.execute_query(events_query, params)

    if not all_events:
        return {team_id: {"possessions": 0, "goals": 0} for team_id in team_ids}

    # Group events by (game_id, team)
    events_by_game_team = defaultdict(list)
    game_team_mapping = {}

    for event in all_events:
        game_id = event["game_id"]
        team = event["team"]
        key = (game_id, team)
        events_by_game_team[key].append(event)

        if team == "home":
            game_team_mapping[key] = event["home_team_id"]
        else:
            game_team_mapping[key] = event["away_team_id"]

    # Process each (game, team) group and aggregate by team_id
    team_stats = defaultdict(lambda: {"possessions": 0, "goals": 0})

    for (game_id, team_type), events in events_by_game_team.items():
        team_id = game_team_mapping[(game_id, team_type)]

        # Process events for this game/team
        game_stats = _process_redzone_events(events, team_type)

        # Aggregate into team totals
        team_stats[team_id]["possessions"] += game_stats["possessions"]
        team_stats[team_id]["goals"] += game_stats["goals"]

    # Ensure all requested teams have entries
    for team_id in team_ids:
        if team_id not in team_stats:
            team_stats[team_id] = {"possessions": 0, "goals": 0}

    return dict(team_stats)
