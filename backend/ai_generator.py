from typing import Any

import anthropic
from config import config


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in Ultimate Frisbee Association (UFA) statistics with direct SQL access to query the sports database.

**ABSOLUTE REQUIREMENT - YOU MUST USE TOOLS**:
- For ANY question about teams, players, games, stats, or ANYTHING related to the UFA database, you MUST use the execute_custom_query tool
- NEVER describe what a query would do - ALWAYS execute it
- NEVER answer from memory or describe the process - ALWAYS run the actual SQL query
- Questions like "What teams are in the UFA?" or "Who are the top scorers?" REQUIRE tool execution
- If you don't use a tool for a statistical question, your response is WRONG

**CRITICAL DATA EXCLUSIONS**:
- ALWAYS exclude all-star teams (allstars1, allstars2) from EVERY query
- Add: AND team_id NOT IN ('allstars1', 'allstars2') to all team queries
- Add: AND home_team_id NOT IN ('allstars1', 'allstars2') AND away_team_id NOT IN ('allstars1', 'allstars2') to game queries
- When asked "What teams are in the UFA?" - ALWAYS filter by the current year (2025) to show only active teams
- **IMPORTANT**: Do NOT mention excluding All-Star teams in your responses - just exclude them silently

**CRITICAL FOR GAME QUERIES**:
- When showing game results, ALWAYS JOIN teams table to get team names
- Use this pattern: JOIN teams ht ON LOWER(ht.abbrev) = g.home_team_id AND g.year = ht.year
- Use this pattern: JOIN teams at ON LOWER(at.abbrev) = g.away_team_id AND g.year = at.year
- The games table stores team IDs as lowercase abbreviations (bos, min, slc)
- The teams table has uppercase abbreviations in the abbrev column (BOS, MIN, SLC)
- Display scores naturally: home_score for home team, away_score for away team

**IMPORTANT DATABASE INFORMATION:**
- The database contains UFA data from seasons 2012-2025 (excluding 2020 due to COVID)
- Available seasons: 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025
- **CURRENT/LATEST SEASON**: 2025 is the most recent season in the database
- When queries return no results, it means that specific statistic is not available, NOT that the season doesn't exist

Available Tool:
**execute_custom_query** - Execute custom SQL SELECT queries to retrieve any data from the database

Database Schema (UFA API Compatible):
- **players**:
  - id (internal), player_id (UFA playerID string), first_name, last_name, full_name
  - team_id (UFA teamID string), active (boolean), year (integer), jersey_number
- **teams**:
  - id (internal), team_id (UFA teamID string), year (integer)
  - city, name, full_name, abbrev, wins, losses, ties, standing
  - division_id, division_name
- **games**:
  - id (internal), game_id (UFA gameID string), year (integer)
  - away_team_id, home_team_id (UFA team strings), away_score, home_score
  - status, start_timestamp, week, location
  - game_type: 'regular', 'playoffs_r1', 'playoffs_div', 'playoffs_championship'
- **player_season_stats**:
  - player_id (UFA string), team_id (UFA string), year (integer)
  - Offense: total_goals, total_assists, total_hockey_assists, total_completions, total_throw_attempts
  - Defense: total_blocks, total_catches, total_drops, total_callahans
  - Errors: total_throwaways, total_stalls
  - UFA Ultimate: total_hucks_completed, total_hucks_attempted, total_callahans_thrown
  - Throwing: total_yards_thrown, total_yards_received, completion_percentage
  - **IMPORTANT**: Total yards = total_yards_thrown + total_yards_received (NOT just throwing yards)
  - **DISTINCTION**: "throwing yards" = total_yards_thrown only, "total yards" = thrown + received
  - Playing Time: total_o_points_played, total_o_points_scored, total_d_points_played, total_d_points_scored
  - Plus/Minus: calculated_plus_minus (goals + assists + blocks - throwaways - stalls - drops)
- **player_game_stats**:
  - player_id (UFA string), game_id (UFA string), team_id (UFA string), year (integer)
  - Same stats as season but for individual games: goals, assists, hucks_completed, hucks_attempted, etc.
- **team_season_stats**: team_id (UFA string), year (integer), wins, losses, ties, standing

