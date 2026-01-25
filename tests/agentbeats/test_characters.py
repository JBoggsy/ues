"""Tests for character profile models.

Tests cover validation, serialization, and edge cases for character profiles
used in the Response Generator Sub-agents.
"""

from datetime import timedelta

import pytest
from pydantic import ValidationError

from agentbeats.green.characters import (
    CharacterProfile,
    CharacterRegistry,
    ContactType,
    ResponseTiming,
    RSVPBehavior,
)


# =============================================================================
# ResponseTiming Tests
# =============================================================================


class TestResponseTiming:
    """Tests for ResponseTiming configuration model."""

    def test_default_values(self):
        """Test default timing configuration."""
        timing = ResponseTiming()
        assert timing.base_delay_minutes == 30
        assert timing.variance_minutes == 30
        assert timing.work_hours_only is False
        assert timing.work_hours_start == "09:00"
        assert timing.work_hours_end == "17:00"
        assert timing.timezone == "America/New_York"

    def test_custom_values(self):
        """Test custom timing configuration."""
        timing = ResponseTiming(
            base_delay_minutes=60,
            variance_minutes=15,
            work_hours_only=True,
            work_hours_start="08:00",
            work_hours_end="18:00",
            timezone="Europe/London",
        )
        assert timing.base_delay_minutes == 60
        assert timing.variance_minutes == 15
        assert timing.work_hours_only is True

    def test_negative_base_delay_fails(self):
        """Base delay must be non-negative."""
        with pytest.raises(ValidationError):
            ResponseTiming(base_delay_minutes=-1)

    def test_negative_variance_fails(self):
        """Variance must be non-negative."""
        with pytest.raises(ValidationError):
            ResponseTiming(variance_minutes=-5)

    def test_zero_values_valid(self):
        """Zero is a valid value for delays."""
        timing = ResponseTiming(base_delay_minutes=0, variance_minutes=0)
        assert timing.base_delay_minutes == 0
        assert timing.variance_minutes == 0

    def test_invalid_work_hours_format_fails(self):
        """Work hours must match HH:MM pattern."""
        with pytest.raises(ValidationError):
            ResponseTiming(work_hours_start="9:00")  # Missing leading zero

        with pytest.raises(ValidationError):
            ResponseTiming(work_hours_end="5pm")  # Wrong format

    def test_get_base_delay(self):
        """Test base delay as timedelta."""
        timing = ResponseTiming(base_delay_minutes=45)
        assert timing.get_base_delay() == timedelta(minutes=45)

    def test_get_max_delay(self):
        """Test maximum delay calculation."""
        timing = ResponseTiming(base_delay_minutes=30, variance_minutes=20)
        assert timing.get_max_delay() == timedelta(minutes=50)

    def test_from_legacy_format_basic(self):
        """Convert basic legacy format."""
        legacy = {
            "min_delay_minutes": 10,
            "max_delay_minutes": 30,
        }
        timing = ResponseTiming.from_legacy_format(legacy)
        assert timing.base_delay_minutes == 10
        assert timing.variance_minutes == 20  # 30 - 10

    def test_from_legacy_format_with_work_hours(self):
        """Convert legacy format with work hours."""
        legacy = {
            "min_delay_minutes": 5,
            "max_delay_minutes": 15,
            "work_hours_only": True,
            "work_hours": {
                "start": "10:00",
                "end": "16:00",
                "timezone": "America/Los_Angeles",
            },
        }
        timing = ResponseTiming.from_legacy_format(legacy)
        assert timing.work_hours_only is True
        assert timing.work_hours_start == "10:00"
        assert timing.work_hours_end == "16:00"
        assert timing.timezone == "America/Los_Angeles"

    def test_from_legacy_format_empty(self):
        """Convert empty legacy format uses defaults."""
        timing = ResponseTiming.from_legacy_format({})
        assert timing.base_delay_minutes == 30
        assert timing.variance_minutes == 30  # max(60) - base(30)

    def test_from_legacy_format_min_equals_max(self):
        """Handle min == max in legacy format."""
        legacy = {
            "min_delay_minutes": 20,
            "max_delay_minutes": 20,
        }
        timing = ResponseTiming.from_legacy_format(legacy)
        assert timing.base_delay_minutes == 20
        assert timing.variance_minutes == 0


# =============================================================================
# RSVPBehavior Enum Tests
# =============================================================================


