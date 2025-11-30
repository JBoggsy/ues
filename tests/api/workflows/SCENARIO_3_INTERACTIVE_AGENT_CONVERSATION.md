# Scenario 3: Interactive Agent Conversation with Scheduling

## Executive Summary

This scenario simulates a complex, interactive session where a user communicates with an AI assistant through chat, triggering actions across multiple modalities. The assistant must:

- Respond to user queries about their schedule
- Detect and handle calendar conflicts
- Create new calendar events based on user requests
- Manage email state (marking as read, starring)
- Provide contextual reminders based on time

This tests the system's ability to handle immediate events (agent responses), cross-modality state queries, and realistic conversational workflows that an AI personal assistant would encounter.

**Complexity**: Complex  
**Modalities Used**: Chat, Calendar, Email, Location  
**Total Events**: ~18 events (mix of scheduled and immediate)  
**Simulated Duration**: ~3.5 hours (1:30 PM - 5:00 PM)  

---

## Scenario Context

**User Profile**:
- Name: Alex Developer
- Email: alex@example.com
- Work Location: TechCorp Office

**Pre-populated State** (set before simulation starts):
- **Calendar**: 1 existing event (Dentist at 2:00 PM)
- **Email**: 3 unread emails in inbox
- **Location**: Office
- **Chat**: Empty (fresh conversation)

---

## Detailed Timeline

### Phase 1: Initial State Setup

| Time | Event # | Type | Description |
|------|---------|------|-------------|
| 1:30 PM | Setup-1 | Calendar | Pre-existing dentist appointment |
| 1:30 PM | Setup-2 | Email | Unread email from HR |
| 1:30 PM | Setup-3 | Email | Unread email from Bob |
| 1:30 PM | Setup-4 | Email | Unread email from Newsletter |
| 1:30 PM | Setup-5 | Location | Set location to office |

### Phase 2: Schedule Query (1:30 PM - 1:32 PM)

| Time | Event # | Type | Description |
|------|---------|------|-------------|
| 1:30 PM | 1 | Chat (User) | "What's on my schedule today?" |
| 1:30 PM | 2 | Chat (Assistant) | Response listing dentist appointment |

### Phase 3: Scheduling with Conflict (1:32 PM - 1:38 PM)

| Time | Event # | Type | Description |
|------|---------|------|-------------|
| 1:32 PM | 3 | Chat (User) | "Schedule a meeting with Bob at 2:00 PM" |
| 1:32 PM | 4 | Chat (Assistant) | Detects conflict, suggests alternatives |
| 1:34 PM | 5 | Chat (User) | "Make it 3:00 PM instead" |
| 1:34 PM | 6 | Chat (Assistant) | Confirms and creates event |
| 1:34 PM | 7 | Calendar | New event: Meeting with Bob at 3:00 PM |

### Phase 4: Email Management (1:38 PM - 1:42 PM)

| Time | Event # | Type | Description |
|------|---------|------|-------------|
| 1:38 PM | 8 | Email | Bob sends meeting confirmation email |
| 1:40 PM | 9 | Chat (User) | "Mark Bob's email as read and star it" |
| 1:40 PM | 10 | Chat (Assistant) | Confirms actions taken |
| 1:40 PM | 11 | Email Action | Mark Bob's email as read |
| 1:40 PM | 12 | Email Action | Star Bob's email |

### Phase 5: Time Jump and Reminders (1:42 PM - 2:00 PM)

| Time | Event # | Type | Description |
|------|---------|------|-------------|
| 1:45 PM | 13 | Chat (Assistant) | Proactive reminder: Dentist in 15 minutes |
| 2:00 PM | - | Time Jump | User at dentist (no events) |

### Phase 6: End of Day Summary (5:00 PM)

| Time | Event # | Type | Description |
|------|---------|------|-------------|
| 5:00 PM | 14 | Chat (User) | "Give me a summary of my day" |
| 5:00 PM | 15 | Chat (Assistant) | Summary of events, emails, actions |

---

## Pre-populated State Contents

### Setup-1: Existing Dentist Appointment

```json
{
  "modality": "calendar",
  "scheduled_time": "2025-11-28T13:30:00",
  "priority": 50,
  "data": {
    "action": "create",
    "event_data": {
      "title": "Dentist Appointment",
      "description": "Regular 6-month checkup and cleaning.\n\nDr. Sarah Chen\nBright Smiles Dental\n(555) 234-5678",
      "start_time": "2025-11-28T14:00:00",
      "end_time": "2025-11-28T15:00:00",
      "location": "Bright Smiles Dental, 456 Health Ave, New York, NY",
      "attendees": ["alex@example.com"],
      "reminders": [
        {"minutes_before": 60, "method": "notification"},
        {"minutes_before": 15, "method": "notification"}
      ],
      "calendar_id": "personal"
    }
  },
  "metadata": {
    "event_type": "appointment",
    "category": "health"
  }
}
```

