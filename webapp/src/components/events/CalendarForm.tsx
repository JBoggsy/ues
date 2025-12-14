/**
 * Calendar event creation form.
 *
 * Allows creating, updating, or deleting calendar events.
 * Supports all-day events, recurrence, attendees, reminders, etc.
 */

import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { ModalityFormProps } from './types';

/**
 * Recurrence frequency options.
 */
const RECURRENCE_FREQUENCIES = [
  { value: 'daily', label: 'Daily' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'monthly', label: 'Monthly' },
  { value: 'yearly', label: 'Yearly' },
];

/**
 * Days of the week for weekly recurrence.
 */
const DAYS_OF_WEEK = [
  { value: 'monday', label: 'Mon' },
  { value: 'tuesday', label: 'Tue' },
  { value: 'wednesday', label: 'Wed' },
  { value: 'thursday', label: 'Thu' },
  { value: 'friday', label: 'Fri' },
  { value: 'saturday', label: 'Sat' },
  { value: 'sunday', label: 'Sun' },
];

/**
 * Event status options.
 */
const EVENT_STATUSES = [
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'tentative', label: 'Tentative' },
  { value: 'cancelled', label: 'Cancelled' },
];

/**
 * Recurrence end type options.
 */
const RECURRENCE_END_TYPES = [
  { value: 'never', label: 'Never ends' },
  { value: 'until', label: 'End by date' },
  { value: 'count', label: 'After N occurrences' },
];

/**
 * Reminder presets in minutes.
 */
const REMINDER_PRESETS = [
  { value: '0', label: 'At event time' },
  { value: '5', label: '5 minutes before' },
  { value: '10', label: '10 minutes before' },
  { value: '15', label: '15 minutes before' },
  { value: '30', label: '30 minutes before' },
  { value: '60', label: '1 hour before' },
  { value: '1440', label: '1 day before' },
];

/**
 * Default data for a new calendar event.
 */
export const calendarDefaultData = {
  operation: 'create',
  event_id: '',
  calendar_id: 'primary',
  recurrence_scope: 'this',
  // Event details
  title: '',
  description: '',
  location: '',
  status: 'confirmed',
  // Timing
  start_date: '',
  start_time: '09:00',
  end_date: '',
  end_time: '10:00',
  all_day: false,
  timezone: 'America/New_York',
  // Attendees (comma-separated emails)
  attendees: '',
  // Recurrence
  is_recurring: false,
  recurrence_frequency: 'weekly',
  recurrence_interval: '1',
  recurrence_days: [] as string[],
  recurrence_end_type: 'never',
  recurrence_end_date: '',
  recurrence_count: '10',
  // Reminder
  reminder_minutes: '15',
  // Optional
  conference_link: '',
  color: '',
};

/**
 * Validate calendar data based on operation.
 */
export function validateCalendarData(data: Record<string, unknown>): string | null {
  const operation = data.operation as string;

  if (!operation) {
    return 'Operation is required';
  }

  if (operation === 'create') {
    if (!data.title || (data.title as string).trim() === '') {
      return 'Event title is required';
    }
    if (!data.start_date || (data.start_date as string).trim() === '') {
      return 'Start date is required';
    }
    if (!data.end_date || (data.end_date as string).trim() === '') {
      return 'End date is required';
    }
  }

  if (operation === 'update' || operation === 'delete') {
    if (!data.event_id || (data.event_id as string).trim() === '') {
      return 'Event ID is required for update/delete operations';
    }
  }

  return null;
}

/**
 * Transform form data to API format.
 */
