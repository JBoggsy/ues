"""Unit tests for ContactsState modality.

Tests are organized into sections:
1. General ModalityState pattern tests (replicate for all modalities)
2. Contact sub-model tests
3. Operation-specific tests (create, update, delete, block, favorite, group, merge)
4. Cross-modality lookup tests
5. Query tests
6. Snapshot tests
7. Validate state tests
8. Undo tests
9. Clear tests
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from ues.models.modalities.contacts_input import (
    ContactIdentifier,
    ContactsInput,
    PostalAddress,
)
from ues.models.modalities.contacts_state import Contact, ContactsState
from tests.fixtures.modalities.contacts import (
    SAMPLE_CONTACT_ALICE,
    SAMPLE_CONTACT_BOB,
    SAMPLE_CONTACT_CAROL,
    create_contact,
    create_contact_identifier,
    create_contacts_input,
    create_contacts_state,
    create_postal_address,
)


# ============================================================================
# Timestamps used throughout tests
# ============================================================================

_T0 = datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
_T1 = datetime(2025, 6, 1, 10, 5, 0, tzinfo=timezone.utc)
_T2 = datetime(2025, 6, 1, 10, 10, 0, tzinfo=timezone.utc)
_T3 = datetime(2025, 6, 1, 10, 15, 0, tzinfo=timezone.utc)


# ============================================================================
# 1. General ModalityState Pattern Tests
# ============================================================================


class TestContactsStateInstantiation:
    """GENERAL PATTERN: Tests for ModalityState base class contract."""

    def test_instantiation_defaults(self):
        """Empty state should have no contacts and update_count 0."""
        state = create_contacts_state(last_updated=_T0)

        assert state.contacts == {}
        assert state.update_count == 0
        assert state.last_updated == _T0

    def test_instantiation_modality_type(self):
        """modality_type should always be 'contacts'."""
        state = create_contacts_state()

        assert state.modality_type == "contacts"

    def test_modality_type_is_frozen(self):
        """modality_type should not be changeable after creation."""
        state = create_contacts_state()

        with pytest.raises(Exception):
            state.modality_type = "something_else"

    def test_get_snapshot_empty(self):
        """Snapshot of empty state should have correct structure."""
        state = create_contacts_state(last_updated=_T0)
        snapshot = state.get_snapshot()

        assert snapshot["modality_type"] == "contacts"
        assert snapshot["total_contacts"] == 0
        assert snapshot["favorites_count"] == 0
        assert snapshot["blocked_count"] == 0
        assert snapshot["groups"] == []
        assert snapshot["contacts"] == {}
        assert snapshot["update_count"] == 0

    def test_validate_state_empty(self):
        """Empty state should pass validation with no issues."""
        state = create_contacts_state()
        issues = state.validate_state()

        assert issues == []

    def test_apply_input_increments_update_count(self):
        """Each apply_input should increment update_count by 1."""
        state = create_contacts_state(last_updated=_T0)

        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15550001111")],
        )
        state.apply_input(inp)

        assert state.update_count == 1

        inp2 = create_contacts_input(
            operation="create_contact",
            timestamp=_T2,
            identifiers=[create_contact_identifier("phone", "+15550002222")],
        )
        state.apply_input(inp2)

        assert state.update_count == 2

    def test_apply_input_updates_last_updated(self):
        """last_updated should advance to the input's timestamp."""
        state = create_contacts_state(last_updated=_T0)

        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15550001111")],
        )
        state.apply_input(inp)

        assert state.last_updated == _T1

    def test_apply_input_rejects_non_contacts_input(self):
        """apply_input should raise ValueError for non-ContactsInput."""
        state = create_contacts_state()

        # Use a different modality's input (not ContactsInput)
        from ues.models.modalities.sms_input import SMSInput

        sms_input = SMSInput(
            timestamp=_T0,
            operation="send_message",
            message_data={
                "from_number": "+15551234567",
                "to_numbers": ["+15559876543"],
                "body": "test",
            },
        )

        with pytest.raises(ValueError, match="Expected ContactsInput"):
            state.apply_input(sms_input)


# ============================================================================
# 2. Contact Sub-model Tests
# ============================================================================


