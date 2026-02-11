# UES Scenario File Format Specification

This document provides the complete, authoritative specification for UES scenario file formats. All JSON structures documented here match the actual serialization output of the UES models.

## Overview

UES supports three file formats for saving and loading simulation state:

| Extension | Description | Contents |
|-----------|-------------|----------|
| `.ues-scenario.json` | Complete scenario | Metadata + Environment + Events |
| `.ues-env.json` | Environment only | Metadata + Environment |
| `.ues-events.json` | Event queue only | Metadata + Events |

All formats use JSON with ISO 8601 datetime strings.

---

## Complete Scenario Format (`.ues-scenario.json`)

A complete scenario file contains three top-level sections:

```json
{
  "metadata": { ... },
  "environment": { ... },
  "events": { ... }
}
```

### Metadata Section

The `metadata` section provides version information and documentation:

```json
{
  "metadata": {
    "ues_version": "0.1.0",
    "scenario_version": "1",
    "created_at": "2024-03-15T14:30:00+00:00",
    "author": "Developer Name",
    "description": "Description of this scenario"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ues_version` | string | Yes | UES version that created this file (e.g., "0.1.0") |
| `scenario_version` | string | Yes | Schema version for this file format (currently "1") |
| `created_at` | string | Yes | ISO 8601 UTC timestamp of creation |
| `author` | string | No | Optional author name/identifier |
| `description` | string | No | Optional human-readable description |

---

## Environment Section

The `environment` section contains the complete simulation state:

```json
{
  "environment": {
    "time_state": { ... },
    "modality_states": { ... }
  }
}
```

### Time State (`time_state`)

Produced by `SimulatorTime.model_dump(mode="json")`:

