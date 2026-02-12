# Contacts Modality Implementation Plan

Implementation plan for the Contacts modality as specified in `docs/models/modalities/CONTACTS.md`. This is the first modality in UES that other modalities explicitly depend on, serving as the authoritative source for people-related metadata.

**Reference Document**: `docs/models/modalities/CONTACTS.md`
**Pattern Reference**: Follows the Email/SMS modality patterns (operation-based input, flat typed fields)

---

## Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Models (Foundation) | **COMPLETE** |
| 2 | API Routes | **COMPLETE** |
| 3 | Python Client Library | Not Started |
| 4 | Web UI | Not Started |
| 5 | Documentation Updates | Not Started |
| 6 | Testing | **IN PROGRESS** (6.1–6.4 complete) |
| 7 | Cross-Modality Integration | Deferred |

**Test baseline after Phase 1**: 3,720 tests passing (zero regressions)
**Test baseline after Phase 2**: 3,720 tests passing (zero regressions — no new tests added; existing hardcoded counts updated)
**Test baseline after Phase 6.1–6.4**: 4,020 tests passing (+300 new tests, zero regressions)

---

## Phase 1: Models (Foundation) — COMPLETE

The models are the foundation everything else builds on. Implement these first so that registry, API, client, and tests can all reference them.

### 1.1 Helper Classes — DONE

**File**: `src/ues/models/modalities/contacts_input.py` (top of file, before `ContactsInput`)

Created these Pydantic `BaseModel` helper classes:

- **`ContactIdentifier`** — `identifier_type: str`, `value: str`, `label: Optional[str] = None`; validators for non-empty type/value and email `@` check; `to_dict()` method
- **`PostalAddress`** — All optional address fields; `to_dict()` and `format_oneline()` methods
- **`Contact`** — Defined in `contacts_state.py` (state entity pattern). 17 fields including UUID `contact_id`, names, identifiers list, org, addresses, birthday, notes, photo_url, favorites/blocked flags, groups set, timestamps. Methods: `get_resolved_display_name()` (5-level fallback), `get_phone_numbers()`, `get_email_addresses()`, `has_identifier()`, `add_identifier()`, `remove_identifier()`, `to_dict()`
- **`ContactsOperation`** — `Literal` of 10 operations as planned

### 1.2 `ContactsInput` — DONE

**File**: `src/ues/models/modalities/contacts_input.py`

Implemented as planned: extends `ModalityInput` with frozen `modality_type`, `operation` discriminator, and 23 flat optional data fields. All four abstract methods implemented — `validate_input()` dispatches to 10 private `_validate_*()` methods, `get_affected_entities()` returns contact IDs (both for merge), `get_summary()` returns human-readable strings, `should_merge_with()` returns `False`.

### 1.3 `ContactsState` — DONE

**File**: `src/ues/models/modalities/contacts_state.py`

Implemented as planned. All abstract methods working:
- `apply_input()` dispatches to 10 private `_apply_*()` handlers; includes identifier uniqueness validation across contacts
- `get_snapshot()` returns contacts, groups, counts (total, favorites, blocked)
- `validate_state()` checks for duplicate identifiers and contacts without identifiers
- `query()` supports all 8 filter types + `limit`/`offset` pagination
- `clear()` resets state
- `create_undo_data()` / `apply_undo()` implemented for all 10 operations

All 7 cross-modality lookup methods implemented: `get_display_name()`, `is_identifier_blocked()`, `find_contact_by_identifier()`, `find_contacts_by_group()`, `get_all_groups()`, `get_favorites()`, `get_blocked_contacts()`.

Optional overrides: `summary` property and `get_compact_snapshot()` both implemented.

**Implementation note**: `_apply_create_contact()` uses `input_data.contact_id or str(uuid4())` to respect IDs pre-set by `create_undo_data()` (matching EmailState undo pattern).

### 1.4 Registry Registration — DONE

**File**: `src/ues/models/registry.py`

Added under "Priority 3 Modalities (Implemented)" comment in `_register_default_modalities()`. Updated `tests/models/test_registry.py` — 4 expected modality lists updated from 7 to 8 entries (added `"contacts"`).

### 1.5 Modality `__init__.py` — DONE

**File**: `src/ues/models/modalities/__init__.py`

Added imports and `__all__` entries for `ContactIdentifier`, `ContactsInput`, `ContactsOperation`, `PostalAddress` (from `contacts_input`), `Contact`, `ContactsState` (from `contacts_state`) under "Priority 3 Modalities (Implemented)" section.

---

## Phase 2: API Routes — COMPLETE

### 2.1 Permissions — DONE

**File**: `src/ues/api/auth.py`

