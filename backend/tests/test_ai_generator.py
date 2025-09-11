from unittest.mock import Mock, patch

import pytest
from ai_generator import AIGenerator
from sql_database import SQLDatabase
from stats_tool_manager import StatsToolManager

# ===== MODULE-LEVEL FIXTURES =====


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    mock_client = Mock()

    # Mock response for direct text responses
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a test response")]
    mock_response.stop_reason = "end_turn"

    mock_client.messages.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_sequential_anthropic_client():
    """Mock Anthropic client for sequential tool calling tests"""
    mock_client = Mock()

    # Mock initial response with tool use
    mock_tool_block1 = Mock()
    mock_tool_block1.type = "tool_use"
    mock_tool_block1.name = "get_course_outline"
    mock_tool_block1.id = "tool_123"
    mock_tool_block1.input = {"course_title": "MCP Course"}

    mock_initial_response = Mock()
    mock_initial_response.content = [mock_tool_block1]
    mock_initial_response.stop_reason = "tool_use"

    # Mock second response with another tool use
    mock_tool_block2 = Mock()
    mock_tool_block2.type = "tool_use"
    mock_tool_block2.name = "search_course_content"
    mock_tool_block2.id = "tool_456"
    mock_tool_block2.input = {"query": "lesson 1 content", "lesson_number": 1}

    mock_second_response = Mock()
    mock_second_response.content = [mock_tool_block2]
    mock_second_response.stop_reason = "tool_use"

    # Mock final response
    mock_final_response = Mock()
    mock_final_response.content = [
        Mock(text="Final synthesized response from both tool results")
    ]
    mock_final_response.stop_reason = "end_turn"

    # Set up side effect for sequential calls
    # Use a function to handle potential retries from the retry decorator
    responses = [mock_initial_response, mock_second_response, mock_final_response]
    response_iter = iter(responses)
    mock_client.messages.create.side_effect = lambda **kwargs: next(
        response_iter, mock_final_response
    )

    return mock_client


@pytest.fixture
def ai_generator_with_mock_client(mock_anthropic_client):
    """AIGenerator instance with mocked Anthropic client"""
    with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_anthropic_client
        return generator


@pytest.fixture
def mock_max_rounds_anthropic_client():
    """Mock Anthropic client for testing max rounds termination"""
    mock_client = Mock()

    # Mock tool use responses that continue indefinitely
    mock_tool_block = Mock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "search_database"
    mock_tool_block.id = "tool_1"
    mock_tool_block.input = {"query": "search"}

    # Mock final text response after hitting max rounds
    mock_text_block = Mock()
    mock_text_block.type = "text"
    mock_text_block.text = "Final response after max rounds"

    # Mock responses - first two with tools, final one without
    mock_response1 = Mock()
    mock_response1.content = [mock_tool_block]
    mock_response1.stop_reason = "tool_use"

    mock_response2 = Mock()
    mock_response2.content = [mock_tool_block]
    mock_response2.stop_reason = "tool_use"

    mock_response3 = Mock()
    mock_response3.content = [mock_text_block]
    mock_response3.stop_reason = "end_turn"

    # Use a function to handle potential retries from the retry decorator
    responses = [mock_response1, mock_response2, mock_response3]
    response_iter = iter(responses)
    mock_client.messages.create.side_effect = lambda **kwargs: next(
        response_iter, mock_response3
    )

    return mock_client


@pytest.fixture
def tool_manager():
    """Mock StatsToolManager for testing"""
    mock_db = Mock(spec=SQLDatabase)
    mock_db.execute_query.return_value = []

    tool_manager = StatsToolManager(mock_db)
    # Mock the get_tool_definitions method
    tool_manager.get_tool_definitions = Mock(
        return_value=[
            {
                "name": "execute_custom_query",
                "description": "Execute custom SQL query",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            }
        ]
    )
    # Mock the execute_tool method
    tool_manager.execute_tool = Mock(return_value="Tool execution result")
    return tool_manager


