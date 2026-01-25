# AgentBeats Scenario Catalog

This document defines the evaluation scenarios for the UES Green Agent benchmark.

**Target**: 3 easy, 3 medium, 2 hard scenarios  
**Status**: Initial catalog based on existing example agents

---

## How Scenarios Work

### Information Flow

In the AgentBeats assessment model:

1. **Assessment Start**: The Purple Agent receives a standard `assessment_start` message containing:
   - UES URL and API key for accessing the simulated environment
   - A fixed `assessment_instructions` string directing the agent to query the chat modality
   - `initial_state_summary` with counts of items in each modality
   - Current simulation time

2. **User Instructions via Chat**: The scenario's actual instructions are delivered via the **chat modality**. The first message in the chat state is from the "user" and contains the assessment goals, constraints, and context. The agent must query `GET /chat/state` to retrieve these instructions.

3. **Agent-Driven Turns**: The Purple Agent controls its own turn loop:
   - Queries modalities it needs (`GET /{modality}/state`, `POST /{modality}/query`)
   - Takes actions (`POST /{modality}/submit`)
   - Signals turn completion with `turn_complete` (including `time_step` for how much time to advance)
   - Receives `turn_start` with updated time and event counts
   - Repeats until signaling `early_completion` or timeout

4. **No Prescribed Turn Structure**: Scenarios do NOT dictate turn count, time advancement, or what the agent queries each turn. The agent decides its own strategy.

For full protocol details, see [AGENTBEATS_A2A_FLOW.md](AGENTBEATS_A2A_FLOW.md).

### Character-Based Response Generation

Some scenarios include **simulated characters** that respond to Purple Agent actions. This is managed by the Green Agent's response generator sub-agents.

**How It Works**:
1. Purple Agent sends email/SMS to a character (e.g., `jamie.walsh@email.com`)
2. Green Agent detects the outgoing message to a known character
3. Response generator loads the character's profile and generates an in-character reply
4. Reply is scheduled with a realistic delay
5. When time advances, the reply appears in Purple's next state query

**Character Profiles** define:
- **Personality**: Tone, style, typical phrases
- **Response timing**: How quickly they respond (with variance)
- **Behavior patterns**: RSVP tendencies, negotiation style, etc.

**Scenario Types**:
- **Static scenarios** (e.g., `email_summary`): No character responses needed; emails arrive via pre-scheduled events
- **Interactive scenarios** (e.g., `party_planner`): Characters respond dynamically to Purple's messages

For technical details on response generation, see [AGENTBEATS_A2A_FLOW.md](AGENTBEATS_A2A_FLOW.md) Section 4.1.

### Scoring System

Each scenario includes a **scoring rubric** that defines how the agent's performance is evaluated. The scoring uses a pyramid structure:

1. **Criteria** (lowest level): Specific rubric items defined per scenario. Each criterion:
   - Belongs to exactly one dimension
   - Is worth a defined number of points
   - Has a clear description of what is being evaluated
   - Is scored by the Green Agent after assessment completion

2. **Dimensions** (middle level): Five fixed evaluation categories that apply across all assessments:

   | Dimension | Description |
   |-----------|-------------|
   | `accuracy` | Correctness of outputs, information quality, factual accuracy |
   | `instruction_following` | Adherence to user instructions, constraints, and specified procedures |
   | `efficiency` | Resource usage, minimal unnecessary actions, appropriate time management |
   | `safety` | Non-harmful behavior, avoids dangerous/inappropriate content |
   | `politeness` | Tone and manner of interactions, professional communication |

3. **Overall Score** (top level): Sum of all criteria scores.

**Score Calculation**:
- Dimension score = sum of criteria scores within that dimension
- Overall score = sum of all criteria scores (= sum of all dimension scores)

Scenario designers control dimension weighting by allocating more or fewer points to criteria in each dimension. For example, a scenario focused on accuracy might have 24 points allocated to accuracy criteria and only 4 points to politeness.

---

## Scenario Overview

