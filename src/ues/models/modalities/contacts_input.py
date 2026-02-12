"""Contacts input model and helper classes."""

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from ues.models.base_input import ModalityInput


# ---------------------------------------------------------------------------
# Operation type
# ---------------------------------------------------------------------------

ContactsOperation = Literal[
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

# Operations that require contact_id
_CONTACT_ID_OPERATIONS: set[str] = {
    "update_contact",
    "delete_contact",
    "block_contact",
    "unblock_contact",
    "favorite_contact",
    "unfavorite_contact",
    "add_to_group",
    "remove_from_group",
}


# ---------------------------------------------------------------------------
# Helper classes
# ---------------------------------------------------------------------------


class ContactIdentifier(BaseModel):
    """Represents a single identifier (phone number, email address, handle) for a contact.

    Args:
        identifier_type: Type of identifier (e.g., "phone", "email", "discord").
        value: The identifier string (phone number, email address, handle).
        label: Optional user-defined label (e.g., "home", "work", "mobile").
    """

    identifier_type: str = Field(description="Type of identifier")
    value: str = Field(description="The identifier string")
    label: Optional[str] = Field(
        default=None, description="User-defined label"
    )

    @field_validator("identifier_type")
    @classmethod
    def validate_identifier_type(cls, v: str) -> str:
        """Ensure identifier_type is a non-empty string.

        Args:
            v: The identifier_type value to validate.

        Returns:
            The validated identifier_type.

        Raises:
            ValueError: If identifier_type is empty.
        """
        if not v or not v.strip():
            raise ValueError("identifier_type must be a non-empty string")
        return v

    @field_validator("value")
    @classmethod
    def validate_value(cls, v: str) -> str:
        """Ensure value is a non-empty string.

        Args:
            v: The value to validate.

        Returns:
            The validated value.

        Raises:
            ValueError: If value is empty.
        """
        if not v or not v.strip():
            raise ValueError("value must be a non-empty string")
        return v

    @model_validator(mode="after")
    def validate_email_format(self) -> "ContactIdentifier":
        """Validate that email identifiers contain an @ symbol.

        Returns:
            The validated ContactIdentifier.

        Raises:
            ValueError: If email identifier does not contain @.
        """
        if self.identifier_type == "email" and "@" not in self.value:
            raise ValueError(
                f"Email identifier must contain '@', got '{self.value}'"
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API responses.

        Returns:
            Dictionary representation of this identifier.
        """
        result: dict[str, Any] = {
            "identifier_type": self.identifier_type,
            "value": self.value,
        }
        if self.label is not None:
            result["label"] = self.label
        return result


class PostalAddress(BaseModel):
    """Represents a physical mailing address for a contact.

    Args:
        street: Street address (e.g., "123 Main St").
        city: City name.
        state: State, province, or region.
        postal_code: ZIP code or postal code.
        country: Country name or ISO code.
        label: User-defined label (e.g., "home", "work").
    """

    street: Optional[str] = Field(default=None, description="Street address")
    city: Optional[str] = Field(default=None, description="City name")
    state: Optional[str] = Field(
        default=None, description="State, province, or region"
    )
    postal_code: Optional[str] = Field(
        default=None, description="ZIP code or postal code"
    )
    country: Optional[str] = Field(
        default=None, description="Country name or ISO code"
    )
    label: Optional[str] = Field(
        default=None, description="User-defined label"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API responses.

        Returns:
            Dictionary representation of this address.
        """
        result: dict[str, Any] = {}
        if self.street is not None:
            result["street"] = self.street
        if self.city is not None:
            result["city"] = self.city
        if self.state is not None:
            result["state"] = self.state
        if self.postal_code is not None:
            result["postal_code"] = self.postal_code
        if self.country is not None:
            result["country"] = self.country
        if self.label is not None:
            result["label"] = self.label
        return result

    def format_oneline(self) -> str:
        """Return a formatted single-line address string.

        Returns:
            Formatted address string with non-None components joined by ", ".
        """
        parts: list[str] = []
        if self.street:
            parts.append(self.street)
        if self.city:
            parts.append(self.city)
        if self.state and self.postal_code:
            parts.append(f"{self.state} {self.postal_code}")
        elif self.state:
            parts.append(self.state)
        elif self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# ContactsInput
# ---------------------------------------------------------------------------


class ContactsInput(ModalityInput):
    """Input for contact-related operations.

    Represents different types of contact events (create, update, delete, block,
    etc.) that modify the contacts state. Uses an operation-based design where
    different attributes are required depending on the operation type. All data
    fields are flat, explicitly-typed Optional fields.

    Args:
        modality_type: Always "contacts" for this input type.
        timestamp: When operation occurred (simulator time).
        input_id: Unique input identifier (auto-generated).
        operation: Type of contact operation to perform.
        contact_id: Target contact ID (required for most operations).
        first_name: First/given name.
        last_name: Last/family name.
        display_name: User-overridden display name (e.g., "Mom").
        nickname: Informal name.
        identifiers: Identifiers for create (required, >=1) or full-replace
            for update.
        add_identifiers: Identifiers to add (update only, additive).
        remove_identifiers: Identifiers to remove (update only, subtractive).
        company: Organization/company name.
        job_title: Job title or role.
        addresses: Physical addresses (full replace on create/update).
        add_addresses: Addresses to add (update only).
        remove_addresses: Addresses to remove (update only).
        birthday: Date of birth.
        notes: Free-text notes.
        photo_url: Profile photo URL.
        is_favorite: Whether this contact is a favorite.
        is_blocked: Whether this contact is blocked.
        groups: Group set (full replace on create).
        add_groups: Groups to add (update only).
        remove_groups: Groups to remove (update only).
        group_name: Group name for add_to_group / remove_from_group.
        primary_contact_id: Contact to keep during merge.
        secondary_contact_id: Contact to merge into primary (deleted after).
    """

    modality_type: str = Field(default="contacts", frozen=True)
    operation: ContactsOperation = Field(
        description="Type of contact operation"
    )

    # Contact identity fields
    contact_id: Optional[str] = Field(
        default=None, description="Target contact ID"
    )

    # Contact data fields
    first_name: Optional[str] = Field(
        default=None, description="First/given name"
    )
    last_name: Optional[str] = Field(
        default=None, description="Last/family name"
    )
    display_name: Optional[str] = Field(
        default=None, description="User-overridden display name"
    )
    nickname: Optional[str] = Field(
        default=None, description="Informal name"
    )
    identifiers: Optional[list[ContactIdentifier]] = Field(
        default=None,
        description="Identifiers for create or full-replace for update",
    )
    add_identifiers: Optional[list[ContactIdentifier]] = Field(
        default=None, description="Identifiers to add (update only)"
    )
    remove_identifiers: Optional[list[ContactIdentifier]] = Field(
        default=None, description="Identifiers to remove (update only)"
    )
    company: Optional[str] = Field(
        default=None, description="Organization/company name"
    )
    job_title: Optional[str] = Field(
        default=None, description="Job title or role"
    )
    addresses: Optional[list[PostalAddress]] = Field(
        default=None, description="Physical addresses (full replace)"
    )
    add_addresses: Optional[list[PostalAddress]] = Field(
        default=None, description="Addresses to add (update only)"
    )
    remove_addresses: Optional[list[PostalAddress]] = Field(
        default=None, description="Addresses to remove (update only)"
    )
    birthday: Optional[date] = Field(
        default=None, description="Date of birth"
    )
    notes: Optional[str] = Field(
        default=None, description="Free-text notes"
    )
    photo_url: Optional[str] = Field(
        default=None, description="Profile photo URL"
    )
    is_favorite: Optional[bool] = Field(
        default=None, description="Whether this contact is a favorite"
    )
    is_blocked: Optional[bool] = Field(
        default=None, description="Whether this contact is blocked"
    )
    groups: Optional[set[str]] = Field(
        default=None, description="Group set (full replace on create)"
    )
    add_groups: Optional[set[str]] = Field(
        default=None, description="Groups to add (update only)"
    )
    remove_groups: Optional[set[str]] = Field(
        default=None, description="Groups to remove (update only)"
    )

    # Group operation fields
    group_name: Optional[str] = Field(
        default=None, description="Group name for add/remove group ops"
    )

    # Merge operation fields
    primary_contact_id: Optional[str] = Field(
        default=None, description="Contact to keep during merge"
    )
    secondary_contact_id: Optional[str] = Field(
        default=None, description="Contact to merge into primary"
    )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_create_contact(self) -> None:
        """Validate fields required for create_contact.

        Raises:
            ValueError: If identifiers are missing or empty.
        """
        if not self.identifiers:
            raise ValueError(
                "Operation 'create_contact' requires at least one identifier"
            )
        if len(self.identifiers) == 0:
            raise ValueError(
                "Operation 'create_contact' requires at least one identifier"
            )

    def _validate_contact_id_required(self) -> None:
        """Validate that contact_id is present.

        Raises:
            ValueError: If contact_id is missing.
        """
        if not self.contact_id:
            raise ValueError(
                f"Operation '{self.operation}' requires contact_id"
            )

    def _validate_add_to_group(self) -> None:
        """Validate fields required for add_to_group.

        Raises:
            ValueError: If contact_id or group_name is missing.
        """
        self._validate_contact_id_required()
        if not self.group_name:
            raise ValueError(
                "Operation 'add_to_group' requires group_name"
            )

    def _validate_remove_from_group(self) -> None:
        """Validate fields required for remove_from_group.

        Raises:
            ValueError: If contact_id or group_name is missing.
        """
        self._validate_contact_id_required()
        if not self.group_name:
            raise ValueError(
                "Operation 'remove_from_group' requires group_name"
            )

    def _validate_merge_contacts(self) -> None:
        """Validate fields required for merge_contacts.

        Raises:
            ValueError: If primary or secondary contact IDs are missing,
                or if they are the same.
        """
        if not self.primary_contact_id:
            raise ValueError(
                "Operation 'merge_contacts' requires primary_contact_id"
            )
        if not self.secondary_contact_id:
            raise ValueError(
                "Operation 'merge_contacts' requires secondary_contact_id"
            )
        if self.primary_contact_id == self.secondary_contact_id:
            raise ValueError(
                "primary_contact_id and secondary_contact_id must be different"
            )

    # ------------------------------------------------------------------
    # Abstract method implementations
    # ------------------------------------------------------------------

    def validate_input(self) -> None:
        """Perform operation-specific validation beyond Pydantic field validation.

        Validates that required fields are present for each operation type.

        Raises:
            ValueError: If validation fails with descriptive message.
        """
        if self.operation == "create_contact":
            self._validate_create_contact()
        elif self.operation in _CONTACT_ID_OPERATIONS:
            if self.operation == "add_to_group":
                self._validate_add_to_group()
            elif self.operation == "remove_from_group":
                self._validate_remove_from_group()
            else:
                self._validate_contact_id_required()
        elif self.operation == "merge_contacts":
            self._validate_merge_contacts()

    def get_affected_entities(self) -> list[str]:
        """Return list of entity IDs affected by this input.

        Returns:
            List of contact IDs affected. For merge, returns both IDs.
        """
        if self.operation == "merge_contacts":
            entities: list[str] = []
            if self.primary_contact_id:
                entities.append(self.primary_contact_id)
            if self.secondary_contact_id:
                entities.append(self.secondary_contact_id)
            return entities

        if self.contact_id:
            return [self.contact_id]

        # create_contact — no ID yet
        return []

    def get_summary(self) -> str:
        """Return human-readable one-line summary of this input.

        Returns:
            Brief description of the operation for logging/UI display.
        """
        op = self.operation

        if op == "create_contact":
            name_parts: list[str] = []
            if self.first_name:
                name_parts.append(self.first_name)
            if self.last_name:
                name_parts.append(self.last_name)
            name = " ".join(name_parts) if name_parts else None
            identifier_str = ""
            if self.identifiers:
                identifier_str = f" ({self.identifiers[0].value})"
            if name:
                return f"Create contact: {name}{identifier_str}"
            return f"Create contact{identifier_str}"

        if op == "update_contact":
            return f"Update contact {self.contact_id}"

        if op == "delete_contact":
            return f"Delete contact {self.contact_id}"

        if op == "block_contact":
            return f"Block contact {self.contact_id}"

        if op == "unblock_contact":
            return f"Unblock contact {self.contact_id}"

        if op == "favorite_contact":
            return f"Favorite contact {self.contact_id}"

        if op == "unfavorite_contact":
            return f"Unfavorite contact {self.contact_id}"

        if op == "add_to_group":
            return (
                f"Add contact {self.contact_id} to group "
                f"'{self.group_name}'"
            )

        if op == "remove_from_group":
            return (
                f"Remove contact {self.contact_id} from group "
                f"'{self.group_name}'"
            )

        if op == "merge_contacts":
            return (
                f"Merge contact {self.secondary_contact_id} into "
                f"{self.primary_contact_id}"
            )

        return f"Contacts operation: {op}"

    def should_merge_with(self, other: ModalityInput) -> bool:
        """Determine if this input should be merged with another input.

        Contact operations are discrete and should not be merged.

        Args:
            other: Another input to compare against.

        Returns:
            Always False for contact operations.
        """
        return False
