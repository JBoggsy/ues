# UES Web App UI - Implementation Plan

## Overview

This document outlines the implementation plan for the UES browser-based UI (Phase 3). The UI provides a visual interface for designing simulated environments, managing event sequences, and monitoring simulation state in real-time.

### Design Principles

1. **Separation of Concerns**: The web UI is a standalone application that communicates with the UES backend exclusively through the REST API (using the Python API client library patterns as reference)
2. **Polling-Based Updates**: Real-time state updates via polling rather than WebSockets, ensuring consistency with the existing API client library approach
3. **Progressive Enhancement**: Start with core simulation controls, then add modality viewers incrementally
4. **Persistence Ready**: Architecture supports saving/loading environment configurations and event sequences (implementation details TBD)

---

## Tech Stack

| Category | Technology | Purpose |
|----------|------------|---------|
| **Framework** | React 18+ | Component-based UI |
| **Language** | TypeScript | Type safety, IDE support |
| **Build Tool** | Vite | Fast development, HMR |
| **Styling** | Tailwind CSS | Utility-first CSS |
| **Components** | shadcn/ui | Accessible, customizable components |
| **State (Server)** | TanStack Query v5 | API state management, polling |
| **State (Client)** | Zustand | Local UI state (if needed) |
| **Routing** | React Router v6 | Client-side navigation |
| **HTTP Client** | Axios or fetch | API communication |
| **Icons** | Lucide React | Icon library |
| **Date/Time** | date-fns | Date manipulation |
| **Forms** | React Hook Form + Zod | Form handling + validation |

---

## Project Structure

