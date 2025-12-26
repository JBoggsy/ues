"""Unit tests for the modality registry.

Tests cover:
- State registry: registration, retrieval, checking, listing, unregistering, clearing
- Input registry: registration, retrieval, checking, listing, unregistering, clearing
- Auto-registration of default modalities
- Error handling for invalid operations
"""

import pytest

from models.registry import (
    clear_all_registries,
    clear_input_registry,
    clear_state_registry,
    get_modality_input_class,
    get_modality_state_class,
    is_modality_input_registered,
    is_modality_state_registered,
    list_registered_input_modalities,
    list_registered_state_modalities,
    register_modality_input,
    register_modality_state,
    unregister_modality_input,
    unregister_modality_state,
    _register_default_modalities,
)
from models.base_input import ModalityInput
from models.base_state import ModalityState
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


# ===== Fixtures =====


@pytest.fixture
def clean_registries():
    """Fixture that clears registries before and after each test.
    
    This ensures tests are isolated and don't affect each other.
    After the test, it re-registers the default modalities.
    """
    clear_all_registries()
    yield
    clear_all_registries()
    _register_default_modalities()


@pytest.fixture
def populated_registries():
    """Fixture that ensures default modalities are registered.
    
    This is the normal state after module import.
    """
    # Ensure defaults are registered (they should be from import)
    if not is_modality_state_registered("email"):
        _register_default_modalities()
    yield


# ===== State Registry Tests =====


class TestStateRegistryBasicOperations:
    """Tests for basic state registry operations."""

    def test_get_registered_state_class(self, populated_registries):
        """Get a registered state class returns the correct class."""
        state_cls = get_modality_state_class("email")
        assert state_cls is EmailState

    def test_get_all_priority1_state_classes(self, populated_registries):
        """All Priority 1 state classes are registered and retrievable."""
        assert get_modality_state_class("location") is LocationState
        assert get_modality_state_class("time") is TimeState
        assert get_modality_state_class("weather") is WeatherState

    def test_get_all_priority2_state_classes(self, populated_registries):
        """All Priority 2 state classes are registered and retrievable."""
        assert get_modality_state_class("chat") is ChatState
        assert get_modality_state_class("email") is EmailState
        assert get_modality_state_class("calendar") is CalendarState
        assert get_modality_state_class("sms") is SMSState

    def test_is_state_registered_true(self, populated_registries):
        """is_modality_state_registered returns True for registered types."""
        assert is_modality_state_registered("email") is True
        assert is_modality_state_registered("location") is True
        assert is_modality_state_registered("sms") is True

    def test_is_state_registered_false(self, populated_registries):
        """is_modality_state_registered returns False for unregistered types."""
        assert is_modality_state_registered("unknown") is False
        assert is_modality_state_registered("") is False
        assert is_modality_state_registered("EMAIL") is False  # Case sensitive

    def test_list_state_modalities(self, populated_registries):
        """list_registered_state_modalities returns sorted list of all registered types."""
        modalities = list_registered_state_modalities()
        expected = ["calendar", "chat", "email", "location", "sms", "time", "weather"]
        assert modalities == expected

    def test_list_state_modalities_is_sorted(self, populated_registries):
        """list_registered_state_modalities returns a sorted list."""
        modalities = list_registered_state_modalities()
        assert modalities == sorted(modalities)


