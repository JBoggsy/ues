# Scenario 2: Multi-Modality Morning Simulation

## Executive Summary

This scenario simulates a realistic 2-hour morning (8:00 AM - 10:00 AM) where multiple modalities interact. It tests the system's ability to:

- Handle events across 6 different modalities simultaneously
- Maintain consistent state as events execute across modalities
- Use skip-to-next navigation for efficient event-driven progression
- Accumulate state correctly over multiple event executions
- Reset the simulation and verify clean state restoration

**Complexity**: Medium  
**Modalities Used**: SMS, Calendar, Email, Location, Weather, Chat  
**Total Events**: 8 scheduled events  
**Simulated Duration**: 2 hours (8:00 AM - 10:00 AM)  

---

## Scenario Context

**User Profile**:
- Name: Alex Developer
- Home Location: 40.7128° N, 74.0060° W (New York City)
- Work Location: 40.7580° N, 73.9855° W (Midtown Manhattan)
- Phone: +1-555-0100
- Email: alex@example.com

**Starting State**:
- Time: 8:00 AM, November 28, 2025
- Location: Home (NYC residential)
- Weather: Clear, 45°F
- Calendar: Empty (events will be added)
- Email Inbox: Empty
- SMS: Empty
- Chat: Empty

---

## Detailed Timeline

| Sim Time | Event # | Modality | Description |
|----------|---------|----------|-------------|
| 8:00 AM | - | Setup | Simulation starts, initial state set |
| 8:05 AM | 1 | SMS | Spouse sends grocery request |
| 8:15 AM | 2 | Calendar | Team standup reminder notification |
| 8:20 AM | 3 | Email | Work email with meeting agenda |
| 8:30 AM | 4 | Location | User leaves home, starts commute |
| 8:35 AM | 5 | Location | User arrives at subway station |
| 8:45 AM | 6 | Weather | Weather update - rain starting |
| 8:55 AM | 7 | Location | User arrives at work |
| 9:00 AM | 8 | Chat | Assistant reminder about standup |

---

## Event Contents

### Event 1: SMS from Spouse

**Time**: 8:05 AM  
**Modality**: SMS

```json
{
  "modality": "sms",
  "scheduled_time": "2025-11-28T08:05:00",
  "priority": 50,
  "data": {
    "action": "receive",
    "message_data": {
      "from_number": "+1-555-0199",
      "to_numbers": ["+1-555-0100"],
      "body": "Hey! Running late this morning. Can you pick up groceries on your way home? We need milk, bread, and eggs. Thanks! ❤️",
      "message_type": "sms"
    }
  },
  "metadata": {
    "sender_name": "Jordan (Spouse)",
    "relationship": "spouse"
  }
}
```

**Expected State After**:
- SMS inbox: 1 message
- Unread count: 1
- Conversation with +1-555-0199 created

---

### Event 2: Calendar Reminder

**Time**: 8:15 AM  
**Modality**: Calendar

```json
{
  "modality": "calendar",
  "scheduled_time": "2025-11-28T08:15:00",
  "priority": 60,
  "data": {
    "action": "create",
    "event_data": {
      "title": "Team Standup",
      "description": "Daily engineering team standup meeting.\n\nAgenda:\n- Yesterday's progress\n- Today's plans\n- Blockers\n\nVideo call link: https://meet.company.com/standup",
      "start_time": "2025-11-28T09:00:00",
      "end_time": "2025-11-28T09:30:00",
      "location": "Conference Room B / Virtual",
      "attendees": [
        "alex@example.com",
        "alice@company.com",
        "bob@company.com",
        "carol@company.com"
      ],
      "reminders": [
        {"minutes_before": 15, "method": "notification"},
        {"minutes_before": 5, "method": "notification"}
      ],
      "calendar_id": "work"
    }
  },
  "metadata": {
    "event_type": "recurring_meeting",
    "recurrence": "daily_weekdays"
  }
}
```

**Expected State After**:
- Calendar has 1 event
- Event scheduled for 9:00 AM - 9:30 AM
- Event has 4 attendees

---

### Event 3: Work Email with Meeting Agenda

**Time**: 8:20 AM  
**Modality**: Email

```json
{
  "modality": "email",
  "scheduled_time": "2025-11-28T08:20:00",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "alice@company.com",
    "to_addresses": ["alex@example.com"],
    "cc_addresses": ["bob@company.com", "carol@company.com"],
    "subject": "Standup Agenda - Nov 28",
    "body_text": "Hi team,\n\nHere's the agenda for today's standup:\n\n1. Sprint Progress Review\n   - We're at 75% completion for Sprint 23\n   - 3 stories remaining\n\n2. API Documentation Status\n   - Alex: Can you give an update on the REST API docs?\n\n3. Blockers\n   - CI/CD pipeline issues from yesterday\n   - Waiting on design review for the new dashboard\n\n4. Upcoming\n   - Sprint review Friday at 2 PM\n   - Holiday schedule reminder\n\nSee you at 9!\n\nAlice",
    "body_html": null,
    "headers": {
      "X-Priority": "normal",
      "Thread-Index": "thread-standup-001"
    }
  },
  "metadata": {
    "thread_id": "thread-standup-001",
    "category": "work"
  }
}
```

