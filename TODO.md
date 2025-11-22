# UES Development TODO

## Phase 1: Data Models (Foundation)

### Core Infrastructure
- [x] Create `models/` package structure
- [x] Define base `ModalityState` model (base class for current state: EmailState, CalendarState, etc.)
  - Each subclass tracks the current state of that modality (e.g., inbox contents, calendar entries)
  - Events apply `ModalityInput` instances to modify these states
  - Queried by AI agents via API
- [x] Define base `ModalityInput` model (base class for all event payloads: EmailInput, SMSInput, etc.)
  - Each subclass defines the structure of data that events carry
  - Used in `SimulatorEvent.data` field
  - Includes modality-specific validation logic
- [x] Define base `SimulatorEvent` model (scheduled_time, modality, data: ModalityInput, status, agent_id)
- [x] Define `EventQueue` model (ordered events, next_event_time, get_due_events)
- [x] Define `SimulatorTime` model (current_time, time_scale, is_paused, last_wall_time_update, auto_advance)
  - See `docs/SIMULATOR_TIME.md` for detailed time management design
- [x] Define `Environment` model (collection of all ModalityState instances + time state)
  - See `docs/ENVIRONMENT.md` for detailed design decisions
- [x] Define `SimulationEngine` class (coordinates time control, event execution, state access, API gateway)
  - See `docs/SIMULATION_ENGINE.md` for hybrid architecture design
- [x] Define `SimulationLoop` class (threading component for auto-advance mode)
  - See `docs/SIMULATION_ENGINE.md` for separation rationale

### Priority 1 Modalities (Simple, Foundational)
- [x] User Location: `LocationInput` (new location data) + `LocationState` (current location)
- [x] Current Time: `TimeInput` (timezone changes) + `TimeState` (timezone, format preferences)
- [x] Weather Data: `WeatherInput` (new weather data) + `WeatherState` (current conditions, forecast)

### Priority 2 Modalities (Message-Based)
- [x] Chat: `ChatInput` (new user/assistant message) + `ChatState` (conversation history, turn state)
- [x] Email: `EmailInput` (new email) + `EmailState` (inbox, sent, drafts, threads)
  - EmailInput fields: from, to, cc, bcc, subject, body, attachments, thread_id
- [x] Calendar: `CalendarInput` (new/modified event) + `CalendarState` (all events, recurrences)
  - CalendarInput fields: title, start/end time, location, attendees, recurrence
- [x] SMS/RCS: `SMSInput` (new text message) + `SMSState` (all conversations, read status)
  - SMSInput fields: from, to, body, media, group_id
  - See `docs/modalities/SMS.md` for comprehensive design
  - Depends on: Contacts modality (for display names, blocking)

### Priority 3 Modalities (Complex Integrations)
- [ ] Contacts: `ContactInput` (add/update/delete contact) + `ContactState` (contact database)
  - ContactInput fields: phone, email, name, birthday, address, photo, notes, blocked status
  - Used by: SMS (display names, blocking), Email (contact lookup), Calendar (attendee info)
  - Core functionality: CRUD operations, search, grouping, favorites, blocked list
- [ ] File System: `FileSystemInput` (file changes) + `FileSystemState` (directory tree, file contents)
  - FileSystemInput fields: path, content, operation (create/modify/delete), permissions
- [ ] Discord: `DiscordInput` (new message/reaction) + `DiscordState` (servers, channels, message history)
- [ ] Slack: `SlackInput` (new message/reaction) + `SlackState` (workspaces, channels, threads)
- [ ] Social Media: `SocialMediaInput` (new post/interaction) + `SocialMediaState` (feeds, posts, follows)
  - SocialMediaInput fields: platform, content, interaction_type (post/comment/like/follow)
- [ ] Screen: `ScreenInput` (UI interaction) + `ScreenState` (current app, window, UI elements)
  - ScreenInput fields: app, window, interaction_type, target_element

