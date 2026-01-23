# AgentBeats Scenario Catalog

This document defines the evaluation scenarios for the UES Green Agent benchmark.

**Target**: 3 easy, 3 medium, 2 hard scenarios  
**Status**: Initial catalog based on existing example agents

---

## Scenario Overview

| ID | Name | Difficulty | Modalities | Agent Type | Status |
|----|------|------------|------------|------------|--------|
| `email_summary` | Email Triage & Summary | 🟢 Easy | Email | User-side | ✅ Adapted |
| `calendar_conflict` | Calendar Conflict Resolution | 🟡 Medium | Calendar | User-side | ✅ Adapted |
| `party_planner` | Multi-Modal Party Coordination | 🔴 Hard | Email, SMS, Calendar | User-side | ✅ Adapted |
| `email_triage_basic` | Basic Email Triage | 🟢 Easy | Email | User-side | ⏳ Planned |
| `sms_planning` | SMS Group Decision Making | 🟡 Medium | SMS | User-side | ⏳ Planned |
| `daily_briefing` | Morning Briefing Generation | 🟢 Easy | Email, Calendar | User-side | ⏳ Planned |
| `vendor_negotiation` | Vendor Communication | 🟡 Medium | Email | User-side | ⏳ Planned |
| `crisis_response` | Multi-Channel Crisis Response | 🔴 Hard | Email, SMS, Calendar | User-side | ⏳ Planned |

---

## Adapted Scenarios (from examples/agents/)

### 1. `email_summary` — Email Triage & Summary

**Source**: `examples/agents/simple_email_summary/`  
**Difficulty**: 🟢 Easy  
**Modalities**: Email only

#### Scenario Description

A software engineer (Alex Johnson) at TechCorp receives a full day of emails (48 total) spanning work, personal, and promotional messages. The agent must process emails hourly and produce summaries that focus on actionable items.

#### Initial State

- **User**: Alex Johnson, software engineer at TechCorp
- **Time**: Friday, January 16, 2026, 6:00 AM
- **Inbox**: Empty (all emails arrive via scheduled events)
- **Duration**: 14 hours (6 AM → 8 PM)

#### Email Distribution

| Hour | Count | Types |
|------|-------|-------|
| 6-7 AM | 2 | Spam (dev tools, fitness) |
| 7-8 AM | 2 | Spam, Automated (CI/CD) |
| 8-9 AM | 6 | Work (Q1 planning, URGENT incident + replies), Automated (standup) |
| 9-10 AM | 4 | Spam, Work (post-mortem, agenda), Personal (mom) |
| 10-11 AM | 4 | Work (timeline), Automated (Jira, LinkedIn), Spam |
| 11 AM-12 PM | 3 | Personal (reunion), Work (code review), Spam |
| 12-1 PM | 3 | Spam (food/webinar promos) |
| 1-2 PM | 4 | Automated (survey, reminder), Work (PR question), Spam |
| 2-3 PM | 2 | Work (meeting notes), HR (benefits) |
| 3-4 PM | 4 | Spam (webinar), Work (security notice, PR thanks), Personal (dentist) |
| 4-5 PM | 4 | Automated (GitHub, Jira digest), Work (Q1 confirmation), Spam |
| 5-6 PM | 3 | Work (thanks), Personal (dinner plans), Spam |
| 6-7 PM | 3 | Personal (package delivery), Spam |
| 7-8 PM | 4 | Automated (weekly summary), Spam |

**Email types breakdown:**
- Spam/promotional: 18
- Work emails: 13
- Incident thread: 3
- Automated/System: 9
- Personal: 5

#### Agent Task

The agent is presented with the current hour's emails and must:
1. **Identify important emails** (work, personal)
2. **Filter out noise** (spam, promotional, automated notifications)
3. **Synthesize** into a 2-4 sentence briefing
4. **Highlight urgent items** (time-sensitive, needs action)

#### Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Accuracy** | 40% | Correctly identifies important vs. unimportant emails |
| **Completeness** | 30% | Covers all actionable items without omissions |
| **Noise Filtering** | 20% | Successfully ignores spam/promotional/automated |
| **Urgency Detection** | 10% | Correctly identifies and highlights urgent items |

#### Turn Structure

- **Turns**: 14 (one per hour, 6 AM → 8 PM)
- **Per turn**: Agent receives hour's emails, produces summary
- **Time advancement**: 1 hour per turn

---

### 2. `calendar_conflict` — Calendar Conflict Resolution

**Source**: `examples/agents/calendar_conflict_resolver/`  
**Difficulty**: 🟡 Medium  
**Modalities**: Calendar only

#### Scenario Description

A project manager (Jordan Blake) at a consulting firm faces a week of calendar chaos with triple-bookings, location conflicts, and executive meetings conflicting with client meetings. The agent must analyze conflicts and recommend resolutions.

#### Initial State

