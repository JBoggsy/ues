"""Integration tests for email action endpoints."""


class TestPostEmailSend:
    """Tests for POST /email/send endpoint."""

    def test_send_email_succeeds(self, client_with_engine):
        """Test sending an email creates event successfully."""
        client, engine = client_with_engine

        response = client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "to_addresses": ["recipient@example.com"],
                "subject": "Test Subject",
                "body_text": "Test body content",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "event_id" in data
        assert "scheduled_time" in data
        assert data["modality"] == "email"
        assert data["status"] == "executed"

    def test_send_with_multiple_recipients(self, client_with_engine):
        """Test sending email to multiple recipients."""
        client, engine = client_with_engine

        response = client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "to_addresses": ["alice@example.com", "bob@example.com", "charlie@example.com"],
                "subject": "Group Email",
                "body_text": "Hello everyone!",
            },
        )

        assert response.status_code == 200

        state = client.get("/email/state").json()
        email = list(state["emails"].values())[0]
        assert len(email["to_addresses"]) == 3
        assert "alice@example.com" in email["to_addresses"]
        assert "bob@example.com" in email["to_addresses"]
        assert "charlie@example.com" in email["to_addresses"]

    def test_send_with_cc_and_bcc(self, client_with_engine):
        """Test sending email with CC and BCC recipients."""
        client, engine = client_with_engine

        response = client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "to_addresses": ["primary@example.com"],
                "cc_addresses": ["cc1@example.com", "cc2@example.com"],
                "bcc_addresses": ["hidden@example.com"],
                "subject": "CC and BCC Test",
                "body_text": "Testing CC and BCC",
            },
        )

        assert response.status_code == 200

        state = client.get("/email/state").json()
        email = list(state["emails"].values())[0]
        assert email["cc_addresses"] == ["cc1@example.com", "cc2@example.com"]
        assert email["bcc_addresses"] == ["hidden@example.com"]

    def test_send_with_attachments(self, client_with_engine):
        """Test sending email with attachments."""
        client, engine = client_with_engine

        response = client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "to_addresses": ["recipient@example.com"],
                "subject": "Email with Attachment",
                "body_text": "Please see attached",
                "attachments": [
                    {
                        "filename": "report.pdf",
                        "size": 1024,
                        "mime_type": "application/pdf",
                    }
                ],
            },
        )

        assert response.status_code == 200

        state = client.get("/email/state").json()
        email = list(state["emails"].values())[0]
        assert len(email["attachments"]) == 1
        assert email["attachments"][0]["filename"] == "report.pdf"

    def test_send_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine

        # Missing all required fields
        response = client.post("/email/send", json={})
        assert response.status_code == 422

        # Missing to_addresses
        response = client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "subject": "Test",
                "body_text": "Test",
            },
        )
        assert response.status_code == 422

        # Missing subject
        response = client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "to_addresses": ["recipient@example.com"],
                "body_text": "Test",
            },
        )
        assert response.status_code == 422

    def test_send_validates_email_addresses(self, client_with_engine):
        """Test that empty to_addresses list returns 422 error."""
        client, engine = client_with_engine

        # Empty to_addresses list should be rejected
        response = client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "to_addresses": [],
                "subject": "Test",
                "body_text": "Test",
            },
        )
        assert response.status_code == 422

    def test_state_reflects_sent_email(self, client_with_engine):
        """Test that state includes email after send action."""
        client, engine = client_with_engine

        client.post(
            "/email/send",
            json={
                "from_address": "user@example.com",
                "to_addresses": ["recipient@example.com"],
                "subject": "State Test",
                "body_text": "Check state",
            },
        )

        state = client.get("/email/state").json()
        assert state["total_email_count"] == 1

        email = list(state["emails"].values())[0]
        assert email["subject"] == "State Test"
        assert email["folder"] == "sent"


