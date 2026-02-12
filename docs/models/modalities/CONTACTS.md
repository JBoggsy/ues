# Contacts Modality Design

The Contacts modality simulates a user's contact database (address book) for testing AI personal assistants. It serves as the **authoritative source for people-related metadata** — display names, phone numbers, email addresses, blocked status, and organizational grouping — consumed by other modalities (SMS, Email, Calendar) via cross-modality queries. This is the first modality in UES that other modalities explicitly depend on.

## Contact Data

- **Contact ID**: Unique identifier for each contact (UUID)
- **Name**:
  - First name
  - Last name
  - Display name (computed or overridden: e.g., "Mom", "Dr. Smith")
  - Nickname (optional informal name)
- **Identifiers**: Structured list of `ContactIdentifier` entries, each with:
  - Type: `phone`, `email`, or extensible platform types (future: `discord`, `slack`, etc.)
  - Value: The identifier string (phone number, email address, handle)
  - Label: Optional user-defined label (e.g., "work", "home", "mobile")
- **Organization**:
  - Company name
  - Job title
- **Address**:
  - Street address
  - City, state/province, postal code, country
  - Label (e.g., "home", "work")
- **Birthday**: Date of birth (date only, no time)
- **Notes**: Free-text notes field
- **Photo URL**: Profile photo URL (optional, for UI rendering)
- **Favorite status**: Boolean flag for quick-access contacts
- **Blocked status**: Boolean flag — blocks the **entire contact** across all identifiers
- **Groups**: Set of group names this contact belongs to (user-defined, e.g., "Family", "Work")

## Contact Metadata

- **Created at**: Simulator timestamp when contact was created
- **Updated at**: Simulator timestamp when contact was last modified

## Contact Groups

User-defined groups organize contacts for filtering and display:

- **Group names**: Arbitrary strings (e.g., "Family", "Work", "Book Club")
- **Membership**: A contact can belong to zero or more groups
- **Groups are implicit**: Groups are not separate entities — they exist as the union of all group names across contacts. A group "exists" as long as at least one contact belongs to it.
- **Group operations**: Add contact to group, remove contact from group, list contacts in group

## Favorites

- **`is_favorite: bool`** flag on each contact
- Quick-access subset for frequently contacted people
- Independent of groups (a contact can be both favorite and in groups)

## Blocking

- **Scope**: Per-contact blocking — when a contact is blocked, **all** their identifiers (every phone number, email address, and handle) are considered blocked
- **Blocked contacts** are still stored in the contact database; they are not deleted
- **Cross-modality behavior**: Other modalities (SMS, Email) can query ContactsState to check if an identifier belongs to a blocked contact
  - SMS: Reject or filter messages from blocked numbers
  - Email: Filter emails from blocked addresses
  - Calendar: Optionally flag invitations from blocked contacts
- **Block/unblock operations**: Toggle the `is_blocked` flag on a contact

## Search and Filtering

- **Search by**:
  - Name (first, last, display, nickname — substring match)
  - Phone number (exact or partial match)
  - Email address (exact or partial match)
  - Company or job title
  - Notes content
- **Filter by**:
  - Group membership
  - Favorite status
  - Blocked status
  - Has phone number / has email address
  - Recently added or updated

## Cross-Modality Integration

The Contacts modality is a **service modality** — it primarily provides data to other modalities rather than generating user-facing events on its own.

### SMS Integration
- **Display name resolution**: `get_display_name_for_phone(phone_number)` — returns display name or `None` (SMS falls back to raw phone number)
- **Blocked number checking**: `is_identifier_blocked(phone_number)` — returns whether the phone number belongs to a blocked contact
- **Contact lookup**: Phone number → full contact info

### Email Integration
- **Display name resolution**: `get_display_name_for_email(email_address)` — returns display name or `None`
- **Blocked sender checking**: `is_identifier_blocked(email_address)` — returns whether the email belongs to a blocked contact
- **Contact lookup**: Email address → full contact info

### Calendar Integration
- **Attendee enrichment**: `get_contact_for_email(email_address)` — returns contact info to populate `Attendee.display_name` and other metadata
- **Blocked contact detection**: Flag calendar invitations from blocked contacts

### Query Interface for Other Modalities

ContactsState exposes lookup methods that other modalities or the API layer can call:

