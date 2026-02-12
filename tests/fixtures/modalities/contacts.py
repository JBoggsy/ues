"""Fixtures for Contacts modality."""

from datetime import date, datetime, timezone

import pytest

from ues.models.modalities.contacts_input import (
    ContactIdentifier,
    ContactsInput,
    PostalAddress,
)
from ues.models.modalities.contacts_state import Contact, ContactsState


# ---------------------------------------------------------------------------
# Factory functions
# ---------------------------------------------------------------------------


def create_contact_identifier(
    identifier_type: str = "phone",
    value: str = "+15551234567",
    label: str | None = None,
) -> ContactIdentifier:
    """Create a ContactIdentifier with sensible defaults.

    Args:
        identifier_type: Type of identifier (default: "phone").
        value: The identifier value (default: "+15551234567").
        label: Optional user-defined label.

    Returns:
        ContactIdentifier instance ready for testing.
    """
    return ContactIdentifier(
        identifier_type=identifier_type,
        value=value,
        label=label,
    )


def create_postal_address(
    street: str | None = "123 Main St",
    city: str | None = "Springfield",
    state: str | None = "IL",
    postal_code: str | None = "62701",
    country: str | None = "US",
    label: str | None = "home",
) -> PostalAddress:
    """Create a PostalAddress with sensible defaults.

    Args:
        street: Street address.
        city: City name.
        state: State or region.
        postal_code: ZIP code.
        country: Country code.
        label: User-defined label.

    Returns:
        PostalAddress instance ready for testing.
    """
    return PostalAddress(
        street=street,
        city=city,
        state=state,
        postal_code=postal_code,
        country=country,
        label=label,
    )


def create_contact(
    contact_id: str = "contact-001",
    first_name: str | None = "Alice",
    last_name: str | None = "Smith",
    identifiers: list[ContactIdentifier] | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
    **kwargs,
) -> Contact:
    """Create a Contact with sensible defaults.

    Args:
        contact_id: Unique contact identifier.
        first_name: First name.
        last_name: Last name.
        identifiers: List of identifiers (default: one phone number).
        created_at: When contact was created (default: UTC now).
        updated_at: When contact was last modified (default: UTC now).
        **kwargs: Additional fields to override.

    Returns:
        Contact instance ready for testing.
    """
    now = datetime.now(timezone.utc)
    if identifiers is None:
        identifiers = [
            create_contact_identifier(
                identifier_type="phone", value="+15551234567"
            )
        ]
    return Contact(
        contact_id=contact_id,
        first_name=first_name,
        last_name=last_name,
        identifiers=identifiers,
        created_at=created_at or now,
        updated_at=updated_at or now,
        **kwargs,
    )


def create_contacts_input(
    operation: str = "create_contact",
    timestamp: datetime | None = None,
    **kwargs,
) -> ContactsInput:
    """Create a ContactsInput with sensible defaults.

    Args:
        operation: Contact operation type (default: "create_contact").
        timestamp: When operation occurred (defaults to now).
        **kwargs: Additional operation-specific fields.

    Returns:
        ContactsInput instance ready for testing.
    """
    return ContactsInput(
        operation=operation,
        timestamp=timestamp or datetime.now(timezone.utc),
        **kwargs,
    )


