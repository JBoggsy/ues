/**
 * Type definitions for the Calendar Viewer component.
 * These extend the base API types with UI-specific properties.
 */

// ============================================================================
// Enums / Literal Types
// ============================================================================

export type CalendarOperation = 'create' | 'update' | 'delete';
export type RecurrenceScope = 'this' | 'this_and_future' | 'all';
export type AttendeeResponse = 'accepted' | 'declined' | 'tentative' | 'needs-action';
export type EventStatus = 'confirmed' | 'tentative' | 'cancelled';
export type EventVisibility = 'public' | 'private' | 'default';
export type EventTransparency = 'opaque' | 'transparent';
export type ReminderType = 'notification' | 'email' | 'both';
export type RecurrenceFrequency = 'daily' | 'weekly' | 'monthly' | 'yearly';
export type RecurrenceEndType = 'never' | 'until' | 'count';
export type DayOfWeek = 'monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday';

// ============================================================================
// Calendar View Types
// ============================================================================

export type CalendarViewMode = 'month' | 'week' | '3-day' | 'day';

// ============================================================================
// Backend Model Types
// ============================================================================

/**
 * Event attendee.
 */
export interface Attendee {
  email: string;
  display_name?: string | null;
  optional: boolean;
  response: AttendeeResponse;
  comment?: string | null;
}

/**
 * Recurrence rule for repeating events.
 */
export interface RecurrenceRule {
  frequency: RecurrenceFrequency;
  interval: number;
  days_of_week?: DayOfWeek[] | null;
  day_of_month?: number | null;
  month_of_year?: number | null;
  end_type: RecurrenceEndType;
  end_date?: string | null;
  count?: number | null;
}

/**
 * Event reminder.
 */
export interface Reminder {
  minutes_before: number;
  type: ReminderType;
}

/**
 * Event attachment.
 */
export interface Attachment {
  filename: string;
  size: number;
  mime_type: string;
  url?: string | null;
  attachment_id: string;
}

/**
 * A calendar container for events.
 */
export interface Calendar {
  calendar_id: string;
  name: string;
  color: string;
  visible: boolean;
  created_at: string;
  updated_at: string;
  event_ids: string[];
  default_reminders: Reminder[];
}

/**
 * A calendar event with all metadata.
 */
export interface CalendarEvent {
  event_id: string;
  calendar_id: string;
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  timezone: string;
  description?: string | null;
  location?: string | null;
  status: EventStatus;
  organizer?: string | null;
  attendees: Attendee[];
  recurrence?: RecurrenceRule | null;
  recurrence_exceptions: string[];
  recurrence_id?: string | null;
  parent_event_id?: string | null;
  reminders: Reminder[];
  color?: string | null;
  visibility: EventVisibility;
  transparency: EventTransparency;
  attachments: Attachment[];
  conference_link?: string | null;
  created_at: string;
  updated_at: string;
  deleted_at?: string | null;
}

/**
 * Complete calendar state from the backend.
 */
export interface CalendarState {
  modality_type: string;
  last_updated: string;
  update_count: number;
  default_calendar_id: string;
  user_timezone: string;
  calendars: Record<string, Calendar>;
  events: Record<string, CalendarEvent>;
  calendar_count: number;
  event_count: number;
}

// ============================================================================
// API Request Types
// ============================================================================

/**
 * Request to create a new calendar event.
 */
export interface CreateCalendarEventRequest {
  calendar_id?: string;
  title: string;
  description?: string | null;
  start: string;
  end: string;
  all_day?: boolean;
  timezone?: string;
  location?: string | null;
  status?: EventStatus;
  organizer?: string | null;
  attendees?: Attendee[] | null;
  recurrence?: RecurrenceRule | null;
  recurrence_exceptions?: string[] | null;
  reminders?: Reminder[] | null;
  color?: string | null;
  visibility?: EventVisibility;
  transparency?: EventTransparency;
  attachments?: Attachment[] | null;
  conference_link?: string | null;
}

/**
 * Request to update an existing calendar event.
 */
export interface UpdateCalendarEventRequest {
  event_id: string;
  calendar_id?: string;
  recurrence_scope?: RecurrenceScope;
  title?: string | null;
  description?: string | null;
  start?: string | null;
  end?: string | null;
  all_day?: boolean | null;
  timezone?: string | null;
  location?: string | null;
  status?: EventStatus | null;
  organizer?: string | null;
  attendees?: Attendee[] | null;
  recurrence?: RecurrenceRule | null;
  recurrence_exceptions?: string[] | null;
  recurrence_id?: string | null;
  reminders?: Reminder[] | null;
  color?: string | null;
  visibility?: EventVisibility | null;
  transparency?: EventTransparency | null;
  attachments?: Attachment[] | null;
  conference_link?: string | null;
}

/**
 * Request to delete a calendar event.
 */
export interface DeleteCalendarEventRequest {
  event_id: string;
  calendar_id?: string;
  recurrence_scope?: RecurrenceScope;
  recurrence_id?: string | null;
}

/**
 * Request to query calendar events.
 */
export interface CalendarQueryRequest {
  calendar_ids?: string[] | null;
  start?: string | null;
  end?: string | null;
  search?: string | null;
  status?: EventStatus | null;
  has_attendees?: boolean | null;
  recurring?: boolean | null;
  expand_recurring?: boolean;
  limit?: number | null;
  offset?: number;
  sort_by?: string;
  sort_order?: string;
}

// ============================================================================
// UI Types
// ============================================================================

/**
 * Event display item for calendar grid.
 */
export interface EventDisplayItem {
  event: CalendarEvent;
  calendar: Calendar;
  displayColor: string;
  isMultiDay: boolean;
  startDate: Date;
  endDate: Date;
}

/**
 * Time slot for click-to-schedule.
 */
export interface TimeSlot {
  date: Date;
  hour?: number;
  minute?: number;
}

/**
 * Form data for creating/editing events.
 */
export interface EventFormData {
  title: string;
  calendar_id: string;
  all_day: boolean;
  start_date: string;
  start_time: string;
  end_date: string;
  end_time: string;
  timezone: string;
  location: string;
  description: string;
  conference_link: string;
  recurrence: RecurrenceRule | null;
  reminders: Reminder[];
  attendees: Attendee[];
  color: string | null;
  status: EventStatus;
  visibility: EventVisibility;
}

/**
 * Calendar color preset.
 */
export interface ColorPreset {
  name: string;
  value: string;
}

/**
 * Default color presets for calendars.
 */
export const CALENDAR_COLORS: ColorPreset[] = [
  { name: 'Blue', value: '#4285f4' },
  { name: 'Red', value: '#ea4335' },
  { name: 'Yellow', value: '#fbbc04' },
  { name: 'Green', value: '#34a853' },
  { name: 'Purple', value: '#9c27b0' },
  { name: 'Pink', value: '#e91e63' },
  { name: 'Teal', value: '#009688' },
  { name: 'Orange', value: '#ff9800' },
  { name: 'Indigo', value: '#3f51b5' },
  { name: 'Cyan', value: '#00bcd4' },
];

/**
 * Timezone presets for quick selection.
 */
export const TIMEZONE_PRESETS = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
];
