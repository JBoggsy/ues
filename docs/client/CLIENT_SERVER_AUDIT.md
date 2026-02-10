# Client vs Server Model Audit Report

**Date**: 2026-02-10
**Scope**: All implemented modalities (Email, SMS, Calendar, Chat, Weather, Location)
**Method**: Field-by-field comparison of `src/ues/client/_<modality>.py` against `src/ues/models/modalities/<modality>_state.py`, `<modality>_input.py`, and `src/ues/api/routes/<modality>.py`

---

## Executive Summary

| Modality | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| **Calendar** | **4** | **3** | **4** | **4** | **15** |
| **Chat** | **2** | 0 | **2** | 0 | **4** |
| **SMS** | 0 | **1** | **3** | **2** | **6** |
| **Email** | 0 | 0 | **1** | **2** | **3** |
| **Weather** | 0 | 0 | **4** | **3** | **7** |
| **Location** | 0 | 0 | **2** | **4** | **6** |
| **TOTAL** | **6** | **4** | **16** | **15** | **41** |

The Calendar modality is by far the worst — three of its sub-models (`Attachment`, `RecurrenceRule`, `RecurrenceScope`) are **fundamentally incompatible** with the server and appear to have been modeled from a different specification entirely.

### Severity Definitions

- **Critical**: Client sends values the server will reject, or field names are completely wrong causing data loss on deserialization.
- **High**: Client has extra fields the server ignores, or is missing required server fields, leading to incorrect behavior.
- **Medium**: Data silently dropped, phantom fields that always read as defaults, or missing feature support.
- **Low**: Cosmetic type differences, validation constraint gaps, or default value divergences that don't affect runtime behavior for typical use.

---

## Calendar Modality (15 issues)

The calendar client is the most severely affected modality. Three sub-models are built against an entirely different schema than the server implements.

### Critical Issues

#### 1. `RecurrenceScope` enum value mismatch
- **Client**: `Literal["this", "future", "all"]`
- **Server**: `Literal["this", "this_and_future", "all"]`
- **Impact**: Any client call using `scope="future"` for recurring event updates/deletes will be **rejected by the server** with a validation error. The correct value is `"this_and_future"`.

#### 2. `Attachment` model — completely different schema
The client and server `Attachment` models share **zero compatible fields**:

| Field | Client | Server |
|-------|--------|--------|
| `file_url` | `str` (required) | Does not exist |
| `title` | `str` (required) | Does not exist |
| `filename` | Does not exist | `str` (required) |
| `size` | Does not exist | `int` (required, `ge=0`) |
| `mime_type` | `str \| None = None` | `str` (required) |
| `icon_link` | `str \| None = None` | Does not exist |
| `file_id` | `str \| None = None` | Does not exist |
| `url` | Does not exist | `Optional[str] = None` |
| `data` | Does not exist | `Optional[str] = None` |
| `attachment_id` | Does not exist | `str` (auto-UUID) |

**Impact**: Creating events with attachments will fail. Deserializing events with attachments from the server will produce empty/default objects.

#### 3. `RecurrenceRule` model — fundamentally incompatible schema
The client uses an RFC 5545 / iCalendar-style schema while the server uses a domain-specific schema:

| Aspect | Client | Server |
|--------|--------|--------|
| `frequency` values | `"DAILY"`, `"WEEKLY"`, etc. (uppercase) | `"daily"`, `"weekly"`, etc. (lowercase) |
| Recurrence end | `until: str \| None` | `end_type: RecurrenceEndType` + `end_date: Optional[date]` |
| Day-of-week field | `by_day: list[str] \| None` | `days_of_week: Optional[list[DayOfWeek]]` (full names like `"monday"`) |
| Day-of-month field | `by_month_day: list[int] \| None` | `day_of_month: Optional[int]` (single int, not list) |
| Month field | `by_month: list[int] \| None` | `month_of_year: Optional[int]` (single int, not list) |
| `by_set_pos` | `list[int] \| None` | Does not exist |
| `end_type` | Does not exist | Required (`"never"`, `"count"`, `"until"`) |

**Impact**: Creating recurring events through the client will fail. Deserializing recurring events from the server will produce incorrect/empty recurrence data.

#### 4. `CalendarEvent.recurring_event_id` vs `parent_event_id`
- **Client field**: `recurring_event_id: str | None = None`
- **Server field**: `parent_event_id: Optional[str] = None`
- **Impact**: When deserializing server responses, the parent event ID is silently dropped because the field name doesn't match. The client's `recurring_event_id` will always be `None`.

### High Issues

