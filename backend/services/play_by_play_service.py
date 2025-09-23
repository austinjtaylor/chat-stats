"""
Play-by-play service for processing game events.
"""

from typing import List, Dict, Any


def calculate_play_by_play(stats_system, game_id: str) -> List[Dict[str, Any]]:
    """
    Calculate play-by-play data from game events.
    Returns a list of points with their events and metadata.
    """
    # Get game information including year for player lookups
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

    # Get events from home team perspective only to avoid duplicates
    # Home team records both their events and opponent events
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
      AND e.team = 'home'  -- Process from home team perspective only
    ORDER BY e.event_index
    """

    events = stats_system.db.execute_query(events_query, {"game_id": game_id, "year": game_year})
    if not events:
        return []

    # Process events into points
    points = []
    current_point = None
    current_point_events = []
    current_score = {"home": 0, "away": 0}
    quarter = 1
    point_start_time = None
    point_end_time = None
    point_number = 0

    for event in events:
        event_type = event["event_type"]

        # Quarter end events
        if event_type in [28, 29, 30, 31]:  # Quarter/half/regulation ends
            if event_type == 28:
                quarter = 2
            elif event_type == 29:
                quarter = 3
            elif event_type == 30:
                quarter = 4
            continue

        # Start of a new point (pull)
        if event_type in [1, 2]:  # START_D_POINT or START_O_POINT
            # Save previous point if exists
            if current_point:
                current_point["events"] = current_point_events
                # Calculate duration properly
                if point_end_time and point_start_time:
                    current_point["duration_seconds"] = max(0, point_end_time - point_start_time)
                else:
                    current_point["duration_seconds"] = 0
                points.append(current_point)

            point_number += 1
            point_start_time = event["event_time"] if event["event_time"] else 0
            point_end_time = None

            # From home team perspective:
            # Type 1 = Home team pulls (D-point for home)
            # Type 2 = Home team receives (O-point for home)
            if event_type == 1:  # Home pulls (D-point for home)
                pulling_team = "home"
                receiving_team = "away"
                line_type = "D-Line"
                point_team = "home"
            else:  # Type 2: Home receives (O-point for home)
                pulling_team = "away"
                receiving_team = "home"
                line_type = "O-Line"
                point_team = "home"

            # Get line players
            line_players = []
            if event["line_players"]:
                import json
                try:
                    player_ids = json.loads(event["line_players"])
                    # Get player names with year filter to avoid duplicates
                    if player_ids and len(player_ids) > 0:
                        # Create placeholders for SQL query
                        placeholders = ','.join([':p' + str(i) for i in range(len(player_ids))])
                        players_query = f"""
                        SELECT DISTINCT last_name
                        FROM players
                        WHERE player_id IN ({placeholders})
                          AND year = :year
                        """
                        # Create parameters dict including year
                        params = {f'p{i}': pid for i, pid in enumerate(player_ids)}
                        params['year'] = game_year
                        player_results = stats_system.db.execute_query(players_query, params)
                        line_players = [p["last_name"] for p in player_results if p and p.get("last_name")]
                except Exception as e:
                    # Log error but continue
                    print(f"Error parsing line players: {e}")
                    pass

            current_point = {
                "point_number": point_number,
                "quarter": quarter,
                "score": f"{current_score['away']}-{current_score['home']}",
                "home_score": current_score["home"],
                "away_score": current_score["away"],
                "team": point_team,  # Team perspective for this point
                "line_type": line_type,
                "start_time": point_start_time,
                "duration_seconds": 0,
                "players": line_players,
                "pulling_team": pulling_team,
                "receiving_team": receiving_team,
                "scoring_team": None
            }
            current_point_events = []

            # Add pull event
            if event["puller_last"]:
                current_point_events.append({
                    "type": "pull",
                    "description": f"Pull by {event['puller_last']}",
                    "yard_line": None
                })

        # Goal events (from home team perspective)
        elif event_type in [19, 15]:  # GOAL or SCORE_BY_OPPOSING
            point_end_time = event["event_time"] if event["event_time"] else point_start_time

            # Type 19 = Home team scores
            # Type 15 = Away team scores (opponent scores from home perspective)
            if event_type == 19:  # Home team scores
                current_score["home"] += 1
                if current_point:
                    current_point["scoring_team"] = "home"
            else:  # Type 15: Away team scores
                current_score["away"] += 1
                if current_point:
                    current_point["scoring_team"] = "away"

            # Update point score after goal
            if current_point:
                current_point["score"] = f"{current_score['away']}-{current_score['home']}"
                current_point["home_score"] = current_score["home"]
                current_point["away_score"] = current_score["away"]

            # Add goal event
            if event["receiver_last"] and event["thrower_last"]:
                yard_line = int(event["receiver_y"]) if event["receiver_y"] is not None else None
                current_point_events.append({
                    "type": "goal",
                    "description": f"Score from {event['thrower_last']} to {event['receiver_last']}",
                    "yard_line": yard_line
                })

        # Pass events
        elif event_type == 18:  # PASS
            if event["receiver_last"] and event["thrower_last"]:
                # Determine pass type based on distance
                if event["thrower_y"] is not None and event["receiver_y"] is not None:
                    distance = abs(event["receiver_y"] - event["thrower_y"])
                    yard_line = int(event["thrower_y"])

                    if distance > 40:
                        pass_type = "Huck"
                    elif distance > 20:
                        pass_type = "Pass"
                    elif distance > 10:
                        pass_type = "Dish"
                    else:
                        pass_type = "Dump"
                else:
                    pass_type = "Pass"
                    yard_line = None

                current_point_events.append({
                    "type": "pass",
                    "description": f"{pass_type} from {event['thrower_last']} to {event['receiver_last']}",
                    "yard_line": yard_line
                })

        # Turnover events
        elif event_type == 11:  # BLOCK
            if event["defender_last"]:
                yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
                current_point_events.append({
                    "type": "block",
                    "description": f"Block by {event['defender_last']}",
                    "yard_line": yard_line
                })
        elif event_type == 20:  # DROP
            if event["receiver_last"]:
                yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
                current_point_events.append({
                    "type": "drop",
                    "description": f"Drop by {event['receiver_last']}",
                    "yard_line": yard_line
                })
        elif event_type == 22:  # THROWAWAY
            if event["thrower_last"]:
                yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
                current_point_events.append({
                    "type": "throwaway",
                    "description": f"Throwaway by {event['thrower_last']}",
                    "yard_line": yard_line
                })
        elif event_type == 24:  # STALL
            yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
            current_point_events.append({
                "type": "stall",
                "description": "Stall",
                "yard_line": yard_line
            })

    # Save last point if exists
    if current_point:
        current_point["events"] = current_point_events
        # Calculate duration properly
        if point_end_time and point_start_time:
            current_point["duration_seconds"] = max(0, point_end_time - point_start_time)
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

        # Format time remaining in quarter (approximate)
        if point["start_time"] is not None:
            quarter_time = 12 * 60  # 12 minutes per quarter
            time_in_quarter = point["start_time"] % quarter_time
            minutes_remaining = (quarter_time - time_in_quarter) // 60
            seconds_remaining = (quarter_time - time_in_quarter) % 60
            point["time"] = f"{minutes_remaining:02d}:{seconds_remaining:02d}"
        else:
            point["time"] = "12:00"

    return points