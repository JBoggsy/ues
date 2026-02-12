"""Contacts modality endpoints.

Provides REST API endpoints for managing contacts including creating,
updating, deleting, blocking, favoriting, grouping, and merging contacts.

All endpoints require authentication via X-API-Key header.
"""

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ues.api.auth import Permissions, require_permission
from ues.api.broadcast import broadcast_event
from ues.api.dependencies import SimulationEngineDep
from ues.api.models import ModalityActionResponse
from ues.api.utils import create_immediate_event, normalize_phone_number
from ues.api.websocket import WSEventType
from ues.models.api_key import APIKey
from ues.models.modalities.contacts_input import (
    ContactIdentifier,
    ContactsInput,
    PostalAddress,
)
from ues.models.modalities.contacts_state import Contact, ContactsState

router = APIRouter(
    prefix="/contacts",
    tags=["contacts"],
)


# ============================================================================
# Request Models
# ============================================================================


class ContactIdentifierRequest(BaseModel):
    """Request model for a contact identifier.

    Attributes:
        identifier_type: Type of identifier (e.g., "phone", "email").
        value: The identifier string.
        label: Optional user-defined label (e.g., "home", "work").
    """

    identifier_type: str = Field(description="Type of identifier")
    value: str = Field(description="The identifier string")
    label: str | None = Field(default=None, description="User-defined label")