class TestRSVPBehavior:
    """Tests for RSVPBehavior enum."""

    def test_all_values_exist(self):
        """All expected RSVP behaviors exist."""
        assert RSVPBehavior.IMMEDIATE_YES.value == "immediate_yes"
        assert RSVPBehavior.QUICK_YES.value == "quick_yes"
        assert RSVPBehavior.TENTATIVE_YES.value == "tentative_yes"
        assert RSVPBehavior.MAYBE.value == "maybe"
        assert RSVPBehavior.DECLINE.value == "decline"
        assert RSVPBehavior.NO_RESPONSE.value == "no_response"

    def test_string_conversion(self):
        """Enum values can be created from strings."""
        assert RSVPBehavior("quick_yes") == RSVPBehavior.QUICK_YES


# =============================================================================
# ContactType Enum Tests
# =============================================================================


class TestContactType:
    """Tests for ContactType enum."""

    def test_all_values_exist(self):
        """All expected contact types exist."""
        assert ContactType.GUEST.value == "guest"
        assert ContactType.VENDOR.value == "vendor"
        assert ContactType.COLLEAGUE.value == "colleague"
        assert ContactType.OTHER.value == "other"


# =============================================================================
# CharacterProfile Tests
# =============================================================================


class TestCharacterProfile:
    """Tests for CharacterProfile model."""

    def test_minimal_valid(self):
        """Create with name only."""
        profile = CharacterProfile(name="Test Person")
        assert profile.name == "Test Person"
        assert profile.email is None
        assert profile.phone is None
        assert profile.role == "Contact"
        assert profile.contact_type == ContactType.OTHER
        assert profile.rsvp_behavior == RSVPBehavior.QUICK_YES

    def test_full_profile(self):
        """Create with all fields."""
        profile = CharacterProfile(
            name="Jamie Walsh",
            email="jamie@example.com",
            phone="+15551234567",
            role="Best Friend",
            relationship="College roommate",
            contact_type=ContactType.GUEST,
            personality="Outgoing, enthusiastic, supportive",
            communication_style="Casual with lots of exclamation marks!",
            response_timing=ResponseTiming(base_delay_minutes=15, variance_minutes=10),
            rsvp_behavior=RSVPBehavior.IMMEDIATE_YES,
            special_instructions="Always mentions their dog Max",
            example_response="OMG yes! I'll be there! Can I bring Max?",
        )
        assert profile.name == "Jamie Walsh"
        assert profile.email == "jamie@example.com"
        assert profile.phone == "+15551234567"
        assert profile.contact_type == ContactType.GUEST

    def test_empty_name_fails(self):
        """Name cannot be empty."""
        with pytest.raises(ValidationError):
            CharacterProfile(name="")

    def test_email_validation(self):
        """Email must be valid format."""
        # Valid email
        profile = CharacterProfile(name="Test", email="test@example.com")
        assert profile.email == "test@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            CharacterProfile(name="Test", email="not-an-email")

    def test_phone_normalization(self):
        """Phone numbers are normalized."""
        profile = CharacterProfile(name="Test", phone="(555) 123-4567")
        assert profile.phone == "5551234567"

        profile = CharacterProfile(name="Test", phone="+1 555 123 4567")
        assert profile.phone == "+15551234567"

    def test_phone_normalization_empty(self):
        """Empty phone string becomes None."""
        profile = CharacterProfile(name="Test", phone="")
        assert profile.phone is None

    def test_extra_fields_preserved(self):
        """Extra dict stores additional data."""
        profile = CharacterProfile(
            name="Test",
            extra={"custom_field": "custom_value", "priority": 1},
        )
        assert profile.extra["custom_field"] == "custom_value"
        assert profile.extra["priority"] == 1

    def test_build_system_prompt_basic(self):
        """System prompt includes basic info."""
        profile = CharacterProfile(
            name="Jamie Walsh",
            role="Best Friend",
            personality="Enthusiastic",
            communication_style="Casual",
        )
        prompt = profile.build_system_prompt()

        assert "Jamie Walsh" in prompt
        assert "Best Friend" in prompt
        assert "Enthusiastic" in prompt
        assert "Casual" in prompt

    def test_build_system_prompt_with_relationship(self):
        """System prompt includes relationship."""
        profile = CharacterProfile(
            name="Test Person",
            role="Contact",
            relationship="College friend",
            personality="Friendly",
            communication_style="Standard",
        )
        prompt = profile.build_system_prompt()
        assert "College friend" in prompt

    def test_build_system_prompt_with_instructions(self):
        """System prompt includes special instructions."""
        profile = CharacterProfile(
            name="Test Person",
            role="Contact",
            personality="Friendly",
            communication_style="Standard",
            special_instructions="Always ask about the weather",
        )
        prompt = profile.build_system_prompt()
        assert "Always ask about the weather" in prompt

    def test_build_system_prompt_with_example(self):
        """System prompt includes example response."""
        profile = CharacterProfile(
            name="Test Person",
            role="Contact",
            personality="Friendly",
            communication_style="Standard",
            example_response="Sure thing! Count me in!",
        )
        prompt = profile.build_system_prompt()
        assert "Sure thing! Count me in!" in prompt

    def test_from_scenario_format_basic(self):
        """Parse basic scenario format."""
        data = {
            "name": "Jamie Walsh",
            "personality": "Friendly and outgoing",
            "communication_style": "Casual",
        }
        profile = CharacterProfile.from_scenario_format("jamie@example.com", data)

        assert profile.name == "Jamie Walsh"
        assert profile.email == "jamie@example.com"
        assert profile.personality == "Friendly and outgoing"

    def test_from_scenario_format_with_phone(self):
        """Parse scenario format with phone identifier."""
        data = {
            "name": "Alex",
            "personality": "Chill",
        }
        profile = CharacterProfile.from_scenario_format("+15551234567", data)

        assert profile.name == "Alex"
        assert profile.phone == "+15551234567"
        assert profile.email is None

    def test_from_scenario_format_with_response_timing(self):
        """Parse scenario format with response timing."""
        data = {
            "name": "Test",
            "response_timing": {
                "base_delay_minutes": 45,
                "variance_minutes": 15,
            },
        }
        profile = CharacterProfile.from_scenario_format("test@example.com", data)

        assert profile.response_timing.base_delay_minutes == 45
        assert profile.response_timing.variance_minutes == 15

    def test_from_scenario_format_with_legacy_responsiveness(self):
        """Parse scenario format with legacy responsiveness dict."""
        data = {
            "name": "Test",
            "responsiveness": {
                "min_delay_minutes": 10,
                "max_delay_minutes": 40,
            },
        }
        profile = CharacterProfile.from_scenario_format("test@example.com", data)

        assert profile.response_timing.base_delay_minutes == 10
        assert profile.response_timing.variance_minutes == 30

    def test_from_scenario_format_with_contact_type(self):
        """Parse scenario format with contact type."""
        data = {
            "name": "Bakery",
            "contact_type": "vendor",
        }
        profile = CharacterProfile.from_scenario_format("orders@bakery.com", data)
        assert profile.contact_type == ContactType.VENDOR

    def test_from_scenario_format_with_rsvp_behavior(self):
        """Parse scenario format with RSVP behavior."""
        data = {
            "name": "Test",
            "response_behavior": {
                "rsvp": "tentative_yes",
            },
        }
        profile = CharacterProfile.from_scenario_format("test@example.com", data)
        assert profile.rsvp_behavior == RSVPBehavior.TENTATIVE_YES

    def test_from_scenario_format_preserves_extra(self):
        """Parse scenario format preserves unknown fields."""
        data = {
            "name": "Test",
            "custom_field": "custom_value",
            "another_field": 123,
        }
        profile = CharacterProfile.from_scenario_format("test@example.com", data)

        assert profile.extra["custom_field"] == "custom_value"
        assert profile.extra["another_field"] == 123

    def test_from_scenario_format_unknown_contact_type(self):
        """Unknown contact type defaults to OTHER."""
        data = {
            "name": "Test",
            "contact_type": "unknown_type",
        }
        profile = CharacterProfile.from_scenario_format("test@example.com", data)
        assert profile.contact_type == ContactType.OTHER

    def test_from_scenario_format_unknown_rsvp(self):
        """Unknown RSVP behavior defaults to QUICK_YES."""
        data = {
            "name": "Test",
            "response_behavior": {
                "rsvp": "unknown_behavior",
            },
        }
        profile = CharacterProfile.from_scenario_format("test@example.com", data)
        assert profile.rsvp_behavior == RSVPBehavior.QUICK_YES