```
webapp/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── components.json              # shadcn/ui config
│
├── public/
│   └── favicon.ico
│
├── src/
│   ├── main.tsx                 # App entry point
│   ├── App.tsx                  # Root component with routing
│   ├── index.css                # Global styles + Tailwind
│   ├── vite-env.d.ts            # Vite type definitions
│   │
│   ├── api/                     # API client layer
│   │   ├── client.ts            # Axios instance configuration
│   │   ├── types.ts             # TypeScript types (from OpenAPI)
│   │   ├── hooks/               # TanStack Query hooks
│   │   │   ├── useTime.ts       # Time control hooks
│   │   │   ├── useSimulation.ts # Simulation control hooks
│   │   │   ├── useEvents.ts     # Event management hooks
│   │   │   ├── useEnvironment.ts# Environment state hooks
│   │   │   └── useModalities.ts # Modality-specific hooks
│   │   └── index.ts             # API exports
│   │
│   ├── components/              # Reusable UI components
│   │   ├── ui/                  # shadcn/ui components (auto-generated)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── slider.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/              # Layout components
│   │   │   ├── Header.tsx       # Top navigation bar
│   │   │   ├── Sidebar.tsx      # Modality navigation
│   │   │   ├── MainContent.tsx  # Central content area
│   │   │   └── Layout.tsx       # Main layout wrapper
│   │   │
│   │   ├── simulation/          # Simulation control components
│   │   │   ├── SimulationControls.tsx   # Play/pause/stop buttons
│   │   │   ├── TimeDisplay.tsx          # Current time display
│   │   │   ├── TimeScaleSlider.tsx      # Time scale control
│   │   │   ├── TimeAdvanceControls.tsx  # Advance/skip buttons
│   │   │   └── SimulationStatus.tsx     # Status indicator
│   │   │
│   │   ├── events/              # Event management components
│   │   │   ├── EventTimeline.tsx        # Visual timeline
│   │   │   ├── EventList.tsx            # Tabular event list
│   │   │   ├── EventCard.tsx            # Single event display
│   │   │   ├── EventCreator.tsx         # New event form
│   │   │   └── EventDetails.tsx         # Event detail modal
│   │   │
│   │   ├── modalities/          # Modality viewer components
│   │   │   ├── ModalityCard.tsx         # Sidebar modality item
│   │   │   ├── ModalitySummary.tsx      # Quick state summary
│   │   │   │
│   │   │   ├── email/           # Email modality
│   │   │   │   ├── EmailViewer.tsx
│   │   │   │   ├── EmailList.tsx
│   │   │   │   ├── EmailThread.tsx
│   │   │   │   └── EmailComposer.tsx
│   │   │   │
│   │   │   ├── sms/             # SMS modality
│   │   │   │   ├── SMSViewer.tsx
│   │   │   │   ├── ConversationList.tsx
│   │   │   │   └── MessageThread.tsx
│   │   │   │
│   │   │   ├── calendar/        # Calendar modality
│   │   │   │   ├── CalendarViewer.tsx
│   │   │   │   ├── DayView.tsx
│   │   │   │   ├── WeekView.tsx
│   │   │   │   └── EventForm.tsx
│   │   │   │
│   │   │   ├── chat/            # Chat modality
│   │   │   │   ├── ChatViewer.tsx
│   │   │   │   └── ChatHistory.tsx
│   │   │   │
│   │   │   ├── location/        # Location modality
│   │   │   │   ├── LocationViewer.tsx
│   │   │   │   └── LocationHistory.tsx
│   │   │   │
│   │   │   ├── weather/         # Weather modality
│   │   │   │   ├── WeatherViewer.tsx
│   │   │   │   └── ForecastCard.tsx
│   │   │   │
│   │   │   └── time/            # Time preferences modality
│   │   │       └── TimePreferencesViewer.tsx
│   │   │
│   │   └── common/              # Shared components
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorDisplay.tsx
│   │       ├── EmptyState.tsx
│   │       └── Badge.tsx
│   │
│   ├── pages/                   # Page-level components
│   │   ├── Dashboard.tsx        # Main simulation dashboard
│   │   ├── EventManager.tsx     # Event queue management page
│   │   ├── ModalityPage.tsx     # Generic modality detail page
│   │   └── Settings.tsx         # Configuration page
│   │
│   ├── stores/                  # Zustand stores (if needed)
│   │   └── uiStore.ts           # UI state (sidebar open, etc.)
│   │
│   ├── lib/                     # Utility functions
│   │   ├── utils.ts             # General utilities
│   │   ├── formatters.ts        # Date/time formatters
│   │   └── cn.ts                # Class name utility (shadcn)
│   │
│   └── types/                   # Shared TypeScript types
│       ├── modality.ts          # Modality-related types
│       ├── event.ts             # Event-related types
│       └── simulation.ts        # Simulation-related types
│
└── README.md                    # Web app documentation
```

---

## Implementation Phases

### Phase 3.1: Project Setup & Core Layout (Week 1)

**Goal**: Establish project foundation with working layout skeleton.

#### Tasks

1. **Initialize Vite Project**
   ```bash
   cd webapp
   npm create vite@latest . -- --template react-ts
   npm install
   ```

2. **Install Dependencies**
   ```bash
   # Core dependencies
   npm install axios @tanstack/react-query react-router-dom zustand
   npm install date-fns lucide-react
   npm install react-hook-form @hookform/resolvers zod
   
   # Tailwind CSS
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   
   # shadcn/ui (after Tailwind setup)
   npx shadcn@latest init
   npx shadcn@latest add button card input slider badge
   ```

3. **Configure Tailwind CSS**
   - Set up `tailwind.config.js` with shadcn/ui presets
   - Configure dark mode support
   - Add custom UES color palette

4. **Create Layout Components**
   - `Layout.tsx`: Main wrapper with header, sidebar, content areas
   - `Header.tsx`: App title, simulation status indicator
   - `Sidebar.tsx`: Modality navigation list
   - `MainContent.tsx`: Content area wrapper

5. **Set Up Routing**
   - Dashboard route (default)
   - Event manager route
   - Modality detail routes (parameterized)
   - Settings route

