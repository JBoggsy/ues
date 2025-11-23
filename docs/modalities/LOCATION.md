# Location Modality Design

The Location modality simulates user location tracking for testing AI personal assistants. It provides geographic coordinates, human-readable addresses, and location metadata to enable testing of location-aware features like navigation, reminders, travel planning, and context-based assistance.

## Location Data

- **Geographic coordinates**: Latitude and longitude in decimal degrees
- **Address**: Human-readable street address or location description
- **Named locations**: Semantic labels like "Home", "Office", "Gym", "Starbucks on Main St"
- **Altitude**: Elevation above sea level in meters
- **Accuracy**: Position accuracy radius in meters (GPS uncertainty)
- **Speed**: Movement speed in meters per second
- **Bearing**: Direction of travel in degrees (0-360, where 0 is North)

## Location Metadata

- **Timestamp**: When the location update occurred (simulator time)
- **Location history**: Ordered list of previous locations with timestamps
- **Update count**: Number of location changes
- **Last updated**: When the location was last modified

## Location Features

- **Single user tracking**: Tracks one user's location at a time
- **History management**: Maintains configurable history of recent locations
- **Named location support**: Allows semantic labeling of frequently visited places
- **Movement tracking**: Speed and bearing for simulating travel
- **Accuracy simulation**: Models GPS uncertainty for realistic scenarios

## Use Cases

### Location-Aware Reminders
```
Test: User arrives at "Grocery Store"
Expected: Assistant reminds "Don't forget to buy milk"
```

### Travel Detection
```
Test: User location changes rapidly with high speed
Expected: Assistant recognizes user is traveling
```

### Context-Based Suggestions
```
Test: User at "Office" during lunch hours
Expected: Assistant suggests nearby restaurants
```

### Location History Queries
```
Test: Query "Where was I last Tuesday at 3pm?"
Expected: Assistant retrieves historical location data
```

## Features Explicitly Excluded

The following location features are **not** simulated to maintain simplicity:
- Multi-user location tracking (only tracks one user)
- Geofencing and zone definitions
- Location sharing with other users
- Turn-by-turn navigation
- Points of interest (POI) database
- Reverse geocoding (coordinate → address conversion)
- Forward geocoding (address → coordinate lookup)
- Route calculation and traffic data
- Location permissions and privacy settings
- Indoor positioning systems
- Bluetooth beacon detection
- Wi-Fi positioning
- Cell tower triangulation

---

## Implementation Design

### Core Classes

#### `LocationInput` (models/modalities/location_input.py)

The event payload for updating user location.

**Attributes:**
- `modality_type`: Always "location"
- `timestamp`: When this location update occurred (simulator time)
- `input_id`: Unique identifier for this update (auto-generated UUID)
- `latitude`: Latitude in decimal degrees (-90 to 90) **[Required]**
- `longitude`: Longitude in decimal degrees (-180 to 180) **[Required]**
- `address`: Human-readable address or description (optional)
- `named_location`: Semantic location name like "Home" or "Office" (optional)
- `altitude`: Altitude in meters above sea level (optional)
- `accuracy`: Accuracy radius in meters (optional)
- `speed`: Speed in meters per second (optional)
- `bearing`: Bearing/heading in degrees (0-360, 0=North) (optional)

**Field Validation:**
- `latitude`: Must be between -90 and 90
- `longitude`: Must be between -180 and 180
- `accuracy`: Must be non-negative if provided
- `speed`: Must be non-negative if provided
- `bearing`: Must be between 0 and 360 if provided

**Methods:**
- `validate_input()`: All validation handled by field validators
- `get_affected_entities()`: Returns `["user_location"]` and optionally `f"location:{named_location}"`
- `get_summary()`: Returns human-readable description
  - With name and address: `"At Office: 123 Main St (40.7128, -74.0060)"`
  - With address only: `"Moved to 123 Main St (40.7128, -74.0060)"`
  - With name only: `"At Office (40.7128, -74.0060)"`
  - Coordinates only: `"Location update: (40.7128, -74.0060)"`
