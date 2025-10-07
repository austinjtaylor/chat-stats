from datetime import datetime
from typing import Any

from pydantic import BaseModel


class Team(BaseModel):
    """Model for a sports team matching UFA API structure"""

    id: int | None = None  # Internal database ID
    team_id: str  # UFA teamID (primary identifier)
    year: int  # Four digit year
    city: str  # Team's current city
    name: str  # Team's name
    full_name: str  # Team's full name
    abbrev: str  # Team's abbreviation
    wins: int = 0  # Number of wins
    losses: int = 0  # Number of losses
    ties: int = 0  # Number of ties
    standing: int  # Team's current standing
    division_id: str | None = None  # Division ID
    division_name: str | None = None  # Division name


class Player(BaseModel):
    """Model for a player matching UFA API structure"""

    id: int | None = None  # Internal database ID
    player_id: str  # UFA playerID (primary identifier)
    first_name: str  # Player's first name
    last_name: str  # Player's last name
    full_name: str  # Player's full name
    team_id: str | None = None  # UFA teamID
    active: bool = True  # Whether player is active
    year: int | None = None  # Year for team association
    jersey_number: int | None = None  # Player's jersey number


class Game(BaseModel):
    """Model for a game matching UFA API structure"""

    id: int | None = None  # Internal database ID
    game_id: str  # UFA gameID (primary identifier)
    away_team_id: str  # UFA awayTeamID
    home_team_id: str  # UFA homeTeamID
    away_score: int | None = None  # Away team score
    home_score: int | None = None  # Home team score
    status: str  # Game status (Upcoming, Live, Final)
    start_timestamp: datetime | None = None  # Game start timestamp
    start_timezone: str | None = None  # Start timezone
    streaming_url: str | None = None  # Streaming URL
    update_timestamp: datetime | None = None  # Last update timestamp
    week: str | None = None  # Week identifier
    location: str | None = None  # Game location
    year: int  # Four digit year


class PlayerGameStats(BaseModel):
    """Model for Ultimate Frisbee player statistics in a single game matching UFA API"""

    id: int | None = None  # Internal database ID
    player_id: str  # UFA playerID
    game_id: str  # UFA gameID
    team_id: str  # UFA teamID
    year: int  # Four digit year
    # Core Ultimate Frisbee stats
    assists: int = 0
    goals: int = 0
    hockey_assists: int = 0
    completions: int = 0
    throw_attempts: int = 0
    throwaways: int = 0
    stalls: int = 0
    callahans_thrown: int = 0
    yards_received: int = 0
    yards_thrown: int = 0
    hucks_attempted: int = 0
    hucks_completed: int = 0
    hucks_received: int = 0
    catches: int = 0
    drops: int = 0
    blocks: int = 0
    callahans: int = 0
    pulls: int = 0
    ob_pulls: int = 0
    recorded_pulls: int = 0
    recorded_pulls_hangtime: int | None = None
    o_points_played: int = 0
    o_points_scored: int = 0
    d_points_played: int = 0
    d_points_scored: int = 0
    seconds_played: int = 0
    o_opportunities: int = 0
    o_opportunity_scores: int = 0
    d_opportunities: int = 0
    d_opportunity_stops: int = 0

    @property
    def calculated_plus_minus(self) -> int:
        """Calculate UFA plus/minus: goals + assists + blocks - throwaways - stalls - drops"""
        return (
            self.goals
            + self.assists
            + self.blocks
            - self.throwaways
            - self.stalls
            - self.drops
        )

    @property
    def yards_per_turn(self) -> float | None:
        """Calculate yards per turn: (yards_thrown + yards_received) / (throwaways + stalls + drops)"""
        total_turnovers = self.throwaways + self.stalls + self.drops
        if total_turnovers > 0:
            total_yards = self.yards_thrown + self.yards_received
            return round(total_yards / total_turnovers, 1)
        return None