6. **Configure API Client**
   - Create Axios instance with base URL configuration
   - Set up TanStack Query provider
   - Create placeholder hooks

#### Deliverables
- [ ] Running Vite dev server at `http://localhost:5173`
- [ ] Basic layout visible with navigation
- [ ] Routes navigable (even if pages are empty)
- [ ] API client configured (can ping backend)

---

### Phase 3.2: Simulation Controls (Week 2)

**Goal**: Implement time display and simulation control functionality.

#### Tasks

1. **Time Display Component**
   - Show current simulator time
   - Format options (12h/24h, timezone)
   - Auto-refresh via polling (configurable interval)

2. **Simulation Control Buttons**
   - Start simulation button
   - Stop simulation button
   - Pause/Resume toggle
   - Reset simulation button (with confirmation)

3. **Time Advancement Controls**
   - "Advance by duration" input + button
   - "Skip to next event" button
   - "Jump to time" date/time picker

4. **Time Scale Control**
   - Slider for time scale (0.1x to 10x)
   - Preset buttons (0.5x, 1x, 2x, 5x)
   - Display current scale value

5. **Simulation Status Display**
   - Running/Paused/Stopped indicator
   - Events processed count
   - Events pending count
   - Last event executed info

6. **API Hooks**
   - `useTimeState()`: Poll `/simulator/time`
   - `useAdvanceTime()`: Mutation for `/simulator/time/advance`
   - `useSetTime()`: Mutation for `/simulator/time/set`
   - `useSimulationStatus()`: Poll `/simulation/status`
   - `useStartSimulation()`: Mutation for `/simulation/start`
   - `useStopSimulation()`: Mutation for `/simulation/stop`

#### Deliverables
- [ ] Time display updates in real-time (via polling)
- [ ] All simulation controls functional
- [ ] Status indicators reflect actual state
- [ ] Error handling for failed API calls

---

### Phase 3.3: Environment Overview (Week 3)

**Goal**: Display environment state with modality summaries.

#### Tasks

1. **Modality Sidebar Enhancement**
   - List all modalities with icons
   - Show summary badge (e.g., "3 unread" for email)
   - Active state highlighting
   - Click to navigate to modality detail

2. **Dashboard Overview**
   - Grid of modality summary cards
   - Each card shows key metrics
   - Quick action buttons per modality

3. **Modality Summary Cards**
   - Email: Unread count, total count
   - SMS: Conversation count, unread messages
   - Calendar: Today's events, upcoming count
   - Chat: Message count, active conversations
   - Location: Current location name/coords
   - Weather: Current conditions summary
   - Time: Timezone, format preference

4. **API Hooks**
   - `useEnvironmentState()`: Poll `/environment/state`
   - `useModalityList()`: Get `/environment/modalities`
   - `useModalityState(modality)`: Get `/environment/modalities/{modality}`

#### Deliverables
- [ ] Sidebar shows all modalities with live status
- [ ] Dashboard displays summary cards
- [ ] Clicking modality navigates to detail view
- [ ] Summaries update on poll refresh

---

### Phase 3.4: Event Management (Week 4)

**Goal**: View, create, and manage scheduled events.

#### Tasks

1. **Event List View**
   - Table showing all events
   - Columns: Time, Modality, Status, Summary, Actions
   - Sortable by time, modality
   - Filterable by status (pending/executed/cancelled)
   - Filterable by modality

2. **Event Timeline View** (Stretch)
   - Horizontal timeline visualization
   - Events as markers on timeline
   - Color-coded by modality
   - Zoom in/out controls

3. **Event Detail View**
   - Modal showing full event data
   - JSON view of event payload
   - Cancel button for pending events
   - Execution timestamp for executed events

4. **Event Creation**
   - Modal with modality selector
   - Dynamic form based on selected modality
   - Schedule time picker
   - "Create Immediate" option
   - Form validation

