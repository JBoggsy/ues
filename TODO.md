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

### Event Agent Integration
- [ ] Event Agent Configuration model (id, name, prompt_template, triggers)
- [ ] Event Agent Response model (generated_events, metadata)
- [ ] Event Agent Trigger model (event_type, conditions, frequency)

### Configuration & Persistence
- [ ] Environment Configuration schema (JSON/YAML serializable)
- [ ] Event Sequence model (ordered list of timed events)
- [ ] Simulation State model (current time, active agents, event queue)

### Validation & Testing
- [ ] Add Pydantic validators for all models
- [ ] Create example data fixtures for each modality
- [ ] Write unit tests for model serialization/deserialization
- [ ] Document model schemas with examples

## Phase 2: RESTful API (After Data Models)
- [ ] TBD - Design endpoints based on finalized models

## Phase 3: Web App UI (After API)
- [ ] TBD - Design interface based on API capabilities

## Notes
- All models should use Pydantic for validation
- Each modality should have TWO model files: `<modality>_input.py` and `<modality>_state.py`
- `ModalityInput` subclasses define event payloads (what changes)
- `ModalityState` subclasses define current state (what exists now)
- `Environment` holds all `ModalityState` instances
- `SimulatorEvent.data` references a `ModalityInput` instance
- Include comprehensive Google-style docstrings
- Timestamp fields should use simulator time, not wall-clock time