```json
{
  "time_state": {
    "current_time": "2024-03-15T14:30:00+00:00",
    "time_scale": 1.0,
    "is_paused": false,
    "last_wall_time_update": "2024-03-15T14:30:00+00:00",
    "auto_advance": false
  }
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `current_time` | string | Required | Current simulator time (ISO 8601) |
| `time_scale` | float | 1.0 | Time multiplier (must be > 0) |
| `is_paused` | boolean | false | Whether time is frozen |
| `last_wall_time_update` | string | Required | Wall-clock time of last update (ISO 8601) |
| `auto_advance` | boolean | false | Whether time auto-advances with wall time |

### Modality States (`modality_states`)

A dictionary mapping modality type names to their serialized state:

```json
{
  "modality_states": {
    "location": { ... },
    "time": { ... },
    "weather": { ... },
    "chat": { ... },
    "email": { ... },
    "calendar": { ... },
    "sms": { ... }
  }
}
```

Each state is produced by `ModalityState.model_dump(mode="json")`.

---

## Events Section

The `events` section contains all scheduled and executed events:

```json
{
  "events": {
    "events": [
      { ... },
      { ... }
    ]
  }
}
```

### SimulatorEvent Structure

Each event in the array has the following structure:

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "scheduled_time": "2024-03-15T15:00:00+00:00",
  "modality": "email",
  "data": { ... },
  "status": "pending",
  "created_at": "2024-03-15T14:30:00+00:00",
  "executed_at": null,
  "agent_id": null,
  "priority": 0,
  "error_message": null,
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | string | Yes | UUID for this event (regenerated on load by default) |
| `scheduled_time` | string | Yes | When event should execute (ISO 8601) |
| `modality` | string | Yes | Which modality this affects |
| `data` | object | Yes | ModalityInput payload (see modality sections) |
| `status` | string | Yes | Event status (see below) |
| `created_at` | string | Yes | When event was created (ISO 8601) |
| `executed_at` | string | No | When event was executed (ISO 8601), null if not executed |
| `agent_id` | string | No | ID of agent that generated this event |
| `priority` | integer | No | Secondary ordering (higher = first), default 0 |
| `error_message` | string | No | Error details if status is "failed" |
| `metadata` | object | No | Additional extensible data |

#### Event Status Values

| Status | Description |
|--------|-------------|
| `pending` | Not yet executed |
| `executing` | Currently being processed |
| `executed` | Successfully completed |
| `failed` | Execution failed (see `error_message`) |
| `skipped` | Skipped (e.g., scheduled before current time) |
| `cancelled` | Manually cancelled |

---

## Modality-Specific Formats

### Common Base Fields

All `ModalityState` objects include these base fields:

```json
{
  "modality_type": "location",
  "last_updated": "2024-03-15T14:30:00+00:00",
  "update_count": 5
}
```

All `ModalityInput` objects (in event `data` field) include these base fields:

```json
{
  "modality_type": "location",
  "timestamp": "2024-03-15T14:30:00+00:00",
  "input_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

---

### Location Modality

#### LocationState

```json
{
  "modality_type": "location",
  "last_updated": "2024-03-15T14:30:00+00:00",
  "update_count": 3,
  "current_latitude": 37.7749,
  "current_longitude": -122.4194,
  "current_address": "123 Market St, San Francisco, CA",
  "current_named_location": "Office",
  "current_altitude": 10.5,
  "current_accuracy": 5.0,
  "current_speed": 0.0,
  "current_bearing": 90.0,
  "location_history": [
    {
      "timestamp": "2024-03-15T13:00:00+00:00",
      "latitude": 37.7849,
      "longitude": -122.4094,
      "address": "456 Pine St, San Francisco, CA",
      "named_location": "Home",
      "altitude": 15.0,
      "accuracy": 10.0,
      "speed": null,
      "bearing": null
    }
  ],
  "max_history_size": 100
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `current_latitude` | float | No | Current latitude (-90 to 90) |
| `current_longitude` | float | No | Current longitude (-180 to 180) |
| `current_address` | string | No | Human-readable address |
| `current_named_location` | string | No | Semantic name (e.g., "Home", "Office") |
| `current_altitude` | float | No | Altitude in meters |
| `current_accuracy` | float | No | GPS accuracy radius in meters |
| `current_speed` | float | No | Speed in m/s |
| `current_bearing` | float | No | Bearing in degrees (0-360) |
| `location_history` | array | Yes | Historical location entries |
| `max_history_size` | integer | Yes | Maximum history entries to retain |

#### LocationInput

```json
{
  "modality_type": "location",
  "timestamp": "2024-03-15T14:30:00+00:00",
  "input_id": "550e8400-e29b-41d4-a716-446655440001",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "address": "123 Market St, San Francisco, CA",
  "named_location": "Office",
  "altitude": 10.5,
  "accuracy": 5.0,
  "speed": 0.0,
  "bearing": 90.0
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `latitude` | float | Yes | Must be -90 to 90 |
| `longitude` | float | Yes | Must be -180 to 180 |
| `address` | string | No | Human-readable address |
| `named_location` | string | No | Semantic location name |
| `altitude` | float | No | Meters above sea level |
| `accuracy` | float | No | Must be ≥ 0 |
| `speed` | float | No | Must be ≥ 0, in m/s |
| `bearing` | float | No | Must be 0-360 |

---

### Time Modality

#### TimeState

```json
{
  "modality_type": "time",
  "last_updated": "2024-03-15T14:30:00+00:00",
  "update_count": 2,
  "timezone": "America/New_York",
  "format_preference": "12h",
  "date_format": "MM/DD/YYYY",
  "locale": "en_US",
  "week_start": "sunday",
  "settings_history": [
    {
      "timestamp": "2024-03-15T10:00:00+00:00",
      "timezone": "UTC",
      "format_preference": "24h",
      "date_format": null,
      "locale": null,
      "week_start": null
    }
  ],
  "max_history_size": 50
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `timezone` | string | Yes | IANA timezone identifier (default: "UTC") |
| `format_preference` | string | Yes | "12h" or "24h" (default: "12h") |
| `date_format` | string | No | Date format string |
| `locale` | string | No | Locale identifier (e.g., "en_US") |
| `week_start` | string | No | "sunday" or "monday" |
| `settings_history` | array | Yes | Historical settings changes |
| `max_history_size` | integer | Yes | Maximum history entries |

#### TimeInput

```json
{
  "modality_type": "time",
  "timestamp": "2024-03-15T14:30:00+00:00",
  "input_id": "550e8400-e29b-41d4-a716-446655440001",
  "timezone": "America/New_York",
  "format_preference": "12h",
  "date_format": "MM/DD/YYYY",
  "locale": "en_US",
  "week_start": "sunday"
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `timezone` | string | Yes | Must be valid IANA timezone |
| `format_preference` | string | Yes | Must be "12h" or "24h" |
| `date_format` | string | No | One of: "MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD", "YYYY/MM/DD", "DD.MM.YYYY", "DD-MM-YYYY" |
| `locale` | string | No | Locale identifier |
| `week_start` | string | No | "sunday" or "monday" |

---

### Weather Modality

#### WeatherState

```json
{
  "modality_type": "weather",
  "last_updated": "2024-03-15T14:30:00+00:00",
  "update_count": 5,
  "locations": {
    "37.77,-122.42": {
      "latitude": 37.77,
      "longitude": -122.42,
      "current_report": { ... },
      "first_seen": "2024-03-15T10:00:00+00:00",
      "last_updated": "2024-03-15T14:30:00+00:00",
      "update_count": 3,
      "report_history": [ ... ]
    }
  },
  "max_history_per_location": 100
}
```

The `current_report` field contains a `WeatherReport` object with OpenWeather API-compatible structure:

```json
{
  "current_report": {
    "lat": 37.77,
    "lon": -122.42,
    "timezone": "America/Los_Angeles",
    "timezone_offset": -25200,
    "current": {
      "dt": 1710516600,
      "sunrise": 1710505200,
      "sunset": 1710548400,
      "temp": 288.15,
      "feels_like": 287.5,
      "pressure": 1013,
      "humidity": 65,
      "dew_point": 281.0,
      "uvi": 3.5,
      "clouds": 25,
      "visibility": 10000,
      "wind_speed": 5.5,
      "wind_deg": 270,
      "wind_gust": 8.0,
      "weather": [
        {
          "id": 801,
          "main": "Clouds",
          "description": "few clouds",
          "icon": "02d"
        }
      ]
    },
    "minutely": [ ... ],
    "hourly": [ ... ],
    "daily": [ ... ],
    "alerts": [ ... ]
  }
}
```

**Note**: Temperature values are in Kelvin (standard OpenWeather API units).

#### WeatherInput

```json
{
  "modality_type": "weather",
  "timestamp": "2024-03-15T14:30:00+00:00",
  "input_id": "550e8400-e29b-41d4-a716-446655440001",
  "latitude": 37.77,
  "longitude": -122.42,
  "report": { ... }
}
```

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `latitude` | float | Yes | Must be -90 to 90 |
| `longitude` | float | Yes | Must be -180 to 180 |
| `report` | object | Yes | WeatherReport object (see above) |

---

### Chat Modality

#### ChatState

```json
{
  "modality_type": "chat",
  "last_updated": "2024-03-15T14:30:00+00:00",
  "update_count": 10,
  "messages": [
    {
      "message_id": "msg-001",
      "conversation_id": "default",
      "role": "user",
      "content": "Hello, assistant!",
      "timestamp": "2024-03-15T14:25:00+00:00",
      "metadata": {}
    },
    {
      "message_id": "msg-002",
      "conversation_id": "default",
      "role": "assistant",
      "content": "Hello! How can I help you?",
      "timestamp": "2024-03-15T14:26:00+00:00",
      "metadata": {"tokens": 12}
    }
  ],
  "conversations": {
    "default": {
      "conversation_id": "default",
      "created_at": "2024-03-15T14:25:00+00:00",
      "last_message_at": "2024-03-15T14:26:00+00:00",
      "message_count": 2,
      "participant_roles": ["user", "assistant"]
    }
  },
  "max_history_size": 1000,
  "default_conversation_id": "default"
}
```

**Multimodal content** is supported as a list of content blocks:

```json
{
  "content": [
    {"type": "text", "text": "What's in this image?"},
    {"type": "image", "source": "url", "url": "https://example.com/image.jpg"}
  ]
}
```

#### ChatInput

```json
{
  "modality_type": "chat",
  "timestamp": "2024-03-15T14:30:00+00:00",
  "input_id": "550e8400-e29b-41d4-a716-446655440001",
  "operation": "send_message",
  "role": "user",
  "content": "Hello!",
  "message_id": "msg-003",
  "conversation_id": "default",
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `operation` | string | Yes | "send_message", "delete_message", or "clear_conversation" |
| `role` | string | For send_message | "user" or "assistant" |
| `content` | string or array | For send_message | Message content (text or multimodal) |
| `message_id` | string | For delete_message | Message to delete (auto-generated for send) |
| `conversation_id` | string | Yes | Conversation identifier (default: "default") |
| `metadata` | object | No | Additional data (tokens, model info, etc.) |

---

### Email Modality

#### EmailState

```json
{
  "modality_type": "email",
  "last_updated": "2024-03-15T14:30:00+00:00",
  "update_count": 15,
  "emails": {
    "msg-001": {
      "message_id": "msg-001",
      "thread_id": "thread-001",
      "from_address": "sender@example.com",
      "to_addresses": ["recipient@example.com"],
      "cc_addresses": [],
      "bcc_addresses": [],
      "reply_to_address": null,
      "subject": "Meeting Tomorrow",
      "body_text": "Hi, let's meet tomorrow at 10am.",
      "body_html": null,
      "attachments": [],
      "in_reply_to": null,
      "references": [],
      "sent_at": "2024-03-15T14:00:00+00:00",
      "received_at": "2024-03-15T14:00:05+00:00",
      "is_read": true,
      "is_starred": false,
      "priority": "normal",
      "folder": "inbox",
      "labels": ["work"]
    }
  },
  "threads": {
    "thread-001": {
      "thread_id": "thread-001",
      "subject": "Meeting Tomorrow",
      "participant_addresses": ["sender@example.com", "recipient@example.com"],
      "message_ids": ["msg-001"],
      "created_at": "2024-03-15T14:00:00+00:00",
      "last_message_at": "2024-03-15T14:00:05+00:00",
      "message_count": 1,
      "unread_count": 0
    }
  },
  "folders": {
    "inbox": ["msg-001"],
    "sent": [],
    "drafts": [],
    "trash": [],
    "spam": [],
    "archive": []
  },
  "labels": {
    "work": ["msg-001"],
    "personal": []
  },
  "drafts": {},
  "user_email_address": "user@example.com"
}
```

#### EmailInput

```json
{
  "modality_type": "email",
  "timestamp": "2024-03-15T14:30:00+00:00",
  "input_id": "550e8400-e29b-41d4-a716-446655440001",
  "operation": "receive",
  "message_id": "msg-002",
  "from_address": "boss@example.com",
  "to_addresses": ["me@example.com"],
  "cc_addresses": [],
  "bcc_addresses": [],
  "reply_to_address": null,
  "subject": "Urgent: Project Update",
  "body_text": "Please send me the project update ASAP.",
  "body_html": null,
  "attachments": [],
  "thread_id": null,
  "in_reply_to": null,
  "references": [],
  "priority": "high",
  "folder": "inbox",
  "labels": ["urgent"],
  "is_draft": false
}
```

| Operation | Description | Required Fields |
|-----------|-------------|-----------------|
| `receive` | Receive incoming email | from_address, to_addresses, subject, body_text |
| `send` | Send new email | from_address, to_addresses, subject, body_text |
| `reply` | Reply to email | in_reply_to, body_text |
| `reply_all` | Reply to all | in_reply_to, body_text |
| `forward` | Forward email | message_id, to_addresses |
| `mark_read` | Mark as read | message_id or message_ids |
| `mark_unread` | Mark as unread | message_id or message_ids |
| `star` | Star email | message_id |
| `unstar` | Remove star | message_id |
| `move` | Move to folder | message_id, folder |
| `delete` | Delete email | message_id |
| `archive` | Archive email | message_id |
| `add_label` | Add label | message_id, labels |
| `remove_label` | Remove label | message_id, labels |

---

### Calendar Modality

#### CalendarState

```json
{
  "modality_type": "calendar",
  "last_updated": "2024-03-15T14:30:00+00:00",
  "update_count": 8,
  "calendars": {
    "cal-001": {
      "calendar_id": "cal-001",
      "name": "Work",
      "color": "#4285f4",
      "visible": true,
      "created_at": "2024-01-01T00:00:00+00:00",
      "updated_at": "2024-03-15T14:30:00+00:00",
      "event_ids": ["evt-001", "evt-002"],
      "default_reminders": [
        {"method": "notification", "minutes_before": 10}
      ]
    }
  },
  "events": {
    "evt-001": {
      "event_id": "evt-001",
      "calendar_id": "cal-001",
      "title": "Team Meeting",
      "start": "2024-03-16T10:00:00+00:00",
      "end": "2024-03-16T11:00:00+00:00",
      "all_day": false,
      "timezone": "America/New_York",
      "description": "Weekly team sync",
      "location": "Conference Room A",
      "status": "confirmed",
      "organizer": "manager@example.com",
      "attendees": [
        {
          "email": "developer@example.com",
          "display_name": "Dev",
          "optional": false,
          "response": "accepted",
          "comment": null
        }
      ],
      "recurrence": {
        "frequency": "weekly",
        "interval": 1,
        "days_of_week": ["monday"],
        "end_type": "never"
      },
      "recurrence_exceptions": [],
      "recurrence_id": null,
      "parent_event_id": null,
      "reminders": [
        {"method": "notification", "minutes_before": 10}
      ],
      "color": null,
      "visibility": "default",
      "transparency": "opaque",
      "attachments": [],
      "conference_link": "https://meet.example.com/team",
      "created_at": "2024-03-01T10:00:00+00:00",
      "updated_at": "2024-03-15T14:30:00+00:00",
      "deleted_at": null
    }
  },
  "default_calendar_id": "cal-001"
}
```

#### CalendarInput

```json
{
  "modality_type": "calendar",
  "timestamp": "2024-03-15T14:30:00+00:00",
  "input_id": "550e8400-e29b-41d4-a716-446655440001",
  "operation": "create",
  "event_id": "evt-002",
  "calendar_id": "cal-001",
  "title": "Project Review",
  "start": "2024-03-17T14:00:00+00:00",
  "end": "2024-03-17T15:00:00+00:00",
  "all_day": false,
  "timezone": "America/New_York",
  "description": "Q1 project review meeting",
  "location": "Conference Room B",
  "attendees": [
    {"email": "stakeholder@example.com", "optional": false}
  ],
  "reminders": [
    {"method": "email", "minutes_before": 60}
  ]
}
```

| Operation | Description | Required Fields |
|-----------|-------------|-----------------|
| `create` | Create new event | calendar_id, title, start, end |
| `update` | Update existing event | event_id, (fields to update) |
| `delete` | Delete event | event_id |

**Recurrence Rule Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `frequency` | string | "daily", "weekly", "monthly", "yearly" |
| `interval` | integer | Repeat every N periods (default: 1) |
| `days_of_week` | array | For weekly: ["monday", "tuesday", ...] |
| `day_of_month` | integer | For monthly: 1-31 |
| `month_of_year` | integer | For yearly: 1-12 |
| `end_type` | string | "never", "until", "count" |
| `end_date` | string | End date for "until" (ISO date) |
| `count` | integer | Occurrence count for "count" |

---

### SMS Modality

#### SMSState

```json
{
  "modality_type": "sms",
  "last_updated": "2024-03-15T14:30:00+00:00",
  "update_count": 20,
  "conversations": {
    "conv-001": {
      "conversation_id": "conv-001",
      "is_group": false,
      "participants": {
        "+15551234567": {
          "phone_number": "+15551234567",
          "is_admin": false,
          "joined_at": "2024-03-01T00:00:00+00:00",
          "left_at": null
        }
      },
      "group_name": null,
      "group_avatar_url": null,
      "created_at": "2024-03-01T00:00:00+00:00",
      "updated_at": "2024-03-15T14:30:00+00:00",
      "is_muted": false,
      "is_pinned": false,
      "is_archived": false
    }
  },
  "messages": {
    "msg-001": {
      "message_id": "msg-001",
      "conversation_id": "conv-001",
      "from_number": "+15551234567",
      "to_numbers": ["+15559876543"],
      "body": "Hey, are you free tonight?",
      "message_type": "sms",
      "delivery_status": "delivered",
      "sent_at": "2024-03-15T14:25:00+00:00",
      "delivered_at": "2024-03-15T14:25:02+00:00",
      "read_at": "2024-03-15T14:26:00+00:00",
      "attachments": [],
      "reactions": [],
      "is_edited": false,
      "edited_at": null,
      "is_deleted": false,
      "deleted_at": null,
      "reply_to_message_id": null
    }
  },
  "user_phone_number": "+15559876543"
}
```

#### SMSInput

```json
{
  "modality_type": "sms",
  "timestamp": "2024-03-15T14:30:00+00:00",
  "input_id": "550e8400-e29b-41d4-a716-446655440001",
  "operation": "receive_message",
  "from_number": "+15551234567",
  "to_numbers": ["+15559876543"],
  "body": "Sure, let's meet at 7pm!",
  "message_type": "sms"
}
```

| Operation | Description | Required Fields |
|-----------|-------------|-----------------|
| `send_message` | Send SMS/RCS | `from_number`, `to_numbers`, `body` |
| `receive_message` | Receive SMS/RCS | `from_number`, `to_numbers`, `body` |
| `update_delivery_status` | Update delivery status | `message_id`, `new_status` |
| `add_reaction` | Add emoji reaction | `message_id`, `phone_number`, `emoji` |
| `remove_reaction` | Remove reaction | `message_id`, `reaction_id` |
| `edit_message` | Edit message (RCS) | `message_id`, `new_body` |
| `delete_message` | Delete message | `message_id` |
| `create_group` | Create group chat | `creator_number`, `participant_numbers` |
| `update_group` | Update group settings | `thread_id` |
| `add_participant` | Add to group | `thread_id`, `phone_number` |
| `remove_participant` | Remove from group | `thread_id`, `phone_number` |
| `leave_group` | Leave group | `thread_id` |
| `update_conversation` | Update conversation | `thread_id` + at least one flag |

**Message Fields (send_message, receive_message)**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `from_number` | string | Yes | Sender phone number |
| `to_numbers` | array | Yes | Recipient phone numbers |
| `body` | string | Yes | Message text content |
| `message_type` | string | No | "sms" or "rcs" (default: "sms") |
| `attachments` | array | No | Media attachments (list of MessageAttachmentData) |
| `thread_id` | string | No | Existing conversation ID (auto-created if not provided) |
| `replied_to_message_id` | string | No | ID of message being replied to |

---

## Version Compatibility

### Format Version History

| Version | UES Version | Changes |
|---------|-------------|---------|
| 1 | 0.1.0+ | Initial format |

### Compatibility Rules

1. **Forward compatibility**: UES will attempt to load scenarios from newer format versions, skipping unknown fields with warnings.

2. **Backward compatibility**: Scenarios created with older UES versions should load without issues in newer versions.

3. **Modality compatibility**: If a scenario contains modalities not registered in the current UES instance:
   - **Strict mode** (default): Loading fails with an error
   - **Non-strict mode**: Unknown modalities are skipped with warnings

### Event ID Regeneration

By default, `event_id` values are regenerated when loading scenarios to prevent conflicts with existing events. Set `regenerate_ids=false` in the API request to preserve original IDs.

---

## File Extension Conventions

| Extension | Use Case |
|-----------|----------|
| `.ues-scenario.json` | Complete scenario (environment + events) |
| `.ues-env.json` | Environment state only |
| `.ues-events.json` | Event queue only |

These extensions are conventions for clarity; any `.json` file with the correct structure will load successfully.

---

## Validation Rules

### Required Fields

The following fields are always required in a valid scenario file:

- `metadata.ues_version`
- `metadata.scenario_version`
- `metadata.created_at`
- `environment.time_state` (for scenarios/environments)
- `environment.modality_states` (for scenarios/environments)
- `events.events` (for scenarios/event queues)

### Datetime Format

All datetime fields must be:
- ISO 8601 format
- Timezone-aware (include offset or "Z" for UTC)

Examples:
- `"2024-03-15T14:30:00+00:00"` ✓
- `"2024-03-15T10:30:00-04:00"` ✓
- `"2024-03-15T14:30:00Z"` ✓ (converted to +00:00)
- `"2024-03-15T14:30:00"` ✗ (naive datetime, will be converted to UTC)

### Modality Type Consistency

For each modality:
- The dictionary key in `modality_states` must match the `modality_type` field
- Event `modality` field must match `data.modality_type`

---

## Examples

See the [examples/scenarios/](../../examples/scenarios/) directory for complete example scenario files.
