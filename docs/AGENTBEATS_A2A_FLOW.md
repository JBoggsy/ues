# AgentBeats A2A Interaction Flow Design

This document details the A2A protocol interaction flow for the UES Green Agent submission.

---

## 1. Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AgentBeats Platform                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1. Send assessment_request
                                    │    { participants, config }
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UES Green Agent                                      │
│  • Receives assessment_request                                               │
│  • Creates A2A task                                                          │
│  • Orchestrates assessment via turn-based loop                               │
│  • Produces task updates (logs)                                              │
│  • Evaluates performance                                                     │
│  • Produces artifacts (results JSON)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 2. A2A messages + direct UES REST access
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Purple Agent (Participant)                           │
│  • Receives turn notifications via A2A                                       │
│  • Performs actions via UES REST API                                         │
│  • Signals turn completion via A2A                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Pattern**: Traced Environment — Purple Agent interacts directly with UES REST API; Green Agent observes via event history.

---

## 2. Assessment Request Format

### Incoming Message

```json
{
  "participants": {
    "personal_assistant": "http://purple-agent:8001"
  },
  "config": {
    "scenario_id": "email_triage_basic",
    "time_limit_seconds": 300,
    "max_turns": 20,
    "verbose_updates": true,
    "seed": 12345
  }
}
```

### Config Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `scenario_id` | string | Yes | — | ID of the scenario to run |
| `time_limit_seconds` | int | No | 300 | Maximum wall-clock assessment duration |
| `max_turns` | int | No | 20 | Maximum turn loop iterations |
| `verbose_updates` | bool | No | true | Stream detailed task updates |
| `seed` | int | No | — | Random seed for reproducibility |

---

## 3. API Access Control

### Summary

| Category | Access |
|----------|--------|
| Modality Queries | ✅ Full |
| User-Side Actions | ✅ Full |
| Simulator-Side Actions | ❌ None |
| Time Read | ✅ Read-only |
| Time Control | ❌ None |
| Simulation Control | ❌ None |
| Scenario Import/Export | ❌ None |
| Event History | ❌ None |
| Undo/Redo | ❌ None |
| WebSocket/Webhooks | ❌ None |
| Holds System | ❌ None |

### Allowed Endpoints

**State & Query:**
- `GET /{modality}/state` — Full current state for any modality
- `POST /{modality}/query` — Query with filters
- `GET /simulator/time` — Current simulation time (read-only)

**User-Side Actions:**

| Modality | Allowed Actions |
|----------|-----------------|
| Email | `send`, `reply`, `forward`, `move`, `archive`, `delete`, `label`, `mark_read` |
| SMS | `send`, `react`, `delete`, `mark_read` |
| Calendar | `create`, `update`, `delete`, `rsvp` |
| Chat | `send` |

### Forbidden Endpoints

- **Simulator-side actions**: `/email/receive`, `/sms/receive`, `/calendar/invite`, `/chat/receive`, `/location/*`, `/weather/*`
- **Time control**: `/simulator/time/advance`, `/simulator/time/set`, `/simulator/time/pause`, `/simulator/time/resume`
- **Simulation control**: `/simulator/reset`, `/simulator/clear`, `/simulator/start`, `/simulator/stop`
- **Scenario**: `/scenario/import/*`, `/scenario/export/*`
- **Events**: `/events`, `/events/immediate`
- **Undo/Redo**: `/simulator/undo`, `/simulator/redo`
- **Holds**: `/simulator/holds/*`
- **WebSocket/Webhooks**: `/ws`, `/webhooks/*`

### Enforcement: API Key Access Control

**Mechanism**: API key-based access control with two permission levels.

| Level | Holder | Access |
|-------|--------|--------|
| `proctor` | Green Agent | Full API access (all endpoints) |
| `user` | Purple Agent | Restricted access (allowed endpoints only) |

**Flow:**
1. On assessment start, Green Agent generates a `user`-level API key for Purple Agent
2. Key is included in `assessment_start` A2A message along with UES URL
3. All UES requests require `X-API-Key` header (or `Authorization: Bearer <token>`)
4. Middleware validates key and enforces access level
5. Each request is attributed to the originating agent for tracing
6. Keys are invalidated when assessment ends

**Benefits:**
- Enforcement at request time (no cheating possible)
- Request attribution enables detailed tracing beyond just events
- Clean key lifecycle scoped to single assessment

