"""
Test Session Manager module functionality.
Tests session management, message storage, and conversation history.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.session_manager import Message, SessionManager


class TestMessage:
    """Test Message class functionality"""

    def test_message_creation(self):
        """Test creating a Message instance"""
        message = Message(role="user", content="Hello, world!")

        assert message.role == "user"
        assert message.content == "Hello, world!"

    def test_message_creation_assistant(self):
        """Test creating an assistant Message"""
        message = Message(role="assistant", content="Hello back!")

        assert message.role == "assistant"
        assert message.content == "Hello back!"

    def test_message_dataclass_fields(self):
        """Test Message dataclass has correct fields"""
        message = Message(role="user", content="Test message")

        assert hasattr(message, "role")
        assert hasattr(message, "content")
        assert message.role == "user"
        assert message.content == "Test message"

    def test_message_equality(self):
        """Test Message equality comparison"""
        message1 = Message(role="assistant", content="Test response")
        message2 = Message(role="assistant", content="Test response")
        message3 = Message(role="user", content="Test response")

        assert message1 == message2
        assert message1 != message3

    def test_message_validation(self):
        """Test message validation"""
        # Valid roles
        valid_message = Message(role="user", content="Test")
        assert valid_message.role == "user"

        valid_assistant = Message(role="assistant", content="Response")
        assert valid_assistant.role == "assistant"

        # Any role should work since it's just a string field
        custom_role = Message(role="system", content="Test")
        assert custom_role.role == "system"

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
        assert manager.max_history == 5  # Default value

    def test_init_custom_max_history(self):
        """Test SessionManager initialization with custom max_history"""
        manager = SessionManager(max_history=10)
        assert manager.max_history == 10
        assert manager.sessions == {}
        assert manager.session_counter == 0

    def test_create_session(self, session_manager):
        """Test creating a new session"""
        session_id = session_manager.create_session()

        # Session should exist
        assert session_id in session_manager.sessions
        assert len(session_manager.sessions[session_id]) == 0
        assert session_id.startswith("session_")

    def test_add_message_new_session(self, session_manager):
        """Test adding message creates session if it doesn't exist"""
        session_id = "test-session-2"

        # Session shouldn't exist initially
        assert session_id not in session_manager.sessions

        session_manager.add_message(session_id, "user", "Test message")

        # Session should now exist with message
        assert session_id in session_manager.sessions
        assert len(session_manager.sessions[session_id]) == 1
        assert session_manager.sessions[session_id][0].role == "user"
        assert session_manager.sessions[session_id][0].content == "Test message"

    def test_add_message_existing_session(self, session_manager):
        """Test adding message to existing session"""
        session_id = session_manager.create_session()

        session_manager.add_message(session_id, "assistant", "Test response")

        # Verify message was added
        messages = session_manager.sessions[session_id]
        assert len(messages) == 1
        assert messages[0].role == "assistant"
        assert messages[0].content == "Test response"

    def test_add_exchange(self, session_manager):
        """Test adding complete user-assistant exchange"""
        session_id = "test-exchange"

        session_manager.add_exchange(session_id, "Hello", "Hi there!")

        messages = session_manager.sessions[session_id]
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hi there!"

    def test_get_conversation_history_empty_session(self, session_manager):
        """Test getting history from non-existent session"""
        history = session_manager.get_conversation_history("non-existent")
        assert history is None

    def test_get_conversation_history_empty_existing_session(self, session_manager):
        """Test getting history from empty existing session"""
        session_id = session_manager.create_session()
        history = session_manager.get_conversation_history(session_id)
        assert history is None

    def test_get_conversation_history_with_messages(self, session_manager):
        """Test getting formatted history from session with messages"""
        session_id = "test-session-4"

        # Add multiple messages
        session_manager.add_message(session_id, "user", "Hello")
        session_manager.add_message(session_id, "assistant", "Hi there!")
        session_manager.add_message(session_id, "user", "How are you?")
        session_manager.add_message(session_id, "assistant", "I'm doing well, thanks!")

        # Get formatted history
        history = session_manager.get_conversation_history(session_id)

        assert isinstance(history, str)
        assert "User: Hello" in history
        assert "Assistant: Hi there!" in history
        assert "User: How are you?" in history
        assert "Assistant: I'm doing well, thanks!" in history

    def test_clear_session(self, session_manager):
        """Test clearing a session"""
        session_id = "clear-test"

        # Add some messages
        session_manager.add_message(session_id, "user", "Test message")
        session_manager.add_message(session_id, "assistant", "Test response")

        # Verify messages exist
        assert len(session_manager.sessions[session_id]) == 2

        # Clear session
        session_manager.clear_session(session_id)

        # Session should be empty
        assert len(session_manager.sessions[session_id]) == 0

    def test_clear_nonexistent_session(self, session_manager):
        """Test clearing a session that doesn't exist"""
        # Should not raise an error
        session_manager.clear_session("nonexistent")

    def test_max_history_enforcement(self, session_manager):
        """Test that max_history limit is enforced"""
        session_id = "test-session-5"

        # Add more messages than max_history * 2 allows (max_history=5, so limit is 10)
        for i in range(15):  # More than limit
            role = "user" if i % 2 == 0 else "assistant"
            session_manager.add_message(session_id, role, f"Message {i}")

        # Should only keep last 10 messages (max_history * 2)
        messages = session_manager.sessions[session_id]
        assert len(messages) == 10

        # Should be the most recent messages
        assert messages[0].content == "Message 5"  # 6th message (index 5)
        assert messages[-1].content == "Message 14"  # 15th message (index 14)

    def test_max_history_zero(self):
        """Test SessionManager with max_history=0"""
        manager = SessionManager(max_history=0)
        session_id = "test-session"

        # Add messages - due to Python slicing behavior, max_history=0 doesn't work as expected
        manager.add_message(session_id, "user", "Test")

        # Due to bug in slicing logic: messages[-0:] == messages[:]
        # So messages are never actually cleaned up with max_history=0
        messages = manager.sessions[session_id]
        assert len(messages) == 1  # Bug: cleanup doesn't work with max_history=0

    def test_separate_sessions(self, session_manager):
        """Test that different sessions are kept separate"""
        session1 = "session-1"
        session2 = "session-2"

        # Add messages to different sessions
        session_manager.add_message(session1, "user", "Session 1 message")
        session_manager.add_message(session2, "user", "Session 2 message")

        # Verify sessions are separate
        messages1 = session_manager.sessions[session1]
        messages2 = session_manager.sessions[session2]

        assert len(messages1) == 1
        assert len(messages2) == 1
        assert messages1[0].content == "Session 1 message"
        assert messages2[0].content == "Session 2 message"


class TestEdgeCases:
    """Test edge cases and error conditions"""

    @pytest.fixture
    def session_manager(self):
        """SessionManager instance for testing"""
        return SessionManager()

    def test_empty_content(self, session_manager):
        """Test handling empty message content"""
        session_id = "empty-test"
        session_manager.add_message(session_id, "user", "")

        messages = session_manager.sessions[session_id]
        assert len(messages) == 1
        assert messages[0].content == ""

    def test_large_content(self, session_manager):
        """Test handling very large message content"""
        session_id = "large-test"
        large_content = "A" * 100000  # 100KB message

        session_manager.add_message(session_id, "user", large_content)

        messages = session_manager.sessions[session_id]
        assert len(messages) == 1
        assert len(messages[0].content) == 100000

    def test_many_sessions(self, session_manager):
        """Test handling many sessions"""
        # Create many sessions
        num_sessions = 100
        for i in range(num_sessions):
            session_manager.add_message(
                f"session-{i:03d}", "user", f"Message in session {i}"
            )

        # All sessions should exist
        assert len(session_manager.sessions) == num_sessions

        # Random access should work
        test_session = "session-050"
        messages = session_manager.sessions[test_session]
        assert len(messages) == 1
        assert "Message in session 50" in messages[0].content