5. **Modality-Specific Forms**
   - Email: to, subject, body, etc.
   - SMS: to, body, etc.
   - Calendar: title, start, end, etc.
   - Chat: role, content
   - Location: lat, lon, name
   - Weather: location, conditions
   - Time: timezone, format

6. **API Hooks**
   - `useEvents()`: Poll `/events`
   - `useEvent(id)`: Get `/events/{id}`
   - `useCreateEvent()`: Mutation for `POST /events`
   - `useCreateImmediateEvent()`: Mutation for `POST /events/immediate`
   - `useCancelEvent()`: Mutation for `DELETE /events/{id}`
   - `useEventSummary()`: Get `/events/summary`

#### Deliverables
- [ ] Event list displays all events
- [ ] Events can be filtered and sorted
- [ ] New events can be created via form
- [ ] Pending events can be cancelled
- [ ] Event details viewable in modal

---

### Phase 3.5: Modality Detail Viewers (Weeks 5-6)

**Goal**: Build detailed viewers for each modality.

#### Priority Order

1. **Email Viewer** (Most complex, high value)
   - Folder tabs (Inbox, Sent, Drafts, Archive, Trash)
   - Email list with sender, subject, preview
   - Thread view for conversations
   - Read/unread status display
   - Action buttons (delete, archive, etc.)

2. **SMS Viewer**
   - Conversation list
   - Message bubbles (sent/received styling)
   - Timestamp display
   - Read/delivered status

3. **Calendar Viewer**
   - Day/Week/Month toggle
   - Event blocks with color coding
   - Click to view event details
   - Today indicator

4. **Chat Viewer**
   - Conversation selector
   - Message list with role indicators
   - Multimodal content support

5. **Location Viewer**
   - Current location display
   - Coordinates + address
   - Location history list
   - (Stretch: Map integration)

6. **Weather Viewer**
   - Current conditions card
   - Location selector
   - Forecast display
   - Last updated time

7. **Time Preferences Viewer**
   - Current timezone
   - Date format preference
   - Preference history

#### Deliverables
- [ ] Each modality has a functional detail viewer
- [ ] State updates reflect in viewers
- [ ] Query/filter capabilities work
- [ ] Consistent styling across viewers

---

### Phase 3.6: Polish & Configuration (Week 7)

**Goal**: Add settings, persistence groundwork, and polish.

#### Tasks

1. **Settings Page**
   - API endpoint configuration
   - Polling interval settings
   - Theme toggle (light/dark)
   - Date/time format preferences

2. **Persistence Groundwork**
   - Export environment state as JSON
   - Export event queue as JSON
   - Import environment state
   - Import event sequence
   - (Backend persistence endpoints TBD)

3. **Error Handling**
   - Global error boundary
   - Toast notifications for errors
   - Retry logic for failed requests
   - Offline indicator

4. **Loading States**
   - Skeleton loaders for content
   - Spinner for actions
   - Optimistic updates where appropriate

5. **Accessibility**
   - Keyboard navigation
   - Screen reader labels
   - Focus management
   - Color contrast verification

6. **Documentation**
   - User guide for web UI
   - Developer setup instructions
   - Component documentation

#### Deliverables
- [ ] Settings page functional
- [ ] Export/import working (local files)
- [ ] Error handling comprehensive
- [ ] Loading states polished
- [ ] Basic accessibility audit passed

---

## API Integration Details

### Polling Strategy

```typescript
// Example polling configuration
const POLLING_INTERVALS = {
  time: 1000,        // 1 second for time display
  simulation: 2000,  // 2 seconds for status
  events: 3000,      // 3 seconds for event list
  modalities: 5000,  // 5 seconds for modality state
} as const;

// TanStack Query example
const { data: timeState } = useQuery({
  queryKey: ['time'],
  queryFn: () => api.getTimeState(),
  refetchInterval: POLLING_INTERVALS.time,
});
```

