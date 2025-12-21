/**
 * Week view component for the calendar.
 * Displays a week/3-day column view with hourly rows.
 */
import { useMemo, useRef } from 'react';
import { cn } from '@/lib/utils';
import type { CalendarEvent, Calendar, TimeSlot } from './types';

interface WeekViewProps {
  /** Current date to display (determines which week/days) */
  currentDate: Date;
  /** Number of days to show (7 for week, 3 for 3-day) */
  daysToShow: 7 | 3;
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

// Hours to display (6 AM to 10 PM by default)
const START_HOUR = 6;
const END_HOUR = 22;
const HOUR_HEIGHT = 60; // pixels per hour

/**
 * Get the days to display based on current date and view mode.
 */
function getDaysToShow(date: Date, count: 7 | 3): Date[] {
  const days: Date[] = [];
  
  if (count === 7) {
    // Week view: Start from Sunday of the current week
    const startOfWeek = new Date(date);
    startOfWeek.setDate(date.getDate() - date.getDay());
    
    for (let i = 0; i < 7; i++) {
      const day = new Date(startOfWeek);
      day.setDate(startOfWeek.getDate() + i);
      days.push(day);
    }
  } else {
    // 3-day view: Start from current date
    for (let i = 0; i < 3; i++) {
      const day = new Date(date);
      day.setDate(date.getDate() + i);
      days.push(day);
    }
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
    if (!visibleCalendarIds.has(event.calendar_id)) {
      return false;
    }

    const eventStart = new Date(event.start);
    const eventEnd = new Date(event.end);

    return eventStart <= dayEnd && eventEnd >= dayStart;
  });
}

/**
 * Get all-day events for a day.
 */
function getAllDayEvents(events: CalendarEvent[]): CalendarEvent[] {
  return events.filter((e) => e.all_day);
}

/**
 * Get timed events for a day.
 */
function getTimedEvents(events: CalendarEvent[]): CalendarEvent[] {
  return events.filter((e) => !e.all_day);
}

/**
 * Calculate position and height of an event in the time grid.
 */
function getEventPosition(
  event: CalendarEvent,
  day: Date
): { top: number; height: number } {
  const eventStart = new Date(event.start);
  const eventEnd = new Date(event.end);

  // Clamp event to the day boundaries
  const dayStart = new Date(day);
  dayStart.setHours(START_HOUR, 0, 0, 0);
  const dayEnd = new Date(day);
  dayEnd.setHours(END_HOUR, 0, 0, 0);

  const clampedStart = new Date(Math.max(eventStart.getTime(), dayStart.getTime()));
  const clampedEnd = new Date(Math.min(eventEnd.getTime(), dayEnd.getTime()));

  const startHour = clampedStart.getHours() + clampedStart.getMinutes() / 60;
  const endHour = clampedEnd.getHours() + clampedEnd.getMinutes() / 60;

  const top = (startHour - START_HOUR) * HOUR_HEIGHT;
  const height = Math.max((endHour - startHour) * HOUR_HEIGHT, 20); // Min height of 20px

  return { top, height };
}

/**
 * Format time for display.
 */
function formatTime(hour: number): string {
  const h = hour % 12 || 12;
  const ampm = hour < 12 ? 'AM' : 'PM';
  return `${h} ${ampm}`;
}

/**
 * Format event time range.
 */
function formatEventTimeRange(event: CalendarEvent): string {
  const start = new Date(event.start);
  const end = new Date(event.end);
  const startStr = start.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  });
  const endStr = end.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  });
  return `${startStr} - ${endStr}`;
}

/**
 * Time column showing hour labels.
 */
