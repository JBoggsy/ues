"""Contacts modality sub-client for the UES API.

This module provides ContactsClient and AsyncContactsClient for interacting
with the Contacts modality endpoints (/contacts/*).

This is an internal module. Import from ``client`` instead.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field
from uuid import uuid4

from ues.client._base import AsyncBaseClient, BaseClient
from ues.client.models import ModalityActionResponse

if TYPE_CHECKING:
    from ues.client._http import AsyncHTTPClient, HTTPClient


# ===================================================================
# Response Models
# ===================================================================


class ContactIdentifier(BaseModel):
    """Represents a single identifier (phone number, email address, handle)
    for a contact.

    Attributes:
        identifier_type: Type of identifier (e.g., "phone", "email").
        value: The identifier string (phone number, email, handle).
        label: Optional user-defined label (e.g., "home", "work", "mobile").
    """

    identifier_type: str = Field(description="Type of identifier")
    value: str = Field(description="The identifier string")
    label: str | None = Field(
        default=None, description="User-defined label"
    )


class PostalAddress(BaseModel):
    """Represents a physical mailing address for a contact.

    Attributes:
        street: Street address.
        city: City name.
        state: State, province, or region.
        postal_code: ZIP code or postal code.
        country: Country name or ISO code.
        label: User-defined label (e.g., "home", "work").
    """

    street: str | None = Field(default=None, description="Street address")
    city: str | None = Field(default=None, description="City name")
    state: str | None = Field(
        default=None, description="State, province, or region"
    )
    postal_code: str | None = Field(
        default=None, description="ZIP code or postal code"
    )
    country: str | None = Field(
        default=None, description="Country name or ISO code"
    )
    label: str | None = Field(
        default=None, description="User-defined label"
    )


class Contact(BaseModel):
    """Represents a single contact entry in the address book.

    Attributes:
        contact_id: Unique identifier (UUID).
        first_name: First/given name.
        last_name: Last/family name.
        display_name: User-overridden display name (e.g., "Mom", "Dr. Smith").
        nickname: Informal name.
        identifiers: All phone numbers, emails, and handles.
        company: Organization/company name.
        job_title: Job title or role.
        addresses: Physical addresses.
        birthday: Date of birth.
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
    first_name: str | None = Field(
        default=None, description="First/given name"
    )
    last_name: str | None = Field(
        default=None, description="Last/family name"
    )
    display_name: str | None = Field(
        default=None, description="User-overridden display name"
    )
    nickname: str | None = Field(
        default=None, description="Informal name"
    )
    identifiers: list[ContactIdentifier] = Field(
        default_factory=list, description="All identifiers"
    )
    company: str | None = Field(
        default=None, description="Organization/company name"
    )
    job_title: str | None = Field(
        default=None, description="Job title or role"
    )
    addresses: list[PostalAddress] = Field(
        default_factory=list, description="Physical addresses"
    )
    birthday: Any | None = Field(
        default=None, description="Date of birth"
    )
    notes: str | None = Field(
        default=None, description="Free-text notes"
    )
    photo_url: str | None = Field(
        default=None, description="Profile photo URL"
    )
    is_favorite: bool = Field(
        default=False, description="Whether this contact is a favorite"
    )
    is_blocked: bool = Field(
        default=False, description="Whether this contact is blocked"
    )
    groups: list[str] = Field(
        default_factory=list, description="Group names"
    )
    created_at: datetime = Field(description="When contact was created")
    updated_at: datetime = Field(description="When contact was last modified")


class ContactsStateResponse(BaseModel):
    """Response model for contacts state endpoint.

    Attributes:
        modality_type: Always "contacts".
        current_time: Current simulator time.
        contacts: All contacts keyed by contact_id.
        total_count: Total number of contacts.
        favorites_count: Number of favorited contacts.
        blocked_count: Number of blocked contacts.
        groups: List of all group names.
    """

    modality_type: str = "contacts"
    current_time: datetime
    contacts: dict[str, Contact]
    total_count: int
    favorites_count: int
    blocked_count: int
    groups: list[str]