Added 12 permissions to `Permissions` class under "Contacts (/contacts)" comment:
`CONTACTS_STATE`, `CONTACTS_QUERY`, `CONTACTS_CREATE`, `CONTACTS_UPDATE`, `CONTACTS_DELETE`, `CONTACTS_BLOCK`, `CONTACTS_UNBLOCK`, `CONTACTS_FAVORITE`, `CONTACTS_UNFAVORITE`, `CONTACTS_GROUP_ADD`, `CONTACTS_GROUP_REMOVE`, `CONTACTS_MERGE`.

### 2.2 WebSocket Events — DONE

**File**: `src/ues/api/websocket.py`

Added 6 event types to `WSEventType` enum: `CONTACT_CREATED`, `CONTACT_UPDATED`, `CONTACT_DELETED`, `CONTACT_BLOCKED`, `CONTACT_UNBLOCKED`, `CONTACT_MERGED`.

### 2.3 Route Handler — DONE

**File**: `src/ues/api/routes/contacts.py` (NEW, ~900 lines)

Created router with `prefix="/contacts"`, `tags=["contacts"]`.

**Request models** (11, defined in route file per convention):
- `ContactIdentifierRequest`, `PostalAddressRequest` — sub-models for request payloads
- `CreateContactRequest`, `UpdateContactRequest`, `DeleteContactRequest`
- `BlockContactRequest`, `UnblockContactRequest`
- `FavoriteContactRequest`, `UnfavoriteContactRequest`
- `AddToGroupRequest`, `RemoveFromGroupRequest`
- `MergeContactsRequest`
- `ContactsQueryRequest` — mirrors query params from design doc

**Response models** (3):
- `ContactsStateResponse` — full state (supports `?compact=true` query param)
- `ContactsCompactStateResponse` — compact view
- `ContactsQueryResponse` — query result with contacts list, count, and query_params echo

**Helper functions**:
- `_get_contacts_state()` — extract typed `ContactsState` from engine
- `_identifiers_to_model()` — convert request identifiers to domain `ContactIdentifier` objects
- `_addresses_to_model()` — convert request addresses to domain `PostalAddress` objects

**Endpoints** (12 total, all implemented per design doc table):

| Endpoint | Method | Permission | Handler |
|----------|--------|------------|---------|
| `/contacts/state` | GET | `CONTACTS_STATE` | `get_contacts_state()` |
| `/contacts/query` | POST | `CONTACTS_QUERY` | `query_contacts()` |
| `/contacts/create` | POST | `CONTACTS_CREATE` | `create_contact()` |
| `/contacts/update` | POST | `CONTACTS_UPDATE` | `update_contact()` |
| `/contacts/delete` | POST | `CONTACTS_DELETE` | `delete_contact()` |
| `/contacts/block` | POST | `CONTACTS_BLOCK` | `block_contact()` |
| `/contacts/unblock` | POST | `CONTACTS_UNBLOCK` | `unblock_contact()` |
| `/contacts/favorite` | POST | `CONTACTS_FAVORITE` | `favorite_contact()` |
| `/contacts/unfavorite` | POST | `CONTACTS_UNFAVORITE` | `unfavorite_contact()` |
| `/contacts/group/add` | POST | `CONTACTS_GROUP_ADD` | `add_to_group()` |
| `/contacts/group/remove` | POST | `CONTACTS_GROUP_REMOVE` | `remove_from_group()` |
| `/contacts/merge` | POST | `CONTACTS_MERGE` | `merge_contacts()` |

Each action endpoint follows the standard pattern:
1. Gets engine from `SimulationEngineDep`
2. Gets `ContactsState` via `_get_contacts_state(engine)`
3. Builds input data dict, calls `create_immediate_event(engine, "contacts", data, priority)` from `ues.api.utils`
4. Broadcasts WebSocket event via `broadcast_event()` with appropriate `WSEventType`
5. Returns `ModalityActionResponse` with event details

**Implementation note**: Update endpoint builds the data dict dynamically — only includes non-None fields from the request, and converts additive/subtractive list fields (e.g., `add_identifiers`, `remove_groups`) to their model representations.

### 2.4 Route Registration — DONE

**File**: `src/ues/main.py`

Added `from ues.api.routes import contacts as contacts_routes` and `app.include_router(contacts_routes.router)`, placed alphabetically between calendar and location routers.

### 2.5 Engine Initialization — DONE

**File**: `src/ues/api/dependencies.py`

Added `ContactsState` import and `initial_contacts = ContactsState(last_updated=now)` in `initialize_simulation_engine()`. Added `"contacts": initial_contacts` to the `modality_states` dict.

### 2.6 Environment Compact Snapshot — DONE

**File**: `src/ues/models/environment.py`

Added contacts section to `get_compact_snapshot_text()` between SMS and Chat, rendering:
- Summary line: total contacts, favorites count, blocked count, groups count
- Group names with member counts
- Recently updated contacts with 👤 emoji prefix and relative update times

### 2.7 Test Fixture & Hardcoded Count Updates — DONE