class TestContact:
    """Tests for the Contact sub-model."""

    def test_contact_creation_with_all_fields(self):
        """Contact should accept all defined fields."""
        contact = create_contact(
            contact_id="c1",
            first_name="Alice",
            last_name="Smith",
            identifiers=[
                create_contact_identifier("phone", "+15551234567", "mobile"),
                create_contact_identifier("email", "alice@example.com", "work"),
            ],
            display_name="Ali",
            nickname="Al",
            company="Acme",
            job_title="Engineer",
            addresses=[create_postal_address()],
            birthday=date(1990, 5, 15),
            notes="Best friend",
            photo_url="https://example.com/photo.jpg",
            is_favorite=True,
            is_blocked=False,
            groups={"Family", "Work"},
        )

        assert contact.contact_id == "c1"
        assert contact.first_name == "Alice"
        assert contact.last_name == "Smith"
        assert contact.display_name == "Ali"
        assert contact.nickname == "Al"
        assert len(contact.identifiers) == 2
        assert contact.company == "Acme"
        assert contact.job_title == "Engineer"
        assert len(contact.addresses) == 1
        assert contact.birthday == date(1990, 5, 15)
        assert contact.notes == "Best friend"
        assert contact.photo_url == "https://example.com/photo.jpg"
        assert contact.is_favorite is True
        assert contact.is_blocked is False
        assert contact.groups == {"Family", "Work"}

    def test_contact_auto_uuid(self):
        """Contact should auto-generate a UUID if contact_id is not provided."""
        contact = Contact(
            identifiers=[create_contact_identifier()],
            created_at=_T0,
            updated_at=_T0,
        )

        assert contact.contact_id is not None
        assert len(contact.contact_id) > 0

    def test_contact_defaults(self):
        """Contact should have sensible defaults for optional fields."""
        contact = Contact(
            contact_id="c1",
            identifiers=[],
            created_at=_T0,
            updated_at=_T0,
        )

        assert contact.first_name is None
        assert contact.last_name is None
        assert contact.display_name is None
        assert contact.nickname is None
        assert contact.company is None
        assert contact.job_title is None
        assert contact.addresses == []
        assert contact.birthday is None
        assert contact.notes is None
        assert contact.photo_url is None
        assert contact.is_favorite is False
        assert contact.is_blocked is False
        assert contact.groups == set()

    def test_resolved_display_name_explicit(self):
        """Should return display_name when explicitly set."""
        contact = create_contact(
            display_name="Mom",
            first_name="Jane",
            last_name="Doe",
        )

        assert contact.get_resolved_display_name() == "Mom"

    def test_resolved_display_name_from_names(self):
        """Should return 'First Last' when display_name is None."""
        contact = create_contact(
            display_name=None,
            first_name="Jane",
            last_name="Doe",
        )

        assert contact.get_resolved_display_name() == "Jane Doe"

    def test_resolved_display_name_first_only(self):
        """Should return just first name when last name is None."""
        contact = create_contact(
            display_name=None,
            first_name="Jane",
            last_name=None,
        )

        assert contact.get_resolved_display_name() == "Jane"

    def test_resolved_display_name_last_only(self):
        """Should return just last name when first name is None."""
        contact = create_contact(
            display_name=None,
            first_name=None,
            last_name="Doe",
        )

        assert contact.get_resolved_display_name() == "Doe"

    def test_resolved_display_name_nickname_fallback(self):
        """Should fall back to nickname when no names are set."""
        contact = create_contact(
            display_name=None,
            first_name=None,
            last_name=None,
            nickname="JD",
        )

        assert contact.get_resolved_display_name() == "JD"

    def test_resolved_display_name_identifier_fallback(self):
        """Should fall back to first identifier value when no names/nickname."""
        contact = Contact(
            contact_id="c1",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            created_at=_T0,
            updated_at=_T0,
        )

        assert contact.get_resolved_display_name() == "+15551234567"

    def test_resolved_display_name_unknown(self):
        """Should return 'Unknown' for empty contact."""
        contact = Contact(
            contact_id="c1",
            identifiers=[],
            created_at=_T0,
            updated_at=_T0,
        )

        assert contact.get_resolved_display_name() == "Unknown"

    def test_get_phone_numbers(self):
        """Should return only phone-type identifier values."""
        contact = create_contact(
            identifiers=[
                create_contact_identifier("phone", "+15551111111"),
                create_contact_identifier("email", "a@b.com"),
                create_contact_identifier("phone", "+15552222222"),
            ],
        )

        phones = contact.get_phone_numbers()

        assert phones == ["+15551111111", "+15552222222"]

    def test_get_phone_numbers_none(self):
        """Should return empty list when contact has no phone identifiers."""
        contact = create_contact(
            identifiers=[create_contact_identifier("email", "a@b.com")],
        )

        assert contact.get_phone_numbers() == []

    def test_get_email_addresses(self):
        """Should return only email-type identifier values."""
        contact = create_contact(
            identifiers=[
                create_contact_identifier("email", "a@b.com"),
                create_contact_identifier("phone", "+15551111111"),
                create_contact_identifier("email", "c@d.com"),
            ],
        )

        emails = contact.get_email_addresses()

        assert emails == ["a@b.com", "c@d.com"]

    def test_has_identifier_true(self):
        """Should return True when contact has the specified identifier."""
        contact = create_contact(
            identifiers=[
                create_contact_identifier("phone", "+15551111111"),
            ],
        )

        assert contact.has_identifier("phone", "+15551111111") is True

    def test_has_identifier_false(self):
        """Should return False when contact lacks the identifier."""
        contact = create_contact(
            identifiers=[
                create_contact_identifier("phone", "+15551111111"),
            ],
        )

        assert contact.has_identifier("phone", "+15559999999") is False
        assert contact.has_identifier("email", "+15551111111") is False

    def test_add_identifier(self):
        """Should add a new identifier to the contact."""
        contact = create_contact(
            identifiers=[create_contact_identifier("phone", "+15551111111")],
        )

        new_ident = create_contact_identifier("email", "a@b.com")
        contact.add_identifier(new_ident)

        assert len(contact.identifiers) == 2
        assert contact.has_identifier("email", "a@b.com") is True

    def test_add_identifier_duplicate_rejected(self):
        """Should reject adding a duplicate identifier."""
        contact = create_contact(
            identifiers=[create_contact_identifier("phone", "+15551111111")],
        )

        duplicate = create_contact_identifier("phone", "+15551111111")

        with pytest.raises(ValueError, match="already has identifier"):
            contact.add_identifier(duplicate)

    def test_remove_identifier(self):
        """Should remove identifier and return True."""
        contact = create_contact(
            identifiers=[
                create_contact_identifier("phone", "+15551111111"),
                create_contact_identifier("email", "a@b.com"),
            ],
        )

        result = contact.remove_identifier("phone", "+15551111111")

        assert result is True
        assert len(contact.identifiers) == 1
        assert contact.has_identifier("phone", "+15551111111") is False

    def test_remove_identifier_not_found(self):
        """Should return False when identifier not found."""
        contact = create_contact(
            identifiers=[create_contact_identifier("phone", "+15551111111")],
        )

        result = contact.remove_identifier("email", "missing@test.com")

        assert result is False
        assert len(contact.identifiers) == 1

    def test_to_dict(self):
        """Should serialize to a dictionary with all expected keys."""
        contact = create_contact(
            contact_id="c1",
            first_name="Alice",
            last_name="Smith",
            identifiers=[
                create_contact_identifier("phone", "+15551234567"),
            ],
            groups={"Family"},
            created_at=_T0,
            updated_at=_T0,
        )

        d = contact.to_dict()

        assert d["contact_id"] == "c1"
        assert d["first_name"] == "Alice"
        assert d["last_name"] == "Smith"
        assert d["resolved_display_name"] == "Alice Smith"
        assert len(d["identifiers"]) == 1
        assert d["groups"] == ["Family"]
        assert "created_at" in d
        assert "updated_at" in d

    def test_timezone_aware_datetimes(self):
        """Contact timestamps should be timezone-aware."""
        contact = create_contact(created_at=_T0, updated_at=_T0)

        assert contact.created_at.tzinfo is not None
        assert contact.updated_at.tzinfo is not None

    def test_naive_datetime_converted_to_utc(self):
        """Naive datetimes should be converted to UTC."""
        naive = datetime(2025, 1, 1, 12, 0, 0)
        contact = Contact(
            contact_id="c1",
            identifiers=[],
            created_at=naive,
            updated_at=naive,
        )

        assert contact.created_at.tzinfo is not None
        assert contact.updated_at.tzinfo is not None


# ============================================================================
# 3. Create Contact Tests
# ============================================================================