class TestPostEmailReceive:
    """Tests for POST /email/receive endpoint."""

    def test_receive_email_succeeds(self, client_with_engine):
        """Test receiving an external email creates event successfully."""
        client, engine = client_with_engine

        response = client.post(
            "/email/receive",
            json={
                "from_address": "external@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Incoming Email",
                "body_text": "Message from outside",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "event_id" in data
        assert data["modality"] == "email"
        assert data["status"] == "executed"

    def test_receive_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine

        response = client.post("/email/receive", json={})
        assert response.status_code == 422

        # Missing to_addresses
        response = client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "subject": "Test",
                "body_text": "Test",
            },
        )
        assert response.status_code == 422

    def test_state_reflects_received_email(self, client_with_engine):
        """Test that state includes email after receive action."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Received Email",
                "body_text": "Received content",
            },
        )

        state = client.get("/email/state").json()
        assert state["total_email_count"] == 1
        assert state["unread_count"] == 1  # New received emails are unread

        email = list(state["emails"].values())[0]
        assert email["subject"] == "Received Email"
        assert email["folder"] == "inbox"
        assert email["is_read"] is False


class TestPostEmailRead:
    """Tests for POST /email/read endpoint."""

    def test_mark_email_read_succeeds(self, client_with_engine):
        """Test marking emails as read creates event successfully."""
        client, engine = client_with_engine

        # First receive an email
        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Unread Email",
                "body_text": "Content",
            },
        )

        # Get the email ID
        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        # Mark as read
        response = client.post("/email/read", json={"message_ids": [email_id]})

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_mark_multiple_emails_read(self, client_with_engine):
        """Test marking multiple emails as read."""
        client, engine = client_with_engine

        # Create multiple emails
        for i in range(3):
            client.post(
                "/email/receive",
                json={
                    "from_address": f"sender{i}@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": f"Email {i}",
                    "body_text": f"Content {i}",
                },
            )

        # Get all email IDs
        state = client.get("/email/state").json()
        email_ids = list(state["emails"].keys())
        assert len(email_ids) == 3

        # Mark all as read
        response = client.post("/email/read", json={"message_ids": email_ids})
        assert response.status_code == 200

        # Verify all are read
        new_state = client.get("/email/state").json()
        assert new_state["unread_count"] == 0

    def test_read_validates_required_fields(self, client_with_engine):
        """Test that missing email_ids returns 422 error."""
        client, engine = client_with_engine

        response = client.post("/email/read", json={})
        assert response.status_code == 422

        # Empty list should also be rejected
        response = client.post("/email/read", json={"message_ids": []})
        assert response.status_code == 422

    def test_state_reflects_read_status(self, client_with_engine):
        """Test that state shows updated read status."""
        client, engine = client_with_engine

        # Receive email
        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]
        assert state["emails"][email_id]["is_read"] is False

        # Mark as read
        client.post("/email/read", json={"message_ids": [email_id]})

        new_state = client.get("/email/state").json()
        assert new_state["emails"][email_id]["is_read"] is True
        assert new_state["unread_count"] == 0


class TestPostEmailUnread:
    """Tests for POST /email/unread endpoint."""

    def test_mark_email_unread_succeeds(self, client_with_engine):
        """Test marking emails as unread creates event successfully."""
        client, engine = client_with_engine

        # Receive and mark read
        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )
        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]
        client.post("/email/read", json={"message_ids": [email_id]})

        # Mark as unread
        response = client.post("/email/unread", json={"message_ids": [email_id]})

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_mark_multiple_emails_unread(self, client_with_engine):
        """Test marking multiple emails as unread."""
        client, engine = client_with_engine

        # Create multiple emails and mark them read
        for i in range(3):
            client.post(
                "/email/receive",
                json={
                    "from_address": f"sender{i}@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": f"Email {i}",
                    "body_text": f"Content {i}",
                },
            )

        state = client.get("/email/state").json()
        email_ids = list(state["emails"].keys())
        client.post("/email/read", json={"message_ids": email_ids})

        # Verify all read
        state = client.get("/email/state").json()
        assert state["unread_count"] == 0

        # Mark all as unread
        response = client.post("/email/unread", json={"message_ids": email_ids})
        assert response.status_code == 200

        # Verify all unread
        new_state = client.get("/email/state").json()
        assert new_state["unread_count"] == 3

    def test_state_reflects_unread_status(self, client_with_engine):
        """Test that state shows updated unread status."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        # Mark read then unread
        client.post("/email/read", json={"message_ids": [email_id]})
        client.post("/email/unread", json={"message_ids": [email_id]})

        new_state = client.get("/email/state").json()
        assert new_state["emails"][email_id]["is_read"] is False