These updates were not in the original plan but were necessary to keep all 3,720 existing tests passing:

**Test fixture updates**:
- `tests/fixtures/api.py` — Added `ContactsState` import and initialization in `fresh_engine` fixture
- `tests/fixtures/core/environments.py` — Added `ContactsState` to `FULL_ENVIRONMENT`

**Hardcoded modality count updates** (7→8 across 7 test files, 10+ locations):
- `tests/api/simulation/test_simulation_clear.py` — `modalities_cleared == 8`
- `tests/models/test_environment.py` — `FULL_ENVIRONMENT` modality count assertion
- `tests/models/test_environment_serialization.py` — 3 places (count, expected list, restored count)
- `tests/models/test_scenario.py` — 2 places (modality_count, list_modalities length)
- `tests/api/environment/test_modality_listing.py` — expected modality set + count
- `tests/api/environment/test_environment_state.py` — 2 expected modality sets

---

## Phase 3: Python Client Library

### 3.1 Client Sub-client

**File**: `src/ues/client/_contacts.py`

**Client-side response models** (mirroring server models):
- `ContactIdentifier` — mirrors server `ContactIdentifier`
- `PostalAddress` — mirrors server `PostalAddress`
- `Contact` — mirrors server `Contact`
- `ContactsStateResponse` — mirrors server response
- `ContactsCompactStateResponse` — compact view response
- `ContactsQueryResponse` — query result response

**Sync client**: `ContactsClient(BaseClient)`
- `_BASE_PATH = "/contacts"`
- Methods: `get_state()`, `query()`, `create()`, `update()`, `delete()`, `block()`, `unblock()`, `favorite()`, `unfavorite()`, `add_to_group()`, `remove_from_group()`, `merge()`

**Async client**: `AsyncContactsClient(AsyncBaseClient)`
- Mirrors every sync method with `async` versions

### 3.2 Client Integration

**File**: `src/ues/client/client.py`

In both `UESClient` and `AsyncUESClient`:
1. Import `ContactsClient` / `AsyncContactsClient`
2. Add `self._contacts: ContactsClient | None = None` in `__init__()`
3. Add lazy property:
   ```python
   @property
   def contacts(self) -> ContactsClient:
       if self._contacts is None:
           self._contacts = ContactsClient(self._http)
       return self._contacts
   ```

---

## Phase 4: Web UI

### 4.1 Contacts Viewer Component

**Directory**: `webapp/src/components/modalities/contacts/`

Files to create:
- `types.ts` — TypeScript interfaces (`ContactIdentifier`, `PostalAddress`, `Contact`, `ContactsState`)
- `ContactsViewer.tsx` — main component using `useModalityState<ContactsState>('contacts', 3000)`
- `ContactList.tsx` — sortable/filterable list of contacts
- `ContactDetail.tsx` — expanded view of a single contact
- `ContactsToolbar.tsx` — search bar, group filter, favorites toggle
- `ContactsStatusBar.tsx` — summary counts
- `index.ts` — re-exports

### 4.2 Modality Index Update

**File**: `webapp/src/components/modalities/index.ts`

Add re-export for contacts components.

---

## Phase 5: Documentation Updates

### 5.1 API Access Control Docs

**File**: `docs/api/API_ACCESS_CONTROL.md`

Add contacts permissions table with all 12 permissions.

### 5.2 Modality Routes Docs

**File**: `docs/api/MODALITY_ROUTES.md`

Document contacts endpoint patterns, request/response examples.

### 5.3 TODO.md

**File**: `TODO.md`

- Move Contacts from "Priority 3 Modalities (Future)" to completed
- Update test count

### 5.4 Client Quick Reference

**File**: `docs/client/CLIENT_QUICK_REFERENCE.md`

Add contacts client methods and usage examples.

---

## Phase 6: Testing — IN PROGRESS

Testing is organized into three layers: model unit tests, API integration tests, and client sync/round-trip tests. Each layer is described below with expected test coverage.

### Bugs Found and Fixed During Testing

Comprehensive testing surfaced three implementation bugs in Phase 2 code:

1. **Route bug — `get_contacts_state()` KeyError** (`src/ues/api/routes/contacts.py` line 513): `snapshot["total_count"]` referenced a key that doesn't exist; `get_snapshot()` returns `"total_contacts"`. Fixed to `snapshot["total_contacts"]`.
2. **Route bug — `query_contacts()` swapped keys** (`src/ues/api/routes/contacts.py` lines 560-561): `result["total_count"]` and `result["count"]` were using wrong key names. `query()` returns `"count"` (total matching) and `"returned_count"` (after pagination). Fixed both references.
3. **Model bug — `get_compact_snapshot()` missing fields** (`src/ues/models/modalities/contacts_state.py`): The compact snapshot dict was missing `modality_type`, `last_updated`, `update_count`, and `summary` fields required by the `ContactsCompactStateResponse` response model and the environment's `get_compact_snapshot_text()` formatter. Added all four fields.

