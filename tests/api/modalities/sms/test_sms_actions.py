"""Integration tests for SMS action endpoints."""


class TestPostSMSSend:
    """Tests for POST /sms/send endpoint."""

    def test_send_message_succeeds(self, client_with_engine):
        """Test sending an SMS message creates event successfully."""
        client, engine = client_with_engine

        # User phone is +15559876543, so use that as from_number for outgoing
        response = client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello, this is a test message!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert "scheduled_time" in data
        assert data["modality"] == "sms"
        assert data["status"] == "executed"

    def test_send_to_multiple_recipients(self, client_with_engine):
        """Test sending message to multiple phone numbers."""
        client, engine = client_with_engine

        response = client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567", "+15551112222", "+15553334444"],
                "body": "Group message!",
            },
        )

        assert response.status_code == 200

        # Verify state shows message sent to all recipients
        state = client.get("/sms/state").json()
        message = list(state["messages"].values())[0]
        assert len(message["to_numbers"]) == 3

    def test_send_with_media_attachments(self, client_with_engine):
        """Test sending RCS with media attachments."""
        client, engine = client_with_engine

        response = client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Check out this photo!",
                "message_type": "rcs",
                "attachments": [
                    {
                        "filename": "photo.jpg",
                        "size": 1024000,
                        "mime_type": "image/jpeg",
                    }
                ],
            },
        )

        assert response.status_code == 200

        # Verify attachment in state
        state = client.get("/sms/state").json()
        message = list(state["messages"].values())[0]
        assert message["message_type"] == "rcs"
        assert len(message["attachments"]) == 1
        assert message["attachments"][0]["mime_type"] == "image/jpeg"

    def test_send_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine

        # Missing to_numbers
        response = client.post(
            "/sms/send",
            json={"from_number": "+15559876543", "body": "Hello"},
        )
        assert response.status_code == 422

        # Missing body
        response = client.post(
            "/sms/send",
            json={"from_number": "+15559876543", "to_numbers": ["+15551234567"]},
        )
        assert response.status_code == 422

    def test_send_validates_phone_numbers(self, client_with_engine):
        """Test that invalid phone numbers return 422 error."""
        client, engine = client_with_engine

        # Empty to_numbers list
        response = client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": [],
                "body": "Hello",
            },
        )
        assert response.status_code == 422

    def test_state_reflects_sent_message(self, client_with_engine):
        """Test that state includes message after send action."""
        client, engine = client_with_engine

        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Test message for state",
            },
        )

        state = client.get("/sms/state").json()

        assert len(state["messages"]) == 1
        message = list(state["messages"].values())[0]
        assert message["body"] == "Test message for state"
        assert message["direction"] == "outgoing"
        assert message["from_number"] == "+15559876543"


class TestPostSMSReceive:
    """Tests for POST /sms/receive endpoint."""

    def test_receive_message_succeeds(self, client_with_engine):
        """Test receiving an SMS message creates event successfully."""
        client, engine = client_with_engine

        # For incoming, from_number is someone else, to_numbers includes user
        response = client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Hey, got your message!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "sms"
        assert data["status"] == "executed"

    def test_receive_with_media(self, client_with_engine):
        """Test receiving RCS with media."""
        client, engine = client_with_engine

        response = client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Here's a picture",
                "message_type": "rcs",
                "attachments": [
                    {
                        "filename": "image.jpg",
                        "size": 2048000,
                        "mime_type": "image/jpeg",
                    }
                ],
            },
        )

        assert response.status_code == 200

        state = client.get("/sms/state").json()
        message = list(state["messages"].values())[0]
        assert message["message_type"] == "rcs"
        assert len(message["attachments"]) == 1

    def test_receive_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine

        # Missing body
        response = client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
            },
        )
        assert response.status_code == 422

    def test_state_reflects_received_message(self, client_with_engine):
        """Test that state includes message after receive action."""
        client, engine = client_with_engine

        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Incoming message test",
            },
        )

        state = client.get("/sms/state").json()

        assert len(state["messages"]) == 1
        message = list(state["messages"].values())[0]
        assert message["body"] == "Incoming message test"
        assert message["direction"] == "incoming"
        assert message["is_read"] is False
        assert state["unread_count"] == 1