export function transformCalendarData(data: Record<string, unknown>): Record<string, unknown> {
  const operation = data.operation as string;
  const result: Record<string, unknown> = {
    operation,
    calendar_id: data.calendar_id || 'primary',
  };

  if (operation === 'update' || operation === 'delete') {
    result.event_id = data.event_id;
    result.recurrence_scope = data.recurrence_scope || 'this';
  }

  if (operation === 'delete') {
    return result;
  }

  // Event details
  if (data.title) result.title = data.title;
  if (data.description && (data.description as string).trim()) {
    result.description = data.description;
  }
  if (data.location && (data.location as string).trim()) {
    result.location = data.location;
  }
  result.status = data.status || 'confirmed';

  // Timing
  const allDay = data.all_day as boolean;
  result.all_day = allDay;
  result.timezone = data.timezone || 'UTC';

  if (data.start_date) {
    if (allDay) {
      // For all-day events, just use the date
      result.start = `${data.start_date}T00:00:00`;
    } else {
      result.start = `${data.start_date}T${data.start_time || '09:00'}:00`;
    }
  }

  if (data.end_date) {
    if (allDay) {
      result.end = `${data.end_date}T23:59:59`;
    } else {
      result.end = `${data.end_date}T${data.end_time || '10:00'}:00`;
    }
  }

  // Attendees
  const attendeesStr = data.attendees as string;
  if (attendeesStr && attendeesStr.trim()) {
    const emails = attendeesStr.split(',').map((e) => e.trim()).filter((e) => e.length > 0);
    if (emails.length > 0) {
      result.attendees = emails.map((email) => ({ email, response: 'needs-action' }));
    }
  }

  // Recurrence
  if (data.is_recurring) {
    const recurrence: Record<string, unknown> = {
      frequency: data.recurrence_frequency,
      interval: parseInt(data.recurrence_interval as string, 10) || 1,
      end_type: data.recurrence_end_type,
    };

    // Weekly: days of week
    const recurrenceDays = data.recurrence_days as string[];
    if (data.recurrence_frequency === 'weekly' && recurrenceDays && recurrenceDays.length > 0) {
      recurrence.days_of_week = recurrenceDays;
    }

    // End conditions
    if (data.recurrence_end_type === 'until' && data.recurrence_end_date) {
      recurrence.end_date = data.recurrence_end_date;
    }
    if (data.recurrence_end_type === 'count' && data.recurrence_count) {
      recurrence.count = parseInt(data.recurrence_count as string, 10) || 10;
    }

    result.recurrence = recurrence;
  }

  // Reminder (skip if "none" or empty)
  const reminderMinutes = data.reminder_minutes as string;
  if (reminderMinutes && reminderMinutes !== '' && reminderMinutes !== 'none') {
    result.reminders = [
      { minutes_before: parseInt(reminderMinutes, 10), type: 'notification' },
    ];
  }

  // Optional fields
  if (data.conference_link && (data.conference_link as string).trim()) {
    result.conference_link = data.conference_link;
  }
  if (data.color && (data.color as string).trim()) {
    result.color = data.color;
  }

  return result;
}

/**
 * Calendar form component.
 */
