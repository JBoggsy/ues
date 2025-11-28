"""Integration tests for POST /chat/query endpoint."""


class TestPostChatQuery:
    """Tests for POST /chat/query endpoint."""

    def test_query_with_no_filters_returns_all(self, client_with_engine):
        """Test that query with no filters returns all messages."""
        client, engine = client_with_engine
        
        client.post("/chat/send", json={"role": "user", "content": "Message 1"})
        client.post("/chat/send", json={"role": "assistant", "content": "Response 1"})
        client.post("/chat/send", json={"role": "user", "content": "Message 2"})
        
        response = client.post("/chat/query", json={})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 3
        assert data["total_count"] == 3
        assert len(data["messages"]) == 3

    def test_filter_by_conversation_id(self, client_with_engine):
        """Test filtering messages by conversation_id."""
        client, engine = client_with_engine
        
        client.post("/chat/send", json={"role": "user", "content": "Work msg", "conversation_id": "work"})
        client.post("/chat/send", json={"role": "user", "content": "Personal msg", "conversation_id": "personal"})
        client.post("/chat/send", json={"role": "user", "content": "Work msg 2", "conversation_id": "work"})
        
        response = client.post("/chat/query", json={"conversation_id": "work"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 2
        assert all(m["conversation_id"] == "work" for m in data["messages"])

    def test_filter_by_role_user(self, client_with_engine):
        """Test filtering messages by role='user'."""
        client, engine = client_with_engine
        
        client.post("/chat/send", json={"role": "user", "content": "User msg 1"})
        client.post("/chat/send", json={"role": "assistant", "content": "Assistant response"})
        client.post("/chat/send", json={"role": "user", "content": "User msg 2"})
        
        response = client.post("/chat/query", json={"role": "user"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 2
        assert all(m["role"] == "user" for m in data["messages"])

    def test_filter_by_role_assistant(self, client_with_engine):
        """Test filtering messages by role='assistant'."""
        client, engine = client_with_engine
        
        client.post("/chat/send", json={"role": "user", "content": "User msg"})
        client.post("/chat/send", json={"role": "assistant", "content": "Assistant msg 1"})
        client.post("/chat/send", json={"role": "assistant", "content": "Assistant msg 2"})
        
        response = client.post("/chat/query", json={"role": "assistant"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 2
        assert all(m["role"] == "assistant" for m in data["messages"])

    def test_filter_by_search_text(self, client_with_engine):
        """Test searching message content with search parameter."""
        client, engine = client_with_engine
        
        client.post("/chat/send", json={"role": "user", "content": "What's the weather today?"})
        client.post("/chat/send", json={"role": "assistant", "content": "It's sunny and 72°F."})
        client.post("/chat/send", json={"role": "user", "content": "Set a reminder for tomorrow"})
        
        response = client.post("/chat/query", json={"search": "weather"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 1
        assert "weather" in data["messages"][0]["content"].lower()

    def test_filter_by_date_range(self, client_with_engine):
        """Test filtering messages by since/until date range."""
        client, engine = client_with_engine
        
        from datetime import datetime, timedelta, timezone
        
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=2)
        future = now + timedelta(hours=2)
        
        client.post("/chat/send", json={"role": "user", "content": "Message 1"})
        engine.advance_time(timedelta(hours=1))
        client.post("/chat/send", json={"role": "user", "content": "Message 2"})
        engine.advance_time(timedelta(hours=1))
        client.post("/chat/send", json={"role": "user", "content": "Message 3"})
        
        state = client.get("/chat/state").json()
        middle_time = state["messages"][1]["timestamp"]
        
        response = client.post("/chat/query", json={"since": middle_time})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] >= 1

    def test_pagination_with_limit(self, client_with_engine):
        """Test pagination using limit parameter."""
        client, engine = client_with_engine
        
        for i in range(5):
            client.post("/chat/send", json={"role": "user", "content": f"Message {i}"})
        
        response = client.post("/chat/query", json={"limit": 3})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 3
        assert data["total_count"] == 5

    def test_pagination_with_offset(self, client_with_engine):
        """Test pagination using offset parameter."""
        client, engine = client_with_engine
        
        for i in range(5):
            client.post("/chat/send", json={"role": "user", "content": f"Message {i}"})
        
        response = client.post("/chat/query", json={"offset": 2, "limit": 2})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 2
        assert data["total_count"] == 5

    def test_sort_by_timestamp_asc(self, client_with_engine):
        """Test sorting messages by timestamp ascending."""
        client, engine = client_with_engine
        
        from datetime import timedelta
        
        client.post("/chat/send", json={"role": "user", "content": "First"})
        engine.advance_time(timedelta(seconds=1))
        client.post("/chat/send", json={"role": "user", "content": "Second"})
        engine.advance_time(timedelta(seconds=1))
        client.post("/chat/send", json={"role": "user", "content": "Third"})
        
        response = client.post("/chat/query", json={"sort_by": "timestamp", "sort_order": "asc"})
        
        assert response.status_code == 200
        data = response.json()
        
        contents = [m["content"] for m in data["messages"]]
        assert contents == ["First", "Second", "Third"]

    def test_sort_by_timestamp_desc(self, client_with_engine):
        """Test sorting messages by timestamp descending."""
        client, engine = client_with_engine
        
        from datetime import timedelta
        
        client.post("/chat/send", json={"role": "user", "content": "First"})
        engine.advance_time(timedelta(seconds=1))
        client.post("/chat/send", json={"role": "user", "content": "Second"})
        engine.advance_time(timedelta(seconds=1))
        client.post("/chat/send", json={"role": "user", "content": "Third"})
        
        response = client.post("/chat/query", json={"sort_by": "timestamp", "sort_order": "desc"})
        
        assert response.status_code == 200
        data = response.json()
        
        contents = [m["content"] for m in data["messages"]]
        assert contents == ["Third", "Second", "First"]

    def test_combined_filters(self, client_with_engine):
        """Test query with multiple filters combined."""
        client, engine = client_with_engine
        
        client.post("/chat/send", json={"role": "user", "content": "Work question", "conversation_id": "work"})
        client.post("/chat/send", json={"role": "assistant", "content": "Work answer", "conversation_id": "work"})
        client.post("/chat/send", json={"role": "user", "content": "Personal question", "conversation_id": "personal"})
        
        response = client.post(
            "/chat/query",
            json={
                "conversation_id": "work",
                "role": "user",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 1
        assert data["messages"][0]["content"] == "Work question"

    def test_empty_results_when_no_matches(self, client_with_engine):
        """Test that query returns empty results when filters match nothing."""
        client, engine = client_with_engine
        
        client.post("/chat/send", json={"role": "user", "content": "Hello"})
        
        response = client.post("/chat/query", json={"search": "nonexistent"})
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["returned_count"] == 0
        assert data["total_count"] == 0
        assert data["messages"] == []
