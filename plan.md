# Plan: Standardize SMSInput Operation Field Naming

## Status: ✅ COMPLETE

## Problem Statement

The codebase has inconsistent naming across modality inputs for the "what kind of operation is this" discriminator field:

| Modality | Field name | Type |
|----------|------------|------|
| `EmailInput` | `operation` | `EmailOperation` |
| `CalendarInput` | `operation` | `CalendarOperation` |
| `ChatInput` | `operation` | `ChatOperation` |
| ~~`SMSInput`~~ | ~~`action`~~ | ~~`SMSAction`~~ |
| **`SMSInput`** | **`operation`** | **`SMSOperation`** ✅ |

Since `EventResponse.data` is populated via `model_dump()`, the serialized key follows the Pydantic field name. This means consumers of the events API must know which modality uses which key name to extract the operation type — there's no single, reliable key to read.

## Proposed Approach

Standardize on `operation` and `SMSOperation` by refactoring `SMSInput` to align with the other modalities.

---

## Work Plan

### Phase 1: Server Model Changes ✅

- [x] **1.1 Rename type in `sms_input.py`**
  - Changed `SMSAction = Literal[...]` to `SMSOperation = Literal[...]`
  - Kept the same list of operation values

- [x] **1.2 Rename field in `SMSInput` class**
  - Changed `action: SMSAction` to `operation: SMSOperation`
  - Updated Field description

- [x] **1.3 Update all `self.action` references in `SMSInput`**
  - `validate_input()` method - updated all `if self.action == ...` checks
  - `get_affected_entities()` method - updated
  - `get_summary()` method - updated

- [x] **1.4 Update `SMSState.apply_input()` in `sms_state.py`**
  - Changed all `if input_data.action == ...` to `if input_data.operation == ...`
  - Updated `create_undo_data()` as well

### Phase 2: Server API Route Changes ✅

- [x] **2.1 Review `src/ues/api/routes/sms.py`**
  - Updated all SMSInput instantiations from `action=` to `operation=`

### Phase 3: Test Fixture Changes ✅

- [x] **3.1 Update SMS fixtures in `tests/fixtures/modalities/sms.py`**
  - Changed `action=` parameter to `operation=`
  - Updated `create_sms_input()` function signature
  - Updated all pre-built fixtures (SIMPLE_RECEIVE, SIMPLE_SEND, etc.)
  - Updated JSON fixtures (SMS_JSON_EXAMPLES)

### Phase 4: Test Updates ✅

- [x] **4.1 Update `tests/models/test_sms_input.py`**
  - Changed all `action=` to `operation=`
  - Changed all `.action` assertions to `.operation`
  - Updated test method names (`test_all_sms_actions` → `test_all_sms_operations`)

- [x] **4.2 Update `tests/models/test_sms_state.py`**
  - Updated all `action=` to `operation=` for SMS operations

- [x] **4.3 Update `tests/api/modalities/sms/` test files**
  - No changes needed - tests use API endpoints, not direct input construction

- [x] **4.4 Run model schema sync and round-trip tests**
  - All 68 tests passed

- [x] **4.5 Update remaining test files with SMS references**
  - `tests/models/test_compact_snapshot.py`
  - `tests/client/test_integration.py`
  - `tests/client/test_events.py`
  - `tests/api/cross_cutting/test_state_consistency.py`
  - `tests/api/workflows/builders.py`
  - `tests/api/events/test_event_creation.py`
  - `tests/api/events/test_event_listing.py`
  - `tests/api/events/test_batch_events.py`
  - `tests/api/helpers.py`
  - `tests/fixtures/scenarios/busy_workday.py`
  - `tests/fixtures/scenarios/travel_day.py`

### Phase 5: Documentation Updates ✅

- [x] **5.1 Update `docs/models/modalities/SMS.md`**
  - Changed all references from `action` to `operation`
  - Updated the SMSInput attributes section
  - Updated API usage examples

- [x] **5.2 Update `docs/guides/SCENARIO_FORMAT.md`**
  - Updated SMS examples to use `operation` field

### Phase 6: Web UI Updates (Not Needed)

- [x] **6.1 `webapp/src/components/modalities/sms/types.ts`**
  - **No change needed** - The `SMSAction` type is for *UI operations* (send, receive, delete, mark_read)
  - This is unrelated to the server model's discriminator field

### Phase 7: Validation ✅

- [x] **7.1 Run full SMS test suite**
  - 252 SMS-related tests passed

- [x] **7.2 Verify serialization**
  - Confirmed `model_dump()` produces `operation` key, not `action`

---

## Files Modified

### Server Code
1. `src/ues/models/modalities/sms_input.py` - Main model changes
2. `src/ues/models/modalities/sms_state.py` - apply_input() and create_undo_data() updates
3. `src/ues/api/routes/sms.py` - Route SMSInput construction updates

### Test Files
4. `tests/fixtures/modalities/sms.py` - Fixture updates
5. `tests/models/test_sms_input.py` - Input model tests
6. `tests/models/test_sms_state.py` - State model tests
7. `tests/models/test_compact_snapshot.py` - Compact snapshot tests
8. `tests/client/test_integration.py` - Client integration tests
9. `tests/client/test_events.py` - Client event tests
10. `tests/api/cross_cutting/test_state_consistency.py` - State consistency tests
11. `tests/api/workflows/builders.py` - Workflow builders
12. `tests/api/events/test_event_creation.py` - Event creation tests
13. `tests/api/events/test_event_listing.py` - Event listing tests
14. `tests/api/events/test_batch_events.py` - Batch event tests
15. `tests/api/helpers.py` - API test helpers
16. `tests/fixtures/scenarios/busy_workday.py` - Scenario fixtures
17. `tests/fixtures/scenarios/travel_day.py` - Scenario fixtures

### Documentation
18. `docs/models/modalities/SMS.md` - SMS modality docs
19. `docs/guides/SCENARIO_FORMAT.md` - Scenario format examples

---

## Notes

- The web UI `SMSAction` type in `types.ts` is **unrelated** - it's for UI-level operations like "send", "delete", "mark_read" which map to API endpoints, not the input model's discriminator
- The client library (`src/ues/client/_sms.py`) doesn't directly use the `action` field - it makes API calls that construct inputs server-side
- API routes updated to use `operation=` when constructing SMSInput objects

---

## Result

All modalities now use consistent naming:

| Modality | Field name | Type |
|----------|------------|------|
| `EmailInput` | `operation` | `EmailOperation` |
| `CalendarInput` | `operation` | `CalendarOperation` |
| `ChatInput` | `operation` | `ChatOperation` |
| `SMSInput` | `operation` | `SMSOperation` |

Consumers can now reliably read the `operation` key from any modality's serialized input data.
