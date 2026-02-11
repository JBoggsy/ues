# Plan: Refactor SMSInput to Use Typed Top-Level Fields

## Status: PLANNING

## Problem Statement

Currently, `SMSInput` uses per-operation `dict[str, Any]` fields:
- `message_data: Optional[dict[str, Any]]`
- `delivery_update_data: Optional[dict[str, Any]]`
- `reaction_data: Optional[dict[str, Any]]`
- `edit_data: Optional[dict[str, Any]]`
- `delete_data: Optional[dict[str, Any]]`
- `group_data: Optional[dict[str, Any]]`
- `participant_data: Optional[dict[str, Any]]`
- `conversation_update_data: Optional[dict[str, Any]]`

This design:
1. **Lacks type safety** - consumers must know the dict structure
2. **Makes validation complex** - manual dict key checking in validate_input()
3. **Inconsistent with other modalities** - EmailInput uses typed top-level fields

## Target Design (Following EmailInput Pattern)

Convert all nested dict fields to typed, optional, top-level Pydantic fields. Different operations use different subsets of fields.

### Example of EmailInput Pattern
```python
class EmailInput(ModalityInput):
    operation: EmailOperation
    message_id: Optional[str] = None
    from_address: Optional[str] = None
    to_addresses: Optional[list[str]] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    folder: Optional[str] = None
    labels: Optional[list[str]] = None
    # ... all fields at top level, typed
```

### Proposed SMSInput Design
```python
class SMSInput(ModalityInput):
    operation: SMSOperation

    # Message fields (send_message, receive_message)
    from_number: Optional[str] = None
    to_numbers: Optional[list[str]] = None
    body: Optional[str] = None
    message_type: MessageType = "sms"
    attachments: Optional[list[MessageAttachmentData]] = None
    thread_id: Optional[str] = None
    replied_to_message_id: Optional[str] = None

    # Message identifiers (for operations on existing messages)
    message_id: Optional[str] = None

    # Delivery status fields (update_delivery_status)
    new_status: Optional[DeliveryStatus] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    # Reaction fields (add_reaction, remove_reaction)
    phone_number: Optional[str] = None
    emoji: Optional[str] = None
    reaction_id: Optional[str] = None

    # Edit fields (edit_message)
    new_body: Optional[str] = None

    # Delete fields (delete_message)
    delete_for_everyone: bool = False

    # Group fields (create_group, update_group)
    group_name: Optional[str] = None
    creator_number: Optional[str] = None
    participant_numbers: Optional[list[str]] = None
    group_photo_url: Optional[str] = None

    # Conversation update fields (update_conversation)
    pin: Optional[bool] = None
    mute: Optional[bool] = None
    archive: Optional[bool] = None
    mark_all_read: Optional[bool] = None
    draft_message: Optional[str] = None
    mute_until: Optional[datetime] = None
```

---

## Work Plan

### Phase 1: Model Definition Changes

- [ ] **1.1 Add typed top-level fields to SMSInput**
  - Add all fields from the nested dicts as top-level optional fields
  - Use proper types (str, list[str], datetime, bool, etc.)
  - Use typed Literals where appropriate (MessageType, DeliveryStatus)

- [ ] **1.2 Remove the dict[str, Any] fields**
  - Remove: message_data, delivery_update_data, reaction_data, edit_data, delete_data, group_data, participant_data, conversation_update_data

- [ ] **1.3 Update validation methods**
  - Simplify _validate_* methods to check typed fields directly
  - Replace `self.message_data.get("field")` with `self.field`
  - Replace dict key existence checks with `if self.field is None`

### Phase 2: SMSState Changes

- [ ] **2.1 Update SMSState.apply_input()**
  - Replace `input_data.message_data["field"]` with `input_data.field`
  - All handlers need updating to use new field names

- [ ] **2.2 Update SMSState.create_undo_data()**
  - Same pattern - replace dict access with direct field access

### Phase 3: API Route Changes

- [ ] **3.1 Update src/ues/api/routes/sms.py**
  - All SMSInput constructions need updating
  - Change from: `SMSInput(operation="send_message", message_data={...})`
  - Change to: `SMSInput(operation="send_message", from_number=..., to_numbers=..., body=...)`

### Phase 4: Test Updates

- [ ] **4.1 Update tests/fixtures/modalities/sms.py**
  - All fixture creations need new field structure

- [ ] **4.2 Update tests/models/test_sms_input.py**
  - All test SMSInput constructions need updating
  - Validation tests need to check new error messages

- [ ] **4.3 Update tests/models/test_sms_state.py**
  - All SMSInput constructions need updating

- [ ] **4.4 Update other test files**
  - Any file creating SMSInput objects

### Phase 5: Documentation Updates

- [ ] **5.1 Update docs/models/modalities/SMS.md**
  - Update SMSInput section with new field structure
  - Update API usage examples

- [ ] **5.2 Update docs/guides/SCENARIO_FORMAT.md**
  - Update SMS examples

### Phase 6: Validation

- [ ] **6.1 Run full test suite**
- [ ] **6.2 Verify serialization produces flat structure**

---

## Field Mapping (Old → New)

