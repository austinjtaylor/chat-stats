"""
Response validation and processing for AI-generated content.
Handles keyword detection and forces tool use when necessary.
"""

from datetime import datetime
from typing import Any


class ResponseHandler:
    """Handles response validation and processing."""

    def __init__(self, make_api_call: Any) -> None:
        """
        Initialize response handler.

        Args:
            make_api_call: Function to make API calls
        """
        self.make_api_call = make_api_call

    def check_and_enforce_tool_use(
        self, direct_response: str, api_params: dict[str, Any], tool_manager: Any
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
                from core.tool_executor import ToolExecutor

                executor = ToolExecutor(api_params, self.make_api_call)
                return executor.handle_sequential_tool_execution(
                    retry_response, retry_params, tool_manager
                )
            else:
                # Still didn't use tools, return error message
                return "ERROR: Failed to execute query. Claude is not using tools despite enforcement. Please try rephrasing your question."

        return direct_response

    def extract_text_from_response(self, response: Any) -> str:
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
from typing import Any


def format_game_details_response(answer: str, data: list[Any]) -> str:
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

    # Build enhanced team statistics section using markdown tables
    enhanced_stats = []

    game_info = game_data.get("game", {})
    away_stats = team_stats.get("away", {})
    home_stats = team_stats.get("home", {})

    # Always add game details as a table (will replace existing if present)
    enhanced_stats.append("---")
    enhanced_stats.append("")
    enhanced_stats.append("## Game Details")
    enhanced_stats.append("")
    enhanced_stats.append("| | |")
    enhanced_stats.append("|----------|-------------|")
    enhanced_stats.append(f"| **Game ID** | {game_info.get('game_id', 'N/A')} |")

    # Format date - handle both datetime objects and strings
    start_timestamp = game_info.get('start_timestamp', 'N/A')
    if isinstance(start_timestamp, datetime):
        date_str = start_timestamp.strftime('%Y-%m-%d')
    elif isinstance(start_timestamp, str) and start_timestamp != 'N/A':
        date_str = start_timestamp[:10]
    else:
        date_str = 'N/A'
    enhanced_stats.append(f"| **Date** | {date_str} |")
    enhanced_stats.append(
        f"| **Final Score** | **{game_info.get('away_team_name', 'Away')} {game_info.get('away_score', 0)}** - **{game_info.get('home_team_name', 'Home')} {game_info.get('home_score', 0)}** |"
    )
    enhanced_stats.append(f"| **Location** | {game_info.get('location', 'N/A')} |")
    enhanced_stats.append(f"| **Game Type** | {game_info.get('game_type', 'N/A')} |")

    # Build team statistics table
    enhanced_stats.append("")
    enhanced_stats.append("---")
    enhanced_stats.append("")
    enhanced_stats.append("## Team Statistics")
    enhanced_stats.append("")

    away_team_name = game_info.get("away_team_name", "Away Team")
    home_team_name = game_info.get("home_team_name", "Home Team")

    enhanced_stats.append(f"| Statistic | {away_team_name} | {home_team_name} |")
    enhanced_stats.append("|-----------|------------------|------------------|")

    # Completion %
    away_comp = away_stats.get('completion_percentage_display', away_stats.get('completion_percentage', 0))
    home_comp = home_stats.get('completion_percentage_display', home_stats.get('completion_percentage', 0))
    enhanced_stats.append(f"| **Completion %** | {away_comp} | {home_comp} |")

    # Huck %
    away_huck = away_stats.get('huck_percentage_display', away_stats.get('huck_percentage', 0))
    home_huck = home_stats.get('huck_percentage_display', home_stats.get('huck_percentage', 0))
    enhanced_stats.append(f"| **Huck %** | {away_huck} | {home_huck} |")

    # Hold %
    away_hold = away_stats.get('hold_percentage_display', away_stats.get('hold_percentage', 0))
    home_hold = home_stats.get('hold_percentage_display', home_stats.get('hold_percentage', 0))
    enhanced_stats.append(f"| **Hold %** | {away_hold} | {home_hold} |")

    # O-Line Conversion %
    away_o = away_stats.get('o_conversion_display', away_stats.get('o_conversion', 0))
    home_o = home_stats.get('o_conversion_display', home_stats.get('o_conversion', 0))
    enhanced_stats.append(f"| **O-Line Conversion %** | {away_o} | {home_o} |")

    # Break %
    away_break = away_stats.get('break_percentage_display', away_stats.get('break_percentage', 0))
    home_break = home_stats.get('break_percentage_display', home_stats.get('break_percentage', 0))
    enhanced_stats.append(f"| **Break %** | {away_break} | {home_break} |")

    # D-Line Conversion %
    away_d = away_stats.get('d_conversion_display', away_stats.get('d_conversion', 0))
    home_d = home_stats.get('d_conversion_display', home_stats.get('d_conversion', 0))
    enhanced_stats.append(f"| **D-Line Conversion %** | {away_d} | {home_d} |")

    # Red Zone Conversion %
    away_redzone = away_stats.get("redzone_percentage_display", f"{away_stats.get('redzone_percentage', 0)}%" if away_stats.get('redzone_percentage') is not None else "N/A")
    home_redzone = home_stats.get("redzone_percentage_display", f"{home_stats.get('redzone_percentage', 0)}%" if home_stats.get('redzone_percentage') is not None else "N/A")
    enhanced_stats.append(f"| **Red Zone Conversion %** | {away_redzone} | {home_redzone} |")

    # Blocks
    away_blocks = away_stats.get('total_blocks', 0)
    home_blocks = home_stats.get('total_blocks', 0)
    enhanced_stats.append(f"| **Blocks** | {away_blocks} | {home_blocks} |")

    # Turnovers
    away_to = away_stats.get('total_turnovers', 0)
    home_to = home_stats.get('total_turnovers', 0)
    enhanced_stats.append(f"| **Turnovers** | {away_to} | {home_to} |")

    # Add Individual Leaders section as a single consolidated table
    individual_leaders = game_data.get("individual_leaders", {})
    if individual_leaders:
        enhanced_stats.append("")
        enhanced_stats.append("---")
        enhanced_stats.append("")
        enhanced_stats.append("## Individual Leaders")
        enhanced_stats.append("")

        # Create table header with team names as columns
        enhanced_stats.append(f"| Category | {away_team_name} | {home_team_name} |")
        enhanced_stats.append("|----------|------------------|------------------|")

        # Define stat categories with display names
        stat_categories = [
            ("assists", "Assists"),
            ("goals", "Goals"),
            ("blocks", "Blocks"),
            ("completions", "Completions"),
            ("points_played", "Points Played"),
            ("plus_minus", "Plus/Minus")
        ]

        # Add one row per category with both teams' leaders
        for stat_key, stat_display in stat_categories:
            leaders = individual_leaders.get(stat_key, {})
            away_leader = leaders.get("away")
            home_leader = leaders.get("home")

            # Format away team leader
            if away_leader:
                player_name = away_leader.get("full_name", "N/A")
                value = away_leader.get("value", 0)
                # Format plus/minus with + sign for positive values
                if stat_key == "plus_minus" and value > 0:
                    away_cell = f"+{value} - {player_name}"
                else:
                    away_cell = f"{value} - {player_name}"
            else:
                away_cell = "N/A"

            # Format home team leader
            if home_leader:
                player_name = home_leader.get("full_name", "N/A")
                value = home_leader.get("value", 0)
                # Format plus/minus with + sign for positive values
                if stat_key == "plus_minus" and value > 0:
                    home_cell = f"+{value} - {player_name}"
                else:
                    home_cell = f"{value} - {player_name}"
            else:
                home_cell = "N/A"

            # Add row with category and both teams' leaders
            enhanced_stats.append(f"| {stat_display} | {away_cell} | {home_cell} |")

        enhanced_stats.append("")

    # Find where to insert the enhanced stats
    # Replace everything from "Game Details:" to end of response (including any existing Individual Leaders)
    # This ensures we replace Game Details, Team Statistics, and Individual Leaders sections with table versions
    game_details_pattern = r"(Game Details:.*?)$"
    match = re.search(game_details_pattern, answer, re.DOTALL | re.IGNORECASE)

    if match:
        # Replace existing game details, team stats, and individual leaders with table versions
        enhanced_section = "\n".join(enhanced_stats)
        # Keep the intro text before "Game Details:"
        intro = answer[: match.start()]
        # Replace everything from Game Details to end with our formatted tables
        enhanced_answer = intro + enhanced_section
    else:
        # No existing Game Details section, insert before Individual Leaders or at end
        if "Individual Leaders:" in answer or "Individual Leaders" in answer:
            # Find the Individual Leaders section
            leaders_match = re.search(r"Individual Leaders", answer, re.IGNORECASE)
            if leaders_match:
                enhanced_section = "\n".join(enhanced_stats) + "\n\n"
                enhanced_answer = (
                    answer[: leaders_match.start()]
                    + enhanced_section
                    + answer[leaders_match.start() :]
                )
            else:
                enhanced_answer = answer + "\n\n" + "\n".join(enhanced_stats)
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
