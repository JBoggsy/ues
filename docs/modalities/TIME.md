# Time Modality Design

The Time modality simulates user preferences for time and date display formatting. This does **NOT** control simulator time (which is managed by `SimulatorTime` in the core infrastructure) - instead, it tracks how the user wants time to be **displayed** to them, including timezone, 12-hour vs 24-hour format, date formatting, and localization preferences.

**Important Distinction**: 
- **SimulatorTime**: The virtual clock of the simulation itself (managed by simulation engine)
- **Time Modality**: User's display preferences for how time should be shown (managed by this modality)

## Time Display Preferences

- **Timezone**: IANA timezone identifier (e.g., "America/New_York", "Europe/London", "Asia/Tokyo")
- **Time format**: 12-hour (AM/PM) or 24-hour clock
- **Date format**: How dates are formatted (MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, etc.)
- **Locale**: Language and region for localized formatting (e.g., "en_US", "en_GB", "fr_FR")
- **Week start**: Which day starts the week (Sunday or Monday)

## Time Metadata

- **Timestamp**: When the preference change occurred (simulator time)
- **Settings history**: Ordered list of previous preference changes
- **Update count**: Number of preference updates
- **Last updated**: When preferences were last modified

## Time Features

- **Timezone tracking**: Maintains user's current timezone preference
- **Format preferences**: Tracks time and date display formats
- **History management**: Maintains configurable history of preference changes
- **Localization support**: Enables region-specific formatting
- **Calendar settings**: Week start day preference

## Use Cases

### Timezone Changes During Travel
```
Test: User travels from New York to London
Event: TimeInput with timezone="Europe/London"
Expected: Assistant displays times in London timezone
```

### Format Preference Updates
```
Test: User switches from 12-hour to 24-hour format
Event: TimeInput with format_preference="24h"
Expected: Assistant shows "14:30" instead of "2:30 PM"
```

### Localization
```
Test: User changes locale to French
Event: TimeInput with locale="fr_FR", date_format="DD/MM/YYYY"
Expected: Assistant displays dates European-style
```

### Query Preference History
```
Test: Query "What was my timezone last week?"
Expected: Assistant retrieves historical timezone settings
```

## Features Explicitly Excluded

