"""Integration tests for GET /contacts/state endpoint."""

from datetime import datetime


class TestGetContactsState:
    """Tests for GET /contacts/state endpoint."""

    def test_returns_correct_structure(self, client_with_engine):
        """Test that GET /contacts/state returns response with correct structure."""
        client, engine = client_with_engine

        response = client.get("/contacts/state")

        assert response.status_code == 200
        data = response.json()

        assert "modality_type" in data
        assert data["modality_type"] == "contacts"
        assert "current_time" in data
        assert "contacts" in data
        assert "total_count" in data
        assert "favorites_count" in data
        assert "blocked_count" in data
        assert "groups" in data

    def test_returns_empty_state_initially(self, client_with_engine):
        """Test that state has no contacts when none have been created."""
        client, engine = client_with_engine

        response = client.get("/contacts/state")

        assert response.status_code == 200
        data = response.json()

        assert data["contacts"] == {}
        assert data["total_count"] == 0
        assert data["favorites_count"] == 0
        assert data["blocked_count"] == 0
        assert data["groups"] == []

    def test_reflects_created_contact(self, client_with_engine):
        """Test that state includes a contact after creation."""
        client, engine = client_with_engine

        create_response = client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "last_name": "Smith",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
            },
        )
        assert create_response.status_code == 200

        state_response = client.get("/contacts/state")
        assert state_response.status_code == 200

        data = state_response.json()
        assert data["total_count"] == 1
        assert len(data["contacts"]) == 1

        contact = list(data["contacts"].values())[0]
        assert contact["first_name"] == "Alice"
        assert contact["last_name"] == "Smith"

    def test_reflects_multiple_contacts(self, client_with_engine):
        """Test that state includes all created contacts."""
        client, engine = client_with_engine

        for name in ["Alice", "Bob", "Carol"]:
            client.post(
                "/contacts/create",
                json={
                    "first_name": name,
                    "identifiers": [
                        {
                            "identifier_type": "email",
                            "value": f"{name.lower()}@example.com",
                        },
                    ],
                },
            )

        data = client.get("/contacts/state").json()
        assert data["total_count"] == 3
        assert len(data["contacts"]) == 3

    def test_reflects_favorites_count(self, client_with_engine):
        """Test that favorites_count updates when contacts are favorited."""
        client, engine = client_with_engine

        # Create a contact as favorite
        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
                "is_favorite": True,
            },
        )
        # Create a non-favorite contact
        client.post(
            "/contacts/create",
            json={
                "first_name": "Bob",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15559876543"},
                ],
            },
        )

        data = client.get("/contacts/state").json()
        assert data["favorites_count"] == 1
        assert data["total_count"] == 2

    def test_reflects_blocked_count(self, client_with_engine):
        """Test that blocked_count updates when contacts are blocked."""
        client, engine = client_with_engine

        client.post(
            "/contacts/create",
            json={
                "first_name": "Spammer",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15550000000"},
                ],
                "is_blocked": True,
            },
        )

        data = client.get("/contacts/state").json()
        assert data["blocked_count"] == 1

    def test_reflects_groups(self, client_with_engine):
        """Test that groups list includes all groups from contacts."""
        client, engine = client_with_engine

        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
                "groups": ["Family"],
            },
        )
        client.post(
            "/contacts/create",
            json={
                "first_name": "Bob",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15559876543"},
                ],
                "groups": ["Work"],
            },
        )

        data = client.get("/contacts/state").json()
        assert set(data["groups"]) == {"Family", "Work"}

    def test_includes_contact_identifiers(self, client_with_engine):
        """Test that contact data includes identifiers."""
        client, engine = client_with_engine

        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {
                        "identifier_type": "phone",
                        "value": "+15551234567",
                        "label": "mobile",
                    },
                    {
                        "identifier_type": "email",
                        "value": "alice@example.com",
                        "label": "work",
                    },
                ],
            },
        )

        data = client.get("/contacts/state").json()
        contact = list(data["contacts"].values())[0]
        assert len(contact["identifiers"]) == 2

        ident_types = {i["identifier_type"] for i in contact["identifiers"]}
        assert ident_types == {"phone", "email"}

    def test_current_time_matches_simulator_time(self, client_with_engine):
        """Test that state's current_time matches simulator time."""
        client, engine = client_with_engine

        initial_time = engine.environment.time_state.current_time

        data = client.get("/contacts/state").json()
        state_time = datetime.fromisoformat(
            data["current_time"].replace("Z", "+00:00")
        )

        assert abs((state_time - initial_time).total_seconds()) < 1


class TestGetContactsStateCompact:
    """Tests for GET /contacts/state?compact=true endpoint."""

    def test_returns_compact_structure(self, client_with_engine):
        """Test that compact=true returns compact response structure."""
        client, engine = client_with_engine

        response = client.get("/contacts/state", params={"compact": True})

        assert response.status_code == 200
        data = response.json()

        assert "modality_type" in data
        assert data["modality_type"] == "contacts"
        assert "last_updated" in data
        assert "update_count" in data
        assert "total_contacts" in data
        assert "favorites_count" in data
        assert "blocked_count" in data
        assert "groups" in data
        assert "recent_contacts" in data

    def test_compact_empty_state(self, client_with_engine):
        """Test compact response for empty contacts state."""
        client, engine = client_with_engine

        data = client.get(
            "/contacts/state", params={"compact": True}
        ).json()

        assert data["total_contacts"] == 0
        assert data["favorites_count"] == 0
        assert data["blocked_count"] == 0
        assert data["groups"] == {}
        assert data["recent_contacts"] == []

    def test_compact_with_contacts(self, client_with_engine):
        """Test compact response includes summary of contacts."""
        client, engine = client_with_engine

        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "last_name": "Smith",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
                "groups": ["Family"],
                "is_favorite": True,
            },
        )

        data = client.get(
            "/contacts/state", params={"compact": True}
        ).json()

        assert data["total_contacts"] == 1
        assert data["favorites_count"] == 1
        assert data["groups"] == {"Family": 1}
        assert len(data["recent_contacts"]) == 1

    def test_compact_does_not_include_full_contact_objects(
        self, client_with_engine
    ):
        """Test that compact response excludes full contact data."""
        client, engine = client_with_engine

        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
            },
        )

        data = client.get(
            "/contacts/state", params={"compact": True}
        ).json()

        # Compact response should NOT have full contacts dict
        assert "contacts" not in data


class TestContactsStateAuthentication:
    """Tests for authentication on contacts state endpoint."""

    def test_requires_api_key(self, client_with_engine):
        """Test that requests without API key are rejected."""
        client, engine = client_with_engine

        # Remove the API key header
        response = client.get(
            "/contacts/state",
            headers={"X-API-Key": ""},
        )
        assert response.status_code in (401, 403)

    def test_rejects_invalid_api_key(self, client_with_engine):
        """Test that invalid API key is rejected."""
        client, engine = client_with_engine

        response = client.get(
            "/contacts/state",
            headers={"X-API-Key": "invalid-key-12345"},
        )
        assert response.status_code in (401, 403)
