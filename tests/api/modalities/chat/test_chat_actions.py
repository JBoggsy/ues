"""Integration tests for chat action endpoints."""


class TestPostChatSend:
    """Tests for POST /chat/send endpoint."""

    def test_send_user_message_succeeds(self, client_with_engine):
        """Test sending a user message creates event successfully."""
        client, engine = client_with_engine
        
        response = client.post(
            "/chat/send",
            json={
                "role": "user",
                "content": "Hello, assistant!",
                "conversation_id": "default",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "event_id" in data
        assert "scheduled_time" in data
        assert data["modality"] == "chat"

    def test_send_assistant_message_succeeds(self, client_with_engine):
        """Test sending an assistant message creates event successfully."""
        client, engine = client_with_engine
        
        response = client.post(
            "/chat/send",
            json={
                "role": "assistant",
                "content": "Hello! How can I help you?",
                "conversation_id": "default",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["modality"] == "chat"
        assert "event_id" in data

    def test_send_with_custom_conversation_id(self, client_with_engine):
        """Test sending message to specific conversation."""
        client, engine = client_with_engine
        
        response = client.post(
            "/chat/send",
            json={
                "role": "user",
                "content": "Message in custom conversation",
                "conversation_id": "work-chat",
            },
        )
        
        assert response.status_code == 200
        
        state_response = client.get("/chat/state")
        data = state_response.json()
        
        assert "work-chat" in data["conversations"]
        messages = [m for m in data["messages"] if m["conversation_id"] == "work-chat"]
        assert len(messages) == 1

    def test_send_with_metadata(self, client_with_engine):
        """Test sending message with optional metadata."""
        client, engine = client_with_engine
        
        response = client.post(
            "/chat/send",
            json={
                "role": "assistant",
                "content": "Response with metadata",
                "conversation_id": "default",
                "metadata": {
                    "model": "gpt-4",
                    "tokens": 42,
                    "temperature": 0.7,
                },
            },
        )
        
        assert response.status_code == 200
        
        state_response = client.get("/chat/state")
        data = state_response.json()
        
        message = data["messages"][0]
        assert "metadata" in message
        assert message["metadata"]["model"] == "gpt-4"
        assert message["metadata"]["tokens"] == 42

    def test_send_multimodal_content(self, client_with_engine):
        """Test sending message with multimodal content (list of dicts)."""
        client, engine = client_with_engine
        
        response = client.post(
            "/chat/send",
            json={
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image",
                        "source": "url",
                        "url": "https://example.com/image.jpg",
                    },
                ],
                "conversation_id": "default",
            },
        )
        
        assert response.status_code == 200
        
        state_response = client.get("/chat/state")
        data = state_response.json()
        
        message = data["messages"][0]
        assert isinstance(message["content"], list)
        assert len(message["content"]) == 2
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "image"

    def test_send_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine
        
        response = client.post("/chat/send", json={})
        assert response.status_code == 422
        
        response = client.post("/chat/send", json={"role": "user"})
        assert response.status_code == 422
        
        response = client.post("/chat/send", json={"content": "Hello"})
        assert response.status_code == 422

    def test_send_validates_role_enum(self, client_with_engine):
        """Test that invalid role value returns 422 error."""
        client, engine = client_with_engine
        
        response = client.post(
            "/chat/send",
            json={
                "role": "invalid_role",
                "content": "Hello",
                "conversation_id": "default",
            },
        )
        
        assert response.status_code == 422

    def test_state_reflects_sent_message(self, client_with_engine):
        """Test that state includes message after send action."""
        client, engine = client_with_engine
        
        send_response = client.post(
            "/chat/send",
            json={
                "role": "user",
                "content": "Test message",
                "conversation_id": "default",
            },
        )
        assert send_response.status_code == 200
        
        state_response = client.get("/chat/state")
        data = state_response.json()
        
        assert data["total_message_count"] == 1
        assert data["messages"][0]["content"] == "Test message"


class TestPostChatDelete:
    """Tests for POST /chat/delete endpoint."""

    def test_delete_message_succeeds(self, client_with_engine):
        """Test deleting a message by ID creates event successfully."""
        client, engine = client_with_engine
        
        send_response = client.post(
            "/chat/send",
            json={"role": "user", "content": "Message to delete"},
        )
        send_data = send_response.json()
        
        state_response = client.get("/chat/state")
        state_data = state_response.json()
        message_id = state_data["messages"][0]["message_id"]
        
        delete_response = client.post(
            "/chat/delete",
            json={"message_id": message_id},
        )
        
        assert delete_response.status_code == 200
        assert delete_response.json()["modality"] == "chat"

    def test_delete_validates_required_fields(self, client_with_engine):
        """Test that missing message_id returns 422 error."""
        client, engine = client_with_engine
        
        response = client.post("/chat/delete", json={})
        assert response.status_code == 422

    def test_state_reflects_deleted_message(self, client_with_engine):
        """Test that state no longer includes deleted message."""
        client, engine = client_with_engine
        
        client.post(
            "/chat/send",
            json={"role": "user", "content": "Message 1"},
        )
        client.post(
            "/chat/send",
            json={"role": "user", "content": "Message 2"},
        )
        
        state_response = client.get("/chat/state")
        state_data = state_response.json()
        message_id = state_data["messages"][0]["message_id"]
        
        client.post("/chat/delete", json={"message_id": message_id})
        
        new_state = client.get("/chat/state").json()
        assert new_state["total_message_count"] == 1
        assert all(m["message_id"] != message_id for m in new_state["messages"])


class TestPostChatClear:
    """Tests for POST /chat/clear endpoint."""

    def test_clear_conversation_succeeds(self, client_with_engine):
        """Test clearing conversation history creates event successfully."""
        client, engine = client_with_engine
        
        client.post(
            "/chat/send",
            json={"role": "user", "content": "Message 1", "conversation_id": "test"},
        )
        
        response = client.post(
            "/chat/clear",
            json={"conversation_id": "test"},
        )
        
        assert response.status_code == 200
        assert response.json()["modality"] == "chat"

    def test_clear_specific_conversation_id(self, client_with_engine):
        """Test clearing specific conversation by ID."""
        client, engine = client_with_engine
        
        client.post(
            "/chat/send",
            json={"role": "user", "content": "Work message", "conversation_id": "work"},
        )
        client.post(
            "/chat/send",
            json={"role": "user", "content": "Personal message", "conversation_id": "personal"},
        )
        
        client.post("/chat/clear", json={"conversation_id": "work"})
        
        state = client.get("/chat/state").json()
        work_messages = [m for m in state["messages"] if m["conversation_id"] == "work"]
        personal_messages = [m for m in state["messages"] if m["conversation_id"] == "personal"]
        
        assert len(work_messages) == 0
        assert len(personal_messages) == 1

    def test_clear_default_conversation(self, client_with_engine):
        """Test clearing default conversation when no ID provided."""
        client, engine = client_with_engine
        
        client.post(
            "/chat/send",
            json={"role": "user", "content": "Default message"},
        )
        
        response = client.post("/chat/clear", json={})
        assert response.status_code == 200
        
        state = client.get("/chat/state").json()
        default_messages = [m for m in state["messages"] if m["conversation_id"] == "default"]
        assert len(default_messages) == 0

    def test_state_reflects_cleared_conversation(self, client_with_engine):
        """Test that state shows empty conversation after clear."""
        client, engine = client_with_engine
        
        client.post(
            "/chat/send",
            json={"role": "user", "content": "Message 1", "conversation_id": "test"},
        )
        client.post(
            "/chat/send",
            json={"role": "user", "content": "Message 2", "conversation_id": "test"},
        )
        
        client.post("/chat/clear", json={"conversation_id": "test"})
        
        state = client.get("/chat/state").json()
        assert "test" not in state["conversations"]
        assert state["total_message_count"] == 0