#### 5. `EventVisibility` enum — extra value
- **Client**: `Literal["default", "public", "private", "confidential"]`
- **Server**: `Literal["public", "private", "default"]`
- **Impact**: Client code that sends `visibility="confidential"` will be rejected by the server.

#### 6. `Attendee` model — extra fields
- **Client has**: `organizer: bool = False` and `self_: bool = Field(default=False, alias="self")`
- **Server**: Neither field exists on the `Attendee` model
- **Impact**: These fields are silently ignored by the server. Client-side code relying on `attendee.organizer` or `attendee.self_` will always see `False` (the defaults) since the server never populates them.

#### 7. `CalendarEvent.recurrence_exceptions` — missing from client
- **Server**: `recurrence_exceptions: set[str] = Field(default_factory=set)`
- **Client**: Field does not exist
- **Impact**: Exception dates for recurring events are silently dropped during deserialization.

### Medium Issues

#### 8. `CalendarEvent.deleted_at` — missing from client
- **Server**: `deleted_at: Optional[datetime] = None`
- **Client**: Field does not exist
- **Impact**: Client cannot see soft-deletion timestamps.

#### 9. `CalendarEvent.created_at` — optionality mismatch
- **Client**: `datetime | None = None`
- **Server**: `datetime` (always has a value, defaults to `datetime.now(timezone.utc)`)
- **Impact**: Client type annotation misleadingly suggests `None` is possible.

#### 10. `CalendarEvent.updated_at` — optionality mismatch
- Same as `created_at` above.

#### 11. `CalendarContainer.event_ids` — type mismatch
- **Client**: `list[str]`
- **Server**: `set[str]`
- **Impact**: JSON round-trip works (sets serialize to arrays), but client allows duplicate event IDs.

### Low Issues

#### 12. `Reminder.minutes_before` — missing constraint
- **Server**: `Field(ge=0)` — rejects negative values
- **Client**: No constraint

#### 13. `CalendarEvent` status/visibility/transparency — type strictness
- **Client**: Uses `Literal` types (stricter)
- **Server**: Uses plain `str` (more permissive)
- **Impact**: Functionally compatible; client is just more restrictive.

#### 14. `CalendarContainer` name — `CalendarContainer` vs `Calendar`
- Different class names; no runtime impact since Pydantic doesn't match on class name.

#### 15. `CalendarContainer.created_at`/`updated_at` — type
- **Client**: `datetime | str`
- **Server**: `datetime` (with field serializer to str)
- **Impact**: Client accepts both, compatible with server output.

---

## Chat Modality (4 issues)

### Critical Issues

#### 16. `ConversationMetadata.user_message_count` — phantom field
- **Client**: `user_message_count: int = 0`
- **Server**: Field does not exist
- **Impact**: This field will **always be 0**. Any client code that reads it is silently getting wrong data.

#### 17. `ConversationMetadata.assistant_message_count` — phantom field
- **Client**: `assistant_message_count: int = 0`
- **Server**: Field does not exist
- **Impact**: Same as above. Always 0, never populated.

### Medium Issues

#### 18. `ConversationMetadata.participant_roles` — missing from client
- **Server**: `participant_roles: set[str] = Field(default_factory=set)`
- **Client**: Field does not exist
- **Impact**: Server sends this data but Pydantic silently drops it. Client users cannot see which roles participated in a conversation.

#### 19. Missing compact state support
- **Server**: `GET /chat/state?compact=true` returns `ChatCompactStateResponse`
- **Client**: `get_state()` has no `compact` parameter; no `ChatCompactStateResponse` model
- **Impact**: Feature entirely inaccessible from client.

---

## SMS Modality (6 issues)

### High Issues

#### 20. `MessageReaction.message_id` — type mismatch
- **Client**: `message_id: str | None = None`
- **Server**: `message_id: str` (required, no default)
- **Impact**: Client allows `None` for what the server requires. Client model can represent invalid states; type annotation misleadingly suggests the field may be absent.

### Medium Issues

#### 21. `MessageAttachment.attachment_id` — type/default mismatch
- **Client**: `attachment_id: str | None = None`
- **Server**: `attachment_id: str = Field(default_factory=lambda: str(uuid4()))` (never None)
- **Impact**: Client allows `None` but server always provides a UUID. Overly permissive client type.

#### 22. `MessageReaction.reaction_id` — type/default mismatch
- Same pattern as `attachment_id` above.

#### 23. Missing `SMSCompactStateResponse`
- **Server**: `GET /sms/state?compact=true` returns `SMSCompactStateResponse`
- **Client**: No `compact` parameter; no model
- **Impact**: Feature inaccessible from client.