### 6.1 Test Fixtures — DONE

**File**: `tests/fixtures/modalities/contacts.py` (391 lines)

Factory functions:
- `create_contact_identifier(identifier_type, value, label) -> ContactIdentifier`
- `create_postal_address(**kwargs) -> PostalAddress`
- `create_contact(contact_id, first_name, last_name, identifiers, ...) -> Contact`
- `create_contacts_input(operation, timestamp, **kwargs) -> ContactsInput`
- `create_contacts_state(last_updated, contacts, **kwargs) -> ContactsState`

Pre-built examples:
- `SIMPLE_CREATE` — create contact with phone + email
- `SIMPLE_UPDATE` — update contact name
- `SIMPLE_DELETE` — delete by contact_id
- `BLOCK_CONTACT` — block operation
- `ADD_TO_GROUP` — add to group operation
- `MERGE_CONTACTS` — merge two contacts
- `SAMPLE_CONTACT_ALICE` — pre-built Contact object
- `SAMPLE_CONTACT_BOB` — pre-built Contact object

Pytest fixtures:
- `contact_identifier`, `postal_address`, `sample_contact_alice`, `sample_contact_bob`
- `contacts_state_empty`, `contacts_state_with_contacts`
- `contacts_input_create`, `contacts_input_update`, `contacts_input_delete`

**File**: `tests/conftest.py` — Added `"tests.fixtures.modalities.contacts"` to `pytest_plugins` list.

**File**: `tests/fixtures/api.py` — Already updated in Phase 2.7.

### 6.2 Model Unit Tests — `ContactsInput` — DONE

**File**: `tests/models/test_contacts_input.py` (78 tests passing)

#### General `ModalityInput` Pattern Tests
These tests verify the base class contract and should be replicated for all modalities:

| Test | Description |
|------|-------------|
| `test_instantiation_minimal` | Create with only required fields (operation + minimal data), verify defaults |
| `test_instantiation_modality_type_frozen` | Verify `modality_type` is always `"contacts"` |
| `test_instantiation_auto_input_id` | Verify auto-generated UUID for `input_id` |
| `test_instantiation_timestamp_timezone` | Verify timezone-aware timestamp validation |
| `test_get_summary_returns_string` | Verify `get_summary()` returns non-empty string for each operation |
| `test_should_merge_with_returns_false` | Verify `should_merge_with()` always returns `False` |
| `test_serialization_roundtrip` | `model_dump()` → `ContactsInput(**data)` preserves all fields |

#### `ContactIdentifier` Helper Tests

| Test | Description |
|------|-------------|
| `test_contact_identifier_creation` | Create with type, value, optional label |
| `test_contact_identifier_validation_empty_type` | Reject empty `identifier_type` |
| `test_contact_identifier_validation_empty_value` | Reject empty `value` |
| `test_contact_identifier_email_format` | Validate email contains `@` when type is `"email"` |
| `test_contact_identifier_to_dict` | Verify serialization |

#### `PostalAddress` Helper Tests

| Test | Description |
|------|-------------|
| `test_postal_address_creation` | Create with all fields |
| `test_postal_address_all_optional` | Create with no fields |
| `test_postal_address_format_oneline` | Verify formatted string output |
| `test_postal_address_to_dict` | Verify serialization |

#### Operation-Specific Validation Tests

| Test | Description |
|------|-------------|
| `test_validate_create_contact_requires_identifiers` | Reject create without identifiers |
| `test_validate_create_contact_requires_nonempty_identifiers` | Reject create with empty identifiers list |
| `test_validate_create_contact_with_all_fields` | Accept create with full data |
| `test_validate_update_contact_requires_contact_id` | Reject update without contact_id |
| `test_validate_update_contact_with_additive_fields` | Accept update with `add_identifiers`, `add_groups` |
| `test_validate_delete_contact_requires_contact_id` | Reject delete without contact_id |
| `test_validate_block_contact_requires_contact_id` | Reject block without contact_id |
| `test_validate_unblock_contact_requires_contact_id` | Reject unblock without contact_id |
| `test_validate_favorite_contact_requires_contact_id` | Reject favorite without contact_id |
| `test_validate_unfavorite_contact_requires_contact_id` | Reject unfavorite without contact_id |
| `test_validate_add_to_group_requires_contact_id_and_group` | Reject without both fields |
| `test_validate_remove_from_group_requires_contact_id_and_group` | Reject without both fields |
| `test_validate_merge_requires_both_ids` | Reject merge without primary or secondary |
| `test_validate_merge_rejects_same_ids` | Reject merge when primary == secondary |

#### `get_affected_entities()` Tests

