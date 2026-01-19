# Party Planner Integration Test

This example demonstrates a comprehensive **dual-agent** scenario where a user-side AI assistant
is tested against simulator-side agents that simulate friends, family, and vendors. This creates
a realistic end-to-end test of an AI assistant's coordination capabilities.

## Overview

The scenario tests an AI personal assistant's ability to help coordinate a house party by:
- Sending invitations via email and SMS
- Tracking RSVPs across multiple channels
- Coordinating with vendors (bakery, catering)
- Managing the calendar
- Providing status updates

The **user-side agent** (AI assistant being tested) must coordinate across modalities while
**simulator-side agents** create realistic responses from guests and vendors.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        UES (Simulation Engine)                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     SIMULATOR-SIDE AGENTS                            │   │
│  │                                                                      │   │
│  │   Guest Agent                          Vendor Agent                  │   │
│  │   ├── Mom (Linda)                      ├── Sweet Delights Bakery    │   │
│  │   ├── Best Friend (Jamie)              └── Coastal Catering         │   │
│  │   ├── Work Friend (Pat)                                              │   │
│  │   ├── Neighbor (Chris)                                               │   │
│  │   └── College Crew (Group SMS)                                       │   │
│  │                                                                      │   │
│  │   Monitors: email.receive, sms.receive                               │   │
│  │   Generates: email.send, sms.send (replies)                          │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              ▲           │                                  │
│                              │           ▼                                  │
│              ┌───────────────┴───────────┴───────────────┐                 │
│              │           REST API / WebSocket            │                 │
│              └───────────────┬───────────────────────────┘                 │
│                              │           ▲                                  │
│                              ▼           │                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      USER-SIDE AGENT                                 │   │
│  │                   (AI Assistant Under Test)                          │   │
│  │                                                                      │   │
│  │   Receives: Natural language instructions from "user"                │   │
│  │   Actions: Send emails, SMS, create calendar events                  │   │
│  │   Tracks: RSVPs, vendor confirmations, outstanding tasks             │   │
│  │   Reports: Status updates to user                                    │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- **UES server** running at `http://localhost:8000` (or specify with `--ues-host`)
- **Ollama** running at `http://localhost:11434` (or specify with `--ollama-host`)
- A model pulled in Ollama (default: `gemma3:12b`)

## Running the Example

This example requires running **three processes**:

```bash
# Terminal 1: Start the UES server
uv run uvicorn main:app --reload

# Terminal 2: Start the simulator-side agents (guests + vendors)
uv run python examples/agents/party_planner/simulator_agents.py

# Terminal 3: Run the user-side agent (AI assistant test)
uv run python examples/agents/party_planner/user_agent.py
```

Or run the orchestrated test suite:

```bash
# Runs everything and produces a test report
uv run python examples/agents/party_planner/run_test.py
```

## The Scenario (`scenario.ues-scenario.json`)

### Setup

- **User**: Sam Rivera, a remote software engineer who just moved into a new house
- **Party Date**: Saturday, January 31, 2026, starting at 6:00 PM
- **Simulator Start**: Monday, January 26, 2026, 9:00 AM (5 days before party)
- **Goal**: Successfully coordinate a housewarming party with 10-15 guests

### Initial State

**Contacts** (pre-populated):
- Family: Mom (Linda Rivera), Dad (Carlos Rivera)
- Friends: Jamie Walsh, Pat Chen, Chris Miller (neighbor)
- College Crew: Marcus, Aisha, Derek (group SMS thread exists)
- Vendors: Sweet Delights Bakery, Coastal Catering

**Calendar**: Empty (party not yet scheduled)

**Email/SMS**: Clean slate

### User Instructions to AI Assistant

The test begins with the user giving the AI assistant this instruction:

> "Hey, I'm having a housewarming party next Saturday (January 31st) at 6 PM. Can you help me:
> 1. Send invitations to my mom, Jamie, Pat, and my neighbor Chris
> 2. Text the college crew group about it too  
> 3. Order a cake from Sweet Delights Bakery - something for about 15 people
> 4. Get a quote from Coastal Catering for appetizers
> 5. Put it on my calendar
> 6. Keep me updated on RSVPs"

## The Characters (`characters.json`)

### Guests - Friends & Family

| Character | Contact Method | Response Pattern | RSVP Behavior |
|-----------|---------------|------------------|---------------|
| **Linda Rivera (Mom)** | Email | Responds within 1 hour, enthusiastic, asks many questions | Immediate YES, offers to bring food |
| **Jamie Walsh** | Email | Responds within 2 hours, casual and excited | Quick YES, offers to help setup |
| **Pat Chen** | Email | Responds within 4-6 hours, checks calendar | Tentative YES, may be late (kids) |
| **Chris Miller (Neighbor)** | Email | Responds within 1 day, polite | Polite decline - out of town |
| **College Crew** | Group SMS | Chaotic group thread, mixed responses over 24 hours | Marcus: YES, Aisha: YES, Derek: MAYBE |

### Vendors

| Vendor | Contact Method | Response Pattern | Behavior |
|--------|---------------|------------------|----------|
| **Sweet Delights Bakery** | Email | Same-day response, professional | Asks about flavor preferences, dietary restrictions, provides quote |
| **Coastal Catering** | Email | Responds within 4 hours, detailed | Sends menu options, asks about head count, provides itemized quote |

### Character Details

#### Linda Rivera (Mom) 👩‍👦

**Personality**: Warm, excited, slightly overbearing, wants to help with everything

**Response Style**:
- Always replies to Sam as "mijo/mija" or "honey"
- Asks follow-up questions (What should I bring? What time should I arrive? Who else is coming?)
- Mentions she'll tell Dad
- Offers her famous dish before being asked

**Example Response**:
```
Subject: Re: You're Invited - Housewarming Party!

Mijo!!! 🎉

OF COURSE we'll be there! Dad and I are so excited to see the new place!
I'm already planning to bring my famous enchiladas - enough for everyone!

A few questions:
- What time should we arrive? I can come early to help set up
- Do you need me to bring anything else? Plates? Decorations?
- Is Jamie coming? I haven't seen her in ages!

So proud of you and your new home!

Love,
Mom 💕

P.S. - I'm telling Tía Rosa, she'll want to send something
```

#### Jamie Walsh (Best Friend) 🎉

**Personality**: Enthusiastic, casual, always supportive, action-oriented

**Response Style**:
- Casual tone, lots of exclamation points
- Immediately offers to help
- Suggests additions to the party

**Example Response**:
```
Subject: Re: You're Invited - Housewarming Party!

YESSS!!! Finally get to see the new place! 🏠🎊

Count me in - I can come over around 4 to help you set up if you want?

Should I bring anything? I make a mean sangria 🍷

Can't wait!!
- J
```

#### Pat Chen (Work Friend) 👨‍👩‍👧

**Personality**: Friendly but busy, always juggling family logistics

**Response Style**:
- Apologetic about response time
- Checks with spouse before fully committing
- Mentions kid logistics

**Example Response**:
```
Subject: Re: You're Invited - Housewarming Party!

Hey Sam!

So sorry for the late reply - crazy day with the kids.

We'd love to come! Let me double check with Maya about babysitter
availability, but I think we're good. We might need to leave a bit early
(bedtime routine 🙄) but we'll definitely be there for a few hours.

Congrats on the new place! Can't wait to see it.

-Pat
```

#### Chris Miller (Neighbor) 🏠

**Personality**: Polite, friendly, but keeps appropriate neighbor boundaries

**Response Style**:
- Formal-ish, appreciative of being invited
- Apologetic decline with genuine reason

**Example Response**:
```
Subject: Re: You're Invited - Housewarming Party!

Hi Sam,

Thank you so much for the invitation! It's so nice of you to include us.

Unfortunately, we'll be out of town that weekend visiting my parents in 
Portland. We're really sorry to miss it!

I hope the party goes great. Let us know if you ever need anything - 
that's what neighbors are for!

Best,
Chris & Dana
```