---

## 4. Turn-Based Interaction Loop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Green → Purple (A2A): assessment_start                                      │
│  {                                                                           │
│    ues_url: "http://ues:8000",                                              │
│    api_key: "user-level-token-...",                                         │
│    scenario: { description, goals, constraints },                           │
│    current_time: "2026-01-22T09:00:00Z",                                    │
│    initial_state_summary: { unread_emails: 5, ... }                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐
│                              TURN LOOP                                       │
│                                                                              │
│  1. Purple: Takes actions via UES REST API                                   │
│     - GET /email/state                                                       │
│     - POST /email/reply { ... }                                              │
│     - etc.                                                                   │
│                                                                              │
│  2. Purple → Green (A2A): turn_complete                                      │
│     { actions_taken: 3, notes: "..." }                                       │
│                                                                              │
│  3. Green: Advances simulation time, processes events                        │
│                                                                              │
│  4. Green → Purple (A2A): turn_start                                         │
│     {                                                                        │
│       turn_number: 2,                                                        │
│       current_time: "2026-01-22T10:00:00Z",                                  │
│       events: [                                                              │
│         { type: "email.received", summary: "New email from Alice" }          │
│       ]                                                                      │
│     }                                                                        │
│                                                                              │
│  5. Repeat until termination condition                                       │
└ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Green → Purple (A2A): assessment_complete                                   │
│  { reason: "time_limit" | "max_turns" | "scenario_complete" | ... }         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Green: Retrieves event trace, runs evaluation, produces results artifact    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### A2A Message Types

| Direction | Message Type | Content |
|-----------|--------------|---------|
| Green → Purple | `assessment_start` | UES URL, API key, scenario description, goals, initial state |
| Green → Purple | `turn_start` | Turn number, current time, events that occurred |
| Purple → Green | `turn_complete` | Optional notes, action count |
| Green → Purple | `assessment_complete` | Reason for completion |
| Purple → Green | `early_completion` | Purple signals it's done early |

### Termination Conditions

| Condition | Result |
|-----------|--------|
| Wall-clock time exceeds `time_limit_seconds` | Assessment ends |
| Turn count exceeds `max_turns` | Assessment ends |
| Simulation time reaches scenario end | Assessment ends |
| Purple sends `early_completion` | Assessment ends |
| Purple timeout (no response within turn timeout) | Assessment fails |
| Purple crash | Assessment fails |
| Invalid action from Purple | Inform Purple, continue |

---

## 5. Task Updates (Streaming Logs)

Green Agent streams task updates during assessment:

```json
{
  "type": "task_update",
  "timestamp": "2026-01-22T10:30:00Z",
  "message": "Purple Agent completed turn 3",
  "details": { "turn": 3, "actions_taken": 2 }
}
```

### Update Types

| Type | When |
|------|------|
| `assessment_started` | Assessment begins |
| `scenario_loaded` | Scenario imported |
| `turn_started` | New turn begins |
| `turn_completed` | Purple signals ready |
| `simulation_advanced` | Time progresses |
| `assessment_complete` | Assessment ends |

---

## 6. Results Artifact

```json
{
  "assessment_id": "uuid",
  "scenario_id": "email_triage_basic",
  "participant": "personal_assistant",
  "status": "completed",
  "duration_seconds": 145,
  "turns_taken": 8,
  "actions_taken": 12,
  
  "scores": {
    "overall": 85.5,
    "dimensions": {
      "accuracy": { "score": 90, "max": 100, "weight": 0.4 },
      "efficiency": { "score": 75, "max": 100, "weight": 0.2 },
      "completeness": { "score": 88, "max": 100, "weight": 0.3 },
      "safety": { "score": 100, "max": 100, "weight": 0.1 }
    }
  },
  
  "criteria_results": [
    {
      "id": "emails_processed",
      "name": "Emails Processed Correctly",
      "passed": true,
      "score": 25,
      "max_score": 25,
      "explanation": "All 5 emails were triaged correctly"
    }
  ],
  
  "action_log": [
    {
      "turn": 1,
      "timestamp": "2026-01-22T10:30:05Z",
      "action": "email.reply",
      "parameters": { "email_id": "..." },
      "success": true
    }
  ]
}
```

---

*Implementation tasks are tracked in [AGENTBEATS_SUBMISSION.md](AGENTBEATS_SUBMISSION.md).*