| Test | Description |
|------|-------------|
| `test_affected_entities_single_contact` | Returns `[contact_id]` for most operations |
| `test_affected_entities_merge` | Returns both `[primary_id, secondary_id]` |
| `test_affected_entities_create` | Returns empty or generated ID |

#### `get_summary()` Tests

| Test | Description |
|------|-------------|
| `test_summary_create_with_name` | Includes name and identifier |
| `test_summary_update` | Includes contact_id |
| `test_summary_delete` | Includes contact_id |
| `test_summary_block_unblock` | Includes contact_id |
| `test_summary_group_operations` | Includes contact_id and group_name |
| `test_summary_merge` | Includes both contact IDs |

### 6.3 Model Unit Tests — `ContactsState` — DONE

**File**: `tests/models/test_contacts_state.py` (137 tests passing)

Organized into 15 test classes covering all operations, cross-modality lookups, queries, snapshots, validation, undo, and clear. Tests verify *desired behavior* — this approach directly surfaced the compact snapshot bug (missing fields in `get_compact_snapshot()`).

#### General `ModalityState` Pattern Tests

| Test | Description |
|------|-------------|
| `test_instantiation_defaults` | Empty state has no contacts, update_count=0 |
| `test_instantiation_modality_type` | `modality_type` is `"contacts"` |
| `test_get_snapshot_empty` | Snapshot of empty state has expected structure |
| `test_validate_state_empty` | Empty state passes validation |
| `test_clear_resets_state` | `clear()` removes all contacts |
| `test_apply_input_increments_update_count` | Each `apply_input()` bumps `update_count` |
| `test_apply_input_updates_last_updated` | `last_updated` advances with input timestamp |

#### `Contact` Sub-model Tests

| Test | Description |
|------|-------------|
| `test_contact_creation` | Create with all fields |
| `test_contact_auto_uuid` | Auto-generated `contact_id` |
| `test_contact_resolved_display_name_explicit` | Returns `display_name` when set |
| `test_contact_resolved_display_name_from_names` | Returns `"First Last"` when display_name is None |
| `test_contact_resolved_display_name_nickname_fallback` | Falls back to nickname |
| `test_contact_resolved_display_name_identifier_fallback` | Falls back to first identifier value |
| `test_contact_resolved_display_name_unknown` | Returns `"Unknown"` for empty contact |
| `test_contact_get_phone_numbers` | Returns only phone-type identifier values |
| `test_contact_get_email_addresses` | Returns only email-type identifier values |
| `test_contact_has_identifier` | True when identifier exists, False otherwise |
| `test_contact_add_identifier` | Adds new identifier |
| `test_contact_add_identifier_duplicate_rejected` | Rejects duplicate identifier |
| `test_contact_remove_identifier` | Removes and returns True |
| `test_contact_remove_identifier_not_found` | Returns False when not found |
| `test_contact_to_dict` | Full serialization |
| `test_contact_timezone_aware_datetimes` | Validates timezone awareness |

#### Create Contact Tests

| Test | Description |
|------|-------------|
| `test_create_contact_basic` | Create with one identifier, verify in state |
| `test_create_contact_full_data` | Create with all fields populated |
| `test_create_contact_multiple_identifiers` | Phone + email + custom type |
| `test_create_contact_with_addresses` | Include postal addresses |
| `test_create_contact_with_groups` | Include group memberships |
| `test_create_contact_with_birthday` | Include date-only birthday |
| `test_create_contact_duplicate_identifier_rejected` | Reject if identifier exists on another contact |
| `test_create_contact_assigns_uuid` | Generated contact gets a UUID |
| `test_create_contact_sets_timestamps` | `created_at` and `updated_at` set to input timestamp |

#### Update Contact Tests

| Test | Description |
|------|-------------|
| `test_update_contact_name_fields` | Update first_name, last_name, display_name |
| `test_update_contact_add_identifiers` | Additive identifier update |
| `test_update_contact_remove_identifiers` | Subtractive identifier update |
| `test_update_contact_replace_identifiers` | Full-replace identifiers |
| `test_update_contact_add_addresses` | Additive address update |
| `test_update_contact_remove_addresses` | Subtractive address update |
| `test_update_contact_add_groups` | Additive group update |
| `test_update_contact_remove_groups` | Subtractive group update |
| `test_update_contact_scalar_fields` | Update company, job_title, notes, photo_url, birthday |
| `test_update_contact_not_found` | Raise error for nonexistent contact_id |
| `test_update_contact_updates_timestamp` | `updated_at` advances |
| `test_update_contact_duplicate_identifier_rejected` | Reject adding identifier that exists on another contact |

#### Delete Contact Tests

| Test | Description |
|------|-------------|
| `test_delete_contact` | Remove from state |
| `test_delete_contact_not_found` | Raise error for nonexistent contact_id |
| `test_delete_contact_removes_from_groups` | Group disappears if sole member |

#### Block/Unblock Tests

