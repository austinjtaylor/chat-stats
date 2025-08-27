"""
Test Stats Chat System module functionality.
Tests the main orchestrator that coordinates all system components.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, List, Any, Tuple

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from stats_chat_system import StatsChatSystem
from sql_database import SQLDatabase
from stats_processor import StatsProcessor
from stats_tools import StatsToolManager
from ai_generator import AIGenerator
from session_manager import SessionManager


class TestStatsChatSystem:
    """Test StatsChatSystem class functionality"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = Mock()
        config.ANTHROPIC_API_KEY = "test-api-key"
        config.ANTHROPIC_MODEL = "claude-3-5-sonnet"
        config.MAX_HISTORY = 5
        return config
    
    @pytest.fixture
    def mock_db(self):
        """Mock database"""
        return Mock(spec=SQLDatabase)
    
    @pytest.fixture
    def mock_stats_processor(self):
        """Mock stats processor"""
        return Mock(spec=StatsProcessor)
    
    @pytest.fixture
    def mock_tool_manager(self):
        """Mock tool manager"""
        mock = Mock(spec=StatsToolManager)
        mock.get_tool_schemas.return_value = [
            {
                "name": "get_player_stats",
                "description": "Get player statistics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "player_name": {"type": "string"}
                    }
                }
            }
        ]
        return mock
    
    @pytest.fixture
    def mock_ai_generator(self):
        """Mock AI generator"""
        return Mock(spec=AIGenerator)
    
    @pytest.fixture
    def mock_session_manager(self):
        """Mock session manager"""
        return Mock(spec=SessionManager)
    
    @pytest.fixture
    def chat_system(self, mock_config):
        """StatsChatSystem instance with mocked dependencies"""
        with patch('stats_chat_system.get_db') as mock_get_db, \
             patch('stats_chat_system.StatsProcessor') as mock_processor_class, \
             patch('stats_chat_system.StatsToolManager') as mock_tool_class, \
             patch('stats_chat_system.AIGenerator') as mock_ai_class, \
             patch('stats_chat_system.SessionManager') as mock_session_class:
            
            # Setup mocks
            mock_db = Mock(spec=SQLDatabase)
            mock_get_db.return_value = mock_db
            
            mock_processor = Mock(spec=StatsProcessor)
            mock_processor_class.return_value = mock_processor
            
            mock_tool_manager = Mock(spec=StatsToolManager)
            mock_tool_manager.get_tool_schemas.return_value = []
            mock_tool_class.return_value = mock_tool_manager
            
            mock_ai_gen = Mock(spec=AIGenerator)
            mock_ai_class.return_value = mock_ai_gen
            
            mock_session_mgr = Mock(spec=SessionManager)
            mock_session_class.return_value = mock_session_mgr
            
            system = StatsChatSystem(mock_config)
            
            # Store mocks for easy access
            system._mock_db = mock_db
            system._mock_processor = mock_processor
            system._mock_tool_manager = mock_tool_manager
            system._mock_ai_generator = mock_ai_gen
            system._mock_session_manager = mock_session_mgr
            
            return system
    
    def test_init(self, mock_config, chat_system):
        """Test StatsChatSystem initialization"""
        assert chat_system.config is mock_config
        assert hasattr(chat_system, 'db')
        assert hasattr(chat_system, 'stats_processor')
        assert hasattr(chat_system, 'tool_manager')
        assert hasattr(chat_system, 'ai_generator')
        assert hasattr(chat_system, 'session_manager')
    
    def test_init_with_defaults(self, mock_config):
        """Test initialization with default components"""
        with patch('stats_chat_system.get_db') as mock_get_db:
            mock_get_db.return_value = Mock(spec=SQLDatabase)
            
            system = StatsChatSystem(mock_config)
            
            # Verify components are initialized
            assert system.db is not None
            assert system.stats_processor is not None
            assert system.tool_manager is not None
            assert system.ai_generator is not None
            assert system.session_manager is not None


