"""
Test Session Manager module functionality.
Tests session management, message storage, and conversation history.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from session_manager import SessionManager, Message


class TestMessage:
    """Test Message class functionality"""
    
    def test_message_creation(self):
        """Test creating a Message instance"""
        message = Message(role="user", content="Hello, world!")
        
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert isinstance(message.timestamp, datetime)
        
    def test_message_creation_with_timestamp(self):
        """Test creating a Message with custom timestamp"""
        custom_time = datetime(2024, 1, 15, 12, 0, 0)
        message = Message(
            role="assistant", 
            content="Hello back!",
            timestamp=custom_time
        )
        
        assert message.timestamp == custom_time
        
    def test_message_dict_conversion(self):
        """Test converting Message to dictionary"""
        message = Message(role="user", content="Test message")
        message_dict = message.to_dict()
        
        assert message_dict["role"] == "user"
        assert message_dict["content"] == "Test message"
        assert "timestamp" in message_dict
        assert isinstance(message_dict["timestamp"], str)
        
    def test_message_from_dict(self):
        """Test creating Message from dictionary"""
        message_dict = {
            "role": "assistant",
            "content": "Test response",
            "timestamp": "2024-01-15T12:00:00"
        }
        
        message = Message.from_dict(message_dict)
        
        assert message.role == "assistant"
        assert message.content == "Test response"
        assert isinstance(message.timestamp, datetime)
        
    def test_message_validation(self):
        """Test message validation"""
        # Valid roles
        valid_message = Message(role="user", content="Test")
        assert valid_message.role == "user"
        
        valid_assistant = Message(role="assistant", content="Response")
        assert valid_assistant.role == "assistant"
        
        # Invalid role should be handled by pydantic validation
        with pytest.raises(ValueError):
            Message(role="invalid_role", content="Test")
            
    def test_message_empty_content(self):
        """Test message with empty content"""
        message = Message(role="user", content="")
        assert message.content == ""
        
    def test_message_long_content(self):
        """Test message with very long content"""
        long_content = "A" * 10000
        message = Message(role="user", content=long_content)
        assert len(message.content) == 10000


class TestSessionManager:
    """Test SessionManager class functionality"""
    
    @pytest.fixture
    def session_manager(self):
        """SessionManager instance for testing"""
        return SessionManager(max_history=5)
    
    def test_init_default_max_history(self):
        """Test SessionManager initialization with default max_history"""
        manager = SessionManager()
        assert manager.max_history == 10  # Default value
        assert manager.sessions == {}
        
    def test_init_custom_max_history(self):
        """Test SessionManager initialization with custom max_history"""
        manager = SessionManager(max_history=3)
        assert manager.max_history == 3
        
    def test_create_session(self, session_manager):
        """Test creating a new session"""
        session_id = "test-session-1"
        
        # Session shouldn't exist initially
        assert session_id not in session_manager.sessions
        
        # Add a message (should create session)
        message = Message(role="user", content="Hello")
        session_manager.add_message(session_id, message)
        
        # Session should now exist
        assert session_id in session_manager.sessions
        assert len(session_manager.sessions[session_id]) == 1
        
    def test_add_message_dict(self, session_manager):
        """Test adding message as dictionary"""
        session_id = "test-session-2"
        message_dict = {
            "role": "user",
            "content": "Test message"
        }
        
        session_manager.add_message(session_id, message_dict)
        
        # Verify message was added
        messages = session_manager.get_history(session_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test message"
        
    def test_add_message_object(self, session_manager):
        """Test adding message as Message object"""
        session_id = "test-session-3"
        message = Message(role="assistant", content="Test response")
        
        session_manager.add_message(session_id, message)
        
        # Verify message was added
        messages = session_manager.get_history(session_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "Test response"
        
    def test_get_history_empty_session(self, session_manager):
        """Test getting history from non-existent session"""
        messages = session_manager.get_history("non-existent")
        assert messages == []
        
    def test_get_history_with_messages(self, session_manager):
        """Test getting history from session with messages"""
        session_id = "test-session-4"
        
        # Add multiple messages
        messages_to_add = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm doing well, thanks!"}
        ]
        
        for msg in messages_to_add:
            session_manager.add_message(session_id, msg)
            
        # Get history
        history = session_manager.get_history(session_id)
        
        assert len(history) == 4
        assert history[0]["content"] == "Hello"
        assert history[-1]["content"] == "I'm doing well, thanks!"
        
    def test_max_history_enforcement(self, session_manager):
        """Test that max_history limit is enforced"""
        session_id = "test-session-5"
        
        # Add more messages than max_history allows
        for i in range(10):  # More than max_history=5
            session_manager.add_message(session_id, {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}"
            })
            
        # Should only keep last 5 messages
        history = session_manager.get_history(session_id)
        assert len(history) == 5
        
        # Should be the most recent messages
        assert history[0]["content"] == "Message 5"  # 6th message (index 5)
        assert history[-1]["content"] == "Message 9"  # 10th message (index 9)
        
    def test_max_history_zero(self):
        """Test SessionManager with max_history=0"""
        manager = SessionManager(max_history=0)
        session_id = "test-session"
        
        # Add messages
        manager.add_message(session_id, {"role": "user", "content": "Test"})
        
        # Should keep no history
        history = manager.get_history(session_id)
        assert len(history) == 0
        
    def test_multiple_sessions(self, session_manager):
        """Test managing multiple sessions simultaneously"""
        session1 = "session-1"
        session2 = "session-2"
        
        # Add different messages to each session
        session_manager.add_message(session1, {
            "role": "user", "content": "Session 1 message"
        })
        session_manager.add_message(session2, {
            "role": "user", "content": "Session 2 message"
        })
        
        # Verify sessions are separate
        history1 = session_manager.get_history(session1)
        history2 = session_manager.get_history(session2)
        
        assert len(history1) == 1
        assert len(history2) == 1
        assert history1[0]["content"] == "Session 1 message"
        assert history2[0]["content"] == "Session 2 message"
        
    def test_session_cleanup(self, session_manager):
        """Test session cleanup functionality"""
        session_id = "cleanup-test"
        
        # Add messages
        session_manager.add_message(session_id, {
            "role": "user", "content": "Test message"
        })
        
        # Clear specific session
        session_manager.clear_session(session_id)
        
        # Session should be empty but still exist
        history = session_manager.get_history(session_id)
        assert history == []
        
    def test_clear_all_sessions(self, session_manager):
        """Test clearing all sessions"""
        # Create multiple sessions
        for i in range(3):
            session_manager.add_message(f"session-{i}", {
                "role": "user", "content": f"Message {i}"
            })
            
        # Verify sessions exist
        assert len(session_manager.sessions) == 3
        
        # Clear all sessions
        session_manager.clear_all_sessions()
        
        # All sessions should be gone
        assert len(session_manager.sessions) == 0
        
    def test_get_session_info(self, session_manager):
        """Test getting session information"""
        session_id = "info-test"
        
        # Add messages at different times
        session_manager.add_message(session_id, {
            "role": "user", "content": "First message"
        })
        session_manager.add_message(session_id, {
            "role": "assistant", "content": "Response"
        })
        
        # Get session info
        info = session_manager.get_session_info(session_id)
        
        assert info["session_id"] == session_id
        assert info["message_count"] == 2
        assert "created_at" in info
        assert "last_activity" in info
        
    def test_get_all_session_ids(self, session_manager):
        """Test getting all session IDs"""
        # Initially no sessions
        session_ids = session_manager.get_all_session_ids()
        assert session_ids == []
        
        # Create some sessions
        test_sessions = ["session-a", "session-b", "session-c"]
        for session_id in test_sessions:
            session_manager.add_message(session_id, {
                "role": "user", "content": "Test"
            })
            
        # Get all session IDs
        session_ids = session_manager.get_all_session_ids()
        assert len(session_ids) == 3
        for session_id in test_sessions:
            assert session_id in session_ids
            
    def test_session_statistics(self, session_manager):
        """Test getting session statistics"""
        # Create sessions with different message counts
        session_manager.add_message("session-1", {"role": "user", "content": "Msg"})
        
        for i in range(3):
            session_manager.add_message("session-2", {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}"
            })
            
        # Get statistics
        stats = session_manager.get_statistics()
        
        assert stats["total_sessions"] == 2
        assert stats["total_messages"] == 4
        assert stats["average_messages_per_session"] == 2.0
        
    def test_message_search(self, session_manager):
        """Test searching for messages across sessions"""
        # Add messages to different sessions
        session_manager.add_message("session-1", {
            "role": "user", "content": "Tell me about basketball"
        })
        session_manager.add_message("session-1", {
            "role": "assistant", "content": "Basketball is a great sport"
        })
        session_manager.add_message("session-2", {
            "role": "user", "content": "What about football?"
        })
        
        # Search for basketball-related messages
        results = session_manager.search_messages("basketball")
        
        assert len(results) == 2  # User question and assistant response
        assert any("Tell me about basketball" in result["content"] for result in results)
        assert any("Basketball is a great sport" in result["content"] for result in results)


class TestMessageValidation:
    """Test message validation and error handling"""
    
    def test_invalid_message_role(self, session_manager):
        """Test handling invalid message roles"""
        session_id = "validation-test"
        
        # Try to add message with invalid role
        with pytest.raises((ValueError, Exception)):
            session_manager.add_message(session_id, {
                "role": "invalid",
                "content": "Test message"
            })
            
    def test_missing_message_content(self, session_manager):
        """Test handling messages with missing content"""
        session_id = "missing-content-test"
        
        # Message without content should be handled gracefully or raise error
        with pytest.raises((ValueError, KeyError)):
            session_manager.add_message(session_id, {
                "role": "user"
                # Missing content
            })
            
    def test_none_message(self, session_manager):
        """Test handling None message"""
        session_id = "none-test"
        
        with pytest.raises((ValueError, TypeError)):
            session_manager.add_message(session_id, None)
            
    def test_empty_session_id(self, session_manager):
        """Test handling empty session ID"""
        with pytest.raises((ValueError, Exception)):
            session_manager.add_message("", {
                "role": "user",
                "content": "Test message"
            })
            
    def test_none_session_id(self, session_manager):
        """Test handling None session ID"""
        with pytest.raises((ValueError, TypeError)):
            session_manager.add_message(None, {
                "role": "user", 
                "content": "Test message"
            })


class TestConcurrency:
    """Test concurrent access to sessions"""
    
    def test_concurrent_message_addition(self, session_manager):
        """Test adding messages concurrently to same session"""
        session_id = "concurrent-test"
        
        # Simulate concurrent access (basic test)
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)
        ]
        
        # Add messages rapidly
        for msg in messages:
            session_manager.add_message(session_id, msg)
            
        # All messages should be added
        history = session_manager.get_history(session_id)
        assert len(history) == 5  # Limited by max_history
        
    def test_concurrent_session_creation(self, session_manager):
        """Test creating multiple sessions concurrently"""
        # Create multiple sessions rapidly
        for i in range(5):
            session_manager.add_message(f"concurrent-session-{i}", {
                "role": "user",
                "content": f"Initial message {i}"
            })
            
        # All sessions should exist
        session_ids = session_manager.get_all_session_ids()
        assert len(session_ids) == 5


class TestMemoryManagement:
    """Test memory management and performance"""
    
    def test_large_message_content(self, session_manager):
        """Test handling very large message content"""
        session_id = "large-message-test"
        
        # Create large message content
        large_content = "A" * 100000  # 100KB message
        
        session_manager.add_message(session_id, {
            "role": "user",
            "content": large_content
        })
        
        # Should handle large content
        history = session_manager.get_history(session_id)
        assert len(history) == 1
        assert len(history[0]["content"]) == 100000
        
    def test_many_sessions(self, session_manager):
        """Test handling many sessions"""
        # Create many sessions
        num_sessions = 100
        for i in range(num_sessions):
            session_manager.add_message(f"session-{i:03d}", {
                "role": "user",
                "content": f"Message in session {i}"
            })
            
        # All sessions should be accessible
        session_ids = session_manager.get_all_session_ids()
        assert len(session_ids) == num_sessions
        
        # Random access should work
        test_session = "session-050"
        history = session_manager.get_history(test_session)
        assert len(history) == 1
        assert "Message in session 50" in history[0]["content"]
        
    def test_session_memory_cleanup(self):
        """Test that memory is properly cleaned up"""
        manager = SessionManager(max_history=2)
        session_id = "memory-test"
        
        # Add many messages to trigger cleanup
        for i in range(100):
            manager.add_message(session_id, {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}"
            })
            
        # Should only keep recent messages
        history = manager.get_history(session_id)
        assert len(history) == 2
        
        # Should be the most recent messages
        assert history[0]["content"] == "Message 98"
        assert history[1]["content"] == "Message 99"


class TestPersistence:
    """Test session persistence functionality"""
    
    def test_export_session(self, session_manager):
        """Test exporting session to JSON"""
        session_id = "export-test"
        
        # Add some messages
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        for msg in messages:
            session_manager.add_message(session_id, msg)
            
        # Export session
        exported_data = session_manager.export_session(session_id)
        
        assert "session_id" in exported_data
        assert "messages" in exported_data
        assert len(exported_data["messages"]) == 3
        assert exported_data["messages"][0]["content"] == "Hello"
        
    def test_import_session(self, session_manager):
        """Test importing session from JSON"""
        session_data = {
            "session_id": "imported-session",
            "messages": [
                {"role": "user", "content": "Imported message 1"},
                {"role": "assistant", "content": "Imported response 1"}
            ]
        }
        
        # Import session
        session_manager.import_session(session_data)
        
        # Verify session was imported
        history = session_manager.get_history("imported-session")
        assert len(history) == 2
        assert history[0]["content"] == "Imported message 1"
        assert history[1]["content"] == "Imported response 1"
        
    def test_export_all_sessions(self, session_manager):
        """Test exporting all sessions"""
        # Create multiple sessions
        for i in range(3):
            session_manager.add_message(f"export-session-{i}", {
                "role": "user",
                "content": f"Message {i}"
            })
            
        # Export all sessions
        all_sessions = session_manager.export_all_sessions()
        
        assert len(all_sessions) == 3
        assert all(session["session_id"].startswith("export-session-") for session in all_sessions)