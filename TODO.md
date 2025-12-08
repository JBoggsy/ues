# UES Development TODO

## Test Suite Summary

**Total Tests: 2,135 (2,133 passing, 2 skipped)**

| Category | Test Count | Location |
|----------|------------|----------|
| Core Infrastructure Models | 392 | `tests/models/` (includes 61 undo + 22 simulation undo tests) |
| Priority 1 Modality Models | 234 | `tests/models/` |
| Priority 2 Modality Models | 549 | `tests/models/` (includes 192 modality undo tests) |
| API Integration Tests | 523 | `tests/api/{events,time,environment,simulation,modalities}/` (includes 40 undo/redo + 20 reset tests) |
| API Unit Tests | 285 | `tests/api/unit/` |
| API Workflow Tests | 47 | `tests/api/workflows/` |
| Cross-Cutting Tests | 105 | `tests/api/cross_cutting/` |

Run all tests: `uv run pytest`

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

### Modality State Summaries
- [ ] Override `summary` property for each `ModalityState` subclass (used by `/environment/state`)
  - [ ] `LocationState.summary` - e.g., "At 123 Main St, New York" or "Location not set"
  - [ ] `TimeState.summary` - e.g., "UTC, 12h format"
  - [ ] `WeatherState.summary` - e.g., "Weather data for 3 locations"
  - [ ] `ChatState.summary` - e.g., "15 messages in 2 conversations"
  - [ ] `EmailState.summary` - e.g., "3 unread, 12 total emails"
  - [ ] `CalendarState.summary` - e.g., "2 events today, 5 this week"
  - [ ] `SMSState.summary` - e.g., "4 conversations, 2 unread"

### Priority 3 Modalities (Complex Integrations)
- [ ] **Contacts**: `ContactInput` (add/update/delete contact) + `ContactState` (contact database)
  - ContactInput fields: phone, email, name, birthday, address, photo, notes, blocked status
  - Used by: SMS (display names, blocking), Email (contact lookup), Calendar (attendee info)
  - Core functionality: CRUD operations, search, grouping, favorites, blocked list
  - REST API Routes (when implemented):
    - `GET /contacts/state` - Get all contacts
    - `POST /contacts/query` - Query contacts with filters
    - `POST /contacts/create` - Create a new contact
    - `POST /contacts/update` - Update existing contact
    - `POST /contacts/delete` - Delete contact(s)
    - `POST /contacts/block` - Block contact(s)
    - `POST /contacts/unblock` - Unblock contact(s)
- [ ] **File System**: `FileSystemInput` (file changes) + `FileSystemState` (directory tree, file contents)
  - FileSystemInput fields: path, content, operation (create/modify/delete), permissions
  - REST API Routes (when implemented):
    - `GET /filesystem/state` - Get file system state
    - `POST /filesystem/query` - Query files/directories
    - `POST /filesystem/create` - Create file/directory
    - `POST /filesystem/update` - Modify file content
    - `POST /filesystem/delete` - Delete file/directory
    - `POST /filesystem/move` - Move/rename file/directory
    - `POST /filesystem/copy` - Copy file/directory
- [ ] **Discord**: `DiscordInput` (new message/reaction) + `DiscordState` (servers, channels, message history)
  - REST API Routes (when implemented):
    - `GET /discord/state` - Get Discord state (all servers/channels)
    - `POST /discord/query` - Query messages with filters
    - `POST /discord/send` - Send a message
    - `POST /discord/react` - Add reaction to message
    - `POST /discord/delete` - Delete message
- [ ] **Slack**: `SlackInput` (new message/reaction) + `SlackState` (workspaces, channels, threads)
  - REST API Routes (when implemented):
    - `GET /slack/state` - Get Slack state (all workspaces/channels)
    - `POST /slack/query` - Query messages with filters
    - `POST /slack/send` - Send a message
    - `POST /slack/react` - Add reaction to message
    - `POST /slack/delete` - Delete message
    - `POST /slack/thread` - Reply in thread
- [ ] **Social Media**: `SocialMediaInput` (new post/interaction) + `SocialMediaState` (feeds, posts, follows)
  - SocialMediaInput fields: platform, content, interaction_type (post/comment/like/follow)
  - REST API Routes (when implemented):
    - `GET /social/state` - Get social media state
    - `POST /social/query` - Query posts/interactions
    - `POST /social/post` - Create a new post
    - `POST /social/comment` - Comment on post
    - `POST /social/like` - Like/unlike post
    - `POST /social/follow` - Follow/unfollow user
    - `POST /social/share` - Share/repost content