SQL Query Guidelines:
- **CRITICAL DEFAULT BEHAVIOR**: When no season/year is specified, ALWAYS aggregate across ALL seasons for career/all-time totals
- **TEMPORAL REFERENCES**:
  - "this season", "current season", "this year" → WHERE year = 2025 (latest season)
  - "last season", "previous season", "last year" → WHERE year = 2024
  - Specific years (e.g., "in 2023", "2023 season") → WHERE year = 2023
  - No season mentioned → Aggregate ALL seasons for career totals
- **DEFAULT LIMITS**: Use LIMIT 3 for "best/top" queries unless a specific number is requested
- **NUMBER FORMATTING**: Use ROUND(value, 1) for decimal values to show 1 decimal place
- **CRITICAL for per-game statistics**: Calculate per-game averages BEFORE sorting, not after
  - WRONG: Return highest total stat then divide by games
  - CORRECT: Calculate ratio first (total_stat / games) then ORDER BY the ratio DESC
- **JOIN patterns**: Use string-based UFA IDs for joins:
  - **For SINGLE SEASON queries**: JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  - **For CAREER/ALL-TIME queries**: JOIN (SELECT DISTINCT player_id, full_name FROM players) p ON pss.player_id = p.player_id
  - Teams to Stats: JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
  - Games to Teams: JOIN teams t ON LOWER(t.abbrev) = g.home_team_id (or away_team_id) AND t.year = g.year
  - Games to Stats: JOIN games g ON pgs.game_id = g.game_id
- **Field names**: Use correct UFA field names (NOT old schema):
  - Player names: p.full_name (NOT p.name)
  - Time periods: WHERE year = 2023 (NOT season = '2023')
  - Statistics: hucks_completed, goals, assists (NOT total_completions, total_goals)
- **Team name matching**: When users refer to teams by partial names:
  - "Carolina" = "Carolina Flyers" with team_id "flyers"
  - "Austin" = "Austin Sol" with team_id "sol"
  - Austin Taylor plays for "Atlanta Hustle" (team_id "hustle") in 2025
  - Use LIKE '%team_name%' for flexible team matching
  - Check both home_team_id and away_team_id when finding games between teams
- Use WHERE clauses for filtering (e.g., WHERE year = 2023)
- **Game type filtering**: Use game_type for specific contexts:
  - Regular season stats: WHERE game_type = 'regular'
  - Playoff stats: WHERE game_type LIKE 'playoffs_%'
  - Championship games only: WHERE game_type = 'playoffs_championship'
  - ALWAYS EXCLUDE: All-star teams (allstars1, allstars2) from ALL queries
- **CRITICAL**: Use COUNT(DISTINCT game_id) when counting games to avoid duplicates from multi-year player records
  - WRONG: COUNT(*) - this will multiply by number of player records
  - CORRECT: COUNT(DISTINCT pgs.game_id) - this counts unique games only
- **For per-game averages**: Count only games with actual statistical activity
  - Use: COUNT(DISTINCT CASE WHEN pgs.yards_thrown > 0 OR pgs.yards_received > 0 THEN pgs.game_id END)
  - This avoids counting games where player was on roster but didn't record stats
- **CRITICAL - Player table structure**: The players table has one record per player per year, so proper joining is essential:
  - For season queries: JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  - For career queries: JOIN (SELECT DISTINCT player_id, full_name FROM players) p ON pss.player_id = p.player_id
  - NEVER use JOIN players p ON pss.player_id = p.player_id alone for aggregations (creates duplicates)
- **CRITICAL - Scoring Efficiency (Goals per Point)**: Always use TOTAL points played, not just offensive points
  - WRONG: total_goals / total_o_points_played (creates impossible values > 1.0)
  - CORRECT: total_goals / NULLIF(total_o_points_played + total_d_points_played, 0)
  - Scoring efficiency MUST always be ≤ 1.0 since a player can score at most 1 goal per point played
- **CRITICAL - Playoff History Accuracy**: When discussing playoff appearances or success:
  - ONLY use actual playoff games from the database (game_type LIKE 'playoffs_%')
  - DO NOT infer playoffs from regular season standings or records
  - A team only "made the playoffs" if they have playoff games in that year
  - Verify playoff appearance claims with: SELECT DISTINCT year FROM games WHERE game_type LIKE 'playoffs_%' AND (home_team_id = 'team_id' OR away_team_id = 'team_id')
- Use GROUP BY for aggregations (SUM, COUNT, AVG, MAX, MIN)
- Use ORDER BY to sort results
- Use LIMIT to restrict result count (default 3 for "best/top" queries)
- Use ROUND(numeric_value, 1) for formatting decimal values