class TestQueryProcessing:
    """Test query processing functionality"""
    
    @pytest.fixture
    def chat_system_with_mocks(self, mock_config):
        """Chat system with detailed mocks for query testing"""
        with patch('stats_chat_system.get_db') as mock_get_db:
            mock_db = Mock(spec=SQLDatabase)
            mock_get_db.return_value = mock_db
            
            system = StatsChatSystem(mock_config)
            
            # Replace components with mocks
            system.tool_manager = Mock(spec=StatsToolManager)
            system.ai_generator = Mock(spec=AIGenerator)
            system.session_manager = Mock(spec=SessionManager)
            
            return system
    
    def test_query_without_session(self, chat_system_with_mocks):
        """Test querying without a session ID"""
        # Setup mocks
        chat_system_with_mocks.session_manager.get_history.return_value = []
        chat_system_with_mocks.tool_manager.get_tool_schemas.return_value = [
            {
                "name": "get_player_stats",
                "description": "Get player stats",
                "parameters": {"type": "object"}
            }
        ]
        chat_system_with_mocks.ai_generator.generate_response.return_value = (
            "LeBron James averages 25.2 points per game this season.",
            [{"source": "player_stats", "data": {"player": "LeBron James"}}]
        )
        
        # Execute query
        response, sources = chat_system_with_mocks.query(
            "What are LeBron James' stats?"
        )
        
        # Verify results
        assert response == "LeBron James averages 25.2 points per game this season."
        assert len(sources) == 1
        assert sources[0]["source"] == "player_stats"
        
        # Verify session manager was called
        chat_system_with_mocks.session_manager.add_message.assert_called()
        
    def test_query_with_session(self, chat_system_with_mocks):
        """Test querying with a session ID"""
        # Setup session history
        mock_history = [
            {
                "role": "user",
                "content": "Who is the best player?"
            },
            {
                "role": "assistant", 
                "content": "Many consider LeBron James one of the best."
            }
        ]
        chat_system_with_mocks.session_manager.get_history.return_value = mock_history
        
        # Setup AI response
        chat_system_with_mocks.tool_manager.get_tool_schemas.return_value = []
        chat_system_with_mocks.ai_generator.generate_response.return_value = (
            "Based on our previous discussion about LeBron, he averages 25.2 PPG.",
            []
        )
        
        # Execute query with session
        response, sources = chat_system_with_mocks.query(
            "What are his current stats?", 
            session_id="test-session"
        )
        
        # Verify session was used
        chat_system_with_mocks.session_manager.get_history.assert_called_with("test-session")
        
        # Verify history was passed to AI generator
        ai_call = chat_system_with_mocks.ai_generator.generate_response.call_args
        assert mock_history in ai_call[0] or mock_history in ai_call[1].values()
        
    def test_query_tool_integration(self, chat_system_with_mocks):
        """Test query with tool integration"""
        # Setup tool schemas
        tool_schemas = [
            {
                "name": "get_player_stats",
                "description": "Get player statistics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "player_name": {"type": "string"}
                    }
                }
            }
        ]
        chat_system_with_mocks.tool_manager.get_tool_schemas.return_value = tool_schemas
        
        # Setup AI response
        chat_system_with_mocks.ai_generator.generate_response.return_value = (
            "LeBron James is averaging 25.2 points, 7.8 rebounds, and 6.9 assists per game.",
            [{"tool": "get_player_stats", "result": {"points": 25.2}}]
        )
        
        # Execute query
        response, sources = chat_system_with_mocks.query(
            "How is LeBron James performing this season?"
        )
        
        # Verify tools were provided to AI
        ai_call = chat_system_with_mocks.ai_generator.generate_response.call_args
        assert tool_schemas in ai_call[0] or any(tool_schemas == v for v in ai_call[1].values())
        
        # Verify response includes tool results
        assert "25.2 points" in response
        assert len(sources) == 1
        
    def test_query_error_handling(self, chat_system_with_mocks):
        """Test query error handling"""
        # Setup AI generator to raise exception
        chat_system_with_mocks.ai_generator.generate_response.side_effect = Exception(
            "API error"
        )
        
        # Query should handle error gracefully
        response, sources = chat_system_with_mocks.query(
            "What are the Lakers' stats?"
        )
        
        # Should return error response
        assert "error" in response.lower() or "sorry" in response.lower()
        assert sources == []
        
    def test_query_session_error_handling(self, chat_system_with_mocks):
        """Test query with session manager errors"""
        # Setup session manager to raise exception
        chat_system_with_mocks.session_manager.get_history.side_effect = Exception(
            "Session error"
        )
        
        # Should still process query without history
        chat_system_with_mocks.ai_generator.generate_response.return_value = (
            "Response without history", []
        )
        
        response, sources = chat_system_with_mocks.query(
            "Test query", 
            session_id="test-session"
        )
        
        # Should get response despite session error
        assert response == "Response without history"
        
        # AI should be called with empty history
        ai_call = chat_system_with_mocks.ai_generator.generate_response.call_args
        # History should be None or empty
        history_param = ai_call[1].get('history', [])
        assert history_param is None or len(history_param) == 0