class TestPostEmailStar:
    """Tests for POST /email/star endpoint."""

    def test_star_email_succeeds(self, client_with_engine):
        """Test starring emails creates event successfully."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Important",
                "body_text": "Important content",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        response = client.post("/email/star", json={"message_ids": [email_id]})

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_star_multiple_emails(self, client_with_engine):
        """Test starring multiple emails."""
        client, engine = client_with_engine

        for i in range(3):
            client.post(
                "/email/receive",
                json={
                    "from_address": f"sender{i}@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": f"Email {i}",
                    "body_text": f"Content {i}",
                },
            )

        state = client.get("/email/state").json()
        email_ids = list(state["emails"].keys())

        response = client.post("/email/star", json={"message_ids": email_ids})
        assert response.status_code == 200

        new_state = client.get("/email/state").json()
        assert new_state["starred_count"] == 3

    def test_state_reflects_starred_status(self, client_with_engine):
        """Test that state shows updated starred status."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]
        assert state["emails"][email_id]["is_starred"] is False
        assert state["starred_count"] == 0

        client.post("/email/star", json={"message_ids": [email_id]})

        new_state = client.get("/email/state").json()
        assert new_state["emails"][email_id]["is_starred"] is True
        assert new_state["starred_count"] == 1


class TestPostEmailUnstar:
    """Tests for POST /email/unstar endpoint."""

    def test_unstar_email_succeeds(self, client_with_engine):
        """Test unstarring emails creates event successfully."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]
        client.post("/email/star", json={"message_ids": [email_id]})

        response = client.post("/email/unstar", json={"message_ids": [email_id]})

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_unstar_multiple_emails(self, client_with_engine):
        """Test unstarring multiple emails."""
        client, engine = client_with_engine

        for i in range(3):
            client.post(
                "/email/receive",
                json={
                    "from_address": f"sender{i}@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": f"Email {i}",
                    "body_text": f"Content {i}",
                },
            )

        state = client.get("/email/state").json()
        email_ids = list(state["emails"].keys())
        client.post("/email/star", json={"message_ids": email_ids})

        state = client.get("/email/state").json()
        assert state["starred_count"] == 3

        response = client.post("/email/unstar", json={"message_ids": email_ids})
        assert response.status_code == 200

        new_state = client.get("/email/state").json()
        assert new_state["starred_count"] == 0

    def test_state_reflects_unstarred_status(self, client_with_engine):
        """Test that state shows updated unstarred status."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        client.post("/email/star", json={"message_ids": [email_id]})
        client.post("/email/unstar", json={"message_ids": [email_id]})

        new_state = client.get("/email/state").json()
        assert new_state["emails"][email_id]["is_starred"] is False


class TestPostEmailArchive:
    """Tests for POST /email/archive endpoint."""

    def test_archive_email_succeeds(self, client_with_engine):
        """Test archiving emails creates event successfully."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Old Email",
                "body_text": "Archive me",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        response = client.post("/email/archive", json={"message_ids": [email_id]})

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_archive_multiple_emails(self, client_with_engine):
        """Test archiving multiple emails."""
        client, engine = client_with_engine

        for i in range(3):
            client.post(
                "/email/receive",
                json={
                    "from_address": f"sender{i}@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": f"Email {i}",
                    "body_text": f"Content {i}",
                },
            )

        state = client.get("/email/state").json()
        email_ids = list(state["emails"].keys())

        response = client.post("/email/archive", json={"message_ids": email_ids})
        assert response.status_code == 200

        new_state = client.get("/email/state").json()
        for email_id in email_ids:
            assert new_state["emails"][email_id]["folder"] == "archive"

    def test_state_reflects_archived_email(self, client_with_engine):
        """Test that state shows email moved to archive."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]
        assert state["emails"][email_id]["folder"] == "inbox"

        client.post("/email/archive", json={"message_ids": [email_id]})

        new_state = client.get("/email/state").json()
        assert new_state["emails"][email_id]["folder"] == "archive"


