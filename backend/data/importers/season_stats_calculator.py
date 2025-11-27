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
                END as completion_percentage
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.id
            WHERE g.year = :year
            GROUP BY pgs.player_id, pgs.team_id
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
                END) as points_against
            FROM teams t
            LEFT JOIN games g ON (g.home_team_id = t.id OR g.away_team_id = t.id)
                              AND g.year = :year
            GROUP BY t.id
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