| Test | Description |
|------|-------------|
| `test_block_contact` | Sets `is_blocked = True` |
| `test_unblock_contact` | Sets `is_blocked = False` |
| `test_block_already_blocked` | Idempotent (no error) |
| `test_unblock_already_unblocked` | Idempotent (no error) |
| `test_block_not_found` | Raise error for nonexistent contact_id |

#### Favorite/Unfavorite Tests

| Test | Description |
|------|-------------|
| `test_favorite_contact` | Sets `is_favorite = True` |
| `test_unfavorite_contact` | Sets `is_favorite = False` |
| `test_favorite_already_favorited` | Idempotent |
| `test_unfavorite_already_unfavorited` | Idempotent |

#### Group Operation Tests

| Test | Description |
|------|-------------|
| `test_add_to_group` | Adds group to contact's groups set |
| `test_add_to_group_already_member` | Idempotent |
| `test_remove_from_group` | Removes group from contact's groups set |
| `test_remove_from_group_not_member` | No error if not in group |
| `test_remove_from_group_not_found` | Raise error for nonexistent contact_id |

#### Merge Contact Tests

| Test | Description |
|------|-------------|
| `test_merge_contacts_basic` | Primary absorbs secondary's identifiers, secondary deleted |
| `test_merge_contacts_preserves_primary_scalars` | Primary keeps its name/company when both have values |
| `test_merge_contacts_fills_primary_gaps` | Primary gets secondary's fields when primary's are None |
| `test_merge_contacts_combines_groups` | Union of both contacts' groups |
| `test_merge_contacts_combines_addresses` | Union of both contacts' addresses |
| `test_merge_contacts_combines_identifiers` | Union of both contacts' identifiers (deduped) |
| `test_merge_contacts_not_found_primary` | Raise error |
| `test_merge_contacts_not_found_secondary` | Raise error |

#### Cross-Modality Lookup Tests

| Test | Description |
|------|-------------|
| `test_get_display_name_by_phone` | Returns resolved display name |
| `test_get_display_name_by_email` | Returns resolved display name |
| `test_get_display_name_not_found` | Returns `None` |
| `test_is_identifier_blocked_true` | Blocked contact's identifier returns `True` |
| `test_is_identifier_blocked_false` | Unblocked contact's identifier returns `False` |
| `test_is_identifier_blocked_unknown` | Unknown identifier returns `False` |
| `test_find_contact_by_identifier` | Returns full `Contact` |
| `test_find_contact_by_identifier_not_found` | Returns `None` |
| `test_find_contacts_by_group` | Returns all contacts in group |
| `test_find_contacts_by_group_empty` | Returns `[]` for nonexistent group |
| `test_get_all_groups` | Returns union of all contacts' groups |
| `test_get_all_groups_empty` | Returns empty set when no contacts |
| `test_get_favorites` | Returns only favorited contacts |
| `test_get_blocked_contacts` | Returns only blocked contacts |

#### Query Tests

| Test | Description |
|------|-------------|
| `test_query_all` | Returns all contacts with no filters |
| `test_query_search_text_name` | Substring match on first/last/display/nickname |
| `test_query_search_text_case_insensitive` | Case-insensitive search |
| `test_query_filter_group` | Filter by group membership |
| `test_query_filter_is_favorite` | Filter favorites only |
| `test_query_filter_is_blocked` | Filter blocked only |
| `test_query_filter_has_phone` | Contacts with at least one phone identifier |
| `test_query_filter_has_email` | Contacts with at least one email identifier |
| `test_query_identifier_lookup` | Exact match by identifier_type + identifier_value |
| `test_query_limit` | Limit result count |
| `test_query_offset` | Offset for pagination |
| `test_query_limit_and_offset` | Combined pagination |
| `test_query_no_results` | Empty result set |
| `test_query_response_structure` | Verify `contacts`, `count`, `query_params` keys |

#### Snapshot Tests

| Test | Description |
|------|-------------|
| `test_snapshot_empty_state` | Correct structure with zero counts |
| `test_snapshot_with_contacts` | All contacts serialized |
| `test_snapshot_includes_groups` | Group list derived from contacts |
| `test_snapshot_includes_counts` | Total, favorites, blocked counts |
| `test_compact_snapshot` | LLM-optimized view with counts and summaries |

#### Validate State Tests

| Test | Description |
|------|-------------|
| `test_validate_state_clean` | No issues with valid state |
| `test_validate_state_duplicate_identifiers` | Detects cross-contact duplicates |

#### Undo Tests