class PostalAddressRequest(BaseModel):
    """Request model for a postal address.

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
    state: str | None = Field(default=None, description="State or region")
    postal_code: str | None = Field(default=None, description="Postal code")
    country: str | None = Field(default=None, description="Country")
    label: str | None = Field(default=None, description="User-defined label")


class CreateContactRequest(BaseModel):
    """Request model for creating a new contact.

    Attributes:
        first_name: First/given name.
        last_name: Last/family name.
        display_name: User-overridden display name.
        nickname: Informal name.
        identifiers: Contact identifiers (at least one required).
        company: Organization/company name.
        job_title: Job title or role.
        addresses: Physical addresses.
        birthday: Date of birth.
        notes: Free-text notes.
        photo_url: Profile photo URL.
        is_favorite: Whether this contact is a favorite.
        is_blocked: Whether this contact is blocked.
        groups: Group names this contact belongs to.
    """

    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    display_name: str | None = Field(
        default=None, description="Display name override"
    )
    nickname: str | None = Field(default=None, description="Nickname")
    identifiers: list[ContactIdentifierRequest] = Field(
        min_length=1, description="Contact identifiers (at least one)"
    )
    company: str | None = Field(default=None, description="Company name")
    job_title: str | None = Field(default=None, description="Job title")
    addresses: list[PostalAddressRequest] = Field(
        default_factory=list, description="Physical addresses"
    )
    birthday: date | None = Field(default=None, description="Date of birth")
    notes: str | None = Field(default=None, description="Free-text notes")
    photo_url: str | None = Field(default=None, description="Photo URL")
    is_favorite: bool = Field(default=False, description="Favorite status")
    is_blocked: bool = Field(default=False, description="Blocked status")
    groups: set[str] = Field(
        default_factory=set, description="Group memberships"
    )


class UpdateContactRequest(BaseModel):
    """Request model for updating an existing contact.

    Supports both full-replace and additive/subtractive updates
    for identifiers, addresses, and groups.

    Attributes:
        contact_id: ID of the contact to update.
        first_name: Updated first name.
        last_name: Updated last name.
        display_name: Updated display name.
        nickname: Updated nickname.
        identifiers: Full-replace identifiers.
        add_identifiers: Identifiers to add.
        remove_identifiers: Identifiers to remove.
        company: Updated company name.
        job_title: Updated job title.
        addresses: Full-replace addresses.
        add_addresses: Addresses to add.
        remove_addresses: Addresses to remove.
        birthday: Updated birthday.
        notes: Updated notes.
        photo_url: Updated photo URL.
        is_favorite: Updated favorite status.
        is_blocked: Updated blocked status.
        groups: Full-replace groups.
        add_groups: Groups to add.
        remove_groups: Groups to remove.
    """

    contact_id: str = Field(description="Contact ID to update")
    first_name: str | None = Field(default=None, description="First name")
    last_name: str | None = Field(default=None, description="Last name")
    display_name: str | None = Field(default=None, description="Display name")
    nickname: str | None = Field(default=None, description="Nickname")
    identifiers: list[ContactIdentifierRequest] | None = Field(
        default=None, description="Full-replace identifiers"
    )
    add_identifiers: list[ContactIdentifierRequest] | None = Field(
        default=None, description="Identifiers to add"
    )
    remove_identifiers: list[ContactIdentifierRequest] | None = Field(
        default=None, description="Identifiers to remove"
    )
    company: str | None = Field(default=None, description="Company name")
    job_title: str | None = Field(default=None, description="Job title")
    addresses: list[PostalAddressRequest] | None = Field(
        default=None, description="Full-replace addresses"
    )
    add_addresses: list[PostalAddressRequest] | None = Field(
        default=None, description="Addresses to add"
    )
    remove_addresses: list[PostalAddressRequest] | None = Field(
        default=None, description="Addresses to remove"
    )
    birthday: date | None = Field(default=None, description="Date of birth")
    notes: str | None = Field(default=None, description="Notes")
    photo_url: str | None = Field(default=None, description="Photo URL")
    is_favorite: bool | None = Field(
        default=None, description="Favorite status"
    )
    is_blocked: bool | None = Field(
        default=None, description="Blocked status"
    )
    groups: set[str] | None = Field(
        default=None, description="Full-replace groups"
    )
    add_groups: set[str] | None = Field(
        default=None, description="Groups to add"
    )
    remove_groups: set[str] | None = Field(
        default=None, description="Groups to remove"
    )


class DeleteContactRequest(BaseModel):
    """Request model for deleting a contact.

    Attributes:
        contact_id: ID of the contact to delete.
    """

    contact_id: str = Field(description="Contact ID to delete")


class BlockContactRequest(BaseModel):
    """Request model for blocking a contact.

    Attributes:
        contact_id: ID of the contact to block.
    """

    contact_id: str = Field(description="Contact ID to block")


class UnblockContactRequest(BaseModel):
    """Request model for unblocking a contact.

    Attributes:
        contact_id: ID of the contact to unblock.
    """

    contact_id: str = Field(description="Contact ID to unblock")


class FavoriteContactRequest(BaseModel):
    """Request model for favoriting a contact.

    Attributes:
        contact_id: ID of the contact to favorite.
    """

    contact_id: str = Field(description="Contact ID to favorite")


class UnfavoriteContactRequest(BaseModel):
    """Request model for unfavoriting a contact.

    Attributes:
        contact_id: ID of the contact to unfavorite.
    """

    contact_id: str = Field(description="Contact ID to unfavorite")


class AddToGroupRequest(BaseModel):
    """Request model for adding a contact to a group.

    Attributes:
        contact_id: ID of the contact.
        group_name: Name of the group to add to.
    """

    contact_id: str = Field(description="Contact ID")
    group_name: str = Field(description="Group name to add to")


class RemoveFromGroupRequest(BaseModel):
    """Request model for removing a contact from a group.

    Attributes:
        contact_id: ID of the contact.
        group_name: Name of the group to remove from.
    """

    contact_id: str = Field(description="Contact ID")
    group_name: str = Field(description="Group name to remove from")


class MergeContactsRequest(BaseModel):
    """Request model for merging two contacts.

    The primary contact absorbs data from the secondary contact.
    The secondary contact is deleted after merge.

    Attributes:
        primary_contact_id: Contact to keep (absorbs data).
        secondary_contact_id: Contact to merge in (deleted after).
    """

    primary_contact_id: str = Field(description="Contact to keep")
    secondary_contact_id: str = Field(
        description="Contact to merge into primary (deleted)"
    )


class ContactsQueryRequest(BaseModel):
    """Request model for querying contacts.

    Attributes:
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
    """

    search_text: str | None = Field(
        default=None, description="Search by name or identifier"
    )
    group: str | None = Field(
        default=None, description="Filter by group membership"
    )
    is_favorite: bool | None = Field(
        default=None, description="Filter by favorite status"
    )
    is_blocked: bool | None = Field(
        default=None, description="Filter by blocked status"
    )
    has_phone: bool | None = Field(
        default=None, description="Filter by has phone identifier"
    )
    has_email: bool | None = Field(
        default=None, description="Filter by has email identifier"
    )
    identifier_type: str | None = Field(
        default=None, description="Filter by identifier type"
    )
    identifier_value: str | None = Field(
        default=None, description="Filter by identifier value"
    )
    limit: int | None = Field(
        default=None, ge=1, le=1000, description="Max results"
    )
    offset: int = Field(default=0, ge=0, description="Results to skip")


# ============================================================================
# Response Models
# ============================================================================


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

    modality_type: str = Field(default="contacts")
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

    modality_type: str = Field(default="contacts")
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

    modality_type: str = Field(default="contacts")
    contacts: list[dict[str, Any]]
    total_count: int
    returned_count: int
    query: dict


# ============================================================================
# Helper Functions
# ============================================================================


def _get_contacts_state(engine: SimulationEngineDep) -> ContactsState:
    """Get the ContactsState from the engine, validating it exists.

    Args:
        engine: The simulation engine dependency.

    Returns:
        The ContactsState instance.

    Raises:
        HTTPException: If contacts state is not properly initialized.
    """
    contacts_state = engine.environment.get_state("contacts")

    if not isinstance(contacts_state, ContactsState):
        raise HTTPException(
            status_code=500,
            detail="Contacts state not properly initialized",
        )

    return contacts_state


def _identifiers_to_model(
    identifiers: list[ContactIdentifierRequest],
) -> list[ContactIdentifier]:
    """Convert request identifier models to domain models.

    Phone-type identifiers are normalized to a consistent E.164-like
    format via ``normalize_phone_number`` so that different input
    representations (parentheses, hyphens, spaces, etc.) are stored
    uniformly.

    Args:
        identifiers: List of request identifier objects.

    Returns:
        List of ContactIdentifier domain models.
    """
    return [
        ContactIdentifier(
            identifier_type=ident.identifier_type,
            value=(
                normalize_phone_number(ident.value)
                if ident.identifier_type == "phone"
                else ident.value
            ),
            label=ident.label,
        )
        for ident in identifiers
    ]


def _addresses_to_model(
    addresses: list[PostalAddressRequest],
) -> list[PostalAddress]:
    """Convert request address models to domain models.

    Args:
        addresses: List of request address objects.

    Returns:
        List of PostalAddress domain models.
    """
    return [
        PostalAddress(
            street=addr.street,
            city=addr.city,
            state=addr.state,
            postal_code=addr.postal_code,
            country=addr.country,
            label=addr.label,
        )
        for addr in addresses
    ]


# ============================================================================
# Route Handlers
# ============================================================================


@router.get("/state")
async def get_contacts_state(
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_STATE))],
    compact: bool = False,
) -> ContactsStateResponse | ContactsCompactStateResponse:
    """Get current contacts state.

    Returns a snapshot of the contacts database including all contacts,
    group information, and counts.

    Args:
        engine: The simulation engine dependency.
        compact: If True, return compact state optimized for LLM context.

    Returns:
        ContactsStateResponse: Full state with all contacts (default).
        ContactsCompactStateResponse: Compact state (if compact=True).

    Requires:
        Permission: contacts:state
    """
    contacts_state = _get_contacts_state(engine)

    if compact:
        current_time = engine.environment.time_state.current_time
        snapshot = contacts_state.get_compact_snapshot(current_time)
        return ContactsCompactStateResponse(**snapshot)

    snapshot = contacts_state.get_snapshot()

    return ContactsStateResponse(
        current_time=engine.environment.time_state.current_time,
        contacts=contacts_state.contacts,
        total_count=snapshot["total_contacts"],
        favorites_count=snapshot["favorites_count"],
        blocked_count=snapshot["blocked_count"],
        groups=snapshot["groups"],
    )


@router.post("/query", response_model=ContactsQueryResponse)
async def query_contacts(
    request: ContactsQueryRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_QUERY))],
) -> ContactsQueryResponse:
    """Query contacts with filters.

    Allows filtering and searching through contacts with various criteria
    including name search, group membership, favorite/blocked status, etc.

    Args:
        request: Query filters and pagination parameters.
        engine: The simulation engine dependency.

    Returns:
        Filtered contact results with counts.

    Requires:
        Permission: contacts:query
    """
    contacts_state = _get_contacts_state(engine)

    query_params = {
        "search_text": request.search_text,
        "group": request.group,
        "is_favorite": request.is_favorite,
        "is_blocked": request.is_blocked,
        "has_phone": request.has_phone,
        "has_email": request.has_email,
        "identifier_type": request.identifier_type,
        "identifier_value": request.identifier_value,
        "limit": request.limit,
        "offset": request.offset,
    }

    result = contacts_state.query(query_params)

    return ContactsQueryResponse(
        contacts=result["contacts"],
        total_count=result["count"],
        returned_count=result["returned_count"],
        query=request.model_dump(exclude_none=True),
    )


@router.post("/create", response_model=ModalityActionResponse)
async def create_contact(
    request: CreateContactRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_CREATE))],
) -> ModalityActionResponse:
    """Create a new contact.

    Adds a new contact to the address book with the provided information.
    At least one identifier (phone, email, etc.) is required.

    Args:
        request: Contact data including identifiers.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:create
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="create_contact",
        first_name=request.first_name,
        last_name=request.last_name,
        display_name=request.display_name,
        nickname=request.nickname,
        identifiers=_identifiers_to_model(request.identifiers),
        company=request.company,
        job_title=request.job_title,
        addresses=(
            _addresses_to_model(request.addresses)
            if request.addresses
            else None
        ),
        birthday=request.birthday,
        notes=request.notes,
        photo_url=request.photo_url,
        is_favorite=request.is_favorite,
        is_blocked=request.is_blocked,
        groups=request.groups if request.groups else None,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_CREATED, {
        "event_id": event.event_id,
        "name": (
            f"{request.first_name or ''} {request.last_name or ''}".strip()
            or request.display_name
            or request.identifiers[0].value
        ),
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            "Contact created successfully"
            if not event.error_message
            else f"Failed to create contact: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/update", response_model=ModalityActionResponse)