```python
# Resolve a display name from any identifier type
contacts_state.get_display_name("phone", "+15551234567")  # → "Alice Smith" or None
contacts_state.get_display_name("email", "alice@example.com")  # → "Alice Smith" or None

# Check if an identifier belongs to a blocked contact
contacts_state.is_identifier_blocked("+15551234567")  # → True/False
contacts_state.is_identifier_blocked("alice@example.com")  # → True/False

# Full contact lookup by identifier
contacts_state.find_contact_by_identifier("phone", "+15551234567")  # → Contact or None
```

### Cross-Modality Query Mechanism

> **✅ RESOLVED**: The `ModalityState.apply_input()` signature has been extended to accept an optional `environment` parameter:
>
> ```python
> def apply_input(
>     self,
>     input_data: "ModalityInput",
>     environment: Optional["Environment"] = None,
> ) -> None:
> ```
>
> **How it works**:
> - The `Environment` object holds all modality states in a `dict[str, ModalityState]`. When `apply_input()` is called from the production event execution pipeline (`SimulatorEvent.execute()`, simulation redo, route handlers), the caller always passes the `Environment` reference.
> - Modalities that need cross-modality access (e.g., `ContactsState` in the future, or `SMSState` checking blocked status) can call `environment.get_state("contacts")` to obtain the `ContactsState` and invoke its lookup methods.
> - The `environment` parameter defaults to `None` for backward compatibility and isolated unit testing. Modalities that *require* it should raise `ValueError` if `None` is passed.
> - Existing modalities (`EmailState`, `SMSState`, `CalendarState`, etc.) accept but do not yet use the parameter. They can be updated incrementally to leverage contacts lookups (e.g., blocked-sender filtering, display name enrichment) without further signature changes.
>
> **Example usage in a future SMSState update**:
> ```python
> def apply_input(self, input_data, environment=None):
>     if input_data.action == "receive_message":
>         if environment:
>             contacts = environment.get_state("contacts")
>             if contacts.is_identifier_blocked(input_data.message_data["from_number"]):
>                 # Silently discard or mark as blocked
>                 return
>     # ... normal processing ...
> ```
>
> **Files changed**: `base_state.py` (abstract signature), all 7 modality state implementations (signature updated), `event.py` and `simulation.py` (callers pass environment), `sms.py` route (direct call passes environment).

## Features Explicitly Excluded

The following features are **not** simulated to maintain simplicity:
- Contact sync protocols (CardDAV, Exchange ActiveSync, Google Contacts API)
- Social media profile integration (auto-fetching profile info)
- Contact sharing (vCard export/import as messages)
- Contact linking/unlinking across accounts (Google, iCloud, Exchange)
- Contact suggestions ("You may know...")
- Duplicate detection and auto-merge
- Emergency contacts designation
- Speed dial assignments
- Contact ringtone/vibration settings
- Contact widget configurations
- SIM card contact storage
- Contact backup and restore protocols
- Contact permissions and access control (per-app)

---

## Implementation Design

### Helper Classes

#### `ContactIdentifier`
Represents a single identifier (phone number, email address, handle) for a contact.

**Attributes:**
- `identifier_type: str` — Type of identifier: `"phone"`, `"email"`, or extensible platform types (future: `"discord"`, `"slack"`, etc.)
- `value: str` — The identifier string (phone number in E.164 format recommended, email address, username/handle)
- `label: Optional[str]` — User-defined label (e.g., `"home"`, `"work"`, `"mobile"`)