class TestCreateContact:
    """Tests for the create_contact operation."""

    def test_create_contact_basic(self):
        """Create with one identifier should add the contact to state."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            last_name="Smith",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )

        state.apply_input(inp)

        assert len(state.contacts) == 1
        contact = list(state.contacts.values())[0]
        assert contact.first_name == "Alice"
        assert contact.last_name == "Smith"
        assert contact.has_identifier("phone", "+15551234567")

    def test_create_contact_full_data(self):
        """Create with all fields populated should store everything."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            last_name="Smith",
            display_name="Ali",
            nickname="Al",
            identifiers=[
                create_contact_identifier("phone", "+15551234567", "mobile"),
            ],
            company="Acme Corp",
            job_title="Engineer",
            addresses=[create_postal_address()],
            birthday=date(1990, 5, 15),
            notes="College friend",
            photo_url="https://example.com/photo.jpg",
            is_favorite=True,
            is_blocked=False,
            groups={"Family", "Work"},
        )

        state.apply_input(inp)

        contact = list(state.contacts.values())[0]
        assert contact.display_name == "Ali"
        assert contact.nickname == "Al"
        assert contact.company == "Acme Corp"
        assert contact.job_title == "Engineer"
        assert len(contact.addresses) == 1
        assert contact.birthday == date(1990, 5, 15)
        assert contact.notes == "College friend"
        assert contact.photo_url == "https://example.com/photo.jpg"
        assert contact.is_favorite is True
        assert contact.is_blocked is False
        assert contact.groups == {"Family", "Work"}

    def test_create_contact_multiple_identifiers(self):
        """Create with phone + email + custom type."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[
                create_contact_identifier("phone", "+15551234567"),
                create_contact_identifier("email", "alice@example.com"),
                create_contact_identifier("discord", "alice#1234"),
            ],
        )

        state.apply_input(inp)

        contact = list(state.contacts.values())[0]
        assert len(contact.identifiers) == 3
        assert contact.has_identifier("phone", "+15551234567")
        assert contact.has_identifier("email", "alice@example.com")
        assert contact.has_identifier("discord", "alice#1234")

    def test_create_contact_with_addresses(self):
        """Create with postal addresses."""
        state = create_contacts_state(last_updated=_T0)
        home_addr = create_postal_address(
            street="123 Main St", city="Springfield", label="home"
        )
        work_addr = create_postal_address(
            street="456 Office Blvd", city="Shelbyville", label="work"
        )
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            addresses=[home_addr, work_addr],
        )

        state.apply_input(inp)

        contact = list(state.contacts.values())[0]
        assert len(contact.addresses) == 2

    def test_create_contact_with_groups(self):
        """Create with group memberships."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            groups={"Family", "Book Club"},
        )

        state.apply_input(inp)

        contact = list(state.contacts.values())[0]
        assert contact.groups == {"Family", "Book Club"}

    def test_create_contact_with_birthday(self):
        """Create with date-only birthday."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            birthday=date(1990, 3, 14),
        )

        state.apply_input(inp)

        contact = list(state.contacts.values())[0]
        assert contact.birthday == date(1990, 3, 14)

    def test_create_contact_duplicate_identifier_rejected(self):
        """Reject creation if identifier already exists on another contact."""
        state = create_contacts_state(last_updated=_T0)

        # Create first contact
        inp1 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp1)

        # Try creating second contact with same phone number
        inp2 = create_contacts_input(
            operation="create_contact",
            timestamp=_T2,
            first_name="Bob",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )

        with pytest.raises(ValueError, match="already belongs to contact"):
            state.apply_input(inp2)

    def test_create_contact_assigns_uuid(self):
        """Created contact should get a UUID contact_id."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )

        state.apply_input(inp)

        contact = list(state.contacts.values())[0]
        assert len(contact.contact_id) > 0

    def test_create_contact_sets_timestamps(self):
        """created_at and updated_at should equal the input timestamp."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )

        state.apply_input(inp)

        contact = list(state.contacts.values())[0]
        assert contact.created_at == _T1
        assert contact.updated_at == _T1


# ============================================================================
# 4. Update Contact Tests
# ============================================================================


class TestUpdateContact:
    """Tests for the update_contact operation."""

    def _create_state_with_contact(self) -> tuple[ContactsState, str]:
        """Helper to create a state with one contact and return (state, contact_id)."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            last_name="Smith",
            identifiers=[
                create_contact_identifier("phone", "+15551234567", "mobile"),
            ],
            groups={"Work"},
        )
        state.apply_input(inp)
        contact_id = list(state.contacts.keys())[0]
        return state, contact_id

    def test_update_contact_name_fields(self):
        """Update first_name, last_name, display_name."""
        state, cid = self._create_state_with_contact()
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            first_name="Alicia",
            last_name="Johnson",
            display_name="AJ",
        )

        state.apply_input(inp)

        contact = state.contacts[cid]
        assert contact.first_name == "Alicia"
        assert contact.last_name == "Johnson"
        assert contact.display_name == "AJ"

    def test_update_contact_add_identifiers(self):
        """Additive identifier update — adds without removing existing."""
        state, cid = self._create_state_with_contact()
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            add_identifiers=[
                create_contact_identifier("email", "alice@work.com"),
            ],
        )

        state.apply_input(inp)

        contact = state.contacts[cid]
        assert contact.has_identifier("phone", "+15551234567")  # still there
        assert contact.has_identifier("email", "alice@work.com")  # new one

    def test_update_contact_remove_identifiers(self):
        """Subtractive identifier update — removes specified identifiers."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[
                create_contact_identifier("phone", "+15551234567"),
                create_contact_identifier("email", "alice@example.com"),
            ],
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_update = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            remove_identifiers=[
                create_contact_identifier("phone", "+15551234567"),
            ],
        )

        state.apply_input(inp_update)

        contact = state.contacts[cid]
        assert contact.has_identifier("phone", "+15551234567") is False
        assert contact.has_identifier("email", "alice@example.com") is True

    def test_update_contact_replace_identifiers(self):
        """Full-replace identifiers — replaces all identifiers."""
        state, cid = self._create_state_with_contact()
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            identifiers=[
                create_contact_identifier("email", "new@example.com"),
            ],
        )

        state.apply_input(inp)

        contact = state.contacts[cid]
        assert contact.has_identifier("phone", "+15551234567") is False
        assert contact.has_identifier("email", "new@example.com") is True
        assert len(contact.identifiers) == 1

    def test_update_contact_add_addresses(self):
        """Additive address update."""
        state, cid = self._create_state_with_contact()
        new_addr = create_postal_address(
            street="789 New Ave", city="Newtown", label="work"
        )
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            add_addresses=[new_addr],
        )

        state.apply_input(inp)

        assert len(state.contacts[cid].addresses) == 1

    def test_update_contact_remove_addresses(self):
        """Subtractive address update."""
        state = create_contacts_state(last_updated=_T0)
        addr = create_postal_address(street="123 Main", city="Town")
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15550001111")],
            addresses=[addr],
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_update = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            remove_addresses=[addr],
        )

        state.apply_input(inp_update)

        assert len(state.contacts[cid].addresses) == 0

    def test_update_contact_add_groups(self):
        """Additive group update."""
        state, cid = self._create_state_with_contact()
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            add_groups={"Family", "Friends"},
        )

        state.apply_input(inp)

        assert state.contacts[cid].groups == {"Work", "Family", "Friends"}

    def test_update_contact_remove_groups(self):
        """Subtractive group update."""
        state, cid = self._create_state_with_contact()
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            remove_groups={"Work"},
        )

        state.apply_input(inp)

        assert "Work" not in state.contacts[cid].groups

    def test_update_contact_scalar_fields(self):
        """Update company, job_title, notes, photo_url, birthday."""
        state, cid = self._create_state_with_contact()
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            company="NewCo",
            job_title="CTO",
            notes="Updated notes",
            photo_url="https://new.com/photo.jpg",
            birthday=date(1985, 12, 25),
        )

        state.apply_input(inp)

        contact = state.contacts[cid]
        assert contact.company == "NewCo"
        assert contact.job_title == "CTO"
        assert contact.notes == "Updated notes"
        assert contact.photo_url == "https://new.com/photo.jpg"
        assert contact.birthday == date(1985, 12, 25)

    def test_update_contact_not_found(self):
        """Raise error for nonexistent contact_id."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T1,
            contact_id="nonexistent",
            first_name="Ghost",
        )

        with pytest.raises(ValueError, match="Contact not found"):
            state.apply_input(inp)

    def test_update_contact_updates_timestamp(self):
        """updated_at should advance to the input timestamp."""
        state, cid = self._create_state_with_contact()
        inp = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            first_name="Alicia",
        )

        state.apply_input(inp)

        assert state.contacts[cid].updated_at == _T2

    def test_update_contact_duplicate_identifier_rejected(self):
        """Reject adding identifier that exists on another contact."""
        state = create_contacts_state(last_updated=_T0)

        # Create two contacts
        inp1 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551111111")],
        )
        state.apply_input(inp1)
        cid1 = list(state.contacts.keys())[0]

        inp2 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15552222222")],
        )
        state.apply_input(inp2)
        cid2 = [k for k in state.contacts.keys() if k != cid1][0]

        # Try adding cid1's phone to cid2
        inp_update = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid2,
            add_identifiers=[
                create_contact_identifier("phone", "+15551111111"),
            ],
        )

        with pytest.raises(ValueError, match="already belongs to contact"):
            state.apply_input(inp_update)


