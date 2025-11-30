# Scenario 1: Basic Manual Time Control

## Executive Summary

This scenario tests the fundamental simulation lifecycle and manual time advancement with a simple email-only workflow. It validates that:

- The simulation can be started in manual mode
- Events can be scheduled at specific future times
- Manual time advancement executes events in the correct order
- Pause/resume functionality works correctly
- Environment state accurately reflects executed events
- Simulation stop returns accurate statistics

**Complexity**: Simple  
**Modalities Used**: Email only  
**Total Events**: 3 scheduled emails  
**Estimated Duration**: ~3 minutes of simulated time  

---

## Detailed Timeline

| Sim Time | Real Step | Action | Expected Outcome |
|----------|-----------|--------|------------------|
| T+0:00 | 1 | Start simulation in manual mode | Simulation running, time at T+0 |
| T+0:00 | 2 | Create Email #1 scheduled for T+1:00 | Event created with pending status |
| T+0:00 | 3 | Create Email #2 scheduled for T+2:00 | Event created with pending status |
| T+0:00 | 4 | Create Email #3 scheduled for T+3:00 | Event created with pending status |
| T+0:00 | 5 | Verify 3 pending events in queue | Event summary shows 3 pending |
| T+0:00 → T+1:00 | 6 | Advance time by 60 seconds | Time advances, Email #1 executed |
| T+1:00 | 7 | Verify Email #1 in inbox | Email state shows 1 email |
| T+1:00 | 8 | Pause simulation | Simulation paused |
| T+1:00 | 9 | Attempt to advance time | Should fail (409 Conflict) |
| T+1:00 | 10 | Verify time unchanged | Time still at T+1:00 |
| T+1:00 | 11 | Resume simulation | Simulation resumed |
| T+1:00 → T+3:00 | 12 | Advance time by 120 seconds | Email #2 and #3 executed |
| T+3:00 | 13 | Verify all 3 emails in inbox | Email state shows 3 emails |
| T+3:00 | 14 | Query email state | All emails present with correct details |
| T+3:00 | 15 | Stop simulation | Returns accurate event counts |

---

## Event Contents

### Email #1: Meeting Reminder from Calendar System

**Scheduled Time**: T+1:00 (60 seconds after simulation start)

```json
{
  "modality": "email",
  "scheduled_time": "<T+60s>",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "calendar@company.com",
    "to_addresses": ["user@example.com"],
    "subject": "Reminder: Team Standup in 30 minutes",
    "body_text": "This is a reminder that your meeting 'Team Standup' starts at 9:30 AM.\n\nLocation: Conference Room B\nDuration: 30 minutes\n\nClick here to join the video call or view meeting details.",
    "body_html": null,
    "headers": {
      "X-Calendar-Event-ID": "evt-standup-001",
      "X-Priority": "normal"
    }
  },
  "metadata": {
    "source": "calendar_integration",
    "event_type": "meeting_reminder"
  }
}
```

**Expected State After Execution**:
- Email appears in inbox with `is_read: false`
- Email has `is_starred: false`
- Email has `folder: "inbox"`

---

### Email #2: Message from Coworker

**Scheduled Time**: T+2:00 (120 seconds after simulation start)

```json
{
  "modality": "email",
  "scheduled_time": "<T+120s>",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "alice.johnson@company.com",
    "to_addresses": ["user@example.com"],
    "subject": "Quick question about the project",
    "body_text": "Hey,\n\nDo you have a minute to chat about the API documentation? I found a few inconsistencies I wanted to run by you before the review meeting.\n\nLet me know when you're free.\n\nThanks,\nAlice",
    "body_html": null,
    "headers": {}
  },
  "metadata": {
    "source": "external",
    "sender_department": "engineering"
  }
}
```

**Expected State After Execution**:
- Email appears in inbox with `is_read: false`
- Total inbox count: 2

---

### Email #3: Automated Report