class TestPostSMSRead:
    """Tests for POST /sms/read endpoint."""

    def test_mark_messages_read_succeeds(self, client_with_engine):
        """Test marking messages as read creates event successfully."""
        client, engine = client_with_engine

        # First receive a message (incoming from someone else)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Unread message",
            },
        )

        # Get message_id from state
        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]

        # Mark it as read
        response = client.post("/sms/read", json={"message_ids": [message_id]})

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "sms"

    def test_mark_multiple_messages_read(self, client_with_engine):
        """Test marking multiple messages as read."""
        client, engine = client_with_engine

        # Receive multiple messages (incoming)
        for i in range(3):
            client.post(
                "/sms/receive",
                json={
                    "from_number": "+15551234567",
                    "to_numbers": ["+15559876543"],
                    "body": f"Message {i}",
                },
            )

        # Get message_ids from state
        state = client.get("/sms/state").json()
        msg_ids = list(state["messages"].keys())

        # Mark all as read
        response = client.post("/sms/read", json={"message_ids": msg_ids})

        assert response.status_code == 200

        # Verify all are read
        state = client.get("/sms/state").json()
        assert state["unread_count"] == 0

    def test_read_validates_required_fields(self, client_with_engine):
        """Test that missing message_ids returns 422 error."""
        client, engine = client_with_engine

        response = client.post("/sms/read", json={})
        assert response.status_code == 422

    def test_state_reflects_read_status(self, client_with_engine):
        """Test that state shows updated read status."""
        client, engine = client_with_engine

        # Receive message (incoming)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test read status",
            },
        )

        # Get message_id from state
        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]

        # Verify unread
        assert state["messages"][message_id]["is_read"] is False
        assert state["unread_count"] == 1

        # Mark read
        client.post("/sms/read", json={"message_ids": [message_id]})

        # Verify read
        state = client.get("/sms/state").json()
        assert state["messages"][message_id]["is_read"] is True
        assert state["unread_count"] == 0


class TestPostSMSUnread:
    """Tests for POST /sms/unread endpoint."""

    def test_mark_messages_unread_succeeds(self, client_with_engine):
        """Test marking messages as unread creates event successfully."""
        client, engine = client_with_engine

        # Receive and read a message (incoming)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Read then unread message",
            },
        )

        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]
        client.post("/sms/read", json={"message_ids": [message_id]})

        # Mark as unread
        response = client.post("/sms/unread", json={"message_ids": [message_id]})

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data

    def test_mark_multiple_messages_unread(self, client_with_engine):
        """Test marking multiple messages as unread."""
        client, engine = client_with_engine

        # Receive and read messages (incoming)
        for i in range(3):
            client.post(
                "/sms/receive",
                json={
                    "from_number": "+15551234567",
                    "to_numbers": ["+15559876543"],
                    "body": f"Message {i}",
                },
            )

        state = client.get("/sms/state").json()
        msg_ids = list(state["messages"].keys())

        client.post("/sms/read", json={"message_ids": msg_ids})

        # Mark all as unread
        response = client.post("/sms/unread", json={"message_ids": msg_ids})

        assert response.status_code == 200

        # Verify all unread
        state = client.get("/sms/state").json()
        assert state["unread_count"] == 3

    def test_state_reflects_unread_status(self, client_with_engine):
        """Test that state shows updated unread status."""
        client, engine = client_with_engine

        # Receive and read message (incoming)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Test unread status",
            },
        )

        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]
        client.post("/sms/read", json={"message_ids": [message_id]})

        # Verify read
        state = client.get("/sms/state").json()
        assert state["messages"][message_id]["is_read"] is True

        # Mark unread
        client.post("/sms/unread", json={"message_ids": [message_id]})

        # Verify unread
        state = client.get("/sms/state").json()
        assert state["messages"][message_id]["is_read"] is False
        assert state["unread_count"] == 1