### Setup-2: Unread Email from HR

```json
{
  "modality": "email",
  "scheduled_time": "2025-11-28T13:30:00",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "hr@company.com",
    "to_addresses": ["alex@example.com"],
    "subject": "Holiday Schedule Reminder",
    "body_text": "Hi Alex,\n\nThis is a friendly reminder about the upcoming holiday schedule:\n\n- Thursday, Nov 28: Thanksgiving (Office Closed)\n- Friday, Nov 29: Day After Thanksgiving (Office Closed)\n\nPlease ensure all urgent tasks are completed before the break.\n\nHappy Holidays!\nHR Team",
    "body_html": null,
    "headers": {}
  },
  "metadata": {
    "category": "administrative",
    "priority": "low"
  }
}
```

### Setup-3: Unread Email from Bob

```json
{
  "modality": "email",
  "scheduled_time": "2025-11-28T13:30:01",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "bob@company.com",
    "to_addresses": ["alex@example.com"],
    "subject": "Quick sync about the API project?",
    "body_text": "Hey Alex,\n\nDo you have some time today to sync up about the API project? I have some questions about the authentication flow and wanted to discuss the timeline.\n\nLet me know what works for you.\n\nBob",
    "body_html": null,
    "headers": {}
  },
  "metadata": {
    "category": "work",
    "priority": "normal",
    "requires_response": true
  }
}
```

### Setup-4: Unread Newsletter Email

```json
{
  "modality": "email",
  "scheduled_time": "2025-11-28T13:30:02",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "newsletter@techweekly.com",
    "to_addresses": ["alex@example.com"],
    "subject": "Tech Weekly: AI Agents and the Future of Work",
    "body_text": "TECH WEEKLY - November 28, 2025\n\n📰 TOP STORIES\n\n1. AI Agents Transform Personal Productivity\n   New research shows 40% productivity gains...\n\n2. OpenAI Announces GPT-5 Preview\n   Early access program begins next month...\n\n3. The Rise of Agentic Workflows\n   How companies are automating complex tasks...\n\nRead more at techweekly.com",
    "body_html": null,
    "headers": {
      "List-Unsubscribe": "<mailto:unsubscribe@techweekly.com>"
    }
  },
  "metadata": {
    "category": "newsletter",
    "priority": "low"
  }
}
```

### Setup-5: Initial Location

```json
{
  "modality": "location",
  "scheduled_time": "2025-11-28T13:30:00",
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
    "venue_type": "workplace"
  }
}
```

---

## Phase 2: Schedule Query

### Event 1: User Asks About Schedule

**Time**: 1:30 PM (immediate after setup)

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:30:30",
  "priority": 80,
  "data": {
    "role": "user",
    "content": "What's on my schedule today?",
    "conversation_id": "main"
  },
  "metadata": {
    "intent": "query_calendar",
    "user_initiated": true
  }
}
```

### Event 2: Assistant Response - Schedule Overview

**Time**: 1:30 PM (immediate response)

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:30:35",
  "priority": 80,
  "data": {
    "role": "assistant",
    "content": "Here's your schedule for today, November 28th:\n\n📅 **Today's Events:**\n\n• **2:00 PM - 3:00 PM**: Dentist Appointment\n  📍 Bright Smiles Dental, 456 Health Ave\n  🦷 Regular checkup with Dr. Sarah Chen\n\nYou have one appointment this afternoon. The rest of your day appears to be open.\n\nWould you like me to help you schedule anything else?",
    "conversation_id": "main"
  },
  "metadata": {
    "response_type": "calendar_summary",
    "events_found": 1,
    "context_used": ["calendar"]
  }
}
```

---

## Phase 3: Scheduling with Conflict

### Event 3: User Requests Conflicting Meeting