**Scheduled Time**: T+3:00 (180 seconds after simulation start)

```json
{
  "modality": "email",
  "scheduled_time": "<T+180s>",
  "priority": 50,
  "data": {
    "operation": "receive",
    "from_address": "noreply@analytics.company.com",
    "to_addresses": ["user@example.com"],
    "subject": "Daily Analytics Report - November 28, 2025",
    "body_text": "Your daily analytics report is ready.\n\n=== Summary ===\nPage Views: 12,453\nUnique Visitors: 3,891\nAvg Session Duration: 4m 32s\nBounce Rate: 42.3%\n\nTop Pages:\n1. /dashboard - 2,341 views\n2. /products - 1,892 views\n3. /about - 987 views\n\nView the full report at: https://analytics.company.com/reports/daily/2025-11-28",
    "body_html": null,
    "headers": {
      "X-Auto-Generated": "true",
      "List-Unsubscribe": "<mailto:unsubscribe@analytics.company.com>"
    }
  },
  "metadata": {
    "source": "automated",
    "report_type": "daily_analytics"
  }
}
```

**Expected State After Execution**:
- Email appears in inbox with `is_read: false`
- Total inbox count: 3
- All 3 emails have unique message IDs

---

## Verification Checkpoints

### After Step 5 (Events Created)
```json
{
  "event_summary": {
    "total_events": 3,
    "pending_events": 3,
    "executed_events": 0,
    "failed_events": 0,
    "by_modality": {
      "email": 3
    }
  }
}
```

### After Step 7 (First Advance)
```json
{
  "email_state": {
    "inbox_count": 1,
    "unread_count": 1,
    "messages": [
      {
        "from": "calendar@company.com",
        "subject": "Reminder: Team Standup in 30 minutes",
        "is_read": false
      }
    ]
  },
  "event_summary": {
    "pending_events": 2,
    "executed_events": 1
  }
}
```

### After Step 13 (Final State)
```json
{
  "email_state": {
    "inbox_count": 3,
    "unread_count": 3,
    "messages": [
      {
        "from": "calendar@company.com",
        "subject": "Reminder: Team Standup in 30 minutes"
      },
      {
        "from": "alice.johnson@company.com",
        "subject": "Quick question about the project"
      },
      {
        "from": "noreply@analytics.company.com",
        "subject": "Daily Analytics Report - November 28, 2025"
      }
    ]
  }
}
```

### After Step 15 (Simulation Stop)
```json
{
  "stop_response": {
    "status": "stopped",
    "total_events": 3,
    "executed_events": 3,
    "failed_events": 0
  }
}
```

---

## API Calls Sequence

1. `POST /simulation/start` with `{"auto_advance": false}`
2. `POST /events` (Email #1)
3. `POST /events` (Email #2)
4. `POST /events` (Email #3)
5. `GET /events/summary`
6. `POST /simulator/time/advance` with `{"seconds": 60}`
7. `GET /email/state`
8. `POST /simulator/time/pause`
9. `POST /simulator/time/advance` with `{"seconds": 60}` → expect 409
10. `GET /simulator/time`
11. `POST /simulator/time/resume`
12. `POST /simulator/time/advance` with `{"seconds": 120}`
13. `GET /email/state`
14. `POST /email/query` with `{}`
15. `POST /simulation/stop`

---

## Test Assertions

| Step | Assertion |
|------|-----------|
| 1 | Response status 200, `is_running: true` |
| 2-4 | Response status 201, event IDs returned |
| 5 | `pending_events: 3`, `executed_events: 0` |
| 6 | Response status 200, `events_executed: 1` |
| 7 | Inbox contains 1 email from calendar@company.com |
| 9 | Response status 409 (Conflict) |
| 10 | Time unchanged from T+1:00 |
| 12 | Response status 200, `events_executed: 2` |
| 13 | Inbox contains 3 emails |
| 15 | `executed_events: 3`, `failed_events: 0` |