| Test | Description |
|------|-------------|
| `test_undo_create_contact` | Undo removes created contact |
| `test_undo_delete_contact` | Undo restores deleted contact with all data |
| `test_undo_update_contact` | Undo restores previous field values |
| `test_undo_block_contact` | Undo restores previous blocked state |
| `test_undo_unblock_contact` | Undo restores previous blocked state |
| `test_undo_favorite_contact` | Undo restores previous favorite state |
| `test_undo_add_to_group` | Undo removes group membership |
| `test_undo_remove_from_group` | Undo restores group membership |
| `test_undo_merge_contacts` | Undo restores both contacts to pre-merge state |
| `test_undo_restores_update_count` | `update_count` reverts |
| `test_undo_restores_last_updated` | `last_updated` reverts |

#### Clear Tests

| Test | Description |
|------|-------------|
| `test_clear_removes_contacts` | All contacts removed |
| `test_clear_resets_counts` | update_count reset to 0 |

### 6.4 API Integration Tests — DONE

**Directory**: `tests/api/modalities/contacts/` (4 files, 128 tests passing)

Follows the SMS/Email test patterns using `client_with_engine` fixture with admin API key authentication.

**Important design pattern discovered**: Event execution catches ALL exceptions internally — operations on nonexistent contacts return HTTP 200 with `status="failed"` in the response body, not HTTP 400/404. Only invalid event data (missing required fields) returns HTTP 400 via Pydantic validation. This is consistent across all modalities.

#### `test_contacts_state.py` (15 tests)

- **TestGetContactsState** (9 tests): response structure, empty state, reflects created contacts, multiple contacts, favorites/blocked counts, groups list, contact identifiers in response, metadata fields, current_time matches simulator
- **TestGetContactsStateCompact** (4 tests): compact response structure, empty compact, compact with contacts (summary counts), excludes full contact data
- **TestContactsStateAuthentication** (2 tests): requires API key, rejects invalid key

#### `test_contacts_actions.py` (88 tests)

- **TestPostContactsCreate** (8 tests): basic create, full details, multiple identifiers, validates required fields, validates empty identifiers, state reflects creation, assigns unique IDs
- **TestPostContactsUpdate** (6 tests): name fields, add/remove identifiers, add/remove groups, nonexistent returns failed, validates contact_id
- **TestPostContactsDelete** (4 tests): success, state reflects, nonexistent returns failed, validates
- **TestPostContactsBlock** (3 tests): success, state reflects, nonexistent returns failed
- **TestPostContactsUnblock** (3 tests): success, state reflects, nonexistent returns failed
- **TestPostContactsFavorite** (3 tests): success, state reflects, nonexistent returns failed
- **TestPostContactsUnfavorite** (3 tests): success, state reflects, nonexistent returns failed
- **TestPostContactsGroupAdd** (6 tests): success, state reflects, multiple groups, validates required fields
- **TestPostContactsGroupRemove** (3 tests): success, state reflects, nonexistent returns failed
- **TestPostContactsMerge** (9 tests): success, removes secondary, combines identifiers/groups, preserves primary name, nonexistent primary/secondary returns failed, validates
- **TestContactsActionAuthentication** (4 tests): requires API key across all action endpoint categories

**Implementation note**: Tests for nonexistent contact operations (10 tests) verify HTTP 200 with `status="failed"` and error message in response — matching the event execution pattern rather than assuming HTTP error codes.

#### `test_contacts_queries.py` (25 tests)

- **TestPostContactsQuery** (23 tests): response structure, no filters returns all, search by first/last name, case-insensitive search, partial match, company search, identifier value search, group filter, multiple group filter, favorite/blocked/has_phone/has_email filters, identifier type+value lookup, pagination (limit, offset, combined), combined filters (group + has_phone), empty results, query parameter echo, empty state query, nonexistent group filter
- **TestContactsQueryAuthentication** (2 tests): requires API key, rejects invalid key

### 6.5 Client/Server Model Sync Tests

**File**: `tests/client/test_model_schema_sync.py`

Add model pairs to the sync test suite. These tests verify that client-side models match server-side models in field names, types, and optionality:

| Server Model | Client Model |
|--------------|-------------|
| `contacts_input.ContactIdentifier` | `_contacts.ContactIdentifier` |
| `contacts_input.PostalAddress` | `_contacts.PostalAddress` |
| `contacts_state.Contact` | `_contacts.Contact` |
| `contacts routes.ContactsStateResponse` | `_contacts.ContactsStateResponse` |
| `contacts routes.ContactsQueryResponse` | `_contacts.ContactsQueryResponse` |

### 6.6 Client/Server Round-Trip Tests

**File**: `tests/client/test_roundtrip.py`

Add round-trip tests that create server model instances with realistic data, serialize to JSON via `model_dump(mode="json")`, and deserialize into client models:

| Test | Description |
|------|-------------|
| `test_contact_identifier_roundtrip` | Server → JSON → Client `ContactIdentifier` |
| `test_postal_address_roundtrip` | Server → JSON → Client `PostalAddress` |
| `test_contact_roundtrip` | Server → JSON → Client `Contact` (full data) |
| `test_contacts_state_response_roundtrip` | Server → JSON → Client `ContactsStateResponse` |
| `test_contacts_query_response_roundtrip` | Server → JSON → Client `ContactsQueryResponse` |