# =============================================================================
# CharacterRegistry Tests
# =============================================================================


class TestCharacterRegistry:
    """Tests for CharacterRegistry lookup functionality."""

    @pytest.fixture
    def sample_characters(self) -> list[CharacterProfile]:
        """Create sample characters for testing."""
        return [
            CharacterProfile(
                name="Jamie Walsh",
                email="jamie@example.com",
                phone="+15551111111",
            ),
            CharacterProfile(
                name="Alex Chen",
                email="alex@example.com",
                phone="+15552222222",
            ),
            CharacterProfile(
                name="Phone Only",
                phone="+15553333333",
            ),
            CharacterProfile(
                name="Email Only",
                email="emailonly@example.com",
            ),
        ]

    def test_empty_registry(self):
        """Empty registry has no characters."""
        registry = CharacterRegistry()
        assert len(registry) == 0
        assert registry.list_all() == []

    def test_register_characters(self, sample_characters):
        """Characters can be registered."""
        registry = CharacterRegistry()
        for char in sample_characters:
            registry.register(char)

        assert len(registry) == 4

    def test_init_with_characters(self, sample_characters):
        """Registry can be initialized with character list."""
        registry = CharacterRegistry(sample_characters)
        assert len(registry) == 4

    def test_get_by_email(self, sample_characters):
        """Look up character by email."""
        registry = CharacterRegistry(sample_characters)

        char = registry.get_by_email("jamie@example.com")
        assert char is not None
        assert char.name == "Jamie Walsh"

    def test_get_by_email_case_insensitive(self, sample_characters):
        """Email lookup is case-insensitive."""
        registry = CharacterRegistry(sample_characters)

        char = registry.get_by_email("JAMIE@EXAMPLE.COM")
        assert char is not None
        assert char.name == "Jamie Walsh"

    def test_get_by_email_not_found(self, sample_characters):
        """Return None for unknown email."""
        registry = CharacterRegistry(sample_characters)
        assert registry.get_by_email("unknown@example.com") is None

    def test_get_by_phone(self, sample_characters):
        """Look up character by phone."""
        registry = CharacterRegistry(sample_characters)

        char = registry.get_by_phone("+15551111111")
        assert char is not None
        assert char.name == "Jamie Walsh"

    def test_get_by_phone_normalized(self, sample_characters):
        """Phone lookup ignores formatting."""
        registry = CharacterRegistry(sample_characters)

        # Lookup with different formatting but same digits
        char = registry.get_by_phone("+1 (555) 111-1111")
        assert char is not None
        assert char.name == "Jamie Walsh"

        # Also test without country code - this won't match since stored has +1
        char_no_prefix = registry.get_by_phone("(555) 111-1111")
        assert char_no_prefix is None  # Won't match +15551111111

    def test_get_by_phone_not_found(self, sample_characters):
        """Return None for unknown phone."""
        registry = CharacterRegistry(sample_characters)
        assert registry.get_by_phone("+15559999999") is None

    def test_get_by_identifier_email(self, sample_characters):
        """Identifier lookup with email."""
        registry = CharacterRegistry(sample_characters)

        char = registry.get_by_identifier("alex@example.com")
        assert char is not None
        assert char.name == "Alex Chen"

    def test_get_by_identifier_phone(self, sample_characters):
        """Identifier lookup with phone."""
        registry = CharacterRegistry(sample_characters)

        char = registry.get_by_identifier("+15553333333")
        assert char is not None
        assert char.name == "Phone Only"

    def test_list_all(self, sample_characters):
        """List all registered characters."""
        registry = CharacterRegistry(sample_characters)
        all_chars = registry.list_all()

        assert len(all_chars) == 4
        names = {c.name for c in all_chars}
        assert "Jamie Walsh" in names
        assert "Phone Only" in names

    def test_list_emails(self, sample_characters):
        """List all registered emails."""
        registry = CharacterRegistry(sample_characters)
        emails = registry.list_emails()

        assert "jamie@example.com" in emails
        assert "alex@example.com" in emails
        assert "emailonly@example.com" in emails
        assert len(emails) == 3  # Phone Only has no email

    def test_list_phones(self, sample_characters):
        """List all registered phones."""
        registry = CharacterRegistry(sample_characters)
        phones = registry.list_phones()

        assert "+15551111111" in phones
        assert "+15552222222" in phones
        assert "+15553333333" in phones
        assert len(phones) == 3  # Email Only has no phone

    def test_contains_email(self, sample_characters):
        """Check if email is in registry."""
        registry = CharacterRegistry(sample_characters)

        assert "jamie@example.com" in registry
        assert "unknown@example.com" not in registry

    def test_contains_phone(self, sample_characters):
        """Check if phone is in registry."""
        registry = CharacterRegistry(sample_characters)

        assert "+15551111111" in registry
        assert "+15559999999" not in registry

    def test_from_dict(self):
        """Create registry from dict format."""
        data = {
            "jamie@example.com": {
                "name": "Jamie Walsh",
                "personality": "Friendly",
            },
            "+15551234567": {
                "name": "Alex",
                "personality": "Chill",
            },
        }
        registry = CharacterRegistry.from_dict(data)

        assert len(registry) == 2
        assert registry.get_by_email("jamie@example.com") is not None
        assert registry.get_by_phone("+15551234567") is not None

    def test_from_scenario_characters(self):
        """Create registry from full scenario format."""
        scenario_data = {
            "characters": {
                "jamie@example.com": {
                    "name": "Jamie Walsh",
                    "personality": "Friendly",
                },
                "taylor@example.com": {
                    "name": "Taylor",
                    "personality": "Reserved",
                },
            },
            "sms_characters": {
                "+15551111111": {
                    "name": "Alex",
                    "nickname": "Lex",
                },
            },
            "vendors": {
                "orders@bakery.com": {
                    "name": "Sweet Treats Bakery",
                    "role": "Bakery",
                },
            },
        }
        registry = CharacterRegistry.from_scenario_characters(scenario_data)

        assert len(registry) == 4

        # Email characters
        jamie = registry.get_by_email("jamie@example.com")
        assert jamie is not None
        assert jamie.name == "Jamie Walsh"

        # SMS characters
        alex = registry.get_by_phone("+15551111111")
        assert alex is not None
        assert alex.name == "Alex"

        # Vendors
        bakery = registry.get_by_email("orders@bakery.com")
        assert bakery is not None
        assert bakery.name == "Sweet Treats Bakery"

    def test_from_scenario_characters_empty_sections(self):
        """Handle missing sections in scenario data."""
        scenario_data = {
            "characters": {
                "test@example.com": {"name": "Test"},
            },
            # Missing sms_characters and vendors
        }
        registry = CharacterRegistry.from_scenario_characters(scenario_data)
        assert len(registry) == 1

    def test_from_scenario_characters_all_empty(self):
        """Handle completely empty scenario data."""
        registry = CharacterRegistry.from_scenario_characters({})
        assert len(registry) == 0


