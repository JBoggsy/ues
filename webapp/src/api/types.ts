/**
 * TypeScript types for the UES API.
 * These types mirror the Pydantic models from the backend.
 */

// ============================================================================
// Time Types
// ============================================================================

export interface TimeState {
  current_time: string; // ISO datetime string
  time_scale: number;
  is_paused: boolean;
  auto_advance: boolean;
  mode: 'manual' | 'auto' | 'paused';
}

export interface AdvanceTimeRequest {
  seconds: number;
}

export interface SetTimeRequest {
  target_time: string; // ISO datetime string
}

export interface SetScaleRequest {
  scale: number;
}

export interface EventExecutionDetail {
  event_id: string;
  modality: Modality;
  status: string;
  error?: string;
}

export interface AdvanceTimeResponse {
  previous_time: string;
  current_time: string;
  time_advanced: string;
  events_executed: number;
  events_failed: number;
  execution_details: EventExecutionDetail[];
}

export interface SetTimeResponse {
  previous_time: string;
  current_time: string;
  skipped_events: number;
  executed_events: number;
}

export interface SkipToNextResponse {
  previous_time: string;
  current_time: string;
  events_executed: number;
  next_event_time: string | null;
}

// ============================================================================
// Simulation Types
// ============================================================================

export interface SimulationStatus {
  is_running: boolean;
  current_time: string;
  is_paused: boolean;
  auto_advance: boolean;
  time_scale: number;
  pending_events: number;
  executed_events: number;
  failed_events: number;
  next_event_time: string | null;
}

export interface StartSimulationRequest {
  auto_advance?: boolean;
  time_scale?: number;
}

export interface UndoRedoRequest {
  count?: number;
}

export interface ClearRequest {
  reset_time_to?: string;
}

// ============================================================================
// Event Types
// ============================================================================

export type EventStatus = 'pending' | 'executing' | 'executed' | 'failed' | 'skipped' | 'cancelled';
export type Modality = 'email' | 'sms' | 'chat' | 'calendar' | 'location' | 'weather' | 'time';

export interface SimulatorEvent {
  event_id: string;  // Changed from 'id' to match API
  scheduled_time: string;
  modality: Modality;
  status: EventStatus;
  data: Record<string, unknown> | null;  // Can be null from API
  agent_id?: string;
  executed_at?: string;
  error_message?: string | null;
}

export interface CreateEventRequest {
  scheduled_time: string;
  modality: Modality;
  data: Record<string, unknown>;
  agent_id?: string;
}

export interface ImmediateEventRequest {
  modality: Modality;
  data: Record<string, unknown>;
  agent_id?: string;
}

export interface EventListResponse {
  events: SimulatorEvent[];
  total: number;
  pending: number;
  executed: number;
  failed: number;
  skipped: number;
}

export interface EventSummaryResponse {
  total: number;
  pending: number;
  executed: number;
  failed: number;
  skipped: number;
  by_modality: Record<string, number>;
  next_event_time: string | null;
}

// ============================================================================
// Environment Types
// ============================================================================

export interface ModalitySummary {
  modality_type: string;
  state_summary: string;
}

export interface EnvironmentState {
  current_time: string;
  modalities: Record<string, Record<string, unknown>>;
  summary: ModalitySummary[];
}

export interface ModalityListResponse {
  modalities: string[];
  count: number;
}

// ============================================================================
// Modality-Specific Types
// ============================================================================

// Email
export interface Email {
  id: string;
  from_address: string;
  to: string[];
  cc?: string[];
  bcc?: string[];
  subject: string;
  body: string;
  timestamp: string;
  thread_id?: string;
  is_read: boolean;
  folder: 'inbox' | 'sent' | 'drafts' | 'archive' | 'trash';
  attachments?: string[];
}

export interface EmailState {
  emails: Email[];
  threads: Record<string, string[]>;
}

// SMS
export interface SMSMessage {
  id: string;
  conversation_id: string;
  sender: string;
  body: string;
  timestamp: string;
  is_read: boolean;
  status: 'sent' | 'delivered' | 'read' | 'failed';
}

export interface SMSConversation {
  id: string;
  participants: string[];
  messages: SMSMessage[];
  last_message_time: string;
  unread_count: number;
}

export interface SMSState {
  conversations: SMSConversation[];
}

// Calendar
export interface CalendarEvent {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  location?: string;
  description?: string;
  attendees?: string[];
  is_all_day: boolean;
  recurrence_rule?: string;
}

export interface CalendarState {
  events: CalendarEvent[];
}

// Chat
export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface ChatConversation {
  id: string;
  messages: ChatMessage[];
}

export interface ChatState {
  conversations: ChatConversation[];
}

// Location
export interface Location {
  latitude: number;
  longitude: number;
  altitude?: number;
  accuracy?: number;
  name?: string;
  address?: string;
  timestamp: string;
}

export interface LocationState {
  current: Location | null;
  history: Location[];
}

// Weather
export interface WeatherConditions {
  temperature: number;
  feels_like: number;
  humidity: number;
  description: string;
  icon?: string;
  wind_speed?: number;
  wind_direction?: number;
}

export interface WeatherReport {
  location: string;
  current: WeatherConditions;
  forecast?: WeatherConditions[];
  timestamp: string;
}

export interface WeatherState {
  reports: Record<string, WeatherReport>;
}

// Time Preferences
export interface TimePreferences {
  timezone: string;
  date_format: string;
  time_format: '12h' | '24h';
}

export interface TimePreferencesState {
  current: TimePreferences;
  history: TimePreferences[];
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface SuccessResponse {
  success: boolean;
  message?: string;
}