function TimeColumn() {
  const hours = [];
  for (let h = START_HOUR; h <= END_HOUR; h++) {
    hours.push(h);
  }

  return (
    <div className="w-16 flex-shrink-0 border-r">
      {/* Empty space for all-day header */}
      <div className="h-10 border-b" />
      
      {/* Hour labels */}
      <div className="relative">
        {hours.map((hour) => (
          <div
            key={hour}
            className="h-[60px] border-b text-xs text-muted-foreground pr-2 text-right"
            style={{ lineHeight: '60px' }}
          >
            {formatTime(hour)}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Day column with events.
 */
function DayColumn({
  date,
  events,
  calendars,
  onEventClick,
  onTimeSlotClick,
}: {
  date: Date;
  events: CalendarEvent[];
  calendars: Record<string, Calendar>;
  onEventClick: (event: CalendarEvent) => void;
  onTimeSlotClick: (slot: TimeSlot) => void;
}) {
  const allDayEvents = getAllDayEvents(events);
  const timedEvents = getTimedEvents(events);

  const handleTimeSlotClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const hour = Math.floor(y / HOUR_HEIGHT) + START_HOUR;
    const minute = Math.floor((y % HOUR_HEIGHT) / HOUR_HEIGHT * 60);
    
    onTimeSlotClick({
      date,
      hour,
      minute: Math.round(minute / 15) * 15, // Round to nearest 15 min
    });
  };

  return (
    <div className="flex-1 min-w-[100px] border-r last:border-r-0">
      {/* Day header */}
      <div
        className={cn(
          'h-10 border-b flex flex-col items-center justify-center',
          isToday(date) && 'bg-primary/10'
        )}
      >
        <span className="text-xs text-muted-foreground">
          {date.toLocaleDateString('en-US', { weekday: 'short' })}
        </span>
        <span
          className={cn(
            'text-sm font-medium',
            isToday(date) && 'bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center'
          )}
        >
          {date.getDate()}
        </span>
      </div>

      {/* All-day events area */}
      {allDayEvents.length > 0 && (
        <div className="border-b bg-muted/30 p-1 space-y-0.5 max-h-20 overflow-auto">
          {allDayEvents.map((event) => {
            const calendar = calendars[event.calendar_id];
            const color = event.color || calendar?.color || '#4285f4';

            return (
              <button
                key={event.event_id}
                className="w-full text-left px-1.5 py-0.5 rounded text-xs truncate hover:opacity-80"
                style={{ backgroundColor: color, color: '#fff' }}
                onClick={() => onEventClick(event)}
                title={event.title}
              >
                {event.title}
              </button>
            );
          })}
        </div>
      )}

      {/* Time grid */}
      <div
        className="relative cursor-pointer"
        style={{ height: `${(END_HOUR - START_HOUR + 1) * HOUR_HEIGHT}px` }}
        onClick={handleTimeSlotClick}
      >
        {/* Hour grid lines */}
        {Array.from({ length: END_HOUR - START_HOUR + 1 }).map((_, i) => (
          <div
            key={i}
            className="absolute w-full border-b border-dashed border-muted"
            style={{ top: `${i * HOUR_HEIGHT}px`, height: `${HOUR_HEIGHT}px` }}
          />
        ))}

        {/* Events */}
        {timedEvents.map((event) => {
          const { top, height } = getEventPosition(event, date);
          const calendar = calendars[event.calendar_id];
          const color = event.color || calendar?.color || '#4285f4';

          return (
            <button
              key={event.event_id}
              className="absolute left-1 right-1 px-1.5 py-0.5 rounded text-xs text-white overflow-hidden hover:opacity-90 transition-opacity"
              style={{
                top: `${top}px`,
                height: `${height}px`,
                backgroundColor: color,
              }}
              onClick={(e) => {
                e.stopPropagation();
                onEventClick(event);
              }}
              title={`${event.title}\n${formatEventTimeRange(event)}`}
            >
              <div className="font-medium truncate">{event.title}</div>
              {height > 35 && (
                <div className="text-[10px] opacity-90 truncate">
                  {formatEventTimeRange(event)}
                </div>
              )}
              {height > 55 && event.location && (
                <div className="text-[10px] opacity-75 truncate">
                  📍 {event.location}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export function WeekView({
  currentDate,
  daysToShow,
  events,
  calendars,
  visibleCalendarIds,
  onEventClick,
  onTimeSlotClick,
}: WeekViewProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  
  // Get the days to display
  const days = useMemo(
    () => getDaysToShow(currentDate, daysToShow),
    [currentDate, daysToShow]
  );

  // Pre-compute events for each day
  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const day of days) {
      const key = day.toISOString().split('T')[0];
      map.set(key, getEventsForDay(day, events, visibleCalendarIds));
    }
    return map;
  }, [days, events, visibleCalendarIds]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Scrollable content */}
      <div
        ref={scrollContainerRef}
        className="flex-1 flex overflow-auto"
      >
        {/* Time column */}
        <TimeColumn />

        {/* Day columns */}
        <div className="flex flex-1">
          {days.map((day) => {
            const key = day.toISOString().split('T')[0];
            const dayEvents = eventsByDay.get(key) || [];

            return (
              <DayColumn
                key={key}
                date={day}
                events={dayEvents}
                calendars={calendars}
                onEventClick={onEventClick}
                onTimeSlotClick={onTimeSlotClick}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
