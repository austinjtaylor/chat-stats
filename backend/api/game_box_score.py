"""
Game box score API endpoint with detailed player and team statistics.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any


def calculate_team_stats(stats_system, game_id: str, team_id: str, is_home: bool) -> Dict[str, Any]:
    """
    Calculate team statistics for a single game.

    Args:
        stats_system: The stats system instance
        game_id: Game identifier
        team_id: Team identifier
        is_home: Whether this is the home team

    Returns:
        Dictionary containing all team statistics
    """
    from data.possession import calculate_possessions, calculate_redzone_stats_for_team

    # Get team aggregate stats from player_game_stats
    team_stats_query = """
    SELECT
        SUM(completions) as total_completions,
        SUM(throw_attempts) as total_attempts,
        SUM(hucks_completed) as total_hucks_completed,
        SUM(hucks_attempted) as total_hucks_attempted,
        SUM(blocks) as total_blocks,
        SUM(throwaways) as total_throwaways,
        SUM(stalls) as total_stalls,
        SUM(drops) as total_drops
    FROM player_game_stats
    WHERE game_id = :game_id AND team_id = :team_id
    """

    team_stats_result = stats_system.db.execute_query(
        team_stats_query, {"game_id": game_id, "team_id": team_id}
    )

    if not team_stats_result:
        return {}

    team_stats = team_stats_result[0]

    # Calculate basic percentages
    completions = team_stats["total_completions"] or 0
    attempts = team_stats["total_attempts"] or 0
    completion_pct = round((completions / attempts * 100), 1) if attempts > 0 else 0

    hucks_completed = team_stats["total_hucks_completed"] or 0
    hucks_attempted = team_stats["total_hucks_attempted"] or 0
    huck_pct = round((hucks_completed / hucks_attempted * 100), 1) if hucks_attempted > 0 else 0

    blocks = team_stats["total_blocks"] or 0
    turnovers = (team_stats["total_throwaways"] or 0) + (team_stats["total_stalls"] or 0)

    # Calculate possession stats from game_events
    possession_stats = calculate_possessions(stats_system.db, game_id, team_id, is_home)

    # Calculate red zone stats
    redzone_stats = calculate_redzone_stats_for_team(stats_system.db, game_id, team_id, is_home)

    # Build result dictionary
    result = {
        "completions": {
            "percentage": completion_pct,
            "made": completions,
            "attempted": attempts
        },
        "hucks": {
            "percentage": huck_pct,
            "made": hucks_completed,
            "attempted": hucks_attempted
        },
        "blocks": blocks,
        "turnovers": turnovers
    }

    # Add possession stats if available
    if possession_stats:
        # Hold %
        hold_pct = 0
        hold_made = possession_stats.get("o_line_scores", 0)
        hold_total = possession_stats.get("o_line_points", 0)
        if hold_total > 0:
            hold_pct = round((hold_made / hold_total * 100), 1)

        # O-Line Conversion %
        o_conv_pct = 0
        o_conv_made = possession_stats.get("o_line_scores", 0)
        o_conv_total = possession_stats.get("o_line_possessions", 0)
        if o_conv_total > 0:
            o_conv_pct = round((o_conv_made / o_conv_total * 100), 1)

        # Break %
        break_pct = 0
        break_made = possession_stats.get("d_line_scores", 0)
        break_total = possession_stats.get("d_line_points", 0)
        if break_total > 0:
            break_pct = round((break_made / break_total * 100), 1)

        # D-Line Conversion %
        d_conv_pct = 0
        d_conv_made = possession_stats.get("d_line_scores", 0)
        d_conv_total = possession_stats.get("d_line_possessions", 0)
        if d_conv_total > 0:
            d_conv_pct = round((d_conv_made / d_conv_total * 100), 1)

        result["hold"] = {
            "percentage": hold_pct,
            "made": hold_made,
            "total": hold_total
        }
        result["o_line_conversion"] = {
            "percentage": o_conv_pct,
            "made": o_conv_made,
            "total": o_conv_total
        }
        result["break"] = {
            "percentage": break_pct,
            "made": break_made,
            "total": break_total
        }
        result["d_line_conversion"] = {
            "percentage": d_conv_pct,
            "made": d_conv_made,
            "total": d_conv_total
        }

    # Add red zone stats if available
    if redzone_stats:
        result["redzone_conversion"] = {
            "percentage": redzone_stats.get("percentage", 0),
            "made": redzone_stats.get("goals", 0),
            "total": redzone_stats.get("possessions", 0)
        }

    return result


def create_box_score_routes(stats_system):
    """Create game box score API routes."""
    router = APIRouter()

    @router.get("/api/games/{game_id}/box-score")
    async def get_game_box_score(game_id: str):
        """Get complete box score for a game including all player statistics"""
        try:
            # Get game information with quarter scoring
            game_query = """
            SELECT
                g.game_id,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                g.status,
                g.start_timestamp,
                g.location,
                g.year,
                g.week,
                ht.full_name as home_team_name,
                ht.city as home_team_city,
                ht.name as home_team_short_name,
                at.full_name as away_team_name,
                at.city as away_team_city,
                at.name as away_team_short_name
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
            LEFT JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
            WHERE g.game_id = :game_id
            """

            game_info = stats_system.db.execute_query(game_query, {"game_id": game_id})
            if not game_info:
                raise HTTPException(status_code=404, detail="Game not found")

            game = game_info[0]

            # Get quarter-by-quarter scoring from game events
            quarter_scores = calculate_quarter_scores(stats_system, game_id)

            # Get all player statistics for both teams
            player_stats_query = """
            SELECT
                p.full_name,
                p.jersey_number,
                pgs.player_id,
                pgs.team_id,
                pgs.o_points_played,
                pgs.d_points_played,
                (pgs.o_points_played + pgs.d_points_played) as points_played,
                pgs.assists,
                pgs.goals,
                pgs.blocks,
                pgs.completions,
                pgs.throw_attempts,
                CASE
                    WHEN pgs.throw_attempts > 0
                    THEN ROUND((pgs.completions * 100.0 / pgs.throw_attempts), 1)
                    ELSE 0
                END as completion_percentage,
                pgs.throwaways,
                pgs.stalls,
                pgs.drops,
                pgs.callahans,
                pgs.hockey_assists,
                pgs.yards_thrown,
                pgs.yards_received,
                (pgs.yards_thrown + pgs.yards_received) as total_yards,
                pgs.catches,
                pgs.hucks_completed,
                pgs.hucks_attempted,
                pgs.hucks_received,
                CASE
                    WHEN pgs.hucks_attempted > 0
                    THEN ROUND((pgs.hucks_completed * 100.0 / pgs.hucks_attempted), 1)
                    ELSE 0
                END as huck_percentage,
                CASE
                    WHEN (pgs.throwaways + pgs.stalls + pgs.drops) > 0
                    THEN ROUND((pgs.yards_thrown + pgs.yards_received) * 1.0 / (pgs.throwaways + pgs.stalls + pgs.drops), 1)
                    ELSE NULL
                END as yards_per_turn,
                (pgs.goals + pgs.assists + pgs.blocks - pgs.throwaways - pgs.drops - pgs.stalls) as plus_minus
            FROM player_game_stats pgs
            JOIN players p ON pgs.player_id = p.player_id AND pgs.year = p.year
            WHERE pgs.game_id = :game_id
            AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0)
            ORDER BY pgs.team_id, (pgs.goals + pgs.assists) DESC, plus_minus DESC
            """

            all_players = stats_system.db.execute_query(
                player_stats_query, {"game_id": game_id}
            )

            # Separate players by team
            home_players = []
            away_players = []

            for player in all_players:
                player_data = {
                    "name": player["full_name"],
                    "jersey_number": player["jersey_number"] or "",
                    "points_played": player["points_played"],
                    "o_points_played": player["o_points_played"],
                    "d_points_played": player["d_points_played"],
                    "assists": player["assists"],
                    "goals": player["goals"],
                    "blocks": player["blocks"],
                    "plus_minus": player["plus_minus"],
                    "yards_received": player["yards_received"],
                    "yards_thrown": player["yards_thrown"],
                    "total_yards": player["total_yards"],
                    "completions": player["completions"],
                    "completion_percentage": player["completion_percentage"],
                    "hockey_assists": player["hockey_assists"],
                    "hucks_completed": player["hucks_completed"],
                    "hucks_received": player["hucks_received"],
                    "huck_percentage": player["huck_percentage"],
                    "turnovers": player["throwaways"] + player["stalls"],
                    "yards_per_turn": player["yards_per_turn"],
                    "stalls": player["stalls"],
                    "callahans": player["callahans"],
                    "drops": player["drops"],
                }

                if player["team_id"] == game["home_team_id"]:
                    home_players.append(player_data)
                elif player["team_id"] == game["away_team_id"]:
                    away_players.append(player_data)

            # Calculate team statistics
            home_team_stats = calculate_team_stats(
                stats_system, game_id, game["home_team_id"], is_home=True
            )
            away_team_stats = calculate_team_stats(
                stats_system, game_id, game["away_team_id"], is_home=False
            )

            return {
                "game_id": game["game_id"],
                "status": game["status"],
                "start_timestamp": game["start_timestamp"],
                "location": game["location"],
                "year": game["year"],
                "week": game["week"],
                "home_team": {
                    "team_id": game["home_team_id"],
                    "name": game["home_team_short_name"],
                    "full_name": game["home_team_name"],
                    "city": game["home_team_city"],
                    "final_score": game["home_score"],
                    "quarter_scores": quarter_scores.get("home", []),
                    "players": home_players,
                    "stats": home_team_stats,
                },
                "away_team": {
                    "team_id": game["away_team_id"],
                    "name": game["away_team_short_name"],
                    "full_name": game["away_team_name"],
                    "city": game["away_team_city"],
                    "final_score": game["away_score"],
                    "quarter_scores": quarter_scores.get("away", []),
                    "players": away_players,
                    "stats": away_team_stats,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/games")
    async def get_games(year: int = None, team_id: str = None, limit: int = 500):
        """Get list of games with optional filters - compatible with frontend"""
        try:
            year_filter = f"AND g.year = {year}" if year else ""
            team_filter = f"AND (g.home_team_id = '{team_id}' OR g.away_team_id = '{team_id}')" if team_id and team_id != 'all' else ""

            query = f"""
            SELECT
                g.game_id,
                g.game_id as id,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                g.status,
                g.start_timestamp as date,
                g.location as venue,
                g.year,
                g.week,
                ht.full_name as home_team,
                at.full_name as away_team
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
            LEFT JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
            WHERE g.status = 'Final' {year_filter} {team_filter}
            ORDER BY g.start_timestamp DESC
            LIMIT :limit
            """

            games = stats_system.db.execute_query(query, {"limit": limit})

            return {
                "games": games,
                "total": len(games),
                "page": 1,
                "pages": 1
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/games/list")
    async def get_games_list(year: int = None, team_id: str = None, limit: int = 500):
        """Get list of all games for the game selection dropdown"""
        try:
            year_filter = f"AND g.year = {year}" if year else ""
            team_filter = f"AND (g.home_team_id = :team_id OR g.away_team_id = :team_id)" if team_id else ""

            query = f"""
            SELECT
                g.game_id,
                g.home_team_id,
                g.away_team_id,
                g.home_score,
                g.away_score,
                g.status,
                g.start_timestamp,
                g.year,
                g.week,
                ht.full_name as home_team_name,
                ht.city as home_team_city,
                at.full_name as away_team_name,
                at.city as away_team_city
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
            LEFT JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
            WHERE g.status = 'Final' {year_filter} {team_filter}
            ORDER BY g.start_timestamp DESC
            LIMIT :limit
            """

            params = {"limit": limit}
            if team_id:
                params["team_id"] = team_id

            games = stats_system.db.execute_query(query, params)

            return {
                "games": [
                    {
                        "game_id": game["game_id"],
                        "display_name": f"{game['away_team_name']} vs {game['home_team_name']}",
                        "date": game["start_timestamp"],
                        "home_team": game["home_team_name"],
                        "away_team": game["away_team_name"],
                        "home_score": game["home_score"],
                        "away_score": game["away_score"],
                        "year": game["year"],
                        "week": game["week"],
                    }
                    for game in games
                ]
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/api/games/{game_id}/play-by-play")
    async def get_game_play_by_play(game_id: str):
        """Get play-by-play data for a game"""
        try:
            points = calculate_play_by_play(stats_system, game_id)
            return {"points": points}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router


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