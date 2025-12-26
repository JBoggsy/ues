# Scenario Save/Load User Guide

This guide explains how to save and load simulation scenarios in UES. Scenarios allow you to capture complete simulation states, share them with others, and restore them later for testing or development.

## Overview

UES provides three ways to save simulation state:

1. **Complete Scenario** - Environment state + event queue (`.ues-scenario.json`)
2. **Environment Only** - Just the current modality states (`.ues-env.json`)
3. **Events Only** - Just the event queue (`.ues-events.json`)

## Quick Start

### Saving a Scenario via Web UI

1. Set up your simulation with the desired state and events
2. Click the **Export** button in the toolbar
3. Choose what to export:
   - **Complete Scenario** - Everything
   - **Environment Only** - Current state without events
   - **Events Only** - Events without current state
4. Optionally add author name and description
5. Click **Export** to download the JSON file

### Loading a Scenario via Web UI

1. Click the **Import** button in the toolbar
2. Select a `.ues-scenario.json`, `.ues-env.json`, or `.ues-events.json` file
3. For event imports, choose:
   - **Replace** - Clear existing events and load new ones
   - **Merge** - Add new events to existing queue
4. Review any compatibility warnings
5. Click **Import** to load

### Saving via REST API

```bash
# Export complete scenario
curl -X POST http://localhost:8000/api/scenario/export \
  -H "Content-Type: application/json" \
  -d '{"author": "Developer", "description": "Test scenario"}' \
  -o my-scenario.ues-scenario.json

# Export environment only
curl -X POST http://localhost:8000/api/scenario/export/environment \
  -H "Content-Type: application/json" \
  -d '{"author": "Developer"}' \
  -o my-env.ues-env.json

# Export events only
curl -X POST http://localhost:8000/api/scenario/export/events \
  -o my-events.ues-events.json
```

### Loading via REST API

```bash
# Load complete scenario (stops simulation first)
curl -X POST http://localhost:8000/api/scenario/import \
  -H "Content-Type: application/json" \
  -d @my-scenario.ues-scenario.json

# Load environment only
curl -X POST http://localhost:8000/api/scenario/import/environment \
  -H "Content-Type: application/json" \
  -d @my-env.ues-env.json

# Load events (replace mode)
curl -X POST http://localhost:8000/api/scenario/import/events \
  -H "Content-Type: application/json" \
  -d @my-events.ues-events.json

# Load events (merge mode)
curl -X POST "http://localhost:8000/api/scenario/import/events?mode=merge" \
  -H "Content-Type: application/json" \
  -d @my-events.ues-events.json
```

### Using the Python Client

```python
from client import UESClient

client = UESClient("http://localhost:8000")

# Export complete scenario
scenario = client.scenario.export_scenario(
    author="Developer",
    description="Test scenario"
)
with open("my-scenario.ues-scenario.json", "w") as f:
    f.write(scenario)

# Export environment only
env_data = client.scenario.export_environment()

# Export events only
events_data = client.scenario.export_events()

# Load complete scenario
with open("my-scenario.ues-scenario.json") as f:
    result = client.scenario.import_scenario(f.read())

# Load events in merge mode
with open("my-events.ues-events.json") as f:
    result = client.scenario.import_events(f.read(), mode="merge")
```

---

## Use Cases

### 1. Regression Testing

Save a scenario after setting up a specific test case, then reload it before each test run to ensure consistent starting conditions:

```python
# Setup test scenario once
client.time.set_time("2024-03-15T09:00:00Z")
client.email.receive(
    from_address="boss@company.com",
    to_addresses=["user@company.com"],
    subject="Important Meeting",
    body_text="Please attend the meeting at 2pm"
)
client.calendar.create_event(
    title="Important Meeting",
    start="2024-03-15T14:00:00Z",
    end="2024-03-15T15:00:00Z"
)

# Save as baseline
scenario = client.scenario.export_scenario(
    author="Test Suite",
    description="Baseline for meeting reminder tests"
)
with open("tests/scenarios/meeting_baseline.ues-scenario.json", "w") as f:
    f.write(scenario)

# In each test
def test_meeting_reminder():
    with open("tests/scenarios/meeting_baseline.ues-scenario.json") as f:
        client.scenario.import_scenario(f.read())
    
    # Run test against known state
    ...
```

### 2. Sharing Test Cases

Export scenarios to share with team members or include in bug reports:

```python
# After reproducing a bug
scenario = client.scenario.export_scenario(
    author="QA Team",
    description="Reproduces calendar sync bug #1234"
)
with open("bug_1234_repro.ues-scenario.json", "w") as f:
    f.write(scenario)
```

### 3. Demo Scenarios

Create pre-configured scenarios for demonstrations:

```python
# Setup demo environment
client.location.update(latitude=37.7749, longitude=-122.4194, named_location="Office")
client.weather.update(latitude=37.7749, longitude=-122.4194, report=sunny_report)
# ... add more demo data

scenario = client.scenario.export_scenario(
    author="Demo Team",
    description="Standard demo scenario with San Francisco location"
)
```

### 4. Event Templates

Save just the events to create reusable event sequences:

```python
# Create a "morning routine" event sequence
events = [
    {"modality": "location", "data": home_location, "scheduled_time": "07:00:00"},
    {"modality": "weather", "data": weather_report, "scheduled_time": "07:01:00"},
    {"modality": "calendar", "data": morning_meeting, "scheduled_time": "07:30:00"},
    {"modality": "email", "data": daily_digest, "scheduled_time": "08:00:00"},
]

for event in events:
    client.events.schedule(...)

# Export just events
events_json = client.scenario.export_events()
with open("templates/morning_routine.ues-events.json", "w") as f:
    f.write(events_json)

# Later, merge into any scenario
with open("templates/morning_routine.ues-events.json") as f:
    client.scenario.import_events(f.read(), mode="merge")
```

---

## Important Considerations

### Simulation Must Be Stopped

Loading a scenario requires the simulation to be stopped (paused). If the simulation is running, the import request will return an error:

```json
{
  "detail": "Cannot load scenario while simulation is running. Stop the simulation first."
}
```

### Undo Stack Behavior

| Operation | Undo Stack |
|-----------|------------|
| Load complete scenario | Cleared |
| Load environment | Cleared |
| Load events (replace) | Cleared |
| Load events (merge) | Preserved |

### Event ID Regeneration

By default, when loading events, new `event_id` values are generated to prevent conflicts with existing events. This means:

- Loaded events get fresh UUIDs
- References to old event IDs won't work
- Event ordering is preserved based on `scheduled_time` and `priority`

To preserve original event IDs (advanced use case):

```bash
curl -X POST "http://localhost:8000/api/scenario/import/events?regenerate_ids=false" \
  -H "Content-Type: application/json" \
  -d @events.json
```

### Historic Events Warning

If a loaded scenario contains events scheduled before the current environment time, you'll receive a warning:

```json
{
  "success": true,
  "warnings": [
    "3 events are scheduled before current simulator time and will be skipped"
  ]
}
```

These events are loaded but will be skipped during execution since their time has already passed.

### Modality Compatibility

Scenarios can only be loaded if all modalities in the file are registered in the current UES instance.

**Registered Modalities** (built-in):
- `location`
- `time`
- `weather`
- `chat`
- `email`
- `calendar`
- `sms`

If a scenario contains an unknown modality:

```json
{
  "detail": "Unknown modality type: 'discord'. Use strict=false to skip unknown modalities."
}
```

To load with unknown modalities skipped:

```bash
curl -X POST "http://localhost:8000/api/scenario/import?strict=false" \
  -H "Content-Type: application/json" \
  -d @scenario.json
```

---

## File Format Reference

See [SCENARIO_FORMAT.md](SCENARIO_FORMAT.md) for the complete file format specification including all modality-specific field definitions.

### Quick Reference

**Complete Scenario Structure:**
```json
{
  "metadata": {
    "ues_version": "0.1.0",
    "scenario_version": "1",
    "created_at": "2024-03-15T14:30:00+00:00",
    "author": "Optional Author",
    "description": "Optional description"
  },
  "environment": {
    "time_state": { ... },
    "modality_states": {
      "location": { ... },
      "email": { ... }
    }
  },
  "events": {
    "events": [ ... ]
  }
}
```

**Event Structure:**
```json
{
  "event_id": "uuid",
  "scheduled_time": "2024-03-15T15:00:00+00:00",
  "modality": "email",
  "data": {
    "modality_type": "email",
    "timestamp": "...",
    "operation": "receive",
    ...
  },
  "status": "pending",
  "created_at": "...",
  "priority": 0
}
```

---

## Troubleshooting

### "Cannot load scenario while simulation is running"

**Solution**: Stop or pause the simulation before importing:
```bash
curl -X POST http://localhost:8000/api/simulation/pause
```

### "Unknown modality type"

**Cause**: The scenario contains modalities not registered in your UES instance.

**Solutions**:
1. Use `strict=false` to skip unknown modalities
2. Register the missing modality before loading
3. Edit the scenario file to remove the unknown modality

### "Events scheduled before current time"

**Cause**: The scenario's event times are earlier than the environment's current time.

**Solutions**:
1. Accept the warning - events will be skipped
2. Load environment first, then load events separately after adjusting times
3. Edit the scenario to update event times

### "Validation error in modality state"

**Cause**: The scenario data doesn't match the expected schema (possibly from a different UES version).

**Solutions**:
1. Check `metadata.ues_version` against your current version
2. Review the specific validation error message
3. Manually edit the scenario file to fix invalid data

### Large Scenario Files

For scenarios with many events (10,000+), loading may take several seconds. Consider:
- Splitting into smaller scenario files
- Using events-only files for event templates
- Archiving old executed events before export

---

## Best Practices

1. **Always include metadata**: Author and description help identify scenarios later
2. **Use descriptive filenames**: `regression_test_email_threading_v2.ues-scenario.json`
3. **Version control scenarios**: Track scenario files in git for test reproducibility
4. **Validate before sharing**: Load scenarios in a fresh environment to verify they work
5. **Document time expectations**: Note what simulator time the scenario expects
6. **Keep scenarios focused**: One scenario per test case or use case
7. **Archive regularly**: Export scenarios before major changes as backup
