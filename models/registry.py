"""Registry for modality input and state classes.

This module provides a centralized registry for mapping modality_type strings
to their corresponding ModalityInput and ModalityState subclasses. This enables
polymorphic deserialization when loading scenarios from JSON.

Example:
    >>> from models.registry import get_modality_state_class, get_modality_input_class
    >>> state_cls = get_modality_state_class("email")
    >>> state = state_cls.model_validate(data)
    >>> input_cls = get_modality_input_class("email")
    >>> input_data = input_cls.model_validate(event_data)
"""

from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from models.base_input import ModalityInput
    from models.base_state import ModalityState

# Registry mapping modality_type strings to ModalityState subclasses
_MODALITY_STATE_REGISTRY: dict[str, Type["ModalityState"]] = {}

# Registry mapping modality_type strings to ModalityInput subclasses
_MODALITY_INPUT_REGISTRY: dict[str, Type["ModalityInput"]] = {}


# ===== State Registry Functions =====


def register_modality_state(
    modality_type: str, state_class: Type["ModalityState"]
) -> None:
    """Register a ModalityState subclass for deserialization.

    This function adds a mapping from a modality_type string to its
    corresponding ModalityState subclass. This enables the deserialization
    code to instantiate the correct concrete class when loading scenarios.

    Args:
        modality_type: The modality type identifier (e.g., "email", "location").
        state_class: The ModalityState subclass to register.

    Raises:
        ValueError: If modality_type is already registered with a different class.

    Example:
        >>> from models.modalities import EmailState
        >>> register_modality_state("email", EmailState)
    """
    if modality_type in _MODALITY_STATE_REGISTRY:
        existing = _MODALITY_STATE_REGISTRY[modality_type]
        if existing is not state_class:
            raise ValueError(
                f"modality_type '{modality_type}' is already registered "
                f"with {existing.__name__}, cannot register {state_class.__name__}"
            )
        # Already registered with same class, no-op
        return

    _MODALITY_STATE_REGISTRY[modality_type] = state_class


def get_modality_state_class(modality_type: str) -> Type["ModalityState"]:
    """Get the ModalityState subclass for a given modality_type.

    Args:
        modality_type: The modality type identifier (e.g., "email", "location").

    Returns:
        The registered ModalityState subclass.

    Raises:
        ValueError: If modality_type is not registered.

    Example:
        >>> state_cls = get_modality_state_class("email")
        >>> state = state_cls.model_validate(data)
    """
    if modality_type not in _MODALITY_STATE_REGISTRY:
        available = ", ".join(sorted(_MODALITY_STATE_REGISTRY.keys()))
        raise ValueError(
            f"Unknown modality_type: '{modality_type}'. "
            f"Available types: {available or '(none registered)'}"
        )
    return _MODALITY_STATE_REGISTRY[modality_type]


def is_modality_state_registered(modality_type: str) -> bool:
    """Check if a modality_type has a registered state class.

    Args:
        modality_type: The modality type identifier to check.

    Returns:
        True if the modality_type is registered, False otherwise.

    Example:
        >>> if is_modality_state_registered("email"):
        ...     state_cls = get_modality_state_class("email")
    """
    return modality_type in _MODALITY_STATE_REGISTRY


def list_registered_state_modalities() -> list[str]:
    """List all registered modality types for states.

    Returns:
        Sorted list of registered modality type strings.

    Example:
        >>> modalities = list_registered_state_modalities()
        >>> print(modalities)
        ['calendar', 'chat', 'email', 'location', 'sms', 'time', 'weather']
    """
    return sorted(_MODALITY_STATE_REGISTRY.keys())


def unregister_modality_state(modality_type: str) -> None:
    """Remove a modality_type from the state registry.

    Primarily useful for testing. Use with caution in production code.

    Args:
        modality_type: The modality type identifier to remove.

    Raises:
        ValueError: If modality_type is not registered.

    Example:
        >>> unregister_modality_state("email")
    """
    if modality_type not in _MODALITY_STATE_REGISTRY:
        raise ValueError(f"modality_type '{modality_type}' is not registered")
    del _MODALITY_STATE_REGISTRY[modality_type]


def clear_state_registry() -> None:
    """Clear all entries from the state registry.

    Primarily useful for testing. Use with extreme caution in production code
    as this will break deserialization until modalities are re-registered.

    Example:
        >>> clear_state_registry()
        >>> list_registered_state_modalities()
        []
    """
    _MODALITY_STATE_REGISTRY.clear()


# ===== Input Registry Functions =====


