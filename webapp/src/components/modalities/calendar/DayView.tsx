/**
 * Day view component for the calendar.
 * Displays a single day's schedule with detailed event information.
 */
import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import type { CalendarEvent, Calendar, TimeSlot } from './types';

interface DayViewProps {
  /** Current date to display */
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

// Hours to display
const START_HOUR = 0;
const END_HOUR = 23;
const HOUR_HEIGHT = 60; // pixels per hour

/**
 * Get events for the day.
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
 * Calculate position and height of an event.
 */
function getEventPosition(
  event: CalendarEvent,
  day: Date
): { top: number; height: number } {
  const eventStart = new Date(event.start);
  const eventEnd = new Date(event.end);

  const dayStart = new Date(day);
  dayStart.setHours(START_HOUR, 0, 0, 0);
  const dayEnd = new Date(day);
  dayEnd.setHours(END_HOUR + 1, 0, 0, 0);

  const clampedStart = new Date(Math.max(eventStart.getTime(), dayStart.getTime()));
  const clampedEnd = new Date(Math.min(eventEnd.getTime(), dayEnd.getTime()));

  const startHour = clampedStart.getHours() + clampedStart.getMinutes() / 60;
  const endHour = clampedEnd.getHours() + clampedEnd.getMinutes() / 60;

  const top = (startHour - START_HOUR) * HOUR_HEIGHT;
  const height = Math.max((endHour - startHour) * HOUR_HEIGHT, 30);

  return { top, height };
}

/**
 * Format time.
 */
function formatTime(hour: number): string {
  const h = hour % 12 || 12;
  const ampm = hour < 12 ? 'AM' : 'PM';
  return `${h}:00 ${ampm}`;
}

/**
 * Format event time range.
 */
function formatEventTimeRange(event: CalendarEvent): string {
  const start = new Date(event.start);
  const end = new Date(event.end);
  return `${start.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  })} - ${end.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  })}`;
}

/**
 * Check if it's today.
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
 * Current time indicator line.
 */
function CurrentTimeIndicator() {
  const now = new Date();
  const currentHour = now.getHours() + now.getMinutes() / 60;
  const top = (currentHour - START_HOUR) * HOUR_HEIGHT;

  return (
    <div
      className="absolute left-0 right-0 z-20 pointer-events-none"
      style={{ top: `${top}px` }}
    >
      <div className="flex items-center">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500 -ml-1" />
        <div className="flex-1 h-0.5 bg-red-500" />
      </div>
    </div>
  );
}

export function DayView({
  currentDate,
  events,
  calendars,
  visibleCalendarIds,
  onEventClick,
  onTimeSlotClick,
}: DayViewProps) {
  // Get events for this day
  const dayEvents = useMemo(
    () => getEventsForDay(currentDate, events, visibleCalendarIds),
    [currentDate, events, visibleCalendarIds]
  );

  const allDayEvents = dayEvents.filter((e) => e.all_day);
  const timedEvents = dayEvents.filter((e) => !e.all_day);

  // Generate hour slots
  const hours = Array.from({ length: END_HOUR - START_HOUR + 1 }, (_, i) => START_HOUR + i);

  const handleTimeSlotClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const hour = Math.floor(y / HOUR_HEIGHT) + START_HOUR;
    const minute = Math.floor((y % HOUR_HEIGHT) / HOUR_HEIGHT * 60);

    onTimeSlotClick({
      date: currentDate,
      hour,
      minute: Math.round(minute / 15) * 15,
    });
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Day header */}
      <div
        className={cn(
          'flex items-center justify-center py-3 border-b',
          isToday(currentDate) && 'bg-primary/5'
        )}
      >
        <div className="text-center">
          <div className="text-sm text-muted-foreground">
            {currentDate.toLocaleDateString('en-US', { weekday: 'long' })}
          </div>
          <div
            className={cn(
              'text-2xl font-semibold',
              isToday(currentDate) && 'text-primary'
            )}
          >
            {currentDate.toLocaleDateString('en-US', { 
              month: 'long', 
              day: 'numeric', 
              year: 'numeric' 
            })}
          </div>
        </div>
      </div>

      {/* All-day events */}
      {allDayEvents.length > 0 && (
        <div className="border-b bg-muted/30 p-2">
          <div className="text-xs text-muted-foreground mb-1 font-medium">ALL DAY</div>
          <div className="space-y-1">
            {allDayEvents.map((event) => {
              const calendar = calendars[event.calendar_id];
              const color = event.color || calendar?.color || '#4285f4';

              return (
                <button
                  key={event.event_id}
                  className="w-full text-left px-3 py-2 rounded hover:opacity-80 transition-opacity"
                  style={{ backgroundColor: color, color: '#fff' }}
                  onClick={() => onEventClick(event)}
                >
                  <div className="font-medium">{event.title}</div>
                  {event.location && (
                    <div className="text-xs opacity-80">📍 {event.location}</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Time grid */}
      <div className="flex-1 flex overflow-auto">
        {/* Time labels */}
        <div className="w-20 flex-shrink-0 border-r">
          {hours.map((hour) => (
            <div
              key={hour}
              className="h-[60px] text-xs text-muted-foreground text-right pr-2 pt-0"
              style={{ marginTop: hour === START_HOUR ? 0 : -6 }}
            >
              {formatTime(hour)}
            </div>
          ))}
        </div>

        {/* Events area */}
        <div
          className="flex-1 relative cursor-pointer"
          style={{ height: `${(END_HOUR - START_HOUR + 1) * HOUR_HEIGHT}px` }}
          onClick={handleTimeSlotClick}
        >
          {/* Hour grid lines */}
          {hours.map((hour) => (
            <div
              key={hour}
              className="absolute w-full border-b border-dashed border-muted"
              style={{ 
                top: `${(hour - START_HOUR) * HOUR_HEIGHT}px`, 
                height: `${HOUR_HEIGHT}px` 
              }}
            >
              {/* Half-hour line */}
              <div 
                className="absolute w-full border-b border-dotted border-muted/50"
                style={{ top: '50%' }}
              />
            </div>
          ))}

          {/* Current time indicator */}
          {isToday(currentDate) && <CurrentTimeIndicator />}

          {/* Events */}
          {timedEvents.map((event) => {
            const { top, height } = getEventPosition(event, currentDate);
            const calendar = calendars[event.calendar_id];
            const color = event.color || calendar?.color || '#4285f4';

            return (
              <button
                key={event.event_id}
                className="absolute left-2 right-2 px-3 py-2 rounded text-white overflow-hidden hover:opacity-90 transition-opacity text-left"
                style={{
                  top: `${top}px`,
                  height: `${height}px`,
                  backgroundColor: color,
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  onEventClick(event);
                }}
              >
                <div className="font-medium truncate">{event.title}</div>
                <div className="text-xs opacity-90">{formatEventTimeRange(event)}</div>
                {height > 70 && event.location && (
                  <div className="text-xs opacity-75 mt-1 truncate">
                    📍 {event.location}
                  </div>
                )}
                {height > 90 && event.description && (
                  <div className="text-xs opacity-75 mt-1 line-clamp-2">
                    {event.description}
                  </div>
                )}
                {height > 110 && event.attendees.length > 0 && (
                  <div className="text-xs opacity-75 mt-1">
                    👥 {event.attendees.length} attendee{event.attendees.length !== 1 ? 's' : ''}
                  </div>
                )}
                {event.recurrence && (
                  <div className="absolute top-2 right-2 text-xs">🔄</div>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
