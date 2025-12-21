/**
 * Main calendar viewer component.
 * Integrates all calendar sub-components and handles API interactions.
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import apiClient from '@/api/client';
import { useModalityState } from '@/api';
import { CalendarToolbar } from './CalendarToolbar';
import { CalendarSidebar } from './CalendarSidebar';
import { MonthView } from './MonthView';
import { WeekView } from './WeekView';
import { DayView } from './DayView';
import { EventDetailModal } from './EventDetailModal';
import { CreateEventDialog } from './CreateEventDialog';
import { CalendarSettingsDialog } from './CalendarSettingsDialog';
import type {
  CalendarState,
  CalendarEvent,
  CalendarViewMode,
  EventFormData,
  RecurrenceScope,
  TimeSlot,
  CreateCalendarEventRequest,
  UpdateCalendarEventRequest,
  DeleteCalendarEventRequest,
} from './types';

/**
 * API endpoints for calendar operations.
 */
const CALENDAR_API = {
  state: '/calendar/state',
  query: '/calendar/query',
  create: '/calendar/create',
  update: '/calendar/update',
  delete: '/calendar/delete',
};

/**
 * Convert form data to API request format.
 */
function formDataToCreateRequest(data: EventFormData): CreateCalendarEventRequest {
  const startDate = new Date(`${data.start_date}T${data.all_day ? '00:00' : data.start_time}`);
  const endDate = new Date(`${data.end_date}T${data.all_day ? '23:59' : data.end_time}`);

  return {
    calendar_id: data.calendar_id,
    title: data.title,
    description: data.description || null,
    start: startDate.toISOString(),
    end: endDate.toISOString(),
    all_day: data.all_day,
    timezone: data.timezone,
    location: data.location || null,
    status: data.status,
    organizer: null,
    attendees: data.attendees.length > 0 ? data.attendees : null,
    recurrence: data.recurrence,
    recurrence_exceptions: null,
    reminders: data.reminders.length > 0 ? data.reminders : null,
    color: data.color,
    visibility: data.visibility,
    transparency: 'opaque',
    attachments: null,
    conference_link: data.conference_link || null,
  };
}

/**
 * Convert form data to update request format.
 */
function formDataToUpdateRequest(
  data: EventFormData,
  eventId: string
): UpdateCalendarEventRequest {
  const startDate = new Date(`${data.start_date}T${data.all_day ? '00:00' : data.start_time}`);
  const endDate = new Date(`${data.end_date}T${data.all_day ? '23:59' : data.end_time}`);

  return {
    event_id: eventId,
    calendar_id: data.calendar_id,
    title: data.title,
    description: data.description || null,
    start: startDate.toISOString(),
    end: endDate.toISOString(),
    all_day: data.all_day,
    timezone: data.timezone,
    location: data.location || null,
    status: data.status,
    attendees: data.attendees.length > 0 ? data.attendees : null,
    recurrence: data.recurrence,
    reminders: data.reminders.length > 0 ? data.reminders : null,
    color: data.color,
    visibility: data.visibility,
    conference_link: data.conference_link || null,
  };
}