# ============================================================================
# 5. Delete Contact Tests
# ============================================================================


class TestDeleteContact:
    """Tests for the delete_contact operation."""

    def test_delete_contact(self):
        """Delete should remove the contact from state."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_delete = create_contacts_input(
            operation="delete_contact",
            timestamp=_T2,
            contact_id=cid,
        )

        state.apply_input(inp_delete)

        assert len(state.contacts) == 0

    def test_delete_contact_not_found(self):
        """Raise error for nonexistent contact_id."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="delete_contact",
            timestamp=_T1,
            contact_id="nonexistent",
        )

        with pytest.raises(ValueError, match="Contact not found"):
            state.apply_input(inp)

    def test_delete_contact_removes_from_groups(self):
        """Deleting a contact should remove it from all groups.

        If a group has no remaining members after deletion, the group
        should no longer appear in get_all_groups().
        """
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            groups={"UniqueGroup"},
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        # Verify group exists
        assert "UniqueGroup" in state.get_all_groups()

        # Delete the sole member
        inp_delete = create_contacts_input(
            operation="delete_contact",
            timestamp=_T2,
            contact_id=cid,
        )
        state.apply_input(inp_delete)

        # Group should vanish (no remaining members)
        assert "UniqueGroup" not in state.get_all_groups()


# ============================================================================
# 6. Block/Unblock Tests
# ============================================================================


class TestBlockUnblock:
    """Tests for block_contact and unblock_contact operations."""

    def _create_state_with_contact(self) -> tuple[ContactsState, str]:
        """Helper to create a state with one unblocked contact."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp)
        cid = list(state.contacts.keys())[0]
        return state, cid

    def test_block_contact(self):
        """Block should set is_blocked = True."""
        state, cid = self._create_state_with_contact()
        inp = create_contacts_input(
            operation="block_contact",
            timestamp=_T2,
            contact_id=cid,
        )

        state.apply_input(inp)

        assert state.contacts[cid].is_blocked is True

    def test_unblock_contact(self):
        """Unblock should set is_blocked = False."""
        state, cid = self._create_state_with_contact()

        # Block first
        state.apply_input(create_contacts_input(
            operation="block_contact", timestamp=_T2, contact_id=cid,
        ))

        # Then unblock
        state.apply_input(create_contacts_input(
            operation="unblock_contact", timestamp=_T3, contact_id=cid,
        ))

        assert state.contacts[cid].is_blocked is False

    def test_block_already_blocked(self):
        """Blocking an already-blocked contact should be idempotent."""
        state, cid = self._create_state_with_contact()

        state.apply_input(create_contacts_input(
            operation="block_contact", timestamp=_T2, contact_id=cid,
        ))
        # Block again — should not raise
        state.apply_input(create_contacts_input(
            operation="block_contact", timestamp=_T3, contact_id=cid,
        ))

        assert state.contacts[cid].is_blocked is True

    def test_unblock_already_unblocked(self):
        """Unblocking an already-unblocked contact should be idempotent."""
        state, cid = self._create_state_with_contact()

        # Unblock without ever blocking — should not raise
        state.apply_input(create_contacts_input(
            operation="unblock_contact", timestamp=_T2, contact_id=cid,
        ))

        assert state.contacts[cid].is_blocked is False

    def test_block_not_found(self):
        """Block on nonexistent contact should raise error."""
        state = create_contacts_state(last_updated=_T0)

        with pytest.raises(ValueError, match="Contact not found"):
            state.apply_input(create_contacts_input(
                operation="block_contact",
                timestamp=_T1,
                contact_id="nonexistent",
            ))

    def test_block_updates_timestamp(self):
        """Block should update the contact's updated_at."""
        state, cid = self._create_state_with_contact()
        state.apply_input(create_contacts_input(
            operation="block_contact", timestamp=_T2, contact_id=cid,
        ))

        assert state.contacts[cid].updated_at == _T2


# ============================================================================
# 7. Favorite/Unfavorite Tests
# ============================================================================


class TestFavoriteUnfavorite:
    """Tests for favorite_contact and unfavorite_contact operations."""

    def _create_state_with_contact(self) -> tuple[ContactsState, str]:
        """Helper to create a state with one non-favorite contact."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp)
        cid = list(state.contacts.keys())[0]
        return state, cid

    def test_favorite_contact(self):
        """Favorite should set is_favorite = True."""
        state, cid = self._create_state_with_contact()
        state.apply_input(create_contacts_input(
            operation="favorite_contact", timestamp=_T2, contact_id=cid,
        ))

        assert state.contacts[cid].is_favorite is True

    def test_unfavorite_contact(self):
        """Unfavorite should set is_favorite = False."""
        state, cid = self._create_state_with_contact()

        state.apply_input(create_contacts_input(
            operation="favorite_contact", timestamp=_T2, contact_id=cid,
        ))
        state.apply_input(create_contacts_input(
            operation="unfavorite_contact", timestamp=_T3, contact_id=cid,
        ))

        assert state.contacts[cid].is_favorite is False

    def test_favorite_already_favorited(self):
        """Favoriting an already-favorited contact should be idempotent."""
        state, cid = self._create_state_with_contact()

        state.apply_input(create_contacts_input(
            operation="favorite_contact", timestamp=_T2, contact_id=cid,
        ))
        state.apply_input(create_contacts_input(
            operation="favorite_contact", timestamp=_T3, contact_id=cid,
        ))

        assert state.contacts[cid].is_favorite is True

    def test_unfavorite_already_unfavorited(self):
        """Unfavoriting a non-favorite should be idempotent."""
        state, cid = self._create_state_with_contact()

        state.apply_input(create_contacts_input(
            operation="unfavorite_contact", timestamp=_T2, contact_id=cid,
        ))

        assert state.contacts[cid].is_favorite is False

    def test_favorite_updates_timestamp(self):
        """Favorite should update the contact's updated_at."""
        state, cid = self._create_state_with_contact()
        state.apply_input(create_contacts_input(
            operation="favorite_contact", timestamp=_T2, contact_id=cid,
        ))

        assert state.contacts[cid].updated_at == _T2


# ============================================================================
# 8. Group Operation Tests
# ============================================================================