**Validation:**
- `identifier_type` must be a non-empty string
- `value` must be a non-empty string
- Phone numbers: E.164 format recommended but not enforced (matches SMS modality's flexibility)
- Email addresses: Basic format validation (contains `@`)

**Methods:**
- `to_dict() -> dict[str, Any]` — Serialize to dictionary for API responses

#### `PostalAddress`
Represents a physical mailing address for a contact.

**Attributes:**
- `street: Optional[str]` — Street address (e.g., "123 Main St")
- `city: Optional[str]` — City name
- `state: Optional[str]` — State, province, or region
- `postal_code: Optional[str]` — ZIP code or postal code
- `country: Optional[str]` — Country name or ISO code
- `label: Optional[str]` — User-defined label (e.g., `"home"`, `"work"`)

**Methods:**
- `to_dict() -> dict[str, Any]` — Serialize to dictionary
- `format_oneline() -> str` — Returns formatted single-line address string

#### `Contact`
Represents a single contact entry in the address book.

**Attributes:**
- `contact_id: str` — Unique identifier (auto-generated UUID)
- `first_name: Optional[str]` — First/given name
- `last_name: Optional[str]` — Last/family name
- `display_name: Optional[str]` — User-overridden display name (e.g., "Mom", "Dr. Smith"). If not set, computed from first/last name.
- `nickname: Optional[str]` — Informal name
- `identifiers: list[ContactIdentifier]` — All phone numbers, emails, and handles for this person
- `company: Optional[str]` — Organization/company name
- `job_title: Optional[str]` — Job title or role
- `addresses: list[PostalAddress]` — Physical addresses (default: empty list)
- `birthday: Optional[date]` — Date of birth (date only)
- `notes: Optional[str]` — Free-text notes
- `photo_url: Optional[str]` — Profile photo URL
- `is_favorite: bool` — Whether this contact is a favorite (default: False)
- `is_blocked: bool` — Whether this contact is blocked (default: False)
- `groups: set[str]` — Group names this contact belongs to (default: empty set)
- `created_at: datetime` — When contact was created (simulator time)
- `updated_at: datetime` — When contact was last modified (simulator time)

**Methods:**
- `to_dict() -> dict[str, Any]` — Serialize to dictionary for API responses
- `get_resolved_display_name() -> str` — Returns `display_name` if set, else computed `"{first_name} {last_name}"`, else `nickname`, else first identifier value, else `"Unknown"`
- `get_phone_numbers() -> list[str]` — Returns all phone-type identifier values
- `get_email_addresses() -> list[str]` — Returns all email-type identifier values
- `has_identifier(identifier_type: str, value: str) -> bool` — Check if contact has a specific identifier
- `add_identifier(identifier: ContactIdentifier) -> None` — Add identifier, reject duplicates
- `remove_identifier(identifier_type: str, value: str) -> bool` — Remove identifier, return whether found

---

## Contacts Input/State Models

### Operation Type

```python
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
```

### `ContactsInput` (models/modalities/contacts_input.py)

The event payload for contact operations. Uses an operation-based design where different
attributes are required depending on the operation type. All data fields are flat,
explicitly-typed `Optional` fields on the model (following the `EmailInput` pattern).

**Attributes:**
- `modality_type: Literal["contacts"]` — Always `"contacts"` (frozen)
- `timestamp: datetime` — When this input event occurs (simulator time)
- `input_id: str` — Unique identifier for this input (auto-generated UUID)
- `operation: ContactsOperation` — Type of contact operation to perform:
  - `create_contact` — Add a new contact
  - `update_contact` — Modify an existing contact's fields
  - `delete_contact` — Remove a contact from the database
  - `block_contact` — Block a contact (all identifiers)
  - `unblock_contact` — Unblock a contact
  - `favorite_contact` — Mark a contact as favorite
  - `unfavorite_contact` — Remove favorite status
  - `add_to_group` — Add a contact to a group
  - `remove_from_group` — Remove a contact from a group
  - `merge_contacts` — Merge two contacts into one

**Contact identity fields** (used by operations that target existing contacts):
- `contact_id: Optional[str]` — Target contact ID. Required for: `update_contact`, `delete_contact`, `block_contact`, `unblock_contact`, `favorite_contact`, `unfavorite_contact`, `add_to_group`, `remove_from_group`.

**Contact data fields** (used by `create_contact` and `update_contact`):
- `first_name: Optional[str]` — First/given name
- `last_name: Optional[str]` — Last/family name
- `display_name: Optional[str]` — User-overridden display name (e.g., "Mom")
- `nickname: Optional[str]` — Informal name
- `identifiers: Optional[list[ContactIdentifier]]` — Identifiers for create (required, at least one) or full-replace for update
- `add_identifiers: Optional[list[ContactIdentifier]]` — Identifiers to add (update only, additive)
- `remove_identifiers: Optional[list[ContactIdentifier]]` — Identifiers to remove (update only, subtractive)
- `company: Optional[str]` — Organization/company name
- `job_title: Optional[str]` — Job title or role
- `addresses: Optional[list[PostalAddress]]` — Physical addresses (full replace on create/update)
- `add_addresses: Optional[list[PostalAddress]]` — Addresses to add (update only)
- `remove_addresses: Optional[list[PostalAddress]]` — Addresses to remove (update only)
- `birthday: Optional[date]` — Date of birth
- `notes: Optional[str]` — Free-text notes
- `photo_url: Optional[str]` — Profile photo URL
- `is_favorite: Optional[bool]` — Whether this contact is a favorite
- `is_blocked: Optional[bool]` — Whether this contact is blocked
- `groups: Optional[set[str]]` — Group set (full replace on create)
- `add_groups: Optional[set[str]]` — Groups to add (update only)
- `remove_groups: Optional[set[str]]` — Groups to remove (update only)

**Group operation fields** (used by `add_to_group`, `remove_from_group`):
- `group_name: Optional[str]` — Name of the group to add to / remove from

**Merge operation fields** (used by `merge_contacts`):
- `primary_contact_id: Optional[str]` — Contact to keep (absorbs data from secondary)
- `secondary_contact_id: Optional[str]` — Contact to merge into primary (deleted after merge)

**Methods:**
- `validate_input()` — Validates operation-specific required fields; ensures `create_contact` has at least one identifier; validates identifier formats; ensures `contact_id` is present for operations that target existing contacts
- `get_affected_entities() -> list[str]` — Returns `[contact_id]` for the contact(s) affected. For `merge_contacts`, returns both `primary_contact_id` and `secondary_contact_id`.
- `get_summary() -> str` — Human-readable summary (e.g., `"Create contact: Alice Smith (+15551234567)"`)
- `should_merge_with(other: ContactsInput) -> bool` — Returns `False` (contact events are discrete)

**Operation-Specific Required Fields:**

| Operation | Required Fields | Optional Fields Used |
|-----------|----------------|---------------------|
| `create_contact` | `identifiers` (≥1) | `first_name`, `last_name`, `display_name`, `nickname`, `company`, `job_title`, `addresses`, `birthday`, `notes`, `photo_url`, `is_favorite`, `is_blocked`, `groups` |
| `update_contact` | `contact_id` | Any contact data field; `add_identifiers`/`remove_identifiers` for additive edits; `add_addresses`/`remove_addresses`; `add_groups`/`remove_groups` |
| `delete_contact` | `contact_id` | — |
| `block_contact` | `contact_id` | — |
| `unblock_contact` | `contact_id` | — |
| `favorite_contact` | `contact_id` | — |
| `unfavorite_contact` | `contact_id` | — |
| `add_to_group` | `contact_id`, `group_name` | — |
| `remove_from_group` | `contact_id`, `group_name` | — |
| `merge_contacts` | `primary_contact_id`, `secondary_contact_id` | — |

**Design Decisions:**
- **Operation-based with flat typed fields**: Follows the `EmailInput` pattern — a single input class with a `Literal` `operation` discriminator and all data as flat, explicitly-typed `Optional` fields. This provides type safety, IDE autocompletion, and schema validation that `dict[str, Any]` cannot.
- **Additive/subtractive updates**: `update_contact` supports both full-replace (`identifiers`, `addresses`, `groups`) and additive/subtractive (`add_identifiers`/`remove_identifiers`, `add_addresses`/`remove_addresses`, `add_groups`/`remove_groups`) update styles. The additive/subtractive pattern is safer for partial updates and prevents accidental data loss.
- **Merge semantics**: `merge_contacts` combines two contacts — primary keeps its fields where both have values; secondary's unique identifiers, addresses, and groups are added to primary; secondary is deleted.

### `ContactsState` (models/modalities/contacts_state.py)

Tracks all contacts, groups, and provides cross-modality lookup services.

**Attributes:**
- `modality_type: str` — Always `"contacts"`
- `last_updated: datetime` — When state was last modified
- `update_count: int` — Number of inputs applied
- `contacts: dict[str, Contact]` — All contacts keyed by `contact_id`

**Derived/Computed State (not stored, computed on access):**
- Groups: Derived from union of all contacts' `groups` sets
- Blocked identifiers index: Built from blocked contacts' identifiers for fast lookup
- Identifier-to-contact index: Built for fast reverse lookup

**Methods:**
- `apply_input(input_data: ContactsInput, environment: Optional[Environment] = None)` — Processes contact operation and updates state
  - Handles all operation types: create_contact, update_contact, delete_contact, block_contact, unblock_contact, favorite_contact, unfavorite_contact, add_to_group, remove_from_group, merge_contacts
  - Validates contact_id exists for update/delete/block/unblock operations
  - Prevents duplicate identifiers across contacts (same phone number can't belong to two contacts)
- `get_snapshot() -> dict[str, Any]` — Returns complete state for API responses
  - Includes all contacts serialized, group list, blocked count, favorites count
- `validate_state() -> list[str]` — Checks state consistency
  - Verifies no duplicate identifiers across contacts
  - Validates all contacts have at least one identifier
  - Checks group name consistency
- `query(query_params: dict[str, Any]) -> dict[str, Any]` — Search and filter contacts
  - Returns dictionary with `contacts` (list of contact dicts), `count`, and `query_params`
  - Supports: `search_text`, `group`, `is_favorite`, `is_blocked`, `has_phone`, `has_email`, `identifier_type`, `identifier_value`, `limit`, `offset`
- `clear()` — Reset to empty state (no contacts)
- `create_undo_data(input_data: ContactsInput) -> dict[str, Any]` — Capture undo data before applying input
- `apply_undo(undo_data: dict[str, Any])` — Reverse a previous input application

**Cross-Modality Lookup Methods:**
- `get_display_name(identifier_type: str, value: str) -> Optional[str]` — Resolve an identifier to a display name. Returns `None` if not found.
- `is_identifier_blocked(value: str) -> bool` — Check if any blocked contact has this identifier (checks all types). Returns `False` if identifier not found in any contact.
- `find_contact_by_identifier(identifier_type: str, value: str) -> Optional[Contact]` — Full contact lookup by identifier.
- `find_contacts_by_group(group_name: str) -> list[Contact]` — Get all contacts in a group.
- `get_all_groups() -> set[str]` — Get the set of all group names across all contacts.
- `get_favorites() -> list[Contact]` — Get all favorited contacts.
- `get_blocked_contacts() -> list[Contact]` — Get all blocked contacts.

**Design Decisions:**

1. **Contact Storage**:
   - Contacts stored in flat dictionary keyed by `contact_id` for fast lookup
   - Identifier-based lookups scan all contacts (acceptable for typical contact list sizes of hundreds to low thousands)
   - For performance with very large contact lists, an in-memory index could be added later

2. **Identifier Uniqueness**:
   - A given identifier (type + value pair) can only belong to one contact
   - Creating a contact with an identifier that already exists on another contact raises an error
   - `merge_contacts` handles the case where you want to combine contacts that share identifiers

3. **Groups Are Implicit**:
   - No separate `Group` model — groups are just string labels on contacts
   - `get_all_groups()` computes the group list dynamically from all contacts
   - A group "disappears" when no contacts belong to it
   - This keeps the model simple and avoids group-contact relationship management

4. **Blocking Is Per-Contact**:
   - The `is_blocked` flag on `Contact` blocks all identifiers for that person
   - `is_identifier_blocked()` searches all blocked contacts' identifiers
   - This models how real phone contact blocking works — you block a person, not just a number

5. **Display Name Resolution**:
   - `get_display_name()` returns `Contact.get_resolved_display_name()` if found
   - Callers (SMS, Email, Calendar) fall back to raw identifiers when `None` is returned
   - This keeps the Contacts modality as an optional enhancement, not a hard dependency

6. **No Separate "Owner" Contact**:
   - The simulated user's own contact info is tracked by other modalities (`SMSState.user_phone_number`, `EmailState.user_email_address`)
   - Contacts represent _other people_ in the user's address book
   - The user's own info could be added as a special contact later if needed

---

## Undo Design

Following the patterns established in [MODALITY_UNDO_NOTES.md](../../models/MODALITY_UNDO_NOTES.md):

### Additive Operations (store minimal data)
- **create_contact**: Store `{"undo_type": "delete_contact", "contact_id": "..."}`
- **add_to_group**: Store `{"undo_type": "remove_from_group", "contact_id": "...", "group_name": "..."}`
- **favorite_contact**: Store `{"undo_type": "unfavorite_contact", "contact_id": "..."}`

### Destructive Operations (store full previous state)
- **delete_contact**: Store `{"undo_type": "restore_contact", "contact": {... full Contact dict ...}}`
- **update_contact**: Store `{"undo_type": "restore_fields", "contact_id": "...", "previous_fields": {... only changed fields ...}}`
- **merge_contacts**: Store `{"undo_type": "unmerge_contacts", "primary_before": {... full ...}, "secondary": {... full ...}}`
- **block_contact**: Store `{"undo_type": "unblock_contact", "contact_id": "...", "was_blocked": false}`
- **unblock_contact**: Store `{"undo_type": "block_contact", "contact_id": "...", "was_blocked": true}`

### All Undo Data Includes
```python
"state_previous_update_count": self.update_count,
"state_previous_last_updated": self.last_updated.isoformat(),
```

---

## API Routes

### Planned Endpoints

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/contacts/state` | GET | `contacts:state` | Get complete contacts state |
| `/contacts/query` | POST | `contacts:query` | Query/search contacts with filters |
| `/contacts/create` | POST | `contacts:create` | Create a new contact |
| `/contacts/update` | POST | `contacts:update` | Update an existing contact |
| `/contacts/delete` | POST | `contacts:delete` | Delete a contact |
| `/contacts/block` | POST | `contacts:block` | Block a contact |
| `/contacts/unblock` | POST | `contacts:unblock` | Unblock a contact |
| `/contacts/favorite` | POST | `contacts:favorite` | Mark contact as favorite |
| `/contacts/unfavorite` | POST | `contacts:unfavorite` | Unfavorite a contact |
| `/contacts/group/add` | POST | `contacts:group:add` | Add contact to group |
| `/contacts/group/remove` | POST | `contacts:group:remove` | Remove contact from group |
| `/contacts/merge` | POST | `contacts:merge` | Merge two contacts |

### Compact State (`?compact=true`)

Returns a compact, LLM-context-optimized view:
- Total contact count
- Favorite count
- Blocked count
- Group list with member counts
- Recently added/updated contacts (names only)

---

## API Usage Patterns

### Create a Contact
```json
POST /events/immediate
{
  "modality": "contacts",
  "data": {
    "operation": "create_contact",
    "first_name": "Alice",
    "last_name": "Smith",
    "identifiers": [
      {"identifier_type": "phone", "value": "+15551234567", "label": "mobile"},
      {"identifier_type": "email", "value": "alice@example.com", "label": "work"}
    ],
    "company": "Acme Corp",
    "job_title": "Engineer",
    "groups": ["Work", "Friends"]
  }
}
```

### Update a Contact
```json
POST /events/immediate
{
  "modality": "contacts",
  "data": {
    "operation": "update_contact",
    "contact_id": "abc-123",
    "job_title": "Senior Engineer",
    "add_identifiers": [
      {"identifier_type": "email", "value": "alice.smith@newjob.com", "label": "work"}
    ],
    "add_groups": ["Book Club"]
  }
}
```

### Block a Contact
```json
POST /events/immediate
{
  "modality": "contacts",
  "data": {
    "operation": "block_contact",
    "contact_id": "abc-123"
  }
}
```

### Merge Two Contacts
```json
POST /events/immediate
{
  "modality": "contacts",
  "data": {
    "operation": "merge_contacts",
    "primary_contact_id": "abc-123",
    "secondary_contact_id": "def-456"
  }
}
```

### Query Contacts
```bash
# Get all contacts in a group
POST /contacts/query
{
  "group": "Work",
  "limit": 50
}

# Search by name
POST /contacts/query
{
  "search_text": "alice",
  "is_blocked": false
}

# Find contact by phone number
POST /contacts/query
{
  "identifier_type": "phone",
  "identifier_value": "+15551234567"
}
```

### Get Contact State
```
GET /contacts/state
GET /contacts/state?compact=true
```

---

## Testing Scenarios

The Contacts modality enables testing various realistic scenarios:

1. **Basic CRUD**: Create, read, update, delete contacts
2. **Contact Lookup**: Resolve display names from phone numbers and email addresses
3. **Blocking**: Block contacts and verify cross-modality behavior (blocked SMS/email)
4. **Group Management**: Organize contacts into groups, query by group
5. **Favorites**: Mark/unmark favorites, query favorites
6. **Merge Conflicts**: Merge contacts with overlapping identifiers
7. **Cross-Modality Name Resolution**: SMS/Email display names populated from Contacts
8. **Missing Contacts**: Graceful fallback when identifiers don't match any contact
9. **Bulk Contact Setup**: Scenario loading with pre-populated contact databases
10. **Contact-Driven Filtering**: Filter SMS conversations or emails by contact group