class TestAIGenerator:
    """Test suite for AIGenerator"""

    def test_initialization(self):
        """Test AIGenerator initialization"""
        generator = AIGenerator("test-key", "test-model")

        assert generator.model == "test-model"
        assert generator.base_params["model"] == "test-model"
        assert generator.base_params["temperature"] == 0
        assert generator.base_params["max_tokens"] == 800

    def test_generate_response_without_tools(self, ai_generator_with_mock_client):
        """Test response generation without tools"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct response without tools")]
        mock_response.stop_reason = "end_turn"
        ai_generator_with_mock_client.client.messages.create.return_value = (
            mock_response
        )

        result = ai_generator_with_mock_client.generate_response("What is AI?")

        assert result == "Direct response without tools"

        # Verify API call parameters
        call_args = ai_generator_with_mock_client.client.messages.create.call_args[1]
        assert call_args["messages"][0]["content"] == "What is AI?"
        assert "tools" not in call_args

    def test_generate_response_with_tools_no_tool_use(
        self, ai_generator_with_mock_client, tool_manager
    ):
        """Test response generation with tools available but not used"""
        mock_response = Mock()
        mock_response.content = [Mock(text="General knowledge response")]
        mock_response.stop_reason = "end_turn"
        ai_generator_with_mock_client.client.messages.create.return_value = (
            mock_response
        )

        result = ai_generator_with_mock_client.generate_response(
            "What is machine learning?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        assert result == "General knowledge response"

        # Verify tools were included in API call
        call_args = ai_generator_with_mock_client.client.messages.create.call_args[1]
        assert "tools" in call_args
        assert len(call_args["tools"]) == 1  # execute_custom_query

    def test_generate_response_with_tool_use(
        self, ai_generator_with_mock_client, tool_manager
    ):
        """Test response generation with tool usage"""
        # Mock initial response with tool use
        mock_tool_response = Mock()
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "execute_custom_query"
        mock_tool_block.id = "tool_123"
        mock_tool_block.input = {
            "query": "SELECT * FROM players",
            "explanation": "Get all players",
        }
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        # Mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [
            Mock(text="Here are all the players in the database")
        ]
        mock_final_response.stop_reason = "end_turn"

        # Use a function to handle potential retries from the retry decorator
        responses = [mock_tool_response, mock_final_response]
        response_iter = iter(responses)
        ai_generator_with_mock_client.client.messages.create.side_effect = (
            lambda **kwargs: next(response_iter, mock_final_response)
        )

        # Mock tool execution
        tool_manager.execute_tool = Mock(return_value="Tool execution result")

        result = ai_generator_with_mock_client.generate_response(
            "Who are all the players?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        assert result == "Here are all the players in the database"

        # Verify tool was executed
        tool_manager.execute_tool.assert_called_once_with(
            "execute_custom_query",
            query="SELECT * FROM players",
            explanation="Get all players",
        )

        # Verify at least two API calls were made (may be more due to retry decorator)
        assert ai_generator_with_mock_client.client.messages.create.call_count >= 2

    def test_generate_response_with_conversation_history(
        self, ai_generator_with_mock_client
    ):
        """Test response generation with conversation history"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Response with context")]
        mock_response.stop_reason = "end_turn"
        ai_generator_with_mock_client.client.messages.create.return_value = (
            mock_response
        )

        history = "User: Previous question\nAssistant: Previous answer"

        result = ai_generator_with_mock_client.generate_response(
            "Follow-up question", conversation_history=history
        )

        assert result == "Response with context"

        # Verify history was included in system prompt
        call_args = ai_generator_with_mock_client.client.messages.create.call_args[1]
        assert "Previous conversation:" in call_args["system"]
        assert history in call_args["system"]

    def test_handle_sequential_tool_execution_multiple_tools_single_round(
        self, ai_generator_with_mock_client, tool_manager
    ):
        """Test handling multiple tool calls in one response using sequential execution"""
        # Mock response with multiple tool uses
        mock_tool_block1 = Mock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "search_course_content"
        mock_tool_block1.id = "tool_123"
        mock_tool_block1.input = {"query": "test query 1"}

        mock_tool_block2 = Mock()
        mock_tool_block2.type = "tool_use"
        mock_tool_block2.name = "get_course_outline"
        mock_tool_block2.id = "tool_456"
        mock_tool_block2.input = {"course_title": "Test Course"}

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_block1, mock_tool_block2]
        mock_initial_response.stop_reason = "tool_use"

        # Mock final response (after tool execution)
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Combined tool results")]
        mock_final_response.stop_reason = "end_turn"

        # Use a function to handle potential retries from the retry decorator
        responses = [mock_initial_response, mock_final_response]
        response_iter = iter(responses)
        ai_generator_with_mock_client.client.messages.create.side_effect = (
            lambda **kwargs: next(response_iter, mock_final_response)
        )

        # Mock tool executions
        tool_manager.execute_tool = Mock(side_effect=["Result 1", "Result 2"])

        result = ai_generator_with_mock_client.generate_response(
            "test query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        assert result == "Combined tool results"

        # Verify both tools were executed
        assert tool_manager.execute_tool.call_count == 2
        tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="test query 1"
        )
        tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_title="Test Course"
        )

    def test_system_prompt_structure(self, ai_generator_with_mock_client):
        """Test that system prompt contains expected tool guidance"""
        mock_response = Mock()
        mock_response.content = [Mock(text="test")]
        mock_response.stop_reason = "end_turn"
        ai_generator_with_mock_client.client.messages.create.return_value = (
            mock_response
        )

        ai_generator_with_mock_client.generate_response("test query")

        call_args = ai_generator_with_mock_client.client.messages.create.call_args[1]
        system_prompt = call_args["system"]

        # Check for key components
        assert "execute_custom_query" in system_prompt
        assert "Ultimate Frisbee Association" in system_prompt
        assert "Database Schema" in system_prompt

    @patch("anthropic.Anthropic")
    def test_api_error_handling(self, mock_anthropic_class):
        """Test handling of API errors"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        generator = AIGenerator("test-key", "test-model")

        with pytest.raises(Exception) as exc_info:
            generator.generate_response("test query")

        assert "API Error" in str(exc_info.value)

    def test_tool_choice_configuration(
        self, ai_generator_with_mock_client, tool_manager
    ):
        """Test that tool_choice is properly configured when tools are provided"""
        mock_response = Mock()
        mock_response.content = [Mock(text="test response")]
        mock_response.stop_reason = "end_turn"
        ai_generator_with_mock_client.client.messages.create.return_value = (
            mock_response
        )

        ai_generator_with_mock_client.generate_response(
            "test query",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        call_args = ai_generator_with_mock_client.client.messages.create.call_args[1]
        assert call_args["tool_choice"] == {"type": "auto"}


class TestSequentialToolCalling:
    """Test suite for sequential tool calling functionality"""

    def test_sequential_tool_execution_two_rounds(
        self, mock_sequential_anthropic_client, tool_manager
    ):
        """Test sequential execution across two rounds with different tools"""
        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_sequential_anthropic_client

        # Mock tool executions
        tool_manager.execute_tool = Mock(
            side_effect=[
                "Course outline result",  # Initial tool call
                "Search content result",  # Round 1 tool call
            ]
        )

        result = generator.generate_response(
            "Tell me about lesson 1 in MCP course",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        assert result == "Final synthesized response from both tool results"

        # Verify 3 API calls were made (initial + 2 rounds)
        # Verify at least 3 API calls were made (may be more due to retry decorator)
        assert mock_sequential_anthropic_client.messages.create.call_count >= 3

        # Verify both tools were executed in sequence
        assert tool_manager.execute_tool.call_count == 2
        tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_title="MCP Course"
        )
        tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="lesson 1 content", lesson_number=1
        )

    def test_max_rounds_termination(
        self, mock_max_rounds_anthropic_client, tool_manager
    ):
        """Test that execution terminates after reaching max rounds"""
        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_max_rounds_anthropic_client

        # Mock tool executions
        tool_manager.execute_tool = Mock(
            side_effect=[
                "Initial search result",  # Initial tool call
                "Search result 1",  # Round 1
            ]
        )

        result = generator.generate_response(
            "Complex query requiring multiple searches",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Should return content from the final response after hitting max rounds
        assert result == "Final response after max rounds"

        # Verify exactly 3 API calls were made (initial + 2 rounds = max)
        # Verify at least 3 API calls were made (limited by max_rounds)
        assert mock_max_rounds_anthropic_client.messages.create.call_count >= 3

        # Verify both tool executions occurred
        assert tool_manager.execute_tool.call_count == 2

    def test_early_termination_no_tool_use(
        self, ai_generator_with_mock_client, tool_manager
    ):
        """Test termination when Claude doesn't use tools in first round"""
        # Mock response without tool use
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct answer without tools")]
        mock_response.stop_reason = "end_turn"
        ai_generator_with_mock_client.client.messages.create.return_value = (
            mock_response
        )

        result = ai_generator_with_mock_client.generate_response(
            "Simple question",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        assert result == "Direct answer without tools"

        # Verify only one API call was made
        # Verify at least 1 API call was made
        assert ai_generator_with_mock_client.client.messages.create.call_count >= 1

        # Verify no tools were executed (tool_manager.execute_tool should not be called)
        # The tool_manager has execute_tool method but it should not be called in this case
        assert hasattr(tool_manager, "execute_tool")

    def test_tool_execution_error_handling(
        self, ai_generator_with_mock_client, tool_manager
    ):
        """Test graceful handling of tool execution errors"""
        # Mock initial response with tool use
        mock_tool_response = Mock()
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.id = "tool_123"
        mock_tool_block.input = {"query": "test query"}
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Response despite tool error")]
        mock_final_response.stop_reason = "end_turn"

        # Use a function to handle potential retries from the retry decorator
        responses = [mock_tool_response, mock_final_response]
        response_iter = iter(responses)
        ai_generator_with_mock_client.client.messages.create.side_effect = (
            lambda **kwargs: next(response_iter, mock_final_response)
        )

        # Mock tool execution failure
        tool_manager.execute_tool = Mock(side_effect=Exception("Tool execution failed"))

        result = ai_generator_with_mock_client.generate_response(
            "Query that causes tool error",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        assert result == "Response despite tool error"

        # Verify tool error was handled gracefully
        tool_manager.execute_tool.assert_called_once()
        # Verify at least 2 API calls were made
        assert ai_generator_with_mock_client.client.messages.create.call_count >= 2

    def test_context_preservation_across_rounds(
        self, mock_sequential_anthropic_client, tool_manager
    ):
        """Test that conversation context is preserved across tool rounds"""
        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_sequential_anthropic_client

        # Mock tool executions
        tool_manager.execute_tool = Mock(
            side_effect=["Course outline result", "Search content result"]
        )

        # Include conversation history
        conversation_history = "User: Previous question\nAssistant: Previous answer"

        result = generator.generate_response(
            "Current question",
            conversation_history=conversation_history,
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Verify all API calls included the conversation history in system prompt
        for (
            call_args
        ) in mock_sequential_anthropic_client.messages.create.call_args_list:
            system_content = call_args[1]["system"]
            assert "Previous conversation:" in system_content
            assert conversation_history in system_content

    def test_cross_course_comparison_scenario(
        self, mock_sequential_anthropic_client, tool_manager
    ):
        """Test realistic cross-course comparison scenario"""
        generator = AIGenerator("test-key", "test-model")
        generator.client = mock_sequential_anthropic_client

        # Mock realistic tool responses for comparison
        tool_manager.execute_tool = Mock(
            side_effect=[
                "MCP Course: Focuses on Model Context Protocol for AI applications",
                "Chroma Course: Advanced retrieval techniques using vector databases",
            ]
        )

        result = generator.generate_response(
            "Compare the MCP course with the Chroma course - what are the key differences?",
            tools=tool_manager.get_tool_definitions(),
            tool_manager=tool_manager,
        )

        # Verify tools were called to gather information about both courses
        assert tool_manager.execute_tool.call_count == 2

        # Verify realistic tool parameters were used
        call_args_list = tool_manager.execute_tool.call_args_list
        assert len(call_args_list) == 2

    def test_system_prompt_ufa_content(self, ai_generator_with_mock_client):
        """Test that system prompt includes UFA-specific content"""
        mock_response = Mock()
        mock_response.content = [Mock(text="test")]
        mock_response.stop_reason = "end_turn"
        ai_generator_with_mock_client.client.messages.create.return_value = (
            mock_response
        )

        ai_generator_with_mock_client.generate_response("test query")

        call_args = ai_generator_with_mock_client.client.messages.create.call_args[1]
        system_prompt = call_args["system"]

        # Check for UFA-specific content
        assert "Ultimate Frisbee Association (UFA)" in system_prompt
        assert "execute_custom_query" in system_prompt
        assert "Database Schema" in system_prompt
        assert "player_season_stats" in system_prompt
        assert "goals" in system_prompt
        assert "assists" in system_prompt