class TestGroupOperations:
    """Tests for add_to_group and remove_from_group operations."""

    def _create_state_with_contact(self) -> tuple[ContactsState, str]:
        """Helper to create a state with one contact (no groups)."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp)
        cid = list(state.contacts.keys())[0]
        return state, cid

    def test_add_to_group(self):
        """Add to group should add group to contact's groups set."""
        state, cid = self._create_state_with_contact()
        state.apply_input(create_contacts_input(
            operation="add_to_group",
            timestamp=_T2,
            contact_id=cid,
            group_name="Family",
        ))

        assert "Family" in state.contacts[cid].groups

    def test_add_to_group_already_member(self):
        """Adding to a group the contact is already in should be idempotent."""
        state, cid = self._create_state_with_contact()

        state.apply_input(create_contacts_input(
            operation="add_to_group",
            timestamp=_T2,
            contact_id=cid,
            group_name="Family",
        ))
        state.apply_input(create_contacts_input(
            operation="add_to_group",
            timestamp=_T3,
            contact_id=cid,
            group_name="Family",
        ))

        assert "Family" in state.contacts[cid].groups

    def test_remove_from_group(self):
        """Remove from group should remove group from contact's set."""
        state, cid = self._create_state_with_contact()

        state.apply_input(create_contacts_input(
            operation="add_to_group",
            timestamp=_T2,
            contact_id=cid,
            group_name="Family",
        ))
        state.apply_input(create_contacts_input(
            operation="remove_from_group",
            timestamp=_T3,
            contact_id=cid,
            group_name="Family",
        ))

        assert "Family" not in state.contacts[cid].groups

    def test_remove_from_group_not_member(self):
        """Removing from a group the contact isn't in should not raise."""
        state, cid = self._create_state_with_contact()

        # Should not raise
        state.apply_input(create_contacts_input(
            operation="remove_from_group",
            timestamp=_T2,
            contact_id=cid,
            group_name="Nonexistent",
        ))

    def test_remove_from_group_not_found(self):
        """Remove from group with nonexistent contact_id should raise."""
        state = create_contacts_state(last_updated=_T0)

        with pytest.raises(ValueError, match="Contact not found"):
            state.apply_input(create_contacts_input(
                operation="remove_from_group",
                timestamp=_T1,
                contact_id="nonexistent",
                group_name="Family",
            ))

    def test_add_to_group_updates_timestamp(self):
        """Add to group should update the contact's updated_at."""
        state, cid = self._create_state_with_contact()
        state.apply_input(create_contacts_input(
            operation="add_to_group",
            timestamp=_T2,
            contact_id=cid,
            group_name="Family",
        ))

        assert state.contacts[cid].updated_at == _T2


# ============================================================================
# 9. Merge Contact Tests
# ============================================================================


class TestMergeContacts:
    """Tests for the merge_contacts operation."""

    def _create_state_with_two_contacts(self) -> tuple[ContactsState, str, str]:
        """Helper to create a state with two contacts."""
        state = create_contacts_state(last_updated=_T0)

        inp1 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            last_name="Smith",
            identifiers=[
                create_contact_identifier("phone", "+15551111111"),
            ],
            company="Acme Corp",
            groups={"Work"},
        )
        state.apply_input(inp1)
        cid1 = list(state.contacts.keys())[0]

        inp2 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alicia",
            last_name="S.",
            identifiers=[
                create_contact_identifier("email", "alice@example.com"),
            ],
            company="Acme Inc",
            notes="Met at conference",
            groups={"Friends"},
        )
        state.apply_input(inp2)
        cid2 = [k for k in state.contacts.keys() if k != cid1][0]

        return state, cid1, cid2

    def test_merge_contacts_basic(self):
        """Primary absorbs secondary's identifiers; secondary is deleted."""
        state, cid1, cid2 = self._create_state_with_two_contacts()

        inp = create_contacts_input(
            operation="merge_contacts",
            timestamp=_T2,
            primary_contact_id=cid1,
            secondary_contact_id=cid2,
        )

        state.apply_input(inp)

        # Secondary should be deleted
        assert cid2 not in state.contacts
        assert len(state.contacts) == 1

        # Primary should have secondary's email
        primary = state.contacts[cid1]
        assert primary.has_identifier("phone", "+15551111111")
        assert primary.has_identifier("email", "alice@example.com")

    def test_merge_contacts_preserves_primary_scalars(self):
        """Primary keeps its fields where both contacts have values."""
        state, cid1, cid2 = self._create_state_with_two_contacts()

        state.apply_input(create_contacts_input(
            operation="merge_contacts",
            timestamp=_T2,
            primary_contact_id=cid1,
            secondary_contact_id=cid2,
        ))

        primary = state.contacts[cid1]
        # Primary had "Alice" / "Smith", secondary had "Alicia" / "S."
        # Primary should keep its own values
        assert primary.first_name == "Alice"
        assert primary.last_name == "Smith"
        assert primary.company == "Acme Corp"

    def test_merge_contacts_fills_primary_gaps(self):
        """Primary gets secondary's fields when primary's are None."""
        state = create_contacts_state(last_updated=_T0)

        # Primary has no notes
        inp1 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551111111")],
        )
        state.apply_input(inp1)
        cid1 = list(state.contacts.keys())[0]

        # Secondary has notes
        inp2 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("email", "bob@test.com")],
            notes="Important person",
            company="BigCo",
        )
        state.apply_input(inp2)
        cid2 = [k for k in state.contacts.keys() if k != cid1][0]

        state.apply_input(create_contacts_input(
            operation="merge_contacts",
            timestamp=_T2,
            primary_contact_id=cid1,
            secondary_contact_id=cid2,
        ))

        primary = state.contacts[cid1]
        assert primary.notes == "Important person"
        assert primary.company == "BigCo"

    def test_merge_contacts_combines_groups(self):
        """Union of both contacts' groups."""
        state, cid1, cid2 = self._create_state_with_two_contacts()

        state.apply_input(create_contacts_input(
            operation="merge_contacts",
            timestamp=_T2,
            primary_contact_id=cid1,
            secondary_contact_id=cid2,
        ))

        primary = state.contacts[cid1]
        assert "Work" in primary.groups
        assert "Friends" in primary.groups

    def test_merge_contacts_combines_addresses(self):
        """Union of both contacts' addresses."""
        state = create_contacts_state(last_updated=_T0)

        addr1 = create_postal_address(street="111 A St", label="home")
        addr2 = create_postal_address(street="222 B St", label="work")

        inp1 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551111111")],
            addresses=[addr1],
        )
        state.apply_input(inp1)
        cid1 = list(state.contacts.keys())[0]

        inp2 = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("email", "b@test.com")],
            addresses=[addr2],
        )
        state.apply_input(inp2)
        cid2 = [k for k in state.contacts.keys() if k != cid1][0]

        state.apply_input(create_contacts_input(
            operation="merge_contacts",
            timestamp=_T2,
            primary_contact_id=cid1,
            secondary_contact_id=cid2,
        ))

        assert len(state.contacts[cid1].addresses) == 2

    def test_merge_contacts_combines_identifiers_deduped(self):
        """Union of identifiers, deduplicating shared ones."""
        state = create_contacts_state(last_updated=_T0)

        # Both contacts share the same phone (normally not allowed,
        # but test via direct state manipulation to verify merge dedup logic)
        c1 = create_contact(
            contact_id="c1",
            identifiers=[
                create_contact_identifier("phone", "+15551111111"),
                create_contact_identifier("email", "shared@test.com"),
            ],
            created_at=_T0,
            updated_at=_T0,
        )
        c2 = create_contact(
            contact_id="c2",
            identifiers=[
                create_contact_identifier("email", "shared@test.com"),
                create_contact_identifier("email", "unique@test.com"),
            ],
            created_at=_T0,
            updated_at=_T0,
        )
        state.contacts["c1"] = c1
        state.contacts["c2"] = c2

        state.apply_input(create_contacts_input(
            operation="merge_contacts",
            timestamp=_T1,
            primary_contact_id="c1",
            secondary_contact_id="c2",
        ))

        primary = state.contacts["c1"]
        # Should have phone, shared email, unique email — no duplicates
        assert len(primary.identifiers) == 3
        assert primary.has_identifier("phone", "+15551111111")
        assert primary.has_identifier("email", "shared@test.com")
        assert primary.has_identifier("email", "unique@test.com")

    def test_merge_contacts_inherits_blocked(self):
        """If secondary is blocked, primary becomes blocked."""
        state = create_contacts_state(last_updated=_T0)

        c1 = create_contact(
            contact_id="c1",
            identifiers=[create_contact_identifier("phone", "+15551111111")],
            is_blocked=False,
            created_at=_T0,
            updated_at=_T0,
        )
        c2 = create_contact(
            contact_id="c2",
            identifiers=[create_contact_identifier("email", "b@test.com")],
            is_blocked=True,
            created_at=_T0,
            updated_at=_T0,
        )
        state.contacts["c1"] = c1
        state.contacts["c2"] = c2

        state.apply_input(create_contacts_input(
            operation="merge_contacts",
            timestamp=_T1,
            primary_contact_id="c1",
            secondary_contact_id="c2",
        ))

        assert state.contacts["c1"].is_blocked is True

    def test_merge_contacts_inherits_favorite(self):
        """If secondary is favorite, primary becomes favorite."""
        state = create_contacts_state(last_updated=_T0)

        c1 = create_contact(
            contact_id="c1",
            identifiers=[create_contact_identifier("phone", "+15551111111")],
            is_favorite=False,
            created_at=_T0,
            updated_at=_T0,
        )
        c2 = create_contact(
            contact_id="c2",
            identifiers=[create_contact_identifier("email", "b@test.com")],
            is_favorite=True,
            created_at=_T0,
            updated_at=_T0,
        )
        state.contacts["c1"] = c1
        state.contacts["c2"] = c2

        state.apply_input(create_contacts_input(
            operation="merge_contacts",
            timestamp=_T1,
            primary_contact_id="c1",
            secondary_contact_id="c2",
        ))

        assert state.contacts["c1"].is_favorite is True

    def test_merge_not_found_primary(self):
        """Merge with nonexistent primary should raise error."""
        state = create_contacts_state(last_updated=_T0)
        c = create_contact(
            contact_id="c2",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            created_at=_T0,
            updated_at=_T0,
        )
        state.contacts["c2"] = c

        with pytest.raises(ValueError, match="Primary contact not found"):
            state.apply_input(create_contacts_input(
                operation="merge_contacts",
                timestamp=_T1,
                primary_contact_id="nonexistent",
                secondary_contact_id="c2",
            ))

    def test_merge_not_found_secondary(self):
        """Merge with nonexistent secondary should raise error."""
        state = create_contacts_state(last_updated=_T0)
        c = create_contact(
            contact_id="c1",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            created_at=_T0,
            updated_at=_T0,
        )
        state.contacts["c1"] = c

        with pytest.raises(ValueError, match="Secondary contact not found"):
            state.apply_input(create_contacts_input(
                operation="merge_contacts",
                timestamp=_T1,
                primary_contact_id="c1",
                secondary_contact_id="nonexistent",
            ))


