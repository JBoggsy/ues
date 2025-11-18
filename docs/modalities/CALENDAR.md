# Calendar Modality Design

The Calendar modality simulates a comprehensive calendar system for testing AI personal assistants. It includes the core features of modern calendar applications (Google Calendar, Outlook Calendar, Apple Calendar) without complex backend details like CalDAV protocol, server synchronization, or enterprise resource scheduling.

## Calendar Events

- **Title/Summary**: Event name/description
- **Description**: Detailed event notes/body content
- **Start time**: Event start date and time
- **End time**: Event end date and time
- **All-day events**: Events without specific times (date-only)
- **Time zone**: Event time zone (important for cross-timezone scheduling)
- **Location**: Physical or virtual location (free-text field)
- **Status**: Confirmed, tentative, cancelled

## Event Participants

- **Organizer**: Event creator/owner
- **Attendees**: Invited participants with email addresses
- **Attendance response**: Per-attendee status (accepted, declined, tentative, needs-action)
- **Optional attendees**: Distinguish required vs optional participants
- **Response tracking**: Track who has/hasn't responded

## Event Organization

- **Multiple calendars**: Separate calendars (Work, Personal, Family, etc.)
- **Calendar colors**: Visual distinction between calendars
- **Event colors**: Individual event color overrides
- **Calendar visibility**: Show/hide specific calendars
- **Calendar names**: User-defined calendar names
- **Default calendar**: Which calendar new events go to

## Recurring Events

- **Recurrence rules**: RRULE-style patterns (daily, weekly, monthly, yearly)
- **Recurrence frequency**: Every N days/weeks/months/years
- **Day of week**: Weekly recurrence on specific days (e.g., every Monday and Wednesday)
- **Day of month**: Monthly recurrence on specific date (e.g., 15th of each month)
- **End conditions**:
  - Recur forever (until explicitly stopped)
  - End by date (until a specific date)
  - End after N occurrences
- **Exception dates**: Skip specific occurrences (e.g., skip holiday)
- **Modified occurrences**: Edit single occurrence differently from series
- **Recurrence range editing**: Edit this event, this and future events, or all events

## Reminders and Notifications

- **Event reminders**: Alert before event starts
- **Multiple reminders**: Multiple alerts per event
- **Reminder timing**: N minutes/hours/days/weeks before event
- **Reminder type**: Visual notification, email, both
- **Default reminders**: Per-calendar default reminder settings

## Event Visibility and Privacy

- **Visibility levels**:
  - Public: Anyone can see full details
  - Private: Only user sees event details
  - Default: Calendar's default visibility
- **Free/busy status**: Show as busy/free/tentative/out-of-office
- **Transparency**: Does event block time (opaque) or not (transparent)

## Event Attachments and Links

- **File attachments**: Attach documents, images, etc. (filename, size, MIME type)
- **Web links**: URLs in event description or dedicated link field
- **Conference links**: Video meeting URLs (Zoom, Meet, Teams, etc.)

## Event Search and Filtering

- **Search by**:
  - Title/description keywords
  - Location
  - Attendee email
  - Date range
  - Calendar name
- **Filter by**:
  - Calendar
  - Event color
  - Status (confirmed/tentative/cancelled)
  - Has attendees
  - Has reminders
  - Recurring vs one-time events

## Event Operations

- **Create event**: Add new calendar event
- **Edit event**: Modify existing event (with recurrence handling)
- **Delete event**: Remove event (with recurrence handling)
- **Duplicate event**: Copy event to create similar one
- **Move event**: Change event time (drag-and-drop style)
- **Change calendar**: Move event to different calendar
- **Respond to invitation**: Accept/decline/tentative
- **Propose new time**: Suggest alternative time to organizer

## Calendar Operations

- **Create calendar**: Add new calendar
- **Rename calendar**: Change calendar name
- **Change calendar color**: Update visual appearance
- **Delete calendar**: Remove calendar and all events
- **Show/hide calendar**: Toggle calendar visibility
- **Set default calendar**: Choose where new events go

## Calendar Views and Display

While UES doesn't provide a visual interface, the state model supports common view queries:
- **Day view**: Events for a specific date
- **Week view**: Events for a date range (7 days)
- **Month view**: Events for an entire month
- **Agenda view**: Chronological list of upcoming events
- **Event list**: Filter and sort events by various criteria

## Time Zone Handling