- [ ] **Screen**: `ScreenInput` (UI interaction) + `ScreenState` (current app, window, UI elements)
  - ScreenInput fields: app, window, interaction_type, target_element
  - REST API Routes (when implemented):
    - `GET /screen/state` - Get current screen state
    - `POST /screen/query` - Query screen history
    - `POST /screen/interact` - Simulate UI interaction
    - `POST /screen/switch` - Switch app/window
    - `POST /screen/capture` - Capture screenshot

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
- [x] Write unit tests for modalities (input/state classes) - 591 tests for implemented modalities
  - [x] Priority 1 Modalities (234 tests total)
    - [x] Location (74 tests) - includes serialization/deserialization
    - [x] Time (83 tests) - includes serialization/deserialization
    - [x] Weather (77 tests) - includes serialization/deserialization
  - [x] Priority 2 Modalities (357 tests total)
    - [x] Chat (114 tests) - includes serialization/deserialization
    - [x] Email (56 tests) - includes serialization/deserialization
    - [x] Calendar (94 tests) - includes serialization/deserialization
    - [x] SMS (93 tests) - includes serialization/deserialization
  - [ ] Priority 3 Modalities (when implemented)
    - [ ] Contacts (input and state tests)
    - [ ] File System (input and state tests)
    - [ ] Discord (input and state tests)
    - [ ] Slack (input and state tests)
    - [ ] Social Media (input and state tests)
    - [ ] Screen (input and state tests)
- [x] Write unit tests for core infrastructure (331 tests total)
  - [x] SimulatorEvent
  - [x] EventQueue
  - [x] SimulatorTime
  - [x] Environment
  - [x] SimulationEngine (includes 22 undo/redo tests)
  - [x] UndoEntry and UndoStack (61 tests)
- [x] Document model schemas with examples
  - [x] Core infrastructure (SimulatorEvent, EventQueue, SimulatorTime, Environment, SimulationEngine)
  - [x] Base classes (ModalityInput, ModalityState)
  - [x] Priority 1 modalities (Location, Time, Weather)
  - [x] Priority 2 modalities (Email, Chat, Calendar, SMS)
  - [ ]Priority 3 modalities (will be documented when implemented)

## Phase 2: RESTful API (After Data Models)

### API Design & Documentation
- [x] Design complete REST API specification
  - [x] Time control endpoints (`/simulator/time`)
  - [x] Environment state endpoints (`/environment`)
  - [x] Event management endpoints (`/events`)
  - [x] Simulation control endpoints (`/simulation`)
  - [x] Modality-specific query endpoints
  - [x] Agent convenience endpoints (`/modalities/{modality}/submit`, `/events/immediate`)
- [x] Document all endpoints
  - [x] Request/response formats
  - [x] Query parameters
  - [x] Error handling
  - [x] HTTP status codes
  - [x] Usage examples

### FastAPI Implementation
- [x] Set up FastAPI application structure
  - [x] Create `api/` package
  - [ ] Configure CORS, middleware
  - [x] Exception handlers
  - [x] Set up dependency injection for SimulationEngine
  - [x] Configure automatic OpenAPI documentation
- [x] Implement Time Control Routes (`api/routes/time.py`)
  - [x] `GET /simulator/time` - Get current time state
  - [x] `POST /simulator/time/advance` - Advance by duration
  - [x] `POST /simulator/time/set` - Jump to specific time
  - [x] `POST /simulator/time/skip-to-next` - Event-driven skip
  - [x] `POST /simulator/time/pause` - Pause simulation
  - [x] `POST /simulator/time/resume` - Resume simulation
  - [x] `POST /simulator/time/set-scale` - Change time scale
- [x] Implement Environment Routes (`api/routes/environment.py`)
  - [x] `GET /environment/state` - Complete state snapshot
  - [x] `GET /environment/modalities` - List modalities
  - [x] `GET /environment/modalities/{modality}` - Get modality state
  - [x] `POST /environment/modalities/{modality}/query` - Query with filters
  - [x] `POST /environment/validate` - Validate consistency
- [x] Implement Event Routes (`api/routes/events.py`)
  - [x] `GET /events` - List events with filters
  - [x] `POST /events` - Create scheduled event
  - [x] `POST /events/immediate` - Create immediate event (convenience)
  - [x] `GET /events/{event_id}` - Get event details
  - [x] `DELETE /events/{event_id}` - Cancel event
  - [x] `GET /events/next` - Peek at next event
  - [x] `GET /events/summary` - Get statistics