- **User**: Jordan Blake, Senior Project Manager at Apex Consulting
- **Time**: Monday, January 19, 2026, 8:00 AM
- **Calendar**: 35+ events pre-loaded across Mon-Fri
- **Duration**: 5 business days

#### Characters & Priority Levels

| Character | Role | Priority |
|-----------|------|----------|
| Rachel Kim | VP of Client Services | 🔴 Critical |
| Tom Nguyen | Client A Lead | 🟡 Medium (flexible) |
| Aisha Patel | Client B Lead | 🔴 High (contract renewal) |
| Derek Morrison | Client C Lead | 🟡 Medium (new engagement) |
| Dev Team | Internal engineers | 🟢 Low-Medium |

#### Conflicts by Day

| Day | Conflicts | Key Issues |
|-----|-----------|------------|
| Monday | 3 | 9 AM triple-booking (standup, client sync, VP 1:1); 2 PM double-booking (VP strategy, client B, retro) |
| Tuesday | 2 | Back-to-back with 0 gap at different locations; lunch meeting conflicts with dentist |
| Wednesday | 4 | 2-4 PM nightmare: all-hands, Client B escalation, Client A call, Client C review all overlap |
| Thursday | 2 | Two client presentations scheduled simultaneously; no travel time between sites |
| Friday | 1 | Week review conflicts with team celebration |

#### Conflict Types

1. **Direct Overlaps**: Multiple meetings at exact same time
2. **Insufficient Gaps**: Back-to-back with no buffer
3. **Location Conflicts**: Different locations without travel time
4. **Priority Conflicts**: VP meetings vs. client meetings
5. **Recurring vs. One-time**: Standing meetings vs. important one-offs

#### Agent Task

For each day, the agent must:
1. **Detect all conflicts** in the calendar
2. **Analyze priority factors** (attendee seniority, client importance, recurrence)
3. **Recommend specific resolutions** (which to attend, which to reschedule, alternative times)
4. **Explain reasoning** for each recommendation

#### Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Conflict Detection** | 25% | Identifies all conflicts correctly |
| **Priority Analysis** | 25% | Correctly weighs meeting importance |
| **Resolution Quality** | 30% | Recommendations are actionable and realistic |
| **Business Judgment** | 20% | Considers relationships, politics, consequences |

#### Turn Structure

- **Turns**: 5 (one per day)
- **Per turn**: Agent receives day's calendar, produces conflict analysis and recommendations
- **Time advancement**: 1 day per turn

---

### 3. `party_planner` — Multi-Modal Party Coordination

**Source**: `examples/agents/party_planner/`  
**Difficulty**: 🔴 Hard  
**Modalities**: Email, SMS, Calendar

#### Scenario Description

A remote software engineer (Sam Rivera) has just moved into a new house and wants to host a housewarming party. The agent must coordinate invitations, track RSVPs across multiple channels, negotiate with vendors, and manage the calendar — all while simulator-side agents generate realistic responses.

#### Initial State

- **User**: Sam Rivera, remote software engineer
- **Time**: Monday, January 26, 2026, 9:00 AM
- **Party Date**: Saturday, January 31, 2026, 6:00 PM
- **Planning Window**: 5 days
- **Initial channels**: Empty email/SMS, empty calendar

#### User Instructions

> "Hey, I'm having a housewarming party next Saturday (January 31st) at 6 PM. Can you help me:
> 1. Send invitations to my mom, Jamie, Pat, and my neighbor Chris
> 2. Text the college crew group about it too  
> 3. Order a cake from Sweet Delights Bakery - something for about 15 people
> 4. Get a quote from Coastal Catering for appetizers
> 5. Put it on my calendar
> 6. Keep me updated on RSVPs"

#### Characters

**Guests:**

| Character | Contact | Response Pattern | RSVP Behavior |
|-----------|---------|------------------|---------------|
| Linda Rivera (Mom) | Email | 1 hour, enthusiastic | Immediate YES, offers food |
| Jamie Walsh | Email | 2 hours, casual | Quick YES, offers help |
| Pat Chen | Email | 4-6 hours, busy | Tentative YES, may be late |
| Chris Miller (Neighbor) | Email | 1 day, polite | Decline (out of town) |
| College Crew | Group SMS | Chaotic, mixed | Marcus: YES, Aisha: YES, Derek: MAYBE |

**Vendors:**

| Vendor | Contact | Response Pattern | Behavior |
|--------|---------|------------------|----------|
| Sweet Delights Bakery | Email | Same-day | Asks flavor/dietary, provides quote |
| Coastal Catering | Email | 4 hours | Sends menu options, provides itemized quote |

#### Agent Task

The agent must:
1. **Send appropriate invitations** via correct channels (email vs. SMS)
2. **Track RSVPs** as responses arrive (maintaining accurate count)
3. **Communicate with vendors** (provide requirements, request quotes)
4. **Create calendar event** with accurate details
5. **Provide status updates** on request

#### Complexity Factors

