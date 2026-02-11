# Plan: Standardize SMSInput Operation Field Naming

## Problem Statement

The codebase has inconsistent naming across modality inputs for the "what kind of operation is this" discriminator field:

| Modality | Field name | Type |
|----------|------------|------|
| `EmailInput` | `operation` | `EmailOperation` |
| `CalendarInput` | `operation` | `CalendarOperation` |
| `ChatInput` | `operation` | `ChatOperation` |
| **`SMSInput`** | **`action`** | **`SMSAction`** |

Since `EventResponse.data` is populated via `model_dump()`, the serialized key follows the Pydantic field name. This means consumers of the events API must know which modality uses which key name to extract the operation type — there's no single, reliable key to read.

## Proposed Approach

Standardize on `operation` and `SMSOperation` by refactoring `SMSInput` to align with the other modalities.

---

## Work Plan

### Phase 1: Server Model Changes

- [ ] **1.1 Rename type in `sms_input.py`**
  - Change `SMSAction = Literal[...]` to `SMSOperation = Literal[...]`
  - Keep the same list of operation values

- [ ] **1.2 Rename field in `SMSInput` class**
  - Change `action: SMSAction` to `operation: SMSOperation`
  - Update Field description

- [ ] **1.3 Update all `self.action` references in `SMSInput`**
  - `validate_input()` method has many `if self.action == ...` checks
  - `get_affected_entities()` method
  - `get_summary()` method

- [ ] **1.4 Update `SMSState.apply_input()` in `sms_state.py`**
  - Change all `if input_data.action == ...` to `if input_data.operation == ...`

### Phase 2: Server API Route Changes

- [ ] **2.1 Review `src/ues/api/routes/sms.py`**
  - Check if routes reference the `action` field directly
  - Update any references to use `operation`

### Phase 3: Client Library Changes

- [ ] **3.1 Update SMS fixtures in `tests/fixtures/modalities/sms.py`**
  - Change `action=` parameter to `operation=`
  - Update `create_sms_input()` function signature
  - Update all pre-built fixtures (SIMPLE_RECEIVE, SIMPLE_SEND, etc.)
  - Update JSON fixtures (SMS_JSON_EXAMPLES)

### Phase 4: Test Updates

- [ ] **4.1 Update `tests/models/test_sms_input.py`**
  - Change all `action=` to `operation=`
  - Change all `.action` assertions to `.operation`
  - Update test class/method names if they reference "action"

- [ ] **4.2 Update `tests/models/test_sms_state.py`**
  - Check for any `action` references and update to `operation`

- [ ] **4.3 Update `tests/api/modalities/sms/` test files**
  - `test_sms_actions.py` - update any action references
  - `test_sms_queries.py` - check for action references
  - `test_sms_state.py` - check for action references

- [ ] **4.4 Run model schema sync and round-trip tests**
  - `uv run pytest tests/client/test_model_schema_sync.py tests/client/test_roundtrip.py -v`

### Phase 5: Documentation Updates

- [ ] **5.1 Update `docs/models/modalities/SMS.md`**
  - Change all references from `action` to `operation`
  - Update the SMSInput attributes section
  - Update API usage examples

- [ ] **5.2 Update `docs/guides/SCENARIO_FORMAT.md`**
  - Check for SMS examples using `action` field
  - Update to use `operation`

- [ ] **5.3 Update `docs/models/MODALITY_MODELS.md`**
  - If SMS examples exist, update them

### Phase 6: Web UI Updates (Optional)

- [ ] **6.1 Update `webapp/src/components/modalities/sms/types.ts`**
  - Note: The `SMSAction` type here is for *UI operations*, not the input model
  - This is a different type (send, receive, delete, mark_read, etc.) used for API operations
  - **No change needed** - this is unrelated to the server model

### Phase 7: Validation

- [ ] **7.1 Run full test suite**
  - `uv run pytest tests/ -v`
  - Ensure all tests pass

- [ ] **7.2 Verify serialization**
  - Create an SMSInput, call `model_dump()`, verify the key is `operation`

---

## Files to Modify

### Server Code
1. `src/ues/models/modalities/sms_input.py` - Main model changes
2. `src/ues/models/modalities/sms_state.py` - apply_input() updates

### Test Files
3. `tests/fixtures/modalities/sms.py` - Fixture updates
4. `tests/models/test_sms_input.py` - Input model tests
5. `tests/models/test_sms_state.py` - State model tests
6. `tests/api/modalities/sms/test_sms_actions.py` - API tests
7. `tests/api/modalities/sms/test_sms_queries.py` - Query tests
8. `tests/api/modalities/sms/test_sms_state.py` - State API tests

### Documentation
9. `docs/models/modalities/SMS.md` - SMS modality docs
10. `docs/guides/SCENARIO_FORMAT.md` - Scenario format (if SMS examples)

---

## Notes

- The web UI `SMSAction` type in `types.ts` is **unrelated** - it's for UI-level operations like "send", "delete", "mark_read" which map to API endpoints, not the input model's discriminator
- The client library (`src/ues/client/_sms.py`) doesn't directly use the `action` field - it makes API calls that construct inputs server-side
- No API route changes should be needed since routes construct `SMSInput` objects internally

---

## Considerations

- **Backward Compatibility**: This is a breaking change for any external consumers parsing the `action` field from serialized SMS inputs. However, since this is a pre-1.0 project, breaking changes are acceptable.
- **Migration**: No migration script needed since this is a schema change, not a data migration.
