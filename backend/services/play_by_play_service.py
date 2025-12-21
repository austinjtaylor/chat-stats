"""
Play-by-play service for processing game events.

This file now serves as a thin orchestrator delegating to specialized service modules.
The original 577-line file has been split into focused services for better maintainability.

See backend/services/play_by_play/ for the new modular structure:
- event_handlers.py: Process different event types (329 lines)
- point_builder.py: Manage point state and construction (255 lines)
- player_enrichment.py: Fetch and enrich player data (134 lines)

Total: 739 lines across 3 focused service modules (was 577 lines in 1 monolithic file)
"""

from typing import Any

from .play_by_play import EventHandlers, PlayerEnrichment, PointBuilder


def process_team_events(
    events: list[dict], team: str, player_lookup: dict[str, dict[str, str]]
) -> list[dict[str, Any]]:
    """
    Process events for a single team to build their play-by-play perspective.

    Args:
        events: List of events for this team
        team: 'home' or 'away'
        player_lookup: Dictionary mapping player_id to dict with full_name and last_name

    Returns:
        List of points with events from this team's perspective
    """
    points = []
    current_point = None
    current_point_events = []

    # Initialize point builder and event handlers
    point_builder = PointBuilder()
    handlers = EventHandlers()

    for event in events:
        event_type = event["event_type"]

        # Quarter end events
        if event_type in [28, 29, 30, 31]:  # Quarter/half/regulation ends
            if current_point:
                # Calculate the end time for the quarter
                quarter_end_time = point_builder.get_quarter_end_time(event_type)
                if quarter_end_time is not None:
                    point_builder.finalize_point(current_point, quarter_end_time)

                current_point["events"] = current_point_events
                points.append(current_point)
                current_point = None
                current_point_events = []

            # Update quarter
            point_builder.update_quarter(event_type)
            continue

        # Start of a new point (pull)
        elif event_type in [1, 2]:  # START_D_POINT or START_O_POINT
            # Save previous point if exists
            if current_point:
                if event["event_time"] is not None:
                    absolute_time = point_builder.quarter_offset + event["event_time"]
                    point_builder.finalize_point(current_point, absolute_time)

                current_point["events"] = current_point_events
                points.append(current_point)

            # Create new point
            current_point = point_builder.create_point(event, team, player_lookup)
            current_point_events = []

            # Add initial pull event if this team pulls
            if current_point["pulling_team"] == team:
                pull_event = handlers.handle_pull_event(event, team, current_point)
                if pull_event:
                    current_point_events.append(pull_event)

        # Pull inbounds/out of bounds (detailed pull data)
        elif event_type in [7, 8]:  # PULL_INBOUNDS or PULL_OUT_OF_BOUNDS
            detailed_pull = handlers.handle_pull_event(event, team, current_point)
            if detailed_pull:
                # Replace generic pull with detailed one
                if current_point_events and current_point_events[-1]["type"] == "pull":
                    current_point_events[-1] = detailed_pull
                else:
                    current_point_events.append(detailed_pull)

        # Pass events
        elif event_type == 18:  # PASS
            pass_event = handlers.handle_pass_event(event)
            if pass_event:
                current_point_events.append(pass_event)

        # Goal events
        elif event_type == 19:  # GOAL (this team scored)
            point_builder.update_score_for_goal(team, current_point)
            goal_event = handlers.handle_goal_event(event)
            if goal_event:
                current_point_events.append(goal_event)

        elif event_type == 15:  # SCORE_BY_OPPOSING (opponent scored)
            point_builder.update_score_for_opponent_goal(team, current_point)
            opponent_score_event = handlers.handle_opponent_score_event()
            current_point_events.append(opponent_score_event)

        # Block events
        elif event_type == 11:  # BLOCK (this team got a block)
            block_event = handlers.handle_block_event(event)
            if block_event:
                current_point_events.append(block_event)

        elif event_type == 12:  # BLOCK_BY_OPPOSING (opponent got a block)
            opponent_block = handlers.handle_opponent_block_event(event)
            current_point_events.append(opponent_block)

        # Other turnovers
        elif event_type == 20:  # DROP
            drop_event = handlers.handle_drop_event(event)
            if drop_event:
                current_point_events.append(drop_event)

        elif event_type == 22:  # THROWAWAY
            throwaway_event = handlers.handle_throwaway_event(event)
            if throwaway_event:
                current_point_events.append(throwaway_event)

        elif event_type == 24:  # STALL
            stall_event = handlers.handle_stall_event(event)
            current_point_events.append(stall_event)

        # Opponent turnovers
        elif event_type in [13, 14]:  # THROWAWAY_BY_OPPOSING or STALL_ON_OPPOSING
            turnover_type = "Throwaway" if event_type == 13 else "Stall"
            opponent_turnover = handlers.handle_opponent_turnover_event(
                event, turnover_type
            )
            current_point_events.append(opponent_turnover)

    # Save last point if exists
    if current_point:
        current_point["events"] = current_point_events
        point_builder.finalize_point(current_point)
        points.append(current_point)

    # Add formatted time and duration to each point
    PointBuilder.format_point_times(points)

    return points


def calculate_play_by_play(stats_system, game_id: str) -> list[dict[str, Any]]:
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

    # Get events from both teams (without player JOINs for better performance)
    events_query = """
    SELECT
        e.event_index, e.team, e.event_type, e.event_time,
        e.thrower_id, e.receiver_id, e.defender_id, e.puller_id,
        e.thrower_x, e.thrower_y, e.receiver_x, e.receiver_y,
        e.turnover_x, e.turnover_y, e.pull_x, e.pull_y,
        e.pull_ms, e.line_players
    FROM game_events e
    WHERE e.game_id = :game_id
    ORDER BY e.team, e.event_index
    """

    events = stats_system.db.execute_query(events_query, {"game_id": game_id})
    if not events:
        return []

    # Collect all unique player IDs and fetch player data
    all_player_ids = PlayerEnrichment.collect_player_ids(events)
    player_lookup = PlayerEnrichment.fetch_players(
        stats_system.db, all_player_ids, game_year
    )

    # Enrich events with player names from lookup
    PlayerEnrichment.enrich_events(events, player_lookup)

    # Separate events by team
    home_events = [e for e in events if e["team"] == "home"]
    away_events = [e for e in events if e["team"] == "away"]

    # Process each team's events separately
    home_points = process_team_events(home_events, "home", player_lookup)
    away_points = process_team_events(away_events, "away", player_lookup)

    # Combine and return both perspectives
    return home_points + away_points
