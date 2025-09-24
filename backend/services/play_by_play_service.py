"""
Play-by-play service for processing game events.
"""

import math
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
    home_team_id = game_result[0]["home_team_id"]
    away_team_id = game_result[0]["away_team_id"]

    # Get events from BOTH teams' perspectives for complete data
    # Each team records their own events with more detail
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
        p.full_name as puller_name, p.last_name as puller_last,
        -- Look ahead to get next pull time for estimating goal time if needed
        LEAD(CASE WHEN e.event_type IN (1, 2) THEN e.event_time ELSE NULL END)
            OVER (PARTITION BY e.team ORDER BY e.event_index) as next_pull_time
    FROM game_events e
    LEFT JOIN players t ON e.thrower_id = t.player_id AND t.year = :year
    LEFT JOIN players r ON e.receiver_id = r.player_id AND r.year = :year
    LEFT JOIN players d ON e.defender_id = d.player_id AND d.year = :year
    LEFT JOIN players p ON e.puller_id = p.player_id AND p.year = :year
    WHERE e.game_id = :game_id
    ORDER BY e.event_index, e.team
    """

    events = stats_system.db.execute_query(events_query, {"game_id": game_id, "year": game_year})
    if not events:
        return []

    # Separate events by team for processing
    home_events = [e for e in events if e["team"] == "home"]
    away_events = [e for e in events if e["team"] == "away"]

    # Create index maps for quick lookup
    home_events_by_index = {}
    away_events_by_index = {}
    for event in home_events:
        idx = event["event_index"]
        if idx not in home_events_by_index:
            home_events_by_index[idx] = []
        home_events_by_index[idx].append(event)
    for event in away_events:
        idx = event["event_index"]
        if idx not in away_events_by_index:
            away_events_by_index[idx] = []
        away_events_by_index[idx].append(event)

    # Get unique event indices and sort them
    all_indices = sorted(set([e["event_index"] for e in events]))

    # Process events into points for both team perspectives
    points_home = []  # Points from home team perspective
    points_away = []  # Points from away team perspective
    current_point_home = None
    current_point_away = None
    current_point_events_home = []
    current_point_events_away = []
    current_score = {"home": 0, "away": 0}
    quarter = 1
    point_start_time = None
    point_end_time = None
    point_number = 0
    quarter_offset = 0  # Track cumulative time offset for quarters

    for event_index in all_indices:
        # Get events at this index from both teams
        home_event = home_events_by_index.get(event_index, [None])[0]
        away_event = away_events_by_index.get(event_index, [None])[0]

        # Use the event with actual data, preferring home team's perspective for common events
        event = home_event if home_event else away_event
        if not event:
            continue
        event_type = event["event_type"]

        # Quarter end events
        if event_type in [28, 29, 30, 31]:  # Quarter/half/regulation ends
            # Save current points before quarter ends
            if current_point_home:
                # Calculate the end time based on which quarter is ending
                quarter_end_time = None
                if event_type == 28:  # End of Q1
                    quarter_end_time = 720  # 12 minutes * 60 seconds
                elif event_type == 29:  # Halftime (End of Q2)
                    quarter_end_time = 1440  # 24 minutes * 60 seconds
                elif event_type == 30:  # End of Q3
                    quarter_end_time = 2160  # 36 minutes * 60 seconds
                elif event_type == 31:  # End of regulation (End of Q4)
                    quarter_end_time = 2880  # 48 minutes * 60 seconds

                if quarter_end_time is not None:
                    current_point_home["end_time"] = quarter_end_time
                    if current_point_home["start_time"] is not None:
                        current_point_home["duration_seconds"] = max(0, quarter_end_time - current_point_home["start_time"])

                current_point_home["events"] = current_point_events_home
                points_home.append(current_point_home)

                # Also save away team perspective
                if current_point_away:
                    current_point_away["end_time"] = quarter_end_time
                    if current_point_away["start_time"] is not None:
                        current_point_away["duration_seconds"] = max(0, quarter_end_time - current_point_away["start_time"])
                    current_point_away["events"] = current_point_events_away
                    points_away.append(current_point_away)

                current_point_home = None
                current_point_away = None
                current_point_events_home = []
                current_point_events_away = []

            # Update quarter and time offset for next points
            if event_type == 28:
                quarter = 2
                quarter_offset = 720  # Q2 starts after 12 minutes
            elif event_type == 29:
                quarter = 3
                quarter_offset = 1440  # Q3 starts after 24 minutes
            elif event_type == 30:
                quarter = 4
                quarter_offset = 2160  # Q4 starts after 36 minutes
            continue

        # Start of a new point (pull)
        if event_type in [1, 2]:  # START_D_POINT or START_O_POINT
            # Save previous points if exist
            if current_point_home:
                # Since the next point starts immediately, use current pull time as end time of previous point
                if event["event_time"] is not None:
                    # Adjust event time to absolute game time
                    absolute_time = quarter_offset + event["event_time"]
                    current_point_home["end_time"] = absolute_time
                    if current_point_home["start_time"] is not None:
                        current_point_home["duration_seconds"] = max(0, absolute_time - current_point_home["start_time"])

                current_point_home["events"] = current_point_events_home
                points_home.append(current_point_home)

                # Also save away team perspective
                if current_point_away:
                    current_point_away["end_time"] = absolute_time
                    if current_point_away["start_time"] is not None:
                        current_point_away["duration_seconds"] = max(0, absolute_time - current_point_away["start_time"])
                    current_point_away["events"] = current_point_events_away
                    points_away.append(current_point_away)

            point_number += 1
            # Adjust start time to absolute game time
            point_start_time = (quarter_offset + event["event_time"]) if event["event_time"] is not None else quarter_offset
            point_end_time = None

            # From home team perspective:
            # Type 1 = Home team pulls (D-point for home, O-point for away)
            # Type 2 = Home team receives (O-point for home, D-point for away)
            if event_type == 1:  # Home pulls
                pulling_team = "home"
                receiving_team = "away"
                home_line_type = "D-Line"
                away_line_type = "O-Line"
            else:  # Type 2: Home receives
                pulling_team = "away"
                receiving_team = "home"
                home_line_type = "O-Line"
                away_line_type = "D-Line"

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

            # Create point from home team perspective
            current_point_home = {
                "point_number": point_number,
                "quarter": quarter,
                "score": f"{current_score['away']}-{current_score['home']}",
                "home_score": current_score["home"],
                "away_score": current_score["away"],
                "team": "home",  # Home team perspective
                "line_type": home_line_type,
                "start_time": point_start_time,
                "end_time": None,  # Will be set when goal is scored
                "duration_seconds": 0,
                "players": line_players if home_line_type == "O-Line" or home_line_type == "D-Line" else [],
                "pulling_team": pulling_team,
                "receiving_team": receiving_team,
                "scoring_team": None
            }

            # Create point from away team perspective
            current_point_away = {
                "point_number": point_number,
                "quarter": quarter,
                "score": f"{current_score['away']}-{current_score['home']}",
                "home_score": current_score["home"],
                "away_score": current_score["away"],
                "team": "away",  # Away team perspective
                "line_type": away_line_type,
                "start_time": point_start_time,
                "end_time": None,  # Will be set when goal is scored
                "duration_seconds": 0,
                "players": [],  # Away team players would need to be fetched separately
                "pulling_team": pulling_team,
                "receiving_team": receiving_team,
                "scoring_team": None
            }
            current_point_events_home = []
            current_point_events_away = []

            # Add pull event to both perspectives using data from the pulling team
            # Check which team's event has the puller information
            if pulling_team == "home":
                # Home team pulls - use home event data
                puller_name = home_event["puller_last"] if home_event else None
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
                current_point_events_home.append(pull_event)
            else:
                # Away team pulls - use away event data
                puller_name = away_event["puller_last"] if away_event else None
                if puller_name:
                    away_pull_event = {
                        "type": "pull",
                        "description": f"Pull by {puller_name}",
                        "yard_line": None
                    }
                else:
                    away_pull_event = {
                        "type": "pull",
                        "description": "Pull",
                        "yard_line": None
                    }
                current_point_events_away.append(away_pull_event)

        # Pull inbounds/out of bounds events (actual pull data)
        elif event_type in [7, 8]:  # PULL_INBOUNDS or PULL_OUT_OF_BOUNDS
            if current_point_home:
                # Determine which team pulled and get their event data
                if current_point_home["pulling_team"] == "home":
                    # Home team pulled - use home event for details
                    pull_event = home_event if home_event and home_event["event_type"] in [7, 8] else event
                    if pull_event and pull_event["puller_last"]:
                        # Calculate pull distance if coordinates are available
                        pull_distance = None
                        if pull_event["pull_y"] is not None:
                            # Pull Y coordinate is where it landed
                            # Distance from endzone (20y line) is pull_y - 20
                            pull_distance = int(abs(pull_event["pull_y"] - 20))

                        # Replace the generic pull event with detailed one
                        pull_description = f"Pull by {pull_event['puller_last']}"
                        if pull_distance:
                            pull_description = f"{pull_distance}y {pull_description}"

                        detailed_pull_event = {
                            "type": "pull",
                            "description": pull_description,
                            "yard_line": None  # Don't show yard line for pulls, distance is in description
                        }

                        # Replace the last event (generic pull) with detailed one
                        if current_point_events_home and current_point_events_home[-1]["type"] == "pull":
                            current_point_events_home[-1] = detailed_pull_event
                        else:
                            current_point_events_home.append(detailed_pull_event)
                else:
                    # Away team pulled - use away event for details
                    pull_event = away_event if away_event and away_event["event_type"] in [7, 8] else event
                    if pull_event and pull_event["puller_last"]:
                        # Calculate pull distance if coordinates are available
                        pull_distance = None
                        if pull_event["pull_y"] is not None:
                            pull_distance = int(abs(pull_event["pull_y"] - 20))

                        # Replace the generic pull event with detailed one
                        pull_description = f"Pull by {pull_event['puller_last']}"
                        if pull_distance:
                            pull_description = f"{pull_distance}y {pull_description}"

                        detailed_pull_event = {
                            "type": "pull",
                            "description": pull_description,
                            "yard_line": None
                        }

                        # Replace the last event (generic pull) with detailed one
                        if current_point_events_away and current_point_events_away[-1]["type"] == "pull":
                            current_point_events_away[-1] = detailed_pull_event
                        else:
                            current_point_events_away.append(detailed_pull_event)

        # Opponent block events (block BY opposing team)
        elif event_type == 12:  # BLOCK_BY_OPPOSING
            # Home team's perspective: opponent blocked them
            if home_event and home_event["event_type"] == 12:
                defender_name = home_event["defender_last"] if home_event["defender_last"] else None
                yard_line = int(home_event["turnover_y"]) if home_event["turnover_y"] is not None else None
                if defender_name:
                    # Home team sees they were blocked
                    current_point_events_home.append({
                        "type": "opponent_turnover",
                        "description": f"Opponent turnover (Blocked by {defender_name})",
                        "yard_line": yard_line
                    })
                    # Away team sees they got a block
                    current_point_events_away.append({
                        "type": "block",
                        "description": f"Block by {defender_name}",
                        "yard_line": yard_line
                    })
            # Away team's perspective: opponent blocked them
            if away_event and away_event["event_type"] == 12:
                defender_name = away_event["defender_last"] if away_event["defender_last"] else None
                yard_line = int(away_event["turnover_y"]) if away_event["turnover_y"] is not None else None
                if defender_name:
                    # Away team sees they were blocked
                    current_point_events_away.append({
                        "type": "opponent_turnover",
                        "description": f"Opponent turnover (Blocked by {defender_name})",
                        "yard_line": yard_line
                    })
                    # Home team sees they got a block
                    current_point_events_home.append({
                        "type": "block",
                        "description": f"Block by {defender_name}",
                        "yard_line": yard_line
                    })

        # Opponent turnover events (from home perspective, opponent turns over)
        elif event_type in [13, 14]:  # THROWAWAY_BY_OPPOSING or STALL_ON_OPPOSING
            # Process for home team perspective
            if home_event and home_event["event_type"] in [13, 14]:
                turnover_type = "Throwaway" if home_event["event_type"] == 13 else "Stall"
                yard_line = int(home_event["turnover_y"]) if home_event["turnover_y"] is not None else None
                current_point_events_home.append({
                    "type": "opponent_turnover",
                    "description": f"Opponent turnover ({turnover_type})",
                    "yard_line": yard_line
                })
            # Process for away team perspective
            if away_event and away_event["event_type"] in [13, 14]:
                turnover_type = "Throwaway" if away_event["event_type"] == 13 else "Stall"
                yard_line = int(away_event["turnover_y"]) if away_event["turnover_y"] is not None else None
                current_point_events_away.append({
                    "type": "opponent_turnover",
                    "description": f"Opponent turnover ({turnover_type})",
                    "yard_line": yard_line
                })

        # Goal events (from home team perspective)
        elif event_type in [19, 15]:  # GOAL or SCORE_BY_OPPOSING
            # Don't set end_time here - it will be set when next point starts
            # Since there's no time between points, the goal time equals the next pull time

            # Type 19 = Home team scores
            # Type 15 = Away team scores (opponent scores from home perspective)
            if event_type == 19:  # Home team scores
                current_score["home"] += 1
                if current_point_home:
                    current_point_home["scoring_team"] = "home"
                if current_point_away:
                    current_point_away["scoring_team"] = "home"
            else:  # Type 15: Away team scores
                current_score["away"] += 1
                if current_point_home:
                    current_point_home["scoring_team"] = "away"
                if current_point_away:
                    current_point_away["scoring_team"] = "away"

            # Update point scores after goal
            if current_point_home:
                current_point_home["score"] = f"{current_score['away']}-{current_score['home']}"
                current_point_home["home_score"] = current_score["home"]
                current_point_home["away_score"] = current_score["away"]
            if current_point_away:
                current_point_away["score"] = f"{current_score['away']}-{current_score['home']}"
                current_point_away["home_score"] = current_score["home"]
                current_point_away["away_score"] = current_score["away"]

            # Add goal event to the scoring team's events
            if event_type == 19:  # Home team scored
                # Use home event for home goal details
                if home_event and home_event["receiver_last"] and home_event["thrower_last"]:
                    # Calculate direction for goal if coordinates available
                    if (home_event["thrower_y"] is not None and home_event["receiver_y"] is not None and
                        home_event["thrower_x"] is not None and home_event["receiver_x"] is not None):
                        vertical_yards = home_event["receiver_y"] - home_event["thrower_y"]
                        horizontal_yards = home_event["receiver_x"] - home_event["thrower_x"]
                        angle_radians = math.atan2(vertical_yards, -horizontal_yards)
                        angle_degrees = math.degrees(angle_radians)

                        goal_event = {
                            "type": "goal",
                            "description": f"Score from {home_event['thrower_last']} to {home_event['receiver_last']}",
                            "yard_line": None,
                            "direction": angle_degrees
                        }
                        current_point_events_home.append(goal_event)
                    else:
                        goal_event = {
                            "type": "goal",
                            "description": f"Score from {home_event['thrower_last']} to {home_event['receiver_last']}",
                            "yard_line": None
                        }
                        current_point_events_home.append(goal_event)
                # Add "They scored" event to away team's events
                current_point_events_away.append({
                    "type": "opponent_score",
                    "description": "They scored",
                    "yard_line": None
                })
            else:  # Away team scored (event_type == 15)
                # Use away event for away goal details if available
                if away_event and away_event["event_type"] == 19:  # Away team reports their own goal as type 19
                    if away_event["receiver_last"] and away_event["thrower_last"]:
                        # Calculate direction for goal if coordinates available
                        if (away_event["thrower_y"] is not None and away_event["receiver_y"] is not None and
                            away_event["thrower_x"] is not None and away_event["receiver_x"] is not None):
                            vertical_yards = away_event["receiver_y"] - away_event["thrower_y"]
                            horizontal_yards = away_event["receiver_x"] - away_event["thrower_x"]
                            angle_radians = math.atan2(vertical_yards, -horizontal_yards)
                            angle_degrees = math.degrees(angle_radians)

                            goal_event = {
                                "type": "goal",
                                "description": f"Score from {away_event['thrower_last']} to {away_event['receiver_last']}",
                                "yard_line": None,
                                "direction": angle_degrees
                            }
                            current_point_events_away.append(goal_event)
                        else:
                            goal_event = {
                                "type": "goal",
                                "description": f"Score from {away_event['thrower_last']} to {away_event['receiver_last']}",
                                "yard_line": None
                            }
                            current_point_events_away.append(goal_event)
                # Add "They scored" event to home team's events
                current_point_events_home.append({
                    "type": "opponent_score",
                    "description": "They scored",
                    "yard_line": None
                })

        # Pass events
        elif event_type == 18:  # PASS
            # Process pass for home team if it's their event
            if home_event and home_event["event_type"] == 18:
                if home_event["receiver_last"] and home_event["thrower_last"]:
                    # Calculate pass distance and type
                    if (home_event["thrower_y"] is not None and home_event["receiver_y"] is not None and
                        home_event["thrower_x"] is not None and home_event["receiver_x"] is not None):
                        # Calculate vertical distance (positive = forward, negative = backward)
                        vertical_yards = home_event["receiver_y"] - home_event["thrower_y"]
                        horizontal_yards = home_event["receiver_x"] - home_event["thrower_x"]

                        # Calculate actual distance using Pythagorean theorem
                        actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)

                        # Calculate direction angle in degrees
                        angle_radians = math.atan2(vertical_yards, -horizontal_yards)
                        angle_degrees = math.degrees(angle_radians)

                        # Determine pass type based on vertical yards
                        if vertical_yards <= 0:
                            pass_type = "Dump"
                        elif vertical_yards >= 40:
                            pass_type = "Huck"
                        else:
                            pass_type = "Pass"

                        # Format distance for display
                        distance_str = f"{int(actual_distance)}y"
                        pass_event = {
                            "type": "pass",
                            "description": f"{distance_str} {pass_type} from {home_event['thrower_last']} to {home_event['receiver_last']}",
                            "yard_line": None,  # Don't show yard line for pass events
                            "direction": angle_degrees
                        }
                    else:
                        pass_event = {
                            "type": "pass",
                            "description": f"Pass from {home_event['thrower_last']} to {home_event['receiver_last']}",
                            "yard_line": None
                        }
                    # Add to home team's events
                    current_point_events_home.append(pass_event)

            # Process pass for away team if it's their event
            if away_event and away_event["event_type"] == 18:
                if away_event["receiver_last"] and away_event["thrower_last"]:
                    # Calculate pass distance and type
                    if (away_event["thrower_y"] is not None and away_event["receiver_y"] is not None and
                        away_event["thrower_x"] is not None and away_event["receiver_x"] is not None):
                        # Calculate vertical distance (positive = forward, negative = backward)
                        vertical_yards = away_event["receiver_y"] - away_event["thrower_y"]
                        horizontal_yards = away_event["receiver_x"] - away_event["thrower_x"]

                        # Calculate actual distance using Pythagorean theorem
                        actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)

                        # Calculate direction angle in degrees
                        angle_radians = math.atan2(vertical_yards, -horizontal_yards)
                        angle_degrees = math.degrees(angle_radians)

                        # Determine pass type based on vertical yards
                        if vertical_yards <= 0:
                            pass_type = "Dump"
                        elif vertical_yards >= 40:
                            pass_type = "Huck"
                        else:
                            pass_type = "Pass"

                        # Format distance for display
                        distance_str = f"{int(actual_distance)}y"
                        pass_event = {
                            "type": "pass",
                            "description": f"{distance_str} {pass_type} from {away_event['thrower_last']} to {away_event['receiver_last']}",
                            "yard_line": None,  # Don't show yard line for pass events
                            "direction": angle_degrees
                        }
                    else:
                        pass_event = {
                            "type": "pass",
                            "description": f"Pass from {away_event['thrower_last']} to {away_event['receiver_last']}",
                            "yard_line": None
                        }
                    # Add to away team's events
                    current_point_events_away.append(pass_event)

        # Turnover events
        elif event_type == 11:  # BLOCK
            # Process block for home team if it's their event
            if home_event and home_event["event_type"] == 11:
                if home_event["defender_last"]:
                    yard_line = int(home_event["turnover_y"]) if home_event["turnover_y"] is not None else None
                    block_event = {
                        "type": "block",
                        "description": f"Block by {home_event['defender_last']}",
                        "yard_line": yard_line
                    }
                    # Add to home team's events
                    current_point_events_home.append(block_event)
                    # Add opponent turnover to away team's events with blocker name
                    current_point_events_away.append({
                        "type": "opponent_turnover",
                        "description": f"Opponent turnover (Blocked by {home_event['defender_last']})",
                        "yard_line": yard_line
                    })

            # Process block for away team if it's their event
            if away_event and away_event["event_type"] == 11:
                if away_event["defender_last"]:
                    yard_line = int(away_event["turnover_y"]) if away_event["turnover_y"] is not None else None
                    block_event = {
                        "type": "block",
                        "description": f"Block by {away_event['defender_last']}",
                        "yard_line": yard_line
                    }
                    # Add to away team's events
                    current_point_events_away.append(block_event)
                    # Add opponent turnover to home team's events with blocker name
                    current_point_events_home.append({
                        "type": "opponent_turnover",
                        "description": f"Opponent turnover (Blocked by {away_event['defender_last']})",
                        "yard_line": yard_line
                    })
        elif event_type == 20:  # DROP
            if event["receiver_last"]:
                yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
                drop_event = {
                    "type": "drop",
                    "description": f"Drop by {event['receiver_last']}",
                    "yard_line": yard_line
                }
                # Add to home team's events (since we're processing home team events)
                current_point_events_home.append(drop_event)
                # Add opponent turnover to away team's events
                current_point_events_away.append({
                    "type": "opponent_turnover",
                    "description": "Opponent turnover (Drop)",
                    "yard_line": yard_line
                })
        elif event_type == 22:  # THROWAWAY
            if event["thrower_last"]:
                # Calculate distance and direction for throwaway if coordinates available
                if (event["thrower_y"] is not None and event["turnover_y"] is not None and
                    event["thrower_x"] is not None and event["turnover_x"] is not None):
                    # Calculate vertical and horizontal distance
                    vertical_yards = event["turnover_y"] - event["thrower_y"]
                    horizontal_yards = event["turnover_x"] - event["thrower_x"]

                    # Calculate actual distance using Pythagorean theorem
                    actual_distance = math.sqrt(horizontal_yards**2 + vertical_yards**2)

                    # Calculate direction angle in degrees
                    angle_radians = math.atan2(vertical_yards, -horizontal_yards)
                    angle_degrees = math.degrees(angle_radians)

                    # Determine if it's a huck throwaway (>=40 vertical yards)
                    throwaway_type = "Huck throwaway" if vertical_yards >= 40 else "Throwaway"

                    # Format distance for display
                    distance_str = f"{int(actual_distance)}y"

                    throwaway_event = {
                        "type": "throwaway",
                        "description": f"{distance_str} {throwaway_type} by {event['thrower_last']}",
                        "yard_line": None,  # Don't show yard line for throwaway events
                        "direction": angle_degrees
                    }
                else:
                    # Fallback for throwaways without coordinates
                    throwaway_event = {
                        "type": "throwaway",
                        "description": f"Throwaway by {event['thrower_last']}",
                        "yard_line": None  # Don't show yard line for throwaway events
                    }
                # Add to home team's events (since we're processing home team events)
                current_point_events_home.append(throwaway_event)
                # Add opponent turnover to away team's events
                current_point_events_away.append({
                    "type": "opponent_turnover",
                    "description": "Opponent turnover (Throwaway)",
                    "yard_line": None
                })
        elif event_type == 24:  # STALL
            yard_line = int(event["turnover_y"]) if event["turnover_y"] is not None else None
            stall_event = {
                "type": "stall",
                "description": "Stall",
                "yard_line": yard_line
            }
            # Add to home team's events (since we're processing home team events)
            current_point_events_home.append(stall_event)
            # Add opponent turnover to away team's events
            current_point_events_away.append({
                "type": "opponent_turnover",
                "description": "Opponent turnover (Stall)",
                "yard_line": yard_line
            })

    # Save last points if exist
    if current_point_home:
        current_point_home["events"] = current_point_events_home
        # For the last point, estimate a reasonable duration since there's no next pull
        if not current_point_home.get("end_time"):
            # Estimate last point took 90 seconds
            if current_point_home["start_time"] is not None:
                current_point_home["end_time"] = current_point_home["start_time"] + 90
                current_point_home["duration_seconds"] = 90
            else:
                current_point_home["duration_seconds"] = 0
        points_home.append(current_point_home)

    if current_point_away:
        current_point_away["events"] = current_point_events_away
        if not current_point_away.get("end_time"):
            if current_point_away["start_time"] is not None:
                current_point_away["end_time"] = current_point_away["start_time"] + 90
                current_point_away["duration_seconds"] = 90
            else:
                current_point_away["duration_seconds"] = 0
        points_away.append(current_point_away)

    # Combine points from both perspectives
    points = points_home + points_away

    # Add formatted time and duration to each point
    for point in points:
        minutes = point["duration_seconds"] // 60 if point["duration_seconds"] else 0
        seconds = point["duration_seconds"] % 60 if point["duration_seconds"] else 0

        if minutes > 0:
            point["duration"] = f"{minutes}m{seconds:02d}s"
        else:
            point["duration"] = f"{seconds}s"

        # Format time remaining in quarter at END of point (when goal was scored)
        # Use end_time if available, otherwise fall back to start_time
        time_reference = point.get("end_time") or point["start_time"]
        if time_reference is not None:
            quarter_time = 12 * 60  # 12 minutes per quarter
            time_in_quarter = time_reference % quarter_time

            # If the time is exactly at the quarter boundary (0), it means the quarter ended
            if time_in_quarter == 0 and time_reference > 0:
                point["time"] = "00:00"
            else:
                minutes_remaining = (quarter_time - time_in_quarter) // 60
                seconds_remaining = (quarter_time - time_in_quarter) % 60
                point["time"] = f"{minutes_remaining:02d}:{seconds_remaining:02d}"
        else:
            point["time"] = "12:00"

        # Remove end_time from output (it was only needed for calculations)
        if "end_time" in point:
            del point["end_time"]

    return points