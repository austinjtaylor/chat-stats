"""
Response formatter for ensuring complete game statistics display.
"""

import re
from typing import Dict, Any, Optional


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
    check_stats = ["O-Line Conversion", "D-Line Conversion", "Red Zone Conversion", "Turnovers"]
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
        enhanced_stats.append(f"- Final Score: {game_info.get('away_team_name', 'Away')} {game_info.get('away_score', 0)}, {game_info.get('home_team_name', 'Home')} {game_info.get('home_score', 0)}")
        enhanced_stats.append(f"- Location: {game_info.get('location', 'N/A')}")
        enhanced_stats.append("")
    
    enhanced_stats.append("**Team Statistics:**")
    
    # Format away team stats
    away_stats = team_stats.get("away", {})
    if away_stats:
        team_name = game_info.get("away_team_name", "Away Team")
        enhanced_stats.append(f"\n{team_name}:")
        enhanced_stats.append(f"- Completion Percentage: {away_stats.get('completion_percentage', 0)}%")
        enhanced_stats.append(f"- Huck Percentage: {away_stats.get('huck_percentage', 0)}%")
        enhanced_stats.append(f"- Hold Percentage: {away_stats.get('hold_percentage', 0)}%")
        enhanced_stats.append(f"- O-Line Conversion %: {away_stats.get('o_conversion', 0)}%")
        enhanced_stats.append(f"- Break Percentage: {away_stats.get('break_percentage', 0)}%")
        enhanced_stats.append(f"- D-Line Conversion %: {away_stats.get('d_conversion', 0)}%")
        enhanced_stats.append(f"- Red Zone Conversion %: {away_stats.get('redzone_percentage', 'N/A')}%")
        enhanced_stats.append(f"- Blocks: {away_stats.get('total_blocks', 0)}")
        enhanced_stats.append(f"- Turnovers: {away_stats.get('total_turnovers', 0)}")
    
    # Format home team stats
    home_stats = team_stats.get("home", {})
    if home_stats:
        team_name = game_info.get("home_team_name", "Home Team")
        enhanced_stats.append(f"\n{team_name}:")
        enhanced_stats.append(f"- Completion Percentage: {home_stats.get('completion_percentage', 0)}%")
        enhanced_stats.append(f"- Huck Percentage: {home_stats.get('huck_percentage', 0)}%")
        enhanced_stats.append(f"- Hold Percentage: {home_stats.get('hold_percentage', 0)}%")
        enhanced_stats.append(f"- O-Line Conversion %: {home_stats.get('o_conversion', 0)}%")
        enhanced_stats.append(f"- Break Percentage: {home_stats.get('break_percentage', 0)}%")
        enhanced_stats.append(f"- D-Line Conversion %: {home_stats.get('d_conversion', 0)}%")
        enhanced_stats.append(f"- Red Zone Conversion %: {home_stats.get('redzone_percentage', 'N/A')}%")
        enhanced_stats.append(f"- Blocks: {home_stats.get('total_blocks', 0)}")
        enhanced_stats.append(f"- Turnovers: {home_stats.get('total_turnovers', 0)}")
    
    # Find where to insert the enhanced stats
    # Look for existing Team Statistics section
    team_stats_pattern = r"(Team Statistics:.*?)(?=Individual Leaders:|$)"
    match = re.search(team_stats_pattern, answer, re.DOTALL)
    
    if match:
        # Replace existing incomplete team stats with complete version
        enhanced_section = "\n".join(enhanced_stats)
        enhanced_answer = answer[:match.start()] + enhanced_section + answer[match.end():]
    else:
        # Insert before Individual Leaders if present
        if "Individual Leaders:" in answer:
            parts = answer.split("Individual Leaders:")
            enhanced_section = "\n".join(enhanced_stats) + "\n\n"
            enhanced_answer = parts[0] + enhanced_section + "Individual Leaders:" + "Individual Leaders:".join(parts[1:])
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
        "versus"
    ]
    
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in game_keywords)