### Validation & Testing
- [ ] Add Pydantic validators for all models
  - [x] Core Infrastructure
    - [x] `SimulatorEvent` - Has comprehensive validation methods (validate(), can_execute())
    - [x] `EventQueue` - Has validation logic in add_event() and add_events()
    - [x] `SimulatorTime` - Has field_validator for timezone awareness
    - [x] `Environment` - Has model_validator for modality consistency
    - [x] `SimulationEngine` - Has validation logic in start() method
    - [x] `ModalityInput` (base) - Abstract methods enforce validation contract
    - [x] `ModalityState` (base) - Abstract validate_state() method
  - [x] Priority 1 Modalities
    - [x] `LocationInput` - Has field_validators for lat/lon/accuracy/speed/bearing ranges
    - [x] `LocationState` - No field validators needed (simple state container)
    - [x] `TimeInput` - Has field_validators for timezone and date_format
    - [x] `TimeState` - No field validators needed (inherits validated fields)
    - [x] `WeatherInput` - Has field_validators for latitude/longitude ranges
    - [x] `WeatherState` - No field validators needed (stores validated reports)
  - [x] Priority 2 Modalities
    - [x] `ChatInput` - Has field_validator for content structure (text vs multimodal)
    - [x] `ChatState` - No field validators needed (uses validated ChatInput data)
    - [x] `EmailInput` - Has field_validators for email addresses and operation-specific validation
    - [x] `EmailState` - No field validators needed (stores validated Email objects)
    - [x] `CalendarInput` - Has field_validators for emails, dates, recurrence rules
    - [x] `CalendarState` - No field validators needed (stores validated CalendarEvent objects)
    - [x] `SMSInput` - Has field_validators for phone numbers and action-specific validation
    - [x] `SMSState` - No field validators needed (stores validated message data)
  - [ ] Priority 3 Modalities (Not Yet Implemented)
    - [ ] Contacts (ContactInput, ContactState)
    - [ ] File System (FileSystemInput, FileSystemState)
    - [ ] Discord (DiscordInput, DiscordState)
    - [ ] Slack (SlackInput, SlackState)
    - [ ] Social Media (SocialMediaInput, SocialMediaState)
    - [ ] Screen (ScreenInput, ScreenState)
- [ ] Create example data fixtures for each modality
  - [x] Core infrastructure fixtures (events, times, queues, environments)
  - [x] Priority 1 modality fixtures (location, time, weather)
  - [x] Priority 2 modality fixtures (chat, email, calendar, sms)
  - [x] Simulation scenario fixtures (morning_routine, busy_workday, travel_day)
  - [ ] Priority 3 modality fixtures (when implemented)
- [ ] Write unit tests for modalities (input/state classes)
  - [x] Priority 1 Modalities
    - [x] Location (35 input tests, 34 state tests) - includes serialization/deserialization
    - [x] Time (39 input tests, 39 state tests) - includes serialization/deserialization
    - [x] Weather (input and state tests)
  - [x] Priority 2 Modalities
    - [x] Chat (46 input tests, 47 state tests) - includes serialization/deserialization
    - [x] Email (input and state tests)
    - [x] Calendar (52 input tests, 42 state tests) - includes serialization/deserialization
    - [x] SMS (input and state tests)
  - [ ] Priority 3 Modalities (when implemented)
    - [ ] Contacts (input and state tests)
    - [ ] File System (input and state tests)
    - [ ] Discord (input and state tests)
    - [ ] Slack (input and state tests)
    - [ ] Social Media (input and state tests)
    - [ ] Screen (input and state tests)
- [ ] Write unit tests for core infrastructure
  - [x] SimulatorEvent
  - [x] EventQueue
  - [x] SimulatorTime
  - [x] Environment
  - [x] SimulationEngine
- [ ] Document model schemas with examples

## Phase 2: RESTful API (After Data Models)
- [ ] TBD - Design endpoints based on finalized models

## Phase 3: Web App UI (After API)
- [ ] TBD - Design interface based on API capabilities

## Phase 4: Event Agent Integration
- [ ] Event Agent Configuration model (id, name, prompt_template, triggers)
- [ ] Event Agent Response model (generated_events, metadata)
- [ ] Event Agent Trigger model (event_type, conditions, frequency)

## Notes
- All models should use Pydantic for validation
- Each modality should have TWO model files: `<modality>_input.py` and `<modality>_state.py`
- `ModalityInput` subclasses define event payloads (what changes)
- `ModalityState` subclasses define current state (what exists now)
- `Environment` holds all `ModalityState` instances
- `SimulatorEvent.data` references a `ModalityInput` instance
- Include comprehensive Google-style docstrings
- Timestamp fields should use simulator time, not wall-clock time