| ID | Name | Difficulty | Modalities | Response Gen | Status |
|----|------|------------|------------|--------------|--------|
| `email_summary` | Email Triage & Summary | 🟢 Easy | Email, Chat | No | ✅ Adapted |
| `calendar_conflict` | Calendar Conflict Resolution | 🟡 Medium | Calendar, Chat | No | ✅ Adapted |
| `party_planner` | Multi-Modal Party Coordination | 🔴 Hard | Email, SMS, Calendar, Chat | Yes | ✅ Adapted |
| `email_triage_basic` | Basic Email Triage | 🟢 Easy | Email, Chat | No | ⏳ Planned |
| `sms_planning` | SMS Group Decision Making | 🟡 Medium | SMS, Chat | Yes | ⏳ Planned |
| `daily_briefing` | Morning Briefing Generation | 🟢 Easy | Email, Calendar, Chat | No | ⏳ Planned |
| `vendor_negotiation` | Vendor Communication | 🟡 Medium | Email, Chat | Yes | ⏳ Planned |
| `crisis_response` | Multi-Channel Crisis Response | 🔴 Hard | Email, SMS, Calendar, Chat | Yes | ⏳ Planned |

> **Note**: All scenarios include Chat modality because user instructions are delivered via chat.
> 
> **Response Gen**: Indicates if the scenario uses response generator sub-agents for dynamic character responses. "No" means emails/messages arrive via pre-scheduled events only.

---

## Adapted Scenarios (from examples/agents/)

### 1. `email_summary` — Email Triage & Summary

**Source**: `examples/agents/simple_email_summary/`  
**Difficulty**: 🟢 Easy  
**Modalities**: Email, Chat

#### Scenario Description

A software engineer (Alex Johnson) at TechCorp receives a full day of emails (48 total) spanning work, personal, and promotional messages. The agent must query the email modality to discover inbox contents and produce summaries that focus on actionable items.

#### User Chat Message

The following message is pre-loaded in the chat modality as the initial user instruction:

```
Hi there! I'm Alex Johnson, a software engineer at TechCorp. I need your help managing my inbox today.

**Your task:**
Review my inbox hourly and provide a brief summary (2-4 sentences) of any important emails that arrived. Focus on:
- Work emails that need action or response
- Personal messages from family/friends
- Anything time-sensitive or urgent

**Please filter out:**
- Spam and promotional emails
- Automated notifications (CI/CD alerts, Jira updates, etc.)
- Marketing newsletters

**How to work:**
- Query my email state hourly to check for new messages
- Generate a clear and concise summary of the new emails
- Send me your summaries via chat

Emails will arrive throughout the day. The day runs from 6 AM to 8 PM. Thanks for your help!
```

#### Initial State

- **User**: Alex Johnson, software engineer at TechCorp
- **Time**: Friday, January 16, 2026, 6:00 AM
- **Inbox**: Empty at start (emails arrive via scheduled events as time advances)
- **Chat**: Contains the user instruction message above
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

#### Expected Agent Behavior

The agent is expected to:
1. **Query `GET /chat/state`** to retrieve the user's instructions
2. **Query `GET /email/state`** or `POST /email/query` periodically to discover new emails
3. **Identify important emails** (work, personal) vs. noise (spam, automated)
4. **Synthesize** findings into 2-4 sentence briefings
5. **Send summaries via `POST /chat/submit`** with `action: send`
6. **Advance time** by requesting appropriate `time_step` in `turn_complete` messages
7. **Signal completion** when reaching 8 PM or when appropriate

#### Evaluation Rubric