async def update_contact(
    request: UpdateContactRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_UPDATE))],
) -> ModalityActionResponse:
    """Update an existing contact.

    Modifies contact fields. Supports both full-replace and additive/subtractive
    updates for identifiers, addresses, and groups.

    Args:
        request: Contact ID and fields to update.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:update
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="update_contact",
        contact_id=request.contact_id,
        first_name=request.first_name,
        last_name=request.last_name,
        display_name=request.display_name,
        nickname=request.nickname,
        identifiers=(
            _identifiers_to_model(request.identifiers)
            if request.identifiers is not None
            else None
        ),
        add_identifiers=(
            _identifiers_to_model(request.add_identifiers)
            if request.add_identifiers is not None
            else None
        ),
        remove_identifiers=(
            _identifiers_to_model(request.remove_identifiers)
            if request.remove_identifiers is not None
            else None
        ),
        company=request.company,
        job_title=request.job_title,
        addresses=(
            _addresses_to_model(request.addresses)
            if request.addresses is not None
            else None
        ),
        add_addresses=(
            _addresses_to_model(request.add_addresses)
            if request.add_addresses is not None
            else None
        ),
        remove_addresses=(
            _addresses_to_model(request.remove_addresses)
            if request.remove_addresses is not None
            else None
        ),
        birthday=request.birthday,
        notes=request.notes,
        photo_url=request.photo_url,
        is_favorite=request.is_favorite,
        is_blocked=request.is_blocked,
        groups=request.groups,
        add_groups=request.add_groups,
        remove_groups=request.remove_groups,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_UPDATED, {
        "event_id": event.event_id,
        "contact_id": request.contact_id,
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contact {request.contact_id} updated successfully"
            if not event.error_message
            else f"Failed to update contact: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/delete", response_model=ModalityActionResponse)
async def delete_contact(
    request: DeleteContactRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_DELETE))],
) -> ModalityActionResponse:
    """Delete a contact.

    Removes a contact from the address book entirely.

    Args:
        request: Contact ID to delete.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:delete
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="delete_contact",
        contact_id=request.contact_id,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_DELETED, {
        "event_id": event.event_id,
        "contact_id": request.contact_id,
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contact {request.contact_id} deleted successfully"
            if not event.error_message
            else f"Failed to delete contact: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/block", response_model=ModalityActionResponse)