---

## Phase 7: Cross-Modality Integration (Deferred)

This phase is listed for completeness but should be implemented **after** the Contacts modality is fully working and tested independently. It involves updating other modalities to consume Contacts data.

### 7.1 SMS Integration
- Update `SMSState.apply_input()` to check `ContactsState.is_identifier_blocked()` via the `environment` parameter (signature already accepts it)
- Update SMS display name resolution to use `ContactsState.get_display_name("phone", number)`

### 7.2 Email Integration
- Update `EmailState.apply_input()` to check blocked senders via the `environment` parameter (signature already accepts it)
- Update email display name resolution

### 7.3 Calendar Integration
- Update calendar attendee enrichment using `ContactsState.get_contact_for_email()`
- Flag invitations from blocked contacts

### 7.4 Cross-Modality Integration Tests
- Test SMS rejecting messages from blocked contacts
- Test email filtering with blocked senders
- Test calendar attendee name resolution
- Test graceful fallback when Contacts modality is not present

---

## Implementation Order

The recommended implementation sequence, with dependencies noted:

```
Phase 1: Models (no dependencies) ✅ COMPLETE
  1.1  Helper classes (ContactIdentifier, PostalAddress, Contact) ✅
  1.2  ContactsInput ✅
  1.3  ContactsState ✅
  1.4  Registry registration ✅
  1.5  __init__.py exports ✅
         ↓
Phase 6.1: Test Fixtures (depends on models) ✅ COMPLETE
Phase 6.2: Model Input Tests (depends on fixtures) ✅ COMPLETE (78 tests)
Phase 6.3: Model State Tests (depends on fixtures) ✅ COMPLETE (137 tests)
         ↓ (validate models work before building API)
Phase 2: API Routes (depends on models) ✅ COMPLETE
  2.1  Permissions ✅
  2.2  WebSocket events ✅
  2.3  Route handler ✅
  2.4  Route registration ✅
  2.5  Engine initialization ✅
  2.6  Environment compact snapshot ✅
  2.7  Test fixture & hardcoded count updates ✅
         ↓
Phase 6.4: API Integration Tests (depends on routes + fixtures) ✅ COMPLETE (128 tests)
         ↓
Phase 3: Python Client (depends on API being defined)
  3.1  Client sub-client
  3.2  Client integration
         ↓
Phase 6.5: Schema Sync Tests (depends on both server + client models)
Phase 6.6: Round-Trip Tests (depends on both server + client models)
         ↓
Phase 4: Web UI (can run in parallel with Phase 3)
         ↓
Phase 5: Documentation Updates (after all implementation)
         ↓
Phase 7: Cross-Modality Integration (deferred, after everything stable)
```

### Estimated File Count

| Category | New Files | Modified Files |
|----------|-----------|----------------|
| Models | 2 | 2 (`registry.py`, `__init__.py`) |
| API | 1 | 4 (`auth.py`, `websocket.py`, `main.py`, `dependencies.py`) |
| Environment | 0 | 1 (`environment.py`) |
| Client | 1 | 1 (`client.py`) |
| Tests — Fixtures | 1 | 2 (`conftest.py`, `api.py`) |
| Tests — Models | 2 | 0 |
| Tests — API | 4 (incl `__init__`) | 0 |
| Tests — Client | 0 | 2 (`test_model_schema_sync.py`, `test_roundtrip.py`) |
| Web UI | 7 | 1 (`index.ts`) |
| Docs | 0 | 3+ (`API_ACCESS_CONTROL.md`, `MODALITY_ROUTES.md`, `TODO.md`, `CLIENT_QUICK_REFERENCE.md`) |
| **Total** | **18** | **16** |

### Validation Checkpoints

After each phase, run these commands to validate:

```bash
# After Phase 1 (Models): ✅ PASSED
uv run python -c "from ues.models.modalities import ContactsInput, ContactsState; print('Models OK')"

# After Phase 6.2-6.3 (Model Tests): ✅ PASSED (215 tests)
uv run pytest tests/models/test_contacts_input.py tests/models/test_contacts_state.py -v

# After Phase 2 (API Routes): ✅ PASSED
uv run uvicorn ues.main:app --reload  # Check /docs for contacts endpoints
# Verified: 12 contacts endpoints visible in OpenAPI schema

# After Phase 6.4 (API Tests): ✅ PASSED (128 tests)
uv run pytest tests/api/modalities/contacts/ -v

# After Phase 3 (Client):
uv run python -c "from ues.client import UESClient; print(UESClient.__dict__)"

# After Phase 6.5-6.6 (Sync Tests):
uv run pytest tests/client/test_model_schema_sync.py tests/client/test_roundtrip.py -v

# Full regression:
uv run pytest
```