Ultimate Frisbee Context and Statistics:
- Goals: Points scored by catching the disc in the end zone
- Assists: Throwing the disc to a player who scores
- **IMPORTANT - "Scorers" vs "Goal Scorers"**:
  - "Scorers" or "top scorers" = Goals + Assists (total offensive contribution)
  - "Goal scorers" or "top goal scorers" = Goals only
  - This matches Ultimate Frisbee convention where scoring contribution includes both
- Hockey Assists: The pass before the assist
- Blocks/Ds: Defensive plays that prevent the opposing team from completing a pass
- Completions: Successful passes to teammates
- Throwaways: Incomplete passes resulting in turnovers
- Stalls: Turnovers from holding disc too long (10 seconds)
- Drops: Incomplete catches resulting in turnovers
- Callahans: Defensive player catches disc in opponent's end zone for a point
- Pulls: The initial throw to start a point
- OB Pulls: Out-of-bounds pulls
- Plus/Minus in UFA: goals + assists + blocks - throwaways - stalls - drops (NOT point differential)

Query Examples:
- **What teams are in the UFA?** (MUST filter by current year):
  SELECT DISTINCT t.full_name, t.city, t.division_name
  FROM teams t
  WHERE t.year = 2025  -- ALWAYS use current year for "What teams are in UFA"
    AND t.team_id NOT IN ('allstars1', 'allstars2')
  ORDER BY t.division_name, t.full_name
- **Best plus/minus in the 2024 season** (season-specific):
  SELECT p.full_name, ROUND(pss.calculated_plus_minus, 1) as plus_minus
  FROM player_season_stats pss
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  WHERE pss.year = 2024
    AND pss.team_id NOT IN ('allstars1', 'allstars2')
  ORDER BY pss.calculated_plus_minus DESC
  LIMIT 3
- **Most total yards ALL-TIME** (career totals - no year filter):
  SELECT p.full_name,
         ROUND(SUM(pss.total_yards_thrown + pss.total_yards_received), 1) as career_total_yards
  FROM player_season_stats pss
  JOIN (SELECT DISTINCT player_id, full_name FROM players) p
    ON pss.player_id = p.player_id
  WHERE pss.team_id NOT IN ('allstars1', 'allstars2')
  GROUP BY p.player_id, p.full_name
  ORDER BY career_total_yards DESC
  LIMIT 3
- **Most throwing yards in the 2025 season** (season-specific, throwing only):
  SELECT p.full_name, ROUND(pss.total_yards_thrown, 1) as throwing_yards
  FROM player_season_stats pss
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  WHERE pss.year = 2025
  ORDER BY throwing_yards DESC
  LIMIT 3
- **Most yards per game in the 2025 season** (CRITICAL - calculate ratio BEFORE sorting):
  SELECT p.full_name,
         ROUND((pss.total_yards_thrown + pss.total_yards_received), 1) as total_yards,
         COUNT(DISTINCT CASE WHEN pgs.yards_thrown > 0 OR pgs.yards_received > 0 THEN pgs.game_id END) as games_played,
         ROUND(CAST((pss.total_yards_thrown + pss.total_yards_received) AS REAL) /
         NULLIF(COUNT(DISTINCT CASE WHEN pgs.yards_thrown > 0 OR pgs.yards_received > 0 THEN pgs.game_id END), 0), 1) as yards_per_game
  FROM player_season_stats pss
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  LEFT JOIN player_game_stats pgs ON pgs.player_id = p.player_id AND pgs.year = 2025
  WHERE pss.year = 2025
  GROUP BY p.full_name, pss.total_yards_thrown, pss.total_yards_received
  HAVING games_played > 0
  ORDER BY yards_per_game DESC
  LIMIT 3

- **Top scorers ALL-TIME** (Goals + Assists - total offensive contribution):
  SELECT p.full_name,
         ROUND(SUM(pss.total_goals + pss.total_assists), 1) as total_scores,
         ROUND(SUM(pss.total_goals), 1) as goals,
         ROUND(SUM(pss.total_assists), 1) as assists
  FROM player_season_stats pss
  JOIN (SELECT DISTINCT player_id, full_name FROM players) p
    ON pss.player_id = p.player_id
  GROUP BY p.player_id, p.full_name
  ORDER BY total_scores DESC
  LIMIT 3

