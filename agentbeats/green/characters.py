"""Character profile models for response generator sub-agents.

This module defines the data models for simulated characters that the Green Agent
uses to generate realistic responses to Purple Agent actions. Characters represent
the people (guests, vendors, contacts) that the user interacts with in scenarios.

Character profiles control:
- Personality and communication style for LLM-based response generation
- Response timing (delays, work hours)
- RSVP and response behavior patterns
- Contact information for matching outgoing messages

Example:
    >>> from agentbeats.green.characters import CharacterRegistry
    >>> registry = CharacterRegistry.from_dict({
    ...     "jamie@example.com": {
    ...         "name": "Jamie Walsh",
    ...         "personality": "Casual and friendly",
    ...         "response_timing": {"base_delay_minutes": 60, "variance_minutes": 30}
    ...     }
    ... })
    >>> character = registry.get_by_email("jamie@example.com")
    >>> print(character.name)
    Jamie Walsh
"""

from datetime import timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field, field_validator


class RSVPBehavior(str, Enum):
    """Pre-defined RSVP response patterns for calendar invites."""

    IMMEDIATE_YES = "immediate_yes"
    QUICK_YES = "quick_yes"
    TENTATIVE_YES = "tentative_yes"
    MAYBE = "maybe"
    DECLINE = "decline"
    NO_RESPONSE = "no_response"


class ContactType(str, Enum):
    """Type of character contact for routing responses."""

    GUEST = "guest"  # Personal contacts (friends, family)
    VENDOR = "vendor"  # Business contacts (catering, services)
    COLLEAGUE = "colleague"  # Work contacts
    OTHER = "other"


class ResponseTiming(BaseModel):
    """Configuration for character response timing.

    Controls how long a character takes to respond and during what hours.
    Used by the response generator to schedule realistic reply delays.

    Attributes:
        base_delay_minutes: Minimum delay before responding (default: 30).
        variance_minutes: Random variance added to base delay (default: 30).
        work_hours_only: Only respond during work hours (default: False).
        work_hours_start: Start of work hours in 24h format (default: "09:00").
        work_hours_end: End of work hours in 24h format (default: "17:00").
        timezone: Timezone for work hours (default: "America/New_York").
    """

    base_delay_minutes: int = Field(
        default=30,
        ge=0,
        description="Minimum delay before responding (minutes)",
    )
    variance_minutes: int = Field(
        default=30,
        ge=0,
        description="Random variance added to base delay (minutes)",
    )
    work_hours_only: bool = Field(
        default=False,
        description="Only respond during work hours",
    )
    work_hours_start: str = Field(
        default="09:00",
        pattern=r"^\d{2}:\d{2}$",
        description="Start of work hours (HH:MM)",
    )
    work_hours_end: str = Field(
        default="17:00",
        pattern=r"^\d{2}:\d{2}$",
        description="End of work hours (HH:MM)",
    )
    timezone: str = Field(
        default="America/New_York",
        description="Timezone for work hours",
    )

    def get_base_delay(self) -> timedelta:
        """Get the base delay as a timedelta."""
        return timedelta(minutes=self.base_delay_minutes)

    def get_max_delay(self) -> timedelta:
        """Get the maximum possible delay as a timedelta."""
        return timedelta(minutes=self.base_delay_minutes + self.variance_minutes)

    @classmethod
    def from_legacy_format(cls, data: dict) -> "ResponseTiming":
        """Create ResponseTiming from legacy party_planner format.

        Converts the `responsiveness` dict format used in existing scenarios
        to the new ResponseTiming model.

        Args:
            data: Dict with min_delay_minutes, max_delay_minutes, work_hours_only.

        Returns:
            ResponseTiming instance.
        """
        min_delay = data.get("min_delay_minutes", 30)
        max_delay = data.get("max_delay_minutes", 60)
        variance = max_delay - min_delay if max_delay > min_delay else 0

        return cls(
            base_delay_minutes=min_delay,
            variance_minutes=variance,
            work_hours_only=data.get("work_hours_only", False),
            work_hours_start=data.get("work_hours", {}).get("start", "09:00"),
            work_hours_end=data.get("work_hours", {}).get("end", "17:00"),
            timezone=data.get("work_hours", {}).get("timezone", "America/New_York"),
        )


