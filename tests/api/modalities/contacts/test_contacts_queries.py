"""Integration tests for POST /contacts/query endpoint."""


class TestPostContactsQuery:
    """Tests for POST /contacts/query endpoint."""

    def _seed_contacts(self, client):
        """Seed the state with several contacts for query testing.

        Creates:
        - Alice Smith: phone + email, group=Family, favorite
        - Bob Johnson: phone, group=Work
        - Carol White: email, group=Family+Work, blocked
        - Dave Brown: phone + email, group=Friends

        Returns:
            dict mapping name to contact_id.
        """
        contacts = [
            {
                "first_name": "Alice",
                "last_name": "Smith",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15551111111"},
                    {"identifier_type": "email", "value": "alice@example.com"},
                ],
                "groups": ["Family"],
                "is_favorite": True,
                "company": "Acme Corp",
            },
            {
                "first_name": "Bob",
                "last_name": "Johnson",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15552222222"},
                ],
                "groups": ["Work"],
            },
            {
                "first_name": "Carol",
                "last_name": "White",
                "identifiers": [
                    {"identifier_type": "email", "value": "carol@example.com"},
                ],
                "groups": ["Family", "Work"],
                "is_blocked": True,
            },
            {
                "first_name": "Dave",
                "last_name": "Brown",
                "identifiers": [
                    {"identifier_type": "phone", "value": "+15554444444"},
                    {"identifier_type": "email", "value": "dave@example.com"},
                ],
                "groups": ["Friends"],
            },
        ]

        for contact_data in contacts:
            client.post("/contacts/create", json=contact_data)

        state = client.get("/contacts/state").json()
        name_to_id = {}
        for cid, contact in state["contacts"].items():
            name_to_id[contact["first_name"]] = cid
        return name_to_id

    def test_query_returns_correct_structure(self, client_with_engine):
        """Test that query response has correct structure."""
        client, engine = client_with_engine

        response = client.post("/contacts/query", json={})

        assert response.status_code == 200
        data = response.json()
        assert "modality_type" in data
        assert data["modality_type"] == "contacts"
        assert "contacts" in data
        assert "total_count" in data
        assert "returned_count" in data
        assert "query" in data

    def test_query_with_no_filters_returns_all(self, client_with_engine):
        """Test that query with no filters returns all contacts."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post("/contacts/query", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 4
        assert data["returned_count"] == 4
        assert len(data["contacts"]) == 4

    def test_search_by_first_name(self, client_with_engine):
        """Test searching contacts by first name."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"search_text": "Alice"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["contacts"][0]["first_name"] == "Alice"

    def test_search_by_last_name(self, client_with_engine):
        """Test searching contacts by last name."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"search_text": "Johnson"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["contacts"][0]["last_name"] == "Johnson"

    def test_search_is_case_insensitive(self, client_with_engine):
        """Test that text search is case-insensitive."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"search_text": "alice"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1

    def test_search_partial_match(self, client_with_engine):
        """Test searching with partial name matches."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"search_text": "ali"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] >= 1
        names = [c["first_name"] for c in data["contacts"]]
        assert "Alice" in names

    def test_search_by_company(self, client_with_engine):
        """Test searching contacts by company name."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"search_text": "Acme"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["contacts"][0]["first_name"] == "Alice"

    def test_search_by_identifier_value(self, client_with_engine):
        """Test searching contacts by identifier value."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"search_text": "+15551111111"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["contacts"][0]["first_name"] == "Alice"

    def test_filter_by_group(self, client_with_engine):
        """Test filtering contacts by group membership."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"group": "Family"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 2
        names = {c["first_name"] for c in data["contacts"]}
        assert names == {"Alice", "Carol"}

    def test_filter_by_work_group(self, client_with_engine):
        """Test filtering contacts by Work group."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"group": "Work"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 2
        names = {c["first_name"] for c in data["contacts"]}
        assert names == {"Bob", "Carol"}

    def test_filter_by_is_favorite(self, client_with_engine):
        """Test filtering by favorite status."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"is_favorite": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["contacts"][0]["first_name"] == "Alice"

    def test_filter_by_is_blocked(self, client_with_engine):
        """Test filtering by blocked status."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"is_blocked": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["contacts"][0]["first_name"] == "Carol"

    def test_filter_by_has_phone(self, client_with_engine):
        """Test filtering contacts that have phone identifiers."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"has_phone": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 3
        names = {c["first_name"] for c in data["contacts"]}
        assert names == {"Alice", "Bob", "Dave"}

    def test_filter_by_has_email(self, client_with_engine):
        """Test filtering contacts that have email identifiers."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"has_email": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 3
        names = {c["first_name"] for c in data["contacts"]}
        assert names == {"Alice", "Carol", "Dave"}

    def test_filter_by_identifier_lookup(self, client_with_engine):
        """Test filtering by exact identifier type and value."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={
                "identifier_type": "email",
                "identifier_value": "alice@example.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["contacts"][0]["first_name"] == "Alice"

    def test_pagination_limit(self, client_with_engine):
        """Test pagination with limit parameter."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"limit": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 2
        assert data["total_count"] == 4
        assert len(data["contacts"]) == 2

    def test_pagination_offset(self, client_with_engine):
        """Test pagination with offset parameter."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"offset": 2},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 2
        assert data["total_count"] == 4

    def test_pagination_limit_and_offset(self, client_with_engine):
        """Test pagination with both limit and offset."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"limit": 1, "offset": 1},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["total_count"] == 4

    def test_combined_filters(self, client_with_engine):
        """Test combining multiple filters."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        # Family group + has phone → Alice (Carol is email-only in Family)
        response = client.post(
            "/contacts/query",
            json={
                "group": "Family",
                "has_phone": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 1
        assert data["contacts"][0]["first_name"] == "Alice"

    def test_empty_results(self, client_with_engine):
        """Test query that returns no results."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"search_text": "nonexistent_xyz_name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 0
        assert data["total_count"] == 0
        assert data["contacts"] == []

    def test_query_echoes_parameters(self, client_with_engine):
        """Test that query response echoes the query parameters."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/query",
            json={
                "search_text": "Alice",
                "group": "Family",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query"]["search_text"] == "Alice"
        assert data["query"]["group"] == "Family"

    def test_query_on_empty_state(self, client_with_engine):
        """Test querying when no contacts exist."""
        client, engine = client_with_engine

        response = client.post("/contacts/query", json={})

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["returned_count"] == 0
        assert data["contacts"] == []

    def test_filter_nonexistent_group_returns_empty(self, client_with_engine):
        """Test filtering by a group that doesn't exist returns empty."""
        client, engine = client_with_engine
        self._seed_contacts(client)

        response = client.post(
            "/contacts/query",
            json={"group": "NonexistentGroup"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["returned_count"] == 0


class TestContactsQueryAuthentication:
    """Tests for authentication on contacts query endpoint."""

    def test_query_requires_api_key(self, client_with_engine):
        """Test that query endpoint requires valid API key."""
        client, engine = client_with_engine

        response = client.post(
            "/contacts/query",
            json={},
            headers={"X-API-Key": "invalid-key-12345"},
        )

        assert response.status_code in (401, 403)