- **Event time zones**: Each event stores its own time zone
- **User time zone**: Default time zone for display/entry
- **Cross-timezone events**: Events in different time zones than user
- **Time zone conversion**: Display events in user's current time zone
- **Floating times**: Events that follow user's time zone (e.g., "9am wherever I am")

## Features Explicitly Excluded

The following calendar features are **not** simulated to maintain simplicity:
- CalDAV/iCal protocol details
- Calendar server synchronization
- Calendar sharing permissions (read/write access control)
- Resource booking (conference rooms, equipment)
- Meeting room availability checking
- Enterprise resource scheduling
- Calendar delegation (assistant managing boss's calendar)
- Calendar publishing (public calendar URLs)
- Import/export file formats (ICS parsing)
- Birthday/holiday calendar subscriptions
- Task/todo integration (separate modality if needed)
- Complex recurrence rules (EXRULE, RDATE, EXDATE beyond basic exceptions)
- Working hours and availability settings
- Calendar analytics and insights

---

## Implementation Design

### Core Classes

#### `CalendarInput` (models/modalities/calendar_input.py)

The event payload for calendar operations (create, update, delete).

**Attributes:**
- `modality_type`: Always "calendar"
- `timestamp`: When this operation occurred (simulator time)
- `input_id`: Unique identifier for this input
- `operation`: Operation type - "create", "update", "delete"
- `event_id`: Event identifier (required for update/delete, auto-generated for create)
- `calendar_id`: Which calendar this event belongs to (default: "primary")
- `recurrence_scope`: For recurring events - "this", "this_and_future", "all" (default: "this")

**Event Data (for create/update operations):**
- `title`: Event title/summary (required for create)
- `description`: Event description/notes
- `start`: Start datetime (required for create)
- `end`: End datetime (required for create)
- `all_day`: Boolean - is this an all-day event
- `timezone`: Event time zone (defaults to user time zone)
- `location`: Event location
- `status`: "confirmed", "tentative", "cancelled"

**Attendee Data:**
- `organizer`: Organizer email address
- `attendees`: List of attendee objects with:
  - `email`: Attendee email
  - `display_name`: Optional attendee name
  - `optional`: Boolean - is attendance optional
  - `response`: "accepted", "declined", "tentative", "needs-action"
  - `comment`: Optional response comment

**Recurrence Data:**
- `recurrence`: Recurrence rule object (if recurring):
  - `frequency`: "daily", "weekly", "monthly", "yearly"
  - `interval`: Repeat every N periods (default: 1)
  - `days_of_week`: For weekly - list of days (["monday", "wednesday"])
  - `day_of_month`: For monthly - day number (1-31)
  - `month_of_year`: For yearly - month number (1-12)
  - `end_type`: "never", "until", "count"
  - `end_date`: End date (if end_type is "until")
  - `count`: Number of occurrences (if end_type is "count")
- `recurrence_exceptions`: List of dates to skip (YYYY-MM-DD)
- `recurrence_id`: For modified occurrences - which occurrence this is

**Reminder Data:**
- `reminders`: List of reminder objects:
  - `minutes_before`: Minutes before event to alert
  - `type`: "notification", "email", "both"

**Visual and Metadata:**
- `color`: Event color (hex code or color name)
- `visibility`: "public", "private", "default"
- `transparency`: "opaque" (blocks time), "transparent" (doesn't block)
- `attachments`: List of attachment objects (filename, size, mime_type, url/data)
- `conference_link`: Video conference URL

**Methods:**
- `validate_input()`: Validates operation type, required fields, time logic, recurrence consistency
- `get_affected_entities()`: Returns (calendar_id, event_id) tuple
- `get_summary()`: Human-readable summary (e.g., "Create event: Team Meeting on 2024-01-15 at 10:00")
- `should_merge_with()`: Returns False (each operation is distinct)

#### `CalendarState` (models/modalities/calendar_state.py)

Tracks all calendars and events with full history and recurrence expansion.

**Attributes:**
- `modality_type`: Always "calendar"
- `last_updated`: When state was last modified
- `update_count`: Number of operations applied
- `calendars`: Dict mapping calendar_id to `Calendar` objects
- `events`: Dict mapping event_id to `CalendarEvent` objects
- `default_calendar_id`: ID of default calendar (default: "primary")
- `user_timezone`: User's default time zone (default: "UTC")

**Helper Class - `Calendar`:**
- `calendar_id`: Unique calendar identifier
- `name`: Calendar display name
- `color`: Calendar color (hex code)
- `visible`: Boolean - is calendar currently shown
- `created_at`: When calendar was created
- `updated_at`: When calendar was last modified
- `event_ids`: Set of event IDs in this calendar
- `default_reminders`: List of default reminder settings

**Helper Class - `CalendarEvent`:**
- `event_id`: Unique event identifier
- `calendar_id`: Which calendar this belongs to
- `title`: Event title
- `description`: Event description
- `start`: Start datetime
- `end`: End datetime
- `all_day`: Boolean - all-day event flag
- `timezone`: Event time zone
- `location`: Event location
- `status`: Event status
- `organizer`: Organizer email
- `attendees`: List of attendee objects
- `recurrence`: Recurrence rule (if recurring)
- `recurrence_exceptions`: Set of skipped dates
- `recurrence_id`: If this is a modified occurrence
- `parent_event_id`: If this is modified occurrence, link to parent
- `reminders`: List of reminder objects
- `color`: Event color override
- `visibility`: Visibility level
- `transparency`: Free/busy transparency
- `attachments`: List of attachments
- `conference_link`: Video conference URL
- `created_at`: When event was created
- `updated_at`: When event was last modified
- `deleted_at`: If deleted, when (for recurrence handling)

**Methods:**
- `apply_input(input_data)`: Processes calendar operations
  - **Create**: Validates data, generates event_id, adds to calendar and events dict
  - **Update**: Handles recurrence scope (this/this_and_future/all), modifies event(s)
  - **Delete**: Handles recurrence scope, marks deleted or adds exceptions
- `get_snapshot()`: Returns all calendars and events for API responses
- `validate_state()`: Checks calendar/event consistency, time logic, recurrence validity
- `query(query_params)`: Filters events with complex criteria
  - Supports: calendar_id(s), start/end date range, search text, status, has_attendees, recurring, color, etc.
  - **Recurrence expansion**: Generates individual occurrences for recurring events in date range
- `get_events_for_date_range(start, end, calendar_ids, expand_recurring)`: Returns events in range
  - If expand_recurring=True, generates all recurring event instances
  - Applies recurrence exceptions
  - Handles modified occurrences
- `get_calendar(calendar_id)`: Returns calendar object
- `get_event(event_id)`: Returns event object
- `create_calendar(calendar_id, name, color)`: Helper to create new calendar
- `delete_calendar(calendar_id)`: Removes calendar and all its events
- `_expand_recurrence(event, start_date, end_date)`: Helper to generate recurring occurrences
- `_should_skip_occurrence(event, date)`: Helper to check recurrence exceptions
- `_handle_recurrence_update(event, input_data, scope)`: Helper for updating recurring events

### Design Decisions

**1. Recurrence Handling**

Recurring events present the most complex design challenge. Options:
- **Store each occurrence separately**: Inflates storage, complex rule changes
- **Store rule and expand on query**: Efficient storage, requires expansion logic
- **Hybrid approach**: Store rule + individual modifications

Solution: **Hybrid approach**
- Store parent event with recurrence rule
- Store modified occurrences as separate events with `parent_event_id` and `recurrence_id`
- Store exceptions as date set on parent event
- Expand occurrences on query within requested date range
- Updates with "this_and_future" create new recurrence rule from that date forward

**2. Multiple Calendars**

Users commonly separate events into multiple calendars (Work, Personal, Family). The state must:
- Track multiple calendars with independent settings
- Associate each event with a calendar
- Support showing/hiding calendars
- Allow moving events between calendars

Solution: Separate `Calendar` objects with `event_ids` sets for quick lookup.

**3. Time Zone Complexity**

Calendar events must handle:
- Events in different time zones than user
- User switching time zones (traveling)
- Displaying events in user's current time zone
- Preserving event's original time zone

Solution: Store all events with explicit time zones, track user's current time zone separately, convert on query/display.

**4. Attendee Management**

For testing AI assistants that schedule meetings:
- Track organizer vs attendees
- Track each attendee's response status
- Support optional attendees
- Allow assistant to respond to invitations

Solution: Each event stores full attendee list with response status. Input operations support response updates.

**5. Event Updates and History**

Calendar operations need to:
- Modify existing events
- Track what changed over time (for AI learning)
- Handle partial updates (only change some fields)

Solution: Store `updated_at` timestamp, support partial updates where only provided fields change.

**6. All-Day Events**

All-day events don't have specific times and are date-based. They must:
- Not have hour/minute times
- Display as full-day blocks
- Handle multi-day spanning (vacation, conference)

Solution: `all_day` boolean flag, store start/end as dates only (00:00 times), special handling in queries.

**7. Event Attachments**

Modern calendars support file attachments. For UES:
- Store metadata (filename, size, type)
- Reference content by URL or inline data
- Avoid complex file storage implementation

Solution: Store attachment list with metadata, defer actual file content to test design.

**8. Free/Busy Status**

Calendars track whether events block time for scheduling. This affects:
- Meeting scheduling (finding free slots)
- Out-of-office indicators
- Tentative vs confirmed blocking

Solution: `transparency` field (opaque/transparent) + `status` field (confirmed/tentative/cancelled) provide full semantics.

---

## API Query Patterns

The `CalendarState.query()` method should support common use cases:

### Get Today's Events
```python
query({
    "date": "2024-01-15",  # or use start/end for same date
    "calendar_ids": ["primary", "work"],
    "expand_recurring": True
})
```

### Get Week's Events
```python
query({
    "start": "2024-01-15",
    "end": "2024-01-21",
    "expand_recurring": True
})
```

### Search for Events
```python
query({
    "search": "team meeting",
    "start": "2024-01-01",  # optional date range
    "end": "2024-12-31"
})
```

### Get Events with Specific Attendee
```python
query({
    "attendee_email": "colleague@example.com",
    "start": "2024-01-01"
})
```

### Get Upcoming Events
```python
query({
    "start": "<current_simulator_time>",
    "limit": 10,
    "expand_recurring": True
})
```

### Get Recurring Events Only
```python
query({
    "recurring": True,
    "calendar_ids": ["primary"]
})
```

---

## Example Event Structures

### Simple One-Time Event
```python
CalendarInput(
    operation="create",
    calendar_id="primary",
    title="Dentist Appointment",
    start=datetime(2024, 1, 15, 14, 0),
    end=datetime(2024, 1, 15, 15, 0),
    location="123 Main St, Suite 200",
    reminders=[{"minutes_before": 60, "type": "notification"}]
)
```

### All-Day Event
```python
CalendarInput(
    operation="create",
    calendar_id="personal",
    title="Vacation",
    start=date(2024, 7, 1),
    end=date(2024, 7, 7),
    all_day=True,
    transparency="transparent"  # Doesn't block time
)
```

### Recurring Weekly Meeting
```python
CalendarInput(
    operation="create",
    calendar_id="work",
    title="Team Standup",
    start=datetime(2024, 1, 15, 9, 0),
    end=datetime(2024, 1, 15, 9, 30),
    recurrence={
        "frequency": "weekly",
        "interval": 1,
        "days_of_week": ["monday", "wednesday", "friday"],
        "end_type": "never"
    },
    reminders=[{"minutes_before": 15, "type": "notification"}]
)
```

### Meeting with Attendees
```python
CalendarInput(
    operation="create",
    calendar_id="work",
    title="Project Planning",
    start=datetime(2024, 1, 20, 14, 0),
    end=datetime(2024, 1, 20, 15, 30),
    location="Conference Room A",
    organizer="me@example.com",
    attendees=[
        {
            "email": "alice@example.com",
            "display_name": "Alice Smith",
            "optional": False,
            "response": "accepted"
        },
        {
            "email": "bob@example.com",
            "display_name": "Bob Jones",
            "optional": True,
            "response": "tentative"
        }
    ],
    conference_link="https://meet.google.com/abc-defg-hij"
)
```

### Skipping Recurring Event Occurrence
```python
# First create the recurring event (above)
# Then add exception for a specific date
CalendarInput(
    operation="update",
    event_id="recurring-standup-id",
    recurrence_scope="this",  # Just this occurrence
    recurrence_exceptions=["2024-01-17"]  # Skip MLK Day
)
```

### Modifying Single Recurring Occurrence
```python
CalendarInput(
    operation="update",
    event_id="recurring-standup-id",
    recurrence_scope="this",
    recurrence_id="2024-01-22",  # Which occurrence to modify
    start=datetime(2024, 1, 22, 10, 0),  # Move from 9am to 10am just this once
    end=datetime(2024, 1, 22, 10, 30)
)
```

---

## State Initialization

When a new simulation starts, `CalendarState` should initialize with:
- One "primary" calendar (id: "primary", name: "Personal", color: "#4285f4")
- Empty events dict
- User timezone set to "UTC" (or from config)

Additional calendars can be created via input events or configuration.