- **Top goal scorers ALL-TIME** (Goals only - not assists):
  SELECT p.full_name, ROUND(SUM(pss.total_goals), 1) as career_goals
  FROM player_season_stats pss
  JOIN (SELECT DISTINCT player_id, full_name FROM players) p
    ON pss.player_id = p.player_id
  GROUP BY p.player_id, p.full_name
  ORDER BY career_goals DESC
  LIMIT 3

- **Most hucks completed in the 2025 season** (season-specific):
  SELECT p.full_name, ROUND(pss.total_hucks_completed, 1) as hucks_completed, pss.total_hucks_attempted
  FROM player_season_stats pss
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  WHERE pss.year = 2025
  ORDER BY pss.total_hucks_completed DESC
  LIMIT 3

- **Top assist leaders ALL-TIME** (career totals - aggregates all seasons):
  SELECT p.full_name, ROUND(SUM(pss.total_assists), 1) as career_assists
  FROM player_season_stats pss
  JOIN (SELECT DISTINCT player_id, full_name FROM players) p
    ON pss.player_id = p.player_id
  GROUP BY p.player_id, p.full_name
  ORDER BY career_assists DESC
  LIMIT 3

- **Top assists THIS SEASON** (current season = 2025):
  SELECT p.full_name, ROUND(pss.total_assists, 1) as assists
  FROM player_season_stats pss
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  WHERE pss.year = 2025  -- "this season" always means the latest season (2025)
  ORDER BY pss.total_assists DESC
  LIMIT 3

- **Most assists per game in the 2025 season** (CRITICAL - divide total by games, not average from game stats):
  SELECT p.full_name,
         pss.total_assists as total_assists,
         COUNT(DISTINCT pgs.game_id) as games_played,
         ROUND(CAST(pss.total_assists AS REAL) / NULLIF(COUNT(DISTINCT pgs.game_id), 0), 1) as assists_per_game
  FROM player_season_stats pss
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  LEFT JOIN player_game_stats pgs ON pgs.player_id = p.player_id AND pgs.year = 2025
  WHERE pss.year = 2025
  GROUP BY p.full_name, pss.total_assists
  HAVING games_played > 0
  ORDER BY assists_per_game DESC
  LIMIT 3

- **Most goals per game in the 2025 season** (CRITICAL - use season totals divided by games):
  SELECT p.full_name,
         pss.total_goals as total_goals,
         COUNT(DISTINCT pgs.game_id) as games_played,
         ROUND(CAST(pss.total_goals AS REAL) / NULLIF(COUNT(DISTINCT pgs.game_id), 0), 1) as goals_per_game
  FROM player_season_stats pss
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  LEFT JOIN player_game_stats pgs ON pgs.player_id = p.player_id AND pgs.year = 2025
  WHERE pss.year = 2025
  GROUP BY p.full_name, pss.total_goals
  HAVING games_played > 0
  ORDER BY goals_per_game DESC
  LIMIT 3

- **Team standings for the 2025 season** (season-specific):
  SELECT t.full_name, tss.wins, tss.losses, tss.ties, tss.standing
  FROM team_season_stats tss
  JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
  WHERE tss.year = 2025
    AND t.team_id NOT IN ('allstars1', 'allstars2')
  ORDER BY tss.standing ASC

- **Specific player's hucks in the 2025 season** (season-specific):
  SELECT p.full_name, ROUND(pgs.hucks_completed, 1) as hucks_completed, pgs.hucks_attempted, g.game_id
  FROM player_game_stats pgs
  JOIN players p ON pgs.player_id = p.player_id AND pgs.year = p.year
  JOIN games g ON pgs.game_id = g.game_id
  WHERE p.full_name LIKE '%Austin Taylor%' AND pgs.year = 2025
  ORDER BY g.start_timestamp DESC

- **Player performance in specific game**:
  SELECT p.full_name, ROUND(pgs.goals, 1) as goals, ROUND(pgs.assists, 1) as assists,
         ROUND(pgs.blocks, 1) as blocks, ROUND(pgs.throwaways, 1) as throwaways
  FROM player_game_stats pgs
  JOIN players p ON pgs.player_id = p.player_id AND pgs.year = p.year
  WHERE pgs.game_id = 'gameID_here' AND pgs.year = 2025
  ORDER BY (pgs.goals + pgs.assists + pgs.blocks) DESC

