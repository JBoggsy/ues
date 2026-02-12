"""Contacts state model and helper classes."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ues.models.base_input import ModalityInput
from ues.models.base_state import ModalityState
from ues.models.modalities.contacts_input import (
    ContactIdentifier,
    ContactsInput,
    PostalAddress,
)

if TYPE_CHECKING:
    from ues.models.environment import Environment


# ---------------------------------------------------------------------------
# Timezone helper
# ---------------------------------------------------------------------------


def _ensure_timezone_aware(v: datetime) -> datetime:
    """Ensure a datetime is timezone-aware, converting naive to UTC.

    Args:
        v: The datetime to check.

    Returns:
        A timezone-aware datetime.
    """
    if isinstance(v, str):
        v = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if isinstance(v, datetime) and v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v


# ---------------------------------------------------------------------------
# Contact sub-model
# ---------------------------------------------------------------------------


class Contact(BaseModel):
    """Represents a single contact entry in the address book.

    Args:
        contact_id: Unique identifier (auto-generated UUID).
        first_name: First/given name.
        last_name: Last/family name.
        display_name: User-overridden display name (e.g., "Mom", "Dr. Smith").
        nickname: Informal name.
        identifiers: All phone numbers, emails, and handles.
        company: Organization/company name.
        job_title: Job title or role.
        addresses: Physical addresses.
        birthday: Date of birth (date only).
        notes: Free-text notes.
        photo_url: Profile photo URL.
        is_favorite: Whether this contact is a favorite.
        is_blocked: Whether this contact is blocked.
        groups: Group names this contact belongs to.
        created_at: When contact was created (simulator time).
        updated_at: When contact was last modified (simulator time).
    """

    contact_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier",
    )
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
    identifiers: list[ContactIdentifier] = Field(
        default_factory=list, description="All identifiers"
    )
    company: Optional[str] = Field(
        default=None, description="Organization/company name"
    )
    job_title: Optional[str] = Field(
        default=None, description="Job title or role"
    )
    addresses: list[PostalAddress] = Field(
        default_factory=list, description="Physical addresses"
    )
    birthday: Optional[Any] = Field(
        default=None, description="Date of birth"
    )
    notes: Optional[str] = Field(
        default=None, description="Free-text notes"
    )
    photo_url: Optional[str] = Field(
        default=None, description="Profile photo URL"
    )
    is_favorite: bool = Field(
        default=False, description="Whether this contact is a favorite"
    )
    is_blocked: bool = Field(
        default=False, description="Whether this contact is blocked"
    )
    groups: set[str] = Field(
        default_factory=set, description="Group names"
    )
    created_at: datetime = Field(description="When contact was created")
    updated_at: datetime = Field(description="When contact was last modified")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime | str) -> datetime:
        """Ensure datetime fields are timezone-aware.

        Args:
            v: The datetime value to validate.

        Returns:
            A timezone-aware datetime.
        """
        return _ensure_timezone_aware(v)

    # ------------------------------------------------------------------
    # Methods
    # ------------------------------------------------------------------

    def get_resolved_display_name(self) -> str:
        """Return the best available display name for this contact.

        Resolution order:
        1. display_name (if explicitly set)
        2. "First Last" (if first_name or last_name set)
        3. nickname
        4. First identifier value
        5. "Unknown"

        Returns:
            The resolved display name string.
        """
        if self.display_name:
            return self.display_name

        name_parts: list[str] = []
        if self.first_name:
            name_parts.append(self.first_name)
        if self.last_name:
            name_parts.append(self.last_name)
        if name_parts:
            return " ".join(name_parts)

        if self.nickname:
            return self.nickname

        if self.identifiers:
            return self.identifiers[0].value

        return "Unknown"

    def get_phone_numbers(self) -> list[str]:
        """Return all phone-type identifier values.

        Returns:
            List of phone number strings.
        """
        return [
            ident.value
            for ident in self.identifiers
            if ident.identifier_type == "phone"
        ]

    def get_email_addresses(self) -> list[str]:
        """Return all email-type identifier values.

        Returns:
            List of email address strings.
        """
        return [
            ident.value
            for ident in self.identifiers
            if ident.identifier_type == "email"
        ]

    def has_identifier(self, identifier_type: str, value: str) -> bool:
        """Check if this contact has a specific identifier.

        Args:
            identifier_type: Type of identifier to check.
            value: Value of identifier to check.

        Returns:
            True if the contact has this identifier.
        """
        return any(
            ident.identifier_type == identifier_type and ident.value == value
            for ident in self.identifiers
        )

    def add_identifier(self, identifier: ContactIdentifier) -> None:
        """Add an identifier, rejecting duplicates.

        Args:
            identifier: The identifier to add.

        Raises:
            ValueError: If this contact already has this identifier.
        """
        if self.has_identifier(identifier.identifier_type, identifier.value):
            raise ValueError(
                f"Contact already has identifier "
                f"{identifier.identifier_type}:{identifier.value}"
            )
        self.identifiers.append(identifier)

    def remove_identifier(
        self, identifier_type: str, value: str
    ) -> bool:
        """Remove an identifier by type and value.

        Args:
            identifier_type: Type of identifier to remove.
            value: Value of identifier to remove.

        Returns:
            True if the identifier was found and removed, False otherwise.
        """
        for i, ident in enumerate(self.identifiers):
            if (
                ident.identifier_type == identifier_type
                and ident.value == value
            ):
                self.identifiers.pop(i)
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for API responses.

        Returns:
            Dictionary representation of this contact.
        """
        result: dict[str, Any] = {
            "contact_id": self.contact_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "resolved_display_name": self.get_resolved_display_name(),
            "nickname": self.nickname,
            "identifiers": [ident.to_dict() for ident in self.identifiers],
            "company": self.company,
            "job_title": self.job_title,
            "addresses": [addr.to_dict() for addr in self.addresses],
            "birthday": (
                self.birthday.isoformat() if self.birthday else None
            ),
            "notes": self.notes,
            "photo_url": self.photo_url,
            "is_favorite": self.is_favorite,
            "is_blocked": self.is_blocked,
            "groups": sorted(self.groups),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        return result


# ---------------------------------------------------------------------------
# ContactsState
# ---------------------------------------------------------------------------


class ContactsState(ModalityState):
    """Tracks all contacts, groups, and provides cross-modality lookup services.

    The Contacts modality is a service modality — it primarily provides data
    to other modalities (SMS, Email, Calendar) rather than generating
    user-facing events on its own.

    Args:
        modality_type: Always "contacts".
        last_updated: When state was last modified.
        update_count: Number of inputs applied.
        contacts: All contacts keyed by contact_id.
    """

    modality_type: str = Field(default="contacts", frozen=True)
    contacts: dict[str, Contact] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ==================================================================
    # apply_input
    # ==================================================================

    def apply_input(
        self,
        input_data: "ModalityInput",
        environment: Optional["Environment"] = None,
    ) -> None:
        """Apply a ContactsInput to modify state.

        Args:
            input_data: The ContactsInput to apply.
            environment: The simulation environment (optional).

        Raises:
            ValueError: If input_data is not a ContactsInput or is invalid.
        """
        if not isinstance(input_data, ContactsInput):
            raise ValueError(
                f"Expected ContactsInput, got {type(input_data).__name__}"
            )
        input_data.validate_input()

        operation_handlers: dict[str, Any] = {
            "create_contact": self._apply_create_contact,
            "update_contact": self._apply_update_contact,
            "delete_contact": self._apply_delete_contact,
            "block_contact": self._apply_block_contact,
            "unblock_contact": self._apply_unblock_contact,
            "favorite_contact": self._apply_favorite_contact,
            "unfavorite_contact": self._apply_unfavorite_contact,
            "add_to_group": self._apply_add_to_group,
            "remove_from_group": self._apply_remove_from_group,
            "merge_contacts": self._apply_merge_contacts,
        }

        handler = operation_handlers.get(input_data.operation)
        if not handler:
            raise ValueError(
                f"Unknown contacts operation: '{input_data.operation}'"
            )

        handler(input_data)
        self.last_updated = input_data.timestamp
        self.update_count += 1

    # ------------------------------------------------------------------
    # Operation handlers
    # ------------------------------------------------------------------

    def _check_identifier_uniqueness(
        self,
        identifiers: list[ContactIdentifier],
        exclude_contact_id: Optional[str] = None,
    ) -> None:
        """Check that none of the identifiers already belong to another contact.

        Args:
            identifiers: Identifiers to check.
            exclude_contact_id: Contact ID to skip (for updates on self).

        Raises:
            ValueError: If a duplicate identifier is found.
        """
        for ident in identifiers:
            for cid, contact in self.contacts.items():
                if cid == exclude_contact_id:
                    continue
                if contact.has_identifier(
                    ident.identifier_type, ident.value
                ):
                    raise ValueError(
                        f"Identifier {ident.identifier_type}:"
                        f"{ident.value} already belongs to contact "
                        f"{cid} ({contact.get_resolved_display_name()})"
                    )

    def _apply_create_contact(self, input_data: ContactsInput) -> None:
        """Handle create_contact operation.

        Args:
            input_data: The input with contact data.

        Raises:
            ValueError: If identifiers are duplicated across contacts.
        """
        identifiers = input_data.identifiers or []
        self._check_identifier_uniqueness(identifiers)

        # Use pre-assigned ID from create_undo_data if available
        contact_id = input_data.contact_id or str(uuid4())
        contact = Contact(
            contact_id=contact_id,
            first_name=input_data.first_name,
            last_name=input_data.last_name,
            display_name=input_data.display_name,
            nickname=input_data.nickname,
            identifiers=list(identifiers),
            company=input_data.company,
            job_title=input_data.job_title,
            addresses=list(input_data.addresses or []),
            birthday=input_data.birthday,
            notes=input_data.notes,
            photo_url=input_data.photo_url,
            is_favorite=input_data.is_favorite or False,
            is_blocked=input_data.is_blocked or False,
            groups=set(input_data.groups) if input_data.groups else set(),
            created_at=input_data.timestamp,
            updated_at=input_data.timestamp,
        )

        self.contacts[contact_id] = contact

        # Store the generated ID back on the input for undo/event tracking
        input_data.contact_id = contact_id

    def _apply_update_contact(self, input_data: ContactsInput) -> None:
        """Handle update_contact operation.

        Args:
            input_data: The input with update data.

        Raises:
            ValueError: If contact_id not found or identifier conflicts.
        """
        contact_id = input_data.contact_id
        if contact_id not in self.contacts:
            raise ValueError(f"Contact not found: {contact_id}")

        contact = self.contacts[contact_id]

        # Scalar fields — update if provided
        if input_data.first_name is not None:
            contact.first_name = input_data.first_name
        if input_data.last_name is not None:
            contact.last_name = input_data.last_name
        if input_data.display_name is not None:
            contact.display_name = input_data.display_name
        if input_data.nickname is not None:
            contact.nickname = input_data.nickname
        if input_data.company is not None:
            contact.company = input_data.company
        if input_data.job_title is not None:
            contact.job_title = input_data.job_title
        if input_data.birthday is not None:
            contact.birthday = input_data.birthday
        if input_data.notes is not None:
            contact.notes = input_data.notes
        if input_data.photo_url is not None:
            contact.photo_url = input_data.photo_url
        if input_data.is_favorite is not None:
            contact.is_favorite = input_data.is_favorite
        if input_data.is_blocked is not None:
            contact.is_blocked = input_data.is_blocked

        # Identifiers — full replace or additive/subtractive
        if input_data.identifiers is not None:
            self._check_identifier_uniqueness(
                input_data.identifiers, exclude_contact_id=contact_id
            )
            contact.identifiers = list(input_data.identifiers)

        if input_data.add_identifiers:
            self._check_identifier_uniqueness(
                input_data.add_identifiers, exclude_contact_id=contact_id
            )
            for ident in input_data.add_identifiers:
                if not contact.has_identifier(
                    ident.identifier_type, ident.value
                ):
                    contact.identifiers.append(ident)

        if input_data.remove_identifiers:
            for ident in input_data.remove_identifiers:
                contact.remove_identifier(
                    ident.identifier_type, ident.value
                )

        # Addresses — full replace or additive/subtractive
        if input_data.addresses is not None:
            contact.addresses = list(input_data.addresses)

        if input_data.add_addresses:
            contact.addresses.extend(input_data.add_addresses)

        if input_data.remove_addresses:
            for addr_to_remove in input_data.remove_addresses:
                addr_dict = addr_to_remove.model_dump()
                contact.addresses = [
                    a
                    for a in contact.addresses
                    if a.model_dump() != addr_dict
                ]

        # Groups — full replace or additive/subtractive
        if input_data.groups is not None:
            contact.groups = set(input_data.groups)

        if input_data.add_groups:
            contact.groups |= input_data.add_groups

        if input_data.remove_groups:
            contact.groups -= input_data.remove_groups

        contact.updated_at = input_data.timestamp

    def _apply_delete_contact(self, input_data: ContactsInput) -> None:
        """Handle delete_contact operation.

        Args:
            input_data: The input with contact_id.

        Raises:
            ValueError: If contact_id not found.
        """
        contact_id = input_data.contact_id
        if contact_id not in self.contacts:
            raise ValueError(f"Contact not found: {contact_id}")
        del self.contacts[contact_id]

    def _apply_block_contact(self, input_data: ContactsInput) -> None:
        """Handle block_contact operation.

        Args:
            input_data: The input with contact_id.

        Raises:
            ValueError: If contact_id not found.
        """
        contact_id = input_data.contact_id
        if contact_id not in self.contacts:
            raise ValueError(f"Contact not found: {contact_id}")
        self.contacts[contact_id].is_blocked = True
        self.contacts[contact_id].updated_at = input_data.timestamp

    def _apply_unblock_contact(self, input_data: ContactsInput) -> None:
        """Handle unblock_contact operation.

        Args:
            input_data: The input with contact_id.

        Raises:
            ValueError: If contact_id not found.
        """
        contact_id = input_data.contact_id
        if contact_id not in self.contacts:
            raise ValueError(f"Contact not found: {contact_id}")
        self.contacts[contact_id].is_blocked = False
        self.contacts[contact_id].updated_at = input_data.timestamp

    def _apply_favorite_contact(self, input_data: ContactsInput) -> None:
        """Handle favorite_contact operation.

        Args:
            input_data: The input with contact_id.

        Raises:
            ValueError: If contact_id not found.
        """
        contact_id = input_data.contact_id
        if contact_id not in self.contacts:
            raise ValueError(f"Contact not found: {contact_id}")
        self.contacts[contact_id].is_favorite = True
        self.contacts[contact_id].updated_at = input_data.timestamp

    def _apply_unfavorite_contact(self, input_data: ContactsInput) -> None:
        """Handle unfavorite_contact operation.

        Args:
            input_data: The input with contact_id.

        Raises:
            ValueError: If contact_id not found.
        """
        contact_id = input_data.contact_id
        if contact_id not in self.contacts:
            raise ValueError(f"Contact not found: {contact_id}")
        self.contacts[contact_id].is_favorite = False
        self.contacts[contact_id].updated_at = input_data.timestamp

    def _apply_add_to_group(self, input_data: ContactsInput) -> None:
        """Handle add_to_group operation.

        Args:
            input_data: The input with contact_id and group_name.

        Raises:
            ValueError: If contact_id not found.
        """
        contact_id = input_data.contact_id
        if contact_id not in self.contacts:
            raise ValueError(f"Contact not found: {contact_id}")
        self.contacts[contact_id].groups.add(input_data.group_name)
        self.contacts[contact_id].updated_at = input_data.timestamp

    def _apply_remove_from_group(self, input_data: ContactsInput) -> None:
        """Handle remove_from_group operation.

        Args:
            input_data: The input with contact_id and group_name.

        Raises:
            ValueError: If contact_id not found.
        """
        contact_id = input_data.contact_id
        if contact_id not in self.contacts:
            raise ValueError(f"Contact not found: {contact_id}")
        self.contacts[contact_id].groups.discard(input_data.group_name)
        self.contacts[contact_id].updated_at = input_data.timestamp

    def _apply_merge_contacts(self, input_data: ContactsInput) -> None:
        """Handle merge_contacts operation.

        Merges secondary contact into primary:
        - Primary keeps its scalar fields where both have values
        - Secondary's unique identifiers, addresses, groups are added
        - Secondary is deleted

        Args:
            input_data: The input with primary and secondary contact IDs.

        Raises:
            ValueError: If either contact ID not found.
        """
        primary_id = input_data.primary_contact_id
        secondary_id = input_data.secondary_contact_id

        if primary_id not in self.contacts:
            raise ValueError(f"Primary contact not found: {primary_id}")
        if secondary_id not in self.contacts:
            raise ValueError(f"Secondary contact not found: {secondary_id}")

        primary = self.contacts[primary_id]
        secondary = self.contacts[secondary_id]

        # Fill in primary's gaps with secondary's data
        if not primary.first_name and secondary.first_name:
            primary.first_name = secondary.first_name
        if not primary.last_name and secondary.last_name:
            primary.last_name = secondary.last_name
        if not primary.display_name and secondary.display_name:
            primary.display_name = secondary.display_name
        if not primary.nickname and secondary.nickname:
            primary.nickname = secondary.nickname
        if not primary.company and secondary.company:
            primary.company = secondary.company
        if not primary.job_title and secondary.job_title:
            primary.job_title = secondary.job_title
        if not primary.birthday and secondary.birthday:
            primary.birthday = secondary.birthday
        if not primary.notes and secondary.notes:
            primary.notes = secondary.notes
        if not primary.photo_url and secondary.photo_url:
            primary.photo_url = secondary.photo_url

        # Merge identifiers (add unique ones from secondary)
        for ident in secondary.identifiers:
            if not primary.has_identifier(
                ident.identifier_type, ident.value
            ):
                primary.identifiers.append(ident)

        # Merge addresses (add all from secondary, simple append)
        existing_addr_dicts = [
            a.model_dump() for a in primary.addresses
        ]
        for addr in secondary.addresses:
            if addr.model_dump() not in existing_addr_dicts:
                primary.addresses.append(addr)

        # Merge groups (union)
        primary.groups |= secondary.groups

        # Inherit blocked/favorite from secondary if not already set
        if secondary.is_blocked:
            primary.is_blocked = True
        if secondary.is_favorite:
            primary.is_favorite = True

        primary.updated_at = input_data.timestamp

        # Delete secondary
        del self.contacts[secondary_id]

    # ==================================================================
    # get_snapshot
    # ==================================================================

    def get_snapshot(self) -> dict[str, Any]:
        """Return a complete snapshot of current state for API responses.

        Returns:
            Dictionary with all contacts, groups, and summary counts.
        """
        all_groups = self.get_all_groups()
        favorites_count = sum(
            1 for c in self.contacts.values() if c.is_favorite
        )
        blocked_count = sum(
            1 for c in self.contacts.values() if c.is_blocked
        )

        return {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "total_contacts": len(self.contacts),
            "favorites_count": favorites_count,
            "blocked_count": blocked_count,
            "groups": sorted(all_groups),
            "contacts": {
                cid: contact.to_dict()
                for cid, contact in self.contacts.items()
            },
        }

    # ==================================================================
    # summary property
    # ==================================================================

    @property
    def summary(self) -> str:
        """Brief string summary of contacts state.

        Returns:
            Human-readable summary (e.g., "12 contacts, 3 favorites, 1 blocked").
        """
        total = len(self.contacts)
        if total == 0:
            return "No contacts"

        favorites = sum(
            1 for c in self.contacts.values() if c.is_favorite
        )
        blocked = sum(
            1 for c in self.contacts.values() if c.is_blocked
        )

        parts = [f"{total} contact{'s' if total != 1 else ''}"]
        if favorites:
            parts.append(f"{favorites} favorite{'s' if favorites != 1 else ''}")
        if blocked:
            parts.append(f"{blocked} blocked")
        return ", ".join(parts)

    # ==================================================================
    # get_compact_snapshot
    # ==================================================================

    def get_compact_snapshot(
        self, current_time: datetime
    ) -> dict[str, Any]:
        """Return an LLM-context-optimized view of contacts state.

        Args:
            current_time: Current simulator time for relative timestamps.

        Returns:
            Compact dictionary with counts, groups, and recent contacts.
        """
        all_groups = self.get_all_groups()
        group_counts: dict[str, int] = {}
        for group_name in all_groups:
            group_counts[group_name] = len(
                self.find_contacts_by_group(group_name)
            )

        # Recent contacts — 5 most recently updated
        sorted_contacts = sorted(
            self.contacts.values(),
            key=lambda c: c.updated_at,
            reverse=True,
        )
        recent = [
            {
                "name": c.get_resolved_display_name(),
                "updated_ago": self._format_relative_time(
                    c.updated_at, current_time
                ),
            }
            for c in sorted_contacts[:5]
        ]

        return {
            "modality_type": self.modality_type,
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count,
            "summary": self.summary,
            "total_contacts": len(self.contacts),
            "favorites_count": sum(
                1 for c in self.contacts.values() if c.is_favorite
            ),
            "blocked_count": sum(
                1 for c in self.contacts.values() if c.is_blocked
            ),
            "groups": group_counts,
            "recent_contacts": recent,
        }

    # ==================================================================
    # validate_state
    # ==================================================================

    def validate_state(self) -> list[str]:
        """Validate internal state consistency.

        Checks:
        - No duplicate identifiers across contacts.
        - All contacts have at least one identifier.

        Returns:
            List of validation error messages (empty if valid).
        """
        issues: list[str] = []

        # Check duplicate identifiers across contacts
        seen_identifiers: dict[tuple[str, str], str] = {}
        for cid, contact in self.contacts.items():
            if not contact.identifiers:
                issues.append(
                    f"Contact {cid} "
                    f"({contact.get_resolved_display_name()}) "
                    f"has no identifiers"
                )
            for ident in contact.identifiers:
                key = (ident.identifier_type, ident.value)
                if key in seen_identifiers:
                    issues.append(
                        f"Duplicate identifier {ident.identifier_type}:"
                        f"{ident.value} found in contacts "
                        f"{seen_identifiers[key]} and {cid}"
                    )
                else:
                    seen_identifiers[key] = cid

        return issues

    # ==================================================================
    # query
    # ==================================================================

    def query(self, query_params: dict[str, Any]) -> dict[str, Any]:
        """Search and filter contacts.

        Supported query parameters:
        - search_text: Substring match on name, nickname, company, notes.
        - group: Filter by group membership.
        - is_favorite: Filter by favorite status (bool).
        - is_blocked: Filter by blocked status (bool).
        - has_phone: Contacts with at least one phone identifier (bool).
        - has_email: Contacts with at least one email identifier (bool).
        - identifier_type + identifier_value: Exact identifier match.
        - limit: Max results to return.
        - offset: Skip this many results.

        Args:
            query_params: Dictionary of query parameters.

        Returns:
            Dictionary with contacts, count, and query_params.
        """
        results = list(self.contacts.values())

        # Filter: search_text
        search_text = query_params.get("search_text")
        if search_text:
            text_lower = search_text.lower()
            results = [
                c
                for c in results
                if self._matches_search_text(c, text_lower)
            ]

        # Filter: group
        group = query_params.get("group")
        if group:
            results = [c for c in results if group in c.groups]

        # Filter: is_favorite
        is_favorite = query_params.get("is_favorite")
        if is_favorite is not None:
            results = [
                c for c in results if c.is_favorite == is_favorite
            ]

        # Filter: is_blocked
        is_blocked = query_params.get("is_blocked")
        if is_blocked is not None:
            results = [
                c for c in results if c.is_blocked == is_blocked
            ]

        # Filter: has_phone
        has_phone = query_params.get("has_phone")
        if has_phone is not None:
            if has_phone:
                results = [
                    c for c in results if c.get_phone_numbers()
                ]
            else:
                results = [
                    c for c in results if not c.get_phone_numbers()
                ]

        # Filter: has_email
        has_email = query_params.get("has_email")
        if has_email is not None:
            if has_email:
                results = [
                    c for c in results if c.get_email_addresses()
                ]
            else:
                results = [
                    c for c in results if not c.get_email_addresses()
                ]

        # Filter: identifier_type + identifier_value (exact match)
        identifier_type = query_params.get("identifier_type")
        identifier_value = query_params.get("identifier_value")
        if identifier_type and identifier_value:
            results = [
                c
                for c in results
                if c.has_identifier(identifier_type, identifier_value)
            ]

        total_count = len(results)

        # Pagination
        offset = query_params.get("offset", 0)
        limit = query_params.get("limit")

        if offset:
            results = results[offset:]
        if limit is not None:
            results = results[:limit]

        return {
            "contacts": [c.to_dict() for c in results],
            "count": total_count,
            "returned_count": len(results),
            "query_params": query_params,
        }

    def _matches_search_text(self, contact: Contact, text: str) -> bool:
        """Check if a contact matches a search text.

        Searches across first_name, last_name, display_name, nickname,
        company, job_title, notes, and identifier values.

        Args:
            contact: The contact to check.
            text: Lowercased search text.

        Returns:
            True if any field contains the search text.
        """
        searchable_fields = [
            contact.first_name,
            contact.last_name,
            contact.display_name,
            contact.nickname,
            contact.company,
            contact.job_title,
            contact.notes,
        ]
        for field_val in searchable_fields:
            if field_val and text in field_val.lower():
                return True

        # Search identifier values
        for ident in contact.identifiers:
            if text in ident.value.lower():
                return True

        return False

    # ==================================================================
    # clear
    # ==================================================================

    def clear(self) -> None:
        """Reset to empty state (no contacts).

        Clears all contacts and resets counters.
        """
        self.contacts.clear()
        self.update_count = 0

    # ==================================================================
    # create_undo_data / apply_undo
    # ==================================================================

    def create_undo_data(
        self, input_data: "ModalityInput"
    ) -> dict[str, Any]:
        """Capture minimal data needed to undo applying the given input.

        Called BEFORE apply_input() to capture current state that will be lost.

        Args:
            input_data: The ContactsInput that will be applied.

        Returns:
            Dictionary containing undo information.
        """
        if not isinstance(input_data, ContactsInput):
            raise ValueError(
                f"Expected ContactsInput, got {type(input_data).__name__}"
            )

        base_undo: dict[str, Any] = {
            "state_previous_update_count": self.update_count,
            "state_previous_last_updated": self.last_updated.isoformat(),
        }

        op = input_data.operation

        if op == "create_contact":
            # After apply, input_data.contact_id will be set
            # We generate it here so undo knows what to delete
            contact_id = str(uuid4())
            input_data.contact_id = contact_id
            return {
                **base_undo,
                "action": "delete_contact",
                "contact_id": contact_id,
            }

        if op == "delete_contact":
            contact = self.contacts.get(input_data.contact_id)
            if contact:
                return {
                    **base_undo,
                    "action": "restore_contact",
                    "contact": contact.model_dump(mode="json"),
                }
            return {**base_undo, "action": "noop"}

        if op == "update_contact":
            contact = self.contacts.get(input_data.contact_id)
            if contact:
                return {
                    **base_undo,
                    "action": "restore_contact",
                    "contact": contact.model_dump(mode="json"),
                }
            return {**base_undo, "action": "noop"}

        if op == "block_contact":
            contact = self.contacts.get(input_data.contact_id)
            if contact:
                return {
                    **base_undo,
                    "action": "restore_blocked_state",
                    "contact_id": input_data.contact_id,
                    "was_blocked": contact.is_blocked,
                    "previous_updated_at": contact.updated_at.isoformat(),
                }
            return {**base_undo, "action": "noop"}

        if op == "unblock_contact":
            contact = self.contacts.get(input_data.contact_id)
            if contact:
                return {
                    **base_undo,
                    "action": "restore_blocked_state",
                    "contact_id": input_data.contact_id,
                    "was_blocked": contact.is_blocked,
                    "previous_updated_at": contact.updated_at.isoformat(),
                }
            return {**base_undo, "action": "noop"}

        if op == "favorite_contact":
            contact = self.contacts.get(input_data.contact_id)
            if contact:
                return {
                    **base_undo,
                    "action": "restore_favorite_state",
                    "contact_id": input_data.contact_id,
                    "was_favorite": contact.is_favorite,
                    "previous_updated_at": contact.updated_at.isoformat(),
                }
            return {**base_undo, "action": "noop"}

        if op == "unfavorite_contact":
            contact = self.contacts.get(input_data.contact_id)
            if contact:
                return {
                    **base_undo,
                    "action": "restore_favorite_state",
                    "contact_id": input_data.contact_id,
                    "was_favorite": contact.is_favorite,
                    "previous_updated_at": contact.updated_at.isoformat(),
                }
            return {**base_undo, "action": "noop"}

        if op == "add_to_group":
            contact = self.contacts.get(input_data.contact_id)
            if contact:
                was_member = input_data.group_name in contact.groups
                return {
                    **base_undo,
                    "action": "restore_group_membership",
                    "contact_id": input_data.contact_id,
                    "group_name": input_data.group_name,
                    "was_member": was_member,
                    "previous_updated_at": contact.updated_at.isoformat(),
                }
            return {**base_undo, "action": "noop"}

        if op == "remove_from_group":
            contact = self.contacts.get(input_data.contact_id)
            if contact:
                was_member = input_data.group_name in contact.groups
                return {
                    **base_undo,
                    "action": "restore_group_membership",
                    "contact_id": input_data.contact_id,
                    "group_name": input_data.group_name,
                    "was_member": was_member,
                    "previous_updated_at": contact.updated_at.isoformat(),
                }
            return {**base_undo, "action": "noop"}

        if op == "merge_contacts":
            primary = self.contacts.get(input_data.primary_contact_id)
            secondary = self.contacts.get(input_data.secondary_contact_id)
            undo: dict[str, Any] = {
                **base_undo,
                "action": "unmerge_contacts",
            }
            if primary:
                undo["primary_before"] = primary.model_dump(mode="json")
            if secondary:
                undo["secondary"] = secondary.model_dump(mode="json")
            return undo

        return {**base_undo, "action": "noop"}

    def apply_undo(self, undo_data: dict[str, Any]) -> None:
        """Reverse a previous input application.

        Args:
            undo_data: The undo data captured by create_undo_data().
        """
        undo_type = undo_data.get("action", "noop")

        if undo_type == "delete_contact":
            contact_id = undo_data["contact_id"]
            if contact_id in self.contacts:
                del self.contacts[contact_id]

        elif undo_type == "restore_contact":
            contact_data = undo_data["contact"]
            contact = Contact(**contact_data)
            self.contacts[contact.contact_id] = contact

        elif undo_type == "restore_blocked_state":
            contact_id = undo_data["contact_id"]
            if contact_id in self.contacts:
                self.contacts[contact_id].is_blocked = undo_data[
                    "was_blocked"
                ]
                self.contacts[contact_id].updated_at = (
                    datetime.fromisoformat(
                        undo_data["previous_updated_at"]
                    )
                )

        elif undo_type == "restore_favorite_state":
            contact_id = undo_data["contact_id"]
            if contact_id in self.contacts:
                self.contacts[contact_id].is_favorite = undo_data[
                    "was_favorite"
                ]
                self.contacts[contact_id].updated_at = (
                    datetime.fromisoformat(
                        undo_data["previous_updated_at"]
                    )
                )

        elif undo_type == "restore_group_membership":
            contact_id = undo_data["contact_id"]
            group_name = undo_data["group_name"]
            if contact_id in self.contacts:
                if undo_data["was_member"]:
                    self.contacts[contact_id].groups.add(group_name)
                else:
                    self.contacts[contact_id].groups.discard(group_name)
                self.contacts[contact_id].updated_at = (
                    datetime.fromisoformat(
                        undo_data["previous_updated_at"]
                    )
                )

        elif undo_type == "unmerge_contacts":
            # Restore primary to pre-merge state
            if "primary_before" in undo_data:
                primary_data = undo_data["primary_before"]
                primary = Contact(**primary_data)
                self.contacts[primary.contact_id] = primary
            # Restore secondary contact
            if "secondary" in undo_data:
                secondary_data = undo_data["secondary"]
                secondary = Contact(**secondary_data)
                self.contacts[secondary.contact_id] = secondary

        # Restore state-level metadata
        self.update_count = undo_data.get(
            "state_previous_update_count", self.update_count
        )
        prev_updated = undo_data.get("state_previous_last_updated")
        if prev_updated:
            self.last_updated = datetime.fromisoformat(prev_updated)

    # ==================================================================
    # Cross-modality lookup methods
    # ==================================================================

    def get_display_name(
        self, identifier_type: str, value: str
    ) -> Optional[str]:
        """Resolve an identifier to a display name.

        Args:
            identifier_type: Type of identifier (e.g., "phone", "email").
            value: The identifier value.

        Returns:
            The resolved display name, or None if not found.
        """
        contact = self.find_contact_by_identifier(identifier_type, value)
        if contact:
            return contact.get_resolved_display_name()
        return None

    def is_identifier_blocked(self, value: str) -> bool:
        """Check if any blocked contact has this identifier.

        Checks all identifier types across all blocked contacts.

        Args:
            value: The identifier value to check.

        Returns:
            True if the identifier belongs to a blocked contact.
        """
        for contact in self.contacts.values():
            if not contact.is_blocked:
                continue
            for ident in contact.identifiers:
                if ident.value == value:
                    return True
        return False

    def find_contact_by_identifier(
        self, identifier_type: str, value: str
    ) -> Optional[Contact]:
        """Find a contact by a specific identifier.

        Args:
            identifier_type: Type of identifier to search.
            value: The identifier value.

        Returns:
            The Contact if found, None otherwise.
        """
        for contact in self.contacts.values():
            if contact.has_identifier(identifier_type, value):
                return contact
        return None

    def find_contacts_by_group(self, group_name: str) -> list[Contact]:
        """Get all contacts in a group.

        Args:
            group_name: The group name to filter by.

        Returns:
            List of contacts in the specified group.
        """
        return [
            c
            for c in self.contacts.values()
            if group_name in c.groups
        ]

    def get_all_groups(self) -> set[str]:
        """Get the set of all group names across all contacts.

        Returns:
            Set of group name strings.
        """
        groups: set[str] = set()
        for contact in self.contacts.values():
            groups |= contact.groups
        return groups

    def get_favorites(self) -> list[Contact]:
        """Get all favorited contacts.

        Returns:
            List of contacts where is_favorite is True.
        """
        return [
            c for c in self.contacts.values() if c.is_favorite
        ]

    def get_blocked_contacts(self) -> list[Contact]:
        """Get all blocked contacts.

        Returns:
            List of contacts where is_blocked is True.
        """
        return [
            c for c in self.contacts.values() if c.is_blocked
        ]
