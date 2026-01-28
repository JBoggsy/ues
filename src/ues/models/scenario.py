"""Scenario model for save/load functionality.

This module provides models for saving and loading complete simulation
scenarios, including environment state, event queues, and metadata.

Example:
    >>> from ues.models.scenario import Scenario
    >>> from ues.models.environment import Environment
    >>> from ues.models.queue import EventQueue
    >>> 
    >>> # Create scenario from current state
    >>> scenario = Scenario.create(
    ...     environment=environment,
    ...     event_queue=event_queue,
    ...     author="Test User",
    ...     description="Initial test scenario",
    ... )
    >>> 
    >>> # Save to JSON
    >>> json_str = scenario.to_json()
    >>> 
    >>> # Load from JSON
    >>> loaded = Scenario.from_json(json_str)
"""

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field, field_validator

from ues.models.version import UES_VERSION

if TYPE_CHECKING:
    from ues.models.environment import Environment
    from ues.models.queue import EventQueue

# Scenario format version - increment when schema changes
SCENARIO_FORMAT_VERSION = "1"


class ScenarioMetadata(BaseModel):
    """Metadata for a saved scenario.

    Contains version information for compatibility checking, timestamps
    for tracking, and optional author/description fields for documentation.

    Args:
        ues_version: UES version that created this scenario (e.g., "0.1.0").
        scenario_version: Schema version for this file format (e.g., "1").
        created_at: When the scenario was created (timezone-aware UTC).
        author: Optional author name/identifier.
        description: Optional human-readable description.

    Example:
        >>> metadata = ScenarioMetadata(
        ...     ues_version="0.1.0",
        ...     scenario_version="1",
        ...     created_at=datetime.now(timezone.utc),
        ...     author="Test User",
        ...     description="Test scenario for email workflows",
        ... )
    """

    ues_version: str = Field(
        description="UES version that created this scenario"
    )
    scenario_version: str = Field(
        default=SCENARIO_FORMAT_VERSION,
        description="Schema version for this file format",
    )
    created_at: datetime = Field(
        description="When the scenario was created (UTC)"
    )
    author: Optional[str] = Field(
        default=None,
        description="Author name or identifier",
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the scenario",
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_timezone_aware(cls, v: datetime | str) -> datetime:
        """Ensure datetime is timezone-aware, converting naive to UTC if needed."""
        if isinstance(v, str):
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        if isinstance(v, datetime) and v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        return v


class Scenario(BaseModel):
    """Complete scenario containing environment state and event queue.

    A Scenario represents a complete, serializable snapshot of a simulation
    that can be saved to a file and loaded later. It includes:
    - Metadata for version compatibility and documentation
    - Environment state (all modality states and simulator time)
    - Event queue (all scheduled, executed, and pending events)

    The environment and events fields store serialized dictionaries rather
    than actual Environment/EventQueue instances. This defers parsing until
    load time, allowing for partial compatibility when loading scenarios
    with unknown modality types.

    Args:
        metadata: Scenario metadata (version info, author, description).
        environment: Serialized Environment dictionary.
        events: Serialized EventQueue dictionary.

    Example:
        >>> # Create from current simulation state
        >>> scenario = Scenario.create(
        ...     environment=simulation.environment,
        ...     event_queue=simulation.event_queue,
        ...     author="Developer",
        ...     description="Test scenario",
        ... )
        >>> 
        >>> # Save to file
        >>> with open("scenario.ues-scenario.json", "w") as f:
        ...     f.write(scenario.to_json())
        >>> 
        >>> # Load from file
        >>> with open("scenario.ues-scenario.json") as f:
        ...     loaded = Scenario.from_json(f.read())
    """

    metadata: ScenarioMetadata = Field(
        description="Scenario metadata (version info, author, description)"
    )
    environment: dict[str, Any] = Field(
        description="Serialized Environment state"
    )
    events: dict[str, Any] = Field(
        description="Serialized EventQueue"
    )

    @classmethod
    def create(
        cls,
        environment: "Environment",
        event_queue: "EventQueue",
        author: Optional[str] = None,
        description: Optional[str] = None,
    ) -> "Scenario":
        """Create a scenario from current simulation state.

        Factory method that serializes the environment and event queue
        and creates appropriate metadata.

        Args:
            environment: Current Environment instance to serialize.
            event_queue: Current EventQueue instance to serialize.
            author: Optional author name for metadata.
            description: Optional description for metadata.

        Returns:
            New Scenario instance ready for serialization.

        Example:
            >>> scenario = Scenario.create(
            ...     environment=env,
            ...     event_queue=queue,
            ...     author="Test User",
            ...     description="Initial state for regression testing",
            ... )
        """
        metadata = ScenarioMetadata(
            ues_version=UES_VERSION,
            scenario_version=SCENARIO_FORMAT_VERSION,
            created_at=datetime.now(timezone.utc),
            author=author,
            description=description,
        )

        return cls(
            metadata=metadata,
            environment=environment.to_scenario_dict(),
            events=event_queue.to_scenario_dict(),
        )

    def to_json(self, indent: int = 2) -> str:
        """Serialize scenario to a JSON string.

        Produces a human-readable JSON string suitable for saving to a file.
        Uses ISO 8601 format for datetime fields.

        Args:
            indent: Number of spaces for indentation (default 2).

        Returns:
            JSON string representation of the scenario.

        Example:
            >>> json_str = scenario.to_json()
            >>> with open("scenario.json", "w") as f:
            ...     f.write(json_str)
        """
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "Scenario":
        """Deserialize scenario from a JSON string.

        Parses a JSON string (typically read from a file) into a Scenario
        instance. The environment and events are stored as dictionaries
        and not fully deserialized until load time.

        Args:
            json_str: JSON string from to_json() or a scenario file.

        Returns:
            New Scenario instance with parsed data.

        Raises:
            ValueError: If JSON is invalid or missing required fields.
            ValidationError: If data fails Pydantic validation.

        Example:
            >>> with open("scenario.json") as f:
            ...     scenario = Scenario.from_json(f.read())
        """
        return cls.model_validate_json(json_str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scenario":
        """Deserialize scenario from a dictionary.

        Alternative to from_json() when you already have parsed JSON data.

        Args:
            data: Dictionary containing scenario data.

        Returns:
            New Scenario instance.

        Raises:
            ValueError: If required fields are missing.
            ValidationError: If data fails Pydantic validation.
        """
        return cls.model_validate(data)

    def to_dict(self) -> dict[str, Any]:
        """Serialize scenario to a dictionary.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        return self.model_dump(mode="json")

    def get_environment(
        self,
        strict: bool = True,
    ) -> tuple["Environment", list[str]]:
        """Deserialize and return the Environment from this scenario.

        Convenience method that deserializes the stored environment dict
        into an actual Environment instance.

        Args:
            strict: If True, raise on unknown modality types.
                If False, skip unknown modalities with warnings.

        Returns:
            Tuple of (Environment, list of warning messages).

        Example:
            >>> env, warnings = scenario.get_environment(strict=False)
            >>> if warnings:
            ...     print(f"Loaded with warnings: {warnings}")
        """
        from ues.models.environment import Environment

        return Environment.from_scenario_dict(self.environment, strict=strict)

    def get_event_queue(
        self,
        regenerate_ids: bool = True,
    ) -> "EventQueue":
        """Deserialize and return the EventQueue from this scenario.

        Convenience method that deserializes the stored events dict
        into an actual EventQueue instance.

        Args:
            regenerate_ids: If True (default), generate new event IDs
                to avoid conflicts. If False, preserve original IDs.

        Returns:
            New EventQueue instance.

        Example:
            >>> queue = scenario.get_event_queue(regenerate_ids=True)
            >>> print(f"Loaded {len(queue.events)} events")
        """
        from ues.models.queue import EventQueue

        return EventQueue.from_scenario_dict(self.events, regenerate_ids=regenerate_ids)

    @property
    def is_compatible(self) -> bool:
        """Check if this scenario is compatible with current UES version.

        Currently checks if the major version matches. Future versions
        may implement more sophisticated compatibility checking.

        Returns:
            True if scenario can be loaded, False otherwise.
        """
        scenario_major = self.metadata.ues_version.split(".")[0]
        current_major = UES_VERSION.split(".")[0]
        return scenario_major == current_major

    @property
    def summary(self) -> dict[str, Any]:
        """Get a summary of the scenario without full deserialization.

        Useful for displaying scenario info in a file browser or
        selection dialog without loading the full data.

        Returns:
            Dictionary with summary information.
        """
        modality_count = len(self.environment.get("modality_states", {}))
        event_count = len(self.events.get("events", []))

        return {
            "ues_version": self.metadata.ues_version,
            "scenario_version": self.metadata.scenario_version,
            "created_at": self.metadata.created_at.isoformat(),
            "author": self.metadata.author,
            "description": self.metadata.description,
            "modality_count": modality_count,
            "event_count": event_count,
            "is_compatible": self.is_compatible,
        }
