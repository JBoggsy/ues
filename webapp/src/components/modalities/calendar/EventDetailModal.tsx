/**
 * Event detail modal component.
 * Shows full event information with edit/delete options.
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Separator } from '@/components/ui/separator';
import {
  Calendar,
  MapPin,
  FileText,
  Users,
  Bell,
  Paperclip,
  Link,
  Repeat,
  Edit2,
  Copy,
  Trash2,
  ChevronDown,
} from 'lucide-react';
import type { CalendarEvent, Calendar as CalendarType, RecurrenceScope } from './types';

interface EventDetailModalProps {
  /** Event to display */
  event: CalendarEvent | null;
  /** Calendar the event belongs to */
  calendar: CalendarType | null;
  /** Whether modal is open */
  open: boolean;
  /** Callback when modal closes */
  onClose: () => void;
  /** Callback to edit the event */
  onEdit: (event: CalendarEvent) => void;
  /** Callback to duplicate the event */
  onDuplicate: (event: CalendarEvent) => void;
  /** Callback to delete the event */
  onDelete: (event: CalendarEvent, scope: RecurrenceScope) => void;
}

/**
 * Format date/time range for display.
 */
function formatDateTimeRange(event: CalendarEvent): string {
  const start = new Date(event.start);
  const end = new Date(event.end);

  if (event.all_day) {
    const isSameDay = start.toDateString() === end.toDateString();
    if (isSameDay) {
      return start.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      });
    }
    return `${start.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
    })} - ${end.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    })}`;
  }

  const isSameDay = start.toDateString() === end.toDateString();
  const dateStr = start.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  });
  const startTime = start.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
  const endTime = end.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });

  if (isSameDay) {
    return `${dateStr}\n${startTime} - ${endTime}`;
  }

  return `${start.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric' 
  })} ${startTime} - ${end.toLocaleDateString('en-US', { 
    month: 'short', 
    day: 'numeric' 
  })} ${endTime}`;
}

/**
 * Format recurrence rule for display.
 */
function formatRecurrence(event: CalendarEvent): string | null {
  if (!event.recurrence) return null;

  const { frequency, interval, days_of_week, end_type, end_date, count } = event.recurrence;

  let base = '';
  if (interval === 1) {
    base = frequency.charAt(0).toUpperCase() + frequency.slice(1);
  } else {
    base = `Every ${interval} ${frequency.replace('ly', '')}s`;
  }

  if (days_of_week && days_of_week.length > 0) {
    const dayNames = days_of_week.map(d => 
      d.charAt(0).toUpperCase() + d.slice(1, 3)
    ).join(', ');
    base += ` on ${dayNames}`;
  }

  if (end_type === 'until' && end_date) {
    base += `, until ${new Date(end_date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })}`;
  } else if (end_type === 'count' && count) {
    base += `, ${count} times`;
  }

  return base;
}

/**
 * Format attendee response status.
 */
function getResponseIcon(response: string): string {
  switch (response) {
    case 'accepted':
      return '✓';
    case 'declined':
      return '✗';
    case 'tentative':
      return '?';
    default:
      return '○';
  }
}

/**
 * Format reminder for display.
 */
function formatReminder(minutes: number, type: string): string {
  let timeStr = '';
  if (minutes < 60) {
    timeStr = `${minutes} minute${minutes !== 1 ? 's' : ''}`;
  } else if (minutes < 1440) {
    const hours = Math.floor(minutes / 60);
    timeStr = `${hours} hour${hours !== 1 ? 's' : ''}`;
  } else {
    const days = Math.floor(minutes / 1440);
    timeStr = `${days} day${days !== 1 ? 's' : ''}`;
  }

  return `${timeStr} before (${type})`;
}