class PlayerSeasonStats(BaseModel):
    """Model for aggregated Ultimate Frisbee player season statistics matching UFA API"""

    id: int | None = None  # Internal database ID
    player_id: str  # UFA playerID
    team_id: str  # UFA teamID
    year: int  # Four digit year
    # Aggregated Ultimate Frisbee stats
    total_assists: int = 0
    total_goals: int = 0
    total_hockey_assists: int = 0
    total_completions: int = 0
    total_throw_attempts: int = 0
    total_throwaways: int = 0
    total_stalls: int = 0
    total_callahans_thrown: int = 0
    total_yards_received: int = 0
    total_yards_thrown: int = 0
    total_hucks_attempted: int = 0
    total_hucks_completed: int = 0
    total_hucks_received: int = 0
    total_catches: int = 0
    total_drops: int = 0
    total_blocks: int = 0
    total_callahans: int = 0
    total_pulls: int = 0
    total_ob_pulls: int = 0
    total_recorded_pulls: int = 0
    total_recorded_pulls_hangtime: int | None = None
    total_o_points_played: int = 0
    total_o_points_scored: int = 0
    total_d_points_played: int = 0
    total_d_points_scored: int = 0
    total_seconds_played: int = 0
    total_o_opportunities: int = 0
    total_o_opportunity_scores: int = 0
    total_d_opportunities: int = 0
    total_d_opportunity_stops: int = 0
    # Calculated fields
    calculated_plus_minus: int | None = None
    completion_percentage: float | None = None

    @property
    def plus_minus(self) -> int:
        """Calculate UFA plus/minus: goals + assists + blocks - throwaways - stalls - drops"""
        return (
            self.total_goals
            + self.total_assists
            + self.total_blocks
            - self.total_throwaways
            - self.total_stalls
            - self.total_drops
        )

    @property
    def yards_per_turn(self) -> float | None:
        """Calculate yards per turn: (total_yards_thrown + total_yards_received) / (total_throwaways + total_stalls + total_drops)"""
        total_turnovers = self.total_throwaways + self.total_stalls + self.total_drops
        if total_turnovers > 0:
            total_yards = self.total_yards_thrown + self.total_yards_received
            return round(total_yards / total_turnovers, 1)
        return None


class TeamSeasonStats(BaseModel):
    """Model for team season statistics matching UFA API"""

    id: int | None = None  # Internal database ID
    team_id: str  # UFA teamID
    year: int  # Four digit year
    wins: int = 0  # Number of wins
    losses: int = 0  # Number of losses
    ties: int = 0  # Number of ties
    standing: int | None = None  # Team's standing
    division_id: str | None = None  # Division ID
    division_name: str | None = None  # Division name
    points_for: int = 0  # Points scored
    points_against: int = 0  # Points allowed

    # Basic game stats
    games_played: int = 0
    scores: int = 0
    scores_against: int = 0

    # Completion/turnover stats
    completions: int = 0
    throw_attempts: int = 0
    turnovers: int = 0
    completion_percentage: float | None = None

    # Huck stats
    hucks_completed: int = 0
    hucks_attempted: int = 0
    huck_percentage: float | None = None

    # Defensive stats
    blocks: int = 0

    # Possession-based stats
    hold_percentage: float | None = None
    o_line_conversion: float | None = None
    break_percentage: float | None = None
    d_line_conversion: float | None = None
    red_zone_conversion: float | None = None

    # Opponent stats (for opponent perspective view)
    opp_completions: int = 0
    opp_throw_attempts: int = 0
    opp_turnovers: int = 0
    opp_completion_percentage: float | None = None
    opp_hucks_completed: int = 0
    opp_hucks_attempted: int = 0
    opp_huck_percentage: float | None = None
    opp_blocks: int = 0
    opp_hold_percentage: float | None = None
    opp_o_line_conversion: float | None = None
    opp_break_percentage: float | None = None
    opp_d_line_conversion: float | None = None
    opp_red_zone_conversion: float | None = None


class StatsQuery(BaseModel):
    """Model for a statistics query request"""

    query_type: str  # 'player', 'team', 'game', 'comparison'
    filters: dict[str, Any] = {}
    aggregations: list[str] = []
    sort_by: str | None = None
    limit: int = 10