**Time**: 1:32 PM

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:32:00",
  "priority": 80,
  "data": {
    "role": "user",
    "content": "Schedule a meeting with Bob at 2:00 PM",
    "conversation_id": "main"
  },
  "metadata": {
    "intent": "create_calendar_event",
    "extracted_entities": {
      "attendee": "Bob",
      "time": "2:00 PM"
    }
  }
}
```

### Event 4: Assistant Detects Conflict

**Time**: 1:32 PM (immediate response)

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:32:05",
  "priority": 80,
  "data": {
    "role": "assistant",
    "content": "⚠️ **Scheduling Conflict Detected**\n\nYou have a **Dentist Appointment** scheduled from 2:00 PM - 3:00 PM today.\n\nWould you like me to:\n1. Schedule the meeting with Bob at **3:00 PM** (after your dentist appointment)\n2. Schedule it at **1:00 PM** (before your appointment)\n3. Schedule it for a different day\n\nOr would you prefer to reschedule your dentist appointment?",
    "conversation_id": "main"
  },
  "metadata": {
    "response_type": "conflict_resolution",
    "conflict_with": "Dentist Appointment",
    "suggested_alternatives": ["15:00", "13:00", "different_day"]
  }
}
```

### Event 5: User Chooses Alternative Time

**Time**: 1:34 PM

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:34:00",
  "priority": 80,
  "data": {
    "role": "user",
    "content": "Make it 3:00 PM instead",
    "conversation_id": "main"
  },
  "metadata": {
    "intent": "confirm_alternative",
    "selected_time": "15:00"
  }
}
```

### Event 6: Assistant Confirms Creation

**Time**: 1:34 PM (immediate response)

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:34:05",
  "priority": 80,
  "data": {
    "role": "assistant",
    "content": "✅ **Meeting Scheduled**\n\nI've created a meeting with Bob:\n\n📅 **Meeting with Bob**\n🕒 Today, 3:00 PM - 3:30 PM\n📍 TechCorp Office (your current location)\n\nI'll send Bob an invite. Is there anything specific you'd like to discuss that I should include in the meeting description?",
    "conversation_id": "main"
  },
  "metadata": {
    "response_type": "confirmation",
    "action_taken": "calendar_event_created",
    "event_id": "meeting-bob-001"
  }
}
```

### Event 7: Calendar Event Created

**Time**: 1:34 PM (triggered by assistant)

```json
{
  "modality": "calendar",
  "scheduled_time": "2025-11-28T13:34:10",
  "priority": 70,
  "data": {
    "action": "create",
    "event_data": {
      "title": "Meeting with Bob",
      "description": "Sync meeting to discuss API project.\n\nScheduled via AI Assistant.",
      "start_time": "2025-11-28T15:00:00",
      "end_time": "2025-11-28T15:30:00",
      "location": "TechCorp Office",
      "attendees": ["alex@example.com", "bob@company.com"],
      "reminders": [
        {"minutes_before": 15, "method": "notification"}
      ],
      "calendar_id": "work"
    }
  },
  "metadata": {
    "created_by": "assistant",
    "context": "user_request",
    "original_conflict_resolved": true
  }
}
```

---

## Phase 4: Email Management

### Event 8: Bob Sends Confirmation Email

**Time**: 1:38 PM

```json
{
  "modality": "email",
  "scheduled_time": "2025-11-28T13:38:00",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "bob@company.com",
    "to_addresses": ["alex@example.com"],
    "subject": "Re: Meeting Invite - Meeting with Bob",
    "body_text": "Thanks Alex!\n\nI accepted the invite for 3 PM. Looking forward to discussing the API project.\n\nI'll bring my notes on the authentication questions.\n\nSee you then!\nBob",
    "body_html": null,
    "headers": {
      "In-Reply-To": "<meeting-invite-001@calendar.company.com>",
      "References": "<meeting-invite-001@calendar.company.com>"
    }
  },
  "metadata": {
    "thread_id": "meeting-bob-thread",
    "is_reply": true,
    "meeting_response": "accepted"
  }
}
```

### Event 9: User Requests Email Actions

**Time**: 1:40 PM

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:40:00",
  "priority": 80,
  "data": {
    "role": "user",
    "content": "Mark Bob's email as read and star it",
    "conversation_id": "main"
  },
  "metadata": {
    "intent": "email_action",
    "target": "bob@company.com",
    "actions": ["mark_read", "star"]
  }
}
```

### Event 10: Assistant Confirms Email Actions

**Time**: 1:40 PM (immediate response)

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:40:05",
  "priority": 80,
  "data": {
    "role": "assistant",
    "content": "✅ Done! I've updated Bob's emails:\n\n📧 **\"Re: Meeting Invite - Meeting with Bob\"**\n• Marked as read\n• ⭐ Starred\n\n📧 **\"Quick sync about the API project?\"**\n• Marked as read\n• ⭐ Starred\n\nYou now have **2 unread emails** remaining in your inbox (HR holiday reminder and Tech Weekly newsletter).",
    "conversation_id": "main"
  },
  "metadata": {
    "response_type": "action_confirmation",
    "emails_modified": 2,
    "actions_performed": ["mark_read", "star"]
  }
}
```