### API Endpoints Used

| UI Feature | Endpoint | Method | Polling |
|------------|----------|--------|---------|
| Time Display | `/simulator/time` | GET | 1s |
| Advance Time | `/simulator/time/advance` | POST | - |
| Set Time | `/simulator/time/set` | POST | - |
| Skip to Next | `/simulator/time/skip-to-next` | POST | - |
| Pause | `/simulator/time/pause` | POST | - |
| Resume | `/simulator/time/resume` | POST | - |
| Set Scale | `/simulator/time/set-scale` | POST | - |
| Sim Status | `/simulation/status` | GET | 2s |
| Start Sim | `/simulation/start` | POST | - |
| Stop Sim | `/simulation/stop` | POST | - |
| Reset Sim | `/simulation/reset` | POST | - |
| Clear Sim | `/simulation/clear` | POST | - |
| Undo | `/simulation/undo` | POST | - |
| Redo | `/simulation/redo` | POST | - |
| Env State | `/environment/state` | GET | 5s |
| Modality List | `/environment/modalities` | GET | - |
| Modality State | `/environment/modalities/{m}` | GET | 5s |
| Modality Query | `/environment/modalities/{m}/query` | POST | - |
| Event List | `/events` | GET | 3s |
| Create Event | `/events` | POST | - |
| Immediate Event | `/events/immediate` | POST | - |
| Get Event | `/events/{id}` | GET | - |
| Cancel Event | `/events/{id}` | DELETE | - |
| Event Summary | `/events/summary` | GET | 5s |

---

## TypeScript Types

Types will be generated/derived from the OpenAPI specification. Key types include:

```typescript
// api/types.ts (simplified examples)

interface TimeState {
  current_time: string;  // ISO datetime
  time_scale: number;
  is_paused: boolean;
  timezone: string;
}

interface SimulationStatus {
  is_running: boolean;
  events_executed: number;
  events_pending: number;
  start_time: string | null;
}

interface SimulatorEvent {
  id: string;
  scheduled_time: string;
  modality: string;
  status: 'pending' | 'executed' | 'cancelled' | 'failed';
  data: Record<string, unknown>;
  agent_id?: string;
}

interface EnvironmentState {
  time: TimeState;
  modalities: Record<string, ModalityState>;
}

interface ModalityState {
  modality_type: string;
  summary: string;
  // ... modality-specific fields
}
```

---

## Development Workflow

### Running the Development Server

```bash
# Terminal 1: Start the UES backend
cd /home/boggsj/Coding/personal/ues
uv run uvicorn main:app --reload --port 8000

# Terminal 2: Start the web UI
cd /home/boggsj/Coding/personal/ues/webapp
npm run dev
```

### Environment Configuration

```env
# webapp/.env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_POLLING_ENABLED=true
VITE_DEFAULT_POLLING_INTERVAL=3000
```

---

## Future Considerations

### WebSocket Support (Optional Enhancement)
If real-time requirements increase, consider adding WebSocket support to the backend:
- `/ws/simulation` - Real-time simulation state
- `/ws/events` - Event execution notifications
- The UI can fall back to polling if WebSocket unavailable

### Scenario Library
- Pre-built simulation scenarios
- Import/export scenario bundles
- Community sharing (future)

### Agent Integration UI
- View connected agents
- Agent activity logs
- Manual agent trigger controls

---

## Success Criteria

### Phase 3 MVP Complete When:
1. ✅ UI connects to backend API successfully
2. ✅ Simulation can be started/stopped/paused from UI
3. ✅ Time can be viewed and controlled from UI
4. ✅ Events can be viewed in a list
5. ✅ New events can be created via forms
6. ✅ At least 3 modality viewers are functional
7. ✅ State updates reflect within polling interval

### Quality Gates:
- No console errors in normal operation
- Responsive on desktop (1024px+)
- All API errors display user-friendly messages
- Loading states for all async operations