#### College Crew (Group SMS) 📱

**Marcus**: Always down for a party, responds with enthusiasm  
**Aisha**: Checks her schedule, usually confirms, asks about plus-ones  
**Derek**: Perpetual "maybe", mentions other potential conflicts, usually shows up

**Example Thread**:
```
Sam: "Hey everyone! Housewarming party at my new place Jan 31st @ 6pm. You in?"

[10 min later]
Marcus: "YOOO finally!! Count me in 🙌"

[25 min later]  
Aisha: "Let me check... yeah I should be free! Can I bring Tyler?"

[3 hours later]
Derek: "Oh nice! I might have a thing but I'll try to make it work"

[5 min later]
Marcus: "derek's "thing" = his couch 😂"

[2 min later]
Derek: "😤"
```

#### Sweet Delights Bakery 🎂

**Business Personality**: Professional, helpful, asks good qualifying questions

**Response Flow**:
1. Acknowledges order request, asks clarifying questions
2. Provides options and pricing
3. Confirms order with details

**Example Initial Response**:
```
Subject: Re: Cake Order Inquiry - January 31st

Dear Sam,

Thank you for reaching out to Sweet Delights Bakery!

We'd be happy to help with your housewarming celebration. For a party of 
approximately 15 people, I'd recommend our 10" round cake, which serves 
14-18 guests.

A few questions to help us prepare the perfect cake:
- Flavor preference? (Our most popular: Chocolate, Vanilla, Red Velvet, Carrot)
- Any dietary restrictions we should know about? (We offer gluten-free options)
- Would you like a custom message on the cake?
- Pickup or delivery? (Delivery is $15 within 10 miles)

Our standard 10" decorated cake starts at $65. Custom designs available 
upon request.

Please let us know your preferences and we'll send a confirmation!

Best regards,
Sweet Delights Bakery
555-CAKE
```

#### Coastal Catering 🍽️

**Business Personality**: Professional, detailed, provides comprehensive quotes

**Response Flow**:
1. Thanks for inquiry, asks about head count and preferences
2. Sends detailed menu options with pricing
3. Follows up if no response

**Example Quote Response**:
```
Subject: Re: Appetizer Quote - Housewarming Party

Hi Sam,

Thank you for considering Coastal Catering for your housewarming party!

Based on 15 guests with a 3-hour event, here are our recommended packages:

OPTION A - "The Crowd Pleaser" - $180
- Bruschetta trio (tomato, mushroom, olive tapenade)
- Spinach artichoke dip with crostini
- Caprese skewers
- Meatballs (Swedish or BBQ)
- Veggie crudité platter

OPTION B - "Elevated Bites" - $250
- Everything in Option A, plus:
- Bacon-wrapped dates
- Shrimp cocktail
- Assorted cheese board with crackers

Both options include:
✓ All serving platters and utensils
✓ Setup and cleanup
✓ Delivery within 15 miles

Please confirm your head count and preferred option by January 29th 
for guaranteed availability.

Questions? Reply here or call 555-CATER.

Best,
The Coastal Catering Team
```

## The Agents

### User-Side Agent (`user_agent.py`)

The AI assistant being tested. It receives the user's natural language instructions and must:

1. **Parse the request** into discrete tasks
2. **Execute tasks** via UES API:
   - Send personalized email invitations
   - Send group SMS to college crew
   - Email vendors with appropriate requests
   - Create calendar event
3. **Monitor for responses** (polling or WebSocket)
4. **Track state**:
   - Who has been invited
   - Who has responded (YES/NO/MAYBE)
   - Vendor status (quoted/ordered/confirmed)
5. **Report to user** periodically on progress
6. **Handle follow-ups**:
   - Answer vendor questions
   - Send reminders to non-responders

### Simulator-Side Agents (`simulator_agents.py`)

