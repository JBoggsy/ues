"""Integration tests for contacts action endpoints."""


class TestPostContactsCreate:
    """Tests for POST /contacts/create endpoint."""

    def test_create_contact_succeeds(self, client_with_engine):
        """Test creating a contact returns success response."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "last_name": "Smith",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert "scheduled_time" in data
        assert data["modality"] == "contacts"
        assert data["status"] == "executed"

    def test_create_with_full_details(self, client_with_engine):
        """Test creating a contact with all optional fields."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "last_name": "Smith",
                "display_name": "Ali",
                "nickname": "Ally",
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
                "company": "Acme Corp",
                "job_title": "Engineer",
                "addresses": [
                    {
                        "street": "123 Main St",
                        "city": "Springfield",
                        "state": "IL",
                        "postal_code": "62701",
                        "country": "US",
                        "label": "home",
                    },
                ],
                "birthday": "1990-01-15",
                "notes": "Met at conference",
                "is_favorite": True,
                "groups": ["Friends", "Work"],
            },
        )

        assert response.status_code == 200

        # Verify the contact is in state with all details
        state = client.get("/contacts/state").json()
        contact = list(state["contacts"].values())[0]
        assert contact["first_name"] == "Alice"
        assert contact["last_name"] == "Smith"
        assert contact["display_name"] == "Ali"
        assert contact["nickname"] == "Ally"
        assert contact["company"] == "Acme Corp"
        assert contact["job_title"] == "Engineer"
        assert contact["is_favorite"] is True
        assert len(contact["identifiers"]) == 2
        assert len(contact["addresses"]) == 1

    def test_create_with_multiple_identifiers(self, client_with_engine):
        """Test creating a contact with multiple identifiers."""
        client, engine = client_with_engine

        client.post(
            "/contacts/create",
            json={
                "first_name": "Bob",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551111111"},
                    {"identifier_type": "phone", "value": "+15552222222"},
                    {"identifier_type": "email", "value": "bob@example.com"},
                ],
            },
        )

        state = client.get("/contacts/state").json()
        contact = list(state["contacts"].values())[0]
        assert len(contact["identifiers"]) == 3

    def test_create_validates_identifiers_required(self, client_with_engine):
        """Test that creating a contact without identifiers returns 422."""
        client, engine = client_with_engine

        # Missing identifiers entirely
        response = client.post(
            "/contacts/create",
            json={"first_name": "Alice"},
        )
        assert response.status_code == 422

    def test_create_validates_identifiers_not_empty(self, client_with_engine):
        """Test that creating a contact with empty identifiers returns 422."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [],
            },
        )
        assert response.status_code == 422

    def test_state_reflects_created_contact(self, client_with_engine):
        """Test that state includes contact after create action."""
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

        state = client.get("/contacts/state").json()
        assert state["total_count"] == 1
        contact = list(state["contacts"].values())[0]
        assert contact["first_name"] == "Alice"

    def test_create_assigns_contact_id(self, client_with_engine):
        """Test that each created contact gets a unique contact_id."""
        client, engine = client_with_engine

        for name in ["Alice", "Bob"]:
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

        state = client.get("/contacts/state").json()
        contact_ids = list(state["contacts"].keys())
        assert len(contact_ids) == 2
        assert contact_ids[0] != contact_ids[1]


class TestPostContactsUpdate:
    """Tests for POST /contacts/update endpoint."""

    def _create_contact(self, client):
        """Helper to create a contact and return its ID."""
        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "last_name": "Smith",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
            },
        )
        state = client.get("/contacts/state").json()
        return list(state["contacts"].keys())[0]

    def test_update_name_fields(self, client_with_engine):
        """Test updating name fields on a contact."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        response = client.post(
            "/contacts/update",
            json={
                "contact_id": contact_id,
                "first_name": "Alicia",
                "last_name": "Johnson",
            },
        )

        assert response.status_code == 200

        state = client.get("/contacts/state").json()
        contact = state["contacts"][contact_id]
        assert contact["first_name"] == "Alicia"
        assert contact["last_name"] == "Johnson"

    def test_add_identifiers(self, client_with_engine):
        """Test adding identifiers to a contact."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        response = client.post(
            "/contacts/update",
            json={
                "contact_id": contact_id,
                "add_identifiers": [
                    {"identifier_type": "email", "value": "alice@example.com"},
                ],
            },
        )

        assert response.status_code == 200

        state = client.get("/contacts/state").json()
        contact = state["contacts"][contact_id]
        assert len(contact["identifiers"]) == 2

        ident_types = {i["identifier_type"] for i in contact["identifiers"]}
        assert ident_types == {"phone", "email"}

    def test_remove_identifiers(self, client_with_engine):
        """Test removing identifiers from a contact."""
        client, engine = client_with_engine

        # Create with two identifiers
        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                    {"identifier_type": "email", "value": "alice@example.com"},
                ],
            },
        )
        state = client.get("/contacts/state").json()
        contact_id = list(state["contacts"].keys())[0]

        response = client.post(
            "/contacts/update",
            json={
                "contact_id": contact_id,
                "remove_identifiers": [
                    {"identifier_type": "email", "value": "alice@example.com"},
                ],
            },
        )

        assert response.status_code == 200

        state = client.get("/contacts/state").json()
        contact = state["contacts"][contact_id]
        assert len(contact["identifiers"]) == 1
        assert contact["identifiers"][0]["identifier_type"] == "phone"

    def test_add_groups(self, client_with_engine):
        """Test adding groups to a contact via update."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        response = client.post(
            "/contacts/update",
            json={
                "contact_id": contact_id,
                "add_groups": ["Friends", "Work"],
            },
        )

        assert response.status_code == 200

        state = client.get("/contacts/state").json()
        contact = state["contacts"][contact_id]
        assert set(contact["groups"]) == {"Friends", "Work"}

    def test_update_nonexistent_contact_returns_failed(self, client_with_engine):
        """Test updating a non-existent contact returns failed event."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/update",
            json={
                "contact_id": "nonexistent-id",
                "first_name": "Ghost",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()

    def test_update_validates_contact_id_required(self, client_with_engine):
        """Test that contact_id is required for update."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/update",
            json={"first_name": "Alice"},
        )

        assert response.status_code == 422


