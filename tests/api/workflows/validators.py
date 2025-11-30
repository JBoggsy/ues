"""
State validation helpers for workflow scenarios.

These validators provide reusable assertion functions that can be
attached to workflow steps to verify state after each operation.

Example:
    WorkflowStep(
        step_type=StepType.VERIFY_STATE,
        description="Verify 3 emails in inbox",
        params={"modality": "email"},
        assertions=[
            StateValidator.email_count(3),
            StateValidator.email_from("sender@example.com"),
        ],
    )
"""

from typing import Any, Callable

# Type alias for assertion functions
AssertionFunc = Callable[[dict[str, Any]], None]


class StateValidator:
    """Helpers for validating modality state responses."""

    # -------------------------------------------------------------------------
    # Email State Validators
    # -------------------------------------------------------------------------

    @staticmethod
    def email_count(expected: int) -> AssertionFunc:
        """Assert the total number of emails in state."""
        def check(state: dict[str, Any]) -> None:
            # Handle both direct state and wrapped response
            data = state.get("state", state)
            
            # Try total_email_count first (from EmailStateResponse)
            if "total_email_count" in data:
                total = data["total_email_count"]
            # Then try emails dict (keyed by message_id)
            elif "emails" in data:
                emails = data["emails"]
                if isinstance(emails, dict):
                    total = len(emails)
                else:
                    total = len(emails)
            # Fallback to messages/inbox for other formats
            else:
                messages = data.get("messages", data.get("inbox", []))
                if isinstance(messages, dict):
                    total = sum(len(v) for v in messages.values() if isinstance(v, list))
                else:
                    total = len(messages)
            
            assert total == expected, f"Expected {expected} emails, got {total}"
        return check

    @staticmethod
    def email_from(address: str, exists: bool = True) -> AssertionFunc:
        """Assert email from specific address exists (or not)."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            
            # Get emails - try dict format first (keyed by message_id)
            emails = data.get("emails", {})
            if isinstance(emails, dict):
                messages = list(emails.values())
            else:
                messages = emails if emails else []
            
            # Fallback to messages/inbox if emails is empty
            if not messages:
                messages = data.get("messages", data.get("inbox", []))
                if isinstance(messages, dict):
                    messages = [m for folder in messages.values() if isinstance(folder, list) for m in folder]
            
            found = any(
                m.get("from_address") == address or m.get("from") == address
                for m in messages
            )
            if exists:
                assert found, f"Expected email from {address} not found"
            else:
                assert not found, f"Unexpected email from {address} found"
        return check

    @staticmethod
    def email_subject_contains(text: str) -> AssertionFunc:
        """Assert at least one email subject contains the given text."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            
            # Get emails - try dict format first (keyed by message_id)
            emails = data.get("emails", {})
            if isinstance(emails, dict):
                messages = list(emails.values())
            else:
                messages = emails if emails else []
            
            # Fallback to messages/inbox if emails is empty
            if not messages:
                messages = data.get("messages", data.get("inbox", []))
                if isinstance(messages, dict):
                    messages = [m for folder in messages.values() if isinstance(folder, list) for m in folder]
            
            found = any(text in m.get("subject", "") for m in messages)
            assert found, f"No email subject contains '{text}'"
        return check

    @staticmethod
    def email_unread_count(expected: int) -> AssertionFunc:
        """Assert the number of unread emails."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            
            # Try unread_count field first (from EmailStateResponse)
            if "unread_count" in data:
                unread = data["unread_count"]
            else:
                # Get emails - try dict format first (keyed by message_id)
                emails = data.get("emails", {})
                if isinstance(emails, dict):
                    messages = list(emails.values())
                else:
                    messages = emails if emails else []
                
                # Fallback to messages/inbox if emails is empty
                if not messages:
                    messages = data.get("messages", data.get("inbox", []))
                    if isinstance(messages, dict):
                        messages = [m for folder in messages.values() if isinstance(folder, list) for m in folder]
                
                unread = sum(1 for m in messages if not m.get("is_read", False))
            
            assert unread == expected, f"Expected {expected} unread emails, got {unread}"
        return check

    # -------------------------------------------------------------------------
    # SMS State Validators
    # -------------------------------------------------------------------------

    @staticmethod
    def sms_count(expected: int) -> AssertionFunc:
        """Assert the total number of SMS messages."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Messages are in top-level "messages" dict, not nested in conversations
            messages = data.get("messages", {})
            if isinstance(messages, dict):
                total = len(messages)
            else:
                total = len(messages) if messages else 0
            assert total == expected, f"Expected {expected} SMS messages, got {total}"
        return check

    @staticmethod
    def sms_from(number: str, exists: bool = True) -> AssertionFunc:
        """Assert SMS from specific number exists (or not)."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Messages are in top-level "messages" dict
            messages = data.get("messages", {})
            if isinstance(messages, dict):
                messages = list(messages.values())
            found = any(msg.get("from_number") == number for msg in messages)
            if exists:
                assert found, f"Expected SMS from {number} not found"
            else:
                assert not found, f"Unexpected SMS from {number} found"
        return check

    @staticmethod
    def sms_body_contains(text: str) -> AssertionFunc:
        """Assert at least one SMS body contains the given text."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Messages are in top-level "messages" dict
            messages = data.get("messages", {})
            if isinstance(messages, dict):
                messages = list(messages.values())
            found = any(text in msg.get("body", "") for msg in messages)
            assert found, f"No SMS body contains '{text}'"
        return check

    # -------------------------------------------------------------------------
    # Chat State Validators
    # -------------------------------------------------------------------------

    @staticmethod
    def chat_message_count(expected: int) -> AssertionFunc:
        """Assert the total number of chat messages."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Messages are in top-level "messages" list, not nested in conversations
            messages = data.get("messages", [])
            total = len(messages)
            assert total == expected, f"Expected {expected} chat messages, got {total}"
        return check

    @staticmethod
    def chat_has_message_from(role: str, containing: str | None = None) -> AssertionFunc:
        """Assert a chat message from the given role exists."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Messages are in top-level "messages" list
            messages = data.get("messages", [])
            found = False
            for msg in messages:
                if msg.get("role") == role:
                    if containing is None or containing in msg.get("content", ""):
                        found = True
                        break
            assert found, f"No chat message from '{role}'" + (f" containing '{containing}'" if containing else "")
        return check

    # -------------------------------------------------------------------------
    # Calendar State Validators
    # -------------------------------------------------------------------------

    @staticmethod
    def calendar_event_count(expected: int) -> AssertionFunc:
        """Assert the number of calendar events."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Events is a dict with event_id keys
            events = data.get("events", {})
            if isinstance(events, dict):
                actual = len(events)
            else:
                actual = len(events) if events else 0
            assert actual == expected, f"Expected {expected} calendar events, got {actual}"
        return check

    @staticmethod
    def calendar_event_exists(title: str) -> AssertionFunc:
        """Assert a calendar event with the given title exists."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Events is a dict with event_id keys
            events = data.get("events", {})
            if isinstance(events, dict):
                events = list(events.values())
            found = any(e.get("title") == title for e in events)
            assert found, f"Calendar event '{title}' not found"
        return check

    @staticmethod
    def calendar_event_at_time(title: str, start_time: str) -> AssertionFunc:
        """Assert a calendar event exists at the specified time."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Events is a dict with event_id keys
            events = data.get("events", {})
            if isinstance(events, dict):
                events = list(events.values())
            found = any(
                e.get("title") == title and start_time in e.get("start", "")
                for e in events
            )
            assert found, f"Calendar event '{title}' at {start_time} not found"
        return check

    # -------------------------------------------------------------------------
    # Location State Validators
    # -------------------------------------------------------------------------

    @staticmethod
    def location_is(name: str) -> AssertionFunc:
        """Assert the current location name."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            current = data.get("current_location", data.get("current", {}))
            actual = current.get("named_location", current.get("location_name", current.get("name", "")))
            assert actual == name, f"Expected location '{name}', got '{actual}'"
        return check

    @staticmethod
    def location_near(latitude: float, longitude: float, tolerance: float = 0.01) -> AssertionFunc:
        """Assert current location is near the given coordinates."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            current = data.get("current_location", data.get("current", {}))
            lat = current.get("latitude", 0)
            lon = current.get("longitude", 0)
            lat_ok = abs(lat - latitude) <= tolerance
            lon_ok = abs(lon - longitude) <= tolerance
            assert lat_ok and lon_ok, f"Location ({lat}, {lon}) not near ({latitude}, {longitude})"
        return check

    @staticmethod
    def location_history_count(expected: int) -> AssertionFunc:
        """Assert the number of location history entries."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            history = data.get("history", data.get("location_history", []))
            actual = len(history)
            assert actual == expected, f"Expected {expected} location history entries, got {actual}"
        return check

    # -------------------------------------------------------------------------
    # Weather State Validators
    # -------------------------------------------------------------------------

    @staticmethod
    def weather_conditions(expected: str) -> AssertionFunc:
        """Assert the current weather conditions."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            # Weather uses OpenWeather format stored in locations dict
            locations = data.get("locations", {})
            found = False
            for loc_data in locations.values():
                # Try getting conditions from OpenWeather format
                current_report = loc_data.get("current_report", {})
                current = current_report.get("current", {})
                weather = current.get("weather", [])
                if weather:
                    conditions = weather[0].get("main", "")
                    if conditions == expected:
                        found = True
                        break
                # Also try legacy format
                if loc_data.get("conditions") == expected:
                    found = True
                    break
            # Try simple reports format too
            reports = data.get("reports", {})
            if isinstance(reports, dict):
                for r in reports.values():
                    if isinstance(r, dict) and r.get("conditions") == expected:
                        found = True
                        break
            assert found, f"Weather conditions '{expected}' not found"
        return check

    @staticmethod
    def weather_temperature_range(min_temp: float, max_temp: float) -> AssertionFunc:
        """Assert temperature is within the given range (in Celsius)."""
        def check(state: dict[str, Any]) -> None:
            data = state.get("state", state)
            temps = []
            # Weather uses OpenWeather format stored in locations dict
            locations = data.get("locations", {})
            for loc_data in locations.values():
                current_report = loc_data.get("current_report", {})
                current = current_report.get("current", {})
                temp_k = current.get("temp")
                if temp_k is not None:
                    # Convert from Kelvin to Celsius
                    temp_c = temp_k - 273.15
                    temps.append(temp_c)
            # Also try legacy format
            reports = data.get("reports", {})
            if isinstance(reports, dict):
                for r in reports.values():
                    if isinstance(r, dict):
                        t = r.get("temperature")
                        if t is not None:
                            temps.append(t)
            if not temps:
                raise AssertionError("No temperature data found")
            for temp in temps:
                assert min_temp <= temp <= max_temp, f"Temperature {temp}°C not in range [{min_temp}, {max_temp}]"
        return check


class EventSummaryValidator:
    """Helpers for validating event summary responses."""

    @staticmethod
    def pending_count(expected: int) -> AssertionFunc:
        """Assert the number of pending events."""
        def check(summary: dict[str, Any]) -> None:
            actual = summary.get("pending_events", summary.get("pending", 0))
            assert actual == expected, f"Expected {expected} pending events, got {actual}"
        return check

    @staticmethod
    def executed_count(expected: int) -> AssertionFunc:
        """Assert the number of executed events."""
        def check(summary: dict[str, Any]) -> None:
            actual = summary.get("executed_events", summary.get("executed", 0))
            assert actual == expected, f"Expected {expected} executed events, got {actual}"
        return check

    @staticmethod
    def failed_count(expected: int) -> AssertionFunc:
        """Assert the number of failed events."""
        def check(summary: dict[str, Any]) -> None:
            actual = summary.get("failed_events", summary.get("failed", 0))
            assert actual == expected, f"Expected {expected} failed events, got {actual}"
        return check

    @staticmethod
    def total_count(expected: int) -> AssertionFunc:
        """Assert the total number of events."""
        def check(summary: dict[str, Any]) -> None:
            actual = summary.get("total_events", summary.get("total", 0))
            assert actual == expected, f"Expected {expected} total events, got {actual}"
        return check

    @staticmethod
    def modality_count(modality: str, expected: int) -> AssertionFunc:
        """Assert the number of events for a specific modality."""
        def check(summary: dict[str, Any]) -> None:
            by_modality = summary.get("by_modality", summary.get("modalities", {}))
            actual = by_modality.get(modality, 0)
            assert actual == expected, f"Expected {expected} {modality} events, got {actual}"
        return check


class SimulationStatusValidator:
    """Helpers for validating simulation status responses."""

    @staticmethod
    def is_running(expected: bool = True) -> AssertionFunc:
        """Assert the simulation running state."""
        def check(status: dict[str, Any]) -> None:
            actual = status.get("is_running", False)
            assert actual == expected, f"Expected is_running={expected}, got {actual}"
        return check

    @staticmethod
    def is_paused(expected: bool = True) -> AssertionFunc:
        """Assert the simulation paused state."""
        def check(status: dict[str, Any]) -> None:
            actual = status.get("is_paused", False)
            assert actual == expected, f"Expected is_paused={expected}, got {actual}"
        return check

    @staticmethod
    def time_scale(expected: float) -> AssertionFunc:
        """Assert the simulation time scale."""
        def check(status: dict[str, Any]) -> None:
            actual = status.get("time_scale", 1.0)
            assert abs(actual - expected) < 0.001, f"Expected time_scale={expected}, got {actual}"
        return check


class ResponseValidator:
    """Helpers for validating generic API responses."""

    @staticmethod
    def has_field(field: str, value: Any = None) -> AssertionFunc:
        """Assert response has a field (optionally with specific value)."""
        def check(response: dict[str, Any]) -> None:
            assert field in response, f"Response missing field '{field}'"
            if value is not None:
                actual = response[field]
                assert actual == value, f"Field '{field}' expected {value}, got {actual}"
        return check

    @staticmethod
    def field_contains(field: str, text: str) -> AssertionFunc:
        """Assert a string field contains the given text."""
        def check(response: dict[str, Any]) -> None:
            actual = response.get(field, "")
            assert text in str(actual), f"Field '{field}' does not contain '{text}'"
        return check

    @staticmethod
    def field_gte(field: str, min_value: float) -> AssertionFunc:
        """Assert a numeric field is >= min_value."""
        def check(response: dict[str, Any]) -> None:
            actual = response.get(field, 0)
            assert actual >= min_value, f"Field '{field}' ({actual}) < {min_value}"
        return check

    @staticmethod
    def field_lte(field: str, max_value: float) -> AssertionFunc:
        """Assert a numeric field is <= max_value."""
        def check(response: dict[str, Any]) -> None:
            actual = response.get(field, 0)
            assert actual <= max_value, f"Field '{field}' ({actual}) > {max_value}"
        return check