- [x] Implement Simulation Routes (`api/routes/simulation.py`)
  - [x] `POST /simulation/start` - Start simulation
  - [x] `POST /simulation/stop` - Stop simulation
  - [x] `GET /simulation/status` - Get status and metrics
  - [x] `POST /simulation/reset` - Reset to initial state
- [x] Implement Modality Convenience Routes (`api/routes/modalities.py`)
  - [x] `POST /modalities/chat/submit` - Submit chat message
  - [x] `POST /modalities/email/submit` - Submit email action
  - [x] `POST /modalities/calendar/submit` - Submit calendar action
  - [x] `POST /modalities/sms/submit` - Submit SMS action
  - [x] `POST /modalities/location/submit` - Submit location update
  - [x] `POST /modalities/time/submit` - Submit time preference update (via generic handler)
  - [x] `POST /modalities/weather/submit` - Submit weather update (basic implementation in `api/routes/weather.py`)
  - [x] Generic handler for future modalities (`POST /modalities/{modality}/submit`)

### Query Implementation
- [x] Implement modality-specific query handlers
  - [x] Email query handler (folder, sender, subject search, date range)
  - [x] Calendar query handler (date range, recurrence expansion, attendees)
  - [x] SMS query handler (conversation, participant, message search)
  - [x] Weather query handler (location, units, time range, real API integration)
  - [x] Location query handler (history, named locations, time range)
  - [x] Time query handler (preference history, timezone changes)
  - [x] Chat query handler (conversation, role, content search)

### Request/Response Models
- [x] Create Pydantic request models for all endpoints
  - [x] Time control request models (AdvanceTimeRequest, SetTimeRequest, SetScaleRequest)
  - [x] Event creation request models (CreateEventRequest, ImmediateEventRequest)
  - [x] Query parameter models for each modality (via dict[str, Any] with documented schemas)
  - [x] Simulation control request models (StartSimulationRequest)
- [x] Create Pydantic response models for all endpoints
  - [x] Standardized error response model (via exception handlers in api/exceptions.py)
  - [x] Event summary response model (EventResponse, EventListResponse, EventSummaryResponse)
  - [x] State snapshot response models (EnvironmentStateResponse, ModalitySummary, ModalityListResponse)
  - [x] Execution summary response models (StartSimulationResponse, StopSimulationResponse, SimulationStatusResponse, ResetSimulationResponse)
  - [x] Time-specific response models (TimeStateResponse, SetTimeResponse, SkipToNextResponse)
  - [x] Weather-specific response models (CurrentWeatherResponse, UpdateWeatherRequest)
  - [x] Modality submission response models (ModalitySubmitResponse)
  - [x] Environment validation response models (ValidationResponse)

### Testing (907 tests passing)
- [x] Write API integration tests (520 tests)
  - [x] Test all time control endpoints (50 tests in `tests/api/time/`)
  - [x] Test all event management endpoints (63 tests in `tests/api/events/`)
  - [x] Test all environment query endpoints (34 tests in `tests/api/environment/`)
  - [x] Test all simulation control endpoints (75 tests in `tests/api/simulation/`)
  - [x] Test modality convenience endpoints (248 tests in `tests/api/modalities/`)
  - [x] Test error handling and validation (49 tests in `tests/api/cross_cutting/`)
  - [x] Test concurrent API requests (23 tests in `tests/api/cross_cutting/`)
  - [x] Test state consistency (33 tests in `tests/api/cross_cutting/`)
- [x] Write modality route integration tests (248 tests in `tests/api/modalities/`)
  - [x] Email routes: test all 11 action endpoints + state/query (62 tests)
  - [x] SMS routes: test all 6 action endpoints + state/query (46 tests)
  - [x] Chat routes: test all 3 action endpoints + state/query (33 tests)
  - [x] Calendar routes: test create/update/delete + state/query (38 tests)
  - [x] Location routes: test update + state/query (39 tests)
  - [x] Weather routes: test update + state/query (30 tests)
  - [x] Test state retrieval consistency
  - [x] Test query endpoints with various filters
  - [x] Test error handling (invalid data, missing modality, etc.)
  - [x] Verify OpenAPI schema generation