class TestPostSMSDelete:
    """Tests for POST /sms/delete endpoint."""

    def test_delete_messages_succeeds(self, client_with_engine):
        """Test deleting messages creates event successfully."""
        client, engine = client_with_engine

        # User sends a message (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Message to delete",
            },
        )

        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]

        # Delete it
        response = client.post("/sms/delete", json={"message_ids": [message_id]})

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data

    def test_delete_multiple_messages(self, client_with_engine):
        """Test deleting multiple messages."""
        client, engine = client_with_engine

        # User sends multiple messages (outgoing)
        for i in range(3):
            client.post(
                "/sms/send",
                json={
                    "from_number": "+15559876543",
                    "to_numbers": ["+15551234567"],
                    "body": f"Delete me {i}",
                },
            )

        state = client.get("/sms/state").json()
        msg_ids = list(state["messages"].keys())

        # Delete all
        response = client.post("/sms/delete", json={"message_ids": msg_ids})

        assert response.status_code == 200

    def test_delete_validates_required_fields(self, client_with_engine):
        """Test that missing message_ids returns 422 error."""
        client, engine = client_with_engine

        response = client.post("/sms/delete", json={})
        assert response.status_code == 422

    def test_state_reflects_deleted_messages(self, client_with_engine):
        """Test that deleted messages are marked as deleted in state."""
        client, engine = client_with_engine

        # User sends a message (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Soon to be deleted",
            },
        )

        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]

        # Delete it
        client.post("/sms/delete", json={"message_ids": [message_id]})

        # Verify marked as deleted (soft delete)
        state = client.get("/sms/state").json()
        assert message_id in state["messages"]
        assert state["messages"][message_id]["is_deleted"] is True


class TestPostSMSReact:
    """Tests for POST /sms/react endpoint."""

    def test_add_reaction_succeeds(self, client_with_engine):
        """Test adding a reaction to message creates event successfully."""
        client, engine = client_with_engine

        # User sends a message (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "React to this!",
                "message_type": "rcs",
            },
        )

        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]

        # Other person adds reaction
        response = client.post(
            "/sms/react",
            json={
                "message_id": message_id,
                "phone_number": "+15551234567",
                "emoji": "👍",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data

    def test_add_different_reaction_types(self, client_with_engine):
        """Test adding various emoji reactions."""
        client, engine = client_with_engine

        # User sends a message (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Multiple reactions!",
                "message_type": "rcs",
            },
        )

        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]

        emojis = ["👍", "❤️", "😂", "😮"]
        for emoji in emojis:
            response = client.post(
                "/sms/react",
                json={
                    "message_id": message_id,
                    "phone_number": "+15551234567",
                    "emoji": emoji,
                },
            )
            assert response.status_code == 200

    def test_remove_reaction(self, client_with_engine):
        """Test removing a reaction from message."""
        client, engine = client_with_engine

        # User sends a message (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Remove reaction test",
                "message_type": "rcs",
            },
        )

        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]

        # Add reaction
        client.post(
            "/sms/react",
            json={
                "message_id": message_id,
                "phone_number": "+15551234567",
                "emoji": "👍",
            },
        )

        # Remove reaction (empty emoji)
        response = client.post(
            "/sms/react",
            json={
                "message_id": message_id,
                "phone_number": "+15551234567",
                "emoji": "",
            },
        )

        assert response.status_code == 200

    def test_react_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine

        # Missing message_id
        response = client.post(
            "/sms/react",
            json={"phone_number": "+15551234567", "emoji": "👍"},
        )
        assert response.status_code == 422

        # Missing phone_number
        response = client.post(
            "/sms/react",
            json={"message_id": "some-id", "emoji": "👍"},
        )
        assert response.status_code == 422

    def test_state_reflects_message_reactions(self, client_with_engine):
        """Test that state shows updated reactions on messages."""
        client, engine = client_with_engine

        # User sends a message (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Track my reactions",
                "message_type": "rcs",
            },
        )

        state = client.get("/sms/state").json()
        message_id = list(state["messages"].keys())[0]

        # Other person adds reaction
        client.post(
            "/sms/react",
            json={
                "message_id": message_id,
                "phone_number": "+15551234567",
                "emoji": "❤️",
            },
        )

        # Check state
        state = client.get("/sms/state").json()
        message = state["messages"][message_id]
        assert "reactions" in message
        assert len(message["reactions"]) == 1
        assert message["reactions"][0]["emoji"] == "❤️"
        assert message["reactions"][0]["phone_number"] == "+15551234567"