class TestAnalytics:
    """Test analytics functionality"""
    
    def test_get_database_stats(self, chat_system):
        """Test getting database statistics"""
        # Mock database queries for stats
        chat_system._mock_db.execute_query.side_effect = [
            [{"count": 500}],  # Players count
            [{"count": 30}],   # Teams count  
            [{"count": 1230}], # Games count
            [{"player_name": "LeBron James", "ppg": 25.2}]  # Top scorer
        ]
        
        stats = chat_system.get_database_stats()
        
        assert stats["total_players"] == 500
        assert stats["total_teams"] == 30
        assert stats["total_games"] == 1230
        assert "top_scorers" in stats
        
        # Verify correct queries were made
        assert chat_system._mock_db.execute_query.call_count == 4
        
    def test_get_database_stats_empty_db(self, chat_system):
        """Test getting stats from empty database"""
        chat_system._mock_db.execute_query.return_value = [{"count": 0}]
        
        stats = chat_system.get_database_stats()
        
        # Should handle empty database gracefully
        assert stats["total_players"] == 0
        assert stats["total_teams"] == 0
        assert stats["total_games"] == 0
        
    def test_get_popular_queries(self, chat_system):
        """Test getting popular query analytics"""
        # Mock session manager analytics
        chat_system._mock_session_manager.get_analytics.return_value = {
            "total_sessions": 150,
            "total_queries": 850,
            "popular_topics": ["LeBron James", "Lakers", "player stats"]
        }
        
        analytics = chat_system.get_popular_queries()
        
        assert analytics["total_sessions"] == 150
        assert analytics["total_queries"] == 850
        assert "LeBron James" in analytics["popular_topics"]
        
    def test_get_system_health(self, chat_system):
        """Test system health check"""
        # Mock successful component checks
        chat_system._mock_db.execute_query.return_value = [{"test": "ok"}]
        
        health = chat_system.get_system_health()
        
        assert "database" in health
        assert health["database"]["status"] == "healthy"
        assert "timestamp" in health
        
    def test_get_system_health_database_error(self, chat_system):
        """Test system health with database error"""
        # Mock database error
        chat_system._mock_db.execute_query.side_effect = Exception("Connection failed")
        
        health = chat_system.get_system_health()
        
        assert health["database"]["status"] == "unhealthy"
        assert "error" in health["database"]


class TestSessionIntegration:
    """Test session management integration"""
    
    def test_session_creation(self, chat_system):
        """Test automatic session creation"""
        chat_system._mock_session_manager.get_history.return_value = []
        chat_system._mock_ai_generator.generate_response.return_value = ("Response", [])
        
        response, sources = chat_system.query("Test query")
        
        # Should add messages to session
        assert chat_system._mock_session_manager.add_message.call_count == 2
        
        # Check user message was added
        user_call = chat_system._mock_session_manager.add_message.call_args_list[0]
        assert user_call[0][1]["role"] == "user"
        assert user_call[0][1]["content"] == "Test query"
        
        # Check assistant message was added
        assistant_call = chat_system._mock_session_manager.add_message.call_args_list[1]
        assert assistant_call[0][1]["role"] == "assistant"
        assert assistant_call[0][1]["content"] == "Response"
        
    def test_session_context_preservation(self, chat_system):
        """Test that session context is preserved across queries"""
        # Setup session history
        mock_history = [
            {"role": "user", "content": "Who is LeBron James?"},
            {"role": "assistant", "content": "LeBron James is an NBA player..."}
        ]
        chat_system._mock_session_manager.get_history.return_value = mock_history
        chat_system._mock_ai_generator.generate_response.return_value = (
            "LeBron is currently averaging 25.2 PPG", []
        )
        
        # Make follow-up query
        response, sources = chat_system.query(
            "What are his current stats?", 
            session_id="test-session"
        )
        
        # Verify history was used
        ai_call = chat_system._mock_ai_generator.generate_response.call_args
        # Should include history in the call
        assert any("LeBron James is an NBA player" in str(arg) for arg in ai_call[0]) or \
               any("LeBron James is an NBA player" in str(v) for v in ai_call[1].values())
        
    def test_session_history_limits(self, chat_system):
        """Test that session history respects configured limits"""
        # Create long history that exceeds limit
        long_history = []
        for i in range(20):  # More than MAX_HISTORY (5)
            long_history.extend([
                {"role": "user", "content": f"Question {i}"},
                {"role": "assistant", "content": f"Answer {i}"}
            ])
        
        chat_system._mock_session_manager.get_history.return_value = long_history
        chat_system._mock_ai_generator.generate_response.return_value = ("Response", [])
        
        response, sources = chat_system.query("New query", session_id="test-session")
        
        # Session manager should handle history limiting
        chat_system._mock_session_manager.get_history.assert_called_with("test-session")