async def block_contact(
    request: BlockContactRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_BLOCK))],
) -> ModalityActionResponse:
    """Block a contact.

    Sets the blocked flag on a contact. All identifiers belonging to this
    contact will be considered blocked for cross-modality checks.

    Args:
        request: Contact ID to block.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:block
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="block_contact",
        contact_id=request.contact_id,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_BLOCKED, {
        "event_id": event.event_id,
        "contact_id": request.contact_id,
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contact {request.contact_id} blocked successfully"
            if not event.error_message
            else f"Failed to block contact: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/unblock", response_model=ModalityActionResponse)
async def unblock_contact(
    request: UnblockContactRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_UNBLOCK))],
) -> ModalityActionResponse:
    """Unblock a contact.

    Removes the blocked flag from a contact.

    Args:
        request: Contact ID to unblock.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:unblock
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="unblock_contact",
        contact_id=request.contact_id,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_UNBLOCKED, {
        "event_id": event.event_id,
        "contact_id": request.contact_id,
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contact {request.contact_id} unblocked successfully"
            if not event.error_message
            else f"Failed to unblock contact: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/favorite", response_model=ModalityActionResponse)
async def favorite_contact(
    request: FavoriteContactRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_FAVORITE))],
) -> ModalityActionResponse:
    """Favorite a contact.

    Marks a contact as a favorite for quick access.

    Args:
        request: Contact ID to favorite.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:favorite
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="favorite_contact",
        contact_id=request.contact_id,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_UPDATED, {
        "event_id": event.event_id,
        "contact_id": request.contact_id,
        "action": "favorited",
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contact {request.contact_id} favorited successfully"
            if not event.error_message
            else f"Failed to favorite contact: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/unfavorite", response_model=ModalityActionResponse)
async def unfavorite_contact(
    request: UnfavoriteContactRequest,
    engine: SimulationEngineDep,
    _: Annotated[
        APIKey, Depends(require_permission(Permissions.CONTACTS_UNFAVORITE))
    ],
) -> ModalityActionResponse:
    """Unfavorite a contact.

    Removes a contact from the favorites list.

    Args:
        request: Contact ID to unfavorite.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:unfavorite
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="unfavorite_contact",
        contact_id=request.contact_id,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_UPDATED, {
        "event_id": event.event_id,
        "contact_id": request.contact_id,
        "action": "unfavorited",
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contact {request.contact_id} unfavorited successfully"
            if not event.error_message
            else f"Failed to unfavorite contact: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/group/add", response_model=ModalityActionResponse)