**Expected State After**:
- Email inbox: 1 message
- Unread: 1
- From: alice@company.com

---

### Event 4: Location Update - Leaving Home

**Time**: 8:30 AM  
**Modality**: Location

```json
{
  "modality": "location",
  "scheduled_time": "2025-11-28T08:30:00",
  "priority": 40,
  "data": {
    "latitude": 40.7135,
    "longitude": -74.0046,
    "altitude": 10.0,
    "accuracy": 15.0,
    "speed": 1.2,
    "heading": 45.0,
    "location_name": "Outside Home",
    "address": "123 Main St, New York, NY 10001"
  },
  "metadata": {
    "activity": "walking",
    "destination": "work",
    "transport_mode": "transit"
  }
}
```

**Expected State After**:
- Current location updated
- Location history: 1 entry (excluding initial)
- Activity: walking

---

### Event 5: Location Update - Subway Station

**Time**: 8:35 AM  
**Modality**: Location

```json
{
  "modality": "location",
  "scheduled_time": "2025-11-28T08:35:00",
  "priority": 40,
  "data": {
    "latitude": 40.7200,
    "longitude": -74.0010,
    "altitude": -5.0,
    "accuracy": 50.0,
    "speed": 0.0,
    "heading": null,
    "location_name": "Canal Street Station",
    "address": "Canal St & Lafayette St, New York, NY 10013"
  },
  "metadata": {
    "activity": "stationary",
    "venue_type": "transit_station",
    "transport_mode": "subway"
  }
}
```

**Expected State After**:
- Current location: Canal Street Station
- Location history: 2 entries
- Underground (negative altitude)

---

### Event 6: Weather Update - Rain Starting

**Time**: 8:45 AM  
**Modality**: Weather

```json
{
  "modality": "weather",
  "scheduled_time": "2025-11-28T08:45:00",
  "priority": 30,
  "data": {
    "latitude": 40.7580,
    "longitude": -73.9855,
    "report": {
      "temperature": 43.0,
      "feels_like": 38.0,
      "humidity": 85,
      "pressure": 1008,
      "wind_speed": 12.0,
      "wind_direction": 225,
      "conditions": "Light Rain",
      "description": "Light rain expected to continue through the morning. Temperature dropping slightly.",
      "visibility": 5000,
      "cloud_cover": 90,
      "precipitation_probability": 80,
      "uv_index": 1,
      "sunrise": "2025-11-28T06:52:00",
      "sunset": "2025-11-28T16:32:00"
    }
  },
  "metadata": {
    "source": "weather_service",
    "forecast_type": "current",
    "alert_level": "advisory"
  }
}
```

**Expected State After**:
- Weather at work location updated
- Conditions: Light Rain
- Temperature: 43°F
- High precipitation probability

---

### Event 7: Location Update - Arrived at Work

**Time**: 8:55 AM  
**Modality**: Location

```json
{
  "modality": "location",
  "scheduled_time": "2025-11-28T08:55:00",
  "priority": 40,
  "data": {
    "latitude": 40.7580,
    "longitude": -73.9855,
    "altitude": 15.0,
    "accuracy": 10.0,
    "speed": 0.0,
    "heading": null,
    "location_name": "TechCorp Office",
    "address": "350 5th Avenue, New York, NY 10118"
  },
  "metadata": {
    "activity": "stationary",
    "venue_type": "workplace",
    "arrival_event": true
  }
}
```

**Expected State After**:
- Current location: TechCorp Office
- Location history: 3 entries
- At workplace

---

### Event 8: Chat Assistant Reminder

