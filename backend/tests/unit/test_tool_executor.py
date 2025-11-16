"""
Test tool executor module.
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.tool_executor import ToolExecutor


class TestToolExecutor:
    """Test ToolExecutor class"""

    def test_init_with_db(self):
        """Test initialization with database"""
        mock_db = MagicMock()
        executor = ToolExecutor(mock_db)

        assert executor.db == mock_db
        assert hasattr(executor, "tool_manager")

    def test_init_without_db(self):
        """Test initialization without database"""
        executor = ToolExecutor(None)

        assert executor.db is None
        assert hasattr(executor, "tool_manager")

    def test_execute_tool_success(self):
        """Test successful tool execution"""
        mock_db = MagicMock()
        executor = ToolExecutor(mock_db)

        # Mock the tool manager
        mock_tool = MagicMock()
        mock_tool.return_value = {"result": "test data"}
        executor.tool_manager.get_tool = MagicMock(return_value=mock_tool)

        result = executor.execute_tool("test_tool", {"param": "value"})

        assert result == {"result": "test data"}
        mock_tool.assert_called_once_with(param="value")

    def test_execute_tool_not_found(self):
        """Test execution with non-existent tool"""
        mock_db = MagicMock()
        executor = ToolExecutor(mock_db)

        # Mock tool manager to return None
        executor.tool_manager.get_tool = MagicMock(return_value=None)

        result = executor.execute_tool("non_existent_tool", {})

        assert "error" in result
        assert "Tool not found" in result["error"]

    def test_execute_tool_with_error(self):
        """Test tool execution with error"""
        mock_db = MagicMock()
        executor = ToolExecutor(mock_db)

        # Mock tool to raise exception
        mock_tool = MagicMock()
        mock_tool.side_effect = Exception("Tool execution failed")
        executor.tool_manager.get_tool = MagicMock(return_value=mock_tool)

        result = executor.execute_tool("error_tool", {})

        assert "error" in result
        assert "Tool execution failed" in result["error"]

    def test_execute_multiple_tools(self):
        """Test executing multiple tools in sequence"""
        mock_db = MagicMock()
        executor = ToolExecutor(mock_db)

        # Mock different tools
        tool1 = MagicMock(return_value={"data": "result1"})
        tool2 = MagicMock(return_value={"data": "result2"})

        def get_tool(name):
            if name == "tool1":
                return tool1
            elif name == "tool2":
                return tool2
            return None

        executor.tool_manager.get_tool = MagicMock(side_effect=get_tool)

        # Execute tools
        result1 = executor.execute_tool("tool1", {"param": "a"})
        result2 = executor.execute_tool("tool2", {"param": "b"})

        assert result1 == {"data": "result1"}
        assert result2 == {"data": "result2"}
        tool1.assert_called_once_with(param="a")
        tool2.assert_called_once_with(param="b")

    def test_get_available_tools(self):
        """Test getting list of available tools"""
        mock_db = MagicMock()
        executor = ToolExecutor(mock_db)

        # Mock tool manager to return tool list
        mock_tools = {
            "tool1": {"description": "Tool 1"},
            "tool2": {"description": "Tool 2"},
        }
        executor.tool_manager.get_tools = MagicMock(return_value=mock_tools)

        tools = executor.get_available_tools()

        assert tools == mock_tools
        executor.tool_manager.get_tools.assert_called_once()

    def test_execute_with_db_context(self):
        """Test tool execution uses database context"""
        mock_db = MagicMock()
        mock_db.execute_query = MagicMock(return_value=[{"id": 1, "name": "Test"}])

        executor = ToolExecutor(mock_db)

        # Create a tool that uses the database
        def db_tool(**kwargs):
            query = kwargs.get("query", "SELECT * FROM test")
            return executor.db.execute_query(query)

        executor.tool_manager.get_tool = MagicMock(return_value=db_tool)

        result = executor.execute_tool("db_tool", {"query": "SELECT * FROM players"})

        assert result == [{"id": 1, "name": "Test"}]
        mock_db.execute_query.assert_called_once_with("SELECT * FROM players")


class TestToolExecutorIntegration:
    """Test ToolExecutor integration with actual tools"""

    @patch("tool_executor.StatsToolManager")
    def test_integration_with_stats_tools(self, mock_tool_manager_class):
        """Test integration with StatsToolManager"""
        mock_db = MagicMock()
        mock_tool_manager = MagicMock()
        mock_tool_manager_class.return_value = mock_tool_manager

        executor = ToolExecutor(mock_db)

        # Verify StatsToolManager was initialized with db
        mock_tool_manager_class.assert_called_once_with(mock_db)
        assert executor.tool_manager == mock_tool_manager

    def test_error_handling_chain(self):
        """Test error handling through the execution chain"""
        mock_db = MagicMock()
        executor = ToolExecutor(mock_db)

        # Create a chain of errors
        errors = [
            ValueError("Invalid parameter"),
            TypeError("Wrong type"),
            RuntimeError("Runtime error"),
        ]

        for error in errors:
            mock_tool = MagicMock(side_effect=error)
            executor.tool_manager.get_tool = MagicMock(return_value=mock_tool)

            result = executor.execute_tool("error_tool", {})

            assert "error" in result
            assert str(error) in result["error"]

    def test_tool_parameter_validation(self):
        """Test parameter validation for tools"""
        mock_db = MagicMock()
        executor = ToolExecutor(mock_db)

        # Mock a tool that validates parameters
        def validated_tool(**kwargs):
            required = ["param1", "param2"]
            for param in required:
                if param not in kwargs:
                    raise ValueError(f"Missing required parameter: {param}")
            return {"success": True}

        executor.tool_manager.get_tool = MagicMock(return_value=validated_tool)

        # Test with missing parameters
        result = executor.execute_tool("validated_tool", {"param1": "value"})
        assert "error" in result
        assert "param2" in result["error"]

        # Test with all parameters
        result = executor.execute_tool("validated_tool", {"param1": "a", "param2": "b"})
        assert result == {"success": True}
