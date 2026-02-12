"""Tests for ContactsInput model.

Tests the contacts input model including helper classes (ContactIdentifier,
PostalAddress), operation validation, method behavior, and serialization.

Tests are organized by:
- General ModalityInput pattern tests (replicated for all modalities)
- Helper class tests (ContactIdentifier, PostalAddress)
- Operation-specific validation tests
- Method tests (get_summary, get_affected_entities, should_merge_with)
- Serialization round-trip tests
- Edge case tests
- Fixture sanity-check tests
"""

from datetime import date, datetime, timezone

import pytest

from ues.models.modalities.contacts_input import (
    ContactIdentifier,
    ContactsInput,
    PostalAddress,
)


# ============================================================================
# General ModalityInput Pattern Tests
# ============================================================================


class TestContactsInputInstantiation:
    """Tests for ContactsInput construction and defaults.

    GENERAL PATTERN: These tests verify the base class contract and should
    be replicated for all modalities.
    """

    def test_minimal_create_contact(self):
        """Create a contacts input with only required fields for create."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+15551234567"
                )
            ],
        )
        assert ci.modality_type == "contacts"
        assert ci.operation == "create_contact"
        assert ci.identifiers is not None
        assert len(ci.identifiers) == 1

    def test_modality_type_is_frozen(self):
        """modality_type should always be 'contacts' and cannot be changed."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="delete_contact",
            contact_id="c1",
        )
        assert ci.modality_type == "contacts"
        with pytest.raises(Exception):
            ci.modality_type = "other"

    def test_auto_generated_input_id(self):
        """input_id should be auto-generated as a unique UUID string."""
        ci1 = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="delete_contact",
            contact_id="c1",
        )
        ci2 = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="delete_contact",
            contact_id="c1",
        )
        assert ci1.input_id
        assert ci2.input_id
        assert ci1.input_id != ci2.input_id

    def test_timestamp_must_be_provided(self):
        """timestamp is a required field."""
        with pytest.raises(Exception):
            ContactsInput(operation="delete_contact", contact_id="c1")

    def test_optional_fields_default_to_none(self):
        """All optional data fields should default to None."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="delete_contact",
            contact_id="c1",
        )
        assert ci.first_name is None
        assert ci.last_name is None
        assert ci.display_name is None
        assert ci.nickname is None
        assert ci.identifiers is None
        assert ci.add_identifiers is None
        assert ci.remove_identifiers is None
        assert ci.company is None
        assert ci.job_title is None
        assert ci.addresses is None
        assert ci.birthday is None
        assert ci.notes is None
        assert ci.photo_url is None
        assert ci.is_favorite is None
        assert ci.is_blocked is None
        assert ci.groups is None
        assert ci.add_groups is None
        assert ci.remove_groups is None
        assert ci.group_name is None
        assert ci.primary_contact_id is None
        assert ci.secondary_contact_id is None

    def test_all_operations_are_valid(self):
        """All 10 defined operations should be accepted."""
        operations = [
            "create_contact",
            "update_contact",
            "delete_contact",
            "block_contact",
            "unblock_contact",
            "favorite_contact",
            "unfavorite_contact",
            "add_to_group",
            "remove_from_group",
            "merge_contacts",
        ]
        for op in operations:
            ci = ContactsInput(
                timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
                operation=op,
            )
            assert ci.operation == op

    def test_invalid_operation_rejected(self):
        """Unknown operation types should be rejected at construction."""
        with pytest.raises(Exception):
            ContactsInput(
                timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
                operation="nonexistent_operation",
            )


# ============================================================================
# ContactIdentifier Helper Tests
# ============================================================================


class TestContactIdentifier:
    """Tests for the ContactIdentifier helper model.

    MODALITY-SPECIFIC: ContactIdentifier is unique to the contacts modality.
    """

    def test_creation_with_all_fields(self):
        """Create identifier with type, value, and optional label."""
        ci = ContactIdentifier(
            identifier_type="phone", value="+15551234567", label="mobile"
        )
        assert ci.identifier_type == "phone"
        assert ci.value == "+15551234567"
        assert ci.label == "mobile"

    def test_creation_without_label(self):
        """Label should be optional and default to None."""
        ci = ContactIdentifier(
            identifier_type="email", value="test@example.com"
        )
        assert ci.label is None

    def test_empty_identifier_type_rejected(self):
        """identifier_type must be a non-empty string."""
        with pytest.raises(ValueError, match="non-empty"):
            ContactIdentifier(identifier_type="", value="test")

    def test_whitespace_only_identifier_type_rejected(self):
        """identifier_type of only whitespace should be rejected."""
        with pytest.raises(ValueError, match="non-empty"):
            ContactIdentifier(identifier_type="   ", value="test")

    def test_empty_value_rejected(self):
        """value must be a non-empty string."""
        with pytest.raises(ValueError, match="non-empty"):
            ContactIdentifier(identifier_type="phone", value="")

    def test_whitespace_only_value_rejected(self):
        """value of only whitespace should be rejected."""
        with pytest.raises(ValueError, match="non-empty"):
            ContactIdentifier(identifier_type="phone", value="   ")

    def test_email_must_contain_at_symbol(self):
        """Email identifiers must contain '@' in the value."""
        with pytest.raises(ValueError, match="@"):
            ContactIdentifier(
                identifier_type="email", value="not-an-email"
            )

    def test_email_with_at_symbol_accepted(self):
        """Valid email format should be accepted."""
        ci = ContactIdentifier(
            identifier_type="email", value="user@example.com"
        )
        assert ci.value == "user@example.com"

    def test_phone_does_not_validate_format(self):
        """Phone identifiers should not enforce strict format (design decision)."""
        # E.164 format is recommended but not enforced
        ci = ContactIdentifier(
            identifier_type="phone", value="555-1234"
        )
        assert ci.value == "555-1234"

    def test_extensible_identifier_types(self):
        """Custom identifier types (discord, slack, etc.) should be accepted."""
        ci = ContactIdentifier(
            identifier_type="discord", value="user#1234"
        )
        assert ci.identifier_type == "discord"

    def test_to_dict_includes_required_fields(self):
        """to_dict() should include identifier_type and value."""
        ci = ContactIdentifier(
            identifier_type="phone", value="+15551234567"
        )
        d = ci.to_dict()
        assert d["identifier_type"] == "phone"
        assert d["value"] == "+15551234567"

    def test_to_dict_includes_label_when_present(self):
        """to_dict() should include label only when it is set."""
        ci_with = ContactIdentifier(
            identifier_type="phone", value="+1555", label="work"
        )
        ci_without = ContactIdentifier(
            identifier_type="phone", value="+1555"
        )
        assert "label" in ci_with.to_dict()
        assert "label" not in ci_without.to_dict()


# ============================================================================
# PostalAddress Helper Tests
# ============================================================================


class TestPostalAddress:
    """Tests for the PostalAddress helper model.

    MODALITY-SPECIFIC: PostalAddress is unique to the contacts modality.
    """

    def test_creation_with_all_fields(self):
        """Create address with all fields populated."""
        addr = PostalAddress(
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
            country="US",
            label="home",
        )
        assert addr.street == "123 Main St"
        assert addr.city == "Springfield"
        assert addr.state == "IL"
        assert addr.postal_code == "62701"
        assert addr.country == "US"
        assert addr.label == "home"

    def test_all_fields_optional(self):
        """All PostalAddress fields should be optional."""
        addr = PostalAddress()
        assert addr.street is None
        assert addr.city is None
        assert addr.state is None
        assert addr.postal_code is None
        assert addr.country is None
        assert addr.label is None

    def test_format_oneline_full_address(self):
        """format_oneline() should join non-None components with commas."""
        addr = PostalAddress(
            street="123 Main St",
            city="Springfield",
            state="IL",
            postal_code="62701",
            country="US",
        )
        oneline = addr.format_oneline()
        assert "123 Main St" in oneline
        assert "Springfield" in oneline
        assert "IL 62701" in oneline
        assert "US" in oneline

    def test_format_oneline_partial_address(self):
        """format_oneline() should handle partial addresses gracefully."""
        addr = PostalAddress(city="Portland", state="OR")
        oneline = addr.format_oneline()
        assert "Portland" in oneline
        assert "OR" in oneline

    def test_format_oneline_empty_address(self):
        """format_oneline() should return empty string for empty address."""
        addr = PostalAddress()
        assert addr.format_oneline() == ""

    def test_format_oneline_state_without_postal_code(self):
        """format_oneline() should handle state without postal code."""
        addr = PostalAddress(state="CA")
        assert addr.format_oneline() == "CA"

    def test_format_oneline_postal_code_without_state(self):
        """format_oneline() should handle postal code without state."""
        addr = PostalAddress(postal_code="90210")
        assert addr.format_oneline() == "90210"

    def test_to_dict_omits_none_fields(self):
        """to_dict() should only include fields that are set."""
        addr = PostalAddress(city="Portland")
        d = addr.to_dict()
        assert d == {"city": "Portland"}
        assert "street" not in d
        assert "state" not in d

    def test_to_dict_all_fields(self):
        """to_dict() should include all fields when all are set."""
        addr = PostalAddress(
            street="123 Main",
            city="Portland",
            state="OR",
            postal_code="97201",
            country="US",
            label="work",
        )
        d = addr.to_dict()
        assert len(d) == 6


# ============================================================================
# Operation-Specific Validation Tests
# ============================================================================


class TestContactsInputValidation:
    """Tests for validate_input() — operation-specific required fields.

    Per the design doc, each operation type has specific required fields.
    validate_input() should enforce these requirements.
    """

    # --- create_contact ---

    def test_create_contact_requires_identifiers(self):
        """create_contact must have at least one identifier."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            first_name="Alice",
            # identifiers not provided
        )
        with pytest.raises(ValueError, match="identifier"):
            ci.validate_input()

    def test_create_contact_rejects_empty_identifiers_list(self):
        """create_contact with an empty identifiers list should fail."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            first_name="Alice",
            identifiers=[],
        )
        with pytest.raises(ValueError, match="identifier"):
            ci.validate_input()

    def test_create_contact_with_valid_data(self):
        """create_contact with at least one identifier should pass validation."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            first_name="Alice",
            last_name="Smith",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+15551234567"
                )
            ],
            company="Acme",
            birthday=date(1990, 5, 15),
            groups={"Family"},
        )
        ci.validate_input()  # Should not raise

    # --- update_contact ---

    def test_update_contact_requires_contact_id(self):
        """update_contact must have contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="update_contact",
            first_name="Updated",
        )
        with pytest.raises(ValueError, match="contact_id"):
            ci.validate_input()

    def test_update_contact_with_contact_id_passes(self):
        """update_contact with contact_id should pass validation."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="update_contact",
            contact_id="c1",
            first_name="Updated",
        )
        ci.validate_input()  # Should not raise

    def test_update_contact_with_additive_fields(self):
        """update_contact supports add_identifiers, add_groups etc."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="update_contact",
            contact_id="c1",
            add_identifiers=[
                ContactIdentifier(
                    identifier_type="email", value="new@example.com"
                )
            ],
            add_groups={"NewGroup"},
        )
        ci.validate_input()  # Should not raise

    # --- delete_contact ---

    def test_delete_contact_requires_contact_id(self):
        """delete_contact must have contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="delete_contact",
        )
        with pytest.raises(ValueError, match="contact_id"):
            ci.validate_input()

    # --- block_contact ---

    def test_block_contact_requires_contact_id(self):
        """block_contact must have contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="block_contact",
        )
        with pytest.raises(ValueError, match="contact_id"):
            ci.validate_input()

    # --- unblock_contact ---

    def test_unblock_contact_requires_contact_id(self):
        """unblock_contact must have contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="unblock_contact",
        )
        with pytest.raises(ValueError, match="contact_id"):
            ci.validate_input()

    # --- favorite_contact ---

    def test_favorite_contact_requires_contact_id(self):
        """favorite_contact must have contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="favorite_contact",
        )
        with pytest.raises(ValueError, match="contact_id"):
            ci.validate_input()

    # --- unfavorite_contact ---

    def test_unfavorite_contact_requires_contact_id(self):
        """unfavorite_contact must have contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="unfavorite_contact",
        )
        with pytest.raises(ValueError, match="contact_id"):
            ci.validate_input()

    # --- add_to_group ---

    def test_add_to_group_requires_contact_id_and_group(self):
        """add_to_group must have both contact_id and group_name."""
        # Missing both
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="add_to_group",
        )
        with pytest.raises(ValueError):
            ci.validate_input()

    def test_add_to_group_missing_group_name(self):
        """add_to_group with contact_id but no group_name should fail."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="add_to_group",
            contact_id="c1",
        )
        with pytest.raises(ValueError, match="group_name"):
            ci.validate_input()

    def test_add_to_group_missing_contact_id(self):
        """add_to_group with group_name but no contact_id should fail."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="add_to_group",
            group_name="Family",
        )
        with pytest.raises(ValueError, match="contact_id"):
            ci.validate_input()

    # --- remove_from_group ---

    def test_remove_from_group_requires_contact_id_and_group(self):
        """remove_from_group must have both contact_id and group_name."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="remove_from_group",
            contact_id="c1",
        )
        with pytest.raises(ValueError, match="group_name"):
            ci.validate_input()

    # --- merge_contacts ---

    def test_merge_requires_primary_contact_id(self):
        """merge_contacts must have primary_contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="merge_contacts",
            secondary_contact_id="c2",
        )
        with pytest.raises(ValueError, match="primary_contact_id"):
            ci.validate_input()

    def test_merge_requires_secondary_contact_id(self):
        """merge_contacts must have secondary_contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="merge_contacts",
            primary_contact_id="c1",
        )
        with pytest.raises(ValueError, match="secondary_contact_id"):
            ci.validate_input()

    def test_merge_rejects_same_ids(self):
        """merge_contacts should reject when primary == secondary."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="merge_contacts",
            primary_contact_id="c1",
            secondary_contact_id="c1",
        )
        with pytest.raises(ValueError, match="different"):
            ci.validate_input()

    def test_merge_with_different_ids_passes(self):
        """merge_contacts with distinct IDs should pass validation."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="merge_contacts",
            primary_contact_id="c1",
            secondary_contact_id="c2",
        )
        ci.validate_input()  # Should not raise


# ============================================================================
# Method Tests
# ============================================================================


class TestContactsInputMethods:
    """Tests for get_summary(), get_affected_entities(), should_merge_with().

    These test the abstract method implementations required by ModalityInput.
    """

    # --- get_summary ---

    def test_summary_create_with_name(self):
        """Create summary should include name and first identifier."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            first_name="Alice",
            last_name="Smith",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+15551234567"
                )
            ],
        )
        summary = ci.get_summary()
        assert "Alice Smith" in summary
        assert "+15551234567" in summary

    def test_summary_create_without_name(self):
        """Create summary with no name should still include identifier."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            identifiers=[
                ContactIdentifier(
                    identifier_type="email", value="test@example.com"
                )
            ],
        )
        summary = ci.get_summary()
        assert "test@example.com" in summary

    def test_summary_update(self):
        """Update summary should include contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="update_contact",
            contact_id="c-123",
        )
        summary = ci.get_summary()
        assert "c-123" in summary

    def test_summary_delete(self):
        """Delete summary should include contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="delete_contact",
            contact_id="c-123",
        )
        summary = ci.get_summary()
        assert "c-123" in summary

    def test_summary_block(self):
        """Block summary should include contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="block_contact",
            contact_id="c-123",
        )
        summary = ci.get_summary()
        assert "c-123" in summary
        assert "lock" in summary.lower()

    def test_summary_unblock(self):
        """Unblock summary should include contact_id."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="unblock_contact",
            contact_id="c-123",
        )
        summary = ci.get_summary()
        assert "c-123" in summary

    def test_summary_add_to_group(self):
        """Add to group summary should include contact_id and group name."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="add_to_group",
            contact_id="c-123",
            group_name="Family",
        )
        summary = ci.get_summary()
        assert "c-123" in summary
        assert "Family" in summary

    def test_summary_remove_from_group(self):
        """Remove from group summary should include contact_id and group name."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="remove_from_group",
            contact_id="c-123",
            group_name="Work",
        )
        summary = ci.get_summary()
        assert "c-123" in summary
        assert "Work" in summary

    def test_summary_merge(self):
        """Merge summary should include both contact IDs."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="merge_contacts",
            primary_contact_id="c-primary",
            secondary_contact_id="c-secondary",
        )
        summary = ci.get_summary()
        assert "c-primary" in summary
        assert "c-secondary" in summary

    def test_summary_returns_string_for_all_operations(self):
        """get_summary() should return a non-empty string for every operation."""
        operations_data = [
            {"operation": "create_contact", "identifiers": [
                ContactIdentifier(identifier_type="phone", value="+1555")
            ]},
            {"operation": "update_contact", "contact_id": "c1"},
            {"operation": "delete_contact", "contact_id": "c1"},
            {"operation": "block_contact", "contact_id": "c1"},
            {"operation": "unblock_contact", "contact_id": "c1"},
            {"operation": "favorite_contact", "contact_id": "c1"},
            {"operation": "unfavorite_contact", "contact_id": "c1"},
            {"operation": "add_to_group", "contact_id": "c1",
             "group_name": "G"},
            {"operation": "remove_from_group", "contact_id": "c1",
             "group_name": "G"},
            {"operation": "merge_contacts", "primary_contact_id": "c1",
             "secondary_contact_id": "c2"},
        ]
        for data in operations_data:
            ci = ContactsInput(
                timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
                **data,
            )
            summary = ci.get_summary()
            assert isinstance(summary, str)
            assert len(summary) > 0, f"Empty summary for {data['operation']}"

    # --- get_affected_entities ---

    def test_affected_entities_single_contact(self):
        """Operations targeting one contact should return [contact_id]."""
        for op in [
            "update_contact",
            "delete_contact",
            "block_contact",
            "unblock_contact",
            "favorite_contact",
            "unfavorite_contact",
            "add_to_group",
            "remove_from_group",
        ]:
            ci = ContactsInput(
                timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
                operation=op,
                contact_id="c-target",
                group_name="G" if "group" in op else None,
            )
            entities = ci.get_affected_entities()
            assert entities == ["c-target"], f"Failed for {op}"

    def test_affected_entities_merge_returns_both(self):
        """merge_contacts should return both primary and secondary IDs."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="merge_contacts",
            primary_contact_id="c-primary",
            secondary_contact_id="c-secondary",
        )
        entities = ci.get_affected_entities()
        assert "c-primary" in entities
        assert "c-secondary" in entities
        assert len(entities) == 2

    def test_affected_entities_create_returns_empty(self):
        """create_contact has no pre-existing contact_id, returns empty list."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+15551234567"
                )
            ],
        )
        entities = ci.get_affected_entities()
        assert entities == []

    # --- should_merge_with ---

    def test_should_merge_with_always_false(self):
        """Contact operations are discrete and should never merge."""
        ci1 = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+15551234567"
                )
            ],
        )
        ci2 = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+15559876543"
                )
            ],
        )
        assert ci1.should_merge_with(ci2) is False

    def test_should_merge_with_different_operations(self):
        """should_merge_with should still return False for different ops."""
        ci1 = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="block_contact",
            contact_id="c1",
        )
        ci2 = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="unblock_contact",
            contact_id="c1",
        )
        assert ci1.should_merge_with(ci2) is False


