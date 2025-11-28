"""Integration tests for POST /sms/query endpoint."""

from datetime import timedelta


class TestPostSMSQuery:
    """Tests for POST /sms/query endpoint."""

    def test_query_with_no_filters_returns_all(self, client_with_engine):
        """Test that query with no filters returns all messages."""
        client, engine = client_with_engine

        # User phone is +15559876543
        # User sends a message (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Message 1",
            },
        )
        # User receives a message (incoming)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Message 2",
            },
        )

        response = client.post("/sms/query", json={})

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert "returned_count" in data
        assert "total_count" in data
        assert data["returned_count"] == 2
        assert data["total_count"] == 2
        assert len(data["messages"]) == 2

    def test_filter_by_conversation_id(self, client_with_engine):
        """Test filtering messages by conversation/thread ID."""
        client, engine = client_with_engine

        # User sends to person A
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "To person A",
            },
        )

        # Get thread_id from state
        state = client.get("/sms/state").json()
        thread_id = list(state["conversations"].keys())[0]

        # User sends to different person B (creates new conversation)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551112222"],
                "body": "To person B",
            },
        )

        response = client.post("/sms/query", json={"thread_id": thread_id})

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert all(msg["thread_id"] == thread_id for msg in data["messages"])

    def test_filter_by_participant(self, client_with_engine):
        """Test filtering messages by participant phone number."""
        client, engine = client_with_engine

        # User sends to person A
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "To person A",
            },
        )
        # User sends to person B
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551112222"],
                "body": "To person B",
            },
        )

        # Query by to_number (person A)
        response = client.post("/sms/query", json={"to_number": "+15551234567"})

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert "+15551234567" in data["messages"][0]["to_numbers"]

    def test_filter_by_direction_incoming(self, client_with_engine):
        """Test filtering by incoming direction."""
        client, engine = client_with_engine

        # User sends (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Sent message",
            },
        )
        # User receives (incoming)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Received message",
            },
        )

        response = client.post("/sms/query", json={"direction": "incoming"})

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert all(msg["direction"] == "incoming" for msg in data["messages"])

    def test_filter_by_direction_outgoing(self, client_with_engine):
        """Test filtering by outgoing direction."""
        client, engine = client_with_engine

        # User sends (outgoing)
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Sent message",
            },
        )
        # User receives (incoming)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Received message",
            },
        )

        response = client.post("/sms/query", json={"direction": "outgoing"})

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert all(msg["direction"] == "outgoing" for msg in data["messages"])

    def test_filter_by_is_read(self, client_with_engine):
        """Test filtering by read status."""
        client, engine = client_with_engine

        # Receive a message (starts unread)
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Unread message",
            },
        )

        # Receive another and mark it read
        response = client.post(
            "/sms/receive",
            json={
                "from_number": "+15552223333",
                "to_numbers": ["+15559876543"],
                "body": "Read message",
            },
        )
        # Get message_id from state
        state = client.get("/sms/state").json()
        # Find the message with "Read message" body
        read_msg_id = None
        for msg_id, msg in state["messages"].items():
            if msg["body"] == "Read message":
                read_msg_id = msg_id
                break
        client.post("/sms/read", json={"message_ids": [read_msg_id]})

        # Query unread
        response = client.post("/sms/query", json={"is_read": False})

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert all(msg["is_read"] is False for msg in data["messages"])

    def test_filter_by_body_contains(self, client_with_engine):
        """Test text search in message body."""
        client, engine = client_with_engine

        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello world",
            },
        )
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Goodbye world",
            },
        )

        response = client.post("/sms/query", json={"body_contains": "Hello"})

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert "Hello" in data["messages"][0]["body"]

    def test_filter_by_date_range_sent_after(self, client_with_engine):
        """Test filtering by sent date (sent_after)."""
        client, engine = client_with_engine

        # Send first message at current time
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Old message",
            },
        )

        # Advance time and send second message
        old_time = engine.environment.time_state.current_time
        engine.environment.time_state.current_time = old_time + timedelta(hours=2)

        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "New message",
            },
        )

        # Query for messages after the original time
        cutoff_time = old_time + timedelta(hours=1)
        response = client.post(
            "/sms/query",
            json={"sent_after": cutoff_time.isoformat()},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["messages"][0]["body"] == "New message"

    def test_filter_by_date_range_sent_before(self, client_with_engine):
        """Test filtering by sent date (sent_before)."""
        client, engine = client_with_engine

        # Send first message at current time
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Old message",
            },
        )

        # Advance time and send second message
        old_time = engine.environment.time_state.current_time
        engine.environment.time_state.current_time = old_time + timedelta(hours=2)

        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "New message",
            },
        )

        # Query for messages before the advanced time
        cutoff_time = old_time + timedelta(hours=1)
        response = client.post(
            "/sms/query",
            json={"sent_before": cutoff_time.isoformat()},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["messages"][0]["body"] == "Old message"

    def test_pagination_limit(self, client_with_engine):
        """Test pagination with limit parameter."""
        client, engine = client_with_engine

        # Create 5 messages
        for i in range(5):
            client.post(
                "/sms/send",
                json={
                    "from_number": "+15559876543",
                    "to_numbers": ["+15551234567"],
                    "body": f"Message {i}",
                },
            )

        response = client.post("/sms/query", json={"limit": 3})

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 3
        assert data["total_count"] == 5
        assert len(data["messages"]) == 3

    def test_pagination_offset(self, client_with_engine):
        """Test pagination with offset parameter."""
        client, engine = client_with_engine

        # Create 5 messages
        for i in range(5):
            client.post(
                "/sms/send",
                json={
                    "from_number": "+15559876543",
                    "to_numbers": ["+15551234567"],
                    "body": f"Message {i}",
                },
            )

        response = client.post("/sms/query", json={"offset": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 3
        assert data["total_count"] == 5
        assert len(data["messages"]) == 3

    def test_combined_filters(self, client_with_engine):
        """Test combining multiple filters."""
        client, engine = client_with_engine

        # User sends to person A
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello A",
            },
        )
        # User sends to person B
        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551112222"],
                "body": "Hello B",
            },
        )
        # User receives from person A
        client.post(
            "/sms/receive",
            json={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "Reply from A",
            },
        )

        response = client.post(
            "/sms/query",
            json={
                "direction": "outgoing",
                "to_number": "+15551234567",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["messages"][0]["body"] == "Hello A"

    def test_empty_results(self, client_with_engine):
        """Test query that returns no results."""
        client, engine = client_with_engine

        client.post(
            "/sms/send",
            json={
                "from_number": "+15559876543",
                "to_numbers": ["+15551234567"],
                "body": "Hello world",
            },
        )

        response = client.post(
            "/sms/query", json={"body_contains": "nonexistent_xyz_pattern"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 0
        assert data["messages"] == []