class TestStateRegistryRegistration:
    """Tests for state registry registration operations."""

    def test_register_new_state(self, clean_registries):
        """Registering a new state class succeeds."""
        register_modality_state("email", EmailState)
        assert is_modality_state_registered("email")
        assert get_modality_state_class("email") is EmailState

    def test_register_same_class_twice_is_noop(self, clean_registries):
        """Registering the same class twice is a no-op (no error)."""
        register_modality_state("email", EmailState)
        register_modality_state("email", EmailState)  # Should not raise
        assert get_modality_state_class("email") is EmailState

    def test_register_different_class_same_type_raises(self, clean_registries):
        """Registering a different class with same type raises ValueError."""
        register_modality_state("email", EmailState)
        with pytest.raises(ValueError) as exc_info:
            register_modality_state("email", ChatState)
        assert "already registered" in str(exc_info.value)
        assert "EmailState" in str(exc_info.value)
        assert "ChatState" in str(exc_info.value)

    def test_register_multiple_states(self, clean_registries):
        """Multiple different state types can be registered."""
        register_modality_state("email", EmailState)
        register_modality_state("chat", ChatState)
        register_modality_state("location", LocationState)
        
        assert is_modality_state_registered("email")
        assert is_modality_state_registered("chat")
        assert is_modality_state_registered("location")
        assert list_registered_state_modalities() == ["chat", "email", "location"]


class TestStateRegistryUnregistration:
    """Tests for state registry unregistration operations."""

    def test_unregister_state(self, clean_registries):
        """Unregistering a registered state removes it."""
        register_modality_state("email", EmailState)
        assert is_modality_state_registered("email")
        
        unregister_modality_state("email")
        assert not is_modality_state_registered("email")

    def test_unregister_nonexistent_state_raises(self, clean_registries):
        """Unregistering a non-existent state raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            unregister_modality_state("nonexistent")
        assert "not registered" in str(exc_info.value)

    def test_clear_state_registry(self, clean_registries):
        """clear_state_registry removes all registered states."""
        register_modality_state("email", EmailState)
        register_modality_state("chat", ChatState)
        
        clear_state_registry()
        
        assert list_registered_state_modalities() == []
        assert not is_modality_state_registered("email")
        assert not is_modality_state_registered("chat")


class TestStateRegistryErrors:
    """Tests for state registry error handling."""

    def test_get_unregistered_state_raises(self, clean_registries):
        """Getting an unregistered state raises ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            get_modality_state_class("nonexistent")
        assert "Unknown modality_type" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_get_unregistered_state_shows_available(self, clean_registries):
        """Error message shows available types when some are registered."""
        register_modality_state("email", EmailState)
        register_modality_state("chat", ChatState)
        
        with pytest.raises(ValueError) as exc_info:
            get_modality_state_class("nonexistent")
        assert "chat" in str(exc_info.value)
        assert "email" in str(exc_info.value)

    def test_get_unregistered_state_empty_registry(self, clean_registries):
        """Error message handles empty registry gracefully."""
        with pytest.raises(ValueError) as exc_info:
            get_modality_state_class("nonexistent")
        assert "(none registered)" in str(exc_info.value)


# ===== Input Registry Tests =====


class TestInputRegistryBasicOperations:
    """Tests for basic input registry operations."""

    def test_get_registered_input_class(self, populated_registries):
        """Get a registered input class returns the correct class."""
        input_cls = get_modality_input_class("email")
        assert input_cls is EmailInput

    def test_get_all_priority1_input_classes(self, populated_registries):
        """All Priority 1 input classes are registered and retrievable."""
        assert get_modality_input_class("location") is LocationInput
        assert get_modality_input_class("time") is TimeInput
        assert get_modality_input_class("weather") is WeatherInput

    def test_get_all_priority2_input_classes(self, populated_registries):
        """All Priority 2 input classes are registered and retrievable."""
        assert get_modality_input_class("chat") is ChatInput
        assert get_modality_input_class("email") is EmailInput
        assert get_modality_input_class("calendar") is CalendarInput
        assert get_modality_input_class("sms") is SMSInput

    def test_is_input_registered_true(self, populated_registries):
        """is_modality_input_registered returns True for registered types."""
        assert is_modality_input_registered("email") is True
        assert is_modality_input_registered("location") is True
        assert is_modality_input_registered("sms") is True

    def test_is_input_registered_false(self, populated_registries):
        """is_modality_input_registered returns False for unregistered types."""
        assert is_modality_input_registered("unknown") is False
        assert is_modality_input_registered("") is False
        assert is_modality_input_registered("EMAIL") is False  # Case sensitive

    def test_list_input_modalities(self, populated_registries):
        """list_registered_input_modalities returns sorted list of all registered types."""
        modalities = list_registered_input_modalities()
        expected = ["calendar", "chat", "email", "location", "sms", "time", "weather"]
        assert modalities == expected

    def test_list_input_modalities_is_sorted(self, populated_registries):
        """list_registered_input_modalities returns a sorted list."""
        modalities = list_registered_input_modalities()
        assert modalities == sorted(modalities)