# =============================================================================
# Integration Tests
# =============================================================================


class TestCharacterIntegration:
    """Integration tests for character system."""

    def test_end_to_end_workflow(self):
        """Test complete workflow from scenario data to system prompt."""
        # Simulate loading from scenario
        scenario_data = {
            "characters": {
                "jamie@example.com": {
                    "name": "Jamie Walsh",
                    "role": "Best Friend",
                    "relationship": "College roommate",
                    "personality": "Outgoing, enthusiastic, supportive",
                    "communication_style": "Casual with lots of exclamation marks!",
                    "response_behavior": {"rsvp": "immediate_yes"},
                    "responsiveness": {
                        "min_delay_minutes": 5,
                        "max_delay_minutes": 15,
                    },
                    "example_response": "OMG yes! I'll be there!",
                },
            },
        }

        # Create registry
        registry = CharacterRegistry.from_scenario_characters(scenario_data)

        # Look up character
        jamie = registry.get_by_email("jamie@example.com")
        assert jamie is not None

        # Verify profile
        assert jamie.name == "Jamie Walsh"
        assert jamie.rsvp_behavior == RSVPBehavior.IMMEDIATE_YES
        assert jamie.response_timing.base_delay_minutes == 5
        assert jamie.response_timing.variance_minutes == 10

        # Generate system prompt
        prompt = jamie.build_system_prompt()
        assert "Jamie Walsh" in prompt
        assert "Best Friend" in prompt
        assert "College roommate" in prompt
        assert "Outgoing, enthusiastic, supportive" in prompt
        assert "OMG yes! I'll be there!" in prompt

    def test_multiple_contact_methods(self):
        """Character with both email and phone can be found by either."""
        profile = CharacterProfile(
            name="Multi-Contact",
            email="multi@example.com",
            phone="+15559876543",
        )
        registry = CharacterRegistry([profile])

        by_email = registry.get_by_email("multi@example.com")
        by_phone = registry.get_by_phone("+15559876543")

        assert by_email is by_phone  # Same object
        assert by_email.name == "Multi-Contact"