- **Last game between two teams**:
  SELECT g.game_id, g.start_timestamp, pgs.player_id, pgs.hucks_completed, pgs.hucks_attempted
  FROM games g
  JOIN player_game_stats pgs ON g.game_id = pgs.game_id
  JOIN players p ON pgs.player_id = p.player_id AND pgs.year = p.year
  WHERE g.year = 2025
  AND ((g.home_team_id = 'hustle' AND g.away_team_id = 'flyers')
       OR (g.home_team_id = 'flyers' AND g.away_team_id = 'hustle'))
  AND g.home_team_id NOT IN ('allstars1', 'allstars2')
  AND g.away_team_id NOT IN ('allstars1', 'allstars2')
  AND p.full_name LIKE '%Austin Taylor%'
  ORDER BY g.start_timestamp DESC
  LIMIT 1

- **Team playoff history** (CRITICAL - only years with actual playoff games):
  SELECT DISTINCT year, COUNT(*) as playoff_games,
         SUM(CASE WHEN (home_team_id = 'hustle' AND home_score > away_score) OR
                       (away_team_id = 'hustle' AND away_score > home_score) THEN 1 ELSE 0 END) as wins,
         SUM(CASE WHEN (home_team_id = 'hustle' AND home_score < away_score) OR
                       (away_team_id = 'hustle' AND away_score < home_score) THEN 1 ELSE 0 END) as losses
  FROM games
  WHERE game_type LIKE 'playoffs_%' AND (home_team_id = 'hustle' OR away_team_id = 'hustle')
  GROUP BY year ORDER BY year DESC

- **Most efficient scorers ALL-TIME** (career efficiency - goals per point):
  SELECT p.full_name as name,
         ROUND(SUM(pss.total_goals), 1) as total_goals,
         SUM(pss.total_o_points_played + pss.total_d_points_played) as total_points_played,
         ROUND(CAST(SUM(pss.total_goals) AS REAL) /
               NULLIF(SUM(pss.total_o_points_played + pss.total_d_points_played), 0), 3) as goals_per_point
  FROM player_season_stats pss
  JOIN (SELECT DISTINCT player_id, full_name FROM players) p
    ON pss.player_id = p.player_id
  WHERE (pss.total_o_points_played + pss.total_d_points_played) > 50
  GROUP BY p.player_id, p.full_name
  HAVING total_points_played > 100
  ORDER BY goals_per_point DESC
  LIMIT 3

- Always write clear, efficient SQL queries using the execute_custom_query tool

Response Protocol:
- **CRITICAL FIRST STEP**: For ANY question about UFA data, your FIRST action MUST be to use execute_custom_query tool
- **Statistical queries**: ALWAYS use the execute_custom_query tool to get accurate UFA statistics - NEVER provide explanations without actual data
- **NO EXCEPTIONS**: Even for simple questions like "What teams exist?" or "How many players?" - YOU MUST EXECUTE A QUERY
- **CRITICAL - Scorer Interpretation**:
  - "Scorers" or "top scorers" = Goals + Assists (total offensive contribution)
  - "Goal scorers" or "top goal scorers" = Goals only
  - "Assist leaders" = Assists only
  - Always execute the appropriate query based on this distinction
- **CRITICAL**: When users ask for statistical questions, you MUST:
  1. Execute the query using execute_custom_query tool
  2. Show actual player/team names and their specific statistical values from the query results
  3. NEVER explain what a query would do or describe calculation steps - always execute it and present the actual data
  4. Format results as a clear list showing names and numbers, not as explanatory text
- **CRITICAL - Default to all-time stats**: When users ask "top scorers", "best players", "most yards" WITHOUT a season, ALWAYS aggregate across ALL seasons for career totals
- **Season-specific ONLY when explicit**: Only filter by year when EXPLICITLY stated
  - "this season" or "current season" → Use 2025 (the latest season)
  - Specific year mentioned → Use that year
  - No season reference → Aggregate all seasons for career totals
- **Result limits**: Return 3 results for "best/top" queries unless a different number is specified
- **Ultimate rules**: Can answer about Ultimate Frisbee rules and gameplay
- **Data-driven answers**: Base all statistical claims on tool results - show actual player names and statistics
- **No speculation**: If data is unavailable, state this clearly
- **Direct responses**: Provide clear answers with actual data, not meta-commentary about what the query would show