def create_contacts_state(
    last_updated: datetime | None = None,
    **kwargs,
) -> ContactsState:
    """Create a ContactsState with sensible defaults.

    Args:
        last_updated: When state was last updated (defaults to now).
        **kwargs: Additional fields to override.

    Returns:
        ContactsState instance ready for testing.
    """
    return ContactsState(
        last_updated=last_updated or datetime.now(timezone.utc),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Pre-built examples
# ---------------------------------------------------------------------------

# Timestamps for consistent fixture data
_T0 = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
_T1 = datetime(2025, 6, 1, 10, 5, 0, tzinfo=timezone.utc)
_T2 = datetime(2025, 6, 1, 10, 10, 0, tzinfo=timezone.utc)

SIMPLE_CREATE = create_contacts_input(
    operation="create_contact",
    timestamp=_T0,
    first_name="Alice",
    last_name="Smith",
    identifiers=[
        create_contact_identifier("phone", "+15551234567", "mobile"),
        create_contact_identifier("email", "alice@example.com", "work"),
    ],
)

SIMPLE_UPDATE = create_contacts_input(
    operation="update_contact",
    timestamp=_T1,
    contact_id="contact-001",
    first_name="Alicia",
)

SIMPLE_DELETE = create_contacts_input(
    operation="delete_contact",
    timestamp=_T1,
    contact_id="contact-001",
)

BLOCK_CONTACT = create_contacts_input(
    operation="block_contact",
    timestamp=_T1,
    contact_id="contact-001",
)

UNBLOCK_CONTACT = create_contacts_input(
    operation="unblock_contact",
    timestamp=_T1,
    contact_id="contact-001",
)

FAVORITE_CONTACT = create_contacts_input(
    operation="favorite_contact",
    timestamp=_T1,
    contact_id="contact-001",
)

UNFAVORITE_CONTACT = create_contacts_input(
    operation="unfavorite_contact",
    timestamp=_T1,
    contact_id="contact-001",
)

ADD_TO_GROUP = create_contacts_input(
    operation="add_to_group",
    timestamp=_T1,
    contact_id="contact-001",
    group_name="Family",
)

REMOVE_FROM_GROUP = create_contacts_input(
    operation="remove_from_group",
    timestamp=_T1,
    contact_id="contact-001",
    group_name="Family",
)

MERGE_CONTACTS = create_contacts_input(
    operation="merge_contacts",
    timestamp=_T1,
    primary_contact_id="contact-001",
    secondary_contact_id="contact-002",
)

# Pre-built Contact objects
SAMPLE_CONTACT_ALICE = create_contact(
    contact_id="contact-alice",
    first_name="Alice",
    last_name="Smith",
    identifiers=[
        create_contact_identifier("phone", "+15551234567", "mobile"),
        create_contact_identifier("email", "alice@example.com", "work"),
    ],
    company="Acme Corp",
    job_title="Engineer",
    groups={"Family", "Work"},
    is_favorite=True,
    created_at=_T0,
    updated_at=_T0,
)

SAMPLE_CONTACT_BOB = create_contact(
    contact_id="contact-bob",
    first_name="Bob",
    last_name="Jones",
    identifiers=[
        create_contact_identifier("phone", "+15559876543", "home"),
        create_contact_identifier("email", "bob@example.com", "personal"),
    ],
    company="GlobalTech",
    job_title="Manager",
    groups={"Work"},
    created_at=_T0,
    updated_at=_T0,
)

SAMPLE_CONTACT_CAROL = create_contact(
    contact_id="contact-carol",
    first_name="Carol",
    last_name="Davis",
    identifiers=[
        create_contact_identifier("email", "carol@example.com"),
    ],
    is_blocked=True,
    created_at=_T0,
    updated_at=_T0,
)


# Invalid input examples for testing validation errors
INVALID_CONTACTS_INPUTS = {
    "create_no_identifiers": {
        "modality_type": "contacts",
        "timestamp": _T0.isoformat(),
        "operation": "create_contact",
        "first_name": "NoId",
    },
    "update_no_contact_id": {
        "modality_type": "contacts",
        "timestamp": _T0.isoformat(),
        "operation": "update_contact",
        "first_name": "Updated",
    },
    "delete_no_contact_id": {
        "modality_type": "contacts",
        "timestamp": _T0.isoformat(),
        "operation": "delete_contact",
    },
    "merge_same_ids": {
        "modality_type": "contacts",
        "timestamp": _T0.isoformat(),
        "operation": "merge_contacts",
        "primary_contact_id": "c1",
        "secondary_contact_id": "c1",
    },
    "add_to_group_no_group": {
        "modality_type": "contacts",
        "timestamp": _T0.isoformat(),
        "operation": "add_to_group",
        "contact_id": "c1",
    },
}


# JSON examples for deserialization testing
CONTACTS_JSON_EXAMPLES = {
    "simple_create": {
        "modality_type": "contacts",
        "timestamp": "2025-06-01T10:00:00Z",
        "operation": "create_contact",
        "first_name": "Alice",
        "last_name": "Smith",
        "identifiers": [
            {"identifier_type": "phone", "value": "+15551234567"},
        ],
    },
    "update_with_additive": {
        "modality_type": "contacts",
        "timestamp": "2025-06-01T10:05:00Z",
        "operation": "update_contact",
        "contact_id": "contact-001",
        "add_identifiers": [
            {"identifier_type": "email", "value": "alice@work.com"},
        ],
        "add_groups": ["Colleagues"],
    },
    "merge": {
        "modality_type": "contacts",
        "timestamp": "2025-06-01T10:10:00Z",
        "operation": "merge_contacts",
        "primary_contact_id": "contact-001",
        "secondary_contact_id": "contact-002",
    },
}


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_contacts_input():
    """Provide a simple create-contact input for tests."""
    return create_contacts_input(
        operation="create_contact",
        first_name="Test",
        last_name="User",
        identifiers=[
            create_contact_identifier("phone", "+15550001111"),
        ],
    )


@pytest.fixture
def contacts_state():
    """Provide an empty ContactsState for tests."""
    return create_contacts_state()


@pytest.fixture
def contacts_state_with_alice():
    """Provide a ContactsState pre-populated with Alice."""
    state = create_contacts_state(last_updated=_T0)
    state.contacts["contact-alice"] = SAMPLE_CONTACT_ALICE.model_copy(
        deep=True
    )
    return state


@pytest.fixture
def contacts_state_with_data():
    """Provide a ContactsState pre-populated with Alice, Bob, and Carol."""
    state = create_contacts_state(last_updated=_T0)
    state.contacts["contact-alice"] = SAMPLE_CONTACT_ALICE.model_copy(
        deep=True
    )
    state.contacts["contact-bob"] = SAMPLE_CONTACT_BOB.model_copy(deep=True)
    state.contacts["contact-carol"] = SAMPLE_CONTACT_CAROL.model_copy(
        deep=True
    )
    return state