The following time features are **not** simulated to maintain simplicity:
- Simulator time control (use `SimulatorTime` instead)
- Automatic timezone detection from location
- Daylight saving time calculations (handled by Python's zoneinfo)
- World clock or multiple timezone tracking
- Time zone conversion utilities
- Calendar synchronization
- Natural language time parsing
- Recurring schedule definitions
- Alarm and timer functionality
- Time-based automation rules

---

## Implementation Design

### Core Classes

#### `TimeInput` (models/modalities/time_input.py)

The event payload for updating time display preferences.

**Attributes:**
- `modality_type`: Always "time"
- `timestamp`: When this preference change occurred (simulator time)
- `input_id`: Unique identifier for this update (auto-generated UUID)
- `timezone`: IANA timezone identifier **[Required]**
- `format_preference`: "12h" or "24h" **[Required]**
- `date_format`: Date format string (optional)
  - Valid formats: "MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD", "YYYY/MM/DD", "DD.MM.YYYY", "DD-MM-YYYY"
- `locale`: Locale identifier for localized formatting (optional)
- `week_start`: "sunday" or "monday" (optional)

**Field Validation:**
- `timezone`: Must be a valid IANA timezone identifier (validated using `zoneinfo.ZoneInfo`)
- `format_preference`: Must be exactly "12h" or "24h" (Literal type)
- `date_format`: Must be one of the predefined valid formats
- `week_start`: Must be exactly "sunday" or "monday" if provided

**Methods:**
- `validate_input()`: All validation handled by field validators
- `get_affected_entities()`: Returns `["user_time_preferences"]`
- `get_summary()`: Returns human-readable description
  - Basic: `"Changed timezone to America/New_York (12h format)"`
  - With date format: `"Changed timezone to Europe/London (24h format, DD/MM/YYYY)"`
  - Multiple changes: `"Updated time settings: timezone to Asia/Tokyo, 24h format, locale: ja_JP"`
- `should_merge_with(other)`: Merges if changes within 5 seconds (rapid preference adjustments)

**Example Usage:**
```python
from datetime import datetime
from models.modalities.time_input import TimeInput

# Basic timezone change
time_update = TimeInput(
    timestamp=datetime.now(),
    timezone="America/New_York",
    format_preference="12h"
)

# Complete preference update
full_update = TimeInput(
    timestamp=datetime.now(),
    timezone="Europe/London",
    format_preference="24h",
    date_format="DD/MM/YYYY",
    locale="en_GB",
    week_start="monday"
)

# Format change only (timezone required)
format_change = TimeInput(
    timestamp=datetime.now(),
    timezone="UTC",  # Must provide current timezone
    format_preference="24h"
)
```

#### `TimeSettingsHistoryEntry` (Helper Class)

Pydantic model for storing historical time preference data.

**Attributes:**
- `timestamp`: When this settings change occurred
- `timezone`: Timezone identifier at this point
- `format_preference`: Time format preference at this point
- `date_format`: Date format preference if set (optional)
- `locale`: Locale identifier if set (optional)
- `week_start`: Week start preference if set (optional)

**Methods:**
- `to_dict()`: Converts entry to dictionary for API responses, omitting None values

#### `TimeState` (models/modalities/time_state.py)

Tracks the user's current time display preferences and maintains preference history.

**Attributes:**
- `modality_type`: Always "time"
- `last_updated`: When state was last modified (simulator time)
- `update_count`: Number of preference updates applied
- `timezone`: Current timezone (default: "UTC")
- `format_preference`: Current time format (default: "12h")
- `date_format`: Current date format (optional)
- `locale`: Current locale (optional)
- `week_start`: Current week start preference (optional)
- `settings_history`: List of `TimeSettingsHistoryEntry` objects
- `max_history_size`: Maximum history entries to retain (default: 50)

**Methods:**

##### `apply_input(input_data: TimeInput)`
Updates current preferences and adds previous settings to history.
1. Creates `TimeSettingsHistoryEntry` from current values
2. Appends entry to history
3. Trims history to `max_history_size` if needed
4. Updates all preference fields from input
5. Updates `last_updated` and increments `update_count`

**Note**: Unlike location state, time state always creates a history entry (even on first update) since default values exist.

##### `get_snapshot() -> dict`
Returns complete state for API responses:
```json
{
  "modality_type": "time",
  "last_updated": "2024-03-15T14:30:00Z",
  "update_count": 3,
  "current": {
    "timezone": "Europe/London",
    "format_preference": "24h",
    "date_format": "DD/MM/YYYY",
    "locale": "en_GB",
    "week_start": "monday"
  },
  "history": [
    {
      "timestamp": "2024-03-15T09:00:00Z",
      "timezone": "America/New_York",
      "format_preference": "12h",
      "date_format": "MM/DD/YYYY"
    },
    {
      "timestamp": "2024-03-15T12:00:00Z",
      "timezone": "UTC",
      "format_preference": "24h"
    }
  ]
}
```

##### `validate_state() -> list[str]`
Checks state consistency:
- Current timezone is valid (can be loaded with `zoneinfo.ZoneInfo`)
- History entries in chronological order
- History size doesn't exceed maximum

Returns list of error messages (empty if valid).

##### `query(query_params: dict) -> dict`
Filters settings history by criteria:

**Supported Parameters:**
- `since`: datetime - Return settings changes after this time
- `until`: datetime - Return settings changes before this time
- `timezone`: str - Filter by timezone
- `format_preference`: str - Filter by format ("12h" or "24h")
- `limit`: int - Maximum results to return
- `include_current`: bool - Include current settings (default: True)

**Returns:**
```json
{
  "results": [
    {
      "timestamp": "2024-03-15T14:30:00Z",
      "timezone": "Europe/London",
      "format_preference": "24h",
      "date_format": "DD/MM/YYYY",
      "is_current": true
    }
  ],
  "count": 1
}
```

## API Usage Patterns

### Set Initial Time Preferences
```python
# Via Event
POST /events
{
  "scheduled_time": "2024-03-15T09:00:00Z",
  "modality": "time",
  "data": {
    "timezone": "America/New_York",
    "format_preference": "12h",
    "date_format": "MM/DD/YYYY",
    "locale": "en_US",
    "week_start": "sunday"
  }
}
```

### Update Timezone (Travel)
```python
# User travels to different timezone
POST /events
{
  "scheduled_time": "2024-03-15T18:00:00Z",
  "modality": "time",
  "data": {
    "timezone": "Europe/London",
    "format_preference": "24h",
    "date_format": "DD/MM/YYYY"
  }
}
```

### Change Format Preference
```python
# User switches to 24-hour format
POST /events
{
  "scheduled_time": "2024-03-15T14:00:00Z",
  "modality": "time",
  "data": {
    "timezone": "America/New_York",  # Keep current timezone
    "format_preference": "24h"
  }
}
```

### Query Current Preferences
```python
GET /environment/modalities/time
# Returns current time preferences snapshot
```

### Query Preference History
```python
POST /environment/modalities/time/query
{
  "since": "2024-03-01T00:00:00Z",
  "until": "2024-03-31T23:59:59Z"
}
# Returns all preference changes in March
```

### Query Specific Timezone Usage
```python
POST /environment/modalities/time/query
{
  "timezone": "Europe/London",
  "limit": 10
}
# Returns last 10 times user had London timezone
```

## Design Decisions

### 1. Separate from Simulator Time

**Decision**: Time modality tracks display preferences, not simulation time.

**Rationale**: 
- Simulator time is core infrastructure concern
- Display preferences are user-specific settings
- Clear separation of concerns
- Avoids confusion between "what time is it in the simulation" vs "how should time be displayed"

### 2. Always Require Timezone

**Decision**: Both `timezone` and `format_preference` are required fields.

**Rationale**:
- Every time update should specify complete context
- Prevents partial state updates that might be confusing
- Makes event semantics clear
- Default to UTC if no preference ever set

### 3. Limited Date Format Options

**Decision**: Restrict date formats to 6 predefined patterns.

**Rationale**:
- Covers most common international formats
- Prevents arbitrary format strings (security/validation)
- Easy to validate and document
- Can be extended later if needed

### 4. Merge Rapid Changes

**Decision**: Allow merging preference changes within 5 seconds.

**Rationale**:
- Users often make multiple quick adjustments
- Prevents cluttered event logs
- Longer window than location (1s) since settings changes are more deliberate

### 5. History Management

**Decision**: Maintain configurable history with automatic pruning (default: 50 entries).

**Rationale**:
- Preference changes infrequent compared to location
- Smaller default history (50 vs location's 100)
- Still enables "what timezone was I using last month?" queries
- Prevents unbounded growth

### 6. No Automatic Timezone Detection

**Decision**: Don't automatically update timezone based on location.

**Rationale**:
- Requires cross-modality logic (complex)
- Not all location changes mean timezone changes (e.g., near timezone boundaries)
- Explicit events make simulation behavior predictable
- Can be implemented as agent behavior if needed

### 7. Week Start Preference

**Decision**: Support Sunday or Monday as week start.

**Rationale**:
- Major cultural difference (US vs Europe/most of world)
- Affects calendar display significantly
- Simple binary choice
- Important for assistant calendar features

## Testing Patterns

### Test Preference Changes
```python
# Set initial preferences
time_state.apply_input(TimeInput(
    timestamp=now,
    timezone="America/New_York",
    format_preference="12h",
    date_format="MM/DD/YYYY"
))

# Verify current preferences
assert time_state.timezone == "America/New_York"
assert time_state.format_preference == "12h"
assert len(time_state.settings_history) == 1  # Default settings saved

# Change preferences
time_state.apply_input(TimeInput(
    timestamp=now + timedelta(hours=1),
    timezone="Europe/London",
    format_preference="24h"
))

# Verify history updated
assert time_state.timezone == "Europe/London"
assert len(time_state.settings_history) == 2
assert time_state.settings_history[1].timezone == "America/New_York"
```

### Test Timezone Validation
```python
# Invalid timezone should raise error
with pytest.raises(ValueError, match="Invalid timezone"):
    TimeInput(
        timestamp=now,
        timezone="Invalid/Timezone",
        format_preference="12h"
    )
```

### Test History Limits
```python
# Add more changes than max_history_size
for i in range(75):
    time_state.apply_input(TimeInput(
        timestamp=now + timedelta(hours=i),
        timezone="UTC",
        format_preference="12h" if i % 2 == 0 else "24h"
    ))

# Verify oldest entries pruned
assert len(time_state.settings_history) <= time_state.max_history_size
```

### Test Query Filtering
```python
# Query specific timezone usage
results = time_state.query({
    "timezone": "Europe/London",
    "limit": 5
})

# Verify only matching entries returned
assert all(r["timezone"] == "Europe/London" for r in results["results"])
```

## Integration with Other Modalities

### Calendar Modality
Time preferences affect how calendar events are displayed:
- Event times shown in user's current timezone
- Date formatting follows user preference
- Week view respects week_start preference

### Location Modality
While location can suggest timezone changes, they remain independent:
- Location tracks physical position
- Time tracks display preferences
- Agent can correlate (e.g., "user in London → suggest London timezone")

### Chat Modality
Time preferences affect timestamp display in conversations:
- Message timestamps shown in user's timezone
- Format follows user's preference (12h/24h)
- Date formatting applied to message grouping