class ContactsCompactStateResponse(BaseModel):
    """Compact response model for contacts state endpoint.

    Used when compact=true query parameter is set. Optimized for LLM context.

    Attributes:
        modality_type: Always "contacts".
        last_updated: ISO timestamp of last update.
        update_count: Number of contacts state changes.
        total_contacts: Total number of contacts.
        favorites_count: Number of favorited contacts.
        blocked_count: Number of blocked contacts.
        groups: Group names with member counts.
        recent_contacts: Recently updated contacts (names only).
    """

    modality_type: str = "contacts"
    last_updated: str
    update_count: int
    total_contacts: int
    favorites_count: int
    blocked_count: int
    groups: dict[str, int]
    recent_contacts: list[dict[str, Any]]


class ContactsQueryResponse(BaseModel):
    """Response model for contacts query endpoint.

    Attributes:
        modality_type: Always "contacts".
        contacts: Query results (matching contacts).
        total_count: Total number of results matching query.
        returned_count: Number of results returned (after pagination).
        query: Echo of query parameters for debugging.
    """

    modality_type: str = "contacts"
    contacts: list[dict[str, Any]]
    total_count: int
    returned_count: int
    query: dict[str, Any]


# ===================================================================
# Synchronous ContactsClient
# ===================================================================


class ContactsClient(BaseClient):
    """Synchronous client for Contacts modality endpoints (/contacts/*).

    This client provides methods for managing the simulated contact database
    including creating, updating, deleting, blocking, favoriting, grouping,
    and merging contacts.

    Example:
        with UESClient() as client:
            # Create a contact
            client.contacts.create(
                first_name="Alice",
                last_name="Smith",
                identifiers=[
                    {"identifier_type": "phone", "value": "+15551234567"},
                    {"identifier_type": "email", "value": "alice@example.com"},
                ],
            )

            # Get contacts state
            state = client.contacts.get_state()
            print(f"Total contacts: {state.total_count}")

            # Query contacts
            results = client.contacts.query(search_text="Alice")
            print(f"Found {results.total_count} contacts")
    """

    _BASE_PATH = "/contacts"

    def get_state(
        self, compact: bool = False,
    ) -> ContactsStateResponse | ContactsCompactStateResponse:
        """Get the current contacts state.

        Returns a snapshot of the contacts database. When ``compact=True``,
        returns a lightweight response with contact metadata only, optimized
        for LLM context windows.

        Args:
            compact: If True, return compact state with contact counts and
                metadata only. Default is False (full state).

        Returns:
            Full contacts state, or compact state if ``compact=True``.

        Raises:
            APIError: If the request fails.
        """
        params = {"compact": True} if compact else None
        data = self._get(f"{self._BASE_PATH}/state", params=params)
        if compact:
            return ContactsCompactStateResponse(**data)
        return ContactsStateResponse(**data)

    def query(
        self,
        search_text: str | None = None,
        group: str | None = None,
        is_favorite: bool | None = None,
        is_blocked: bool | None = None,
        has_phone: bool | None = None,
        has_email: bool | None = None,
        identifier_type: str | None = None,
        identifier_value: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> ContactsQueryResponse:
        """Query contacts with filters.

        Allows filtering and searching through contacts with various criteria
        including name search, group membership, favorite/blocked status, etc.

        Args:
            search_text: Search by name or identifier (substring match).
            group: Filter by group membership.
            is_favorite: Filter by favorite status.
            is_blocked: Filter by blocked status.
            has_phone: Filter contacts with at least one phone identifier.
            has_email: Filter contacts with at least one email identifier.
            identifier_type: Filter by exact identifier type.
            identifier_value: Filter by exact identifier value.
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).

        Returns:
            Filtered contact results with counts.

        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {}

        if search_text is not None:
            request_data["search_text"] = search_text
        if group is not None:
            request_data["group"] = group
        if is_favorite is not None:
            request_data["is_favorite"] = is_favorite
        if is_blocked is not None:
            request_data["is_blocked"] = is_blocked
        if has_phone is not None:
            request_data["has_phone"] = has_phone
        if has_email is not None:
            request_data["has_email"] = has_email
        if identifier_type is not None:
            request_data["identifier_type"] = identifier_type
        if identifier_value is not None:
            request_data["identifier_value"] = identifier_value
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset

        data = self._post(f"{self._BASE_PATH}/query", json=request_data)
        return ContactsQueryResponse(**data)

    def create(
        self,
        identifiers: list[dict[str, Any]],
        first_name: str | None = None,
        last_name: str | None = None,
        display_name: str | None = None,
        nickname: str | None = None,
        company: str | None = None,
        job_title: str | None = None,
        addresses: list[dict[str, Any]] | None = None,
        birthday: date | str | None = None,
        notes: str | None = None,
        photo_url: str | None = None,
        is_favorite: bool = False,
        is_blocked: bool = False,
        groups: list[str] | None = None,
    ) -> ModalityActionResponse:
        """Create a new contact.

        Adds a new contact to the address book with the provided information.
        At least one identifier (phone, email, etc.) is required.

        Args:
            identifiers: Contact identifiers (at least one required). Each
                should be a dict with ``identifier_type``, ``value``, and
                optional ``label`` keys.
            first_name: First/given name.
            last_name: Last/family name.
            display_name: User-overridden display name.
            nickname: Informal name.
            company: Organization/company name.
            job_title: Job title or role.
            addresses: Physical addresses. Each should be a dict with optional
                ``street``, ``city``, ``state``, ``postal_code``, ``country``,
                ``label`` keys.
            birthday: Date of birth (date object or ISO date string).
            notes: Free-text notes.
            photo_url: Profile photo URL.
            is_favorite: Whether this contact is a favorite.
            is_blocked: Whether this contact is blocked.
            groups: Group names this contact belongs to.

        Returns:
            Action response with event details.

        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "identifiers": identifiers,
            "is_favorite": is_favorite,
            "is_blocked": is_blocked,
        }

        if first_name is not None:
            request_data["first_name"] = first_name
        if last_name is not None:
            request_data["last_name"] = last_name
        if display_name is not None:
            request_data["display_name"] = display_name
        if nickname is not None:
            request_data["nickname"] = nickname
        if company is not None:
            request_data["company"] = company
        if job_title is not None:
            request_data["job_title"] = job_title
        if addresses is not None:
            request_data["addresses"] = addresses
        if birthday is not None:
            if isinstance(birthday, date):
                request_data["birthday"] = birthday.isoformat()
            else:
                request_data["birthday"] = birthday
        if notes is not None:
            request_data["notes"] = notes
        if photo_url is not None:
            request_data["photo_url"] = photo_url
        if groups is not None:
            request_data["groups"] = groups

        data = self._post(f"{self._BASE_PATH}/create", json=request_data)
        return ModalityActionResponse(**data)

    def update(
        self,
        contact_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        display_name: str | None = None,
        nickname: str | None = None,
        identifiers: list[dict[str, Any]] | None = None,
        add_identifiers: list[dict[str, Any]] | None = None,
        remove_identifiers: list[dict[str, Any]] | None = None,
        company: str | None = None,
        job_title: str | None = None,
        addresses: list[dict[str, Any]] | None = None,
        add_addresses: list[dict[str, Any]] | None = None,
        remove_addresses: list[dict[str, Any]] | None = None,
        birthday: date | str | None = None,
        notes: str | None = None,
        photo_url: str | None = None,
        is_favorite: bool | None = None,
        is_blocked: bool | None = None,
        groups: list[str] | None = None,
        add_groups: list[str] | None = None,
        remove_groups: list[str] | None = None,
    ) -> ModalityActionResponse:
        """Update an existing contact.

        Modifies contact fields. Supports both full-replace and
        additive/subtractive updates for identifiers, addresses, and groups.

        Args:
            contact_id: ID of the contact to update.
            first_name: Updated first name.
            last_name: Updated last name.
            display_name: Updated display name.
            nickname: Updated nickname.
            identifiers: Full-replace identifiers.
            add_identifiers: Identifiers to add (additive).
            remove_identifiers: Identifiers to remove (subtractive).
            company: Updated company name.
            job_title: Updated job title.
            addresses: Full-replace addresses.
            add_addresses: Addresses to add.
            remove_addresses: Addresses to remove.
            birthday: Updated birthday (date object or ISO date string).
            notes: Updated notes.
            photo_url: Updated photo URL.
            is_favorite: Updated favorite status.
            is_blocked: Updated blocked status.
            groups: Full-replace groups.
            add_groups: Groups to add.
            remove_groups: Groups to remove.

        Returns:
            Action response with event details.

        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "contact_id": contact_id,
        }

        if first_name is not None:
            request_data["first_name"] = first_name
        if last_name is not None:
            request_data["last_name"] = last_name
        if display_name is not None:
            request_data["display_name"] = display_name
        if nickname is not None:
            request_data["nickname"] = nickname
        if identifiers is not None:
            request_data["identifiers"] = identifiers
        if add_identifiers is not None:
            request_data["add_identifiers"] = add_identifiers
        if remove_identifiers is not None:
            request_data["remove_identifiers"] = remove_identifiers
        if company is not None:
            request_data["company"] = company
        if job_title is not None:
            request_data["job_title"] = job_title
        if addresses is not None:
            request_data["addresses"] = addresses
        if add_addresses is not None:
            request_data["add_addresses"] = add_addresses
        if remove_addresses is not None:
            request_data["remove_addresses"] = remove_addresses
        if birthday is not None:
            if isinstance(birthday, date):
                request_data["birthday"] = birthday.isoformat()
            else:
                request_data["birthday"] = birthday
        if notes is not None:
            request_data["notes"] = notes
        if photo_url is not None:
            request_data["photo_url"] = photo_url
        if is_favorite is not None:
            request_data["is_favorite"] = is_favorite
        if is_blocked is not None:
            request_data["is_blocked"] = is_blocked
        if groups is not None:
            request_data["groups"] = groups
        if add_groups is not None:
            request_data["add_groups"] = add_groups
        if remove_groups is not None:
            request_data["remove_groups"] = remove_groups

        data = self._post(f"{self._BASE_PATH}/update", json=request_data)
        return ModalityActionResponse(**data)

    def delete(self, contact_id: str) -> ModalityActionResponse:
        """Delete a contact.

        Removes a contact from the address book entirely.

        Args:
            contact_id: ID of the contact to delete.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/delete",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    def block(self, contact_id: str) -> ModalityActionResponse:
        """Block a contact.

        Sets the blocked flag on a contact. All identifiers belonging to
        this contact will be considered blocked for cross-modality checks.

        Args:
            contact_id: ID of the contact to block.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/block",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    def unblock(self, contact_id: str) -> ModalityActionResponse:
        """Unblock a contact.

        Removes the blocked flag from a contact.

        Args:
            contact_id: ID of the contact to unblock.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/unblock",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    def favorite(self, contact_id: str) -> ModalityActionResponse:
        """Favorite a contact.

        Marks a contact as a favorite for quick access.

        Args:
            contact_id: ID of the contact to favorite.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/favorite",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    def unfavorite(self, contact_id: str) -> ModalityActionResponse:
        """Unfavorite a contact.

        Removes a contact from the favorites list.

        Args:
            contact_id: ID of the contact to unfavorite.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/unfavorite",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    def add_to_group(
        self, contact_id: str, group_name: str,
    ) -> ModalityActionResponse:
        """Add a contact to a group.

        Adds the specified contact to a named group. Groups are implicit —
        they exist as long as at least one contact belongs to them.

        Args:
            contact_id: ID of the contact.
            group_name: Name of the group to add to.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/group/add",
            json={
                "contact_id": contact_id,
                "group_name": group_name,
            },
        )
        return ModalityActionResponse(**data)

    def remove_from_group(
        self, contact_id: str, group_name: str,
    ) -> ModalityActionResponse:
        """Remove a contact from a group.

        Removes the specified contact from a named group.

        Args:
            contact_id: ID of the contact.
            group_name: Name of the group to remove from.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/group/remove",
            json={
                "contact_id": contact_id,
                "group_name": group_name,
            },
        )
        return ModalityActionResponse(**data)

    def merge(
        self,
        primary_contact_id: str,
        secondary_contact_id: str,
    ) -> ModalityActionResponse:
        """Merge two contacts.

        Merges the secondary contact into the primary contact. The primary
        contact absorbs the secondary's unique identifiers, addresses, and
        groups. The secondary contact is deleted after merge.

        Args:
            primary_contact_id: Contact to keep (absorbs data).
            secondary_contact_id: Contact to merge into primary (deleted).

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = self._post(
            f"{self._BASE_PATH}/merge",
            json={
                "primary_contact_id": primary_contact_id,
                "secondary_contact_id": secondary_contact_id,
            },
        )
        return ModalityActionResponse(**data)


# ===================================================================
# Asynchronous AsyncContactsClient
# ===================================================================


class AsyncContactsClient(AsyncBaseClient):
    """Asynchronous client for Contacts modality endpoints (/contacts/*).

    This client provides async methods for managing the simulated contact
    database including creating, updating, deleting, blocking, favoriting,
    grouping, and merging contacts.

    Example:
        async with AsyncUESClient() as client:
            # Create a contact
            await client.contacts.create(
                first_name="Alice",
                last_name="Smith",
                identifiers=[
                    {"identifier_type": "phone", "value": "+15551234567"},
                    {"identifier_type": "email", "value": "alice@example.com"},
                ],
            )

            # Get contacts state
            state = await client.contacts.get_state()
            print(f"Total contacts: {state.total_count}")

            # Query contacts
            results = await client.contacts.query(search_text="Alice")
            print(f"Found {results.total_count} contacts")
    """

    _BASE_PATH = "/contacts"

    async def get_state(
        self, compact: bool = False,
    ) -> ContactsStateResponse | ContactsCompactStateResponse:
        """Get the current contacts state.

        Returns a snapshot of the contacts database. When ``compact=True``,
        returns a lightweight response with contact metadata only, optimized
        for LLM context windows.

        Args:
            compact: If True, return compact state with contact counts and
                metadata only. Default is False (full state).

        Returns:
            Full contacts state, or compact state if ``compact=True``.

        Raises:
            APIError: If the request fails.
        """
        params = {"compact": True} if compact else None
        data = await self._get(f"{self._BASE_PATH}/state", params=params)
        if compact:
            return ContactsCompactStateResponse(**data)
        return ContactsStateResponse(**data)

    async def query(
        self,
        search_text: str | None = None,
        group: str | None = None,
        is_favorite: bool | None = None,
        is_blocked: bool | None = None,
        has_phone: bool | None = None,
        has_email: bool | None = None,
        identifier_type: str | None = None,
        identifier_value: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> ContactsQueryResponse:
        """Query contacts with filters.

        Allows filtering and searching through contacts with various criteria
        including name search, group membership, favorite/blocked status, etc.

        Args:
            search_text: Search by name or identifier (substring match).
            group: Filter by group membership.
            is_favorite: Filter by favorite status.
            is_blocked: Filter by blocked status.
            has_phone: Filter contacts with at least one phone identifier.
            has_email: Filter contacts with at least one email identifier.
            identifier_type: Filter by exact identifier type.
            identifier_value: Filter by exact identifier value.
            limit: Maximum number of results to return.
            offset: Number of results to skip (for pagination).

        Returns:
            Filtered contact results with counts.

        Raises:
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {}

        if search_text is not None:
            request_data["search_text"] = search_text
        if group is not None:
            request_data["group"] = group
        if is_favorite is not None:
            request_data["is_favorite"] = is_favorite
        if is_blocked is not None:
            request_data["is_blocked"] = is_blocked
        if has_phone is not None:
            request_data["has_phone"] = has_phone
        if has_email is not None:
            request_data["has_email"] = has_email
        if identifier_type is not None:
            request_data["identifier_type"] = identifier_type
        if identifier_value is not None:
            request_data["identifier_value"] = identifier_value
        if limit is not None:
            request_data["limit"] = limit
        if offset != 0:
            request_data["offset"] = offset

        data = await self._post(
            f"{self._BASE_PATH}/query", json=request_data,
        )
        return ContactsQueryResponse(**data)

    async def create(
        self,
        identifiers: list[dict[str, Any]],
        first_name: str | None = None,
        last_name: str | None = None,
        display_name: str | None = None,
        nickname: str | None = None,
        company: str | None = None,
        job_title: str | None = None,
        addresses: list[dict[str, Any]] | None = None,
        birthday: date | str | None = None,
        notes: str | None = None,
        photo_url: str | None = None,
        is_favorite: bool = False,
        is_blocked: bool = False,
        groups: list[str] | None = None,
    ) -> ModalityActionResponse:
        """Create a new contact.

        Adds a new contact to the address book with the provided information.
        At least one identifier (phone, email, etc.) is required.

        Args:
            identifiers: Contact identifiers (at least one required). Each
                should be a dict with ``identifier_type``, ``value``, and
                optional ``label`` keys.
            first_name: First/given name.
            last_name: Last/family name.
            display_name: User-overridden display name.
            nickname: Informal name.
            company: Organization/company name.
            job_title: Job title or role.
            addresses: Physical addresses. Each should be a dict with optional
                ``street``, ``city``, ``state``, ``postal_code``, ``country``,
                ``label`` keys.
            birthday: Date of birth (date object or ISO date string).
            notes: Free-text notes.
            photo_url: Profile photo URL.
            is_favorite: Whether this contact is a favorite.
            is_blocked: Whether this contact is blocked.
            groups: Group names this contact belongs to.

        Returns:
            Action response with event details.

        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "identifiers": identifiers,
            "is_favorite": is_favorite,
            "is_blocked": is_blocked,
        }

        if first_name is not None:
            request_data["first_name"] = first_name
        if last_name is not None:
            request_data["last_name"] = last_name
        if display_name is not None:
            request_data["display_name"] = display_name
        if nickname is not None:
            request_data["nickname"] = nickname
        if company is not None:
            request_data["company"] = company
        if job_title is not None:
            request_data["job_title"] = job_title
        if addresses is not None:
            request_data["addresses"] = addresses
        if birthday is not None:
            if isinstance(birthday, date):
                request_data["birthday"] = birthday.isoformat()
            else:
                request_data["birthday"] = birthday
        if notes is not None:
            request_data["notes"] = notes
        if photo_url is not None:
            request_data["photo_url"] = photo_url
        if groups is not None:
            request_data["groups"] = groups

        data = await self._post(
            f"{self._BASE_PATH}/create", json=request_data,
        )
        return ModalityActionResponse(**data)

    async def update(
        self,
        contact_id: str,
        first_name: str | None = None,
        last_name: str | None = None,
        display_name: str | None = None,
        nickname: str | None = None,
        identifiers: list[dict[str, Any]] | None = None,
        add_identifiers: list[dict[str, Any]] | None = None,
        remove_identifiers: list[dict[str, Any]] | None = None,
        company: str | None = None,
        job_title: str | None = None,
        addresses: list[dict[str, Any]] | None = None,
        add_addresses: list[dict[str, Any]] | None = None,
        remove_addresses: list[dict[str, Any]] | None = None,
        birthday: date | str | None = None,
        notes: str | None = None,
        photo_url: str | None = None,
        is_favorite: bool | None = None,
        is_blocked: bool | None = None,
        groups: list[str] | None = None,
        add_groups: list[str] | None = None,
        remove_groups: list[str] | None = None,
    ) -> ModalityActionResponse:
        """Update an existing contact.

        Modifies contact fields. Supports both full-replace and
        additive/subtractive updates for identifiers, addresses, and groups.

        Args:
            contact_id: ID of the contact to update.
            first_name: Updated first name.
            last_name: Updated last name.
            display_name: Updated display name.
            nickname: Updated nickname.
            identifiers: Full-replace identifiers.
            add_identifiers: Identifiers to add (additive).
            remove_identifiers: Identifiers to remove (subtractive).
            company: Updated company name.
            job_title: Updated job title.
            addresses: Full-replace addresses.
            add_addresses: Addresses to add.
            remove_addresses: Addresses to remove.
            birthday: Updated birthday (date object or ISO date string).
            notes: Updated notes.
            photo_url: Updated photo URL.
            is_favorite: Updated favorite status.
            is_blocked: Updated blocked status.
            groups: Full-replace groups.
            add_groups: Groups to add.
            remove_groups: Groups to remove.

        Returns:
            Action response with event details.

        Raises:
            ValidationError: If request parameters are invalid.
            APIError: If the request fails.
        """
        request_data: dict[str, Any] = {
            "contact_id": contact_id,
        }

        if first_name is not None:
            request_data["first_name"] = first_name
        if last_name is not None:
            request_data["last_name"] = last_name
        if display_name is not None:
            request_data["display_name"] = display_name
        if nickname is not None:
            request_data["nickname"] = nickname
        if identifiers is not None:
            request_data["identifiers"] = identifiers
        if add_identifiers is not None:
            request_data["add_identifiers"] = add_identifiers
        if remove_identifiers is not None:
            request_data["remove_identifiers"] = remove_identifiers
        if company is not None:
            request_data["company"] = company
        if job_title is not None:
            request_data["job_title"] = job_title
        if addresses is not None:
            request_data["addresses"] = addresses
        if add_addresses is not None:
            request_data["add_addresses"] = add_addresses
        if remove_addresses is not None:
            request_data["remove_addresses"] = remove_addresses
        if birthday is not None:
            if isinstance(birthday, date):
                request_data["birthday"] = birthday.isoformat()
            else:
                request_data["birthday"] = birthday
        if notes is not None:
            request_data["notes"] = notes
        if photo_url is not None:
            request_data["photo_url"] = photo_url
        if is_favorite is not None:
            request_data["is_favorite"] = is_favorite
        if is_blocked is not None:
            request_data["is_blocked"] = is_blocked
        if groups is not None:
            request_data["groups"] = groups
        if add_groups is not None:
            request_data["add_groups"] = add_groups
        if remove_groups is not None:
            request_data["remove_groups"] = remove_groups

        data = await self._post(
            f"{self._BASE_PATH}/update", json=request_data,
        )
        return ModalityActionResponse(**data)

    async def delete(self, contact_id: str) -> ModalityActionResponse:
        """Delete a contact.

        Removes a contact from the address book entirely.

        Args:
            contact_id: ID of the contact to delete.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/delete",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    async def block(self, contact_id: str) -> ModalityActionResponse:
        """Block a contact.

        Sets the blocked flag on a contact. All identifiers belonging to
        this contact will be considered blocked for cross-modality checks.

        Args:
            contact_id: ID of the contact to block.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/block",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    async def unblock(self, contact_id: str) -> ModalityActionResponse:
        """Unblock a contact.

        Removes the blocked flag from a contact.

        Args:
            contact_id: ID of the contact to unblock.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/unblock",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    async def favorite(self, contact_id: str) -> ModalityActionResponse:
        """Favorite a contact.

        Marks a contact as a favorite for quick access.

        Args:
            contact_id: ID of the contact to favorite.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/favorite",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    async def unfavorite(self, contact_id: str) -> ModalityActionResponse:
        """Unfavorite a contact.

        Removes a contact from the favorites list.

        Args:
            contact_id: ID of the contact to unfavorite.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/unfavorite",
            json={"contact_id": contact_id},
        )
        return ModalityActionResponse(**data)

    async def add_to_group(
        self, contact_id: str, group_name: str,
    ) -> ModalityActionResponse:
        """Add a contact to a group.

        Adds the specified contact to a named group. Groups are implicit —
        they exist as long as at least one contact belongs to them.

        Args:
            contact_id: ID of the contact.
            group_name: Name of the group to add to.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/group/add",
            json={
                "contact_id": contact_id,
                "group_name": group_name,
            },
        )
        return ModalityActionResponse(**data)

    async def remove_from_group(
        self, contact_id: str, group_name: str,
    ) -> ModalityActionResponse:
        """Remove a contact from a group.

        Removes the specified contact from a named group.

        Args:
            contact_id: ID of the contact.
            group_name: Name of the group to remove from.

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/group/remove",
            json={
                "contact_id": contact_id,
                "group_name": group_name,
            },
        )
        return ModalityActionResponse(**data)

    async def merge(
        self,
        primary_contact_id: str,
        secondary_contact_id: str,
    ) -> ModalityActionResponse:
        """Merge two contacts.

        Merges the secondary contact into the primary contact. The primary
        contact absorbs the secondary's unique identifiers, addresses, and
        groups. The secondary contact is deleted after merge.

        Args:
            primary_contact_id: Contact to keep (absorbs data).
            secondary_contact_id: Contact to merge into primary (deleted).

        Returns:
            Action response with event details.

        Raises:
            APIError: If the request fails.
        """
        data = await self._post(
            f"{self._BASE_PATH}/merge",
            json={
                "primary_contact_id": primary_contact_id,
                "secondary_contact_id": secondary_contact_id,
            },
        )
        return ModalityActionResponse(**data)