- **Multi-modal coordination**: Must use email for some contacts, SMS for others
- **Asynchronous responses**: Guests respond at different rates
- **Vendor negotiation**: Back-and-forth communication required
- **RSVP tracking**: Must maintain accurate state across channels
- **Time pressure**: 5-day window with party deadline

#### Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| **Task Completion** | 30% | All requested tasks attempted |
| **Channel Accuracy** | 15% | Uses correct contact method for each person |
| **RSVP Tracking** | 20% | Maintains accurate guest count |
| **Vendor Communication** | 15% | Professional, provides necessary details |
| **Calendar Accuracy** | 10% | Event created with correct details |
| **Status Updates** | 10% | Provides accurate progress reports |

#### Turn Structure

- **Turns**: ~20 (variable, based on response timing)
- **Per turn**: Agent takes actions, waits for responses
- **Time advancement**: Variable (1-4 hours per turn)
- **Termination**: All tasks complete OR time runs out

---

## Planned Scenarios

### 4. `email_triage_basic` — Basic Email Triage

**Difficulty**: 🟢 Easy  
**Modalities**: Email only  
**Status**: ⏳ Planned

**Concept**: Simplified email scenario with clear categories (urgent/normal/spam). Agent must move emails to appropriate folders and flag urgent items. No summarization required.

**Key differences from `email_summary`**:
- Action-based (move, flag, archive) rather than summarization
- Smaller email set (~20)
- Clear-cut categories
- No time progression

---

### 5. `sms_planning` — SMS Group Decision Making

**Difficulty**: 🟡 Medium  
**Modalities**: SMS only  
**Status**: ⏳ Planned

**Concept**: Based on `examples/agents/sms_group_chat/`. Agent participates in a group SMS to help plan a camping trip with friends who have different personalities and preferences.

**Adaptation needed**:
- Convert from simulator-side to user-side agent
- Add evaluation criteria for decision facilitation
- Define clear objectives (finalize date, location, responsibilities)

---

### 6. `daily_briefing` — Morning Briefing Generation

**Difficulty**: 🟢 Easy  
**Modalities**: Email, Calendar  
**Status**: ⏳ Planned

**Concept**: Agent generates a morning briefing combining today's calendar and recent important emails. Simple cross-modal scenario with no actions required.

**Evaluation focus**:
- Information synthesis
- Priority identification
- Concise presentation

---

### 7. `vendor_negotiation` — Vendor Communication

**Difficulty**: 🟡 Medium  
**Modalities**: Email only  
**Status**: ⏳ Planned

**Concept**: Agent must negotiate with multiple vendors (price comparison, requirement clarification, terms negotiation). Tests professional communication and decision-making.

**Evaluation focus**:
- Professional tone
- Information gathering
- Comparison analysis
- Recommendation justification

---

### 8. `crisis_response` — Multi-Channel Crisis Response

**Difficulty**: 🔴 Hard  
**Modalities**: Email, SMS, Calendar  
**Status**: ⏳ Planned

**Concept**: A work emergency requires coordinating responses across email (stakeholders), SMS (team members), and calendar (rescheduling meetings). Time-sensitive with evolving situation.

**Evaluation focus**:
- Rapid response
- Stakeholder communication
- Priority management under pressure
- Multi-channel coordination

---

## Scenario File Structure

Each scenario should include:

```
scenarios/
└── {scenario_id}/
    ├── scenario.ues-scenario.json   # UES scenario file
    ├── metadata.json                 # Scenario metadata
    ├── characters.json               # Character definitions (if applicable)
    ├── evaluation_criteria.json      # Scoring criteria
    └── README.md                     # Human-readable description
```

### metadata.json Schema

```json
{
  "scenario_id": "email_summary",
  "name": "Email Triage & Summary",
  "difficulty": "easy",
  "modalities": ["email"],
  "duration_estimate_minutes": 15,
  "max_turns": 20,
  "description": "...",
  "goals": ["..."],
  "constraints": ["..."]
}
```

### evaluation_criteria.json Schema

```json
{
  "dimensions": {
    "accuracy": { "weight": 0.4, "description": "..." },
    "completeness": { "weight": 0.3, "description": "..." }
  },
  "criteria": [
    {
      "id": "urgent_emails_identified",
      "name": "Urgent Emails Identified",
      "dimension": "accuracy",
      "type": "count",
      "target": 3,
      "scoring": "linear"
    }
  ]
}
```

---

## Next Steps

1. [ ] Adapt `email_summary` scenario for AgentBeats format
2. [ ] Adapt `calendar_conflict` scenario for AgentBeats format
3. [ ] Adapt `party_planner` scenario for AgentBeats format
4. [ ] Design `email_triage_basic` scenario
5. [ ] Design `sms_planning` scenario (adapt from sms_group_chat)
6. [ ] Design `daily_briefing` scenario
7. [ ] Design `vendor_negotiation` scenario
8. [ ] Design `crisis_response` scenario
9. [ ] Create evaluation criteria JSON for each scenario
10. [ ] Create scenario README documentation for each