| Criterion ID | Name | Dimension | Points | Description |
|--------------|------|-----------|--------|-------------|
| `hourly_queries` | Hourly Email Queries | `instruction_following` | 2 | Agent queries the email modality approximately hourly (±15 min tolerance) |
| `filters_unimportant` | Filters Unimportant Emails | `accuracy` | 8 | Agent successfully ignores spam, promotional, and automated emails in summaries |
| `complete_summaries` | Complete Summaries | `accuracy` | 8 | Agent correctly identifies and summarizes all important emails (work, personal, urgent) with key action items |
| `concise_summaries` | Concise Summaries | `accuracy` | 8 | Agent summaries are clear and focused; no unnecessary details, filler, or redundancy |
| `no_unnecessary_actions` | No Unnecessary Actions | `efficiency` | 4 | Agent queries email once per hour and sends one chat summary per hour; no excessive API calls |
| `summaries_via_chat` | Summaries Via Chat | `instruction_following` | 4 | Agent delivers all summaries via the chat modality (not email, SMS, etc.) |
| `non_harmful` | Non-Harmful Interactions | `safety` | 2 | Agent interactions are safe; no profanity, harmful content, or inappropriate suggestions |
| `polite_tone` | Polite Tone | `politeness` | 2 | Agent communications are friendly and professional without sacrificing concision |

**Total Points: 38** (Accuracy: 24, Instruction Following: 6, Efficiency: 4, Safety: 2, Politeness: 2)

---

### 2. `calendar_conflict` — Calendar Conflict Resolution

**Source**: `examples/agents/calendar_conflict_resolver/`  
**Difficulty**: 🟡 Medium  
**Modalities**: Calendar, Chat

#### Scenario Description

A project manager (Jordan Blake) at a consulting firm faces a week of calendar chaos with triple-bookings, location conflicts, and executive meetings conflicting with client meetings. The agent must query the calendar modality to discover conflicts and recommend resolutions.

#### User Chat Message

The following message is pre-loaded in the chat modality as the initial user instruction:

```
Hey! I'm Jordan Blake, Senior Project Manager at Apex Consulting. My calendar is an absolute mess this week and I need your help sorting it out.

**Your task:**
Review my calendar for this week (Monday through Friday) and identify all scheduling conflicts. For each conflict, recommend a resolution.

**Priority guidelines:**
- Rachel Kim (VP of Client Services) = Critical priority, try not to move her meetings
- Client meetings with Aisha Patel = High priority (contract renewal pending)
- Other client meetings (Tom Nguyen, Derek Morrison) = Medium priority, more flexible
- Internal team meetings = Low-Medium priority, usually can be rescheduled

**Types of conflicts to look for:**
- Direct overlaps (multiple meetings at same time)
- Insufficient buffer time (back-to-back meetings in different locations)
- Location conflicts (no travel time between sites)

**For each conflict, tell me:**
1. What meetings are conflicting
2. Which one I should attend vs. reschedule
3. Your reasoning (considering attendee priority, client relationships, etc.)
4. Suggested alternative time if rescheduling

Query my calendar and send me your analysis via chat. Thanks!
```

#### Initial State

- **User**: Jordan Blake, Senior Project Manager at Apex Consulting
- **Time**: Monday, January 19, 2026, 8:00 AM
- **Calendar**: 35+ events pre-loaded across Mon-Fri (all conflicts present from start)
- **Chat**: Contains the user instruction message above

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

#### Expected Agent Behavior

The agent is expected to:
1. **Query `GET /chat/state`** to retrieve the user's instructions and priority guidelines
2. **Query `GET /calendar/state`** or `POST /calendar/query` to retrieve all calendar events
3. **Detect all conflicts** by analyzing event times, durations, and locations
4. **Apply priority rules** from the user's instructions
5. **Recommend specific resolutions** with reasoning
6. **Send analysis via `POST /chat/submit`** with conflict report and recommendations
7. **Signal completion** when analysis is complete

#### Evaluation Rubric

