/**
 * Month view component for the calendar.
 * Displays a traditional monthly grid with event chips.
 */
import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { CalendarEvent, Calendar, TimeSlot } from './types';

interface MonthViewProps {
  /** Current date to display (determines which month) */
  currentDate: Date;
  /** All events to display */
  events: CalendarEvent[];
  /** Map of calendars for color lookup */
  calendars: Record<string, Calendar>;
  /** IDs of visible calendars */
  visibleCalendarIds: Set<string>;
  /** Callback when an event is clicked */
  onEventClick: (event: CalendarEvent) => void;
  /** Callback when a time slot is clicked (for creating events) */
  onTimeSlotClick: (slot: TimeSlot) => void;
}

/**
 * Get all days to display in the month grid.
 * Includes days from previous and next month to fill the grid.
 */
function getMonthDays(date: Date): Date[] {
  const year = date.getFullYear();
  const month = date.getMonth();
  
  // First day of the month
  const firstDay = new Date(year, month, 1);
  // Last day of the month
  const lastDay = new Date(year, month + 1, 0);
  
  // Start from the Sunday before (or on) the first day
  const startDate = new Date(firstDay);
  startDate.setDate(startDate.getDate() - startDate.getDay());
  
  // End on the Saturday after (or on) the last day
  const endDate = new Date(lastDay);
  const daysToAdd = 6 - endDate.getDay();
  endDate.setDate(endDate.getDate() + daysToAdd);
  
  const days: Date[] = [];
  const current = new Date(startDate);
  
  while (current <= endDate) {
    days.push(new Date(current));
    current.setDate(current.getDate() + 1);
  }
  
  return days;
}

/**
 * Check if a date is today.
 */
function isToday(date: Date): boolean {
  const today = new Date();
  return (
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate()
  );
}

/**
 * Check if a date is in the current display month.
 */
function isCurrentMonth(date: Date, currentDate: Date): boolean {
  return (
    date.getFullYear() === currentDate.getFullYear() &&
    date.getMonth() === currentDate.getMonth()
  );
}

/**
 * Get events for a specific day.
 */
function getEventsForDay(
  day: Date,
  events: CalendarEvent[],
  visibleCalendarIds: Set<string>
): CalendarEvent[] {
  const dayStart = new Date(day);
  dayStart.setHours(0, 0, 0, 0);
  const dayEnd = new Date(day);
  dayEnd.setHours(23, 59, 59, 999);

  return events.filter((event) => {
    // Only show events from visible calendars
    if (!visibleCalendarIds.has(event.calendar_id)) {
      return false;
    }

    const eventStart = new Date(event.start);
    const eventEnd = new Date(event.end);

    // Event overlaps with this day
    return eventStart <= dayEnd && eventEnd >= dayStart;
  }).sort((a, b) => {
    // Sort all-day events first, then by start time
    if (a.all_day && !b.all_day) return -1;
    if (!a.all_day && b.all_day) return 1;
    return new Date(a.start).getTime() - new Date(b.start).getTime();
  });
}

/**
 * Format event time for display.
 */
function formatEventTime(event: CalendarEvent): string {
  if (event.all_day) {
    return 'All day';
  }
  const start = new Date(event.start);
  return start.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  });
}

/**
 * Single day cell in the month grid.
 */
function DayCell({
  date,
  events,
  calendars,
  isCurrentMonthDay,
  onEventClick,
  onTimeSlotClick,
}: {
  date: Date;
  events: CalendarEvent[];
  calendars: Record<string, Calendar>;
  isCurrentMonthDay: boolean;
  onEventClick: (event: CalendarEvent) => void;
  onTimeSlotClick: (slot: TimeSlot) => void;
}) {
  const maxEventsToShow = 3;
  const visibleEvents = events.slice(0, maxEventsToShow);
  const hiddenCount = events.length - maxEventsToShow;

  const handleCellClick = (e: React.MouseEvent) => {
    // Only trigger if clicking on the cell itself, not an event
    if (e.target === e.currentTarget || (e.target as HTMLElement).classList.contains('day-cell-inner')) {
      onTimeSlotClick({ date });
    }
  };

  return (
    <div
      className={cn(
        'min-h-[100px] border-b border-r p-1 cursor-pointer hover:bg-accent/30 transition-colors',
        !isCurrentMonthDay && 'bg-muted/30'
      )}
      onClick={handleCellClick}
    >
      {/* Day number */}
      <div className="flex justify-end mb-1">
        <span
          className={cn(
            'w-6 h-6 flex items-center justify-center text-sm rounded-full',
            isToday(date) && 'bg-primary text-primary-foreground font-semibold',
            !isCurrentMonthDay && 'text-muted-foreground'
          )}
        >
          {date.getDate()}
        </span>
      </div>

      {/* Events */}
      <div className="day-cell-inner space-y-0.5">
        {visibleEvents.map((event) => {
          const calendar = calendars[event.calendar_id];
          const color = event.color || calendar?.color || '#4285f4';

          return (
            <button
              key={event.event_id}
              className={cn(
                'w-full text-left px-1.5 py-0.5 rounded text-xs truncate',
                'hover:opacity-80 transition-opacity'
              )}
              style={{
                backgroundColor: color,
                color: '#fff',
              }}
              onClick={(e) => {
                e.stopPropagation();
                onEventClick(event);
              }}
              title={`${event.title} - ${formatEventTime(event)}`}
            >
              {event.all_day ? (
                event.title
              ) : (
                <>
                  <span className="font-medium">{formatEventTime(event)}</span>
                  {' '}
                  {event.title}
                </>
              )}
            </button>
          );
        })}

        {hiddenCount > 0 && (
          <button
            className="w-full text-left px-1.5 py-0.5 text-xs text-muted-foreground hover:text-foreground"
            onClick={(e) => {
              e.stopPropagation();
              // Could open a popover showing all events
              onTimeSlotClick({ date });
            }}
          >
            +{hiddenCount} more
          </button>
        )}
      </div>
    </div>
  );
}

export function MonthView({
  currentDate,
  events,
  calendars,
  visibleCalendarIds,
  onEventClick,
  onTimeSlotClick,
}: MonthViewProps) {
  // Get all days to display in the grid
  const days = useMemo(() => getMonthDays(currentDate), [currentDate]);

  // Group days into weeks for rendering
  const weeks = useMemo(() => {
    const result: Date[][] = [];
    for (let i = 0; i < days.length; i += 7) {
      result.push(days.slice(i, i + 7));
    }
    return result;
  }, [days]);

  // Pre-compute events for each day for better performance
  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const day of days) {
      const key = day.toISOString().split('T')[0];
      map.set(key, getEventsForDay(day, events, visibleCalendarIds));
    }
    return map;
  }, [days, events, visibleCalendarIds]);

  return (
    <div className="flex flex-col h-full">
      {/* Day headers */}
      <div className="grid grid-cols-7 border-b bg-muted/50">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
          <div
            key={day}
            className="py-2 text-center text-sm font-medium text-muted-foreground border-r last:border-r-0"
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="flex-1 overflow-auto">
        <div className="grid grid-cols-7">
          {weeks.map((week) =>
            week.map((day) => {
              const key = day.toISOString().split('T')[0];
              const dayEvents = eventsByDay.get(key) || [];

              return (
                <DayCell
                  key={key}
                  date={day}
                  events={dayEvents}
                  calendars={calendars}
                  isCurrentMonthDay={isCurrentMonth(day, currentDate)}
                  onEventClick={onEventClick}
                  onTimeSlotClick={onTimeSlotClick}
                />
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
