"""Environment model - container for all current simulation state."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ues.models.base_state import ModalityState
from ues.models.time import SimulatorTime


class Environment(BaseModel):
    """Container for the complete current state of the simulated world.

    The Environment represents a "snapshot of reality" at a single point in
    simulator time. It holds all modality states and the current time state,
    but does not contain configuration, metadata, or execution history.

    The Environment is a passive state container - it doesn't orchestrate,
    schedule, or execute anything. States within it are modified in-place
    by event execution.

    Args:
        modality_states: Dictionary mapping modality names to their current states.
        time_state: The current simulator time state.

    Example:
        >>> from datetime import datetime, timezone
        >>> time_state = SimulatorTime(current_time=datetime.now(timezone.utc))
        >>> email_state = EmailState(...)
        >>> env = Environment(
        ...     modality_states={"email": email_state},
        ...     time_state=time_state
        ... )
        >>> state = env.get_state("email")
        >>> snapshot = env.get_snapshot()
    """

    modality_states: dict[str, ModalityState] = Field(
        description="Dictionary mapping modality names to their current states"
    )
    time_state: SimulatorTime = Field(
        description="The current simulator time state"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def validate_modality_consistency(self) -> "Environment":
        """Validate that modality names match state types.

        Ensures that the dictionary key (modality name) matches the
        modality_type attribute of each state.

        Raises:
            ValueError: If modality names don't match state types.
        """
        for modality_name, state in self.modality_states.items():
            if state.modality_type != modality_name:
                raise ValueError(
                    f"Modality key '{modality_name}' does not match "
                    f"state.modality_type '{state.modality_type}'"
                )
        return self

    def get_state(self, modality: str) -> ModalityState:
        """Retrieve the state for a specific modality.

        This is the primary method used by events to access the state
        they need to modify.

        Args:
            modality: The modality name (e.g., "email", "location").

        Returns:
            The current state for that modality.

        Raises:
            KeyError: If modality doesn't exist in this environment.
            ValueError: If state reference is None.

        Example:
            >>> state = environment.get_state("email")
            >>> state.apply_input(email_input, environment)
        """
        if modality not in self.modality_states:
            available = ", ".join(sorted(self.modality_states.keys()))
            raise KeyError(
                f"Modality '{modality}' not found in environment. "
                f"Available modalities: {available}"
            )

        state = self.modality_states[modality]

        if state is None:
            raise ValueError(f"State for modality '{modality}' is None")

        return state

    def get_snapshot(self) -> dict[str, Any]:
        """Export complete current state snapshot.

        Creates a nested dictionary representation of all current state:
        - Time state (current_time, time_scale, etc.)
        - All modality states (each as a dictionary)

        This snapshot represents a complete "freeze frame" of the simulation
        at the current moment. It can be saved, compared, or restored.

        Does NOT include:
        - Event queue (future state)
        - Simulation configuration/metadata
        - Execution history

        Returns:
            Dictionary with 'time' and 'modalities' keys.

        Example:
            >>> snapshot = environment.get_snapshot()
            >>> snapshot.keys()
            dict_keys(['time', 'modalities'])
            >>> snapshot['time']['current_time']
            datetime(2024, 3, 15, 14, 30, tzinfo=timezone.utc)
            >>> snapshot['modalities']['email']
            {'modality_type': 'email', 'inbox': [...], ...}
        """
        return {
            "time": self.time_state.to_dict(),
            "modalities": {
                modality_name: state.get_snapshot()
                for modality_name, state in self.modality_states.items()
            },
        }

    def get_compact_snapshot(self) -> dict[str, Any]:
        """Export a compact, LLM-context-optimized snapshot of all modalities.

        Unlike get_snapshot() which returns complete state for each modality,
        this method returns only the most relevant information for AI agent
        context injection. Each modality provides its own compact representation
        suitable for LLM context windows.

        The result is significantly smaller than get_snapshot() output while
        still containing actionable information for agent decision-making.

        Returns:
            Dictionary with:
            - snapshot_time: ISO format timestamp
            - format: "compact"
            - modalities: Dict of modality -> compact snapshot data
            - events: Summary of pending events (placeholder, requires engine)

        Example:
            >>> snapshot = environment.get_compact_snapshot()
            >>> print(snapshot["modalities"]["email"]["summary"])
            "3 unread, 15 total emails"
        """
        current_time = self.time_state.current_time

        return {
            "snapshot_time": current_time.isoformat(),
            "format": "compact",
            "modalities": {
                modality_name: state.get_compact_snapshot(current_time)
                for modality_name, state in self.modality_states.items()
            },
        }

    def get_compact_snapshot_text(self) -> str:
        """Export a plain text, LLM-ready representation of the environment.

        Generates a human-readable text summary suitable for direct injection
        into LLM prompts. Uses emoji prefixes for visual organization.

        Returns:
            Multi-line string with environment summary.

        Example:
            >>> text = environment.get_compact_snapshot_text()
            >>> print(text)
            === UES Environment Snapshot ===
            Time: 2024-03-15 14:30 PST
            ...
        """
        current_time = self.time_state.current_time
        compact = self.get_compact_snapshot()
        modalities = compact["modalities"]

        lines = [
            "=== UES Environment Snapshot ===",
            f"Time: {current_time.strftime('%Y-%m-%d %H:%M')} ({self.time_state.model_dump().get('timezone', 'UTC')})",
            "",
        ]

        # Location
        if "location" in modalities:
            loc = modalities["location"]
            if loc.get("current"):
                c = loc["current"]
                addr = c.get("address") or c.get("named_location") or f"{c['latitude']:.4f}, {c['longitude']:.4f}"
                lines.append(f"📍 LOCATION: {addr}")
            else:
                lines.append("📍 LOCATION: Not set")
            lines.append("")

        # Weather
        if "weather" in modalities:
            w = modalities["weather"]
            if w.get("current"):
                c = w["current"]
                cond = c.get("condition", "Unknown")
                temp_f = c.get("temperature_f", "?")
                temp_c = c.get("temperature_c", "?")
                humidity = c.get("humidity_percent", "?")
                lines.append(f"🌤️ WEATHER: {cond}, {temp_f}°F ({temp_c}°C), {humidity}% humidity")
            else:
                lines.append("🌤️ WEATHER: No data")
            lines.append("")

        # Email
        if "email" in modalities:
            e = modalities["email"]
            lines.append(f"📧 EMAIL: {e['summary']}")
            if e.get("recent_unread"):
                for email in e["recent_unread"][:3]:
                    flag = "⭐ " if email.get("flagged") else ""
                    lines.append(f"  • [{email['received_ago']}] {flag}\"{email['subject']}\" from {email['from']}")
            if e.get("draft_count", 0) > 0:
                lines.append(f"  • {e['draft_count']} drafts pending")
            lines.append("")

        # Calendar
        if "calendar" in modalities:
            cal = modalities["calendar"]
            lines.append(f"📅 CALENDAR: {cal['today_count']} events today")
            if cal.get("current_event"):
                ce = cal["current_event"]
                loc = f" at {ce['location']}" if ce.get("location") else ""
                lines.append(f"  • NOW: {ce['title']}{loc} (ends in {ce['ends_in']})")
            if cal.get("next_event"):
                ne = cal["next_event"]
                loc = f" at {ne['location']}" if ne.get("location") else ""
                lines.append(f"  • NEXT: {ne['title']}{loc} (in {ne['starts_in']})")
            if cal.get("upcoming_today"):
                for evt in cal["upcoming_today"][:3]:
                    if evt != cal.get("next_event"):
                        lines.append(f"  • {evt['start_time']}: {evt['title']}")
            lines.append("")

        # SMS
        if "sms" in modalities:
            s = modalities["sms"]
            lines.append(f"💬 SMS: {s['summary']}")
            if s.get("unread_conversations"):
                for conv in s["unread_conversations"][:3]:
                    participant = conv.get("participant") or conv.get("group_name", "Unknown")
                    msg = conv.get("last_message", "")[:50]
                    lines.append(f"  • {participant} ({conv['received_ago']}): \"{msg}\"")
            lines.append("")

        # Contacts
        if "contacts" in modalities:
            ct = modalities["contacts"]
            lines.append(f"👤 CONTACTS: {ct['summary']}")
            if ct.get("groups"):
                group_strs = [
                    f"{name} ({count})"
                    for name, count in ct["groups"].items()
                ]
                lines.append(f"  Groups: {', '.join(group_strs)}")
            if ct.get("recent_contacts"):
                for rc in ct["recent_contacts"][:3]:
                    lines.append(
                        f"  • {rc['name']} (updated {rc['updated_ago']})"
                    )
            lines.append("")

        # Chat
        if "chat" in modalities:
            ch = modalities["chat"]
            lines.append(f"🤖 CHAT: {ch['summary']}")
            if ch.get("last_user_message"):
                lines.append(f"  Last exchange:")
                user_msg = ch["last_user_message"][:80]
                lines.append(f"    User: \"{user_msg}\"")
                if ch.get("last_assistant_message"):
                    asst_msg = ch["last_assistant_message"][:80]
                    lines.append(f"    Assistant: \"{asst_msg}\"")
            lines.append("")

        # Time preferences
        if "time" in modalities:
            t = modalities["time"]
            lines.append(f"🕐 TIME PREFS: {t['summary']}")
            lines.append("")

        return "\n".join(lines).rstrip()

    def validate(self) -> list[str]:
        """Validate environment consistency and return any issues.

        Checks:
        - time_state is not None and is valid
        - modality_states is not empty
        - All modality states are valid (call state.validate())
        - Modality names match state types
        - No None or invalid state references

        Returns:
            List of validation error messages (empty if valid).

        Example:
            >>> errors = environment.validate()
            >>> if errors:
            ...     print(f"Invalid environment: {errors}")
            >>> # []
        """
        errors = []

        # Validate time state exists
        if self.time_state is None:
            errors.append("time_state is None")
            return errors  # Can't continue without time state

        # Validate time state
        time_errors = self.time_state.validate()
        for error in time_errors:
            errors.append(f"time_state: {error}")

        # Validate modality states exist
        if not self.modality_states:
            errors.append("modality_states is empty (no modalities defined)")
            return errors  # Can't continue without states

        # Validate each modality state
        for modality_name, state in self.modality_states.items():
            # Check for None
            if state is None:
                errors.append(f"modality '{modality_name}': state is None")
                continue

            # Validate modality name matches state type
            if state.modality_type != modality_name:
                errors.append(
                    f"modality '{modality_name}': name does not match "
                    f"state.modality_type '{state.modality_type}'"
                )

            # Validate state itself
            state_errors = state.validate_state()
            for error in state_errors:
                errors.append(f"modality '{modality_name}': {error}")

        # Check for duplicate modality types (shouldn't happen with dict, but be defensive)
        modality_types = [
            state.modality_type
            for state in self.modality_states.values()
            if state is not None
        ]
        if len(modality_types) != len(set(modality_types)):
            duplicates = [t for t in modality_types if modality_types.count(t) > 1]
            errors.append(f"Duplicate modality types found: {set(duplicates)}")

        return errors

    def list_modalities(self) -> list[str]:
        """List all available modality names.

        Returns sorted list of modality names that can be queried
        or accessed in this environment.

        Returns:
            Sorted list of modality name strings.

        Example:
            >>> environment.list_modalities()
            ['calendar', 'email', 'location', 'text', 'weather']
        """
        return sorted(self.modality_states.keys())

    def has_modality(self, modality: str) -> bool:
        """Check if a specific modality exists in this environment.

        Convenience method for checking modality availability without
        catching KeyError from get_state().

        Args:
            modality: The modality name to check.

        Returns:
            True if modality exists, False otherwise.

        Example:
            >>> if environment.has_modality("email"):
            ...     email_state = environment.get_state("email")
        """
        return modality in self.modality_states

    def add_modality(self, modality_name: str, state: ModalityState) -> None:
        """Add a new modality to the environment.

        Allows dynamic addition of modalities after environment creation.
        Useful for extending simulations or lazy initialization of modalities.

        Args:
            modality_name: The name of the modality to add.
            state: The initial state for this modality.

        Raises:
            ValueError: If modality already exists or name doesn't match state type.

        Example:
            >>> weather_state = WeatherState(...)
            >>> environment.add_modality("weather", weather_state)
        """
        if modality_name in self.modality_states:
            raise ValueError(
                f"Modality '{modality_name}' already exists in environment"
            )

        if state.modality_type != modality_name:
            raise ValueError(
                f"Modality name '{modality_name}' does not match "
                f"state.modality_type '{state.modality_type}'"
            )

        self.modality_states[modality_name] = state

    def remove_modality(self, modality_name: str) -> ModalityState:
        """Remove a modality from the environment.

        Allows dynamic removal of modalities. Use with caution as this may
        break events that reference the removed modality.

        Args:
            modality_name: The name of the modality to remove.

        Returns:
            The removed state.

        Raises:
            KeyError: If modality doesn't exist.

        Example:
            >>> old_state = environment.remove_modality("weather")
        """
        if modality_name not in self.modality_states:
            raise KeyError(f"Modality '{modality_name}' not found in environment")

        return self.modality_states.pop(modality_name)

    def clear_all_states(self, new_last_updated: Any) -> int:
        """Clear all modality states to their empty defaults.

        Calls clear() on each modality state, resetting them to freshly
        created conditions. This is used by the simulation clear functionality.

        Args:
            new_last_updated: The timestamp to set as last_updated on all states.

        Returns:
            The number of modality states that were cleared.

        Example:
            >>> from datetime import datetime, timezone
            >>> cleared_count = environment.clear_all_states(datetime.now(timezone.utc))
            >>> print(f"Cleared {cleared_count} modality states")
        """
        for state in self.modality_states.values():
            state.clear()
            state.last_updated = new_last_updated

        return len(self.modality_states)

    # ===== Scenario Serialization Methods =====

    def to_scenario_dict(self) -> dict[str, Any]:
        """Serialize environment to a dictionary suitable for scenario export.

        This method produces a complete, round-trip serializable representation
        of the environment state, suitable for saving to scenario files.

        Unlike `get_snapshot()` which is optimized for API responses, this method
        preserves all data needed to fully reconstruct the environment, including
        the modality_type discriminator for polymorphic deserialization.

        Returns:
            Dictionary with:
            - time_state: Serialized SimulatorTime (using model_dump with ISO dates)
            - modality_states: Dict of modality_type -> serialized state

        Example:
            >>> env = Environment(...)
            >>> data = env.to_scenario_dict()
            >>> # Save to file
            >>> json.dump(data, f, indent=2)
            >>> # Later, restore:
            >>> restored_env, warnings = Environment.from_scenario_dict(data)
        """
        return {
            "time_state": self.time_state.model_dump(mode="json"),
            "modality_states": {
                modality_name: state.model_dump(mode="json")
                for modality_name, state in self.modality_states.items()
            },
        }

    @classmethod
    def from_scenario_dict(
        cls,
        data: dict[str, Any],
        strict: bool = True,
    ) -> tuple["Environment", list[str]]:
        """Deserialize environment from a scenario dictionary.

        Reconstructs an Environment from data previously produced by
        `to_scenario_dict()`. Uses the modality registry to correctly
        instantiate the appropriate ModalityState subclass for each modality.

        Args:
            data: Dictionary from `to_scenario_dict()` containing:
                - time_state: Serialized SimulatorTime data
                - modality_states: Dict of modality_type -> serialized state data
            strict: If True, raise ValueError on unknown modality types.
                If False, skip unknown modalities and add them to warnings.

        Returns:
            Tuple of (Environment, list of warning messages).
            Warnings include skipped modalities when strict=False.

        Raises:
            ValueError: If strict=True and an unknown modality type is encountered.
            ValueError: If required data fields are missing.
            ValidationError: If data fails Pydantic validation.

        Example:
            >>> # Load from file
            >>> with open("scenario.json") as f:
            ...     data = json.load(f)
            >>> env, warnings = Environment.from_scenario_dict(data["environment"])
            >>> if warnings:
            ...     print(f"Loaded with warnings: {warnings}")
        """
        # Import registry functions here to avoid circular imports
        from ues.models.registry import (
            get_modality_state_class,
            is_modality_state_registered,
        )

        warnings: list[str] = []

        # Validate required fields
        if "time_state" not in data:
            raise ValueError("Missing required field: 'time_state'")
        if "modality_states" not in data:
            raise ValueError("Missing required field: 'modality_states'")

        # Deserialize time state
        time_state = SimulatorTime.model_validate(data["time_state"])

        # Deserialize modality states
        modality_states: dict[str, ModalityState] = {}

        for modality_type, state_data in data["modality_states"].items():
            if not is_modality_state_registered(modality_type):
                if strict:
                    raise ValueError(
                        f"Unknown modality type: '{modality_type}'. "
                        "Use strict=False to skip unknown modalities."
                    )
                warnings.append(f"Skipped unknown modality type: '{modality_type}'")
                continue

            state_class = get_modality_state_class(modality_type)
            state = state_class.model_validate(state_data)
            modality_states[modality_type] = state

        # Create and return the environment
        environment = cls(
            time_state=time_state,
            modality_states=modality_states,
        )

        return environment, warnings