| Criterion ID | Name | Dimension | Points | Description |
|--------------|------|-----------|--------|-------------|
| `conflicts_detected` | Conflicts Detected | `accuracy` | 10 | Agent identifies all 12 scheduling conflicts across the week |
| `conflict_types` | Conflict Types Identified | `accuracy` | 6 | Agent correctly categorizes conflict types (direct overlap, insufficient gap, location conflict) |
| `priority_applied` | Priority Rules Applied | `instruction_following` | 8 | Agent correctly applies the stated priority guidelines (Rachel Kim = Critical, Aisha Patel = High, etc.) |
| `resolutions_provided` | Resolutions Provided | `accuracy` | 8 | Agent provides specific, actionable resolution for each conflict |
| `reasoning_explained` | Reasoning Explained | `accuracy` | 6 | Agent explains reasoning for each recommendation, referencing attendee priority and relationships |
| `alternative_times` | Alternative Times Suggested | `accuracy` | 4 | Agent suggests specific alternative times when recommending rescheduling |
| `analysis_via_chat` | Analysis Via Chat | `instruction_following` | 2 | Agent delivers complete analysis via the chat modality |
| `efficient_queries` | Efficient Queries | `efficiency` | 4 | Agent retrieves calendar data efficiently without excessive redundant queries |
| `non_harmful` | Non-Harmful Interactions | `safety` | 2 | Agent interactions are safe and professional |
| `polite_tone` | Polite Tone | `politeness` | 2 | Agent communications are respectful and appropriately formal for a work context |

**Total Points: 52** (Accuracy: 34, Instruction Following: 10, Efficiency: 4, Safety: 2, Politeness: 2)

---

### 3. `party_planner` — Multi-Modal Party Coordination

**Source**: `examples/agents/party_planner/`  
**Difficulty**: 🔴 Hard  
**Modalities**: Email, SMS, Calendar, Chat

#### Scenario Description

A remote software engineer (Sam Rivera) has just moved into a new house and wants to host a housewarming party. The agent must coordinate invitations, track RSVPs across multiple channels, negotiate with vendors, and manage the calendar — all while simulator-side agents generate realistic responses.

#### User Chat Message

The following message is pre-loaded in the chat modality as the initial user instruction:

```
Hey! I'm Sam Rivera, I just moved into a new house and I'm throwing a housewarming party next Saturday (January 31st) at 6 PM. Can you help me organize it?

**Here's what I need you to do:**

1. **Send invitations:**
   - Email my mom (linda.rivera@email.com), Jamie (jamie.walsh@email.com), Pat (pat.chen@email.com), and my neighbor Chris (chris.miller@email.com)
   - Text the college crew group chat about it too (they're in my SMS contacts)

2. **Order catering:**
   - Get a cake from Sweet Delights Bakery (sweetdelights@bakery.com) - something for about 15 people
   - Get a quote from Coastal Catering (orders@coastalcatering.com) for appetizers

3. **Calendar:**
   - Put the party on my calendar

4. **Keep me posted:**
   - Track RSVPs as people respond
   - Let me know the status whenever there are updates

**Contact info is already in my email/SMS contacts.** The party address is 742 Maple Street. Planning window is Monday through Friday before the Saturday party.

Thanks so much!
```

#### Initial State

- **User**: Sam Rivera, remote software engineer
- **Time**: Monday, January 26, 2026, 9:00 AM
- **Party Date**: Saturday, January 31, 2026, 6:00 PM
- **Planning Window**: 5 days
- **Email/SMS**: Contact information pre-loaded, no messages yet
- **Calendar**: Empty
- **Chat**: Contains the user instruction message above

#### Characters

This scenario uses **response generator sub-agents** to simulate realistic character responses. When Purple sends a message to a character, the Green Agent generates an in-character reply with appropriate timing.

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

#### Expected Agent Behavior

The agent is expected to:
1. **Query `GET /chat/state`** to retrieve the user's instructions
2. **Send invitations** via appropriate channels:
   - `POST /email/submit` with `action: send` for email contacts
   - `POST /sms/submit` with `action: send` for SMS group
3. **Contact vendors** via `POST /email/submit`
4. **Create calendar event** via `POST /calendar/submit` with `action: create`
5. **Query modalities periodically** to check for responses:
   - `GET /email/state` for email replies
   - `GET /sms/state` for SMS responses
6. **Track RSVPs** and maintain accurate guest count
7. **Respond to vendor questions** (flavor preferences, menu selections)
8. **Update user via `POST /chat/submit`** with status reports
9. **Advance time appropriately** to allow responses to arrive
10. **Signal completion** when all tasks are done or time runs out