async def add_to_group(
    request: AddToGroupRequest,
    engine: SimulationEngineDep,
    _: Annotated[
        APIKey, Depends(require_permission(Permissions.CONTACTS_GROUP_ADD))
    ],
) -> ModalityActionResponse:
    """Add a contact to a group.

    Adds the specified contact to a named group. Groups are implicit —
    they exist as long as at least one contact belongs to them.

    Args:
        request: Contact ID and group name.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:group:add
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="add_to_group",
        contact_id=request.contact_id,
        group_name=request.group_name,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_UPDATED, {
        "event_id": event.event_id,
        "contact_id": request.contact_id,
        "group": request.group_name,
        "action": "added_to_group",
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contact {request.contact_id} added to group "
            f"'{request.group_name}' successfully"
            if not event.error_message
            else f"Failed to add to group: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/group/remove", response_model=ModalityActionResponse)
async def remove_from_group(
    request: RemoveFromGroupRequest,
    engine: SimulationEngineDep,
    _: Annotated[
        APIKey, Depends(require_permission(Permissions.CONTACTS_GROUP_REMOVE))
    ],
) -> ModalityActionResponse:
    """Remove a contact from a group.

    Removes the specified contact from a named group.

    Args:
        request: Contact ID and group name.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:group:remove
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="remove_from_group",
        contact_id=request.contact_id,
        group_name=request.group_name,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_UPDATED, {
        "event_id": event.event_id,
        "contact_id": request.contact_id,
        "group": request.group_name,
        "action": "removed_from_group",
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contact {request.contact_id} removed from group "
            f"'{request.group_name}' successfully"
            if not event.error_message
            else f"Failed to remove from group: {event.error_message}"
        ),
        modality="contacts",
    )


@router.post("/merge", response_model=ModalityActionResponse)
async def merge_contacts(
    request: MergeContactsRequest,
    engine: SimulationEngineDep,
    _: Annotated[APIKey, Depends(require_permission(Permissions.CONTACTS_MERGE))],
) -> ModalityActionResponse:
    """Merge two contacts.

    Merges the secondary contact into the primary contact. The primary
    contact absorbs the secondary's unique identifiers, addresses, and
    groups. The secondary contact is deleted after merge.

    Args:
        request: Primary and secondary contact IDs.
        engine: The simulation engine dependency.

    Returns:
        Action response with event details.

    Requires:
        Permission: contacts:merge
    """
    contacts_input = ContactsInput(
        timestamp=engine.environment.time_state.current_time,
        operation="merge_contacts",
        primary_contact_id=request.primary_contact_id,
        secondary_contact_id=request.secondary_contact_id,
    )

    event = create_immediate_event(
        engine=engine,
        modality="contacts",
        data=contacts_input,
        priority=100,
    )

    await broadcast_event(WSEventType.CONTACT_MERGED, {
        "event_id": event.event_id,
        "primary_contact_id": request.primary_contact_id,
        "secondary_contact_id": request.secondary_contact_id,
    })

    return ModalityActionResponse(
        event_id=event.event_id,
        scheduled_time=event.scheduled_time,
        status=event.status.value,
        message=(
            f"Contacts merged successfully (primary: "
            f"{request.primary_contact_id})"
            if not event.error_message
            else f"Failed to merge contacts: {event.error_message}"
        ),
        modality="contacts",
    )