export function CalendarForm({ data, onChange }: ModalityFormProps) {
  const operation = data.operation as string;

  const handleChange = (field: string, value: string | boolean | string[]) => {
    onChange({ ...data, [field]: value });
  };

  const toggleDayOfWeek = (day: string) => {
    const currentDays = (data.recurrence_days as string[]) || [];
    const newDays = currentDays.includes(day)
      ? currentDays.filter((d) => d !== day)
      : [...currentDays, day];
    handleChange('recurrence_days', newDays);
  };

  const isCreate = operation === 'create';
  const isUpdate = operation === 'update';
  const isDelete = operation === 'delete';
  const isRecurring = data.is_recurring as boolean;
  const isAllDay = data.all_day as boolean;

  return (
    <div className="space-y-4">
      {/* Operation Selector */}
      <div className="space-y-2">
        <Label htmlFor="operation">Operation</Label>
        <Select
          value={operation}
          onValueChange={(v) => handleChange('operation', v)}
        >
          <SelectTrigger id="operation">
            <SelectValue placeholder="Select operation" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="create">📅 Create Event</SelectItem>
            <SelectItem value="update">✏️ Update Event</SelectItem>
            <SelectItem value="delete">🗑️ Delete Event</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Event ID (for update/delete) */}
      {(isUpdate || isDelete) && (
        <>
          <div className="space-y-2">
            <Label htmlFor="event_id">Event ID</Label>
            <Input
              id="event_id"
              placeholder="event_abc123..."
              value={data.event_id as string}
              onChange={(e) => handleChange('event_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="recurrence_scope">Recurrence Scope</Label>
            <Select
              value={data.recurrence_scope as string}
              onValueChange={(v) => handleChange('recurrence_scope', v)}
            >
              <SelectTrigger id="recurrence_scope">
                <SelectValue placeholder="Select scope" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="this">This occurrence only</SelectItem>
                <SelectItem value="this_and_future">This and future</SelectItem>
                <SelectItem value="all">All occurrences</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              For recurring events, which occurrences to affect
            </p>
          </div>
        </>
      )}

      {/* Delete confirmation */}
      {isDelete && (
        <div className="rounded-md bg-red-500/10 border border-red-500/20 p-4">
          <p className="text-sm text-red-600 dark:text-red-400">
            ⚠️ This event will be permanently deleted.
          </p>
        </div>
      )}

      {/* Event Details (create/update) */}
      {(isCreate || isUpdate) && (
        <>
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Title {isCreate && '*'}</Label>
            <Input
              id="title"
              placeholder="Meeting with team"
              value={data.title as string}
              onChange={(e) => handleChange('title', e.target.value)}
            />
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Event description..."
              value={data.description as string}
              onChange={(e) => handleChange('description', e.target.value)}
              rows={2}
            />
          </div>

          {/* Location */}
          <div className="space-y-2">
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              placeholder="Conference Room A / Zoom link"
              value={data.location as string}
              onChange={(e) => handleChange('location', e.target.value)}
            />
          </div>

          {/* All Day Toggle */}
          <div className="flex items-center justify-between">
            <Label htmlFor="all_day">All-day event</Label>
            <input
              type="checkbox"
              id="all_day"
              checked={isAllDay}
              onChange={(e) => handleChange('all_day', e.target.checked)}
              className="h-4 w-4"
            />
          </div>

          {/* Date/Time */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="start_date">Start Date {isCreate && '*'}</Label>
              <Input
                id="start_date"
                type="date"
                value={data.start_date as string}
                onChange={(e) => handleChange('start_date', e.target.value)}
              />
            </div>
            {!isAllDay && (
              <div className="space-y-2">
                <Label htmlFor="start_time">Start Time</Label>
                <Input
                  id="start_time"
                  type="time"
                  value={data.start_time as string}
                  onChange={(e) => handleChange('start_time', e.target.value)}
                />
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="end_date">End Date {isCreate && '*'}</Label>
              <Input
                id="end_date"
                type="date"
                value={data.end_date as string}
                onChange={(e) => handleChange('end_date', e.target.value)}
              />
            </div>
            {!isAllDay && (
              <div className="space-y-2">
                <Label htmlFor="end_time">End Time</Label>
                <Input
                  id="end_time"
                  type="time"
                  value={data.end_time as string}
                  onChange={(e) => handleChange('end_time', e.target.value)}
                />
              </div>
            )}
          </div>

          {/* Timezone */}
          <div className="space-y-2">
            <Label htmlFor="timezone">Timezone</Label>
            <Select
              value={data.timezone as string}
              onValueChange={(v) => handleChange('timezone', v)}
            >
              <SelectTrigger id="timezone">
                <SelectValue placeholder="Select timezone" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="UTC">UTC</SelectItem>
                <SelectItem value="America/New_York">US/Eastern</SelectItem>
                <SelectItem value="America/Chicago">US/Central</SelectItem>
                <SelectItem value="America/Denver">US/Mountain</SelectItem>
                <SelectItem value="America/Los_Angeles">US/Pacific</SelectItem>
                <SelectItem value="Europe/London">UK/London</SelectItem>
                <SelectItem value="Europe/Paris">Europe/Paris</SelectItem>
                <SelectItem value="Asia/Tokyo">Asia/Tokyo</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Status */}
          <div className="space-y-2">
            <Label htmlFor="status">Status</Label>
            <Select
              value={data.status as string}
              onValueChange={(v) => handleChange('status', v)}
            >
              <SelectTrigger id="status">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                {EVENT_STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Attendees */}
          <div className="space-y-2">
            <Label htmlFor="attendees">Attendees</Label>
            <Input
              id="attendees"
              placeholder="alice@example.com, bob@example.com"
              value={data.attendees as string}
              onChange={(e) => handleChange('attendees', e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated email addresses
            </p>
          </div>

          {/* Recurrence Toggle */}
          <div className="flex items-center justify-between border-t pt-4">
            <Label htmlFor="is_recurring">Recurring event</Label>
            <input
              type="checkbox"
              id="is_recurring"
              checked={isRecurring}
              onChange={(e) => handleChange('is_recurring', e.target.checked)}
              className="h-4 w-4"
            />
          </div>

          {/* Recurrence Settings */}
          {isRecurring && (
            <div className="space-y-4 pl-4 border-l-2 border-primary/20">
              <div className="space-y-2">
                <Label htmlFor="recurrence_frequency">Frequency</Label>
                <Select
                  value={data.recurrence_frequency as string}
                  onValueChange={(v) => handleChange('recurrence_frequency', v)}
                >
                  <SelectTrigger id="recurrence_frequency">
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    {RECURRENCE_FREQUENCIES.map((f) => (
                      <SelectItem key={f.value} value={f.value}>
                        {f.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="recurrence_interval">Repeat every</Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="recurrence_interval"
                    type="number"
                    min="1"
                    value={data.recurrence_interval as string}
                    onChange={(e) => handleChange('recurrence_interval', e.target.value)}
                    className="w-20"
                  />
                  <span className="text-sm text-muted-foreground">
                    {data.recurrence_frequency === 'daily' && 'day(s)'}
                    {data.recurrence_frequency === 'weekly' && 'week(s)'}
                    {data.recurrence_frequency === 'monthly' && 'month(s)'}
                    {data.recurrence_frequency === 'yearly' && 'year(s)'}
                  </span>
                </div>
              </div>

              {/* Days of week for weekly */}
              {data.recurrence_frequency === 'weekly' && (
                <div className="space-y-2">
                  <Label>On days</Label>
                  <div className="flex flex-wrap gap-2">
                    {DAYS_OF_WEEK.map((day) => {
                      const isSelected = ((data.recurrence_days as string[]) || []).includes(day.value);
                      return (
                        <button
                          key={day.value}
                          type="button"
                          onClick={() => toggleDayOfWeek(day.value)}
                          className={`px-3 py-1 text-sm rounded border transition-colors ${
                            isSelected
                              ? 'border-primary bg-primary/10 text-primary'
                              : 'border-border hover:border-primary/50'
                          }`}
                        >
                          {day.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* End type */}
              <div className="space-y-2">
                <Label htmlFor="recurrence_end_type">Ends</Label>
                <Select
                  value={data.recurrence_end_type as string}
                  onValueChange={(v) => handleChange('recurrence_end_type', v)}
                >
                  <SelectTrigger id="recurrence_end_type">
                    <SelectValue placeholder="Select end type" />
                  </SelectTrigger>
                  <SelectContent>
                    {RECURRENCE_END_TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {data.recurrence_end_type === 'until' && (
                <div className="space-y-2">
                  <Label htmlFor="recurrence_end_date">End Date</Label>
                  <Input
                    id="recurrence_end_date"
                    type="date"
                    value={data.recurrence_end_date as string}
                    onChange={(e) => handleChange('recurrence_end_date', e.target.value)}
                  />
                </div>
              )}

              {data.recurrence_end_type === 'count' && (
                <div className="space-y-2">
                  <Label htmlFor="recurrence_count">Number of occurrences</Label>
                  <Input
                    id="recurrence_count"
                    type="number"
                    min="1"
                    value={data.recurrence_count as string}
                    onChange={(e) => handleChange('recurrence_count', e.target.value)}
                    className="w-24"
                  />
                </div>
              )}
            </div>
          )}

          {/* Reminder */}
          <div className="space-y-2 border-t pt-4">
            <Label htmlFor="reminder_minutes">Reminder</Label>
            <Select
              value={data.reminder_minutes as string}
              onValueChange={(v) => handleChange('reminder_minutes', v)}
            >
              <SelectTrigger id="reminder_minutes">
                <SelectValue placeholder="Select reminder" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No reminder</SelectItem>
                {REMINDER_PRESETS.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Conference Link */}
          <div className="space-y-2">
            <Label htmlFor="conference_link">Conference Link</Label>
            <Input
              id="conference_link"
              placeholder="https://zoom.us/j/..."
              value={data.conference_link as string}
              onChange={(e) => handleChange('conference_link', e.target.value)}
            />
          </div>
        </>
      )}
    </div>
  );
}