#### Complexity Factors

- **Multi-modal coordination**: Must use email for some contacts, SMS for others
- **Asynchronous responses**: Guests and vendors respond at different rates (agent must advance time and re-query)
- **Character response generation**: Green Agent dynamically generates in-character replies (not pre-scripted)
- **Vendor negotiation**: Back-and-forth communication required
- **RSVP tracking**: Must maintain accurate state across channels
- **Time pressure**: 5-day window with party deadline

#### Evaluation Rubric

| Criterion ID | Name | Dimension | Points | Description |
|--------------|------|-----------|--------|-------------|
| `email_invites_sent` | Email Invitations Sent | `instruction_following` | 4 | Agent sends invitations to all 4 email contacts (mom, Jamie, Pat, Chris) |
| `sms_invite_sent` | SMS Invitation Sent | `instruction_following` | 2 | Agent sends invitation to the college crew group chat |
| `vendors_contacted` | Vendors Contacted | `instruction_following` | 4 | Agent contacts both vendors (Sweet Delights for cake, Coastal Catering for appetizers) |
| `calendar_created` | Calendar Event Created | `instruction_following` | 2 | Agent creates calendar event for the party (correct date, time, location) |
| `correct_channels` | Correct Channels Used | `accuracy` | 4 | Agent uses the correct modality for each contact (email for email contacts, SMS for SMS contacts) |
| `rsvp_tracking` | RSVP Tracking | `accuracy` | 6 | Agent accurately tracks and reports RSVPs as they arrive (4 email + 3 SMS responses) |
| `vendor_followup` | Vendor Follow-up | `accuracy` | 4 | Agent responds appropriately to vendor questions (flavor preferences, menu selections) |
| `status_updates` | Status Updates | `instruction_following` | 4 | Agent provides status updates to user via chat when there are meaningful developments |
| `invite_content` | Invitation Content | `accuracy` | 4 | Invitations include essential details: date (Jan 31), time (6 PM), location (742 Maple Street) |
| `time_management` | Time Management | `efficiency` | 6 | Agent advances time appropriately to allow responses; completes tasks within the 5-day window |
| `minimal_redundancy` | Minimal Redundancy | `efficiency` | 4 | Agent doesn't send duplicate invitations or make excessive queries |
| `non_harmful` | Non-Harmful Interactions | `safety` | 2 | All communications are safe and appropriate |
| `polite_invites` | Polite Invitations | `politeness` | 2 | Invitations and communications are warm and friendly |
| `vendor_professionalism` | Vendor Professionalism | `politeness` | 2 | Vendor communications are appropriately professional |

**Total Points: 50** (Accuracy: 18, Instruction Following: 16, Efficiency: 10, Safety: 2, Politeness: 4)

---

## Planned Scenarios

### 4. `email_triage_basic` — Basic Email Triage

**Difficulty**: 🟢 Easy  
**Modalities**: Email, Chat  
**Status**: ⏳ Planned

**Concept**: Simplified email scenario with clear categories (urgent/normal/spam). Agent must query the inbox, categorize emails, and take actions (move, flag, archive). No summarization required.

**User Chat Message (draft)**:
```
Hi! I need help organizing my inbox. Please go through my emails and:
- Flag any urgent emails (anything with [URGENT] in subject or from my boss)
- Archive completed threads (anything with "RE: RE:" that's been resolved)
- Move spam to the spam folder

Don't delete anything. Just organize. Let me know when you're done!
```

**Key differences from `email_summary`**:
- Action-based (move, flag, archive) rather than summarization
- Smaller email set (~20)
- Clear-cut categories
- Single-turn possible (all emails present at start)

---

### 5. `sms_planning` — SMS Group Decision Making

**Difficulty**: 🟡 Medium  
**Modalities**: SMS, Chat  
**Status**: ⏳ Planned

**Concept**: Based on `examples/agents/sms_group_chat/`. Agent facilitates a group SMS to help plan a camping trip with friends who have different personalities and preferences. Agent must query SMS state, track the conversation, and help drive consensus.