# ============================================================================
# 10. Cross-Modality Lookup Tests
# ============================================================================


class TestCrossModalityLookup:
    """Tests for cross-modality lookup methods.

    These methods are the primary interface for other modalities (SMS, Email,
    Calendar) to resolve contact information.
    """

    def test_get_display_name_by_phone(self, contacts_state_with_data):
        """Should return resolved display name for known phone number."""
        name = contacts_state_with_data.get_display_name(
            "phone", "+15551234567"
        )
        assert name == "Alice Smith"

    def test_get_display_name_by_email(self, contacts_state_with_data):
        """Should return resolved display name for known email."""
        name = contacts_state_with_data.get_display_name(
            "email", "bob@example.com"
        )
        assert name == "Bob Jones"

    def test_get_display_name_not_found(self, contacts_state_with_data):
        """Should return None for unknown identifier."""
        name = contacts_state_with_data.get_display_name(
            "phone", "+19999999999"
        )
        assert name is None

    def test_is_identifier_blocked_true(self, contacts_state_with_data):
        """Should return True for blocked contact's identifier."""
        # Carol is blocked and has email carol@example.com
        assert contacts_state_with_data.is_identifier_blocked(
            "carol@example.com"
        ) is True

    def test_is_identifier_blocked_false(self, contacts_state_with_data):
        """Should return False for unblocked contact's identifier."""
        # Alice is not blocked
        assert contacts_state_with_data.is_identifier_blocked(
            "+15551234567"
        ) is False

    def test_is_identifier_blocked_unknown(self, contacts_state_with_data):
        """Should return False for unknown identifier."""
        assert contacts_state_with_data.is_identifier_blocked(
            "+19999999999"
        ) is False

    def test_find_contact_by_identifier(self, contacts_state_with_data):
        """Should return full Contact for known identifier."""
        contact = contacts_state_with_data.find_contact_by_identifier(
            "phone", "+15551234567"
        )

        assert contact is not None
        assert contact.first_name == "Alice"
        assert contact.contact_id == "contact-alice"

    def test_find_contact_by_identifier_not_found(
        self, contacts_state_with_data
    ):
        """Should return None for unknown identifier."""
        contact = contacts_state_with_data.find_contact_by_identifier(
            "phone", "+19999999999"
        )
        assert contact is None

    def test_find_contacts_by_group(self, contacts_state_with_data):
        """Should return all contacts in the specified group."""
        work_contacts = contacts_state_with_data.find_contacts_by_group("Work")

        contact_ids = {c.contact_id for c in work_contacts}
        # Alice and Bob are both in "Work"
        assert "contact-alice" in contact_ids
        assert "contact-bob" in contact_ids

    def test_find_contacts_by_group_empty(self, contacts_state_with_data):
        """Should return empty list for nonexistent group."""
        result = contacts_state_with_data.find_contacts_by_group("Nonexistent")
        assert result == []

    def test_get_all_groups(self, contacts_state_with_data):
        """Should return union of all contacts' groups."""
        groups = contacts_state_with_data.get_all_groups()

        assert "Family" in groups
        assert "Work" in groups

    def test_get_all_groups_empty(self):
        """Should return empty set when no contacts."""
        state = create_contacts_state()
        assert state.get_all_groups() == set()

    def test_get_favorites(self, contacts_state_with_data):
        """Should return only favorited contacts."""
        favorites = contacts_state_with_data.get_favorites()

        assert len(favorites) == 1
        assert favorites[0].contact_id == "contact-alice"

    def test_get_blocked_contacts(self, contacts_state_with_data):
        """Should return only blocked contacts."""
        blocked = contacts_state_with_data.get_blocked_contacts()

        assert len(blocked) == 1
        assert blocked[0].contact_id == "contact-carol"


# ============================================================================
# 11. Query Tests
# ============================================================================


