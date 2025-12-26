# Example Scenarios

This directory contains example scenario files demonstrating the UES scenario format.

## Files

### `minimal.ues-scenario.json`

A minimal scenario with only location and time modalities. Use this as a starting point for understanding the basic structure.

**Contains:**
- Location state (Home in San Francisco)
- Time preferences (Pacific timezone, 12h format)
- One scheduled location update event

**Best for:**
- Learning the scenario format
- Starting point for custom scenarios
- Testing basic save/load functionality

### `workday.ues-scenario.json`

A comprehensive workday scenario simulating a typical morning for an AI assistant user.

**Contains:**
- All 7 registered modalities (location, time, weather, chat, email, calendar, sms)
- Calendar with daily standup and project review meetings
- Email inbox with unread messages
- Weather data for San Francisco
- 6 scheduled events throughout the day:
  - Weather update (8:00 AM)
  - Work email from manager (8:30 AM)
  - Commute to office (9:00 AM)
  - SMS lunch invitation (12:30 PM)
  - Location updates for lunch and return

**Best for:**
- Testing multi-modality scenarios
- AI assistant integration testing
- Understanding all modality formats

## Loading Examples

### Via Python Client

```python
from client import UESClient

client = UESClient("http://localhost:8000")

# Load minimal scenario
with open("examples/scenarios/minimal.ues-scenario.json") as f:
    client.scenario.import_scenario(f.read())

# Load workday scenario
with open("examples/scenarios/workday.ues-scenario.json") as f:
    client.scenario.import_scenario(f.read())
```

### Via cURL

```bash
# Load minimal scenario
curl -X POST http://localhost:8000/api/scenario/import \
  -H "Content-Type: application/json" \
  -d @examples/scenarios/minimal.ues-scenario.json

# Load workday scenario
curl -X POST http://localhost:8000/api/scenario/import \
  -H "Content-Type: application/json" \
  -d @examples/scenarios/workday.ues-scenario.json
```

## Creating Your Own Scenarios

1. Set up the simulation state you want to save
2. Export using the API or Web UI
3. Optionally edit the JSON to customize
4. Test by loading in a fresh simulation

See [docs/guides/SCENARIO_SAVE_LOAD.md](../../docs/guides/SCENARIO_SAVE_LOAD.md) for the complete user guide and [docs/guides/SCENARIO_FORMAT.md](../../docs/guides/SCENARIO_FORMAT.md) for the format specification.