# ============================================================================
# Serialization Tests
# ============================================================================


class TestContactsInputSerialization:
    """Tests for model_dump() → model_validate() round-trip.

    GENERAL PATTERN: Verifies that inputs can be serialized and deserialized
    without data loss.
    """

    def test_simple_create_roundtrip(self):
        """Serialize and deserialize a create_contact input."""
        original = ContactsInput(
            timestamp=datetime(2025, 6, 1, 10, 0, 0, tzinfo=timezone.utc),
            operation="create_contact",
            first_name="Alice",
            last_name="Smith",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone",
                    value="+15551234567",
                    label="mobile",
                )
            ],
            birthday=date(1990, 5, 15),
            groups={"Family", "Friends"},
        )
        dumped = original.model_dump(mode="json")
        restored = ContactsInput.model_validate(dumped)
        assert restored.operation == original.operation
        assert restored.first_name == original.first_name
        assert restored.last_name == original.last_name
        assert len(restored.identifiers) == 1
        assert restored.identifiers[0].value == "+15551234567"
        assert restored.birthday == original.birthday
        assert restored.groups == original.groups

    def test_update_with_additive_fields_roundtrip(self):
        """Serialize and deserialize an update with additive fields."""
        original = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="update_contact",
            contact_id="c1",
            add_identifiers=[
                ContactIdentifier(
                    identifier_type="email", value="new@example.com"
                )
            ],
            add_groups={"NewGroup"},
            remove_groups={"OldGroup"},
        )
        dumped = original.model_dump(mode="json")
        restored = ContactsInput.model_validate(dumped)
        assert restored.contact_id == "c1"
        assert len(restored.add_identifiers) == 1
        assert restored.add_groups == {"NewGroup"}
        assert restored.remove_groups == {"OldGroup"}

    def test_merge_roundtrip(self):
        """Serialize and deserialize a merge_contacts input."""
        original = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="merge_contacts",
            primary_contact_id="c-primary",
            secondary_contact_id="c-secondary",
        )
        dumped = original.model_dump(mode="json")
        restored = ContactsInput.model_validate(dumped)
        assert restored.primary_contact_id == "c-primary"
        assert restored.secondary_contact_id == "c-secondary"

    def test_json_example_simple_create(self):
        """Parse a JSON example representing a create_contact."""
        from tests.fixtures.modalities.contacts import CONTACTS_JSON_EXAMPLES

        data = CONTACTS_JSON_EXAMPLES["simple_create"]
        ci = ContactsInput.model_validate(data)
        assert ci.operation == "create_contact"
        assert ci.first_name == "Alice"

    def test_json_example_update_with_additive(self):
        """Parse a JSON example representing an additive update."""
        from tests.fixtures.modalities.contacts import CONTACTS_JSON_EXAMPLES

        data = CONTACTS_JSON_EXAMPLES["update_with_additive"]
        ci = ContactsInput.model_validate(data)
        assert ci.operation == "update_contact"
        assert ci.contact_id == "contact-001"
        assert len(ci.add_identifiers) == 1

    def test_json_example_merge(self):
        """Parse a JSON example representing a merge operation."""
        from tests.fixtures.modalities.contacts import CONTACTS_JSON_EXAMPLES

        data = CONTACTS_JSON_EXAMPLES["merge"]
        ci = ContactsInput.model_validate(data)
        assert ci.operation == "merge_contacts"
        assert ci.primary_contact_id == "contact-001"