class CharacterProfile(BaseModel):
    """Profile defining a simulated character for response generation.

    Contains all information needed to generate in-character responses:
    - Identity (name, role, relationship)
    - Contact info (email, phone)
    - Personality and communication style (for LLM prompts)
    - Response timing configuration
    - RSVP behavior patterns

    Attributes:
        name: Display name of the character.
        email: Email address (used for matching outgoing emails).
        phone: Phone number (used for matching SMS).
        role: Role/title (e.g., "Best Friend", "Bakery").
        relationship: Relationship to the user (e.g., "College friend").
        contact_type: Type of contact (guest, vendor, colleague, other).
        personality: Description of personality traits for LLM prompts.
        communication_style: Description of how the character writes.
        response_timing: Configuration for response delays.
        rsvp_behavior: How they respond to calendar invites.
        special_instructions: Additional LLM guidance for this character.
        example_response: An example response demonstrating the character's style.
    """

    name: str = Field(..., min_length=1, description="Display name")
    email: EmailStr | None = Field(default=None, description="Email address")
    phone: str | None = Field(default=None, description="Phone number")
    role: str = Field(default="Contact", description="Role/title")
    relationship: str | None = Field(default=None, description="Relationship to user")
    contact_type: ContactType = Field(
        default=ContactType.OTHER,
        description="Type of contact",
    )
    personality: str = Field(
        default="Friendly and helpful",
        description="Personality description for LLM",
    )
    communication_style: str = Field(
        default="Standard professional tone",
        description="Writing style description for LLM",
    )
    response_timing: ResponseTiming = Field(
        default_factory=ResponseTiming,
        description="Response delay configuration",
    )
    rsvp_behavior: RSVPBehavior = Field(
        default=RSVPBehavior.QUICK_YES,
        description="How they respond to calendar invites",
    )
    special_instructions: str | None = Field(
        default=None,
        description="Additional LLM guidance",
    )
    example_response: str | None = Field(
        default=None,
        description="Example response in character's style",
    )

    # Additional metadata that may be present in character definitions
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional character-specific data",
    )

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str | None) -> str | None:
        """Normalize phone number format."""
        if v is None:
            return None
        # Remove common formatting, keep just digits and leading +
        normalized = "".join(c for c in v if c.isdigit() or c == "+")
        return normalized if normalized else None

    @classmethod
    def from_scenario_format(cls, identifier: str, data: dict) -> "CharacterProfile":
        """Create CharacterProfile from scenario JSON format.

        Handles both the new format and legacy party_planner format.

        Args:
            identifier: The email or phone used as the dict key.
            data: Character definition dict from scenario.

        Returns:
            CharacterProfile instance.
        """
        # Determine contact type
        contact_type_str = data.get("contact_type", "other")
        try:
            contact_type = ContactType(contact_type_str)
        except ValueError:
            contact_type = ContactType.OTHER

        # Determine RSVP behavior
        rsvp_str = data.get("response_behavior", {}).get("rsvp", "quick_yes")
        try:
            rsvp_behavior = RSVPBehavior(rsvp_str)
        except ValueError:
            rsvp_behavior = RSVPBehavior.QUICK_YES

        # Parse response timing (handle legacy format)
        if "response_timing" in data:
            response_timing = ResponseTiming(**data["response_timing"])
        elif "responsiveness" in data:
            response_timing = ResponseTiming.from_legacy_format(data["responsiveness"])
        else:
            response_timing = ResponseTiming()

        # Determine email/phone from identifier or explicit fields
        email = data.get("email")
        phone = data.get("phone")

        # If identifier looks like email, use it
        if email is None and "@" in identifier:
            email = identifier
        # If identifier looks like phone, use it
        if phone is None and identifier.startswith("+"):
            phone = identifier

        # Build extra dict with fields we don't model explicitly
        known_fields = {
            "name",
            "email",
            "phone",
            "role",
            "relationship",
            "contact_type",
            "personality",
            "communication_style",
            "response_timing",
            "responsiveness",
            "rsvp_behavior",
            "response_behavior",
            "special_instructions",
            "example_response",
            "nickname",
            "preferred_contact",
            "work_hours",
        }
        extra = {k: v for k, v in data.items() if k not in known_fields}

        return cls(
            name=data.get("name", identifier),
            email=email,
            phone=phone,
            role=data.get("role", "Contact"),
            relationship=data.get("relationship"),
            contact_type=contact_type,
            personality=data.get("personality", "Friendly and helpful"),
            communication_style=data.get(
                "communication_style", "Standard professional tone"
            ),
            response_timing=response_timing,
            rsvp_behavior=rsvp_behavior,
            special_instructions=data.get("special_instructions"),
            example_response=data.get("example_response"),
            extra=extra,
        )

    def build_system_prompt(self) -> str:
        """Build an LLM system prompt from this character profile.

        Returns:
            System prompt string describing the character for response generation.
        """
        lines = [
            f"You are {self.name}, responding to a message.",
            f"Role: {self.role}",
        ]
        if self.relationship:
            lines.append(f"Relationship: {self.relationship}")
        lines.extend(
            [
                f"Personality: {self.personality}",
                f"Communication style: {self.communication_style}",
            ]
        )
        if self.special_instructions:
            lines.append(f"Special instructions: {self.special_instructions}")
        if self.example_response:
            lines.append(f"\nExample of how you write:\n{self.example_response}")

        return "\n".join(lines)