class TestQuery:
    """Tests for the query() method."""

    def test_query_all(self, contacts_state_with_data):
        """Query with no filters should return all contacts."""
        result = contacts_state_with_data.query({})

        assert result["count"] == 3
        assert len(result["contacts"]) == 3

    def test_query_search_text_name(self, contacts_state_with_data):
        """search_text should match on first/last/display/nickname."""
        result = contacts_state_with_data.query({"search_text": "Alice"})

        assert result["count"] == 1
        assert result["contacts"][0]["first_name"] == "Alice"

    def test_query_search_text_case_insensitive(self, contacts_state_with_data):
        """Search should be case-insensitive."""
        result = contacts_state_with_data.query({"search_text": "alice"})

        assert result["count"] == 1

    def test_query_search_text_partial(self, contacts_state_with_data):
        """Search should match partial strings (substring)."""
        result = contacts_state_with_data.query({"search_text": "Smi"})

        assert result["count"] == 1
        assert result["contacts"][0]["first_name"] == "Alice"

    def test_query_search_text_company(self, contacts_state_with_data):
        """Search should match company name."""
        result = contacts_state_with_data.query({"search_text": "GlobalTech"})

        assert result["count"] == 1
        assert result["contacts"][0]["first_name"] == "Bob"

    def test_query_search_text_identifier(self, contacts_state_with_data):
        """Search should match identifier values."""
        result = contacts_state_with_data.query({"search_text": "+15551234567"})

        assert result["count"] == 1
        assert result["contacts"][0]["first_name"] == "Alice"

    def test_query_filter_group(self, contacts_state_with_data):
        """Filter by group membership."""
        result = contacts_state_with_data.query({"group": "Work"})

        assert result["count"] == 2  # Alice and Bob

    def test_query_filter_group_exclusive(self, contacts_state_with_data):
        """Filter by group that only one contact belongs to."""
        result = contacts_state_with_data.query({"group": "Family"})

        assert result["count"] == 1  # Only Alice

    def test_query_filter_is_favorite(self, contacts_state_with_data):
        """Filter favorites only."""
        result = contacts_state_with_data.query({"is_favorite": True})

        assert result["count"] == 1
        assert result["contacts"][0]["first_name"] == "Alice"

    def test_query_filter_is_blocked(self, contacts_state_with_data):
        """Filter blocked only."""
        result = contacts_state_with_data.query({"is_blocked": True})

        assert result["count"] == 1
        assert result["contacts"][0]["first_name"] == "Carol"

    def test_query_filter_has_phone(self, contacts_state_with_data):
        """Filter contacts with at least one phone identifier."""
        result = contacts_state_with_data.query({"has_phone": True})

        # Alice and Bob have phones, Carol doesn't
        assert result["count"] == 2

    def test_query_filter_has_email(self, contacts_state_with_data):
        """Filter contacts with at least one email identifier."""
        result = contacts_state_with_data.query({"has_email": True})

        # All three have emails
        assert result["count"] == 3

    def test_query_identifier_lookup(self, contacts_state_with_data):
        """Exact match by identifier_type + identifier_value."""
        result = contacts_state_with_data.query({
            "identifier_type": "phone",
            "identifier_value": "+15551234567",
        })

        assert result["count"] == 1
        assert result["contacts"][0]["first_name"] == "Alice"

    def test_query_limit(self, contacts_state_with_data):
        """Limit should cap the number of returned results."""
        result = contacts_state_with_data.query({"limit": 2})

        assert result["count"] == 3  # total still 3
        assert result["returned_count"] == 2

    def test_query_offset(self, contacts_state_with_data):
        """Offset should skip results."""
        result = contacts_state_with_data.query({"offset": 2})

        assert result["count"] == 3  # total still 3
        assert result["returned_count"] == 1

    def test_query_limit_and_offset(self, contacts_state_with_data):
        """Combined pagination."""
        result = contacts_state_with_data.query({
            "limit": 1,
            "offset": 1,
        })

        assert result["count"] == 3
        assert result["returned_count"] == 1

    def test_query_no_results(self, contacts_state_with_data):
        """Query that matches nothing should return empty list."""
        result = contacts_state_with_data.query({
            "search_text": "ZZZZZZ_NONEXISTENT",
        })

        assert result["count"] == 0
        assert result["contacts"] == []

    def test_query_response_structure(self, contacts_state_with_data):
        """Verify response has expected keys: contacts, count, query_params."""
        result = contacts_state_with_data.query({"search_text": "Alice"})

        assert "contacts" in result
        assert "count" in result
        assert "returned_count" in result
        assert "query_params" in result


# ============================================================================
# 12. Snapshot Tests
# ============================================================================


class TestSnapshots:
    """Tests for get_snapshot() and get_compact_snapshot()."""

    def test_snapshot_empty_state(self):
        """Snapshot of empty state should have correct structure and zero counts."""
        state = create_contacts_state(last_updated=_T0)
        snapshot = state.get_snapshot()

        assert snapshot["modality_type"] == "contacts"
        assert snapshot["total_contacts"] == 0
        assert snapshot["favorites_count"] == 0
        assert snapshot["blocked_count"] == 0
        assert snapshot["groups"] == []
        assert snapshot["contacts"] == {}

    def test_snapshot_with_contacts(self, contacts_state_with_data):
        """Snapshot should include all contacts serialized."""
        snapshot = contacts_state_with_data.get_snapshot()

        assert snapshot["total_contacts"] == 3
        assert "contact-alice" in snapshot["contacts"]
        assert "contact-bob" in snapshot["contacts"]
        assert "contact-carol" in snapshot["contacts"]

    def test_snapshot_includes_groups(self, contacts_state_with_data):
        """Snapshot should derive groups from contacts."""
        snapshot = contacts_state_with_data.get_snapshot()

        assert "Family" in snapshot["groups"]
        assert "Work" in snapshot["groups"]

    def test_snapshot_includes_counts(self, contacts_state_with_data):
        """Snapshot should include total, favorites, and blocked counts."""
        snapshot = contacts_state_with_data.get_snapshot()

        assert snapshot["total_contacts"] == 3
        assert snapshot["favorites_count"] == 1  # Alice
        assert snapshot["blocked_count"] == 1  # Carol

    def test_compact_snapshot(self, contacts_state_with_data):
        """Compact snapshot should have LLM-optimized structure."""
        snapshot = contacts_state_with_data.get_compact_snapshot(_T2)

        assert "modality_type" in snapshot
        assert snapshot["modality_type"] == "contacts"
        assert "last_updated" in snapshot
        assert "update_count" in snapshot
        assert "total_contacts" in snapshot
        assert "favorites_count" in snapshot
        assert "blocked_count" in snapshot
        assert "groups" in snapshot
        assert "recent_contacts" in snapshot

        # Groups should be dict with counts
        assert isinstance(snapshot["groups"], dict)
        assert snapshot["total_contacts"] == 3

    def test_compact_snapshot_recent_contacts(self, contacts_state_with_data):
        """Compact snapshot should list recently updated contacts."""
        snapshot = contacts_state_with_data.get_compact_snapshot(_T2)

        assert len(snapshot["recent_contacts"]) > 0
        for entry in snapshot["recent_contacts"]:
            assert "name" in entry
            assert "updated_ago" in entry

    def test_summary_property_empty(self):
        """Summary of empty state should indicate no contacts."""
        state = create_contacts_state()
        assert state.summary == "No contacts"

    def test_summary_property_with_contacts(self, contacts_state_with_data):
        """Summary should include counts."""
        summary = contacts_state_with_data.summary
        assert "3 contacts" in summary
        assert "1 favorite" in summary
        assert "1 blocked" in summary


# ============================================================================
# 13. Validate State Tests
# ============================================================================


class TestValidateState:
    """Tests for validate_state()."""

    def test_validate_state_clean(self, contacts_state_with_data):
        """Valid state should return no issues."""
        issues = contacts_state_with_data.validate_state()
        assert issues == []

    def test_validate_state_duplicate_identifiers(self):
        """Should detect cross-contact duplicate identifiers."""
        state = create_contacts_state(last_updated=_T0)

        # Manually add two contacts with same identifier (bypassing checks)
        c1 = create_contact(
            contact_id="c1",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            created_at=_T0,
            updated_at=_T0,
        )
        c2 = create_contact(
            contact_id="c2",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            created_at=_T0,
            updated_at=_T0,
        )
        state.contacts["c1"] = c1
        state.contacts["c2"] = c2

        issues = state.validate_state()
        assert len(issues) > 0
        assert any("Duplicate identifier" in issue for issue in issues)

    def test_validate_state_contact_without_identifiers(self):
        """Should detect contacts that have no identifiers."""
        state = create_contacts_state(last_updated=_T0)

        c = Contact(
            contact_id="c1",
            first_name="Ghost",
            identifiers=[],
            created_at=_T0,
            updated_at=_T0,
        )
        state.contacts["c1"] = c

        issues = state.validate_state()
        assert len(issues) > 0
        assert any("has no identifiers" in issue for issue in issues)