Two agents running simultaneously:

**Guest Response Agent**:
- Monitors for party-related emails and SMS
- Identifies which character received the message
- Generates in-character response with appropriate delay
- Maintains consistency (can't RSVP differently twice)

**Vendor Response Agent**:
- Monitors for business inquiry emails
- Generates professional responses
- Tracks conversation state (inquiry → quote → order → confirm)
- Asks appropriate follow-up questions

## Test Objectives & Scoring

The test evaluates the AI assistant on:

| Category | Criteria | Points |
|----------|----------|--------|
| **Invitation Completeness** | All specified guests receive invitations | 20 |
| **Channel Appropriateness** | Email vs SMS used correctly per instructions | 10 |
| **Personalization** | Invitations aren't generic copy-paste | 10 |
| **Calendar Accuracy** | Event created with correct date, time, title | 10 |
| **RSVP Tracking** | Correctly identifies who said YES/NO/MAYBE | 15 |
| **Vendor Communication** | Appropriate inquiries sent, questions answered | 15 |
| **Follow-up Handling** | Responds to vendor questions appropriately | 10 |
| **Status Reporting** | Provides accurate updates to user | 10 |

**Scoring**:
- 90-100: Excellent - Assistant handles complex coordination flawlessly
- 70-89: Good - Minor gaps but core functionality works
- 50-69: Needs Improvement - Significant issues with tracking or communication
- Below 50: Failing - Major functionality broken

## Expected Timeline

| Sim Time | Event |
|----------|-------|
| Mon 9:00 AM | User gives instructions to AI assistant |
| Mon 9:05 AM | AI sends invitations (email + SMS) |
| Mon 9:10 AM | AI emails bakery and catering |
| Mon 9:15 AM | AI creates calendar event |
| Mon 10:00 AM | Mom responds (YES + questions) |
| Mon 10:30 AM | College crew starts responding |
| Mon 11:00 AM | Jamie responds (YES) |
| Mon 1:00 PM | Bakery responds (questions) |
| Mon 1:30 PM | Catering responds (quote) |
| Mon 3:00 PM | Pat responds (tentative YES) |
| Mon 4:00 PM | AI should answer bakery questions |
| Tue 9:00 AM | Chris responds (decline) |
| Tue 10:00 AM | AI should provide status update |
| Wed 9:00 AM | AI should send reminder to non-responders |
| Thu 9:00 AM | AI should finalize vendor orders |
| Fri 5:00 PM | Final status report |

## Key Patterns Demonstrated

1. **Dual-Agent Architecture**: User-side and simulator-side agents interacting through UES
2. **Multi-Modal Coordination**: Tracking invitations across email and SMS
3. **Vendor Negotiation Flow**: Multi-turn business communication
4. **RSVP State Management**: Tracking responses and non-responses
5. **Proactive Follow-ups**: Reminders, status updates, vendor confirmations
6. **Test Evaluation**: Objective scoring of AI assistant capabilities

## Extending This Example

- **Weather Integration**: Check forecast and warn guests if outdoor party
- **Location Sharing**: Send address via SMS with map link
- **Gift Registry**: Track gifts mentioned in responses
- **Dietary Tracking**: Aggregate dietary restrictions from responses
- **Budget Management**: Track spending against a party budget
- **Photo Sharing**: Post-party follow-up with thanks and photos

## File Structure

```
party_planner/
├── user_agent.py               # AI assistant under test
├── simulator_agents.py         # Guest + vendor response agents
├── run_test.py                 # Orchestrated test runner with scoring
├── README.md                   # This documentation
├── system_prompts/
│   ├── assistant.txt           # Prompt for AI assistant
│   ├── guest.txt               # Prompt template for guests
│   └── vendor.txt              # Prompt template for vendors
├── characters.json             # Character definitions
├── vendors.json                # Vendor definitions
├── scenario.ues-scenario.json  # Initial state setup
└── test_criteria.json          # Scoring rubric
```