export function EventDetailModal({
  event,
  calendar,
  open,
  onClose,
  onEdit,
  onDuplicate,
  onDelete,
}: EventDetailModalProps) {
  const [deleteMenuOpen, setDeleteMenuOpen] = useState(false);

  if (!event) return null;

  const color = event.color || calendar?.color || '#4285f4';
  const recurrenceText = formatRecurrence(event);
  const isRecurring = !!event.recurrence;

  const handleDelete = (scope: RecurrenceScope) => {
    setDeleteMenuOpen(false);
    onDelete(event, scope);
  };

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div
            className="h-2 -mx-6 -mt-6 mb-2 rounded-t-lg"
            style={{ backgroundColor: color }}
          />
          <DialogTitle className="text-xl">{event.title}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Date/Time */}
          <div className="flex items-start gap-3">
            <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div className="whitespace-pre-line">
              {formatDateTimeRange(event)}
            </div>
          </div>

          {/* Location */}
          {event.location && (
            <div className="flex items-start gap-3">
              <MapPin className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>{event.location}</div>
            </div>
          )}

          {/* Video conference */}
          {event.conference_link && (
            <div className="flex items-start gap-3">
              <Link className="h-5 w-5 text-muted-foreground mt-0.5" />
              <a
                href={event.conference_link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline truncate"
              >
                {event.conference_link}
              </a>
            </div>
          )}

          {/* Description */}
          {event.description && (
            <div className="flex items-start gap-3">
              <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div className="text-sm whitespace-pre-wrap">{event.description}</div>
            </div>
          )}

          {/* Recurrence */}
          {recurrenceText && (
            <div className="flex items-start gap-3">
              <Repeat className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div>{recurrenceText}</div>
            </div>
          )}

          {/* Attendees */}
          {event.attendees.length > 0 && (
            <>
              <Separator />
              <div className="flex items-start gap-3">
                <Users className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium mb-2">Attendees</div>
                  <div className="space-y-1">
                    {event.attendees.map((attendee, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm">
                        <span className="w-4 text-center">
                          {getResponseIcon(attendee.response)}
                        </span>
                        <span>
                          {attendee.display_name || attendee.email}
                          {attendee.optional && (
                            <span className="text-muted-foreground ml-1">(optional)</span>
                          )}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Reminders */}
          {event.reminders.length > 0 && (
            <>
              <Separator />
              <div className="flex items-start gap-3">
                <Bell className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium mb-2">Reminders</div>
                  <div className="space-y-1 text-sm">
                    {event.reminders.map((reminder, i) => (
                      <div key={i}>
                        {formatReminder(reminder.minutes_before, reminder.type)}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Attachments */}
          {event.attachments.length > 0 && (
            <>
              <Separator />
              <div className="flex items-start gap-3">
                <Paperclip className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div className="flex-1">
                  <div className="font-medium mb-2">Attachments</div>
                  <div className="space-y-1 text-sm">
                    {event.attachments.map((attachment, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span>📎</span>
                        <span>{attachment.filename}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Calendar info */}
          <Separator />
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: calendar?.color || color }}
            />
            <span>{calendar?.name || 'Calendar'}</span>
            {event.status !== 'confirmed' && (
              <span className="ml-auto capitalize">({event.status})</span>
            )}
          </div>
        </div>

        <DialogFooter className="mt-4">
          <div className="flex items-center gap-2 w-full">
            <Button variant="outline" size="sm" onClick={() => onEdit(event)}>
              <Edit2 className="h-4 w-4 mr-1" />
              Edit
            </Button>
            <Button variant="outline" size="sm" onClick={() => onDuplicate(event)}>
              <Copy className="h-4 w-4 mr-1" />
              Duplicate
            </Button>

            {isRecurring ? (
              <DropdownMenu open={deleteMenuOpen} onOpenChange={setDeleteMenuOpen}>
                <DropdownMenuTrigger asChild>
                  <Button variant="destructive" size="sm">
                    <Trash2 className="h-4 w-4 mr-1" />
                    Delete
                    <ChevronDown className="h-3 w-3 ml-1" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem onClick={() => handleDelete('this')}>
                    This event only
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleDelete('this_and_future')}>
                    This and future events
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleDelete('all')}>
                    All events in series
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleDelete('this')}
              >
                <Trash2 className="h-4 w-4 mr-1" />
                Delete
              </Button>
            )}

            <Button variant="ghost" size="sm" className="ml-auto" onClick={onClose}>
              Close
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
