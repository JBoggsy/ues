"""Integration tests for GET /email/state endpoint."""

from datetime import datetime, timezone


class TestGetEmailState:
    """Tests for GET /email/state endpoint."""

    def test_returns_correct_structure(self, client_with_engine):
        """Test that GET /email/state returns response with correct structure."""
        client, engine = client_with_engine

        response = client.get("/email/state")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields are present
        assert "modality_type" in data
        assert data["modality_type"] == "email"
        assert "current_time" in data
        assert "user_email_address" in data
        assert "emails" in data
        assert "threads" in data
        assert "folders" in data
        assert "labels" in data
        assert "total_email_count" in data
        assert "unread_count" in data
        assert "starred_count" in data

    def test_returns_empty_state_initially(self, client_with_engine):
        """Test that state has no emails when no emails sent/received."""
        client, engine = client_with_engine

        response = client.get("/email/state")

        assert response.status_code == 200
        data = response.json()

        assert data["emails"] == {}
        assert data["threads"] == {}
        assert data["total_email_count"] == 0
        assert data["unread_count"] == 0
        assert data["starred_count"] == 0

    def test_reflects_sent_email(self, client_with_engine):
        """Test that state includes email after it's sent."""
        client, engine = client_with_engine

        # Send an email
        send_response = client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "to_addresses": ["recipient@example.com"],
                "subject": "Test Subject",
                "body_text": "Test body content",
            },
        )
        assert send_response.status_code == 200

        # Check state reflects the sent email
        state_response = client.get("/email/state")
        assert state_response.status_code == 200

        data = state_response.json()
        assert data["total_email_count"] == 1
        assert len(data["emails"]) == 1

        # Verify the email content
        email = list(data["emails"].values())[0]
        assert email["from_address"] == "user@example.com"
        assert email["to_addresses"] == ["recipient@example.com"]
        assert email["subject"] == "Test Subject"
        assert email["body_text"] == "Test body content"

    def test_reflects_received_email(self, client_with_engine):
        """Test that state includes email after it's received."""
        client, engine = client_with_engine

        # Receive an email
        receive_response = client.post(
            "/email/receive",
            json={
                "from_address": "sender@external.com",
                "to_addresses": ["user@example.com"],
                "subject": "External Email",
                "body_text": "Email from outside",
            },
        )
        assert receive_response.status_code == 200

        # Check state reflects the received email
        state_response = client.get("/email/state")
        assert state_response.status_code == 200

        data = state_response.json()
        assert data["total_email_count"] == 1
        assert data["unread_count"] == 1  # New received emails are unread

        email = list(data["emails"].values())[0]
        assert email["from_address"] == "sender@external.com"
        assert email["subject"] == "External Email"
        assert email["folder"] == "inbox"

    def test_includes_all_folders(self, client_with_engine):
        """Test that state includes emails from all folders."""
        client, engine = client_with_engine

        # Check that standard folders exist
        state_response = client.get("/email/state")
        data = state_response.json()

        # Standard folders should be present
        expected_folders = ["inbox", "sent", "drafts", "trash", "spam", "archive"]
        for folder in expected_folders:
            assert folder in data["folders"], f"Folder '{folder}' not found"

    def test_includes_email_metadata(self, client_with_engine):
        """Test that state includes email metadata (threads, labels, etc.)."""
        client, engine = client_with_engine

        # Receive two emails in a thread
        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Thread Subject",
                "body_text": "First message",
                "thread_id": "test-thread-123",
            },
        )
        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Re: Thread Subject",
                "body_text": "Second message",
                "thread_id": "test-thread-123",
            },
        )

        state_response = client.get("/email/state")
        data = state_response.json()

        # Check threads are tracked
        assert data["total_email_count"] == 2
        assert len(data["threads"]) >= 1

        # Verify thread metadata
        if "test-thread-123" in data["threads"]:
            thread = data["threads"]["test-thread-123"]
            assert thread["message_count"] == 2

    def test_current_time_matches_simulator_time(self, client_with_engine):
        """Test that state's current_time matches simulator time."""
        client, engine = client_with_engine

        initial_time = engine.environment.time_state.current_time

        state_response = client.get("/email/state")
        data = state_response.json()

        state_time = datetime.fromisoformat(data["current_time"].replace("Z", "+00:00"))

        # Times should be very close (within 1 second)
        assert abs((state_time - initial_time).total_seconds()) < 1