- [x] Write API unit tests (285 tests in `tests/api/unit/`)
  - [x] Test request validation (129 tests)
  - [x] Test response serialization (55 tests)
  - [x] Test dependency injection (30 tests)
  - [x] Test error response formatting (71 tests)
- [x] Write workflow integration tests (47 tests in `tests/api/workflows/`)
  - [x] Scenario 1: Basic manual time control (12 tests)
  - [x] Scenario 2: Multi-modality morning simulation (17 tests)
  - [x] Scenario 3: Interactive agent conversation (18 tests)
  - See `tests/progress/API_TESTING_PROGRESS.md` for detailed test coverage

### Simulation Clear, Undo/Redo & Reset Functionality

#### Clear Functionality ✅
- [x] Implement `clear` functionality for `/simulation/clear`
  - **Desired behavior**: Completely empty the simulation environment
  - Destroys all events (removes from queue entirely)
  - Resets all modality states to empty defaults
  - Optionally resets time (only if user specifies a time to reset to)
  - Use case: Start completely fresh without any prior state
  - Implementation:
    - [x] Add abstract `clear()` method to `ModalityState` base class
    - [x] Implement `clear()` for each modality state (Location, Time, Weather, Chat, Email, Calendar, SMS)
    - [x] Add `clear_all_states()` method to `Environment`
    - [x] Add `clear(reset_time_to: Optional[datetime])` method to `SimulationEngine`
    - [x] Add `POST /simulation/clear` API endpoint
  - Tests: 13 tests in `tests/api/simulation/test_simulation_clear.py`

#### Undo/Redo Functionality
- [x] Implement undo data capture for each modality state ✅ (192 tests)
  - **Design**: Each modality captures minimal undo data before input is applied
  - Space-efficient: Additive ops store just IDs, destructive ops store full objects
  - See `docs/MODALITY_UNDO_NOTES.md` for implementation patterns and lessons learned
  - Implementation:
    - [x] Add `create_undo_data(input_data: ModalityInput) -> dict` to `ModalityState` base class
    - [x] Add `apply_undo(undo_data: dict) -> None` to `ModalityState` base class
    - [x] Implement undo methods for each modality state:
      - [x] Weather (20 tests) - add/update location with history capacity handling
      - [x] Chat (29 tests) - send/delete/clear with conversation side effects
      - [x] Calendar (29 tests) - CRUD + recurring event scope variations
      - [x] Location (19 tests) - update with history capacity handling
      - [x] Time (17 tests) - update with preference history
      - [x] Email (40 tests) - 19 operation types, bulk operations, thread restoration
      - [x] SMS (38 tests) - 13 action types, group/participant management
- [x] Implement simulation-level undo/redo orchestration ✅ (22 tests)
  - [x] Create `UndoEntry` model (event_id, modality, undo_data, executed_at) ✅ (12 tests)
  - [x] Create `UndoStack` model (undo_stack, redo_stack, max_size) ✅ (49 tests)
  - [x] Modify `SimulatorEvent.execute()` to capture and return undo data ✅
  - [x] Add `undo_stack: UndoStack` field to `SimulationEngine` ✅
  - [x] Add `undo(count: int = 1)` method to `SimulationEngine` ✅
  - [x] Add `redo(count: int = 1)` method to `SimulationEngine` ✅
  - [x] Add `POST /simulation/undo` API endpoint ✅ (20 tests)
  - [x] Add `POST /simulation/redo` API endpoint ✅ (20 tests)

#### Reset Functionality ✅
- [x] Implement robust `reset` functionality for `/simulation/reset`
  - **Behavior**: Roll back ALL executed events in reverse order (complete undo)
  - Events remain in queue but reset to PENDING status
  - Time is NOT automatically reset (user can set time separately if desired)
  - Uses undo stack infrastructure to reverse all event applications
  - Implementation:
    - [x] Modify `SimulationEngine.reset()` to use undo stack ✅
    - [x] Update `POST /simulation/reset` endpoint (remove 501 response) ✅
  - Tests: 20 tests in `tests/api/simulation/test_simulation_reset.py`

### Documentation & Examples
- [x] Set up automatic OpenAPI/Swagger documentation
- [ ] Create API usage guides and examples
  - [x] Quickstart guide (`docs/guides/QUICKSTART.md`)
  - [x] Tutorial: Manual time control workflow (`docs/guides/TUTORIAL_MANUAL_TIME.md`)
  - [ ] Tutorial: Building an agent response loop
  - [ ] Examples collection (copy-paste snippets)
- [ ] Write API client library (optional)

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
