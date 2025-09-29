from typing import Any

import anthropic
from core.tool_executor import ToolExecutor
from prompts import SYSTEM_PROMPT
from utils.response import ResponseHandler
from utils.retry import with_rate_limit_retry


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    def __init__(self, api_key: str, model: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

        # Initialize handlers
        self.response_handler = ResponseHandler(self._make_api_call)

    @with_rate_limit_retry(max_retries=4, base_delay=2.0, max_delay=32.0)
    def _make_api_call(self, **params: Any) -> Any:
        """Make an API call to Claude with automatic retry on rate limits."""
        return self.client.messages.create(**params)

    def generate_response(
        self,
        query: str,
        conversation_history: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        tool_manager: Any = None,
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
            f"{SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else SYSTEM_PROMPT
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

        # Get response from Claude with retry logic
        response = self._make_api_call(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            tool_executor = ToolExecutor(self.base_params, self._make_api_call)
            return tool_executor.handle_sequential_tool_execution(
                response, api_params, tool_manager
            )

        # Extract direct response
        direct_response = self.response_handler.extract_text_from_response(response)

        # Check if this looks like a statistical query that should have used tools
        # and enforce tool use if necessary
        if tools and tool_manager:
            return self.response_handler.check_and_enforce_tool_use(
                direct_response, api_params, tool_manager
            )

        # Return direct response for non-statistical queries
        return direct_response
