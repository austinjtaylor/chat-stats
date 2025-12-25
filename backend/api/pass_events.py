"""
Pass events API endpoint for querying pass data across games/seasons.
"""

import math

from fastapi import APIRouter, Query


def create_pass_events_routes(stats_system):
    """Create pass events API routes."""
    router = APIRouter()

    @router.get("/api/pass-events")
    async def get_pass_events(
        season: int | None = Query(None, description="Filter by season year"),
        game_id: str | None = Query(None, description="Filter by specific game"),
        off_team_id: str | None = Query(None, description="Filter by offensive team"),
        def_team_id: str | None = Query(None, description="Filter by defensive team"),
        thrower_id: str | None = Query(None, description="Filter by thrower player"),
        receiver_id: str | None = Query(None, description="Filter by receiver player"),
        pass_types: str | None = Query(
            None, description="Comma-separated pass types: huck,swing,dump,gainer,dish"
        ),
        results: str | None = Query(
            None, description="Comma-separated results: goal,completion,turnover"
        ),
        event_types: str | None = Query(
            None,
            description="Comma-separated event types: throws,catches,assists,goals,throwaways,drops",
        ),
        origin_x_min: float | None = Query(
            None, description="Min thrower X coordinate"
        ),
        origin_x_max: float | None = Query(
            None, description="Max thrower X coordinate"
        ),
        origin_y_min: float | None = Query(
            None, description="Min thrower Y coordinate"
        ),
        origin_y_max: float | None = Query(
            None, description="Max thrower Y coordinate"
        ),
        dest_x_min: float | None = Query(None, description="Min receiver X coordinate"),
        dest_x_max: float | None = Query(None, description="Max receiver X coordinate"),
        dest_y_min: float | None = Query(None, description="Min receiver Y coordinate"),
        dest_y_max: float | None = Query(None, description="Max receiver Y coordinate"),
        distance_min: float | None = Query(None, description="Min throw distance"),
        distance_max: float | None = Query(None, description="Max throw distance"),
        limit: int | None = Query(
            None, description="Max events to return (no limit if not specified)"
        ),
    ):
        """
        Get pass events with comprehensive filtering.

        Returns events with coordinates and aggregate statistics.
        """
        # Build the query dynamically
        query = """
        SELECT
            ge.game_id,
            ge.event_type,
            ge.pass_type,
            ge.thrower_id,
            ge.receiver_id,
            ge.thrower_x,
            ge.thrower_y,
            ge.receiver_x,
            ge.receiver_y,
            ge.turnover_x,
            ge.turnover_y,
            g.year,
            g.home_team_id,
            g.away_team_id,
            ge.team as event_team,
            p_thrower.full_name as thrower_name,
            p_receiver.full_name as receiver_name
        FROM game_events ge
        JOIN games g ON ge.game_id = g.game_id
        LEFT JOIN players p_thrower ON ge.thrower_id = p_thrower.player_id AND g.year = p_thrower.year
        LEFT JOIN players p_receiver ON ge.receiver_id = p_receiver.player_id AND g.year = p_receiver.year
        WHERE ge.event_type IN (18, 19, 20, 22)
          AND ge.thrower_x IS NOT NULL
          AND ge.thrower_y IS NOT NULL
        """

        params = {}

        # Apply filters
        if season:
            query += " AND g.year = :season"
            params["season"] = season

        if game_id:
            query += " AND ge.game_id = :game_id"
            params["game_id"] = game_id

        if off_team_id:
            # Offensive team is the one with possession (event_team matches their home/away status)
            query += """ AND (
                (ge.team = 'home' AND g.home_team_id = :off_team_id) OR
                (ge.team = 'away' AND g.away_team_id = :off_team_id)
            )"""
            params["off_team_id"] = off_team_id

        if def_team_id:
            # Defensive team is the opposing team
            query += """ AND (
                (ge.team = 'home' AND g.away_team_id = :def_team_id) OR
                (ge.team = 'away' AND g.home_team_id = :def_team_id)
            )"""
            params["def_team_id"] = def_team_id

        if thrower_id:
            query += " AND ge.thrower_id = :thrower_id"
            params["thrower_id"] = thrower_id

        if receiver_id:
            query += " AND ge.receiver_id = :receiver_id"
            params["receiver_id"] = receiver_id

        if pass_types:
            types_list = [t.strip() for t in pass_types.split(",")]
            query += " AND ge.pass_type IN :pass_types"
            params["pass_types"] = tuple(types_list)

        if results:
            results_list = [r.strip() for r in results.split(",")]
            result_conditions = []
            if "goal" in results_list:
                result_conditions.append("ge.event_type = 19")
            if "completion" in results_list:
                result_conditions.append("ge.event_type = 18")
            if "turnover" in results_list:
                result_conditions.append("ge.event_type IN (20, 22)")
            if result_conditions:
                query += f" AND ({' OR '.join(result_conditions)})"

        # Event types filter (alternative to results, more granular)
        # Each checkbox controls specific event types independently:
        # - throws/catches: completions (18)
        # - assists/goals: scoring plays (19)
        # - throwaways: throwaway turnovers (22)
        # - drops: drop turnovers (20)
        if event_types:
            event_types_list = [et.strip() for et in event_types.split(",")]
            event_conditions = []
            # Event type 18 (completion): controlled by 'throws' or 'catches'
            if "throws" in event_types_list or "catches" in event_types_list:
                event_conditions.append("ge.event_type = 18")
            # Event type 19 (goal): controlled by 'assists' or 'goals'
            if "assists" in event_types_list or "goals" in event_types_list:
                event_conditions.append("ge.event_type = 19")
            # Event type 20 (drop): controlled by 'drops' only
            if "drops" in event_types_list:
                event_conditions.append("ge.event_type = 20")
            # Event type 22 (throwaway): controlled by 'throwaways' only
            if "throwaways" in event_types_list:
                event_conditions.append("ge.event_type = 22")
            if event_conditions:
                query += f" AND ({' OR '.join(event_conditions)})"

        # Coordinate filters
        if origin_x_min is not None:
            query += " AND ge.thrower_x >= :origin_x_min"
            params["origin_x_min"] = origin_x_min
        if origin_x_max is not None:
            query += " AND ge.thrower_x <= :origin_x_max"
            params["origin_x_max"] = origin_x_max
        if origin_y_min is not None:
            query += " AND ge.thrower_y >= :origin_y_min"
            params["origin_y_min"] = origin_y_min
        if origin_y_max is not None:
            query += " AND ge.thrower_y <= :origin_y_max"
            params["origin_y_max"] = origin_y_max

        if dest_x_min is not None:
            query += " AND COALESCE(ge.receiver_x, ge.turnover_x) >= :dest_x_min"
            params["dest_x_min"] = dest_x_min
        if dest_x_max is not None:
            query += " AND COALESCE(ge.receiver_x, ge.turnover_x) <= :dest_x_max"
            params["dest_x_max"] = dest_x_max
        if dest_y_min is not None:
            query += " AND COALESCE(ge.receiver_y, ge.turnover_y) >= :dest_y_min"
            params["dest_y_min"] = dest_y_min
        if dest_y_max is not None:
            query += " AND COALESCE(ge.receiver_y, ge.turnover_y) <= :dest_y_max"
            params["dest_y_max"] = dest_y_max

        # Add limit if specified
        if limit is not None:
            query += " LIMIT :limit"
            params["limit"] = limit

        # Execute query
        rows = stats_system.db.execute_query(query, params)

        # Process results
        events = []
        stats = {
            "total_throws": 0,
            "completions": 0,
            "turnovers": 0,
            "goals": 0,
            "total_yards": 0,
            "completion_yards": 0,
            "by_type": {
                "huck": {"count": 0},
                "swing": {"count": 0},
                "dump": {"count": 0},
                "gainer": {"count": 0},
                "dish": {"count": 0},
            },
        }

        for row in rows:
            event_type = row["event_type"]

            # Determine result
            if event_type == 19:
                result = "goal"
            elif event_type == 18:
                result = "completion"
            else:
                result = "turnover"

            # Calculate distance
            dest_x = (
                row["receiver_x"]
                if row["receiver_x"] is not None
                else row["turnover_x"]
            )
            dest_y = (
                row["receiver_y"]
                if row["receiver_y"] is not None
                else row["turnover_y"]
            )

            vertical_yards = None
            horizontal_yards = None
            distance = None

            if dest_y is not None and row["thrower_y"] is not None:
                vertical_yards = dest_y - row["thrower_y"]
            if dest_x is not None and row["thrower_x"] is not None:
                horizontal_yards = abs(dest_x - row["thrower_x"])
            if vertical_yards is not None and horizontal_yards is not None:
                distance = math.sqrt(vertical_yards**2 + horizontal_yards**2)

            # Apply distance filter
            if distance_min is not None and (
                distance is None or distance < distance_min
            ):
                continue
            if distance_max is not None and (
                distance is None or distance > distance_max
            ):
                continue

            event = {
                "game_id": row["game_id"],
                "event_type": event_type,
                "pass_type": row["pass_type"],
                "thrower_id": row["thrower_id"],
                "thrower_name": row["thrower_name"],
                "receiver_id": row["receiver_id"],
                "receiver_name": row["receiver_name"],
                "thrower_x": row["thrower_x"],
                "thrower_y": row["thrower_y"],
                "receiver_x": row["receiver_x"],
                "receiver_y": row["receiver_y"],
                "turnover_x": row["turnover_x"],
                "turnover_y": row["turnover_y"],
                "result": result,
                "vertical_yards": (
                    round(vertical_yards, 1) if vertical_yards is not None else None
                ),
                "horizontal_yards": (
                    round(horizontal_yards, 1) if horizontal_yards is not None else None
                ),
                "distance": round(distance, 1) if distance is not None else None,
                "year": row["year"],
            }
            events.append(event)

            # Update stats
            stats["total_throws"] += 1
            if result == "goal":
                stats["goals"] += 1
                stats["completions"] += 1
                if vertical_yards is not None:
                    stats["total_yards"] += vertical_yards
                    stats["completion_yards"] += vertical_yards
            elif result == "completion":
                stats["completions"] += 1
                if vertical_yards is not None:
                    stats["total_yards"] += vertical_yards
                    stats["completion_yards"] += vertical_yards
            else:
                stats["turnovers"] += 1
                if vertical_yards is not None:
                    stats["total_yards"] += vertical_yards

            # Track by type
            pass_type = row["pass_type"]
            if pass_type and pass_type in stats["by_type"]:
                stats["by_type"][pass_type]["count"] += 1

        # Calculate percentages
        total = stats["total_throws"]
        if total > 0:
            stats["completions_pct"] = round(stats["completions"] / total * 100, 1)
            stats["turnovers_pct"] = round(stats["turnovers"] / total * 100, 1)
            stats["goals_pct"] = round(stats["goals"] / total * 100, 1)
            stats["avg_yards_per_throw"] = round(stats["total_yards"] / total, 1)

            for ptype in stats["by_type"]:
                stats["by_type"][ptype]["pct"] = round(
                    stats["by_type"][ptype]["count"] / total * 100, 1
                )
        else:
            stats["completions_pct"] = 0
            stats["turnovers_pct"] = 0
            stats["goals_pct"] = 0
            stats["avg_yards_per_throw"] = 0
            for ptype in stats["by_type"]:
                stats["by_type"][ptype]["pct"] = 0

        if stats["completions"] > 0:
            stats["avg_yards_per_completion"] = round(
                stats["completion_yards"] / stats["completions"], 1
            )
        else:
            stats["avg_yards_per_completion"] = 0

        return {
            "events": events,
            "stats": stats,
            "total": len(events),
        }

    @router.get("/api/pass-events/filters")
    async def get_pass_event_filters(
        season: int | None = Query(None, description="Filter options by season"),
        team_id: str | None = Query(None, description="Filter by team"),
        game_id: str | None = Query(None, description="Filter by game"),
    ):
        """
        Get available filter options for pass events.

        Returns seasons, teams, and players for dropdown filters.
        Supports cascading filters - team/game selection filters player list.
        """
        # Get available seasons
        seasons_query = """
        SELECT DISTINCT year FROM games ORDER BY year DESC
        """
        seasons_rows = stats_system.db.execute_query(seasons_query, {})
        seasons = [row["year"] for row in seasons_rows]

        # Get teams (optionally filtered by season or game)
        teams_params = {}
        if game_id:
            # When game is selected, only return the two teams in that game
            teams_query = """
            SELECT DISTINCT t.team_id, t.full_name, t.abbrev
            FROM teams t
            JOIN games g ON (t.team_id = g.home_team_id OR t.team_id = g.away_team_id) AND t.year = g.year
            WHERE g.game_id = :game_id
            ORDER BY t.full_name
            """
            teams_params["game_id"] = game_id
        else:
            teams_query = """
            SELECT DISTINCT t.team_id, t.full_name, t.abbrev
            FROM teams t
            """
            conditions = []
            if season:
                conditions.append("t.year = :season")
                teams_params["season"] = season
            if conditions:
                teams_query += " WHERE " + " AND ".join(conditions)
            teams_query += " ORDER BY t.full_name"

        teams_rows = stats_system.db.execute_query(teams_query, teams_params)
        # Deduplicate teams by team_id
        seen_teams = set()
        teams = []
        for row in teams_rows:
            if row["team_id"] not in seen_teams:
                seen_teams.add(row["team_id"])
                teams.append(
                    {
                        "team_id": row["team_id"],
                        "name": row["full_name"],
                        "abbrev": row["abbrev"],
                    }
                )

        # Get players with pass events - filtered by season, team, or game
        players_query = """
        SELECT DISTINCT p.player_id, p.full_name
        FROM players p
        JOIN game_events ge ON (p.player_id = ge.thrower_id OR p.player_id = ge.receiver_id)
        JOIN games g ON ge.game_id = g.game_id AND g.year = p.year
        WHERE ge.event_type IN (18, 19, 20, 22)
        """
        players_params = {}
        if season:
            players_query += " AND g.year = :season"
            players_params["season"] = season
        if game_id:
            players_query += " AND ge.game_id = :game_id"
            players_params["game_id"] = game_id
        if team_id:
            players_query += """ AND (
                (ge.team = 'home' AND g.home_team_id = :team_id) OR
                (ge.team = 'away' AND g.away_team_id = :team_id)
            )"""
            players_params["team_id"] = team_id
        players_query += " ORDER BY p.full_name LIMIT 500"

        players_rows = stats_system.db.execute_query(players_query, players_params)
        players = [
            {"player_id": row["player_id"], "name": row["full_name"]}
            for row in players_rows
        ]

        # Get games (optionally filtered by season and team)
        games_query = """
        SELECT g.game_id, g.year, g.week,
               ht.abbrev as home_abbrev, at.abbrev as away_abbrev,
               g.home_score, g.away_score, g.start_timestamp
        FROM games g
        LEFT JOIN teams ht ON g.home_team_id = ht.team_id AND g.year = ht.year
        LEFT JOIN teams at ON g.away_team_id = at.team_id AND g.year = at.year
        WHERE 1=1
        """
        games_params = {}
        if season:
            games_query += " AND g.year = :season"
            games_params["season"] = season
        if team_id:
            games_query += (
                " AND (g.home_team_id = :team_id OR g.away_team_id = :team_id)"
            )
            games_params["team_id"] = team_id
        games_query += " ORDER BY g.start_timestamp DESC LIMIT 500"

        games_rows = stats_system.db.execute_query(games_query, games_params)
        games = [
            {
                "game_id": row["game_id"],
                "label": f"{row['away_abbrev']} @ {row['home_abbrev']} ({row['away_score']}-{row['home_score']})",
                "year": row["year"],
                "week": row["week"],
            }
            for row in games_rows
        ]

        return {
            "seasons": seasons,
            "teams": teams,
            "players": players,
            "games": games,
        }

    return router