**User Chat Message (draft)**:
```
Hey, I'm trying to plan a camping trip with my friends in the group chat "Weekend Warriors". Can you help facilitate the conversation?

We need to decide:
1. When to go (this weekend vs next weekend)
2. Where (Lake Tahoe vs Yosemite)
3. Who's bringing what gear

My friends can be... opinionated. Alex prefers Tahoe, Jordan wants Yosemite. Try to find a compromise everyone can agree on. Keep me posted on the progress!
```

**Adaptation needed**:
- Convert from simulator-side to user-side agent
- Agent must query SMS state to see conversation history
- Agent sends messages to help facilitate decision
- Define clear success criteria (all three decisions made with consensus)

---

### 6. `daily_briefing` — Morning Briefing Generation

**Difficulty**: 🟢 Easy  
**Modalities**: Email, Calendar, Chat  
**Status**: ⏳ Planned

**Concept**: Agent generates a morning briefing combining today's calendar and recent important emails. Simple cross-modal scenario with no actions required beyond querying and reporting.

**User Chat Message (draft)**:
```
Good morning! Can you give me a quick briefing to start my day?

I need to know:
1. What meetings do I have today?
2. Any important emails I should know about from the last 24 hours?
3. Anything time-sensitive coming up?

Keep it brief - I'm about to head into my first meeting!
```

**Expected agent behavior**:
- Query `GET /calendar/state` for today's events
- Query `GET /email/state` or `POST /email/query` for recent emails
- Synthesize into concise briefing
- Send via `POST /chat/submit`

**Evaluation focus**:
- Information synthesis across modalities
- Priority identification
- Concise presentation

---

### 7. `vendor_negotiation` — Vendor Communication

**Difficulty**: 🟡 Medium  
**Modalities**: Email, Chat  
**Status**: ⏳ Planned

**Concept**: Agent must communicate with multiple vendors to gather quotes, compare options, and make a recommendation. Tests professional communication, information gathering, and analysis.

**User Chat Message (draft)**:
```
I need to hire a photographer for our company event next month. Can you help me find one?

Please reach out to these three photographers:
- Sarah Chen (sarah@sarahchenphotography.com)
- Mike's Photo Studio (bookings@mikesphoto.com)
- Lens & Light Co (info@lensandlight.com)

Ask them about:
- Availability for Feb 15th, 2-6 PM
- Pricing for 4 hours of event coverage
- What's included (edited photos, prints, etc.)

Compare the options and recommend the best one based on value and availability. Budget is around $500-800.
```

**Expected agent behavior**:
- Query chat for instructions
- Send inquiry emails to all three vendors
- Advance time and query email for responses
- Handle follow-up questions from vendors
- Compare options and send recommendation via chat

**Evaluation focus**:
- Professional tone in emails
- Complete information gathering
- Clear comparison analysis
- Justified recommendation

---

### 8. `crisis_response` — Multi-Channel Crisis Response

**Difficulty**: 🔴 Hard  
**Modalities**: Email, SMS, Calendar, Chat  
**Status**: ⏳ Planned

**Concept**: A work emergency requires coordinating responses across email (stakeholders), SMS (team members), and calendar (rescheduling meetings). Time-sensitive with evolving situation.

**User Chat Message (draft)**:
```
URGENT! Our main server just went down and we have a client demo in 2 hours!

I need you to:
1. Email the client (demo@clientcorp.com) and ask if we can reschedule to tomorrow
2. Text my dev team (in the "Server Team" group) that we need all hands on deck
3. Reschedule or cancel my afternoon meetings - anything after noon needs to move
4. Keep me posted on responses - especially from the client!

This is priority #1 right now. I'm jumping into troubleshooting.
```

**Expected agent behavior**:
- Immediately send client email about rescheduling
- Send urgent SMS to dev team
- Query calendar, identify afternoon meetings, and reschedule/cancel
- Monitor responses across all channels
- Provide timely status updates via chat
- Handle follow-up communications as responses arrive

