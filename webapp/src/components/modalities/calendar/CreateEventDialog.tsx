/**
 * Create/Edit event dialog component.
 * Provides a form for creating or editing calendar events.
 */
import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { ChevronDown, ChevronUp, Plus, X } from 'lucide-react';
import type {
  CalendarEvent,
  Calendar,
  EventFormData,
  RecurrenceRule,
  RecurrenceFrequency,
  RecurrenceEndType,
  DayOfWeek,
  EventStatus,
  EventVisibility,
} from './types';
import { cn } from '@/lib/utils';

interface CreateEventDialogProps {
  /** Whether dialog is open */
  open: boolean;
  /** Callback when dialog closes */
  onClose: () => void;
  /** Callback to save the event */
  onSave: (data: EventFormData, isEdit: boolean, eventId?: string) => Promise<void>;
  /** Event to edit (null for create mode) */
  editEvent?: CalendarEvent | null;
  /** Available calendars */
  calendars: Calendar[];
  /** Default calendar ID */
  defaultCalendarId: string;
  /** Pre-filled date/time (from click-to-schedule) */
  defaultDateTime?: { date: Date; hour?: number; minute?: number };
}

const DAYS_OF_WEEK: { value: DayOfWeek; label: string }[] = [
  { value: 'monday', label: 'Mon' },
  { value: 'tuesday', label: 'Tue' },
  { value: 'wednesday', label: 'Wed' },
  { value: 'thursday', label: 'Thu' },
  { value: 'friday', label: 'Fri' },
  { value: 'saturday', label: 'Sat' },
  { value: 'sunday', label: 'Sun' },
];

const REMINDER_OPTIONS = [
  { value: 0, label: 'At time of event' },
  { value: 5, label: '5 minutes before' },
  { value: 10, label: '10 minutes before' },
  { value: 15, label: '15 minutes before' },
  { value: 30, label: '30 minutes before' },
  { value: 60, label: '1 hour before' },
  { value: 1440, label: '1 day before' },
  { value: 10080, label: '1 week before' },
];

const COLOR_PRESETS = [
  { name: 'Blue', value: '#4285f4' },
  { name: 'Red', value: '#ea4335' },
  { name: 'Yellow', value: '#fbbc04' },
  { name: 'Green', value: '#34a853' },
  { name: 'Purple', value: '#9c27b0' },
  { name: 'Pink', value: '#e91e63' },
  { name: 'Teal', value: '#009688' },
  { name: 'Orange', value: '#ff9800' },
];

const TIMEZONE_OPTIONS = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Asia/Tokyo',
  'Australia/Sydney',
];

/**
 * Format date for input[type="date"].
 */
function formatDateForInput(date: Date): string {
  return date.toISOString().split('T')[0];
}

/**
 * Format time for input[type="time"].
 */
