/**
 * Calendar settings dialog component.
 * Allows managing calendars (create, edit, delete, visibility, colors).
 */
import { useState } from 'react';
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
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Edit2, Trash2, Plus, Save, X } from 'lucide-react';
import type { Calendar } from './types';
import { cn } from '@/lib/utils';

interface CalendarSettingsDialogProps {
  /** Whether dialog is open */
  open: boolean;
  /** Callback when dialog closes */
  onClose: () => void;
  /** List of calendars */
  calendars: Calendar[];
  /** Default calendar ID */
  defaultCalendarId: string;
  /** User's timezone */
  userTimezone: string;
  /** Callback to create a calendar */
  onCreateCalendar: (name: string, color: string) => Promise<void>;
  /** Callback to update a calendar */
  onUpdateCalendar: (calendarId: string, name: string, color: string) => Promise<void>;
  /** Callback to delete a calendar */
  onDeleteCalendar: (calendarId: string) => Promise<void>;
  /** Callback to set default calendar */
  onSetDefaultCalendar: (calendarId: string) => Promise<void>;
}

const COLOR_PRESETS = [
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

const TIMEZONE_OPTIONS = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Anchorage',
  'Pacific/Honolulu',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Moscow',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Australia/Sydney',
];

/**
 * Single calendar item in the settings list.
 */
function CalendarSettingsItem({
  calendar,
  isDefault,
  onEdit,
  onDelete,
  onSetDefault,
}: {
  calendar: Calendar;
  isDefault: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onSetDefault: () => void;
}) {
  return (
    <div className="flex items-center gap-3 py-2 px-3 rounded-md hover:bg-accent/50 group">
      <div
        className="w-4 h-4 rounded-sm flex-shrink-0"
        style={{ backgroundColor: calendar.color }}
      />
      <span className="flex-1 truncate">{calendar.name}</span>
      {isDefault && (
        <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
          Default
        </span>
      )}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        {!isDefault && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={onSetDefault}
          >
            Set default
          </Button>
        )}
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onEdit}>
          <Edit2 className="h-3.5 w-3.5" />
        </Button>
        {!isDefault && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive hover:text-destructive"
            onClick={onDelete}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * Calendar edit/create form.
 */
function CalendarForm({
  initialName,
  initialColor,
  onSave,
  onCancel,
  isNew,
}: {
  initialName: string;
  initialColor: string;
  onSave: (name: string, color: string) => void;
  onCancel: () => void;
  isNew: boolean;
}) {
  const [name, setName] = useState(initialName);
  const [color, setColor] = useState(initialColor);

  return (
    <div className="space-y-4 p-4 border rounded-md bg-muted/30">
      <div className="space-y-2">
        <Label>Calendar Name</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter calendar name..."
          autoFocus
        />
      </div>

      <div className="space-y-2">
        <Label>Color</Label>
        <div className="flex flex-wrap gap-2">
          {COLOR_PRESETS.map(({ name: colorName, value }) => (
            <button
              key={value}
              type="button"
              className={cn(
                'w-8 h-8 rounded border-2',
                color === value ? 'border-primary ring-2 ring-primary/30' : 'border-transparent'
              )}
              style={{ backgroundColor: value }}
              onClick={() => setColor(value)}
              title={colorName}
            />
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm" onClick={onCancel}>
          <X className="h-4 w-4 mr-1" />
          Cancel
        </Button>
        <Button size="sm" onClick={() => onSave(name, color)} disabled={!name.trim()}>
          <Save className="h-4 w-4 mr-1" />
          {isNew ? 'Create' : 'Save'}
        </Button>
      </div>
    </div>
  );
}

export function CalendarSettingsDialog({
  open,
  onClose,
  calendars,
  defaultCalendarId,
  userTimezone,
  onCreateCalendar,
  onUpdateCalendar,
  onDeleteCalendar,
  onSetDefaultCalendar,
}: CalendarSettingsDialogProps) {
  const [editingCalendarId, setEditingCalendarId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleCreateCalendar = async (name: string, color: string) => {
    setIsLoading(true);
    try {
      await onCreateCalendar(name, color);
      setIsCreating(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateCalendar = async (name: string, color: string) => {
    if (!editingCalendarId) return;
    setIsLoading(true);
    try {
      await onUpdateCalendar(editingCalendarId, name, color);
      setEditingCalendarId(null);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteCalendar = async (calendarId: string) => {
    if (!confirm('Are you sure you want to delete this calendar? All events in this calendar will also be deleted.')) {
      return;
    }
    setIsLoading(true);
    try {
      await onDeleteCalendar(calendarId);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetDefault = async (calendarId: string) => {
    setIsLoading(true);
    try {
      await onSetDefaultCalendar(calendarId);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Calendar Settings</DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* My Calendars section */}
          <div className="space-y-2">
            <h3 className="text-sm font-semibold">My Calendars</h3>
            <Separator />

            <div className="space-y-1">
              {calendars.map((calendar) => (
                <div key={calendar.calendar_id}>
                  {editingCalendarId === calendar.calendar_id ? (
                    <CalendarForm
                      initialName={calendar.name}
                      initialColor={calendar.color}
                      onSave={handleUpdateCalendar}
                      onCancel={() => setEditingCalendarId(null)}
                      isNew={false}
                    />
                  ) : (
                    <CalendarSettingsItem
                      calendar={calendar}
                      isDefault={calendar.calendar_id === defaultCalendarId}
                      onEdit={() => setEditingCalendarId(calendar.calendar_id)}
                      onDelete={() => handleDeleteCalendar(calendar.calendar_id)}
                      onSetDefault={() => handleSetDefault(calendar.calendar_id)}
                    />
                  )}
                </div>
              ))}
            </div>

            {calendars.length === 0 && !isCreating && (
              <p className="text-sm text-muted-foreground text-center py-4">
                No calendars. Create one to get started.
              </p>
            )}

            {isCreating ? (
              <CalendarForm
                initialName=""
                initialColor="#4285f4"
                onSave={handleCreateCalendar}
                onCancel={() => setIsCreating(false)}
                isNew
              />
            ) : (
              <Button
                variant="outline"
                size="sm"
                className="w-full mt-2"
                onClick={() => setIsCreating(true)}
                disabled={isLoading}
              >
                <Plus className="h-4 w-4 mr-2" />
                Create New Calendar
              </Button>
            )}
          </div>

          <Separator />

          {/* Default settings section */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Default Settings</h3>

            <div className="space-y-2">
              <Label>Default Calendar</Label>
              <Select
                value={defaultCalendarId}
                onValueChange={handleSetDefault}
                disabled={isLoading}
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

            <div className="space-y-2">
              <Label>User Timezone</Label>
              <Select value={userTimezone} disabled>
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
              <p className="text-xs text-muted-foreground">
                Timezone is set via the Time modality
              </p>
            </div>
          </div>
        </div>

        <DialogFooter className="mt-4">
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
