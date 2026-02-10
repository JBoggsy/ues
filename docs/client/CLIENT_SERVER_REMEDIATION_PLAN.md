# Client/Server Model Remediation Plan

**Date**: 2026-02-10
**Reference**: [CLIENT_SERVER_AUDIT.md](CLIENT_SERVER_AUDIT.md) — 41 issues across 6 modalities
**Goal**: Fix all mismatches, prevent future drift with automated tooling

---

## Table of Contents

1. [Root Cause Analysis](#root-cause-analysis)
2. [Phase 1: Calendar — Critical Fixes](#phase-1-calendar--critical-fixes)
3. [Phase 2: Chat & SMS — High/Critical Fixes](#phase-2-chat--sms--highcritical-fixes)
4. [Phase 3: Email, Weather, Location — Medium Fixes](#phase-3-email-weather-location--medium-fixes)
5. [Phase 4: Compact State Support (Cross-Cutting)](#phase-4-compact-state-support-cross-cutting)
6. [Phase 5: Drift Prevention Infrastructure](#phase-5-drift-prevention-infrastructure)
7. [Documentation Updates](#documentation-updates)
8. [Test Updates](#test-updates)

---

## Root Cause Analysis

### Why Testing Didn't Catch These Issues

The test architecture has three structural blind spots that allowed 41 model mismatches to accumulate undetected:

#### 1. Client unit tests use hand-crafted mock data

All client unit tests (`tests/client/test_<modality>.py`) mock the HTTP transport layer and return **developer-authored dictionaries** that simulate server responses. These dictionaries were written to match what the developer *thought* the server returned at the time the test was written. When the server model later changed (field renamed, added, or restructured), the mock dictionaries stayed the same and the tests kept passing.

```python
# Example: this test passes even if the server renames "recurring_event_id" to "parent_event_id"
mock_http.get.return_value = {
    "recurring_event_id": "some-id",  # ← Stale. Server now calls this "parent_event_id"
    ...
}
event = CalendarEvent(**mock_http.get.return_value)
assert event.recurring_event_id == "some-id"  # ← Passes against the fiction
```

#### 2. No schema comparison or contract tests exist

There are zero tests that import both client and server models and compare their field schemas. The client and server model definitions are entirely decoupled — they were written independently and can drift without any automated check.

#### 3. Integration tests cover workflows, not field completeness

The integration tests in `tests/client/test_integration.py` do exercise real server responses, but they assert on high-level outcomes (e.g., `state.total_email_count == 1`) rather than verifying that every field round-trips correctly. A renamed or dropped field won't cause an assertion failure if no test specifically checks that field.

### How Drift Accumulated

The most severe cases (Calendar `Attachment`, `RecurrenceRule`) appear to have been modeled from external specifications (RFC 5545 / Google Calendar API) rather than from the actual server implementation. The server models were built domain-specifically, while the client models followed a different convention. No integration test ever exercised these code paths end-to-end with real data.

---

## Phase 1: Calendar — Critical Fixes ✅ COMPLETED (2026-02-10)

**Priority**: Immediate — these cause runtime failures
**Estimated scope**: ~200 lines of client model changes + test updates
**Status**: All 15 calendar issues fixed. All 3597 tests pass.

**Files modified:**
- `src/ues/client/_calendar.py` — All model and method fixes
- `tests/client/test_calendar.py` — All test fixture and assertion updates
- `docs/client/API_CLIENT.md` — Updated calendar examples and model docs
- `CHANGELOG.md` — Added detailed entry for Phase 1 fixes

### 1.1 Fix `RecurrenceScope` enum ✅
- **File**: `src/ues/client/_calendar.py`
- **Change**: Replace `"future"` with `"this_and_future"` in the `RecurrenceScope` Literal type
- **Tests**: Update any client tests using `scope="future"` to `scope="this_and_future"`

### 1.2 Rewrite `Attachment` model ✅
- **File**: `src/ues/client/_calendar.py`
- **Change**: Replace entire `Attachment` class to match server schema:
  - Add: `filename: str`, `size: int`, `mime_type: str`, `attachment_id: str`, `url: Optional[str] = None`, `data: Optional[str] = None`
  - Remove: `file_url`, `title`, `icon_link`, `file_id`
- **Tests**: Update all test fixtures and assertions that reference old field names

### 1.3 Rewrite `RecurrenceRule` model ✅
- **File**: `src/ues/client/_calendar.py`
- **Change**: Replace entire `RecurrenceRule` class to match server schema:
  - Change `frequency` values to lowercase
  - Replace `until` with `end_type` + `end_date`
  - Rename `by_day` → `days_of_week` (with full day names)
  - Replace `by_month_day: list[int]` → `day_of_month: Optional[int]`
  - Replace `by_month: list[int]` → `month_of_year: Optional[int]`
  - Remove `by_set_pos`
  - Add `end_type: Literal["never", "count", "until"] = "never"`
- **Tests**: Rewrite all recurrence-related test fixtures and assertions

### 1.4 Fix `CalendarEvent.recurring_event_id` → `parent_event_id` ✅
- **File**: `src/ues/client/_calendar.py`
- **Change**: Rename field from `recurring_event_id` to `parent_event_id`
- **Tests**: Update all references in tests

### 1.5 Fix remaining Calendar issues ✅
- Removed `"confidential"` from `EventVisibility` — server does not support it
- Removed `organizer` and `self_` from `Attendee` — server never populates these
- Added `recurrence_exceptions: set[str] = Field(default_factory=set)` to `CalendarEvent`
- Added `deleted_at: Optional[datetime] = None` to `CalendarEvent`
- Changed `created_at` and `updated_at` types from `datetime | None` to `datetime` on `CalendarEvent`
- Changed `event_ids` from `list[str]` to `set[str]` on `CalendarContainer`
- Changed `visibility` and `transparency` from `Literal` types to `str` to match server
- Added `ge=0` constraint to `Reminder.minutes_before`

### 1.6 Update CalendarClient methods ✅
- Audited all `CalendarClient` and `AsyncCalendarClient` methods
- Updated all 4 docstrings referencing `scope="future"` to `"this_and_future"`
- Method parameters already use `dict[str, Any]` for attachments/recurrence, so they pass through correctly
- Added new type aliases: `RecurrenceFrequency`, `RecurrenceEndType`, `DayOfWeek`

---

## Phase 2: Chat & SMS — High/Critical Fixes ✅ COMPLETED (2026-02-10)

**Priority**: High — phantom data and type safety issues
**Estimated scope**: ~50 lines of model changes + test updates
**Status**: All 6 Chat & SMS issues fixed. All 3597 tests pass.

**Files modified:**
- `src/ues/client/_chat.py` — Removed phantom fields, added `participant_roles`
- `src/ues/client/_sms.py` — Fixed `MessageReaction`, `MessageAttachment`, `SMSConversation` models
- `tests/client/test_chat.py` — Updated all fixtures and assertions
- `tests/client/test_sms.py` — Updated all fixtures and assertions
- `CHANGELOG.md` — Added detailed entry for Phase 2 fixes

### 2.1 Fix Chat `ConversationMetadata` ✅
- **File**: `src/ues/client/_chat.py`
- **Changes**:
  - Remove `user_message_count: int = 0` (phantom field)
  - Remove `assistant_message_count: int = 0` (phantom field)
  - Add `participant_roles: set[str] = Field(default_factory=set)`
- **Tests**: Removed tests for phantom fields. Added test for `participant_roles`.

### 2.2 Fix SMS `MessageReaction.message_id` type ✅
- **File**: `src/ues/client/_sms.py`
- **Change**: Change `message_id: str | None = None` to `message_id: str`
- **Tests**: Updated test fixtures to always provide `message_id`

### 2.3 Fix SMS `MessageAttachment.attachment_id` and `MessageReaction.reaction_id` types ✅
- **File**: `src/ues/client/_sms.py`
- **Changes**:
  - `attachment_id: str | None = None` → `attachment_id: str = Field(default_factory=lambda: str(uuid4()))`
  - `reaction_id: str | None = None` → `reaction_id: str = Field(default_factory=lambda: str(uuid4()))`
- **Tests**: Updated fixtures that expected `None` for these fields to check for auto-generated UUIDs.

### 2.4 Fix SMS `SMSConversation` defaults ✅
- **File**: `src/ues/client/_sms.py`
- **Changes**: Removed defaults for `conversation_type` and `participants` to match server's required-field semantics. These fields are always present in server responses.

---

## Phase 3: Email, Weather, Location — Medium Fixes ✅ COMPLETED (2026-02-12)

**Priority**: Medium — data loss or missing type safety
**Estimated scope**: ~80 lines of model changes + new weather models
**Status**: All 10 Email/Weather/Location issues fixed. All 3617 tests pass.

**Files modified:**
- `src/ues/client/_email.py` — Added `attachment_id` to `EmailAttachment`, documented `participant_addresses` type decision
- `src/ues/client/_weather.py` — Added 9 typed Pydantic models, updated `WeatherQueryResponse.reports` type, updated `update()` method, removed `modality_type` default
- `src/ues/client/_location.py` — Removed `modality_type` default, updated query docstrings
- `src/ues/client/__init__.py` — Exported new weather typed models
- `tests/client/test_email.py` — Added `attachment_id` tests
- `tests/client/test_weather.py` — Added typed model tests, updated mock data for `WeatherReport`
- `tests/client/test_location.py` — Added `modality_type` no-default test
- `CHANGELOG.md` — Added detailed entry for Phase 3 fixes

### 3.1 Email: Add `attachment_id` to `EmailAttachment` ✅
- **File**: `src/ues/client/_email.py`
- **Change**: Added `attachment_id: str = Field(default_factory=lambda: str(uuid4()))`
- **Tests**: Added tests verifying auto-generated UUID format, uniqueness, and explicit override

### 3.2 Email: Fix `participant_addresses` type ✅
- **File**: `src/ues/client/_email.py`
- **Change**: Kept `list[str]` — JSON arrays always deserialize as lists, so converting to `set[str]` would require extra processing. Added docstring note documenting the decision and rationale.

### 3.3 Weather: Add typed response models ✅
- **File**: `src/ues/client/_weather.py`
- **Changes**: Added 9 client-side Pydantic models mirroring the server's weather data models:
  - `WeatherCondition`
  - `CurrentWeather`
  - `MinutelyForecast`
  - `HourlyForecast`
  - `DailyTemperature`, `DailyFeelsLike`, `DailyForecast`
  - `WeatherAlert`
  - `WeatherReport`
- Updated `WeatherQueryResponse.reports` type from `list[dict[str, Any]]` to `list[WeatherReport]`
- Updated `update()` method to accept `WeatherReport | dict[str, Any]` with auto `model_dump()` for typed instances
- Removed dict-conversion hack from `query()` methods
- **Tests**: Added comprehensive model instantiation tests for all 9 new models

### 3.4 Location & Weather: minor type alignment ✅
- Removed spurious `modality_type` defaults from `WeatherStateResponse` and `LocationStateResponse` (server never sends defaults; client should not either)
- Updated `query()` docstrings in both sync and async location/weather clients to document `limit >= 1` and `offset >= 0` constraints

---

## Phase 4: Compact State Support (Cross-Cutting) ✅ COMPLETED (2026-02-10)

**Priority**: Low-Medium — feature gap, not data correctness
**Estimated scope**: ~120 lines across 4 client files
**Status**: All 4 modalities now support `compact=True`. All 3629 tests pass.

**Files modified:**
- `src/ues/client/_sms.py` — Added `SMSCompactStateResponse` model, updated sync/async `get_state()` with `compact` parameter
- `src/ues/client/_chat.py` — Added `ChatCompactStateResponse` model, updated sync/async `get_state()` with `compact` parameter
- `src/ues/client/_weather.py` — Added `WeatherCompactStateResponse` model, updated sync/async `get_state()` with `compact` parameter
- `src/ues/client/_location.py` — Added `LocationCompactStateResponse` model, updated sync/async `get_state()` with `compact` parameter
- `src/ues/client/__init__.py` — Exported all 4 new compact response models
- `tests/client/test_sms.py` — Added compact state tests (sync + async)
- `tests/client/test_chat.py` — Added compact state tests (sync + async)
- `tests/client/test_weather.py` — Added compact state tests (sync + async)
- `tests/client/test_location.py` — Added compact state tests (sync + async)
- `docs/client/API_CLIENT.md` — Updated SMS, Chat, Location, Weather state sections with compact examples
- `docs/client/CLIENT_QUICK_REFERENCE.md` — Added `compact=True` examples to all four modalities
- `CHANGELOG.md` — Added detailed entry for Phase 4 changes

### 4.1 Add compact state models and parameters ✅

For each modality (SMS, Chat, Weather, Location):

1. **Added compact response model** to `src/ues/client/_<modality>.py` ✅
   - Each model mirrors the server's `<Modality>CompactStateResponse` fields exactly
2. **Added `compact` parameter** to `get_state()` method ✅
   - `compact: bool = False`
   - When `True`, passes `?compact=true` query param and deserializes into the compact model
   - Return type is `<Modality>StateResponse | <Modality>CompactStateResponse`
3. **Tests**: Added tests for `get_state(compact=True)` and `get_state(compact=False)` in each client test file ✅
4. **Async**: All changes mirrored in `Async<Modality>Client` ✅

---

## Phase 5: Drift Prevention Infrastructure ✅ COMPLETED (2026-02-12)

**Priority**: High — prevents recurrence of all the above
**Estimated scope**: ~200 lines of new test infrastructure
**Status**: Phases 5.1–5.3 completed. 91 new tests added (35 schema sync + 33 round-trip + 23 integration sub-model). All 671 client tests pass.

**Files created:**
- `tests/client/test_model_schema_sync.py` — 35 tests comparing client/server Pydantic schemas field-by-field
- `tests/client/test_roundtrip.py` — 33 tests verifying server→JSON→client deserialization for all model pairs

**Files modified:**
- `tests/client/test_integration.py` — Added 23 sub-model integration tests across 7 new test classes

### 5.1 Schema Comparison Tests ✅

Created `tests/client/test_model_schema_sync.py` with:
- `compare_models()` utility that compares field names, types, optionality, and defaults between server and client Pydantic models
- `_normalize_type_name()` handles `typing.Union` ↔ `X|Y` syntax, `set`↔`list` normalization, bare `dict`→`dict[str, Any]`, `Literal`→`str` mapping
- `assert_models_in_sync()` assertion wrapper with detailed diff reporting
- Known type overrides documented inline (e.g., CalendarContainer `created_at`/`updated_at` datetime vs datetime|str due to `@field_serializer`)
- 35 tests: Email (4), SMS (5), Calendar (6), Chat (2), Weather (9), meta utilities (9)

### 5.2 Round-Trip Deserialization Tests ✅

Created `tests/client/test_roundtrip.py` with:
- `_roundtrip()` helper: serializes server model via `model_dump(mode="json")`, deserializes into client model
- Tests every model pair with realistic data, asserting every field value
- Exercises nested sub-models (attachments, attendees, recurrence, reactions, weather layers)
- Edge case tests: empty lists, None optional fields, minimal instances, empty sets
- 33 tests: Email (4), SMS (5), Calendar (8), Chat (3), Weather (7), edge cases (6)

### 5.3 Integration Test Improvements ✅

Enhanced `tests/client/test_integration.py` with 23 new tests in 7 classes:
- `TestEmailSubModelIntegration` — attachments, full field values, thread fields
- `TestSMSSubModelIntegration` — attachments, reactions, field values, conversation fields
- `TestCalendarSubModelIntegration` — attendees, recurrence rules, reminders, attachments, all event fields, calendar container
- `TestChatSubModelIntegration` — metadata dict, multimodal content, conversation metadata
- `TestWeatherSubModelIntegration` — current, hourly, daily (nested temp/feels_like), alerts, minutely
- `TestLocationSubModelIntegration` — all location fields, history entries

### 5.4 CI Check (Optional Future)

Not implemented. Consider adding a CI step that:
- Generates the OpenAPI schema from the running server (`/openapi.json`)
- Compares response schemas against client model schemas
- Fails if new response fields are not represented in client models

---

## Documentation Updates

### Files to Update

| File | Update |
|------|--------|
| `docs/client/CLIENT_QUICK_REFERENCE.md` | ✅ Verified — no calendar field names in code examples (uses generic method signatures). No changes needed. |
| `docs/client/API_CLIENT.md` | ✅ Updated recurrence examples (lowercase freq, `days_of_week`, `end_type`), reminder field names, `recurrence_scope` values, and calendar model listing. |
| `TODO.md` | Mark audit task as complete. Update findings for email `participant_addresses` (decision to keep or change). Remove SMS mismatch item (already fixed + re-fixed). |
| `CHANGELOG.md` | ✅ Added detailed entry documenting all Phase 1 fixes. |
| `tests/API_TESTING_GUIDELINES.md` | ✅ Add section on schema sync tests and why hand-crafted mocks are insufficient for model validation. |
| `.github/copilot-instructions.md` | ✅ Add note about running schema sync tests when modifying models. |

---

## Test Updates

### Tests to Modify

| Test File | Changes |
|-----------|---------|
| `tests/client/test_calendar.py` | ✅ Updated all fixtures using old `Attachment`, `RecurrenceRule`, `RecurrenceScope` schemas. Updated `recurring_event_id` → `parent_event_id`. Removed `Attendee.organizer`/`self_` tests. Added `recurrence_exceptions`, `deleted_at`, `parent_event_id` assertions. Updated `created_at`/`updated_at` to required fields. |
| `tests/client/test_chat.py` | Remove `user_message_count`/`assistant_message_count` tests. Add `participant_roles` test. |
| `tests/client/test_sms.py` | Update `MessageReaction.message_id` fixtures (must always provide value). Update `attachment_id`/`reaction_id` type expectations. |
| `tests/client/test_email.py` | Add `attachment_id` to `EmailAttachment` fixtures. |
| `tests/client/test_weather.py` | Add tests for new typed weather models (`WeatherReport`, etc.). |
| `tests/client/test_integration.py` | ✅ Added 23 sub-model integration tests covering attachments, recurrence, attendees, reactions, metadata, weather forecasts, and location fields. |

### New Test Files

| File | Purpose |
|------|---------|
| `tests/client/test_model_schema_sync.py` | ✅ Automated client/server model comparison (Phase 5.1) — 35 tests |
| `tests/client/test_roundtrip.py` | ✅ Server→JSON→Client deserialization verification (Phase 5.2) — 33 tests |

---

## Execution Order

| Order | Phase | Description | Status |
|-------|-------|-------------|--------|
| 1 | **5.1** | Create schema sync test infrastructure | ✅ **COMPLETED** (2026-02-12) |
| 2 | **1** | Fix Calendar critical issues | ✅ **COMPLETED** (2026-02-10) |
| 3 | **2** | Fix Chat & SMS issues | ✅ **COMPLETED** (2026-02-10) |
| 4 | **3** | Fix Email, Weather, Location issues | ✅ **COMPLETED** (2026-02-12) |
| 5 | **5.2** | Create round-trip tests | ✅ **COMPLETED** (2026-02-12) |
| 6 | **4** | Add compact state support | ✅ **COMPLETED** (2026-02-10) |
| 7 | **5.3** | Integration test improvements | ✅ **COMPLETED** (2026-02-12) |
| 8 | **5.4** | CI check (optional) | Not started |
| 9 | **Docs** | Documentation updates | ✅ **COMPLETED** (2026-02-12) |

**Estimated total effort**: ~500-700 lines of changes across ~15 files.
