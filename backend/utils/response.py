"""
Response validation and processing for AI-generated content.
Handles keyword detection and forces tool use when necessary.
"""

from typing import Any, List


class ResponseHandler:
    """Handles response validation and processing."""

    def __init__(self, make_api_call):
        """
        Initialize response handler.

        Args:
            make_api_call: Function to make API calls
        """
        self.make_api_call = make_api_call

    def check_and_enforce_tool_use(
        self, direct_response: str, api_params: dict[str, Any], tool_manager
    ) -> str:
        """
        Check if response should have used tools and enforce it if necessary.

        Args:
            direct_response: The initial response from Claude
            api_params: API parameters used for the call
            tool_manager: Tool manager for execution

        Returns:
            Either the corrected response or error message
        """
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
                    "content": "STOP! You are describing what a query would do instead of executing it. You MUST use the execute_custom_query tool RIGHT NOW. Run this SQL query and return the ACTUAL DATA:\n\nSELECT DISTINCT t.full_name, t.city, t.division_name FROM teams t WHERE t.year = 2025 ORDER BY t.division_name, t.full_name\n\nUSE THE TOOL NOW!",
                }
            )

            retry_params = {
                **api_params,
                "messages": retry_messages,
                "tool_choice": {"type": "any"},  # Force tool use
            }

            retry_response = self.make_api_call(**retry_params)

            if retry_response.stop_reason == "tool_use" and tool_manager:
                from tool_executor import ToolExecutor

                executor = ToolExecutor(api_params, self.make_api_call)
                return executor.handle_sequential_tool_execution(
                    retry_response, retry_params, tool_manager
                )
            else:
                # Still didn't use tools, return error message
                return "ERROR: Failed to execute query. Claude is not using tools despite enforcement. Please try rephrasing your question."

        return direct_response

    def extract_text_from_response(self, response) -> str:
        """
        Extract text content from a Claude response.

        Args:
            response: Claude's response object

        Returns:
            Extracted text or empty string
        """
        if not response.content:
            return ""

        # Find text content block
        for content_block in response.content:
            if hasattr(content_block, "text"):
                return content_block.text

        return ""

    def validate_response_quality(self, response: str) -> bool:
        """
        Validate that a response meets quality standards.

        Args:
            response: The response text to validate

        Returns:
            True if response is acceptable
        """
        # Check for empty response
        if not response or response.strip() == "":
            return False

        # Check for error indicators
        error_phrases = [
            "unable to generate",
            "error occurred",
            "failed to execute",
        ]

        response_lower = response.lower()
        for phrase in error_phrases:
            if phrase in response_lower:
                return False

        return True
"""
Response formatter for ensuring complete game statistics display.
"""

import re
from typing import Any, Dict, Optional


