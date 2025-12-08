"""Environment model - container for all current simulation state."""

from typing import Any

from pydantic import BaseModel, Field, model_validator

from models.base_state import ModalityState
from models.time import SimulatorTime


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

    class Config:
        arbitrary_types_allowed = True

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
            >>> state.apply_input(email_input)
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