class TestToolManagerIntegration:
    """Test tool manager integration"""
    
    def test_tool_schemas_provided_to_ai(self, chat_system):
        """Test that tool schemas are provided to AI generator"""
        # Setup mock tool schemas
        mock_schemas = [
            {
                "name": "get_player_stats",
                "description": "Get player statistics",
                "parameters": {"type": "object"}
            },
            {
                "name": "get_team_stats", 
                "description": "Get team statistics",
                "parameters": {"type": "object"}
            }
        ]
        chat_system._mock_tool_manager.get_tool_schemas.return_value = mock_schemas
        chat_system._mock_ai_generator.generate_response.return_value = ("Response", [])
        
        response, sources = chat_system.query("Test query")
        
        # Verify tools were provided to AI
        ai_call = chat_system._mock_ai_generator.generate_response.call_args
        assert mock_schemas in ai_call[0] or mock_schemas in ai_call[1].values()
        
    def test_tool_results_in_sources(self, chat_system):
        """Test that tool results are included in response sources"""
        chat_system._mock_ai_generator.generate_response.return_value = (
            "Test response",
            [
                {"tool": "get_player_stats", "result": {"player": "LeBron", "ppg": 25.2}},
                {"tool": "get_team_stats", "result": {"team": "Lakers", "wins": 45}}
            ]
        )
        
        response, sources = chat_system.query("Test query")
        
        # Sources should include tool results
        assert len(sources) == 2
        assert sources[0]["tool"] == "get_player_stats"
        assert sources[1]["tool"] == "get_team_stats"
        
    def test_tool_error_handling(self, chat_system):
        """Test handling of tool execution errors"""
        # AI generator returns error in sources
        chat_system._mock_ai_generator.generate_response.return_value = (
            "I encountered an error retrieving the statistics.",
            [{"error": "Database connection failed", "tool": "get_player_stats"}]
        )
        
        response, sources = chat_system.query("Get player stats")
        
        # Should handle tool errors gracefully
        assert "error" in response.lower()
        assert len(sources) == 1
        assert "error" in sources[0]


class TestConfigurationHandling:
    """Test configuration handling"""
    
    def test_missing_api_key(self):
        """Test handling of missing API key"""
        bad_config = Mock()
        bad_config.ANTHROPIC_API_KEY = ""
        bad_config.ANTHROPIC_MODEL = "claude-3-5-sonnet"
        bad_config.MAX_HISTORY = 5
        
        with patch('stats_chat_system.get_db'):
            with pytest.raises((ValueError, Exception)):
                StatsChatSystem(bad_config)
                
    def test_invalid_model_name(self):
        """Test handling of invalid model name"""
        bad_config = Mock()
        bad_config.ANTHROPIC_API_KEY = "test-key"
        bad_config.ANTHROPIC_MODEL = "invalid-model"
        bad_config.MAX_HISTORY = 5
        
        with patch('stats_chat_system.get_db'):
            # Should initialize but may fail on first query
            system = StatsChatSystem(bad_config)
            assert system.config.ANTHROPIC_MODEL == "invalid-model"
            
    def test_config_validation(self, mock_config):
        """Test configuration validation"""
        # Test with valid config
        with patch('stats_chat_system.get_db'):
            system = StatsChatSystem(mock_config)
            assert system.config is mock_config
            
        # Test with missing required config
        incomplete_config = Mock()
        incomplete_config.ANTHROPIC_API_KEY = "test-key"
        # Missing ANTHROPIC_MODEL
        
        with patch('stats_chat_system.get_db'):
            with pytest.raises(AttributeError):
                StatsChatSystem(incomplete_config)


class TestPerformanceOptimization:
    """Test performance-related functionality"""
    
    def test_query_caching(self, chat_system):
        """Test query result caching if implemented"""
        chat_system._mock_ai_generator.generate_response.return_value = ("Cached response", [])
        
        # Make same query twice
        query = "What are LeBron James' stats?"
        response1, sources1 = chat_system.query(query)
        response2, sources2 = chat_system.query(query)
        
        # If caching is implemented, AI should only be called once
        # Otherwise, both calls should work correctly
        assert response1 == "Cached response"
        assert response2 == "Cached response"
        
    def test_concurrent_queries(self, chat_system):
        """Test handling of concurrent queries"""
        chat_system._mock_ai_generator.generate_response.return_value = ("Response", [])
        
        # Simulate concurrent access (basic test)
        response1, sources1 = chat_system.query("Query 1", session_id="session1")
        response2, sources2 = chat_system.query("Query 2", session_id="session2")
        
        # Both queries should complete successfully
        assert response1 == "Response"
        assert response2 == "Response"
        
        # Should handle different sessions properly
        assert chat_system._mock_session_manager.add_message.call_count >= 4  # 2 queries × 2 messages each
        
    def test_memory_usage(self, chat_system):
        """Test memory usage with large responses"""
        # Create large response
        large_response = "Large response data " * 1000
        large_sources = [{"data": "Large data " * 100} for _ in range(100)]
        
        chat_system._mock_ai_generator.generate_response.return_value = (large_response, large_sources)
        
        # Should handle large responses without issues
        response, sources = chat_system.query("Large query")
        
        assert len(response) > 10000  # Verify we got the large response
        assert len(sources) == 100    # Verify we got all sources