def format_game_details_response(answer: str, data: list) -> str:
    """
    Enhance game details response to include all available statistics.

    Args:
        answer: The AI-generated answer
        data: The tool execution data containing team statistics

    Returns:
        Enhanced answer with all statistics included
    """
    # Check if this is a game details response
    if not data or not isinstance(data, list):
        return answer

    # Look for get_game_details tool data
    game_data = None
    for item in data:
        if isinstance(item, dict) and item.get("tool") == "get_game_details":
            game_data = item.get("data", {})
            break

    if not game_data:
        return answer

    # Extract team statistics
    team_stats = game_data.get("team_statistics", {})
    if not team_stats or (not team_stats.get("home") and not team_stats.get("away")):
        return answer

    # Check if the answer is missing key statistics
    missing_stats = []
    check_stats = [
        "O-Line Conversion",
        "D-Line Conversion",
        "Red Zone Conversion",
        "Turnovers",
    ]
    for stat in check_stats:
        if stat not in answer:
            missing_stats.append(stat)

    # If all stats are present, return as is
    if not missing_stats:
        return answer

    # Build enhanced team statistics section
    enhanced_stats = []

    game_info = game_data.get("game", {})

    # Add game details header if not present
    if "Game Details:" not in answer:
        enhanced_stats.append("**Game Details:**")
        enhanced_stats.append(f"- Game ID: {game_info.get('game_id', 'N/A')}")
        enhanced_stats.append(f"- Date: {game_info.get('start_timestamp', 'N/A')[:10]}")
        enhanced_stats.append(
            f"- Final Score: {game_info.get('away_team_name', 'Away')} {game_info.get('away_score', 0)}, {game_info.get('home_team_name', 'Home')} {game_info.get('home_score', 0)}"
        )
        enhanced_stats.append(f"- Location: {game_info.get('location', 'N/A')}")
        enhanced_stats.append("")

    enhanced_stats.append("**Team Statistics:**")

    # Format away team stats
    away_stats = team_stats.get("away", {})
    if away_stats:
        team_name = game_info.get("away_team_name", "Away Team")
        enhanced_stats.append(f"\n{team_name}:")
        enhanced_stats.append(
            f"- Completion Percentage: {away_stats.get('completion_percentage_display', away_stats.get('completion_percentage', 0))}"
        )
        enhanced_stats.append(
            f"- Huck Percentage: {away_stats.get('huck_percentage_display', away_stats.get('huck_percentage', 0))}"
        )
        enhanced_stats.append(
            f"- Hold %: {away_stats.get('hold_percentage_display', away_stats.get('hold_percentage', 0))}"
        )
        enhanced_stats.append(
            f"- O-Line Conversion %: {away_stats.get('o_conversion_display', away_stats.get('o_conversion', 0))}"
        )
        enhanced_stats.append(
            f"- Break %: {away_stats.get('break_percentage_display', away_stats.get('break_percentage', 0))}"
        )
        enhanced_stats.append(
            f"- D-Line Conversion %: {away_stats.get('d_conversion_display', away_stats.get('d_conversion', 0))}"
        )
        redzone_display = away_stats.get("redzone_percentage_display")
        if redzone_display:
            enhanced_stats.append(f"- Red Zone Conversion %: {redzone_display}")
        elif away_stats.get("redzone_percentage") is not None:
            enhanced_stats.append(
                f"- Red Zone Conversion %: {away_stats.get('redzone_percentage')}%"
            )
        enhanced_stats.append(f"- Blocks: {away_stats.get('total_blocks', 0)}")
        enhanced_stats.append(f"- Turnovers: {away_stats.get('total_turnovers', 0)}")

    # Format home team stats
    home_stats = team_stats.get("home", {})
    if home_stats:
        team_name = game_info.get("home_team_name", "Home Team")
        enhanced_stats.append(f"\n{team_name}:")
        enhanced_stats.append(
            f"- Completion Percentage: {home_stats.get('completion_percentage_display', home_stats.get('completion_percentage', 0))}"
        )
        enhanced_stats.append(
            f"- Huck Percentage: {home_stats.get('huck_percentage_display', home_stats.get('huck_percentage', 0))}"
        )
        enhanced_stats.append(
            f"- Hold %: {home_stats.get('hold_percentage_display', home_stats.get('hold_percentage', 0))}"
        )
        enhanced_stats.append(
            f"- O-Line Conversion %: {home_stats.get('o_conversion_display', home_stats.get('o_conversion', 0))}"
        )
        enhanced_stats.append(
            f"- Break %: {home_stats.get('break_percentage_display', home_stats.get('break_percentage', 0))}"
        )
        enhanced_stats.append(
            f"- D-Line Conversion %: {home_stats.get('d_conversion_display', home_stats.get('d_conversion', 0))}"
        )
        redzone_display = home_stats.get("redzone_percentage_display")
        if redzone_display:
            enhanced_stats.append(f"- Red Zone Conversion %: {redzone_display}")
        elif home_stats.get("redzone_percentage") is not None:
            enhanced_stats.append(
                f"- Red Zone Conversion %: {home_stats.get('redzone_percentage')}%"
            )
        enhanced_stats.append(f"- Blocks: {home_stats.get('total_blocks', 0)}")
        enhanced_stats.append(f"- Turnovers: {home_stats.get('total_turnovers', 0)}")

    # Find where to insert the enhanced stats
    # Look for existing Team Statistics section
    team_stats_pattern = r"(Team Statistics:.*?)(?=Individual Leaders:|$)"
    match = re.search(team_stats_pattern, answer, re.DOTALL)

    if match:
        # Replace existing incomplete team stats with complete version
        enhanced_section = "\n".join(enhanced_stats)
        enhanced_answer = (
            answer[: match.start()] + enhanced_section + answer[match.end() :]
        )
    else:
        # Insert before Individual Leaders if present
        if "Individual Leaders:" in answer:
            parts = answer.split("Individual Leaders:")
            enhanced_section = "\n".join(enhanced_stats) + "\n\n"
            enhanced_answer = (
                parts[0]
                + enhanced_section
                + "Individual Leaders:"
                + "Individual Leaders:".join(parts[1:])
            )
        else:
            # Append to the end
            enhanced_answer = answer + "\n\n" + "\n".join(enhanced_stats)

    return enhanced_answer


def should_format_response(query: str) -> bool:
    """
    Determine if a query should have its response formatted.

    Args:
        query: The user's query

    Returns:
        True if the response should be formatted
    """
    # Keywords that indicate a game details query
    game_keywords = [
        "game details",
        "tell me about",
        "show me details",
        "what happened in",
        "game between",
        "vs",
        "versus",
    ]

    query_lower = query.lower()
    return any(keyword in query_lower for keyword in game_keywords)