### message_data fields
| Old (dict key) | New (top-level field) | Type |
|---------------|----------------------|------|
| `message_data["from_number"]` | `from_number` | `Optional[str]` |
| `message_data["to_numbers"]` | `to_numbers` | `Optional[list[str]]` |
| `message_data["body"]` | `body` | `Optional[str]` |
| `message_data["message_type"]` | `message_type` | `MessageType` (default: "sms") |
| `message_data["attachments"]` | `attachments` | `Optional[list[MessageAttachmentData]]` |
| `message_data["thread_id"]` | `thread_id` | `Optional[str]` |
| `message_data["replied_to_message_id"]` | `replied_to_message_id` | `Optional[str]` |

### delivery_update_data fields
| Old (dict key) | New (top-level field) | Type |
|---------------|----------------------|------|
| `delivery_update_data["message_id"]` | `message_id` | `Optional[str]` |
| `delivery_update_data["new_status"]` | `new_status` | `Optional[DeliveryStatus]` |
| `delivery_update_data["delivered_at"]` | `delivered_at` | `Optional[datetime]` |
| `delivery_update_data["read_at"]` | `read_at` | `Optional[datetime]` |
| `delivery_update_data["conversation_id"]` | `thread_id` | `Optional[str]` (reuse) |

### reaction_data fields
| Old (dict key) | New (top-level field) | Type |
|---------------|----------------------|------|
| `reaction_data["message_id"]` | `message_id` | `Optional[str]` (shared) |
| `reaction_data["phone_number"]` | `phone_number` | `Optional[str]` |
| `reaction_data["emoji"]` | `emoji` | `Optional[str]` |
| `reaction_data["reaction_id"]` | `reaction_id` | `Optional[str]` |
| `reaction_data["conversation_id"]` | `thread_id` | `Optional[str]` (reuse) |

### edit_data fields
| Old (dict key) | New (top-level field) | Type |
|---------------|----------------------|------|
| `edit_data["message_id"]` | `message_id` | `Optional[str]` (shared) |
| `edit_data["new_body"]` | `new_body` | `Optional[str]` |
| `edit_data["conversation_id"]` | `thread_id` | `Optional[str]` (reuse) |

### delete_data fields
| Old (dict key) | New (top-level field) | Type |
|---------------|----------------------|------|
| `delete_data["message_id"]` | `message_id` | `Optional[str]` (shared) |
| `delete_data["delete_for_everyone"]` | `delete_for_everyone` | `bool` (default: False) |
| `delete_data["conversation_id"]` | `thread_id` | `Optional[str]` (reuse) |

### group_data fields
| Old (dict key) | New (top-level field) | Type |
|---------------|----------------------|------|
| `group_data["thread_id"]` | `thread_id` | `Optional[str]` (shared) |
| `group_data["group_name"]` | `group_name` | `Optional[str]` |
| `group_data["creator_number"]` | `creator_number` | `Optional[str]` |
| `group_data["participant_numbers"]` | `participant_numbers` | `Optional[list[str]]` |
| `group_data["group_photo_url"]` | `group_photo_url` | `Optional[str]` |
| `group_data["participants"]` | `participant_numbers` | (alias) |

### participant_data fields
| Old (dict key) | New (top-level field) | Type |
|---------------|----------------------|------|
| `participant_data["thread_id"]` | `thread_id` | `Optional[str]` (shared) |
| `participant_data["phone_number"]` | `phone_number` | `Optional[str]` (shared) |
| `participant_data["added_by"]` | `added_by` | `Optional[str]` |
| `participant_data["removed_by"]` | `removed_by` | `Optional[str]` |
| `participant_data["is_admin"]` | `is_admin` | `bool` (default: False) |

### conversation_update_data fields
| Old (dict key) | New (top-level field) | Type |
|---------------|----------------------|------|
| `conversation_update_data["thread_id"]` | `thread_id` | `Optional[str]` (shared) |
| `conversation_update_data["pin"]` | `pin` | `Optional[bool]` |
| `conversation_update_data["mute"]` | `mute` | `Optional[bool]` |
| `conversation_update_data["archive"]` | `archive` | `Optional[bool]` |
| `conversation_update_data["mark_all_read"]` | `mark_all_read` | `Optional[bool]` |
| `conversation_update_data["draft_message"]` | `draft_message` | `Optional[str]` |
| `conversation_update_data["mute_until"]` | `mute_until` | `Optional[datetime]` |
| `conversation_update_data["is_muted"]` | `mute` | (alias) |
| `conversation_update_data["is_pinned"]` | `pin` | (alias) |
| `conversation_update_data["is_archived"]` | `archive` | (alias) |

---

## Files to Modify

### Server Code
1. `src/ues/models/modalities/sms_input.py` - Complete restructure
2. `src/ues/models/modalities/sms_state.py` - apply_input() and create_undo_data()
3. `src/ues/api/routes/sms.py` - SMSInput construction

### Test Files
4. `tests/fixtures/modalities/sms.py`
5. `tests/models/test_sms_input.py`
6. `tests/models/test_sms_state.py`
7. Other files that create SMSInput objects

### Documentation
8. `docs/models/modalities/SMS.md`
9. `docs/guides/SCENARIO_FORMAT.md`

---

## Notes

- **Shared fields**: `thread_id`, `message_id`, `phone_number` are used by multiple operations
- **Type safety**: Pydantic will validate types automatically
- **Validation simplification**: No more dict key checking, just `if self.field is None`
- **Breaking change**: This changes the API schema - acceptable for pre-1.0