class CharacterRegistry:
    """Registry for looking up character profiles by contact info.

    Maintains indexes for fast lookup by email address or phone number.
    Used by the response generator to find character profiles when
    Purple Agent sends messages to known contacts.

    Example:
        >>> registry = CharacterRegistry.from_dict(characters_data)
        >>> character = registry.get_by_email("jamie@example.com")
        >>> if character:
        ...     print(f"Found: {character.name}")
    """

    def __init__(self, characters: list[CharacterProfile] | None = None):
        """Initialize the registry.

        Args:
            characters: Optional list of character profiles to register.
        """
        self._characters: list[CharacterProfile] = []
        self._by_email: dict[str, CharacterProfile] = {}
        self._by_phone: dict[str, CharacterProfile] = {}

        if characters:
            for character in characters:
                self.register(character)

    def register(self, character: CharacterProfile) -> None:
        """Add a character to the registry.

        Args:
            character: The character profile to register.
        """
        self._characters.append(character)

        if character.email:
            self._by_email[character.email.lower()] = character

        if character.phone:
            # Normalize phone for lookup
            normalized = "".join(c for c in character.phone if c.isdigit() or c == "+")
            if normalized:
                self._by_phone[normalized] = character

    def get_by_email(self, email: str) -> CharacterProfile | None:
        """Look up a character by email address.

        Args:
            email: Email address to look up (case-insensitive).

        Returns:
            CharacterProfile if found, None otherwise.
        """
        return self._by_email.get(email.lower())

    def get_by_phone(self, phone: str) -> CharacterProfile | None:
        """Look up a character by phone number.

        Args:
            phone: Phone number to look up (formatting ignored).

        Returns:
            CharacterProfile if found, None otherwise.
        """
        normalized = "".join(c for c in phone if c.isdigit() or c == "+")
        return self._by_phone.get(normalized)

    def get_by_identifier(self, identifier: str) -> CharacterProfile | None:
        """Look up a character by email or phone.

        Args:
            identifier: Email address or phone number.

        Returns:
            CharacterProfile if found, None otherwise.
        """
        if "@" in identifier:
            return self.get_by_email(identifier)
        else:
            return self.get_by_phone(identifier)

    def list_all(self) -> list[CharacterProfile]:
        """Get all registered characters.

        Returns:
            List of all character profiles.
        """
        return list(self._characters)

    def list_emails(self) -> list[str]:
        """Get all registered email addresses.

        Returns:
            List of email addresses.
        """
        return list(self._by_email.keys())

    def list_phones(self) -> list[str]:
        """Get all registered phone numbers.

        Returns:
            List of phone numbers.
        """
        return list(self._by_phone.keys())

    def __len__(self) -> int:
        """Return the number of registered characters."""
        return len(self._characters)

    def __contains__(self, identifier: str) -> bool:
        """Check if an identifier is registered."""
        return self.get_by_identifier(identifier) is not None

    @classmethod
    def from_dict(cls, data: dict[str, dict]) -> "CharacterRegistry":
        """Create a registry from a dict of character definitions.

        Args:
            data: Dict mapping identifier (email/phone) to character data.

        Returns:
            CharacterRegistry with all characters registered.
        """
        registry = cls()
        for identifier, char_data in data.items():
            character = CharacterProfile.from_scenario_format(identifier, char_data)
            registry.register(character)
        return registry

    @classmethod
    def from_scenario_characters(cls, scenario_data: dict) -> "CharacterRegistry":
        """Create a registry from full scenario character data.

        Handles the scenario format with separate `characters`, `sms_characters`,
        and `vendors` sections.

        Args:
            scenario_data: Dict with characters, sms_characters, vendors keys.

        Returns:
            CharacterRegistry with all characters registered.
        """
        registry = cls()

        # Load email characters
        for identifier, char_data in scenario_data.get("characters", {}).items():
            character = CharacterProfile.from_scenario_format(identifier, char_data)
            registry.register(character)

        # Load SMS characters
        for identifier, char_data in scenario_data.get("sms_characters", {}).items():
            character = CharacterProfile.from_scenario_format(identifier, char_data)
            registry.register(character)

        # Load vendors
        for identifier, char_data in scenario_data.get("vendors", {}).items():
            character = CharacterProfile.from_scenario_format(identifier, char_data)
            registry.register(character)

        return registry
