"""Integration tests for GET /sms/state endpoint."""

from datetime import datetime


class TestGetSMSState:
    """Tests for GET /sms/state endpoint."""

    def test_returns_correct_structure(self, client_with_engine):
        """Test that GET /sms/state returns response with correct structure."""
        client, engine = client_with_engine

        response = client.get("/sms/state")

        assert response.status_code == 200
        data = response.json()

        assert "modality_type" in data
        assert data["modality_type"] == "sms"
        assert "current_time" in data
        assert "user_phone_number" in data
        assert "messages" in data
        assert "conversations" in data
        assert "total_message_count" in data
        assert "unread_count" in data
        assert "total_conversation_count" in data

    def test_returns_empty_state_initially(self, client_with_engine):
        """Test that state has no messages when no SMS sent/received."""
        client, engine = client_with_engine

        response = client.get("/sms/state")

        assert response.status_code == 200
        data = response.json()

        assert data["messages"] == {}
        assert data["conversations"] == {}
        assert data["total_message_count"] == 0
        assert data["unread_count"] == 0
        assert data["total_conversation_count"] == 0

    def test_reflects_sent_message(self, client_with_engine):
        """Test that state includes message after it's sent."""
        client, engine = client_with_engine

        # Use the user's phone number as from_number for outgoing messages
        # Default user_phone_number in fixtures is +15559876543
        send_response = client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello from the user!",
            },
        )
        assert send_response.status_code == 200

        state_response = client.get("/sms/state")
        assert state_response.status_code == 200

        data = state_response.json()
        assert data["total_message_count"] == 1
        assert len(data["messages"]) == 1

        message_id = list(data["messages"].keys())[0]
        message = data["messages"][message_id]
        assert message["from_number"] == "+15559876543"
        assert message["body"] == "Hello from the user!"
        assert message["direction"] == "outgoing"

    def test_reflects_received_message(self, client_with_engine):
        """Test that state includes message after it's received."""
        client, engine = client_with_engine

        # For incoming messages, from_number should be different from user's phone
        receive_response = client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Hello from outside!",
            },
        )
        assert receive_response.status_code == 200

        state_response = client.get("/sms/state")
        assert state_response.status_code == 200

        data = state_response.json()
        assert data["total_message_count"] == 1
        assert data["unread_count"] == 1

        message_id = list(data["messages"].keys())[0]
        message = data["messages"][message_id]
        assert message["from_number"] == "+15551234567"
        assert message["body"] == "Hello from outside!"
        assert message["direction"] == "incoming"
        assert message["is_read"] is False

    def test_includes_conversation_threads(self, client_with_engine):
        """Test that state organizes messages into conversation threads."""
        client, engine = client_with_engine

        # User sends (from_number = user_phone_number +15559876543)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hey there!",
            },
        )
        # User receives (from_number != user_phone_number)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Hi! How are you?",
            },
        )

        state_response = client.get("/sms/state")
        data = state_response.json()

        assert data["total_conversation_count"] >= 1
        assert len(data["conversations"]) >= 1

        # Verify conversation has expected structure
        thread_id = list(data["conversations"].keys())[0]
        conversation = data["conversations"][thread_id]
        assert "thread_id" in conversation
        assert "participants" in conversation

    def test_includes_message_metadata(self, client_with_engine):
        """Test that state includes message metadata (read status, reactions, etc.)."""
        client, engine = client_with_engine

        # Receive a message (from someone else to user)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test message",
                "message_type": "rcs",
            },
        )

        state_response = client.get("/sms/state")
        data = state_response.json()

        message_id = list(data["messages"].keys())[0]
        message = data["messages"][message_id]

        # Check metadata fields exist
        assert "message_id" in message
        assert "thread_id" in message
        assert "from_number" in message
        assert "to_numbers" in message
        assert "body" in message
        assert "message_type" in message
        assert "direction" in message
        assert "sent_at" in message
        assert "is_read" in message
        assert "delivery_status" in message

    def test_current_time_matches_simulator_time(self, client_with_engine):
        """Test that state's current_time matches simulator time."""
        client, engine = client_with_engine

        initial_time = engine.environment.time_state.current_time

        state_response = client.get("/sms/state")
        data = state_response.json()

        state_time = datetime.fromisoformat(data["current_time"].replace("Z", "+00:00"))

        assert abs((state_time - initial_time).total_seconds()) < 1