class TestInputRegistryRegistration:
    """Tests for input registry registration operations."""

    def test_register_new_input(self, clean_registries):
        """Registering a new input class succeeds."""
        register_modality_input("email", EmailInput)
        assert is_modality_input_registered("email")
        assert get_modality_input_class("email") is EmailInput

    def test_register_same_class_twice_is_noop(self, clean_registries):
        """Registering the same class twice is a no-op (no error)."""
        register_modality_input("email", EmailInput)
        register_modality_input("email", EmailInput)  # Should not raise
        assert get_modality_input_class("email") is EmailInput

    def test_register_different_class_same_type_raises(self, clean_registries):
        """Registering a different class with same type raises ValueError."""
        register_modality_input("email", EmailInput)
        with pytest.raises(ValueError) as exc_info:
            register_modality_input("email", ChatInput)
        assert "already registered" in str(exc_info.value)
        assert "EmailInput" in str(exc_info.value)
        assert "ChatInput" in str(exc_info.value)

    def test_register_multiple_inputs(self, clean_registries):
        """Multiple different input types can be registered."""
        register_modality_input("email", EmailInput)
        register_modality_input("chat", ChatInput)
        register_modality_input("location", LocationInput)
        
        assert is_modality_input_registered("email")
        assert is_modality_input_registered("chat")
        assert is_modality_input_registered("location")
        assert list_registered_input_modalities() == ["chat", "email", "location"]


