"""
Season statistics calculator.
"""


class SeasonStatsCalculator:
    """Calculates and stores aggregated season statistics."""

    def __init__(self, db):
        """
        Initialize the season stats calculator.

        Args:
            db: Database instance
        """
        self.db = db

    def calculate_season_stats(self, season):
        """
        Calculate and store aggregated season statistics for all players and teams.

        Args:
            season: Season identifier (year or season string like "2023-24")
        """
        # Handle both year (int) and season string formats
        year_param = (
            season if isinstance(season, int) else int(str(season).split("-")[0])
        )

        # Calculate player and team stats
        self._calculate_player_season_stats(year_param)
        self._calculate_team_season_stats(year_param)

    def _calculate_player_season_stats(self, year_param: int):
        """
        Calculate player season statistics.

        Args:
            year_param: Year parameter
        """
        try:
            # Calculate player season stats - use UFA statistics
            # Include pass type counts from game_events
            player_stats_query = """
            SELECT
                pgs.player_id,
                pgs.team_id,
                COUNT(DISTINCT pgs.game_id) as games_played,
                SUM(pgs.seconds_played) as total_seconds_played,
                SUM(pgs.goals) as total_goals,
                SUM(pgs.assists) as total_assists,
                SUM(pgs.hockey_assists) as total_hockey_assists,
                SUM(pgs.completions) as total_completions,
                SUM(pgs.throw_attempts) as total_throw_attempts,
                SUM(pgs.throwaways) as total_throwaways,
                SUM(pgs.blocks) as total_blocks,
                SUM(pgs.callahans) as total_callahans,
                SUM(pgs.drops) as total_drops,
                SUM(pgs.stalls) as total_stalls,
                CASE
                    WHEN SUM(pgs.throw_attempts) > 0
                    THEN CAST(SUM(pgs.completions) AS FLOAT) / SUM(pgs.throw_attempts) * 100
                    ELSE 0
                END as completion_percentage,
                COALESCE(pt.total_dish, 0) as total_dish,
                COALESCE(pt.total_swing, 0) as total_swing,
                COALESCE(pt.total_dump, 0) as total_dump,
                COALESCE(pt.total_huck, 0) as total_huck,
                COALESCE(pt.total_gainer, 0) as total_gainer
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.id
            LEFT JOIN (
                SELECT
                    ge.thrower_id as player_id,
                    SUM(CASE WHEN ge.pass_type = 'dish' THEN 1 ELSE 0 END) as total_dish,
                    SUM(CASE WHEN ge.pass_type = 'swing' THEN 1 ELSE 0 END) as total_swing,
                    SUM(CASE WHEN ge.pass_type = 'dump' THEN 1 ELSE 0 END) as total_dump,
                    SUM(CASE WHEN ge.pass_type = 'huck' THEN 1 ELSE 0 END) as total_huck,
                    SUM(CASE WHEN ge.pass_type = 'gainer' THEN 1 ELSE 0 END) as total_gainer
                FROM game_events ge
                JOIN games g2 ON ge.game_id = g2.game_id
                WHERE g2.year = :year
                AND ge.event_type IN (18, 19)
                AND ge.pass_type IS NOT NULL
                GROUP BY ge.thrower_id
            ) pt ON pgs.player_id = pt.player_id
            WHERE g.year = :year
            GROUP BY pgs.player_id, pgs.team_id, pt.total_dish, pt.total_swing, pt.total_dump, pt.total_huck, pt.total_gainer
            """

            player_results = self.db.execute_query(
                player_stats_query, {"year": year_param}
            )

            # Clear existing season stats first
            self.db.execute_query(
                "DELETE FROM player_season_stats WHERE year = :year",
                {"year": year_param},
            )

            for row in player_results:
                try:
                    # Add year to the row data
                    row["year"] = year_param

                    # Insert new record
                    self.db.insert_data("player_season_stats", row)
                except Exception as e:
                    print(
                        f"Error calculating season stats for player {row.get('player_id')}: {e}"
                    )
                    continue
        except Exception as e:
            print(f"Error in calculate_player_season_stats: {e}")

    def _calculate_team_season_stats(self, year_param: int):
        """
        Calculate team season statistics.

        Args:
            year_param: Year parameter
        """
        try:
            # Include pass type counts from game_events via player_game_stats
            team_stats_query = """
            SELECT
                t.id as team_id,
                COUNT(DISTINCT g.id) as games_played,
                SUM(CASE
                    WHEN (g.home_team_id = t.id AND g.home_score > g.away_score)
                      OR (g.away_team_id = t.id AND g.away_score > g.home_score)
                    THEN 1 ELSE 0
                END) as wins,
                SUM(CASE
                    WHEN (g.home_team_id = t.id AND g.home_score < g.away_score)
                      OR (g.away_team_id = t.id AND g.away_score < g.home_score)
                    THEN 1 ELSE 0
                END) as losses,
                SUM(CASE
                    WHEN g.home_team_id = t.id THEN g.home_score
                    WHEN g.away_team_id = t.id THEN g.away_score
                    ELSE 0
                END) as points_for,
                SUM(CASE
                    WHEN g.home_team_id = t.id THEN g.away_score
                    WHEN g.away_team_id = t.id THEN g.home_score
                    ELSE 0
                END) as points_against,
                COALESCE(pt.team_dish, 0) as team_dish,
                COALESCE(pt.team_swing, 0) as team_swing,
                COALESCE(pt.team_dump, 0) as team_dump,
                COALESCE(pt.team_huck, 0) as team_huck,
                COALESCE(pt.team_gainer, 0) as team_gainer
            FROM teams t
            LEFT JOIN games g ON (g.home_team_id = t.id OR g.away_team_id = t.id)
                              AND g.year = :year
            LEFT JOIN (
                SELECT
                    pgs.team_id,
                    SUM(CASE WHEN ge.pass_type = 'dish' THEN 1 ELSE 0 END) as team_dish,
                    SUM(CASE WHEN ge.pass_type = 'swing' THEN 1 ELSE 0 END) as team_swing,
                    SUM(CASE WHEN ge.pass_type = 'dump' THEN 1 ELSE 0 END) as team_dump,
                    SUM(CASE WHEN ge.pass_type = 'huck' THEN 1 ELSE 0 END) as team_huck,
                    SUM(CASE WHEN ge.pass_type = 'gainer' THEN 1 ELSE 0 END) as team_gainer
                FROM game_events ge
                JOIN player_game_stats pgs ON ge.thrower_id = pgs.player_id
                    AND ge.game_id = pgs.game_id
                WHERE pgs.year = :year
                AND ge.event_type IN (18, 19)
                AND ge.pass_type IS NOT NULL
                GROUP BY pgs.team_id
            ) pt ON t.id = pt.team_id
            GROUP BY t.id, pt.team_dish, pt.team_swing, pt.team_dump, pt.team_huck, pt.team_gainer
            """

            team_results = self.db.execute_query(team_stats_query, {"year": year_param})

            # Clear existing team season stats first
            self.db.execute_query(
                "DELETE FROM team_season_stats WHERE year = :year",
                {"year": year_param},
            )

            for row in team_results:
                try:
                    # Calculate derived stats
                    if row.get("games_played") and row["games_played"] > 0:
                        row["avg_points_for"] = row["points_for"] / row["games_played"]
                        row["avg_points_against"] = (
                            row["points_against"] / row["games_played"]
                        )
                        row["win_percentage"] = row["wins"] / row["games_played"]
                    else:
                        row["avg_points_for"] = 0
                        row["avg_points_against"] = 0
                        row["win_percentage"] = 0

                    # Add year to the row data
                    row["year"] = year_param

                    # Insert new record
                    self.db.insert_data("team_season_stats", row)
                except Exception as e:
                    print(
                        f"Error calculating team season stats for team {row.get('team_id')}: {e}"
                    )
                    continue
        except Exception as e:
            print(f"Error in team season stats calculation: {e}")
