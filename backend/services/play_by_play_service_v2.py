"""
Play-by-play service for processing game events - Version 2.
This version processes each team's events separately to maintain complete detail.
"""

import math
from typing import List, Dict, Any


def process_team_events(events: List[Dict], team: str, game_year: int, stats_system) -> List[Dict[str, Any]]:
    """
    Process events for a single team to build their play-by-play perspective.

    Args:
        events: List of events for this team
        team: 'home' or 'away'
        game_year: Year for player lookups
        stats_system: Database system for queries

    Returns:
        List of points with events from this team's perspective
    """
    points = []
    current_point = None
    current_point_events = []
    current_score = {"home": 0, "away": 0}
    quarter = 1
    point_number = 0
    quarter_offset = 0

    for event in events:
        event_type = event["event_type"]

        # Quarter end events
        if event_type in [28, 29, 30, 31]:  # Quarter/half/regulation ends
            if current_point:
                # Calculate the end time based on which quarter is ending
                quarter_end_time = None
                if event_type == 28:  # End of Q1
                    quarter_end_time = 720
                elif event_type == 29:  # Halftime
                    quarter_end_time = 1440
                elif event_type == 30:  # End of Q3
                    quarter_end_time = 2160
                elif event_type == 31:  # End of regulation
                    quarter_end_time = 2880

                if quarter_end_time is not None:
                    current_point["end_time"] = quarter_end_time
                    if current_point["start_time"] is not None:
                        current_point["duration_seconds"] = max(0, quarter_end_time - current_point["start_time"])

                current_point["events"] = current_point_events
                points.append(current_point)
                current_point = None
                current_point_events = []

            # Update quarter
            if event_type == 28:
                quarter = 2
                quarter_offset = 720
            elif event_type == 29:
                quarter = 3
                quarter_offset = 1440
            elif event_type == 30:
                quarter = 4
                quarter_offset = 2160
            continue

        # Start of a new point (pull)
        elif event_type in [1, 2]:  # START_D_POINT or START_O_POINT
            # Save previous point if exists
            if current_point:
                if event["event_time"] is not None:
                    absolute_time = quarter_offset + event["event_time"]
                    current_point["end_time"] = absolute_time
                    if current_point["start_time"] is not None:
                        current_point["duration_seconds"] = max(0, absolute_time - current_point["start_time"])
                current_point["events"] = current_point_events
                points.append(current_point)

            point_number += 1
            point_start_time = (quarter_offset + event["event_time"]) if event["event_time"] is not None else quarter_offset

            # Determine line type and who pulls/receives
            if team == "home":
                if event_type == 1:  # Home pulls (D-point)
                    line_type = "D-Line"
                    pulling_team = "home"
                    receiving_team = "away"
                else:  # Home receives (O-point)
                    line_type = "O-Line"
                    pulling_team = "away"
                    receiving_team = "home"
            else:  # team == "away"
                if event_type == 1:  # Away pulls (D-point)
                    line_type = "D-Line"
                    pulling_team = "away"
                    receiving_team = "home"
                else:  # Away receives (O-point)
                    line_type = "O-Line"
                    pulling_team = "home"
                    receiving_team = "away"

            # Get line players
            line_players = []
            if event["line_players"]:
                import json
                try:
                    player_ids = json.loads(event["line_players"])
                    if player_ids and len(player_ids) > 0:
                        # Build query for multiple player IDs
                        placeholders = ', '.join([f':p{i}' for i in range(len(player_ids))])
                        players_query = f"""
                        SELECT DISTINCT last_name
                        FROM players
                        WHERE player_id IN ({placeholders})
                          AND year = :year
                        """
                        params = {f'p{i}': pid for i, pid in enumerate(player_ids)}
                        params['year'] = game_year
                        player_results = stats_system.db.execute_query(players_query, params)
                        line_players = [p["last_name"] for p in player_results if p and p.get("last_name")]
                except Exception as e:
                    print(f"Error parsing line players: {e}")

            # Create new point
            current_point = {
                "point_number": point_number,
                "quarter": quarter,
                "score": f"{current_score['away']}-{current_score['home']}",
                "home_score": current_score["home"],
                "away_score": current_score["away"],
                "team": team,
                "line_type": line_type,
                "start_time": point_start_time,
                "end_time": None,
                "duration_seconds": 0,
                "players": line_players,
                "pulling_team": pulling_team,
                "receiving_team": receiving_team,
                "scoring_team": None
            }
            current_point_events = []

            # Add initial pull event if this team pulls
            if pulling_team == team:
                puller_name = event["puller_last"] if event["puller_last"] else None
                if puller_name:
                    pull_event = {
                        "type": "pull",
                        "description": f"Pull by {puller_name}",
                        "yard_line": None
                    }
                else:
                    pull_event = {
                        "type": "pull",
                        "description": "Pull",
                        "yard_line": None
                    }
                current_point_events.append(pull_event)

        # Pull inbounds/out of bounds (detailed pull data)
        elif event_type in [7, 8]:  # PULL_INBOUNDS or PULL_OUT_OF_BOUNDS
            if current_point and current_point["pulling_team"] == team and event["puller_last"]:
                # Calculate pull distance
                pull_distance = None
                if event["pull_y"] is not None:
                    pull_distance = int(abs(event["pull_y"] - 20))

                pull_description = f"Pull by {event['puller_last']}"
                if pull_distance:
                    pull_description = f"{pull_distance}y {pull_description}"

                detailed_pull_event = {
                    "type": "pull",
                    "description": pull_description,
                    "yard_line": None
                }

                # Replace generic pull with detailed one
                if current_point_events and current_point_events[-1]["type"] == "pull":
                    current_point_events[-1] = detailed_pull_event
                else:
                    current_point_events.append(detailed_pull_event)

        # Pass events
        elif event_type == 18:  # PASS
            if event["receiver_last"] and event["thrower_last"]:
                # Calculate pass details
                if (event["thrower_y"] is not None and event["receiver_y"] is not None and
                    event["thrower_x"] is not None and event["receiver_x"] is not None):
                    vertical_yards = event["receiver_y"] - event["thrower_y"]
                    horizontal_yards = event["receiver_x"] - event["thrower_x"]
                    actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)
                    angle_radians = math.atan2(vertical_yards, -horizontal_yards)
                    angle_degrees = math.degrees(angle_radians)

                    if vertical_yards <= 0:
                        pass_type = "Dump"
                    elif vertical_yards >= 40:
                        pass_type = "Huck"
                    else:
                        pass_type = "Pass"

                    distance_str = f"{int(actual_distance)}y"
                    pass_event = {
                        "type": "pass",
                        "description": f"{distance_str} {pass_type} from {event['thrower_last']} to {event['receiver_last']}",
                        "yard_line": None,
                        "direction": angle_degrees
                    }
                else:
                    pass_event = {
                        "type": "pass",
                        "description": f"Pass from {event['thrower_last']} to {event['receiver_last']}",
                        "yard_line": None
                    }
                current_point_events.append(pass_event)

        # Goal events
        elif event_type == 19:  # GOAL (this team scored)
            if team == "home":
                current_score["home"] += 1
            else:
                current_score["away"] += 1

            if current_point:
                current_point["scoring_team"] = team
                current_point["score"] = f"{current_score['away']}-{current_score['home']}"
                current_point["home_score"] = current_score["home"]
                current_point["away_score"] = current_score["away"]

            # Add goal event
            if event["receiver_last"] and event["thrower_last"]:
                if (event["thrower_y"] is not None and event["receiver_y"] is not None and
                    event["thrower_x"] is not None and event["receiver_x"] is not None):
                    vertical_yards = event["receiver_y"] - event["thrower_y"]
                    horizontal_yards = event["receiver_x"] - event["thrower_x"]
                    actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)
                    angle_radians = math.atan2(vertical_yards, -horizontal_yards)
                    angle_degrees = math.degrees(angle_radians)

                    # Determine if it's a huck (40+ yards forward)
                    pass_type = "Huck " if vertical_yards >= 40 else ""
                    distance_str = f"{int(actual_distance)}y"

                    goal_event = {
                        "type": "goal",
                        "description": f"{distance_str} {pass_type}Score from {event['thrower_last']} to {event['receiver_last']}",
                        "yard_line": None,
                        "direction": angle_degrees
                    }
                else:
                    goal_event = {
                        "type": "goal",
                        "description": f"Score from {event['thrower_last']} to {event['receiver_last']}",
                        "yard_line": None
                    }
                current_point_events.append(goal_event)

        elif event_type == 15:  # SCORE_BY_OPPOSING (opponent scored)
            if team == "home":
                current_score["away"] += 1
                scoring_team = "away"
            else:
                current_score["home"] += 1
                scoring_team = "home"

            if current_point:
                current_point["scoring_team"] = scoring_team
                current_point["score"] = f"{current_score['away']}-{current_score['home']}"
                current_point["home_score"] = current_score["home"]
                current_point["away_score"] = current_score["away"]

            current_point_events.append({
                "type": "opponent_score",
                "description": "They scored",
                "yard_line": None
            })

        # Block events
        elif event_type == 11:  # BLOCK (this team got a block)
            if event["defender_last"]:
                yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
                block_event = {
                    "type": "block",
                    "description": f"Block by {event['defender_last']}",
                    "yard_line": yard_line
                }
                current_point_events.append(block_event)

        elif event_type == 12:  # BLOCK_BY_OPPOSING (opponent got a block)
            defender_name = event["defender_last"] if event["defender_last"] else None
            yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
            if defender_name:
                current_point_events.append({
                    "type": "opponent_turnover",
                    "description": f"Opponent turnover (Blocked by {defender_name})",
                    "yard_line": yard_line
                })
            else:
                current_point_events.append({
                    "type": "opponent_turnover",
                    "description": "Opponent turnover (Block)",
                    "yard_line": yard_line
                })

        # Other turnovers
        elif event_type == 20:  # DROP
            if event["receiver_last"]:
                yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
                drop_event = {
                    "type": "drop",
                    "description": f"Drop by {event['receiver_last']}",
                    "yard_line": yard_line
                }
                current_point_events.append(drop_event)

        elif event_type == 22:  # THROWAWAY
            if event["thrower_last"]:
                # Calculate throwaway details if available
                if (event["thrower_y"] is not None and event["turnover_y"] is not None and
                    event["thrower_x"] is not None and event["turnover_x"] is not None):
                    vertical_yards = event["turnover_y"] - event["thrower_y"]
                    horizontal_yards = event["turnover_x"] - event["thrower_x"]
                    actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)
                    angle_radians = math.atan2(vertical_yards, -horizontal_yards)
                    angle_degrees = math.degrees(angle_radians)

                    throwaway_type = "Huck throwaway" if vertical_yards >= 40 else "Throwaway"
                    distance_str = f"{int(actual_distance)}y"

                    throwaway_event = {
                        "type": "throwaway",
                        "description": f"{distance_str} {throwaway_type} by {event['thrower_last']}",
                        "yard_line": None,
                        "direction": angle_degrees
                    }
                else:
                    throwaway_event = {
                        "type": "throwaway",
                        "description": f"Throwaway by {event['thrower_last']}",
                        "yard_line": None
                    }
                current_point_events.append(throwaway_event)

        elif event_type == 24:  # STALL
            yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
            stall_event = {
                "type": "stall",
                "description": "Stall",
                "yard_line": yard_line
            }
            current_point_events.append(stall_event)

        # Opponent turnovers
        elif event_type in [13, 14]:  # THROWAWAY_BY_OPPOSING or STALL_ON_OPPOSING
            turnover_type = "Throwaway" if event_type == 13 else "Stall"
            yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
            current_point_events.append({
                "type": "opponent_turnover",
                "description": f"Opponent turnover ({turnover_type})",
                "yard_line": yard_line
            })

    # Save last point if exists
    if current_point:
        current_point["events"] = current_point_events
        if not current_point.get("end_time"):
            if current_point["start_time"] is not None:
                current_point["end_time"] = current_point["start_time"] + 90
                current_point["duration_seconds"] = 90
            else:
                current_point["duration_seconds"] = 0
        points.append(current_point)

    # Add formatted time and duration to each point
    for point in points:
        minutes = point["duration_seconds"] // 60 if point["duration_seconds"] else 0
        seconds = point["duration_seconds"] % 60 if point["duration_seconds"] else 0

        if minutes > 0:
            point["duration"] = f"{minutes}m{seconds:02d}s"
        else:
            point["duration"] = f"{seconds}s"

        # Format time remaining
        if point["end_time"] is not None:
            quarter = point["quarter"]
            time_in_quarter = point["end_time"] - ((quarter - 1) * 720)
            time_remaining = 720 - time_in_quarter

            if time_remaining >= 0:
                mins = int(time_remaining // 60)
                secs = int(time_remaining % 60)
                point["time"] = f"{mins:02d}:{secs:02d}"
            else:
                point["time"] = "00:00"
        else:
            point["time"] = "00:00"

    return points


def calculate_play_by_play(stats_system, game_id: str) -> List[Dict[str, Any]]:
    """
    Calculate play-by-play data from game events.
    Returns a list of points with their events and metadata.
    """
    # Get game information
    game_query = """
    SELECT
        g.home_team_id, g.away_team_id, g.year,
        ht.city as home_city, ht.name as home_name,
        at.city as away_city, at.name as away_name
    FROM games g
    JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
    JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
    WHERE g.game_id = :game_id
    """

    game_result = stats_system.db.execute_query(game_query, {"game_id": game_id})
    if not game_result:
        return []

    game_year = game_result[0]["year"]

    # Get events from both teams
    events_query = """
    SELECT
        e.event_index, e.team, e.event_type, e.event_time,
        e.thrower_id, e.receiver_id, e.defender_id, e.puller_id,
        e.thrower_x, e.thrower_y, e.receiver_x, e.receiver_y,
        e.turnover_x, e.turnover_y, e.pull_x, e.pull_y,
        e.pull_ms, e.line_players,
        t.full_name as thrower_name, t.last_name as thrower_last,
        r.full_name as receiver_name, r.last_name as receiver_last,
        d.full_name as defender_name, d.last_name as defender_last,
        p.full_name as puller_name, p.last_name as puller_last
    FROM game_events e
    LEFT JOIN players t ON e.thrower_id = t.player_id AND t.year = :year
    LEFT JOIN players r ON e.receiver_id = r.player_id AND r.year = :year
    LEFT JOIN players d ON e.defender_id = d.player_id AND d.year = :year
    LEFT JOIN players p ON e.puller_id = p.player_id AND p.year = :year
    WHERE e.game_id = :game_id
    ORDER BY e.team, e.event_index
    """

    events = stats_system.db.execute_query(events_query, {"game_id": game_id, "year": game_year})
    if not events:
        return []

    # Separate events by team
    home_events = [e for e in events if e["team"] == "home"]
    away_events = [e for e in events if e["team"] == "away"]

    # Process each team's events separately
    home_points = process_team_events(home_events, "home", game_year, stats_system)
    away_points = process_team_events(away_events, "away", game_year, stats_system)

    # Combine and return both perspectives
    return home_points + away_points