class TestInputRegistryUnregistration:
    """Tests for input registry unregistration operations."""

    def test_unregister_input(self, clean_registries):
        """Unregistering a registered input removes it."""
        register_modality_input("email", EmailInput)
        assert is_modality_input_registered("email")
        
        unregister_modality_input("email")
        assert not is_modality_input_registered("email")

    def test_unregister_nonexistent_input_raises(self, clean_registries):
        """Unregistering a non-existent input raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            unregister_modality_input("nonexistent")
        assert "not registered" in str(exc_info.value)

    def test_clear_input_registry(self, clean_registries):
        """clear_input_registry removes all registered inputs."""
        register_modality_input("email", EmailInput)
        register_modality_input("chat", ChatInput)
        
        clear_input_registry()
        
        assert list_registered_input_modalities() == []
        assert not is_modality_input_registered("email")
        assert not is_modality_input_registered("chat")


class TestInputRegistryErrors:
    """Tests for input registry error handling."""

    def test_get_unregistered_input_raises(self, clean_registries):
        """Getting an unregistered input raises ValueError with helpful message."""
        with pytest.raises(ValueError) as exc_info:
            get_modality_input_class("nonexistent")
        assert "Unknown modality_type" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_get_unregistered_input_shows_available(self, clean_registries):
        """Error message shows available types when some are registered."""
        register_modality_input("email", EmailInput)
        register_modality_input("chat", ChatInput)
        
        with pytest.raises(ValueError) as exc_info:
            get_modality_input_class("nonexistent")
        assert "chat" in str(exc_info.value)
        assert "email" in str(exc_info.value)

    def test_get_unregistered_input_empty_registry(self, clean_registries):
        """Error message handles empty registry gracefully."""
        with pytest.raises(ValueError) as exc_info:
            get_modality_input_class("nonexistent")
        assert "(none registered)" in str(exc_info.value)


# ===== Combined Registry Tests =====


class TestCombinedRegistryOperations:
    """Tests for operations that affect both registries."""

    def test_clear_all_registries(self, clean_registries):
        """clear_all_registries clears both state and input registries."""
        register_modality_state("email", EmailState)
        register_modality_input("email", EmailInput)
        
        clear_all_registries()
        
        assert list_registered_state_modalities() == []
        assert list_registered_input_modalities() == []

    def test_state_and_input_registries_are_independent(self, clean_registries):
        """State and input registries are independent."""
        register_modality_state("email", EmailState)
        
        assert is_modality_state_registered("email")
        assert not is_modality_input_registered("email")
        
        register_modality_input("chat", ChatInput)
        
        assert not is_modality_state_registered("chat")
        assert is_modality_input_registered("chat")

    def test_same_type_different_registries(self, clean_registries):
        """Same modality_type can be registered in both registries independently."""
        register_modality_state("email", EmailState)
        register_modality_input("email", EmailInput)
        
        assert get_modality_state_class("email") is EmailState
        assert get_modality_input_class("email") is EmailInput


# ===== Auto-Registration Tests =====


class TestAutoRegistration:
    """Tests for automatic registration of default modalities."""

    def test_default_modalities_registered_on_import(self, populated_registries):
        """Default modalities are registered when the module is imported."""
        # These should all be registered from module import
        expected_modalities = ["calendar", "chat", "email", "location", "sms", "time", "weather"]
        
        assert list_registered_state_modalities() == expected_modalities
        assert list_registered_input_modalities() == expected_modalities

    def test_reregister_defaults_is_idempotent(self, populated_registries):
        """Calling _register_default_modalities multiple times is safe."""
        # Should not raise even though already registered
        _register_default_modalities()
        _register_default_modalities()
        
        expected = ["calendar", "chat", "email", "location", "sms", "time", "weather"]
        assert list_registered_state_modalities() == expected

    def test_reregister_defaults_after_clear(self, clean_registries):
        """Can re-register defaults after clearing registries."""
        # clean_registries fixture clears everything
        assert list_registered_state_modalities() == []
        
        _register_default_modalities()
        
        expected = ["calendar", "chat", "email", "location", "sms", "time", "weather"]
        assert list_registered_state_modalities() == expected
        assert list_registered_input_modalities() == expected


# ===== Registry State Consistency Tests =====


class TestRegistryConsistency:
    """Tests for registry state consistency."""

    def test_state_and_input_have_same_modalities(self, populated_registries):
        """State and input registries have the same set of modalities."""
        state_modalities = set(list_registered_state_modalities())
        input_modalities = set(list_registered_input_modalities())
        assert state_modalities == input_modalities

    def test_registered_state_class_has_matching_modality_type(self, populated_registries):
        """Each registered state class has modality_type matching its registration key."""
        for modality_type in list_registered_state_modalities():
            state_cls = get_modality_state_class(modality_type)
            # Create a minimal instance to check modality_type
            # Note: We can't easily instantiate without required fields,
            # so we check the default value in the Field definition
            default_type = state_cls.model_fields["modality_type"].default
            assert default_type == modality_type, (
                f"State class {state_cls.__name__} has modality_type default "
                f"'{default_type}' but is registered as '{modality_type}'"
            )

    def test_registered_input_class_has_matching_modality_type(self, populated_registries):
        """Each registered input class has modality_type matching its registration key."""
        for modality_type in list_registered_input_modalities():
            input_cls = get_modality_input_class(modality_type)
            # Check the default value in the Field definition
            default_type = input_cls.model_fields["modality_type"].default
            assert default_type == modality_type, (
                f"Input class {input_cls.__name__} has modality_type default "
                f"'{default_type}' but is registered as '{modality_type}'"
            )