class TestPostEmailDelete:
    """Tests for POST /email/delete endpoint."""

    def test_delete_email_succeeds(self, client_with_engine):
        """Test deleting emails creates event successfully."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Delete Me",
                "body_text": "Content",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        response = client.post("/email/delete", json={"message_ids": [email_id]})

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_delete_multiple_emails(self, client_with_engine):
        """Test deleting multiple emails."""
        client, engine = client_with_engine

        for i in range(3):
            client.post(
                "/email/receive",
                json={
                    "from_address": f"sender{i}@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": f"Email {i}",
                    "body_text": f"Content {i}",
                },
            )

        state = client.get("/email/state").json()
        email_ids = list(state["emails"].keys())

        response = client.post("/email/delete", json={"message_ids": email_ids})
        assert response.status_code == 200

        # Verify all moved to trash
        new_state = client.get("/email/state").json()
        for email_id in email_ids:
            assert new_state["emails"][email_id]["folder"] == "trash"

    def test_delete_with_permanent_flag(self, client_with_engine):
        """Test permanently deleting emails (vs trash).
        
        Note: The current API may not support permanent deletion - 
        this test documents expected behavior.
        """
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        # Standard delete moves to trash
        response = client.post("/email/delete", json={"message_ids": [email_id]})
        assert response.status_code == 200

        new_state = client.get("/email/state").json()
        # Email should be in trash (not permanently deleted)
        assert email_id in new_state["emails"]
        assert new_state["emails"][email_id]["folder"] == "trash"

    def test_state_reflects_deleted_email(self, client_with_engine):
        """Test that state shows email moved to trash after delete."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]
        assert state["emails"][email_id]["folder"] == "inbox"

        client.post("/email/delete", json={"message_ids": [email_id]})

        new_state = client.get("/email/state").json()
        assert new_state["emails"][email_id]["folder"] == "trash"