function formatTimeForInput(date: Date): string {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

/**
 * Get default form data.
 */
function getDefaultFormData(
  defaultCalendarId: string,
  defaultDateTime?: { date: Date; hour?: number; minute?: number }
): EventFormData {
  const now = defaultDateTime?.date || new Date();
  const startHour = defaultDateTime?.hour ?? now.getHours() + 1;
  const startMinute = defaultDateTime?.minute ?? 0;

  const startDate = new Date(now);
  startDate.setHours(startHour, startMinute, 0, 0);

  const endDate = new Date(startDate);
  endDate.setHours(startHour + 1, startMinute, 0, 0);

  return {
    title: '',
    calendar_id: defaultCalendarId,
    all_day: false,
    start_date: formatDateForInput(startDate),
    start_time: formatTimeForInput(startDate),
    end_date: formatDateForInput(endDate),
    end_time: formatTimeForInput(endDate),
    timezone: 'UTC',
    location: '',
    description: '',
    conference_link: '',
    recurrence: null,
    reminders: [{ minutes_before: 30, type: 'notification' }],
    attendees: [],
    color: null,
    status: 'confirmed',
    visibility: 'default',
  };
}

/**
 * Convert CalendarEvent to form data for editing.
 */
function eventToFormData(event: CalendarEvent): EventFormData {
  const start = new Date(event.start);
  const end = new Date(event.end);

  return {
    title: event.title,
    calendar_id: event.calendar_id,
    all_day: event.all_day,
    start_date: formatDateForInput(start),
    start_time: formatTimeForInput(start),
    end_date: formatDateForInput(end),
    end_time: formatTimeForInput(end),
    timezone: event.timezone,
    location: event.location || '',
    description: event.description || '',
    conference_link: event.conference_link || '',
    recurrence: event.recurrence || null,
    reminders: event.reminders.length > 0 
      ? event.reminders 
      : [{ minutes_before: 30, type: 'notification' }],
    attendees: event.attendees,
    color: event.color || null,
    status: event.status,
    visibility: event.visibility,
  };
}

/**
 * Recurrence editor sub-component.
 */
function RecurrenceEditor({
  recurrence,
  onChange,
}: {
  recurrence: RecurrenceRule | null;
  onChange: (rule: RecurrenceRule | null) => void;
}) {
  const [enabled, setEnabled] = useState(!!recurrence);

  const handleToggle = (checked: boolean) => {
    setEnabled(checked);
    if (checked && !recurrence) {
      onChange({
        frequency: 'weekly',
        interval: 1,
        days_of_week: null,
        day_of_month: null,
        month_of_year: null,
        end_type: 'never',
        end_date: null,
        count: null,
      });
    } else if (!checked) {
      onChange(null);
    }
  };

  const updateField = <K extends keyof RecurrenceRule>(
    field: K,
    value: RecurrenceRule[K]
  ) => {
    if (recurrence) {
      onChange({ ...recurrence, [field]: value });
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Checkbox
          id="recurrence-enabled"
          checked={enabled}
          onCheckedChange={handleToggle}
        />
        <Label htmlFor="recurrence-enabled">Repeat</Label>
      </div>

      {enabled && recurrence && (
        <div className="pl-6 space-y-3">
          <div className="flex items-center gap-2">
            <span className="text-sm">Every</span>
            <Input
              type="number"
              min={1}
              value={recurrence.interval}
              onChange={(e) => updateField('interval', parseInt(e.target.value) || 1)}
              className="w-16 h-8"
            />
            <Select
              value={recurrence.frequency}
              onValueChange={(v) => updateField('frequency', v as RecurrenceFrequency)}
            >
              <SelectTrigger className="w-28 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">day(s)</SelectItem>
                <SelectItem value="weekly">week(s)</SelectItem>
                <SelectItem value="monthly">month(s)</SelectItem>
                <SelectItem value="yearly">year(s)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {recurrence.frequency === 'weekly' && (
            <div className="flex flex-wrap gap-1">
              {DAYS_OF_WEEK.map(({ value, label }) => {
                const selected = recurrence.days_of_week?.includes(value) ?? false;
                return (
                  <Button
                    key={value}
                    type="button"
                    variant={selected ? 'default' : 'outline'}
                    size="sm"
                    className="w-10 h-8"
                    onClick={() => {
                      const current = recurrence.days_of_week || [];
                      const updated = selected
                        ? current.filter((d) => d !== value)
                        : [...current, value];
                      updateField('days_of_week', updated.length > 0 ? updated : null);
                    }}
                  >
                    {label}
                  </Button>
                );
              })}
            </div>
          )}

          <div className="flex items-center gap-2">
            <span className="text-sm">Ends</span>
            <Select
              value={recurrence.end_type}
              onValueChange={(v) => updateField('end_type', v as RecurrenceEndType)}
            >
              <SelectTrigger className="w-28 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="never">Never</SelectItem>
                <SelectItem value="until">On date</SelectItem>
                <SelectItem value="count">After</SelectItem>
              </SelectContent>
            </Select>

            {recurrence.end_type === 'until' && (
              <Input
                type="date"
                value={recurrence.end_date || ''}
                onChange={(e) => updateField('end_date', e.target.value || null)}
                className="w-40 h-8"
              />
            )}

            {recurrence.end_type === 'count' && (
              <>
                <Input
                  type="number"
                  min={1}
                  value={recurrence.count || 1}
                  onChange={(e) => updateField('count', parseInt(e.target.value) || 1)}
                  className="w-16 h-8"
                />
                <span className="text-sm">occurrences</span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function CreateEventDialog({
  open,
  onClose,
  onSave,
  editEvent,
  calendars,
  defaultCalendarId,
  defaultDateTime,
}: CreateEventDialogProps) {
  const [formData, setFormData] = useState<EventFormData>(() =>
    editEvent 
      ? eventToFormData(editEvent) 
      : getDefaultFormData(defaultCalendarId, defaultDateTime)
  );
  const [showMoreOptions, setShowMoreOptions] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [newAttendeeEmail, setNewAttendeeEmail] = useState('');

  // Reset form when dialog opens/closes or edit event changes
  useEffect(() => {
    if (open) {
      setFormData(
        editEvent 
          ? eventToFormData(editEvent) 
          : getDefaultFormData(defaultCalendarId, defaultDateTime)
      );
      setShowMoreOptions(!!editEvent);
    }
  }, [open, editEvent, defaultCalendarId, defaultDateTime]);

  const updateField = <K extends keyof EventFormData>(field: K, value: EventFormData[K]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleAddAttendee = () => {
    if (newAttendeeEmail && newAttendeeEmail.includes('@')) {
      updateField('attendees', [
        ...formData.attendees,
        { email: newAttendeeEmail, optional: false, response: 'needs-action' },
      ]);
      setNewAttendeeEmail('');
    }
  };

  const handleRemoveAttendee = (index: number) => {
    updateField(
      'attendees',
      formData.attendees.filter((_, i) => i !== index)
    );
  };

  const handleAddReminder = () => {
    updateField('reminders', [
      ...formData.reminders,
      { minutes_before: 30, type: 'notification' },
    ]);
  };

  const handleRemoveReminder = (index: number) => {
    updateField(
      'reminders',
      formData.reminders.filter((_, i) => i !== index)
    );
  };

  const handleUpdateReminder = (index: number, minutes: number) => {
    const updated = [...formData.reminders];
    updated[index] = { ...updated[index], minutes_before: minutes };
    updateField('reminders', updated);
  };

  const handleSubmit = async () => {
    if (!formData.title.trim()) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave(formData, !!editEvent, editEvent?.event_id);
      onClose();
    } finally {
      setIsSaving(false);
    }
  };

  const isEdit = !!editEvent;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Event' : 'Create New Event'}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Title */}
          <div className="space-y-2">
            <Label htmlFor="title">Title *</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => updateField('title', e.target.value)}
              placeholder="Enter event title..."
            />
          </div>

          {/* Calendar */}
          <div className="space-y-2">
            <Label>Calendar</Label>
            <Select
              value={formData.calendar_id}
              onValueChange={(v) => updateField('calendar_id', v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {calendars.map((cal) => (
                  <SelectItem key={cal.calendar_id} value={cal.calendar_id}>
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-sm"
                        style={{ backgroundColor: cal.color }}
                      />
                      {cal.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* All day checkbox */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="all-day"
              checked={formData.all_day}
              onCheckedChange={(checked) => updateField('all_day', !!checked)}
            />
            <Label htmlFor="all-day">All day</Label>
          </div>

          {/* Start date/time */}
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-2">
              <Label>Start *</Label>
              <Input
                type="date"
                value={formData.start_date}
                onChange={(e) => updateField('start_date', e.target.value)}
              />
            </div>
            {!formData.all_day && (
              <div className="space-y-2">
                <Label>&nbsp;</Label>
                <Input
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => updateField('start_time', e.target.value)}
                />
              </div>
            )}
          </div>

          {/* End date/time */}
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-2">
              <Label>End *</Label>
              <Input
                type="date"
                value={formData.end_date}
                onChange={(e) => updateField('end_date', e.target.value)}
              />
            </div>
            {!formData.all_day && (
              <div className="space-y-2">
                <Label>&nbsp;</Label>
                <Input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => updateField('end_time', e.target.value)}
                />
              </div>
            )}
          </div>

          {/* Timezone */}
          <div className="space-y-2">
            <Label>Timezone</Label>
            <Select
              value={formData.timezone}
              onValueChange={(v) => updateField('timezone', v)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIMEZONE_OPTIONS.map((tz) => (
                  <SelectItem key={tz} value={tz}>
                    {tz}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Separator />

          {/* More options toggle */}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="w-full"
            onClick={() => setShowMoreOptions(!showMoreOptions)}
          >
            {showMoreOptions ? (
              <>
                <ChevronUp className="h-4 w-4 mr-2" />
                Less options
              </>
            ) : (
              <>
                <ChevronDown className="h-4 w-4 mr-2" />
                More options
              </>
            )}
          </Button>

          {showMoreOptions && (
            <div className="space-y-4">
              {/* Location */}
              <div className="space-y-2">
                <Label>Location</Label>
                <Input
                  value={formData.location}
                  onChange={(e) => updateField('location', e.target.value)}
                  placeholder="Enter location..."
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => updateField('description', e.target.value)}
                  placeholder="Enter description..."
                  rows={3}
                />
              </div>

              {/* Video link */}
              <div className="space-y-2">
                <Label>Video Conference Link</Label>
                <Input
                  value={formData.conference_link}
                  onChange={(e) => updateField('conference_link', e.target.value)}
                  placeholder="https://meet.google.com/..."
                />
              </div>

              {/* Recurrence */}
              <RecurrenceEditor
                recurrence={formData.recurrence}
                onChange={(rule) => updateField('recurrence', rule)}
              />

              <Separator />

              {/* Reminders */}
              <div className="space-y-2">
                <Label>Reminders</Label>
                {formData.reminders.map((reminder, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <Select
                      value={String(reminder.minutes_before)}
                      onValueChange={(v) => handleUpdateReminder(index, parseInt(v))}
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {REMINDER_OPTIONS.map((opt) => (
                          <SelectItem key={opt.value} value={String(opt.value)}>
                            {opt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handleRemoveReminder(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleAddReminder}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  Add reminder
                </Button>
              </div>

              <Separator />

              {/* Attendees */}
              <div className="space-y-2">
                <Label>Attendees</Label>
                {formData.attendees.map((attendee, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <span className="flex-1 text-sm truncate">{attendee.email}</span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handleRemoveAttendee(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                <div className="flex items-center gap-2">
                  <Input
                    type="email"
                    value={newAttendeeEmail}
                    onChange={(e) => setNewAttendeeEmail(e.target.value)}
                    placeholder="email@example.com"
                    className="flex-1"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddAttendee();
                      }
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleAddAttendee}
                    disabled={!newAttendeeEmail.includes('@')}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <Separator />

              {/* Color */}
              <div className="space-y-2">
                <Label>Color</Label>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={cn(
                      'w-8 h-8 rounded border-2 flex items-center justify-center text-xs',
                      !formData.color && 'border-primary'
                    )}
                    onClick={() => updateField('color', null)}
                    title="Default"
                  >
                    ✓
                  </button>
                  {COLOR_PRESETS.map(({ name, value }) => (
                    <button
                      key={value}
                      type="button"
                      className={cn(
                        'w-8 h-8 rounded border-2',
                        formData.color === value ? 'border-primary' : 'border-transparent'
                      )}
                      style={{ backgroundColor: value }}
                      onClick={() => updateField('color', value)}
                      title={name}
                    />
                  ))}
                </div>
              </div>

              {/* Status */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(v) => updateField('status', v as EventStatus)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="confirmed">Confirmed</SelectItem>
                      <SelectItem value="tentative">Tentative</SelectItem>
                      <SelectItem value="cancelled">Cancelled</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Visibility</Label>
                  <Select
                    value={formData.visibility}
                    onValueChange={(v) => updateField('visibility', v as EventVisibility)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">Default</SelectItem>
                      <SelectItem value="public">Public</SelectItem>
                      <SelectItem value="private">Private</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isSaving || !formData.title.trim()}>
            {isSaving ? 'Saving...' : isEdit ? 'Update Event' : 'Create Event'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
