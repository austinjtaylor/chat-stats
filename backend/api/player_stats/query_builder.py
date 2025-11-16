"""
SQL query construction for player statistics endpoint.
"""

from .filters import get_team_career_sort_column, build_having_clause, SEASON_STATS_ALIAS_MAPPING
from utils.query import get_sort_column


class PlayerStatsQueryBuilder:
    """Builds complex SQL queries for player statistics retrieval."""

    def __init__(
        self,
        seasons: list,
        teams: list,
        is_career_mode: bool,
        filters_list: list,
        per_game_mode: bool,
        sort: str,
        order: str,
        page: int,
        per_page: int
    ):
        self.seasons = seasons
        self.teams = teams
        self.is_career_mode = is_career_mode
        self.filters_list = filters_list
        self.per_game_mode = per_game_mode
        self.sort = sort
        self.order = order
        self.page = page
        self.per_page = per_page

        # Build filters
        self.season_filter = self._build_season_filter()
        self.team_filter = self._build_team_filter()

    def _build_season_filter(self) -> str:
        """Build SQL WHERE clause for season filtering."""
        if self.is_career_mode:
            return ""
        elif len(self.seasons) == 1:
            return f" AND pss.year = {self.seasons[0]}"
        else:
            season_years_str = ",".join(self.seasons)
            return f" AND pss.year IN ({season_years_str})"

    def _build_team_filter(self) -> str:
        """Build SQL WHERE clause for team filtering."""
        if self.teams[0] == "all":
            return ""
        elif len(self.teams) == 1:
            return f" AND pss.team_id = '{self.teams[0]}'"
        else:
            team_ids_str = ",".join([f"'{t}'" for t in self.teams])
            return f" AND pss.team_id IN ({team_ids_str})"

    def build_main_query(self) -> str:
        """Build the main SELECT query for player stats."""
        if self.is_career_mode and self.teams[0] != "all":
            return self._build_team_career_query()
        elif self.is_career_mode:
            return self._build_full_career_query()
        else:
            return self._build_season_query()

    def build_count_query(self) -> str:
        """Build the COUNT query for pagination."""
        if self.filters_list:
            # With custom filters, use subquery approach
            return self._build_filtered_count_query()
        else:
            # Without filters, use optimized count
            return self._build_optimized_count_query()

    def _build_team_career_query(self) -> str:
        """Build query for career stats filtered by specific team(s)."""
        team_filter_for_query = self.team_filter.replace(" AND ", "")  # Remove leading " AND "

        having_clause = build_having_clause(
            self.filters_list,
            per_game=self.per_game_mode,
            table_prefix="tcs."
        )

        return f"""
        WITH team_career_stats AS (
            SELECT
                pss.player_id,
                pss.team_id,
                MAX(pss.year) as most_recent_year,
                SUM(pss.total_goals) as total_goals,
                SUM(pss.total_assists) as total_assists,
                SUM(pss.total_hockey_assists) as total_hockey_assists,
                SUM(pss.total_blocks) as total_blocks,
                (SUM(pss.total_goals) + SUM(pss.total_assists) + SUM(pss.total_blocks) -
                 SUM(pss.total_throwaways) - SUM(pss.total_drops)) as calculated_plus_minus,
                SUM(pss.total_completions) as total_completions,
                CASE
                    WHEN SUM(pss.total_throw_attempts) > 0
                    THEN ROUND(SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts), 1)
                    ELSE 0
                END as completion_percentage,
                SUM(pss.total_yards_thrown) as total_yards_thrown,
                SUM(pss.total_yards_received) as total_yards_received,
                SUM(pss.total_throwaways) as total_throwaways,
                SUM(pss.total_stalls) as total_stalls,
                SUM(pss.total_drops) as total_drops,
                SUM(pss.total_callahans) as total_callahans,
                SUM(pss.total_hucks_completed) as total_hucks_completed,
                SUM(pss.total_hucks_attempted) as total_hucks_attempted,
                SUM(pss.total_hucks_received) as total_hucks_received,
                SUM(pss.total_pulls) as total_pulls,
                SUM(pss.total_o_points_played) as total_o_points_played,
                SUM(pss.total_d_points_played) as total_d_points_played,
                SUM(pss.total_seconds_played) as total_seconds_played,
                SUM(pss.total_o_opportunities) as total_o_opportunities,
                SUM(pss.total_d_opportunities) as total_d_opportunities,
                SUM(pss.total_o_opportunity_scores) as total_o_opportunity_scores,
                SUM(pss.total_o_opportunities) as possessions,
                (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
                (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
                (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
                ROUND(SUM(pss.total_seconds_played) / 60.0, 0) as minutes_played,
                CASE WHEN SUM(pss.total_hucks_attempted) > 0 THEN ROUND(SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted), 1) ELSE 0 END as huck_percentage,
                CASE
                    WHEN SUM(pss.total_o_opportunities) >= 20
                    THEN ROUND(SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities), 1)
                    ELSE NULL
                END as offensive_efficiency,
                CASE
                    WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                    THEN ROUND((SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 1)
                    WHEN (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) > 0
                    THEN (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0
                    ELSE NULL
                END as yards_per_turn,
                CASE
                    WHEN SUM(pss.total_completions) > 0
                    THEN ROUND(SUM(pss.total_yards_thrown) * 1.0 / SUM(pss.total_completions), 1)
                    ELSE NULL
                END as yards_per_completion,
                CASE
                    WHEN SUM(pss.total_catches) > 0
                    THEN ROUND(SUM(pss.total_yards_received) * 1.0 / SUM(pss.total_catches), 1)
                    ELSE NULL
                END as yards_per_reception,
                CASE
                    WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0
                    THEN ROUND(SUM(pss.total_assists) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 2)
                    ELSE NULL
                END as assists_per_turnover
            FROM player_season_stats pss
            WHERE {team_filter_for_query}
            GROUP BY pss.player_id, pss.team_id
        ),
        player_info AS (
            SELECT DISTINCT ON (pss.player_id)
                pss.player_id,
                p.full_name,
                p.first_name,
                p.last_name
            FROM player_season_stats pss
            JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
            WHERE {team_filter_for_query}
            ORDER BY pss.player_id, pss.year DESC
        ),
        games_count AS (
            SELECT
                pgs.player_id,
                COUNT(DISTINCT pgs.game_id) as games_played
            FROM player_game_stats pgs
            WHERE {team_filter_for_query.replace('pss.', 'pgs.')}
              AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
            GROUP BY pgs.player_id
        ),
        team_info AS (
            SELECT DISTINCT ON (t.team_id)
                t.team_id,
                t.name,
                t.full_name
            FROM teams t
            WHERE {team_filter_for_query.replace('pss.', 't.')}
            ORDER BY t.team_id, t.year DESC
        )
        SELECT
            pi.full_name,
            pi.first_name,
            pi.last_name,
            tcs.team_id,
            NULL as year,
            tcs.total_goals,
            tcs.total_assists,
            tcs.total_hockey_assists,
            tcs.total_blocks,
            tcs.calculated_plus_minus,
            tcs.total_completions,
            tcs.completion_percentage,
            tcs.total_yards_thrown,
            tcs.total_yards_received,
            tcs.total_throwaways,
            tcs.total_stalls,
            tcs.total_drops,
            tcs.total_callahans,
            tcs.total_hucks_completed,
            tcs.total_hucks_attempted,
            tcs.total_hucks_received,
            tcs.total_pulls,
            tcs.total_o_points_played,
            tcs.total_d_points_played,
            tcs.total_seconds_played,
            tcs.total_o_opportunities,
            tcs.total_d_opportunities,
            tcs.total_o_opportunity_scores,
            ti.name as team_name,
            ti.full_name as team_full_name,
            COALESCE(gc.games_played, 0) as games_played,
            tcs.possessions,
            tcs.score_total,
            tcs.total_points_played,
            tcs.total_yards,
            tcs.minutes_played,
            tcs.huck_percentage,
            tcs.offensive_efficiency,
            tcs.yards_per_turn,
            tcs.yards_per_completion,
            tcs.yards_per_reception,
            tcs.assists_per_turnover
        FROM team_career_stats tcs
        JOIN player_info pi ON tcs.player_id = pi.player_id
        LEFT JOIN games_count gc ON tcs.player_id = gc.player_id
        CROSS JOIN team_info ti
        WHERE gc.games_played > 0
        {" AND " + having_clause if having_clause else ""}
        ORDER BY {get_team_career_sort_column(self.sort, per_game=self.per_game_mode)} {self.order.upper()} NULLS LAST
        LIMIT {self.per_page} OFFSET {(self.page-1) * self.per_page}
        """

    def _build_full_career_query(self) -> str:
        """Build query for full career stats (no team filter)."""
        having_clause = build_having_clause(
            self.filters_list,
            per_game=self.per_game_mode,
            table_prefix=""
        )

        return f"""
        SELECT
            full_name,
            first_name,
            last_name,
            most_recent_team_id as team_id,
            NULL as year,
            total_goals,
            total_assists,
            total_hockey_assists,
            total_blocks,
            calculated_plus_minus,
            total_completions,
            completion_percentage,
            total_yards_thrown,
            total_yards_received,
            total_throwaways,
            total_stalls,
            total_drops,
            total_callahans,
            total_hucks_completed,
            total_hucks_attempted,
            total_hucks_received,
            total_pulls,
            total_o_points_played,
            total_d_points_played,
            total_seconds_played,
            total_o_opportunities,
            total_d_opportunities,
            total_o_opportunity_scores,
            most_recent_team_name as team_name,
            most_recent_team_full_name as team_full_name,
            games_played,
            possessions,
            score_total,
            total_points_played,
            total_yards,
            minutes_played,
            huck_percentage,
            offensive_efficiency,
            yards_per_turn,
            yards_per_completion,
            yards_per_reception,
            assists_per_turnover
        FROM player_career_stats
        WHERE games_played > 0
        {" AND " + having_clause if having_clause else ""}
        ORDER BY {get_sort_column(self.sort, is_career=True, per_game=self.per_game_mode, team=self.teams[0])} {self.order.upper()} NULLS LAST
        LIMIT {self.per_page} OFFSET {(self.page-1) * self.per_page}
        """

    def _build_season_query(self) -> str:
        """Build query for season-specific stats."""
        having_clause = build_having_clause(
            self.filters_list,
            per_game=self.per_game_mode,
            table_prefix="",
            alias_mapping=SEASON_STATS_ALIAS_MAPPING
        )

        return f"""
        SELECT
            p.full_name,
            p.first_name,
            p.last_name,
            p.team_id,
            pss.year,
            pss.total_goals,
            pss.total_assists,
            pss.total_hockey_assists,
            pss.total_blocks,
            pss.calculated_plus_minus,
            pss.total_completions,
            pss.completion_percentage,
            pss.total_yards_thrown,
            pss.total_yards_received,
            pss.total_throwaways,
            pss.total_stalls,
            pss.total_drops,
            pss.total_callahans,
            pss.total_hucks_completed,
            pss.total_hucks_attempted,
            pss.total_hucks_received,
            pss.total_pulls,
            pss.total_o_points_played,
            pss.total_d_points_played,
            pss.total_seconds_played,
            pss.total_o_opportunities,
            pss.total_d_opportunities,
            pss.total_o_opportunity_scores,
            t.name as team_name,
            t.full_name as team_full_name,
            COUNT(DISTINCT CASE
                WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                THEN pgs.game_id
                ELSE NULL
            END) as games_played,
            pss.total_o_opportunities as possessions,
            (pss.total_goals + pss.total_assists) as score_total,
            (pss.total_o_points_played + pss.total_d_points_played) as total_points_played,
            (pss.total_yards_thrown + pss.total_yards_received) as total_yards,
            ROUND(pss.total_seconds_played / 60.0, 0) as minutes_played,
            CASE WHEN pss.total_hucks_attempted > 0 THEN ROUND(pss.total_hucks_completed * 100.0 / pss.total_hucks_attempted, 1) ELSE 0 END as huck_percentage,
            CASE
                WHEN pss.total_o_opportunities >= 20
                THEN ROUND(pss.total_o_opportunity_scores * 100.0 / pss.total_o_opportunities, 1)
                ELSE NULL
            END as offensive_efficiency,
            CASE
                WHEN (pss.total_throwaways + pss.total_stalls + pss.total_drops) > 0
                THEN ROUND((pss.total_yards_thrown + pss.total_yards_received) * 1.0 / (pss.total_throwaways + pss.total_stalls + pss.total_drops), 1)
                WHEN (pss.total_yards_thrown + pss.total_yards_received) > 0
                THEN (pss.total_yards_thrown + pss.total_yards_received) * 1.0
                ELSE NULL
            END as yards_per_turn,
            CASE
                WHEN pss.total_completions > 0
                THEN ROUND(pss.total_yards_thrown * 1.0 / pss.total_completions, 1)
                ELSE NULL
            END as yards_per_completion,
            CASE
                WHEN pss.total_catches > 0
                THEN ROUND(pss.total_yards_received * 1.0 / pss.total_catches, 1)
                ELSE NULL
            END as yards_per_reception,
            CASE
                WHEN (pss.total_throwaways + pss.total_stalls + pss.total_drops) > 0
                THEN ROUND(pss.total_assists * 1.0 / (pss.total_throwaways + pss.total_stalls + pss.total_drops), 2)
                ELSE NULL
            END as assists_per_turnover
        FROM player_season_stats pss
        JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
        LEFT JOIN teams t ON pss.team_id = t.team_id AND pss.year = t.year
        LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
        LEFT JOIN games g ON pgs.game_id = g.game_id AND g.year = pss.year
        WHERE 1=1{self.season_filter}{self.team_filter}
        GROUP BY pss.player_id, pss.team_id, pss.year, p.full_name, p.first_name, p.last_name, p.team_id,
                 pss.total_goals, pss.total_assists, pss.total_hockey_assists, pss.total_blocks, pss.calculated_plus_minus,
                 pss.total_completions, pss.completion_percentage, pss.total_yards_thrown, pss.total_yards_received,
                 pss.total_catches, pss.total_throwaways, pss.total_stalls, pss.total_drops, pss.total_callahans,
                 pss.total_hucks_completed, pss.total_hucks_attempted, pss.total_hucks_received, pss.total_pulls,
                 pss.total_o_points_played, pss.total_d_points_played, pss.total_seconds_played,
                 pss.total_o_opportunities, pss.total_d_opportunities, pss.total_o_opportunity_scores,
                 t.name, t.full_name
        HAVING COUNT(DISTINCT CASE
            WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
            THEN pgs.game_id
            ELSE NULL
        END) > 0
        {" AND " + having_clause if having_clause else ""}
        ORDER BY {get_sort_column(self.sort, per_game=self.per_game_mode)} {self.order.upper()} NULLS LAST
        LIMIT {self.per_page} OFFSET {(self.page-1) * self.per_page}
        """

    def _build_filtered_count_query(self) -> str:
        """Build count query when custom filters are present."""
        if self.is_career_mode and self.teams[0] != "all":
            return self._build_team_career_count_query()
        else:
            # Use subquery approach for other cases
            main_query = self.build_main_query()
            return f"""
            SELECT COUNT(*) FROM (
                {main_query.replace(f'LIMIT {self.per_page} OFFSET {(self.page-1) * self.per_page}', '')}
            ) AS filtered_results
            """

    def _build_team_career_count_query(self) -> str:
        """Build optimized count query for team career stats with filters."""
        team_filter_for_count = self.team_filter.replace(" AND ", "")
        having_clause = build_having_clause(
            self.filters_list,
            per_game=self.per_game_mode,
            table_prefix="tcs."
        )

        return f"""
        WITH team_career_stats AS (
            SELECT
                pss.player_id,
                SUM(pss.total_goals) as total_goals,
                SUM(pss.total_assists) as total_assists,
                SUM(pss.total_completions) as total_completions,
                SUM(pss.total_throwaways) as total_throwaways,
                SUM(pss.total_stalls) as total_stalls,
                SUM(pss.total_drops) as total_drops,
                (SUM(pss.total_goals) + SUM(pss.total_assists) + SUM(pss.total_blocks) -
                 SUM(pss.total_throwaways) - SUM(pss.total_drops)) as calculated_plus_minus,
                SUM(pss.total_o_opportunities) as possessions,
                (SUM(pss.total_goals) + SUM(pss.total_assists)) as score_total,
                (SUM(pss.total_o_points_played) + SUM(pss.total_d_points_played)) as total_points_played,
                (SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) as total_yards,
                SUM(pss.total_blocks) as total_blocks,
                CASE WHEN SUM(pss.total_throw_attempts) > 0 THEN ROUND(SUM(pss.total_completions) * 100.0 / SUM(pss.total_throw_attempts), 1) ELSE 0 END as completion_percentage,
                CASE WHEN SUM(pss.total_hucks_attempted) > 0 THEN ROUND(SUM(pss.total_hucks_completed) * 100.0 / SUM(pss.total_hucks_attempted), 1) ELSE 0 END as huck_percentage,
                CASE WHEN SUM(pss.total_o_opportunities) >= 20 THEN ROUND(SUM(pss.total_o_opportunity_scores) * 100.0 / SUM(pss.total_o_opportunities), 1) ELSE NULL END as offensive_efficiency,
                CASE WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0 THEN ROUND((SUM(pss.total_yards_thrown) + SUM(pss.total_yards_received)) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 1) ELSE NULL END as yards_per_turn,
                CASE WHEN SUM(pss.total_completions) > 0 THEN ROUND(SUM(pss.total_yards_thrown) * 1.0 / SUM(pss.total_completions), 1) ELSE NULL END as yards_per_completion,
                CASE WHEN SUM(pss.total_catches) > 0 THEN ROUND(SUM(pss.total_yards_received) * 1.0 / SUM(pss.total_catches), 1) ELSE NULL END as yards_per_reception,
                CASE WHEN (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)) > 0 THEN ROUND(SUM(pss.total_assists) * 1.0 / (SUM(pss.total_throwaways) + SUM(pss.total_stalls) + SUM(pss.total_drops)), 2) ELSE NULL END as assists_per_turnover,
                ROUND(SUM(pss.total_seconds_played) / 60.0, 0) as minutes_played,
                SUM(pss.total_o_points_played) as total_o_points_played,
                SUM(pss.total_d_points_played) as total_d_points_played,
                SUM(pss.total_hockey_assists) as total_hockey_assists
            FROM player_season_stats pss
            WHERE {team_filter_for_count}
            GROUP BY pss.player_id
        ),
        games_count AS (
            SELECT
                pgs.player_id,
                COUNT(DISTINCT pgs.game_id) as games_played
            FROM player_game_stats pgs
            WHERE {team_filter_for_count.replace('pss.', 'pgs.')}
              AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
            GROUP BY pgs.player_id
        )
        SELECT COUNT(*) as total
        FROM team_career_stats tcs
        LEFT JOIN games_count gc ON tcs.player_id = gc.player_id
        WHERE gc.games_played > 0
        {" AND " + having_clause if having_clause else ""}
        """

    def _build_optimized_count_query(self) -> str:
        """Build optimized count query when no custom filters are present."""
        if self.is_career_mode and self.teams[0] != "all":
            team_filter_for_count = self.team_filter.replace(" AND ", "")
            return f"""
            SELECT COUNT(DISTINCT pss.player_id) as total
            FROM player_season_stats pss
            WHERE {team_filter_for_count}
            AND EXISTS (
                SELECT 1 FROM player_game_stats pgs
                WHERE pgs.player_id = pss.player_id
                AND pgs.team_id = pss.team_id
                AND (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
            )
            """
        elif self.is_career_mode:
            return f"""
            SELECT COUNT(*) as total
            FROM player_career_stats
            WHERE games_played > 0
            """
        else:
            return f"""
            SELECT COUNT(*) as total
            FROM (
                SELECT pss.player_id, pss.team_id, pss.year
                FROM player_season_stats pss
                LEFT JOIN player_game_stats pgs ON pss.player_id = pgs.player_id AND pss.year = pgs.year AND pss.team_id = pgs.team_id
                WHERE 1=1{self.season_filter}{self.team_filter}
                GROUP BY pss.player_id, pss.team_id, pss.year
                HAVING COUNT(DISTINCT CASE
                    WHEN (pgs.o_points_played > 0 OR pgs.d_points_played > 0 OR pgs.seconds_played > 0 OR pgs.goals > 0 OR pgs.assists > 0)
                    THEN pgs.game_id
                    ELSE NULL
                END) > 0
            ) as filtered_players
            """