class TestPostContactsDelete:
    """Tests for POST /contacts/delete endpoint."""

    def _create_contact(self, client, name="Alice"):
        """Helper to create a contact and return its ID."""
        client.post(
            "/contacts/create",
            json={
                "first_name": name,
                "identifiers": [
                    {
                        "identifier_type": "phone",
                        "value": f"+1555{hash(name) % 10000000:07d}",
                    },
                ],
            },
        )
        state = client.get("/contacts/state").json()
        # Return the most recently added contact's ID
        return list(state["contacts"].keys())[-1]

    def test_delete_contact_succeeds(self, client_with_engine):
        """Test deleting a contact returns success response."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        response = client.post(
            "/contacts/delete",
            json={"contact_id": contact_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "contacts"
        assert data["status"] == "executed"

    def test_state_reflects_deleted_contact(self, client_with_engine):
        """Test that deleted contact is removed from state."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        client.post(
            "/contacts/delete",
            json={"contact_id": contact_id},
        )

        state = client.get("/contacts/state").json()
        assert state["total_count"] == 0
        assert contact_id not in state["contacts"]

    def test_delete_nonexistent_contact_returns_failed(self, client_with_engine):
        """Test deleting a non-existent contact returns failed event."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/delete",
            json={"contact_id": "nonexistent-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()

    def test_delete_validates_contact_id_required(self, client_with_engine):
        """Test that contact_id is required for delete."""
        client, engine = client_with_engine

        response = client.post("/contacts/delete", json={})
        assert response.status_code == 422


class TestPostContactsBlock:
    """Tests for POST /contacts/block endpoint."""

    def _create_contact(self, client):
        """Helper to create a contact and return its ID."""
        client.post(
            "/contacts/create",
            json={
                "first_name": "Spammer",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15550000000"},
                ],
            },
        )
        state = client.get("/contacts/state").json()
        return list(state["contacts"].keys())[0]

    def test_block_contact_succeeds(self, client_with_engine):
        """Test blocking a contact returns success response."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        response = client.post(
            "/contacts/block",
            json={"contact_id": contact_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "contacts"

    def test_state_reflects_blocked_contact(self, client_with_engine):
        """Test that state shows contact as blocked after blocking."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        client.post(
            "/contacts/block",
            json={"contact_id": contact_id},
        )

        state = client.get("/contacts/state").json()
        assert state["contacts"][contact_id]["is_blocked"] is True
        assert state["blocked_count"] == 1

    def test_block_nonexistent_contact_returns_failed(self, client_with_engine):
        """Test blocking a non-existent contact returns failed event."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/block",
            json={"contact_id": "nonexistent-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()


class TestPostContactsUnblock:
    """Tests for POST /contacts/unblock endpoint."""

    def _create_and_block(self, client):
        """Helper to create and block a contact, returning its ID."""
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
        state = client.get("/contacts/state").json()
        return list(state["contacts"].keys())[0]

    def test_unblock_contact_succeeds(self, client_with_engine):
        """Test unblocking a contact returns success response."""
        client, engine = client_with_engine
        contact_id = self._create_and_block(client)

        response = client.post(
            "/contacts/unblock",
            json={"contact_id": contact_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "contacts"

    def test_state_reflects_unblocked_contact(self, client_with_engine):
        """Test that state shows contact as unblocked."""
        client, engine = client_with_engine
        contact_id = self._create_and_block(client)

        client.post(
            "/contacts/unblock",
            json={"contact_id": contact_id},
        )

        state = client.get("/contacts/state").json()
        assert state["contacts"][contact_id]["is_blocked"] is False
        assert state["blocked_count"] == 0

    def test_unblock_nonexistent_contact_returns_failed(self, client_with_engine):
        """Test unblocking a non-existent contact returns failed event."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/unblock",
            json={"contact_id": "nonexistent-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()


class TestPostContactsFavorite:
    """Tests for POST /contacts/favorite endpoint."""

    def _create_contact(self, client):
        """Helper to create a contact and return its ID."""
        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
            },
        )
        state = client.get("/contacts/state").json()
        return list(state["contacts"].keys())[0]

    def test_favorite_contact_succeeds(self, client_with_engine):
        """Test favoriting a contact returns success response."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        response = client.post(
            "/contacts/favorite",
            json={"contact_id": contact_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "contacts"

    def test_state_reflects_favorited_contact(self, client_with_engine):
        """Test that state shows contact as favorite after favoriting."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        client.post(
            "/contacts/favorite",
            json={"contact_id": contact_id},
        )

        state = client.get("/contacts/state").json()
        assert state["contacts"][contact_id]["is_favorite"] is True
        assert state["favorites_count"] == 1

    def test_favorite_nonexistent_contact_returns_failed(
        self, client_with_engine
    ):
        """Test favoriting a non-existent contact returns failed event."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/favorite",
            json={"contact_id": "nonexistent-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()


class TestPostContactsUnfavorite:
    """Tests for POST /contacts/unfavorite endpoint."""

    def _create_as_favorite(self, client):
        """Helper to create a favorite contact and return its ID."""
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
        state = client.get("/contacts/state").json()
        return list(state["contacts"].keys())[0]

    def test_unfavorite_contact_succeeds(self, client_with_engine):
        """Test unfavoriting a contact returns success response."""
        client, engine = client_with_engine
        contact_id = self._create_as_favorite(client)

        response = client.post(
            "/contacts/unfavorite",
            json={"contact_id": contact_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "contacts"

    def test_state_reflects_unfavorited_contact(self, client_with_engine):
        """Test that state shows contact as not favorite."""
        client, engine = client_with_engine
        contact_id = self._create_as_favorite(client)

        client.post(
            "/contacts/unfavorite",
            json={"contact_id": contact_id},
        )

        state = client.get("/contacts/state").json()
        assert state["contacts"][contact_id]["is_favorite"] is False
        assert state["favorites_count"] == 0

    def test_unfavorite_nonexistent_contact_returns_failed(
        self, client_with_engine
    ):
        """Test unfavoriting a non-existent contact returns failed event."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/unfavorite",
            json={"contact_id": "nonexistent-id"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()


class TestPostContactsGroupAdd:
    """Tests for POST /contacts/group/add endpoint."""

    def _create_contact(self, client):
        """Helper to create a contact and return its ID."""
        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
            },
        )
        state = client.get("/contacts/state").json()
        return list(state["contacts"].keys())[0]

    def test_add_to_group_succeeds(self, client_with_engine):
        """Test adding a contact to a group returns success response."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        response = client.post(
            "/contacts/group/add",
            json={
                "contact_id": contact_id,
                "group_name": "Friends",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "contacts"

    def test_state_reflects_group_membership(self, client_with_engine):
        """Test that contact's groups are updated after adding to group."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        client.post(
            "/contacts/group/add",
            json={
                "contact_id": contact_id,
                "group_name": "Friends",
            },
        )

        state = client.get("/contacts/state").json()
        contact = state["contacts"][contact_id]
        assert "Friends" in contact["groups"]
        assert "Friends" in state["groups"]

    def test_add_to_multiple_groups(self, client_with_engine):
        """Test adding a contact to multiple groups."""
        client, engine = client_with_engine
        contact_id = self._create_contact(client)

        for group in ["Friends", "Work", "Sports"]:
            client.post(
                "/contacts/group/add",
                json={
                    "contact_id": contact_id,
                    "group_name": group,
                },
            )

        state = client.get("/contacts/state").json()
        contact = state["contacts"][contact_id]
        assert set(contact["groups"]) == {"Friends", "Work", "Sports"}

    def test_add_nonexistent_contact_returns_failed(self, client_with_engine):
        """Test adding non-existent contact to group returns failed."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/group/add",
            json={
                "contact_id": "nonexistent-id",
                "group_name": "Friends",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()

    def test_validates_required_fields(self, client_with_engine):
        """Test that both contact_id and group_name are required."""
        client, engine = client_with_engine

        # Missing group_name
        response = client.post(
            "/contacts/group/add",
            json={"contact_id": "some-id"},
        )
        assert response.status_code == 422

        # Missing contact_id
        response = client.post(
            "/contacts/group/add",
            json={"group_name": "Friends"},
        )
        assert response.status_code == 422


class TestPostContactsGroupRemove:
    """Tests for POST /contacts/group/remove endpoint."""

    def _create_contact_in_group(self, client, group_name="Friends"):
        """Helper to create a contact in a group and return its ID."""
        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
                "groups": [group_name],
            },
        )
        state = client.get("/contacts/state").json()
        return list(state["contacts"].keys())[0]

    def test_remove_from_group_succeeds(self, client_with_engine):
        """Test removing a contact from a group returns success response."""
        client, engine = client_with_engine
        contact_id = self._create_contact_in_group(client)

        response = client.post(
            "/contacts/group/remove",
            json={
                "contact_id": contact_id,
                "group_name": "Friends",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "contacts"

    def test_state_reflects_group_removal(self, client_with_engine):
        """Test that contact's groups are updated after removal."""
        client, engine = client_with_engine
        contact_id = self._create_contact_in_group(client)

        client.post(
            "/contacts/group/remove",
            json={
                "contact_id": contact_id,
                "group_name": "Friends",
            },
        )

        state = client.get("/contacts/state").json()
        contact = state["contacts"][contact_id]
        assert "Friends" not in contact["groups"]

    def test_remove_nonexistent_contact_returns_failed(self, client_with_engine):
        """Test removing non-existent contact from group returns failed."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/group/remove",
            json={
                "contact_id": "nonexistent-id",
                "group_name": "Friends",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()


class TestPostContactsMerge:
    """Tests for POST /contacts/merge endpoint."""

    def _create_two_contacts(self, client):
        """Helper to create two contacts and return their IDs."""
        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "last_name": "Smith",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
                "groups": ["Friends"],
            },
        )
        client.post(
            "/contacts/create",
            json={
                "first_name": "Ali",
                "identifiers": [
                    {"identifier_type": "email", "value": "alice@example.com"},
                ],
                "groups": ["Work"],
            },
        )
        state = client.get("/contacts/state").json()
        contact_ids = list(state["contacts"].keys())
        return contact_ids[0], contact_ids[1]

    def test_merge_contacts_succeeds(self, client_with_engine):
        """Test merging two contacts returns success response."""
        client, engine = client_with_engine
        primary_id, secondary_id = self._create_two_contacts(client)

        response = client.post(
            "/contacts/merge",
            json={
                "primary_contact_id": primary_id,
                "secondary_contact_id": secondary_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data["modality"] == "contacts"
        assert data["status"] == "executed"

    def test_merge_removes_secondary_contact(self, client_with_engine):
        """Test that secondary contact is removed after merge."""
        client, engine = client_with_engine
        primary_id, secondary_id = self._create_two_contacts(client)

        client.post(
            "/contacts/merge",
            json={
                "primary_contact_id": primary_id,
                "secondary_contact_id": secondary_id,
            },
        )

        state = client.get("/contacts/state").json()
        assert state["total_count"] == 1
        assert primary_id in state["contacts"]
        assert secondary_id not in state["contacts"]

    def test_merge_combines_identifiers(self, client_with_engine):
        """Test that merged contact has identifiers from both contacts."""
        client, engine = client_with_engine
        primary_id, secondary_id = self._create_two_contacts(client)

        client.post(
            "/contacts/merge",
            json={
                "primary_contact_id": primary_id,
                "secondary_contact_id": secondary_id,
            },
        )

        state = client.get("/contacts/state").json()
        primary = state["contacts"][primary_id]
        ident_values = {i["value"] for i in primary["identifiers"]}
        assert "+15551234567" in ident_values
        assert "alice@example.com" in ident_values

    def test_merge_combines_groups(self, client_with_engine):
        """Test that merged contact has groups from both contacts."""
        client, engine = client_with_engine
        primary_id, secondary_id = self._create_two_contacts(client)

        client.post(
            "/contacts/merge",
            json={
                "primary_contact_id": primary_id,
                "secondary_contact_id": secondary_id,
            },
        )

        state = client.get("/contacts/state").json()
        primary = state["contacts"][primary_id]
        assert set(primary["groups"]) == {"Friends", "Work"}

    def test_merge_preserves_primary_name(self, client_with_engine):
        """Test that primary contact's name fields take precedence."""
        client, engine = client_with_engine
        primary_id, secondary_id = self._create_two_contacts(client)

        client.post(
            "/contacts/merge",
            json={
                "primary_contact_id": primary_id,
                "secondary_contact_id": secondary_id,
            },
        )

        state = client.get("/contacts/state").json()
        primary = state["contacts"][primary_id]
        assert primary["first_name"] == "Alice"
        assert primary["last_name"] == "Smith"

    def test_merge_nonexistent_primary_returns_failed(self, client_with_engine):
        """Test merging with non-existent primary contact returns failed."""
        client, engine = client_with_engine

        # Create one contact as secondary
        client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
            },
        )
        state = client.get("/contacts/state").json()
        contact_id = list(state["contacts"].keys())[0]

        response = client.post(
            "/contacts/merge",
            json={
                "primary_contact_id": "nonexistent-id",
                "secondary_contact_id": contact_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()

    def test_merge_nonexistent_secondary_returns_failed(self, client_with_engine):
        """Test merging with non-existent secondary contact returns failed."""
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
        state = client.get("/contacts/state").json()
        contact_id = list(state["contacts"].keys())[0]

        response = client.post(
            "/contacts/merge",
            json={
                "primary_contact_id": contact_id,
                "secondary_contact_id": "nonexistent-id",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "not found" in data["message"].lower()

    def test_merge_validates_required_fields(self, client_with_engine):
        """Test that both contact IDs are required for merge."""
        client, engine = client_with_engine

        # Missing secondary_contact_id
        response = client.post(
            "/contacts/merge",
            json={"primary_contact_id": "some-id"},
        )
        assert response.status_code == 422


class TestContactsActionAuthentication:
    """Tests for authentication on contacts action endpoints."""

    def test_create_requires_api_key(self, client_with_engine):
        """Test that create endpoint requires valid API key."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/create",
            json={
                "first_name": "Alice",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551234567"},
                ],
            },
            headers={"X-API-Key": "invalid-key-12345"},
        )

        assert response.status_code in (401, 403)

    def test_delete_requires_api_key(self, client_with_engine):
        """Test that delete endpoint requires valid API key."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/delete",
            json={"contact_id": "some-id"},
            headers={"X-API-Key": "invalid-key-12345"},
        )

        assert response.status_code in (401, 403)

    def test_block_requires_api_key(self, client_with_engine):
        """Test that block endpoint requires valid API key."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/block",
            json={"contact_id": "some-id"},
            headers={"X-API-Key": "invalid-key-12345"},
        )

        assert response.status_code in (401, 403)

    def test_merge_requires_api_key(self, client_with_engine):
        """Test that merge endpoint requires valid API key."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/merge",
            json={
                "primary_contact_id": "id1",
                "secondary_contact_id": "id2",
            },
            headers={"X-API-Key": "invalid-key-12345"},
        )

        assert response.status_code in (401, 403)