- `should_merge_with(other)`: Merges if same named_location and within 1 second (prevents duplicate rapid updates)

**Example Usage:**
```python
from datetime import datetime
from models.modalities.location_input import LocationInput

# Basic location update
location = LocationInput(
    timestamp=datetime.now(),
    latitude=40.7128,
    longitude=-74.0060,
    address="New York, NY"
)

# Named location with metadata
home = LocationInput(
    timestamp=datetime.now(),
    latitude=34.0522,
    longitude=-118.2437,
    address="123 Main St, Los Angeles, CA",
    named_location="Home",
    accuracy=10.0
)

# Moving vehicle with speed and bearing
moving = LocationInput(
    timestamp=datetime.now(),
    latitude=37.7749,
    longitude=-122.4194,
    speed=15.6,  # ~35 mph
    bearing=45.0,  # Northeast
    accuracy=5.0
)
```

#### `LocationHistoryEntry` (Helper Class)

Pydantic model for storing historical location data.

**Attributes:**
- `timestamp`: When the user was at this location
- `latitude`: Latitude coordinate
- `longitude`: Longitude coordinate
- `address`: Human-readable address (optional)
- `named_location`: Semantic location name (optional)
- `altitude`: Altitude in meters (optional)
- `accuracy`: Accuracy radius in meters (optional)
- `speed`: Speed in meters per second (optional)
- `bearing`: Bearing in degrees (optional)

**Methods:**
- `to_dict()`: Converts entry to dictionary for API responses, omitting None values

#### `LocationState` (models/modalities/location_state.py)

Tracks the user's current location and maintains location history.

**Attributes:**
- `modality_type`: Always "location"
- `last_updated`: When state was last modified (simulator time)
- `update_count`: Number of location updates applied
- `current_latitude`: Current latitude (None if no location set)
- `current_longitude`: Current longitude (None if no location set)
- `current_address`: Current address (optional)
- `current_named_location`: Current location name (optional)
- `current_altitude`: Current altitude in meters (optional)
- `current_accuracy`: Current accuracy in meters (optional)
- `current_speed`: Current speed in m/s (optional)
- `current_bearing`: Current bearing in degrees (optional)
- `location_history`: List of `LocationHistoryEntry` objects
- `max_history_size`: Maximum history entries to retain (default: 100)

**Methods:**

##### `apply_input(input_data: LocationInput)`
Updates current location and adds previous location to history.
1. If current location exists, creates `LocationHistoryEntry` from current values
2. Appends entry to history
3. Trims history to `max_history_size` if needed
4. Updates all current_* fields from input
5. Updates `last_updated` and increments `update_count`

##### `get_snapshot() -> dict`
Returns complete state for API responses:
```json
{
  "modality_type": "location",
  "last_updated": "2024-03-15T14:30:00Z",
  "update_count": 5,
  "current": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "address": "New York, NY",
    "named_location": "Office",
    "accuracy": 10.0
  },
  "history": [
    {
      "timestamp": "2024-03-15T09:00:00Z",
      "latitude": 34.0522,
      "longitude": -118.2437,
      "address": "Los Angeles, CA",
      "named_location": "Home"
    }
  ]
}
```

##### `validate_state() -> list[str]`
Checks state consistency:
- Both current coordinates set or both None
- Current latitude in valid range (-90 to 90)
- Current longitude in valid range (-180 to 180)
- History entries in chronological order
- History size doesn't exceed maximum

Returns list of error messages (empty if valid).

##### `query(query_params: dict) -> dict`
Filters location history by criteria:

**Supported Parameters:**
- `since`: datetime - Return locations after this time
- `until`: datetime - Return locations before this time
- `named_location`: str - Filter by location name
- `limit`: int - Maximum results to return
- `include_current`: bool - Include current location (default: True)

**Returns:**
```json
{
  "results": [
    {
      "timestamp": "2024-03-15T14:30:00Z",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "named_location": "Office",
      "is_current": true
    }
  ],
  "count": 1
}
```

