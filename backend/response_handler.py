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
                    "content": "STOP! You are describing what a query would do instead of executing it. You MUST use the execute_custom_query tool RIGHT NOW. Run this SQL query and return the ACTUAL DATA:\n\nSELECT DISTINCT t.full_name, t.city, t.division_name FROM teams t WHERE t.year = 2025 AND t.team_id NOT IN ('allstars1', 'allstars2') ORDER BY t.division_name, t.full_name\n\nUSE THE TOOL NOW!",
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