### Event 11: Email Action - Mark as Read

**Time**: 1:40 PM (triggered by assistant)

*Note: This represents the API calls made to update email state*

```json
{
  "action": "mark_read",
  "target_emails": [
    {"from": "bob@company.com", "subject": "Re: Meeting Invite - Meeting with Bob"},
    {"from": "bob@company.com", "subject": "Quick sync about the API project?"}
  ]
}
```

### Event 12: Email Action - Star

**Time**: 1:40 PM (triggered by assistant)

```json
{
  "action": "star",
  "target_emails": [
    {"from": "bob@company.com", "subject": "Re: Meeting Invite - Meeting with Bob"},
    {"from": "bob@company.com", "subject": "Quick sync about the API project?"}
  ]
}
```

---

## Phase 5: Time Jump and Reminders

### Event 13: Proactive Dentist Reminder

**Time**: 1:45 PM

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T13:45:00",
  "priority": 70,
  "data": {
    "role": "assistant",
    "content": "⏰ **Reminder**: Your dentist appointment is in **15 minutes**!\n\n📍 Bright Smiles Dental\n   456 Health Ave, New York, NY\n\n🚗 Based on your current location, it's about a 10-minute trip. You should leave soon to arrive on time.\n\nWould you like me to:\n• Get directions?\n• Let Bob know you might be a few minutes late to your 3 PM meeting if your appointment runs over?",
    "conversation_id": "main"
  },
  "metadata": {
    "message_type": "proactive_reminder",
    "trigger": "calendar_reminder_15min",
    "event_title": "Dentist Appointment",
    "context_used": ["calendar", "location"]
  }
}
```

---

## Phase 6: End of Day Summary

### Event 14: User Requests Daily Summary

**Time**: 5:00 PM

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T17:00:00",
  "priority": 80,
  "data": {
    "role": "user",
    "content": "Give me a summary of my day",
    "conversation_id": "main"
  },
  "metadata": {
    "intent": "daily_summary"
  }
}
```

### Event 15: Assistant Provides Daily Summary

**Time**: 5:00 PM (immediate response)

```json
{
  "modality": "chat",
  "scheduled_time": "2025-11-28T17:00:05",
  "priority": 80,
  "data": {
    "role": "assistant",
    "content": "📊 **Daily Summary - November 28, 2025**\n\n---\n\n**📅 Calendar (2 events)**\n• ✅ Dentist Appointment (2:00 PM - 3:00 PM)\n• ✅ Meeting with Bob (3:00 PM - 3:30 PM)\n\n---\n\n**📧 Email Activity**\n• Received: 4 emails\n• Read: 2 (Bob's emails)\n• Starred: 2\n• Unread: 2 (HR reminder, Tech Weekly)\n\n---\n\n**💬 Our Conversation**\n• Reviewed your schedule\n• Resolved a scheduling conflict\n• Scheduled meeting with Bob\n• Managed Bob's emails\n\n---\n\n**🔮 Tomorrow**\nNo events scheduled yet. Would you like me to help you plan anything?\n\n---\n\nHave a great evening! 🌙",
    "conversation_id": "main"
  },
  "metadata": {
    "response_type": "daily_summary",
    "summary_stats": {
      "calendar_events": 2,
      "emails_received": 4,
      "emails_read": 2,
      "chat_messages": 10
    }
  }
}
```

---

## State Verification Checkpoints

### After Setup Phase (1:30 PM)
```json
{
  "calendar": {
    "events": 1,
    "event_titles": ["Dentist Appointment"]
  },
  "email": {
    "inbox_count": 3,
    "unread_count": 3,
    "from_addresses": ["hr@company.com", "bob@company.com", "newsletter@techweekly.com"]
  },
  "location": {
    "current_name": "TechCorp Office"
  },
  "chat": {
    "messages": 0
  }
}
```

### After Phase 3 (1:34 PM)
```json
{
  "calendar": {
    "events": 2,
    "event_titles": ["Dentist Appointment", "Meeting with Bob"]
  },
  "chat": {
    "messages": 6,
    "user_messages": 3,
    "assistant_messages": 3
  }
}
```