def register_modality_input(
    modality_type: str, input_class: Type["ModalityInput"]
) -> None:
    """Register a ModalityInput subclass for deserialization.

    This function adds a mapping from a modality_type string to its
    corresponding ModalityInput subclass. This enables the deserialization
    code to instantiate the correct concrete class when loading events.

    Args:
        modality_type: The modality type identifier (e.g., "email", "location").
        input_class: The ModalityInput subclass to register.

    Raises:
        ValueError: If modality_type is already registered with a different class.

    Example:
        >>> from models.modalities import EmailInput
        >>> register_modality_input("email", EmailInput)
    """
    if modality_type in _MODALITY_INPUT_REGISTRY:
        existing = _MODALITY_INPUT_REGISTRY[modality_type]
        if existing is not input_class:
            raise ValueError(
                f"modality_type '{modality_type}' is already registered "
                f"with {existing.__name__}, cannot register {input_class.__name__}"
            )
        # Already registered with same class, no-op
        return

    _MODALITY_INPUT_REGISTRY[modality_type] = input_class


def get_modality_input_class(modality_type: str) -> Type["ModalityInput"]:
    """Get the ModalityInput subclass for a given modality_type.

    Args:
        modality_type: The modality type identifier (e.g., "email", "location").

    Returns:
        The registered ModalityInput subclass.

    Raises:
        ValueError: If modality_type is not registered.

    Example:
        >>> input_cls = get_modality_input_class("email")
        >>> input_data = input_cls.model_validate(data)
    """
    if modality_type not in _MODALITY_INPUT_REGISTRY:
        available = ", ".join(sorted(_MODALITY_INPUT_REGISTRY.keys()))
        raise ValueError(
            f"Unknown modality_type: '{modality_type}'. "
            f"Available types: {available or '(none registered)'}"
        )
    return _MODALITY_INPUT_REGISTRY[modality_type]


def is_modality_input_registered(modality_type: str) -> bool:
    """Check if a modality_type has a registered input class.

    Args:
        modality_type: The modality type identifier to check.

    Returns:
        True if the modality_type is registered, False otherwise.

    Example:
        >>> if is_modality_input_registered("email"):
        ...     input_cls = get_modality_input_class("email")
    """
    return modality_type in _MODALITY_INPUT_REGISTRY


def list_registered_input_modalities() -> list[str]:
    """List all registered modality types for inputs.

    Returns:
        Sorted list of registered modality type strings.

    Example:
        >>> modalities = list_registered_input_modalities()
        >>> print(modalities)
        ['calendar', 'chat', 'email', 'location', 'sms', 'time', 'weather']
    """
    return sorted(_MODALITY_INPUT_REGISTRY.keys())


def unregister_modality_input(modality_type: str) -> None:
    """Remove a modality_type from the input registry.

    Primarily useful for testing. Use with caution in production code.

    Args:
        modality_type: The modality type identifier to remove.

    Raises:
        ValueError: If modality_type is not registered.

    Example:
        >>> unregister_modality_input("email")
    """
    if modality_type not in _MODALITY_INPUT_REGISTRY:
        raise ValueError(f"modality_type '{modality_type}' is not registered")
    del _MODALITY_INPUT_REGISTRY[modality_type]


def clear_input_registry() -> None:
    """Clear all entries from the input registry.

    Primarily useful for testing. Use with extreme caution in production code
    as this will break deserialization until modalities are re-registered.

    Example:
        >>> clear_input_registry()
        >>> list_registered_input_modalities()
        []
    """
    _MODALITY_INPUT_REGISTRY.clear()


# ===== Convenience Functions =====


def clear_all_registries() -> None:
    """Clear both state and input registries.

    Primarily useful for testing. Use with extreme caution in production code.

    Example:
        >>> clear_all_registries()
    """
    clear_state_registry()
    clear_input_registry()


def _register_default_modalities() -> None:
    """Register all built-in modality types.

    This function is called automatically when the registry module is imported.
    It registers all Priority 1 and Priority 2 modalities that are fully
    implemented.

    Priority 1 Modalities: location, time, weather
    Priority 2 Modalities: chat, email, calendar, sms
    """
    # Import here to avoid circular imports at module level
    from models.modalities import (
        CalendarInput,
        CalendarState,
        ChatInput,
        ChatState,
        EmailInput,
        EmailState,
        LocationInput,
        LocationState,
        SMSInput,
        SMSState,
        TimeInput,
        TimeState,
        WeatherInput,
        WeatherState,
    )

    # Priority 1 Modalities
    register_modality_state("location", LocationState)
    register_modality_input("location", LocationInput)

    register_modality_state("time", TimeState)
    register_modality_input("time", TimeInput)

    register_modality_state("weather", WeatherState)
    register_modality_input("weather", WeatherInput)

    # Priority 2 Modalities
    register_modality_state("chat", ChatState)
    register_modality_input("chat", ChatInput)

    register_modality_state("email", EmailState)
    register_modality_input("email", EmailInput)

    register_modality_state("calendar", CalendarState)
    register_modality_input("calendar", CalendarInput)

    register_modality_state("sms", SMSState)
    register_modality_input("sms", SMSInput)


# Auto-register default modalities on module import
_register_default_modalities()
