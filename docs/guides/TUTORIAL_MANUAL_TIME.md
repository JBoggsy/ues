# Tutorial: Manual Time Control

This tutorial provides a deep dive into UES's manual time control system. You'll learn how to precisely control simulator time, schedule events at specific moments, and step through a simulation to observe state changes.

**Prerequisites**: Complete the [Quickstart Guide](./QUICKSTART.md) first.

**Time to Complete**: 15-20 minutes

**What You'll Learn**:
- How simulator time differs from wall-clock time
- Scheduling events at specific future times
- Advancing time manually to execute events
- Using pause/resume to inspect simulation state
- Querying event status and environment state

---

## Table of Contents

1. [Understanding Simulator Time](#understanding-simulator-time)
2. [Starting a Manual Simulation](#starting-a-manual-simulation)
3. [Scheduling Events](#scheduling-events)
4. [Advancing Time](#advancing-time)
5. [Pause and Resume](#pause-and-resume)
6. [Querying State](#querying-state)
7. [Complete Workflow Example](#complete-workflow-example)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Understanding Simulator Time

UES maintains its own **simulator time** that is completely decoupled from real wall-clock time. This enables:

- **Instant time jumps**: Skip hours or days in milliseconds
- **Precise control**: Step through events one by one
- **Reproducibility**: Run the same scenario multiple times with identical timing
- **Fast iteration**: Test a full day of events in seconds

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Simulator Time** | The virtual "now" inside the simulation |
| **Wall Time** | Real-world clock time |
| **Time Scale** | Multiplier for auto-advance mode (not used in manual mode) |
| **Events** | Scheduled changes that execute when simulator time reaches their `scheduled_time` |

### Manual vs. Auto-Advance Mode

In **manual mode** (default), time only advances when you explicitly request it via API calls. Events never execute automatically—you have full control.

In **auto-advance mode**, time advances automatically based on wall time and a time scale (e.g., 10x speed). This tutorial focuses on manual mode.

---

## Starting a Manual Simulation

Start a simulation in manual mode (the default):

```bash
curl -X POST http://localhost:8000/simulation/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response:**
```json
{
  "simulation_id": "abc123-...",
  "status": "running",
  "current_time": "2025-11-30T17:00:00.000000+00:00",
  "auto_advance": false,
  "time_scale": null
}
```

Note that `auto_advance` is `false`—this means time will only change when you tell it to.

### Check Current Time State

```bash
curl http://localhost:8000/simulator/time
```

**Response:**
```json
{
  "current_time": "2025-11-30T17:00:00.000000+00:00",
  "time_scale": 1.0,
  "is_paused": false,
  "auto_advance": false,
  "mode": "manual"
}
```

The `mode` field confirms we're in manual mode.

---

## Scheduling Events

Events are scheduled changes to the simulation environment. Each event has:

- **`scheduled_time`**: When the event should execute (in simulator time)
- **`modality`**: Which modality it affects (email, sms, calendar, etc.)
- **`data`**: The payload describing what changes

### Scheduling a Future Event

Let's schedule an email to arrive 60 seconds from now:

```bash
# First, get the current time
CURRENT_TIME=$(curl -s http://localhost:8000/simulator/time | jq -r '.current_time')

# Schedule an email event 60 seconds in the future
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_time": "'$(date -u -d "$CURRENT_TIME + 60 seconds" --iso-8601=seconds)'",
    "modality": "email",
    "data": {
      "operation": "receive",
      "from_address": "calendar@company.com",
      "to_addresses": ["user@example.com"],
      "subject": "Reminder: Team Standup in 30 minutes",
      "body_text": "This is a reminder that your meeting starts at 9:30 AM.\n\nLocation: Conference Room B"
    }
  }'
```

**Response:**
```json
{
  "event_id": "evt-12345...",
  "scheduled_time": "2025-11-30T17:01:00.000000+00:00",
  "modality": "email",
  "status": "pending",
  "priority": 50,
  "created_at": "2025-11-30T17:00:00.000000+00:00",
  "executed_at": null,
  "error_message": null
}
```

The event is now `pending`—it won't execute until simulator time reaches `scheduled_time`.

### Scheduling Multiple Events

Let's add two more emails at different times:

```bash
# Email #2 at T+120 seconds (2 minutes)
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_time": "'$(date -u -d "$CURRENT_TIME + 120 seconds" --iso-8601=seconds)'",
    "modality": "email",
    "data": {
      "operation": "receive",
      "from_address": "alice.johnson@company.com",
      "to_addresses": ["user@example.com"],
      "subject": "Quick question about the project",
      "body_text": "Hey,\n\nDo you have a minute to chat about the API documentation?\n\nThanks,\nAlice"
    }
  }'

# Email #3 at T+180 seconds (3 minutes)
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_time": "'$(date -u -d "$CURRENT_TIME + 180 seconds" --iso-8601=seconds)'",
    "modality": "email",
    "data": {
      "operation": "receive",
      "from_address": "noreply@analytics.company.com",
      "to_addresses": ["user@example.com"],
      "subject": "Daily Analytics Report",
      "body_text": "Your daily analytics report is ready.\n\nPage Views: 12,453\nUnique Visitors: 3,891"
    }
  }'
```

### Verify Pending Events

Check the event queue:

```bash
curl http://localhost:8000/events/summary
```

**Response:**
```json
{
  "total": 3,
  "pending": 3,
  "executed": 0,
  "failed": 0,
  "skipped": 0,
  "by_modality": {
    "email": 3
  },
  "next_event_time": "2025-11-30T17:01:00.000000+00:00"
}
```

All three events are pending, waiting for time to advance.

---

## Advancing Time

Time advancement is the core mechanism for executing events. When you advance time, all events with `scheduled_time <= new_time` are executed.

### Advance by Duration

Advance simulator time by 60 seconds:

```bash
curl -X POST http://localhost:8000/simulator/time/advance \
  -H "Content-Type: application/json" \
  -d '{"seconds": 60}'
```

**Response:**
```json
{
  "previous_time": "2025-11-30T17:00:00.000000+00:00",
  "current_time": "2025-11-30T17:01:00.000000+00:00",
  "time_advanced": "0:01:00",
  "events_executed": 1,
  "events_failed": 0,
  "execution_details": [
    {
      "event_id": "evt-12345...",
      "modality": "email",
      "status": "executed",
      "error": null
    }
  ]
}
```

One event executed (the calendar reminder email).

### Verify Event Execution

Check the email state:

```bash
curl http://localhost:8000/email/state
```

**Response:**
```json
{
  "modality_type": "email",
  "current_time": "2025-11-30T17:01:00.000000+00:00",
  "user_email_address": "user@example.com",
  "emails": {
    "msg-abc123": {
      "message_id": "msg-abc123",
      "from_address": "calendar@company.com",
      "to_addresses": ["user@example.com"],
      "subject": "Reminder: Team Standup in 30 minutes",
      "body_text": "This is a reminder...",
      "is_read": false,
      "sent_at": "2025-11-30T17:01:00.000000+00:00"
    }
  },
  "threads": {},
  "folders": {"inbox": 1},
  "labels": {},
  "total_email_count": 1,
  "unread_count": 1,
  "starred_count": 0
}
```

The email arrived! Notice it's marked as `is_read: false`.

### Duration Formats

The `/simulator/time/advance` endpoint accepts various duration formats:

```bash
# Seconds
{"seconds": 60}

# Minutes
{"minutes": 5}

# Hours
{"hours": 2}

# Combined
{"hours": 1, "minutes": 30, "seconds": 45}
```

### Skip to Next Event

Instead of specifying a duration, you can skip directly to the next pending event:

```bash
curl -X POST http://localhost:8000/simulator/time/skip-to-next
```

**Response:**
```json
{
  "previous_time": "2025-11-30T17:01:00.000000+00:00",
  "current_time": "2025-11-30T17:02:00.000000+00:00",
  "events_executed": 1,
  "next_event_time": "2025-11-30T17:03:00.000000+00:00"
}
```

This is useful for event-driven simulations where you want to jump directly to the next interesting moment.

### Set Absolute Time

You can also jump to a specific time:

```bash
curl -X POST http://localhost:8000/simulator/time/set \
  -H "Content-Type: application/json" \
  -d '{"target_time": "2025-11-30T17:05:00.000000+00:00"}'
```

This executes all events scheduled between the old time and the new time.

---

## Pause and Resume

Pausing the simulation prevents time from advancing in auto-advance mode. In manual mode, pause doesn't block time advancement (since you control time explicitly), but it signals intent to inspect the simulation state.

### Pause

```bash
curl -X POST http://localhost:8000/simulator/time/pause
```

**Response:**
```json
{
  "message": "Time paused",
  "current_time": "2025-11-30T17:02:00.000000+00:00",
  "is_paused": true
}
```

### Check Paused State

```bash
curl http://localhost:8000/simulator/time
```

**Response:**
```json
{
  "current_time": "2025-11-30T17:02:00.000000+00:00",
  "time_scale": 1.0,
  "is_paused": true,
  "auto_advance": false,
  "mode": "paused"
}
```

Note: In manual mode, you can still advance time while paused—this is by design for debugging workflows.

### Resume

```bash
curl -X POST http://localhost:8000/simulator/time/resume
```

**Response:**
```json
{
  "message": "Time resumed",
  "current_time": "2025-11-30T17:02:00.000000+00:00",
  "is_paused": false
}
```

---

## Querying State

### Check Event Summary

```bash
curl http://localhost:8000/events/summary
```

**Response:**
```json
{
  "total": 3,
  "pending": 1,
  "executed": 2,
  "failed": 0,
  "skipped": 0,
  "by_modality": {
    "email": 3
  },
  "next_event_time": "2025-11-30T17:03:00.000000+00:00"
}
```

### Get Specific Event Details

```bash
curl http://localhost:8000/events/{event_id}
```

**Response:**
```json
{
  "event_id": "evt-12345...",
  "scheduled_time": "2025-11-30T17:01:00.000000+00:00",
  "modality": "email",
  "status": "executed",
  "priority": 50,
  "created_at": "2025-11-30T17:00:00.000000+00:00",
  "executed_at": "2025-11-30T17:01:00.000000+00:00",
  "error_message": null,
  "data": {
    "modality_type": "email",
    "operation": "receive",
    "from_address": "calendar@company.com",
    "to_addresses": ["user@example.com"],
    "subject": "Reminder: Team Standup in 30 minutes",
    "body_text": "This is a reminder..."
  }
}
```

### Get All Environment State

```bash
curl http://localhost:8000/environment/state
```

**Response:**
```json
{
  "current_time": "2025-11-30T17:02:00.000000+00:00",
  "modalities": {
    "email": {
      "modality_type": "email",
      "user_email_address": "user@example.com",
      "emails": {...},
      "threads": {...}
    },
    "sms": {
      "modality_type": "sms",
      "threads": {...}
    }
  },
  "summary": [
    {"modality_type": "email", "state_summary": "email state with 12 fields"},
    {"modality_type": "sms", "state_summary": "sms state with 5 fields"}
  ]
}
```

### Query Specific Modality State

```bash
# Email state
curl http://localhost:8000/email/state

# SMS state
curl http://localhost:8000/sms/state

# Calendar state
curl http://localhost:8000/calendar/state
```

---

## Complete Workflow Example

Here's a complete script that demonstrates the full manual time control workflow:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Step 1: Start Simulation ==="
curl -s -X POST "$BASE_URL/simulation/start" \
  -H "Content-Type: application/json" \
  -d '{}' | jq

# Get current time for scheduling
CURRENT_TIME=$(curl -s "$BASE_URL/simulator/time" | jq -r '.current_time')
echo "Current simulator time: $CURRENT_TIME"

echo ""
echo "=== Step 2: Schedule Three Emails ==="

# Email 1: Calendar reminder at T+60s
curl -s -X POST "$BASE_URL/events" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_time": "'$(date -u -d "$CURRENT_TIME + 60 seconds" --iso-8601=seconds)'",
    "modality": "email",
    "data": {
      "operation": "receive",
      "from_address": "calendar@company.com",
      "to_addresses": ["user@example.com"],
      "subject": "Reminder: Team Standup in 30 minutes",
      "body_text": "Your meeting starts at 9:30 AM in Conference Room B."
    }
  }' | jq '.event_id'

# Email 2: Coworker message at T+120s
curl -s -X POST "$BASE_URL/events" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_time": "'$(date -u -d "$CURRENT_TIME + 120 seconds" --iso-8601=seconds)'",
    "modality": "email",
    "data": {
      "operation": "receive",
      "from_address": "alice.johnson@company.com",
      "to_addresses": ["user@example.com"],
      "subject": "Quick question about the project",
      "body_text": "Do you have a minute to chat about the API docs?"
    }
  }' | jq '.event_id'

# Email 3: Automated report at T+180s
curl -s -X POST "$BASE_URL/events" \
  -H "Content-Type: application/json" \
  -d '{
    "scheduled_time": "'$(date -u -d "$CURRENT_TIME + 180 seconds" --iso-8601=seconds)'",
    "modality": "email",
    "data": {
      "operation": "receive",
      "from_address": "noreply@analytics.company.com",
      "to_addresses": ["user@example.com"],
      "subject": "Daily Analytics Report",
      "body_text": "Page Views: 12,453\nUnique Visitors: 3,891"
    }
  }' | jq '.event_id'

echo ""
echo "=== Step 3: Verify 3 Pending Events ==="
curl -s "$BASE_URL/events/summary" | jq '{pending, executed, total}'

echo ""
echo "=== Step 4: Advance 60s (Execute Email #1) ==="
curl -s -X POST "$BASE_URL/simulator/time/advance" \
  -H "Content-Type: application/json" \
  -d '{"seconds": 60}' | jq '{current_time, events_executed}'

echo ""
echo "=== Step 5: Check Email State ==="
curl -s "$BASE_URL/email/state" | jq '{total_email_count, unread_count}'

echo ""
echo "=== Step 6: Pause Simulation ==="
curl -s -X POST "$BASE_URL/simulator/time/pause" | jq '{is_paused}'

echo ""
echo "=== Step 7: Resume Simulation ==="
curl -s -X POST "$BASE_URL/simulator/time/resume" | jq '{is_paused}'

echo ""
echo "=== Step 8: Advance 120s (Execute Emails #2 and #3) ==="
curl -s -X POST "$BASE_URL/simulator/time/advance" \
  -H "Content-Type: application/json" \
  -d '{"seconds": 120}' | jq '{current_time, events_executed}'

echo ""
echo "=== Step 9: Verify All 3 Emails Received ==="
curl -s "$BASE_URL/email/state" | jq '.emails | keys | length'

echo ""
echo "=== Step 10: Check Final Event Summary ==="
curl -s "$BASE_URL/events/summary" | jq '{pending, executed, failed}'

echo ""
echo "=== Step 11: Stop Simulation ==="
curl -s -X POST "$BASE_URL/simulation/stop" | jq
```

### Python Version

```python
import requests
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:8000"

def main():
    # Step 1: Start simulation
    print("=== Step 1: Start Simulation ===")
    response = requests.post(f"{BASE_URL}/simulation/start", json={})
    print(f"Status: {response.json()['status']}")
    
    # Get current time
    time_state = requests.get(f"{BASE_URL}/simulator/time").json()
    current_time = datetime.fromisoformat(time_state["current_time"])
    print(f"Current time: {current_time}")
    
    # Step 2: Schedule three emails
    print("\n=== Step 2: Schedule Three Emails ===")
    
    emails = [
        {
            "offset": 60,
            "from": "calendar@company.com",
            "subject": "Reminder: Team Standup in 30 minutes",
            "body": "Your meeting starts at 9:30 AM."
        },
        {
            "offset": 120,
            "from": "alice.johnson@company.com", 
            "subject": "Quick question about the project",
            "body": "Do you have a minute to chat?"
        },
        {
            "offset": 180,
            "from": "noreply@analytics.company.com",
            "subject": "Daily Analytics Report",
            "body": "Page Views: 12,453"
        }
    ]
    
    for email in emails:
        scheduled_time = current_time + timedelta(seconds=email["offset"])
        response = requests.post(f"{BASE_URL}/events", json={
            "scheduled_time": scheduled_time.isoformat(),
            "modality": "email",
            "data": {
                "operation": "receive",
                "from_address": email["from"],
                "to_addresses": ["user@example.com"],
                "subject": email["subject"],
                "body_text": email["body"]
            }
        })
        print(f"Scheduled: {email['subject'][:30]}... at T+{email['offset']}s")
    
    # Step 3: Verify pending events
    print("\n=== Step 3: Verify Pending Events ===")
    summary = requests.get(f"{BASE_URL}/events/summary").json()
    print(f"Pending: {summary['pending']}, Executed: {summary['executed']}")
    
    # Step 4: Advance 60 seconds
    print("\n=== Step 4: Advance 60s ===")
    response = requests.post(
        f"{BASE_URL}/simulator/time/advance",
        json={"seconds": 60}
    ).json()
    print(f"Events executed: {response['events_executed']}")
    
    # Step 5: Check email state
    print("\n=== Step 5: Check Email State ===")
    email_state = requests.get(f"{BASE_URL}/email/state").json()
    print(f"Total emails: {email_state['total_email_count']}")
    
    # Step 6: Pause
    print("\n=== Step 6: Pause ===")
    pause_response = requests.post(f"{BASE_URL}/simulator/time/pause").json()
    print(f"Is paused: {pause_response['is_paused']}")
    
    # Step 7: Resume
    print("\n=== Step 7: Resume ===")
    resume_response = requests.post(f"{BASE_URL}/simulator/time/resume").json()
    print(f"Is paused: {resume_response['is_paused']}")
    
    # Step 8: Advance remaining time
    print("\n=== Step 8: Advance 120s ===")
    response = requests.post(
        f"{BASE_URL}/simulator/time/advance",
        json={"seconds": 120}
    ).json()
    print(f"Events executed: {response['events_executed']}")
    
    # Step 9: Verify all emails
    print("\n=== Step 9: Final Email Count ===")
    email_state = requests.get(f"{BASE_URL}/email/state").json()
    print(f"Total emails: {email_state['total_email_count']}")
    
    # Verify senders
    senders = [e["from_address"] for e in email_state["emails"].values()]
    print(f"From: {senders}")
    
    # Step 10: Final summary
    print("\n=== Step 10: Final Event Summary ===")
    summary = requests.get(f"{BASE_URL}/events/summary").json()
    print(f"Pending: {summary['pending']}, Executed: {summary['executed']}, Failed: {summary['failed']}")
    
    # Step 11: Stop
    print("\n=== Step 11: Stop Simulation ===")
    stop_response = requests.post(f"{BASE_URL}/simulation/stop").json()
    print(f"Status: {stop_response['status']}")
    print(f"Events executed: {stop_response['events_executed']}")

if __name__ == "__main__":
    main()
```

---

## Best Practices

### 1. Always Check Event Status

After advancing time, verify events executed successfully:

```bash
curl http://localhost:8000/events/summary
```

Check for `failed > 0` to catch execution errors.

### 2. Use Immediate Events for Testing

For quick tests, use `/events/immediate` which schedules an event at the current time:

```bash
curl -X POST http://localhost:8000/events/immediate \
  -H "Content-Type: application/json" \
  -d '{
    "modality": "email",
    "data": {
      "operation": "receive",
      "from_address": "test@example.com",
      "to_addresses": ["user@example.com"],
      "subject": "Test",
      "body_text": "Test email"
    }
  }'

# Still need minimal time advance to execute
curl -X POST http://localhost:8000/simulator/time/advance \
  -H "Content-Type: application/json" \
  -d '{"seconds": 0.001}'
```

### 3. Use Skip-to-Next for Event-Driven Workflows

When you only care about events (not specific timing):

```bash
# Execute events one by one
while curl -s http://localhost:8000/events/summary | jq -e '.pending > 0' > /dev/null; do
  curl -X POST http://localhost:8000/simulator/time/skip-to-next
  # Inspect state here
done
```

### 4. Reset Between Test Runs

**Note**: The `/simulation/reset` endpoint is not yet fully implemented (returns 501). For now, stop and restart the simulation to reset:

```bash
# Stop the current simulation
curl -X POST http://localhost:8000/simulation/stop

# Start a fresh simulation
curl -X POST http://localhost:8000/simulation/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

When reset functionality is implemented, it will restore the simulation to its initial state (initial time, events as pending, initial modality states).

### 5. Validate Environment State

Use the validation endpoint to check for inconsistencies:

```bash
curl -X POST http://localhost:8000/environment/validate
```

---

## Troubleshooting

### Events Not Executing

**Symptom**: Events stay in `pending` status.

**Cause**: Time hasn't advanced past the event's `scheduled_time`.

**Solution**: Check the event's scheduled time and advance accordingly:

```bash
# Check next event time
curl http://localhost:8000/events/summary | jq '.next_event_time'

# Advance to that time
curl -X POST http://localhost:8000/simulator/time/skip-to-next
```

### "Simulation Not Running" Errors

**Symptom**: API calls return 409 Conflict.

**Cause**: Simulation hasn't been started.

**Solution**: Start the simulation first:

```bash
curl -X POST http://localhost:8000/simulation/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

### State Not Updating After Events

**Symptom**: State queries return empty/old data after events should have executed.

**Cause**: Events may have failed silently.

**Solution**: Check event details for error messages:

```bash
# Get event details
curl http://localhost:8000/events/{event_id}

# Check for failed events
curl http://localhost:8000/events/summary | jq '.failed'
```

### Time Calculation Issues

**Symptom**: Events not scheduled at expected times.

**Cause**: Timezone confusion between UTC and local time.

**Solution**: Always use UTC for API calls. UES uses UTC internally.

```python
from datetime import datetime, timezone

# Correct: UTC timezone
scheduled_time = datetime.now(timezone.utc) + timedelta(hours=1)

# Incorrect: naive datetime
scheduled_time = datetime.now() + timedelta(hours=1)  # Don't do this!
```

---

## Next Steps

- **[Building an Agent Loop](./TUTORIAL_AGENT_LOOP.md)** - Create an AI agent that responds to simulation events
- **[API Examples](./EXAMPLES.md)** - Copy-paste examples for common operations
- **[REST API Reference](../REST_API.md)** - Complete endpoint documentation
- **[Modality Routes](../MODALITY_ROUTES.md)** - Detailed modality endpoint specifications

---

## Summary

You've learned how to:

✅ Start a simulation in manual mode
✅ Schedule events at specific future times
✅ Advance time manually to execute events
✅ Use pause/resume for inspection
✅ Query event status and environment state
✅ Use skip-to-next for event-driven workflows

Manual time control gives you precise control over your simulations, making it ideal for testing AI assistants, debugging edge cases, and creating reproducible scenarios.