**Time**: 9:00 AM  
**Modality**: Chat

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T09:00:00",
  "priority": 70,
  "data": {
    "role": "assistant",
    "content": "Good morning! 🌧️ Just a heads up:\n\n📅 Your Team Standup is starting now in Conference Room B.\n\n☔ It's raining outside (43°F), so don't forget your umbrella if you need to step out later.\n\n📱 You have an unread text from Jordan about picking up groceries on your way home.",
    "conversation_id": "default"
  },
  "metadata": {
    "message_type": "proactive_reminder",
    "context_sources": ["calendar", "weather", "sms"]
  }
}
```

**Expected State After**:
- Chat has 1 message
- Message is from assistant
- Contains contextual information from other modalities

---

## Skip-to-Next Execution Sequence

The test will use `skip-to-next` to efficiently progress through events:

| Skip # | From Time | To Time | Event Executed | Cumulative State |
|--------|-----------|---------|----------------|------------------|
| 1 | 8:00 AM | 8:05 AM | SMS from spouse | 1 SMS |
| 2 | 8:05 AM | 8:15 AM | Calendar event | 1 SMS, 1 Calendar |
| 3 | 8:15 AM | 8:20 AM | Work email | 1 SMS, 1 Cal, 1 Email |
| 4 | 8:20 AM | 8:30 AM | Location (leaving) | + 1 Location |
| 5 | 8:30 AM | 8:35 AM | Location (subway) | + 2 Locations |
| 6 | 8:35 AM | 8:45 AM | Weather update | + Weather |
| 7 | 8:45 AM | 8:55 AM | Location (work) | + 3 Locations |
| 8 | 8:55 AM | 9:00 AM | Chat reminder | + 1 Chat |

---

## Verification Checkpoints

### After All Events Scheduled (8:00 AM)
```json
{
  "event_summary": {
    "total_events": 8,
    "pending_events": 8,
    "executed_events": 0,
    "by_modality": {
      "sms": 1,
      "calendar": 1,
      "email": 1,
      "location": 3,
      "weather": 1,
      "chat": 1
    }
  }
}
```

### Mid-Point Check (After Skip 4, 8:30 AM)
```json
{
  "environment_summary": {
    "sms": {"message_count": 1, "unread": 1},
    "calendar": {"event_count": 1},
    "email": {"inbox_count": 1, "unread": 1},
    "location": {"current": "Outside Home"}
  },
  "event_summary": {
    "pending_events": 4,
    "executed_events": 4
  }
}
```

### Final State (9:00 AM)
```json
{
  "environment_state": {
    "current_time": "2025-11-28T09:00:00",
    "sms": {
      "conversations": 1,
      "total_messages": 1,
      "unread_messages": 1
    },
    "calendar": {
      "events": 1,
      "upcoming_in_hour": 0
    },
    "email": {
      "inbox_count": 1,
      "unread_count": 1
    },
    "location": {
      "current_name": "TechCorp Office",
      "history_count": 3
    },
    "weather": {
      "conditions": "Light Rain",
      "temperature": 43.0
    },
    "chat": {
      "messages": 1,
      "from_assistant": 1
    }
  }
}
```

### After Reset
```json
{
  "reset_response": {
    "cleared_events": 8,
    "message": "Simulation reset successfully"
  },
  "post_reset_state": {
    "is_running": false,
    "pending_events": 0,
    "executed_events": 0
  }
}
```

---

## API Calls Sequence

### Setup Phase
1. `POST /simulation/start` with `{"auto_advance": false}`
2. `POST /events` × 8 (all events scheduled)
3. `GET /events/summary` (verify 8 pending)

### Execution Phase (using skip-to-next)
4. `POST /simulator/time/skip-to-next` → 8:05 AM
5. `GET /sms/state` (verify SMS received)
6. `POST /simulator/time/skip-to-next` → 8:15 AM
7. `GET /calendar/state` (verify calendar event)
8. `POST /simulator/time/skip-to-next` → 8:20 AM
9. `GET /email/state` (verify email received)
10. `POST /simulator/time/skip-to-next` → 8:30 AM
11. `GET /location/state` (verify location update)
12. `POST /simulator/time/skip-to-next` → 8:35 AM
13. `POST /simulator/time/skip-to-next` → 8:45 AM
14. `GET /weather/state` (verify weather update)
15. `POST /simulator/time/skip-to-next` → 8:55 AM
16. `POST /simulator/time/skip-to-next` → 9:00 AM
17. `GET /chat/state` (verify chat message)

### Verification Phase
18. `GET /environment/state` (full state snapshot)
19. `POST /environment/validate` (verify consistency)
20. `GET /events/summary` (verify all executed)

### Cleanup Phase
21. `POST /simulation/reset`
22. `GET /simulation/status` (verify clean state)
23. `GET /events` (verify queue empty)

---

## Test Assertions

| Step | Assertion |
|------|-----------|
| 3 | `pending_events: 8`, modality counts correct |
| 5 | SMS from +1-555-0199 with grocery request |
| 7 | Calendar event "Team Standup" at 9:00 AM |
| 9 | Email from alice@company.com with agenda |
| 11 | Location is "Outside Home" |
| 14 | Weather conditions "Light Rain", temp ~43°F |
| 17 | Chat message from assistant with contextual info |
| 18 | All modalities have expected state |
| 19 | Validation returns `valid: true` |
| 20 | `executed_events: 8`, `pending_events: 0` |
| 22 | `is_running: false`, counts reset |

---

## Modality Query Tests

After final state, run queries to verify accumulated data:

### SMS Query
```json
{
  "endpoint": "POST /sms/query",
  "request": {"phone_number": "+1-555-0199"},
  "expected": {
    "count": 1,
    "messages[0].body": "contains 'groceries'"
  }
}
```

### Calendar Query
```json
{
  "endpoint": "POST /calendar/query",
  "request": {
    "start_date": "2025-11-28T00:00:00",
    "end_date": "2025-11-28T23:59:59"
  },
  "expected": {
    "count": 1,
    "events[0].title": "Team Standup"
  }
}
```

### Location Query
```json
{
  "endpoint": "POST /location/query",
  "request": {"include_history": true},
  "expected": {
    "history_count": 3,
    "current.location_name": "TechCorp Office"
  }
}
```