class TestPostEmailLabel:
    """Tests for POST /email/label endpoint."""

    def test_add_label_succeeds(self, client_with_engine):
        """Test adding labels to emails creates event successfully."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Work Email",
                "body_text": "Work content",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        response = client.post(
            "/email/label",
            json={"message_ids": [email_id], "labels": ["work"]},
        )

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_add_multiple_labels(self, client_with_engine):
        """Test adding multiple labels to emails."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Multi-label Email",
                "body_text": "Content",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        response = client.post(
            "/email/label",
            json={"message_ids": [email_id], "labels": ["work", "urgent", "project-x"]},
        )
        assert response.status_code == 200

        new_state = client.get("/email/state").json()
        email_labels = new_state["emails"][email_id]["labels"]
        assert "work" in email_labels
        assert "urgent" in email_labels
        assert "project-x" in email_labels

    def test_label_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine

        response = client.post("/email/label", json={})
        assert response.status_code == 422

        # Missing labels
        response = client.post(
            "/email/label",
            json={"message_ids": ["some-id"]},
        )
        assert response.status_code == 422

        # Empty labels list
        response = client.post(
            "/email/label",
            json={"message_ids": ["some-id"], "labels": []},
        )
        assert response.status_code == 422

    def test_state_reflects_added_labels(self, client_with_engine):
        """Test that state shows updated labels."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]
        assert state["emails"][email_id]["labels"] == []

        client.post(
            "/email/label",
            json={"message_ids": [email_id], "labels": ["important"]},
        )

        new_state = client.get("/email/state").json()
        assert "important" in new_state["emails"][email_id]["labels"]


class TestPostEmailUnlabel:
    """Tests for POST /email/unlabel endpoint."""

    def test_remove_label_succeeds(self, client_with_engine):
        """Test removing labels from emails creates event successfully."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        # First add a label
        client.post(
            "/email/label",
            json={"message_ids": [email_id], "labels": ["work"]},
        )

        # Then remove it
        response = client.post(
            "/email/unlabel",
            json={"message_ids": [email_id], "labels": ["work"]},
        )

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_remove_multiple_labels(self, client_with_engine):
        """Test removing multiple labels from emails."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        # Add labels
        client.post(
            "/email/label",
            json={"message_ids": [email_id], "labels": ["work", "urgent", "project"]},
        )

        # Remove some labels
        response = client.post(
            "/email/unlabel",
            json={"message_ids": [email_id], "labels": ["work", "project"]},
        )
        assert response.status_code == 200

        new_state = client.get("/email/state").json()
        email_labels = new_state["emails"][email_id]["labels"]
        assert "work" not in email_labels
        assert "project" not in email_labels
        assert "urgent" in email_labels

    def test_state_reflects_removed_labels(self, client_with_engine):
        """Test that state shows updated labels."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        client.post(
            "/email/label",
            json={"message_ids": [email_id], "labels": ["temp"]},
        )

        state = client.get("/email/state").json()
        assert "temp" in state["emails"][email_id]["labels"]

        client.post(
            "/email/unlabel",
            json={"message_ids": [email_id], "labels": ["temp"]},
        )

        new_state = client.get("/email/state").json()
        assert "temp" not in new_state["emails"][email_id]["labels"]


class TestPostEmailMove:
    """Tests for POST /email/move endpoint."""

    def test_move_email_succeeds(self, client_with_engine):
        """Test moving emails to different folder creates event successfully."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]

        response = client.post(
            "/email/move",
            json={"message_ids": [email_id], "folder": "archive"},
        )

        assert response.status_code == 200
        assert response.json()["modality"] == "email"

    def test_move_multiple_emails(self, client_with_engine):
        """Test moving multiple emails to folder."""
        client, engine = client_with_engine

        for i in range(3):
            client.post(
                "/email/receive",
                json={
                    "from_address": f"sender{i}@example.com",
                    "to_addresses": ["user@example.com"],
                    "subject": f"Email {i}",
                    "body_text": f"Content {i}",
                },
            )

        state = client.get("/email/state").json()
        email_ids = list(state["emails"].keys())

        response = client.post(
            "/email/move",
            json={"message_ids": email_ids, "folder": "spam"},
        )
        assert response.status_code == 200

        new_state = client.get("/email/state").json()
        for email_id in email_ids:
            assert new_state["emails"][email_id]["folder"] == "spam"

    def test_move_validates_required_fields(self, client_with_engine):
        """Test that missing required fields returns 422 error."""
        client, engine = client_with_engine

        response = client.post("/email/move", json={})
        assert response.status_code == 422

        # Missing folder
        response = client.post(
            "/email/move",
            json={"message_ids": ["some-id"]},
        )
        assert response.status_code == 422

        # Empty message_ids
        response = client.post(
            "/email/move",
            json={"message_ids": [], "folder": "archive"},
        )
        assert response.status_code == 422

    def test_state_reflects_moved_email(self, client_with_engine):
        """Test that state shows email in new folder."""
        client, engine = client_with_engine

        client.post(
            "/email/receive",
            json={
                "from_address": "sender@example.com",
                "to_addresses": ["user@example.com"],
                "subject": "Test",
                "body_text": "Test",
            },
        )

        state = client.get("/email/state").json()
        email_id = list(state["emails"].keys())[0]
        assert state["emails"][email_id]["folder"] == "inbox"

        client.post(
            "/email/move",
            json={"message_ids": [email_id], "folder": "drafts"},
        )

        new_state = client.get("/email/state").json()
        assert new_state["emails"][email_id]["folder"] == "drafts"