### Low Issues

#### 24. `SMSConversation.conversation_type` — default value
- **Client**: `str = "one_on_one"` (has default)
- **Server**: `str` (required, no default)

#### 25. `SMSConversation.participants` — default value
- **Client**: `list[GroupParticipant] = Field(default_factory=list)` (has default)
- **Server**: `list[GroupParticipant]` (required, no default)

---

## Email Modality (3 issues)

### Medium Issues

#### 26. `EmailAttachment.attachment_id` — missing from client
- **Server**: `attachment_id: str = Field(default_factory=lambda: str(uuid4()))`
- **Client**: Field does not exist
- **Impact**: Attachment IDs are silently dropped during deserialization. Client code cannot reference specific attachments by ID.

### Low Issues

#### 27. `Email.attachments` — type annotation
- **Client**: `list[EmailAttachment]` (typed)
- **Server**: `list` (untyped)
- **Impact**: Cosmetic. The actual mismatch propagates from issue #26.

#### 28. `EmailThread.participant_addresses` — type mismatch
- **Client**: `list[str]`
- **Server**: `set[str]`
- **Impact**: JSON round-trip works fine. Client allows duplicates, server enforces uniqueness.

---

## Weather Modality (7 issues)

### Medium Issues

#### 29. `WeatherQueryResponse.reports` — untyped
- **Client**: `list[dict[str, Any]]`
- **Server**: `list[WeatherReport]` (full Pydantic model with nested sub-models)
- **Impact**: Client loses all type safety for weather reports. Users work with raw dicts instead of typed objects.

#### 30. `update()` report parameter — untyped
- **Client**: `report: dict[str, Any]`
- **Server**: `report: WeatherReport`
- **Impact**: Same type safety loss.

#### 31. Missing compact state support
- **Server** supports `GET /weather/state?compact=true`
- **Client** has no `compact` parameter; no `WeatherCompactStateResponse` model

#### 32. No `WeatherReport` or nested models on client
- **Server** defines 9 typed models (`WeatherReport`, `WeatherCondition`, `CurrentWeather`, `MinutelyForecast`, `HourlyForecast`, `DailyTemperature`, `DailyFeelsLike`, `DailyForecast`, `WeatherAlert`)
- **Client** has none of these — all weather data is `dict[str, Any]`

### Low Issues

#### 33. `WeatherStateResponse.modality_type` — default value
- **Client**: `str = "weather"` (has default)
- **Server**: `str` (no default)

#### 34. `query()` `limit` — missing constraint
- **Server**: `ge=1`; **Client**: no constraint

#### 35. `query()` `offset` — type and constraint
- **Client**: `int = 0`; **Server**: `Optional[int] = 0` with `ge=0`

---

## Location Modality (6 issues)

### Medium Issues

#### 36. Missing compact state support
- **Server** supports `GET /location/state?compact=true`
- **Client** has no `compact` parameter; no `LocationCompactStateResponse` model

#### 37. Missing `LocationCompactStateResponse` model
- Directly related to issue #36.

### Low Issues

#### 38. `LocationStateResponse.modality_type` — default value
- **Client**: has default `"location"`; **Server**: no default

#### 39. `query()` `offset` — type
- **Client**: `int`; **Server**: `Optional[int]`

#### 40. `query()` `sort_order` — type strictness
- **Client**: `Literal["asc", "desc"]`; **Server**: `str`
- **Impact**: Client is stricter (good), not a bug.

#### 41. `query()` `limit`/`offset` — missing constraints
- **Server** has `ge=1`/`ge=0` constraints; client does not validate.

---

## Cross-Cutting Pattern: Missing Compact State Support

All four modalities with compact state endpoints (SMS, Chat, Weather, Location) lack client support. This is a single design gap that can be addressed uniformly:

| Modality | Server Endpoint | Server Response Model | Client Support |
|----------|----------------|----------------------|----------------|
| SMS | `GET /sms/state?compact=true` | `SMSCompactStateResponse` | Missing |
| Chat | `GET /chat/state?compact=true` | `ChatCompactStateResponse` | Missing |
| Weather | `GET /weather/state?compact=true` | `WeatherCompactStateResponse` | Missing |
| Location | `GET /location/state?compact=true` | `LocationCompactStateResponse` | Missing |

---

## Root Cause Analysis

See [CLIENT_SERVER_REMEDIATION_PLAN.md](CLIENT_SERVER_REMEDIATION_PLAN.md) for the root cause analysis explaining why these issues went undetected by the existing test suite, and the detailed plan to fix all issues and prevent future drift.