## API Usage Patterns

### Set Initial Location
```python
# Via Event
POST /events
{
  "scheduled_time": "2024-03-15T09:00:00Z",
  "modality": "location",
  "data": {
    "latitude": 34.0522,
    "longitude": -118.2437,
    "address": "123 Main St, Los Angeles, CA",
    "named_location": "Home"
  }
}
```

### Update Location (Movement)
```python
# User travels to new location
POST /events
{
  "scheduled_time": "2024-03-15T10:00:00Z",
  "modality": "location",
  "data": {
    "latitude": 34.0689,
    "longitude": -118.4452,
    "address": "Santa Monica, CA",
    "speed": 13.4,  # ~30 mph
    "bearing": 270.0  # West
  }
}
```

### Query Current Location
```python
GET /environment/modalities/location
# Returns current location snapshot
```

### Query Location History
```python
POST /environment/modalities/location/query
{
  "since": "2024-03-15T00:00:00Z",
  "until": "2024-03-15T23:59:59Z",
  "limit": 10
}
# Returns up to 10 locations from March 15th
```

### Query Named Locations
```python
POST /environment/modalities/location/query
{
  "named_location": "Office",
  "limit": 5
}
# Returns last 5 times user was at "Office"
```

## Design Decisions

### 1. Single User Only

**Decision**: Track only one user's location per simulation.

**Rationale**: 
- Most personal assistants serve a single user
- Multi-user tracking adds significant complexity
- Can be extended later if needed

### 2. History Management

**Decision**: Maintain configurable history with automatic pruning.

**Rationale**:
- Location history grows unbounded without limits
- Querying "where was I last week?" requires history
- Oldest entries least useful, safe to discard

### 3. Named Locations

**Decision**: Support optional semantic labels for locations.

**Rationale**:
- Users think in terms of "Home", "Work", not coordinates
- Enables natural language queries
- No separate location database needed

### 4. No Geocoding Services

**Decision**: Don't provide address ↔ coordinate conversion.

**Rationale**:
- Requires external API dependencies
- Adds complexity and potential failures
- Test scenarios can provide both explicitly

### 5. Merge Rapid Updates

**Decision**: Allow merging location updates within 1 second.

**Rationale**:
- GPS updates often occur multiple times per second
- Prevents cluttered event logs
- Only merges if same named_location (different places are distinct)

### 6. Optional Metadata Fields

**Decision**: Make most fields optional except lat/lon.

**Rationale**:
- GPS doesn't always provide all data (altitude, bearing, etc.)
- Flexibility for different testing scenarios
- Coordinates are sufficient for basic location tracking

## Testing Patterns

### Test Location Changes
```python
# Set initial location
location_state.apply_input(LocationInput(
    timestamp=now,
    latitude=40.7128,
    longitude=-74.0060,
    named_location="Office"
))

# Verify current location
assert location_state.current_named_location == "Office"
assert len(location_state.location_history) == 0

# Change location
location_state.apply_input(LocationInput(
    timestamp=now + timedelta(hours=1),
    latitude=40.7589,
    longitude=-73.9851,
    named_location="Home"
))

# Verify history updated
assert location_state.current_named_location == "Home"
assert len(location_state.location_history) == 1
assert location_state.location_history[0].named_location == "Office"
```

### Test History Limits
```python
# Add more locations than max_history_size
for i in range(150):
    location_state.apply_input(LocationInput(
        timestamp=now + timedelta(minutes=i),
        latitude=40.0 + i * 0.01,
        longitude=-74.0
    ))

# Verify oldest entries pruned
assert len(location_state.location_history) <= location_state.max_history_size
```

### Test Query Filtering
```python
# Query specific time range
results = location_state.query({
    "since": today_morning,
    "until": today_evening,
    "named_location": "Office"
})

# Verify only matching entries returned
assert all(r["named_location"] == "Office" for r in results["results"])
```