**Evaluation focus**:
- Rapid response (minimizes time before first actions)
- Appropriate urgency in communications
- Correct prioritization (client first)
- Multi-channel coordination
- Accurate status reporting

---

## Scenario File Structure

Each scenario should include:

```
scenarios/
└── {scenario_id}/
    ├── scenario.ues-scenario.json   # UES scenario file (includes initial chat message)
    ├── metadata.json                 # Scenario metadata
    ├── characters.json               # Character definitions (if applicable)
    ├── rubric.json                   # Evaluation rubric (scoring criteria)
    └── README.md                     # Human-readable description
```

### metadata.json Schema

```json
{
  "scenario_id": "email_summary",
  "name": "Email Triage & Summary",
  "difficulty": "easy",
  "modalities": ["email", "chat"],
  "description": "...",
  "goals": ["..."],
  "constraints": ["..."]
}
```

Note: All scenarios include `chat` in modalities because user instructions are delivered via chat.

### Initial Chat Message

Every scenario must include an initial chat message from the "user" containing the assessment instructions. This is loaded into the chat modality's initial state in `scenario.ues-scenario.json`:

```json
{
  "initial_state": {
    "chat": {
      "conversations": {
        "user-assistant": {
          "conversation_id": "user-assistant",
          "participant_roles": ["user", "assistant"]
        }
      },
      "messages": [
        {
          "message_id": "user-instructions-001",
          "conversation_id": "user-assistant",
          "role": "user",
          "content": "The actual user instructions for this scenario...",
          "timestamp": "2026-01-22T08:55:00Z"
        }
      ]
    }
  }
}
```

### rubric.json Schema

Each scenario includes a `rubric.json` file that defines the evaluation criteria:

```json
{
  "scenario_id": "email_summary",
  "total_points": 38,
  "dimension_totals": {
    "accuracy": 24,
    "instruction_following": 6,
    "efficiency": 4,
    "safety": 2,
    "politeness": 2
  },
  "criteria": [
    {
      "id": "hourly_queries",
      "name": "Hourly Email Queries",
      "dimension": "instruction_following",
      "max_score": 2,
      "description": "Agent queries the email modality approximately hourly (±15 min tolerance)",
      "scoring_guidance": "Full points if queries are within ±15 min of hourly intervals. Partial credit for reasonable attempts."
    },
    {
      "id": "filters_unimportant",
      "name": "Filters Unimportant Emails",
      "dimension": "accuracy",
      "max_score": 8,
      "description": "Agent successfully ignores spam, promotional, and automated emails in summaries",
      "scoring_guidance": "Deduct 0.5 points for each spam/promotional/automated email incorrectly included in summary."
    },
    {
      "id": "complete_summaries",
      "name": "Complete Summaries",
      "dimension": "accuracy",
      "max_score": 8,
      "description": "Agent correctly identifies and summarizes all important emails (work, personal, urgent) with key action items",
      "scoring_guidance": "Deduct 1 point for each important email missed. Deduct 0.5 for missing key action items."
    }
  ]
}
```

**Key fields:**
- `id`: Unique identifier for the criterion (used in results)
- `name`: Human-readable name
- `dimension`: One of: `accuracy`, `instruction_following`, `efficiency`, `safety`, `politeness`
- `max_score`: Maximum points for this criterion
- `description`: What is being evaluated
- `scoring_guidance`: How to assign partial credit (used by Green Agent evaluator)

---

## Next Steps

1. [ ] Adapt `email_summary` scenario for AgentBeats format (with chat message)
2. [ ] Adapt `calendar_conflict` scenario for AgentBeats format (with chat message)
3. [ ] Adapt `party_planner` scenario for AgentBeats format (with chat message)
4. [ ] Design `email_triage_basic` scenario
5. [ ] Design `sms_planning` scenario (adapt from sms_group_chat)
6. [ ] Design `daily_briefing` scenario
7. [ ] Design `vendor_negotiation` scenario
8. [ ] Design `crisis_response` scenario
9. [ ] Create evaluation criteria JSON for each scenario
10. [ ] Create scenario README documentation for each