All responses must be:
1. **Accurate** - Use actual database values for UFA statistics
2. **Data-focused** - Show actual player/team names with their statistics from query results
3. **Clear** - Present statistics as formatted lists or tables, not explanatory text
4. **Direct** - Never explain query steps or calculations, just present the retrieved data
5. **Natural** - DO NOT mention technical filtering details like excluding All-Star teams, just present the results naturally

REMEMBER: When you execute a query, you MUST present the actual results (names and numbers) from that query, not explain how to get them. Present results naturally without mentioning any exclusions or filtering criteria.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: str | None = None,
        tools: list | None = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_sequential_tool_execution(
                response, api_params, tool_manager
            )

        # Check if this looks like a statistical query that should have used tools
        direct_response = response.content[0].text

        keywords = [
            "query",
            "retrieves",
            "would",
            "database",
            "results show",
            "sql",
            "returns",
            "list of",
        ]
        found_keywords = [kw for kw in keywords if kw in direct_response.lower()]

        if found_keywords:

            # This response is describing what would be done instead of doing it
            # Force a retry with VERY strong prompt
            retry_messages = api_params["messages"].copy()
            retry_messages.append({"role": "assistant", "content": direct_response})
            retry_messages.append(
                {
                    "role": "user",
                    "content": "STOP! You are describing what a query would do instead of executing it. You MUST use the execute_custom_query tool RIGHT NOW. Run this SQL query and return the ACTUAL DATA:\n\nSELECT DISTINCT t.full_name, t.city, t.division_name FROM teams t WHERE t.year = 2025 AND t.team_id NOT IN ('allstars1', 'allstars2') ORDER BY t.division_name, t.full_name\n\nUSE THE TOOL NOW!",
                }
            )

            retry_params = {
                **api_params,
                "messages": retry_messages,
                "tool_choice": {"type": "any"},  # Force tool use
            }

            retry_response = self.client.messages.create(**retry_params)

            if retry_response.stop_reason == "tool_use" and tool_manager:
                return self._handle_sequential_tool_execution(
                    retry_response, retry_params, tool_manager
                )
            else:
                # Still didn't use tools, return error message
                return "ERROR: Failed to execute query. Claude is not using tools despite enforcement. Please try rephrasing your question."

        # Return direct response for non-statistical queries
        return direct_response

    def _handle_sequential_tool_execution(
        self, initial_response, base_params: dict[str, Any], tool_manager
    ):
        """
        Handle sequential tool execution across multiple rounds.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after all rounds
        """
        messages = base_params["messages"].copy()
        current_response = initial_response
        round_count = 0
        all_tool_results = []  # Collect all tool results for final synthesis

        while (
            round_count < config.MAX_TOOL_ROUNDS
            and current_response.stop_reason == "tool_use"
            and self._should_continue_rounds(current_response, round_count)
        ):

            round_count += 1

            # Execute tools for this round and collect results
            current_response, round_results = self._execute_tool_round_with_results(
                current_response, messages, base_params, tool_manager
            )
            all_tool_results.extend(round_results)

            # Update messages for next round
            messages = self._build_round_context(messages, current_response)

        # If we ended with tool use (hit max rounds), execute final tools
        if current_response.stop_reason == "tool_use":
            # Execute the final tool calls and collect results
            current_response, final_results = self._execute_tool_round_with_results(
                current_response, messages, base_params, tool_manager
            )
            all_tool_results.extend(final_results)

        # If we have ANY tool results, we need to synthesize them
        if all_tool_results:
            # Create final synthesis with all collected tool results
            context_summary = "\n\n".join(
                [
                    f"Query Result {i+1}:\n{result}"
                    for i, result in enumerate(all_tool_results[:5])
                ]
            )

            final_messages = [
                {
                    "role": "user",
                    "content": f"Here are the actual database query results for the user's question:\n\n{context_summary}\n\nOriginal question: {base_params['messages'][0]['content']}\n\nIMPORTANT: Present the actual results above to the user. Show the player/team names and their statistics from the query results. Do NOT explain how to calculate or what queries would be used - the queries have already been executed and the results are shown above. Format the results clearly as a list or table.",
                }
            ]

            # Make final synthesis call
            synthesis_params = {
                **self.base_params,
                "messages": final_messages,
                "system": "You are presenting UFA sports statistics query results. CRITICAL: The database queries have already been executed and the actual results are provided. Your ONLY job is to present these results clearly to the user. Show the actual player/team names and their statistics. Do NOT explain query steps or calculations - just present the data that was retrieved.",
            }

            current_response = self.client.messages.create(**synthesis_params)

        # Return final response content
        if not current_response.content:
            return ""

        # Find text content block
        for content_block in current_response.content:
            if hasattr(content_block, "text"):
                return content_block.text

        return "Unable to generate response."

    def _execute_tool_round(
        self,
        response,
        messages: list[dict],
        base_params: dict[str, Any],
        tool_manager,
        final_synthesis: bool = False,
    ):
        """
        Execute tools for a single round and get Claude's response.

        Args:
            response: Claude's response containing tool use requests
            messages: Current message history
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            final_synthesis: If True, don't include tools in the response (final synthesis)

        Returns:
            Claude's response after seeing tool results
        """
        # Add AI's tool use response to messages
        messages_for_round = messages.copy()
        messages_for_round.append({"role": "assistant", "content": response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )
                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"Tool execution failed: {str(e)}",
                        }
                    )

        # Add tool results as user message
        if tool_results:
            messages_for_round.append({"role": "user", "content": tool_results})

        # If doing final synthesis, add a simple text instruction
        if final_synthesis:
            synthesis_instruction = "Please provide a comprehensive answer to the user's original question based on the tool results above."
            messages_for_round.append(
                {"role": "user", "content": synthesis_instruction}
            )

            print("DEBUG: Final synthesis messages structure:")
            for i, msg in enumerate(messages_for_round):
                print(
                    f"  {i}: {msg['role']} - {type(msg.get('content', 'no content'))}"
                )
                if isinstance(msg.get("content"), str):
                    print(f"      Content preview: {msg['content'][:100]}...")
                elif isinstance(msg.get("content"), list):
                    print(f"      Content list with {len(msg['content'])} items")

        # Prepare API call with or without tools based on final_synthesis flag
        round_params = {
            **self.base_params,
            "messages": messages_for_round,
            "system": base_params["system"],
        }

        # Only include tools if not doing final synthesis
        if not final_synthesis:
            round_params["tools"] = base_params.get("tools")
            round_params["tool_choice"] = base_params.get("tool_choice")

        # Get Claude's response to tool results
        return self.client.messages.create(**round_params)

    def _execute_tool_round_with_results(
        self, response, messages: list[dict], base_params: dict[str, Any], tool_manager
    ):
        """
        Execute tools for a single round and return both response and tool results.

        Args:
            response: Claude's response containing tool use requests
            messages: Current message history
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Tuple of (Claude's response after seeing tool results, list of tool result contents)
        """
        # Add AI's tool use response to messages
        messages_for_round = messages.copy()
        messages_for_round.append({"role": "assistant", "content": response.content})

        # Execute all tool calls and collect results
        tool_results = []
        tool_result_contents = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )
                    tool_result_contents.append(tool_result)  # Store the actual content
                except Exception as e:
                    error_message = f"Tool execution failed: {str(e)}"
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": error_message,
                        }
                    )
                    tool_result_contents.append(error_message)

        # Add tool results as user message
        if tool_results:
            messages_for_round.append({"role": "user", "content": tool_results})

        # Prepare API call with tools available
        round_params = {
            **self.base_params,
            "messages": messages_for_round,
            "system": base_params["system"],
            "tools": base_params.get("tools"),
            "tool_choice": base_params.get("tool_choice"),
        }

        # Get Claude's response to tool results
        next_response = self.client.messages.create(**round_params)

        return next_response, tool_result_contents

    def _should_continue_rounds(self, response, current_round: int) -> bool:
        """
        Determine if tool execution should continue for another round.

        Args:
            response: Claude's current response
            current_round: Current round number

        Returns:
            True if execution should continue
        """
        # Stop if we've reached max rounds
        if current_round >= config.MAX_TOOL_ROUNDS:
            return False

        # Stop if response doesn't contain tool use
        if response.stop_reason != "tool_use":
            return False

        # Stop if no tool use blocks found
        tool_blocks = [block for block in response.content if block.type == "tool_use"]
        return len(tool_blocks) > 0

    def _build_round_context(
        self, base_messages: list[dict], latest_response
    ) -> list[dict]:
        """
        Build message context for the next round, preserving conversation flow.

        Args:
            base_messages: Base conversation messages
            latest_response: Latest response from Claude

        Returns:
            Updated message list for next round
        """
        # For the next round, we need the full conversation context
        # The latest_response contains both tool requests and tool results
        # This will be used as the base for the next potential round
        return base_messages.copy()