# ============================================================================
# Edge Cases
# ============================================================================


class TestContactsInputEdgeCases:
    """Edge case and boundary tests."""

    def test_create_with_multiple_identifier_types(self):
        """A contact can have phone, email, and custom identifiers."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+15551234567"
                ),
                ContactIdentifier(
                    identifier_type="email", value="alice@example.com"
                ),
                ContactIdentifier(
                    identifier_type="slack", value="@alice"
                ),
            ],
        )
        ci.validate_input()
        assert len(ci.identifiers) == 3

    def test_create_with_addresses(self):
        """A contact can include postal addresses."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+1555"
                )
            ],
            addresses=[
                PostalAddress(
                    street="123 Main St",
                    city="Portland",
                    state="OR",
                    label="home",
                ),
                PostalAddress(
                    street="456 Elm St",
                    city="Portland",
                    state="OR",
                    label="work",
                ),
            ],
        )
        ci.validate_input()
        assert len(ci.addresses) == 2

    def test_update_with_both_add_and_remove_identifiers(self):
        """An update can add and remove identifiers simultaneously."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="update_contact",
            contact_id="c1",
            add_identifiers=[
                ContactIdentifier(
                    identifier_type="email", value="new@example.com"
                )
            ],
            remove_identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+15550009999"
                )
            ],
        )
        ci.validate_input()

    def test_birthday_accepts_date_object(self):
        """birthday should accept a date object."""
        ci = ContactsInput(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            operation="create_contact",
            identifiers=[
                ContactIdentifier(
                    identifier_type="phone", value="+1555"
                )
            ],
            birthday=date(1985, 12, 25),
        )
        assert ci.birthday == date(1985, 12, 25)


# ============================================================================
# Fixture Sanity Checks
# ============================================================================


class TestContactsInputFromFixtures:
    """Verify that fixture pre-built inputs are valid and usable."""

    def test_simple_create_fixture(self):
        """SIMPLE_CREATE fixture should be a valid create_contact input."""
        from tests.fixtures.modalities.contacts import SIMPLE_CREATE

        assert SIMPLE_CREATE.operation == "create_contact"
        assert SIMPLE_CREATE.first_name == "Alice"
        SIMPLE_CREATE.validate_input()

    def test_simple_update_fixture(self):
        """SIMPLE_UPDATE fixture should be a valid update_contact input."""
        from tests.fixtures.modalities.contacts import SIMPLE_UPDATE

        assert SIMPLE_UPDATE.operation == "update_contact"
        assert SIMPLE_UPDATE.contact_id == "contact-001"
        SIMPLE_UPDATE.validate_input()

    def test_simple_delete_fixture(self):
        """SIMPLE_DELETE fixture should be a valid delete_contact input."""
        from tests.fixtures.modalities.contacts import SIMPLE_DELETE

        assert SIMPLE_DELETE.operation == "delete_contact"
        SIMPLE_DELETE.validate_input()

    def test_block_contact_fixture(self):
        """BLOCK_CONTACT fixture should be a valid block_contact input."""
        from tests.fixtures.modalities.contacts import BLOCK_CONTACT

        assert BLOCK_CONTACT.operation == "block_contact"
        BLOCK_CONTACT.validate_input()

    def test_add_to_group_fixture(self):
        """ADD_TO_GROUP fixture should be a valid add_to_group input."""
        from tests.fixtures.modalities.contacts import ADD_TO_GROUP

        assert ADD_TO_GROUP.operation == "add_to_group"
        assert ADD_TO_GROUP.group_name == "Family"
        ADD_TO_GROUP.validate_input()

    def test_merge_contacts_fixture(self):
        """MERGE_CONTACTS fixture should be a valid merge_contacts input."""
        from tests.fixtures.modalities.contacts import MERGE_CONTACTS

        assert MERGE_CONTACTS.operation == "merge_contacts"
        assert MERGE_CONTACTS.primary_contact_id == "contact-001"
        assert MERGE_CONTACTS.secondary_contact_id == "contact-002"
        MERGE_CONTACTS.validate_input()