# ============================================================================
# 14. Undo Tests
# ============================================================================


class TestUndo:
    """Tests for create_undo_data() and apply_undo()."""

    def test_undo_create_contact(self):
        """Undo create should remove the created contact."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )

        undo_data = state.create_undo_data(inp)
        state.apply_input(inp)
        assert len(state.contacts) == 1

        state.apply_undo(undo_data)
        assert len(state.contacts) == 0

    def test_undo_delete_contact(self):
        """Undo delete should restore the deleted contact with all data."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            last_name="Smith",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            groups={"Family"},
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_delete = create_contacts_input(
            operation="delete_contact",
            timestamp=_T2,
            contact_id=cid,
        )

        undo_data = state.create_undo_data(inp_delete)
        state.apply_input(inp_delete)
        assert len(state.contacts) == 0

        state.apply_undo(undo_data)
        assert len(state.contacts) == 1
        restored = state.contacts[cid]
        assert restored.first_name == "Alice"
        assert restored.last_name == "Smith"
        assert restored.has_identifier("phone", "+15551234567")
        assert "Family" in restored.groups

    def test_undo_update_contact(self):
        """Undo update should restore previous field values."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            first_name="Alice",
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_update = create_contacts_input(
            operation="update_contact",
            timestamp=_T2,
            contact_id=cid,
            first_name="Alicia",
            company="NewCo",
        )

        undo_data = state.create_undo_data(inp_update)
        state.apply_input(inp_update)
        assert state.contacts[cid].first_name == "Alicia"
        assert state.contacts[cid].company == "NewCo"

        state.apply_undo(undo_data)
        assert state.contacts[cid].first_name == "Alice"
        assert state.contacts[cid].company is None

    def test_undo_block_contact(self):
        """Undo block should restore previous blocked state."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]
        assert state.contacts[cid].is_blocked is False

        inp_block = create_contacts_input(
            operation="block_contact",
            timestamp=_T2,
            contact_id=cid,
        )

        undo_data = state.create_undo_data(inp_block)
        state.apply_input(inp_block)
        assert state.contacts[cid].is_blocked is True

        state.apply_undo(undo_data)
        assert state.contacts[cid].is_blocked is False

    def test_undo_unblock_contact(self):
        """Undo unblock should restore previous blocked state."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            is_blocked=True,
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_unblock = create_contacts_input(
            operation="unblock_contact",
            timestamp=_T2,
            contact_id=cid,
        )

        undo_data = state.create_undo_data(inp_unblock)
        state.apply_input(inp_unblock)
        assert state.contacts[cid].is_blocked is False

        state.apply_undo(undo_data)
        assert state.contacts[cid].is_blocked is True

    def test_undo_favorite_contact(self):
        """Undo favorite should restore previous favorite state."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_fav = create_contacts_input(
            operation="favorite_contact",
            timestamp=_T2,
            contact_id=cid,
        )

        undo_data = state.create_undo_data(inp_fav)
        state.apply_input(inp_fav)
        assert state.contacts[cid].is_favorite is True

        state.apply_undo(undo_data)
        assert state.contacts[cid].is_favorite is False

    def test_undo_add_to_group(self):
        """Undo add_to_group should remove group membership."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_group = create_contacts_input(
            operation="add_to_group",
            timestamp=_T2,
            contact_id=cid,
            group_name="Family",
        )

        undo_data = state.create_undo_data(inp_group)
        state.apply_input(inp_group)
        assert "Family" in state.contacts[cid].groups

        state.apply_undo(undo_data)
        assert "Family" not in state.contacts[cid].groups

    def test_undo_remove_from_group(self):
        """Undo remove_from_group should restore group membership."""
        state = create_contacts_state(last_updated=_T0)
        inp_create = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
            groups={"Family"},
        )
        state.apply_input(inp_create)
        cid = list(state.contacts.keys())[0]

        inp_remove_group = create_contacts_input(
            operation="remove_from_group",
            timestamp=_T2,
            contact_id=cid,
            group_name="Family",
        )

        undo_data = state.create_undo_data(inp_remove_group)
        state.apply_input(inp_remove_group)
        assert "Family" not in state.contacts[cid].groups

        state.apply_undo(undo_data)
        assert "Family" in state.contacts[cid].groups

    def test_undo_merge_contacts(self):
        """Undo merge should restore both contacts to pre-merge state."""
        state = create_contacts_state(last_updated=_T0)

        c1 = create_contact(
            contact_id="c1",
            first_name="Alice",
            identifiers=[create_contact_identifier("phone", "+15551111111")],
            groups={"Work"},
            created_at=_T0,
            updated_at=_T0,
        )
        c2 = create_contact(
            contact_id="c2",
            first_name="Bob",
            identifiers=[create_contact_identifier("email", "bob@test.com")],
            groups={"Friends"},
            created_at=_T0,
            updated_at=_T0,
        )
        state.contacts["c1"] = c1
        state.contacts["c2"] = c2

        inp_merge = create_contacts_input(
            operation="merge_contacts",
            timestamp=_T1,
            primary_contact_id="c1",
            secondary_contact_id="c2",
        )

        undo_data = state.create_undo_data(inp_merge)
        state.apply_input(inp_merge)
        assert len(state.contacts) == 1
        assert "c2" not in state.contacts

        state.apply_undo(undo_data)
        assert len(state.contacts) == 2
        assert "c1" in state.contacts
        assert "c2" in state.contacts
        assert state.contacts["c1"].first_name == "Alice"
        assert state.contacts["c2"].first_name == "Bob"
        assert state.contacts["c1"].groups == {"Work"}
        assert state.contacts["c2"].groups == {"Friends"}

    def test_undo_restores_update_count(self):
        """update_count should revert after undo."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )

        assert state.update_count == 0
        undo_data = state.create_undo_data(inp)
        state.apply_input(inp)
        assert state.update_count == 1

        state.apply_undo(undo_data)
        assert state.update_count == 0

    def test_undo_restores_last_updated(self):
        """last_updated should revert after undo."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )

        undo_data = state.create_undo_data(inp)
        state.apply_input(inp)
        assert state.last_updated == _T1

        state.apply_undo(undo_data)
        assert state.last_updated == _T0


# ============================================================================
# 15. Clear Tests
# ============================================================================


class TestClear:
    """Tests for clear()."""

    def test_clear_removes_contacts(self, contacts_state_with_data):
        """clear() should remove all contacts."""
        assert len(contacts_state_with_data.contacts) == 3

        contacts_state_with_data.clear()

        assert len(contacts_state_with_data.contacts) == 0

    def test_clear_resets_counts(self):
        """clear() should reset update_count to 0."""
        state = create_contacts_state(last_updated=_T0)
        inp = create_contacts_input(
            operation="create_contact",
            timestamp=_T1,
            identifiers=[create_contact_identifier("phone", "+15551234567")],
        )
        state.apply_input(inp)
        assert state.update_count == 1

        state.clear()

        assert state.update_count == 0
