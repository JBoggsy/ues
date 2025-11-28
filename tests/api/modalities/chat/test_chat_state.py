"""Integration tests for GET /chat/state endpoint."""

from datetime import datetime, timezone


class TestGetChatState:
    """Tests for GET /chat/state endpoint."""

    def test_returns_correct_structure(self, client_with_engine):
        """Test that GET /chat/state returns response with correct structure."""
        client, engine = client_with_engine
        
        response = client.get("/chat/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "modality_type" in data
        assert data["modality_type"] == "chat"
        assert "current_time" in data
        assert "messages" in data
        assert "conversations" in data
        assert "total_message_count" in data
        assert "conversation_count" in data
        assert "max_history_size" in data

    def test_returns_empty_state_initially(self, client_with_engine):
        """Test that state has no messages when no chat messages sent."""
        client, engine = client_with_engine
        
        response = client.get("/chat/state")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["messages"] == []
        assert data["conversations"] == {}
        assert data["total_message_count"] == 0
        assert data["conversation_count"] == 0

    def test_reflects_sent_user_message(self, client_with_engine):
        """Test that state includes user message after it's sent."""
        client, engine = client_with_engine
        
        send_response = client.post(
            "/chat/send",
            json={
                "role": "user",
                "content": "Hello, assistant!",
                "conversation_id": "default",
            },
        )
        assert send_response.status_code == 200
        
        state_response = client.get("/chat/state")
        assert state_response.status_code == 200
        
        data = state_response.json()
        assert data["total_message_count"] == 1
        assert len(data["messages"]) == 1
        
        message = data["messages"][0]
        assert message["role"] == "user"
        assert message["content"] == "Hello, assistant!"
        assert message["conversation_id"] == "default"

    def test_reflects_sent_assistant_message(self, client_with_engine):
        """Test that state includes assistant message after it's sent."""
        client, engine = client_with_engine
        
        send_response = client.post(
            "/chat/send",
            json={
                "role": "assistant",
                "content": "Hello! How can I help you?",
                "conversation_id": "default",
            },
        )
        assert send_response.status_code == 200
        
        state_response = client.get("/chat/state")
        assert state_response.status_code == 200
        
        data = state_response.json()
        assert data["total_message_count"] == 1
        
        message = data["messages"][0]
        assert message["role"] == "assistant"
        assert message["content"] == "Hello! How can I help you?"

    def test_includes_conversation_metadata(self, client_with_engine):
        """Test that state includes conversation metadata."""
        client, engine = client_with_engine
        
        client.post(
            "/chat/send",
            json={"role": "user", "content": "First message", "conversation_id": "test-conv"},
        )
        client.post(
            "/chat/send",
            json={"role": "assistant", "content": "Response", "conversation_id": "test-conv"},
        )
        
        state_response = client.get("/chat/state")
        data = state_response.json()
        
        assert "test-conv" in data["conversations"]
        conv_meta = data["conversations"]["test-conv"]
        
        assert conv_meta["conversation_id"] == "test-conv"
        assert conv_meta["message_count"] == 2
        assert "created_at" in conv_meta
        assert "last_message_at" in conv_meta
        assert set(conv_meta["participant_roles"]) == {"user", "assistant"}

    def test_current_time_matches_simulator_time(self, client_with_engine):
        """Test that state's current_time matches simulator time."""
        client, engine = client_with_engine
        
        initial_time = engine.environment.time_state.current_time
        
        state_response = client.get("/chat/state")
        data = state_response.json()
        
        state_time = datetime.fromisoformat(data["current_time"].replace("Z", "+00:00"))
        
        assert abs((state_time - initial_time).total_seconds()) < 1
