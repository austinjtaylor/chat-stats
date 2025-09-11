"""
Tool execution handler for AI-driven queries.
Manages sequential tool execution and result aggregation.
"""

from typing import Any, List, Tuple
from config import config


class ToolExecutor:
    """Handles tool execution for AI responses."""
    
    def __init__(self, base_params: dict, make_api_call):
        """
        Initialize tool executor.
        
        Args:
            base_params: Base parameters for API calls
            make_api_call: Function to make API calls
        """
        self.base_params = base_params
        self.make_api_call = make_api_call

    def handle_sequential_tool_execution(
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
            current_response, round_results = self.execute_tool_round_with_results(
                current_response, messages, base_params, tool_manager
            )
            all_tool_results.extend(round_results)

            # Update messages for next round
            messages = self._build_round_context(messages, current_response)

        # If we ended with tool use (hit max rounds), execute final tools
        if current_response.stop_reason == "tool_use":
            # Execute the final tool calls and collect results
            current_response, final_results = self.execute_tool_round_with_results(
                current_response, messages, base_params, tool_manager
            )
            all_tool_results.extend(final_results)

        # If we have ANY tool results, we need to synthesize them
        if all_tool_results:
            return self._synthesize_results(all_tool_results, base_params)

        # Return final response content
        if not current_response.content:
            return ""

        # Find text content block
        for content_block in current_response.content:
            if hasattr(content_block, "text"):
                return content_block.text

        return "Unable to generate response."

    def execute_tool_round_with_results(
        self, response, messages: list[dict], base_params: dict[str, Any], tool_manager
    ) -> Tuple[Any, List[str]]:
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
        next_response = self.make_api_call(**round_params)

        return next_response, tool_result_contents

    def _synthesize_results(self, all_tool_results: List[str], base_params: dict[str, Any]) -> str:
        """
        Synthesize all tool results into a final response.
        
        Args:
            all_tool_results: List of all tool result contents
            base_params: Base API parameters
            
        Returns:
            Final synthesized response
        """
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
        # Preserve the original system prompt (which may include conversation history)
        synthesis_system = "You are presenting UFA sports statistics query results. CRITICAL: The database queries have already been executed and the actual results are provided. Your ONLY job is to present these results clearly to the user. Show the actual player/team names and their statistics. Do NOT explain query steps or calculations - just present the data that was retrieved."
        
        if "system" in base_params and "Previous conversation:" in base_params["system"]:
            # If there was conversation history, preserve it
            from prompts import SYSTEM_PROMPT
            synthesis_system = base_params["system"].replace(
                SYSTEM_PROMPT, synthesis_system
            )

        synthesis_params = {
            **self.base_params,
            "messages": final_messages,
            "system": synthesis_system,
        }

        current_response = self.make_api_call(**synthesis_params)
        
        # Extract text from response
        if not current_response.content:
            return ""

        for content_block in current_response.content:
            if hasattr(content_block, "text"):
                return content_block.text

        return "Unable to generate response."

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