### After Phase 4 (1:40 PM)
```json
{
  "email": {
    "inbox_count": 4,
    "unread_count": 2,
    "starred_count": 2,
    "read_emails": [
      {"from": "bob@company.com", "starred": true},
      {"from": "bob@company.com", "starred": true}
    ]
  },
  "chat": {
    "messages": 8
  }
}
```

### Final State (5:00 PM)
```json
{
  "current_time": "2025-11-28T17:00:05",
  "calendar": {
    "events": 2,
    "all_completed": true
  },
  "email": {
    "inbox_count": 4,
    "unread_count": 2,
    "starred_count": 2
  },
  "chat": {
    "total_messages": 11,
    "user_messages": 4,
    "assistant_messages": 7
  },
  "location": {
    "current_name": "TechCorp Office"
  }
}
```

---

## API Calls Sequence

### Setup Phase
1. `POST /simulation/start` with `{"auto_advance": false}`
2. `POST /events` × 5 (setup events)
3. `POST /simulator/time/advance` with `{"seconds": 1}` (execute setup)
4. `GET /environment/state` (verify initial state)

### Phase 2: Schedule Query
5. `POST /events` (Event 1: user asks about schedule)
6. `POST /events` (Event 2: assistant response)
7. `POST /simulator/time/advance` with `{"seconds": 30}`
8. `GET /chat/state` (verify conversation)
9. `GET /calendar/state` (verify calendar accessed)

### Phase 3: Scheduling with Conflict
10. `POST /simulator/time/set` to 1:32 PM
11. `POST /events` (Event 3: user requests meeting)
12. `POST /events` (Event 4: assistant detects conflict)
13. `POST /simulator/time/advance` with `{"seconds": 5}`
14. `POST /simulator/time/set` to 1:34 PM
15. `POST /events` (Event 5: user chooses 3 PM)
16. `POST /events` (Event 6: assistant confirms)
17. `POST /events` (Event 7: calendar event created)
18. `POST /simulator/time/advance` with `{"seconds": 15}`
19. `GET /calendar/state` (verify 2 events)

### Phase 4: Email Management
20. `POST /simulator/time/set` to 1:38 PM
21. `POST /events` (Event 8: Bob's confirmation email)
22. `POST /simulator/time/advance` with `{"seconds": 1}`
23. `GET /email/state` (verify 4 emails)
24. `POST /simulator/time/set` to 1:40 PM
25. `POST /events` (Event 9: user requests email actions)
26. `POST /events` (Event 10: assistant confirms)
27. `POST /email/read` (mark Bob's emails as read)
28. `POST /email/star` (star Bob's emails)
29. `POST /simulator/time/advance` with `{"seconds": 5}`
30. `GET /email/state` (verify read and starred)

### Phase 5: Proactive Reminder
31. `POST /simulator/time/set` to 1:45 PM
32. `POST /events` (Event 13: proactive reminder)
33. `POST /simulator/time/advance` with `{"seconds": 1}`
34. `GET /chat/state` (verify reminder in chat)

### Phase 6: End of Day Summary
35. `POST /simulator/time/set` to 5:00 PM
36. `POST /events` (Event 14: user requests summary)
37. `POST /events` (Event 15: assistant provides summary)
38. `POST /simulator/time/advance` with `{"seconds": 10}`
39. `GET /chat/state` (verify full conversation)

### Final Verification
40. `GET /environment/state` (complete state snapshot)
41. `GET /events/summary` (all events executed)
42. `POST /simulation/stop` (get final statistics)

---

## Test Assertions

| Phase | Assertion |
|-------|-----------|
| Setup | Calendar has 1 event, Email has 3 unread, Location at office |
| Phase 2 | Chat has 2 messages, assistant correctly lists dentist appointment |
| Phase 3 | Calendar has 2 events, Meeting with Bob at 3 PM (not 2 PM) |
| Phase 4 | 2 emails from Bob marked as read and starred, 2 unread remaining |
| Phase 5 | Proactive reminder appears in chat at 1:45 PM |
| Phase 6 | Summary message contains accurate counts |
| Final | All 15+ events executed successfully, no failures |

---

## Key Integration Points Tested

1. **Calendar Conflict Detection**: Assistant must check calendar before scheduling
2. **Cross-Modality Context**: Assistant references multiple modalities in responses
3. **Immediate Event Creation**: Agent responses created as immediate events
4. **Email State Manipulation**: Direct API calls to modify email state
5. **Time-Based Triggers**: Proactive reminders based on calendar events
6. **Conversational Flow**: Multi-turn conversation with context retention
7. **Summary Generation**: Aggregating state from multiple modalities