export function CalendarViewer() {
  const queryClient = useQueryClient();

  // Fetch calendar state with polling
  const {
    data: calendarState,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useModalityState<CalendarState>('calendar', 3000);

  // View state
  const [viewMode, setViewMode] = useState<CalendarViewMode>('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Visibility state (which calendars are shown)
  const [visibleCalendarIds, setVisibleCalendarIds] = useState<Set<string>>(new Set());

  // Initialize visible calendars when state loads
  useEffect(() => {
    if (calendarState && visibleCalendarIds.size === 0) {
      const initialVisible = new Set(
        Object.values(calendarState.calendars)
          .filter((cal) => cal.visible)
          .map((cal) => cal.calendar_id)
      );
      setVisibleCalendarIds(initialVisible);
    }
  }, [calendarState]);

  // Dialog states
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [eventDetailOpen, setEventDetailOpen] = useState(false);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editEvent, setEditEvent] = useState<CalendarEvent | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [clickedTimeSlot, setClickedTimeSlot] = useState<TimeSlot | undefined>();

  // Derived data
  const calendars = useMemo(
    () => (calendarState ? Object.values(calendarState.calendars) : []),
    [calendarState]
  );

  const events = useMemo(
    () => (calendarState ? Object.values(calendarState.events) : []),
    [calendarState]
  );

  const visibleEvents = useMemo(
    () => events.filter((e) => visibleCalendarIds.has(e.calendar_id)),
    [events, visibleCalendarIds]
  );

  // Get event count for current view
  const eventsInView = useMemo(() => {
    const getViewRange = () => {
      switch (viewMode) {
        case 'month': {
          const start = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
          const end = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0, 23, 59, 59);
          return { start, end };
        }
        case 'week': {
          const start = new Date(currentDate);
          start.setDate(currentDate.getDate() - currentDate.getDay());
          start.setHours(0, 0, 0, 0);
          const end = new Date(start);
          end.setDate(start.getDate() + 6);
          end.setHours(23, 59, 59);
          return { start, end };
        }
        case '3-day': {
          const start = new Date(currentDate);
          start.setHours(0, 0, 0, 0);
          const end = new Date(currentDate);
          end.setDate(currentDate.getDate() + 2);
          end.setHours(23, 59, 59);
          return { start, end };
        }
        case 'day': {
          const start = new Date(currentDate);
          start.setHours(0, 0, 0, 0);
          const end = new Date(currentDate);
          end.setHours(23, 59, 59);
          return { start, end };
        }
      }
    };

    const { start, end } = getViewRange();
    return visibleEvents.filter((e) => {
      const eventStart = new Date(e.start);
      const eventEnd = new Date(e.end);
      return eventStart <= end && eventEnd >= start;
    }).length;
  }, [visibleEvents, currentDate, viewMode]);

  // Invalidate queries after mutations
  const invalidateCalendarState = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['environment', 'modalities', 'calendar'] });
  }, [queryClient]);

  // Navigation handlers
  const handlePrevious = useCallback(() => {
    setCurrentDate((prev) => {
      const newDate = new Date(prev);
      switch (viewMode) {
        case 'month':
          newDate.setMonth(prev.getMonth() - 1);
          break;
        case 'week':
          newDate.setDate(prev.getDate() - 7);
          break;
        case '3-day':
          newDate.setDate(prev.getDate() - 3);
          break;
        case 'day':
          newDate.setDate(prev.getDate() - 1);
          break;
      }
      return newDate;
    });
  }, [viewMode]);

  const handleNext = useCallback(() => {
    setCurrentDate((prev) => {
      const newDate = new Date(prev);
      switch (viewMode) {
        case 'month':
          newDate.setMonth(prev.getMonth() + 1);
          break;
        case 'week':
          newDate.setDate(prev.getDate() + 7);
          break;
        case '3-day':
          newDate.setDate(prev.getDate() + 3);
          break;
        case 'day':
          newDate.setDate(prev.getDate() + 1);
          break;
      }
      return newDate;
    });
  }, [viewMode]);

  const handleToday = useCallback(() => {
    setCurrentDate(new Date());
  }, []);

  // Calendar visibility toggle
  const handleToggleCalendarVisibility = useCallback((calendarId: string) => {
    setVisibleCalendarIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(calendarId)) {
        newSet.delete(calendarId);
      } else {
        newSet.add(calendarId);
      }
      return newSet;
    });
  }, []);

  // Event handlers
  const handleEventClick = useCallback((event: CalendarEvent) => {
    setSelectedEvent(event);
    setEventDetailOpen(true);
  }, []);

  const handleTimeSlotClick = useCallback((slot: TimeSlot) => {
    setClickedTimeSlot(slot);
    setEditEvent(null);
    setCreateDialogOpen(true);
  }, []);

  const handleCreateEvent = useCallback(() => {
    setClickedTimeSlot(undefined);
    setEditEvent(null);
    setCreateDialogOpen(true);
  }, []);

  const handleEditEvent = useCallback((event: CalendarEvent) => {
    setEventDetailOpen(false);
    setEditEvent(event);
    setClickedTimeSlot(undefined);
    setCreateDialogOpen(true);
  }, []);

  const handleDuplicateEvent = useCallback((event: CalendarEvent) => {
    // Create a copy with a new title and no ID (so it creates a new event)
    const duplicated = {
      ...event,
      title: `${event.title} (copy)`,
      event_id: '', // Will be ignored in create
    };
    setEventDetailOpen(false);
    setEditEvent(duplicated);
    setClickedTimeSlot(undefined);
    setCreateDialogOpen(true);
  }, []);

  // API operations
  const handleSaveEvent = useCallback(
    async (data: EventFormData, isEdit: boolean, eventId?: string) => {
      try {
        if (isEdit && eventId) {
          const request = formDataToUpdateRequest(data, eventId);
          await apiClient.post(CALENDAR_API.update, request);
          toast.success('Event updated');
        } else {
          const request = formDataToCreateRequest(data);
          await apiClient.post(CALENDAR_API.create, request);
          toast.success('Event created');
        }
        invalidateCalendarState();
      } catch (error: any) {
        const message = error.response?.data?.detail || 'Failed to save event';
        toast.error(message);
        throw error;
      }
    },
    [invalidateCalendarState]
  );

  const handleDeleteEvent = useCallback(
    async (event: CalendarEvent, scope: RecurrenceScope) => {
      try {
        const request: DeleteCalendarEventRequest = {
          event_id: event.event_id,
          calendar_id: event.calendar_id,
          recurrence_scope: scope,
        };
        await apiClient.post(CALENDAR_API.delete, request);
        toast.success('Event deleted');
        setEventDetailOpen(false);
        invalidateCalendarState();
      } catch (error: any) {
        const message = error.response?.data?.detail || 'Failed to delete event';
        toast.error(message);
      }
    },
    [invalidateCalendarState]
  );

  // Calendar management (for settings dialog)
  const handleCreateCalendar = useCallback(async (name: string, color: string) => {
    try {
      // Generate a calendar ID from the name
      const calendarId = name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
      await apiClient.post('/calendar/calendars/create', {
        calendar_id: calendarId,
        name,
        color,
        visible: true,
      });
      toast.success(`Created calendar: ${name}`);
      invalidateCalendarState();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to create calendar';
      toast.error(message);
    }
  }, [invalidateCalendarState]);

  const handleUpdateCalendar = useCallback(
    async (calendarId: string, name: string, color: string) => {
      try {
        await apiClient.post('/calendar/calendars/update', {
          calendar_id: calendarId,
          name,
          color,
        });
        toast.success(`Updated calendar: ${name}`);
        invalidateCalendarState();
      } catch (error: any) {
        const message = error.response?.data?.detail || 'Failed to update calendar';
        toast.error(message);
      }
    },
    [invalidateCalendarState]
  );

  const handleDeleteCalendar = useCallback(async (calendarId: string) => {
    try {
      await apiClient.post('/calendar/calendars/delete', {
        calendar_id: calendarId,
      });
      toast.success('Calendar deleted');
      invalidateCalendarState();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to delete calendar';
      toast.error(message);
    }
  }, [invalidateCalendarState]);

  const handleSetDefaultCalendar = useCallback(async (calendarId: string) => {
    try {
      await apiClient.post('/calendar/calendars/set-default', {
        calendar_id: calendarId,
      });
      toast.success('Default calendar updated');
      invalidateCalendarState();
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Failed to set default calendar';
      toast.error(message);
    }
  }, [invalidateCalendarState]);

  // Get selected event's calendar
  const selectedEventCalendar = selectedEvent
    ? calendarState?.calendars[selectedEvent.calendar_id] || null
    : null;

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-pulse text-muted-foreground">Loading calendar...</div>
      </div>
    );
  }

  // Error state
  if (isError || !calendarState) {
    return (
      <div className="flex h-full items-center justify-center text-destructive">
        Failed to load calendar state
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <CalendarToolbar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        currentDate={currentDate}
        onPrevious={handlePrevious}
        onNext={handleNext}
        onToday={handleToday}
        onCreateEvent={handleCreateEvent}
        onOpenSettings={() => setSettingsOpen(true)}
        onRefresh={() => refetch()}
        isRefreshing={isRefetching}
        eventCount={eventsInView}
      />

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <CalendarSidebar
          calendars={calendars}
          visibleCalendarIds={visibleCalendarIds}
          onToggleCalendarVisibility={handleToggleCalendarVisibility}
          onAddCalendar={() => setSettingsOpen(true)}
          onOpenSettings={() => setSettingsOpen(true)}
          isCollapsed={sidebarCollapsed}
          onToggleCollapsed={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* Calendar view */}
        <div className="flex-1 overflow-hidden">
          {viewMode === 'month' && (
            <MonthView
              currentDate={currentDate}
              events={events}
              calendars={calendarState.calendars}
              visibleCalendarIds={visibleCalendarIds}
              onEventClick={handleEventClick}
              onTimeSlotClick={handleTimeSlotClick}
            />
          )}
          {viewMode === 'week' && (
            <WeekView
              currentDate={currentDate}
              daysToShow={7}
              events={events}
              calendars={calendarState.calendars}
              visibleCalendarIds={visibleCalendarIds}
              onEventClick={handleEventClick}
              onTimeSlotClick={handleTimeSlotClick}
            />
          )}
          {viewMode === '3-day' && (
            <WeekView
              currentDate={currentDate}
              daysToShow={3}
              events={events}
              calendars={calendarState.calendars}
              visibleCalendarIds={visibleCalendarIds}
              onEventClick={handleEventClick}
              onTimeSlotClick={handleTimeSlotClick}
            />
          )}
          {viewMode === 'day' && (
            <DayView
              currentDate={currentDate}
              events={events}
              calendars={calendarState.calendars}
              visibleCalendarIds={visibleCalendarIds}
              onEventClick={handleEventClick}
              onTimeSlotClick={handleTimeSlotClick}
            />
          )}
        </div>
      </div>

      {/* Event detail modal */}
      <EventDetailModal
        event={selectedEvent}
        calendar={selectedEventCalendar}
        open={eventDetailOpen}
        onClose={() => setEventDetailOpen(false)}
        onEdit={handleEditEvent}
        onDuplicate={handleDuplicateEvent}
        onDelete={handleDeleteEvent}
      />

      {/* Create/Edit event dialog */}
      <CreateEventDialog
        open={createDialogOpen}
        onClose={() => {
          setCreateDialogOpen(false);
          setEditEvent(null);
          setClickedTimeSlot(undefined);
        }}
        onSave={handleSaveEvent}
        editEvent={editEvent}
        calendars={calendars}
        defaultCalendarId={calendarState.default_calendar_id}
        defaultDateTime={clickedTimeSlot}
      />

      {/* Settings dialog */}
      <CalendarSettingsDialog
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        calendars={calendars}
        defaultCalendarId={calendarState.default_calendar_id}
        userTimezone={calendarState.user_timezone}
        onCreateCalendar={handleCreateCalendar}
        onUpdateCalendar={handleUpdateCalendar}
        onDeleteCalendar={handleDeleteCalendar}
        onSetDefaultCalendar={handleSetDefaultCalendar}
      />
    </div>
  );
}
