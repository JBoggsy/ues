# Weather Modality Design

The weather modality allows the UES to provide simulated weather data via its REST API,
allowing the developer to test an agent's weather-based capabilities. The UES allows specifying the
simulated weather at multiple locations and allows creating weather events which update the weather
at these locations as part of the simulation. In order to provide a realistic interface for the
tested agent, the UES provides realistic weather data based on (but not identical to) the
[OpenWeather One Call API](https://openweathermap.org/api/one-call-3) format.

## Data Model Design

### Core Classes

#### `WeatherInput` (models/modalities/weather_input.py)

The event payload for updating weather at a location. Unlike location and time modalities,
weather supports multiple locations simultaneously.

**Attributes:**
- `modality_type`: Always "weather"
- `timestamp`: When this weather update occurred (simulator time)
- `input_id`: Unique identifier for this update
- `latitude`: Location latitude (-90 to 90)
- `longitude`: Location longitude (-180 to 180)
- `report`: Complete weather report conforming to OpenWeather API format (see below)

**Helper Models (for report structure):**
- `WeatherCondition`: Single weather condition (id, main, description, icon)
- `CurrentWeather`: Current conditions (temp, feels_like, pressure, humidity, etc.)
- `MinutelyForecast`: Minute-by-minute precipitation (dt, precipitation)
- `HourlyForecast`: Hourly forecast data (dt, temp, weather conditions, pop, etc.)
- `DailyTemperature`: Daily temperature breakdown (day, min, max, night, eve, morn)
- `DailyFeelsLike`: Daily feels_like breakdown (day, night, eve, morn)
- `DailyForecast`: Daily forecast (dt, sunrise, sunset, temp, feels_like, weather, etc.)
- `WeatherAlert`: Alert information (sender_name, event, start, end, description, tags)
- `WeatherReport`: Complete report (lat, lon, timezone, timezone_offset, current, minutely, hourly, daily, alerts)

**Methods:**
- `validate_input()`: Validates coordinates and report consistency
- `get_affected_entities()`: Returns location identifier (lat,lon tuple)
- `get_summary()`: Human-readable summary (e.g., "Weather at (40.7128, -74.0060): Cloudy, 72°F")
- `should_merge_with()`: Returns False (weather updates should not merge)

#### `WeatherState` (models/modalities/weather_state.py)

Tracks current weather conditions at multiple locations with historical data.

**Attributes:**
- `modality_type`: Always "weather"
- `last_updated`: When state was last modified
- `update_count`: Number of updates applied
- `locations`: Dict mapping (lat, lon) tuples to `WeatherLocationState` objects
- `max_history_per_location`: Maximum historical reports per location (default: 100)

**Helper Class:**
- `WeatherLocationState`: State for a single location
  - `latitude`: Location latitude
  - `longitude`: Location longitude
  - `current_report`: Current weather report (WeatherReport)
  - `report_history`: List of historical reports with timestamps
  - `first_seen`: When this location was first added
  - `last_updated`: When this location was last updated
  - `update_count`: Number of updates for this location

**Methods:**
- `apply_input(input_data)`: Adds/updates weather for a location
  - Extracts lat/lon from input
  - Creates location entry if new
  - Adds current report to history
  - Sets new current report
  - Manages history size
  - Updates timestamps and counters
- `get_snapshot()`: Returns all locations and their current weather
- `validate_state()`: Checks location coordinate validity, history ordering
- `query(query_params)`: Filters weather data
  - Supports: lat/lon (required), exclude (parts), units (conversion), from/to (time range)
- `_convert_units(report, units)`: Helper to convert between standard/metric/imperial
- `_filter_report(report, exclude)`: Helper to remove excluded sections
- `_get_location_key(lat, lon)`: Normalizes coordinates to location key (rounds to ~1km precision)

### Design Decisions

**1. Multi-Location Storage**

Unlike location/time which track single user state, weather must support multiple locations
simultaneously. A tested agent might query weather for multiple cities in one simulation.

Solution: `WeatherState.locations` is a dict keyed by normalized (lat, lon) tuples. Coordinates
are rounded to ~0.01 degrees (~1km) to prevent duplicate nearby locations.

**2. REST API vs Event Pipeline**

State updates flow through the event pipeline:
- Event pipeline: `SimulatorEvent` → `WeatherInput` → `WeatherState.apply_input()`
- REST API update: `POST /weather/update` → `WeatherInput` → `apply_input()`

Solution: All state updates flow through `apply_input()`. This keeps the update logic centralized.

**3. Complex Data Structures**

Weather reports have deeply nested structures (minutely/hourly/daily forecasts with many fields).

Solution: Define comprehensive Pydantic models for all nested structures. This provides:
- Type safety and validation
- Clear documentation of expected format
- Easy serialization/deserialization
- Compatibility with OpenWeather API data format

**4. Unit Conversions**

Queries can request different unit systems (standard/metric/imperial).

Solution: Store all weather internally in standard units (Kelvin, m/s). Convert on query
using `_convert_units()` helper. This prevents confusion about what units are stored.

**5. Historical Data Management**

Weather changes frequently, so history can grow large.

Solution: Each location tracks its own history with configurable max size
(`max_history_per_location`). When querying with `from` parameter, return all matching
reports in chronological order. Without `from`, return only current report.

## REST API Querying

Simulated weather data is retrieved using the normal UES REST API, offering three forms of retrieval:

- `GET /weather/state`: Retrieves the current weather state for all tracked locations
- `POST /weather/query`: Retrieves weather data based on query parameters (location, filters, units) 

### Weather Query Filters
- `lat` (required): Latitude, decimal (-90; 90)
- `lon` (required): Longitude, decimal (-180; 180)
- `exclude` [optional]: By using this parameter you can exclude some parts of the weather data from
  the API response. It should be a comma-delimited list (without spaces). Available values:
  * `current`
  * `minutely`
  * `hourly`
  * `daily`
  * `alerts`
- `units` [optional]: Units of measurement. `standard`, `metric` and `imperial` units are available. If
  you do not use the units parameter, `standard` units will be applied by default. Unit types:
  * `standard`: temperature in Kelvin, wind speed in m/s
  * `imperial`: temperature in Fahrenheit, wind speed in mph
  * `metric`: temperature in Celcis, wind speed in m/s
- `from` [optional]: Timestamp in seconds. All weather reports for the queried location since this
  time are returned. Other filters are applied to each report.
- `to` [optional]: Timestamp in seconds. If `from` is specified and prior to this, only weather
  reports in the specified timeframe are returned. If `from` is not specified or is after `to`, `to`
  is ignored.

### Return Format
The UES returns weather data as a list of JSON objects, where each object in the list is the weather
report. If `from` is not specified, there will only be one weather report in the list, otherwise the
weather reports in the list are in sorted in order of recency. See the [OpenWeather API
format](https://openweathermap.org/api/one-call-3) for details on the response fields. The return format is below:

```json
[
    {
        "lat":33.44,
        "lon":-94.04,
        "timezone":"America/Chicago",
        "timezone_offset":-18000,
        "current":{
            "dt":1684929490,
            "sunrise":1684926645,
            "sunset":1684977332,
            "temp":292.55,
            "feels_like":292.87,
            "pressure":1014,
            "humidity":89,
            "dew_point":290.69,
            "uvi":0.16,
            "clouds":53,
            "visibility":10000,
            "wind_speed":3.13,
            "wind_deg":93,
            "wind_gust":6.71,
            "weather":[
                {
                    "id":803,
                    "main":"Clouds",
                    "description":"broken clouds",
                    "icon":"04d"
                }
            ]
        },
        "minutely":[
            {
                "dt":1684929540,
                "precipitation":0
            },
            ...
        ],
        "hourly":[
            {
                "dt":1684926000,
                "temp":292.01,
                "feels_like":292.33,
                "pressure":1014,
                "humidity":91,
                "dew_point":290.51,
                "uvi":0,
                "clouds":54,
                "visibility":10000,
                "wind_speed":2.58,
                "wind_deg":86,
                "wind_gust":5.88,
                "weather":[
                    {
                    "id":803,
                    "main":"Clouds",
                    "description":"broken clouds",
                    "icon":"04n"
                    }
                ],
                "pop":0.15
            },
            ...
        ],
        "daily":[
            {
                "dt":1684951200,
                "sunrise":1684926645,
                "sunset":1684977332,
                "moonrise":1684941060,
                "moonset":1684905480,
                "moon_phase":0.16,
                "summary":"Expect a day of partly cloudy with rain",
                "temp":{
                    "day":299.03,
                    "min":290.69,
                    "max":300.35,
                    "night":291.45,
                    "eve":297.51,
                    "morn":292.55
                },
                "feels_like":{
                    "day":299.21,
                    "night":291.37,
                    "eve":297.86,
                    "morn":292.87
                },
                "pressure":1016,
                "humidity":59,
                "dew_point":290.48,
                "wind_speed":3.98,
                "wind_deg":76,
                "wind_gust":8.92,
                "weather":[
                    {
                    "id":500,
                    "main":"Rain",
                    "description":"light rain",
                    "icon":"10d"
                    }
                ],
                "clouds":92,
                "pop":0.47,
                "rain":0.15,
                "uvi":9.23
            },
            ...
        ],
            "alerts": [
            {
            "sender_name": "NWS Philadelphia - Mount Holly (New Jersey, Delaware, Southeastern Pennsylvania)",
            "event": "Small Craft Advisory",
            "start": 1684952747,
            "end": 1684988747,
            "description": "...SMALL CRAFT ADVISORY REMAINS IN EFFECT FROM 5 PM THIS\nAFTERNOON TO 3 AM EST FRIDAY...\n* WHAT...North winds 15 to 20 kt with gusts up to 25 kt and seas\n3 to 5 ft expected.\n* WHERE...Coastal waters from Little Egg Inlet to Great Egg\nInlet NJ out 20 nm, Coastal waters from Great Egg Inlet to\nCape May NJ out 20 nm and Coastal waters from Manasquan Inlet\nto Little Egg Inlet NJ out 20 nm.\n* WHEN...From 5 PM this afternoon to 3 AM EST Friday.\n* IMPACTS...Conditions will be hazardous to small craft.",
            "tags": [

            ]
            },
            ...
        ]
    },
    ...
]
```

## Implementation Notes

### Error Handling
- Invalid coordinates should fail fast with validation errors
- Missing weather data for a location should return empty results

### Timestamp Handling
All weather reports use **simulator time**, not wall-clock time.

### Testing Considerations
- Test coordinate normalization (nearby coordinates should map to same location)
- Test history management (verify old reports are discarded)
- Test unit conversions (standard ↔ metric ↔ imperial)
- Test report filtering (exclude parameter)

