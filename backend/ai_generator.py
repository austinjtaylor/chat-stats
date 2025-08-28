from typing import Any

import anthropic
from config import config


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """You are an AI assistant specialized in Ultimate Frisbee Association (UFA) statistics with direct SQL access to query the sports database.

**IMPORTANT DATABASE INFORMATION:**
- The database contains UFA data from seasons 2012-2025 (excluding 2020 due to COVID)
- The most recent complete season is 2025
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
  - game_type: 'regular', 'playoffs_r1', 'playoffs_div', 'playoffs_championship', 'allstar'
- **player_season_stats**: 
  - player_id (UFA string), team_id (UFA string), year (integer)
  - Offense: total_goals, total_assists, total_hockey_assists, total_completions, total_throw_attempts
  - Defense: total_blocks, total_catches, total_drops, total_callahans
  - Errors: total_throwaways, total_stalls
  - UFA Ultimate: total_hucks_completed, total_hucks_attempted, total_callahans_thrown
  - Throwing: total_yards_thrown, total_yards_received, completion_percentage
  - Playing Time: total_o_points_played, total_o_points_scored, total_d_points_played, total_d_points_scored
  - Plus/Minus: calculated_plus_minus (goals + assists + blocks - throwaways - stalls - drops)
- **player_game_stats**: 
  - player_id (UFA string), game_id (UFA string), team_id (UFA string), year (integer)
  - Same stats as season but for individual games: goals, assists, hucks_completed, hucks_attempted, etc.
- **team_season_stats**: team_id (UFA string), year (integer), wins, losses, ties, standing

SQL Query Guidelines:
- **IMPORTANT**: When no season/year is specified in the query, aggregate across ALL seasons for career/all-time totals
- Only filter by a specific season when explicitly mentioned (e.g., 'this season', '2023 season', 'current season')
- **JOIN patterns**: Use string-based UFA IDs for joins (CRITICAL - must include year matching for players):
  - Players to Stats: JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
  - Teams to Stats: JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year
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
  - All-star games: WHERE game_type = 'allstar'
- **CRITICAL**: Use COUNT(DISTINCT game_id) when counting games to avoid duplicates from multi-year player records
  - WRONG: COUNT(*) - this will multiply by number of player records
  - CORRECT: COUNT(DISTINCT pgs.game_id) - this counts unique games only
- **CRITICAL - Player table joins**: The players table has one record per player per year, so joining WITHOUT year matching creates duplicates that multiply stats incorrectly
  - WRONG: JOIN players p ON pss.player_id = p.player_id (multiplies stats by number of years played)  
  - CORRECT: JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year
- Use GROUP BY for aggregations (SUM, COUNT, AVG, MAX, MIN)
- Use ORDER BY to sort results
- Use LIMIT to restrict result count

Ultimate Frisbee Context and Statistics:
- Goals: Points scored by catching the disc in the end zone
- Assists: Throwing the disc to a player who scores
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
- **Best plus/minus in 2024**:
  SELECT p.full_name, pss.calculated_plus_minus 
  FROM player_season_stats pss 
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year 
  WHERE pss.year = 2024 
  ORDER BY pss.calculated_plus_minus DESC 
  LIMIT 10

- **All-time top goal scorers** (no season specified): 
  SELECT p.full_name, SUM(pss.total_goals) as career_goals 
  FROM player_season_stats pss 
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year 
  GROUP BY p.player_id, p.full_name 
  ORDER BY career_goals DESC 
  LIMIT 10

- **Most hucks completed in 2025**:
  SELECT p.full_name, pss.total_hucks_completed, pss.total_hucks_attempted
  FROM player_season_stats pss 
  JOIN players p ON pss.player_id = p.player_id AND pss.year = p.year 
  WHERE pss.year = 2025 
  ORDER BY pss.total_hucks_completed DESC 
  LIMIT 10

- **Team standings for specific season**:
  SELECT t.full_name, tss.wins, tss.losses, tss.ties, tss.standing 
  FROM team_season_stats tss 
  JOIN teams t ON tss.team_id = t.team_id AND tss.year = t.year 
  WHERE tss.year = 2025 
  ORDER BY tss.standing ASC

- **Austin Taylor's hucks in 2025**:
  SELECT p.full_name, pgs.hucks_completed, pgs.hucks_attempted, g.game_id
  FROM player_game_stats pgs 
  JOIN players p ON pgs.player_id = p.player_id AND pgs.year = p.year 
  JOIN games g ON pgs.game_id = g.game_id
  WHERE p.full_name LIKE '%Austin Taylor%' AND pgs.year = 2025
  ORDER BY g.start_timestamp DESC

- **Player performance in specific game**:
  SELECT p.full_name, pgs.goals, pgs.assists, pgs.blocks, pgs.throwaways
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
  AND p.full_name LIKE '%Austin Taylor%'
  ORDER BY g.start_timestamp DESC
  LIMIT 1

- Always write clear, efficient SQL queries using the execute_custom_query tool

Response Protocol:
- **Statistical queries**: Always use the execute_custom_query tool to get accurate UFA statistics
- **Default to all-time stats**: When users ask generic questions like "top scorers" or "best players" without mentioning a specific season, show all-time career totals by aggregating across all seasons
- **Season-specific only when explicit**: Only filter by year when the user specifically mentions one (e.g., "this season", "2023", "current season")
- **Ultimate rules**: Can answer about Ultimate Frisbee rules and gameplay
- **Data-driven answers**: Base all statistical claims on tool results
- **No speculation**: If data is unavailable, state this clearly
- **Direct responses**: Provide clear answers without meta-commentary

All responses must be:
1. **Accurate** - Use actual database values for UFA statistics
2. **Concise** - Focus on key Ultimate Frisbee metrics
3. **Contextual** - Explain Ultimate-specific terms when helpful
4. **Clear** - Present statistics in an easy-to-understand format
Provide only the direct answer to what was asked.
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

        # Return direct response
        return response.content[0].text

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

            # Create final synthesis with all collected tool results
            context_summary = "\n\n".join(
                [
                    f"Data result {i+1}: {result}"
                    for i, result in enumerate(all_tool_results[:5])
                ]
            )

            final_messages = [
                {
                    "role": "user",
                    "content": f"Based on the following sports statistics data:\n\n{context_summary}\n\nOriginal question: {base_params['messages'][0]['content']}\n\nProvide a comprehensive answer using the statistics above.",
                }
            ]

            # Make final synthesis call
            synthesis_params = {
                **self.base_params,
                "messages": final_messages,
                "system": "You are a sports statistics expert. Use the provided data to answer questions about player stats, team performance, and game results accurately and comprehensively.",
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
