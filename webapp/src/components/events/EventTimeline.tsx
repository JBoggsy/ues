/**
 * Event Timeline Visualization Component
 * 
 * A vertical, centered timeline showing events with proportional time spacing.
 * Features:
 * - Proportional spacing based on time differences
 * - Zoom with Ctrl+Mouse wheel
 * - Date headers as horizontal lines
 * - Visual indication of time gaps
 * - Filter by modality and status
 * - Jump to current time button
 * - Color-coded by status (pending, executed, cancelled)
 * - Color-coded by modality type
 */

import { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import { format, isSameDay, differenceInMinutes } from 'date-fns';
import { 
  MapPin, 
  Cloud, 
  Clock, 
  Mail, 
  MessageSquare, 
  MessageCircle, 
  Calendar,
  Filter,
  ZoomIn,
  ZoomOut,
  Navigation,
  type LucideIcon 
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { SimulatorEvent, Modality } from '@/api/types';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';

/**
 * Modality icon mapping.
 */
const MODALITY_ICONS: Record<Modality, LucideIcon> = {
  location: MapPin,
  weather: Cloud,
  time: Clock,
  email: Mail,
  sms: MessageSquare,
  chat: MessageCircle,
  calendar: Calendar,
};

/**
 * Modality color classes for the timeline dots and cards.
 */
const MODALITY_COLORS: Record<Modality, { dot: string; card: string; line: string }> = {
  location: {
    dot: 'bg-blue-500',
    card: 'border-blue-500/30 bg-blue-500/5',
    line: 'bg-blue-500/50',
  },
  weather: {
    dot: 'bg-cyan-500',
    card: 'border-cyan-500/30 bg-cyan-500/5',
    line: 'bg-cyan-500/50',
  },
  time: {
    dot: 'bg-purple-500',
    card: 'border-purple-500/30 bg-purple-500/5',
    line: 'bg-purple-500/50',
  },
  email: {
    dot: 'bg-amber-500',
    card: 'border-amber-500/30 bg-amber-500/5',
    line: 'bg-amber-500/50',
  },
  sms: {
    dot: 'bg-green-500',
    card: 'border-green-500/30 bg-green-500/5',
    line: 'bg-green-500/50',
  },
  chat: {
    dot: 'bg-pink-500',
    card: 'border-pink-500/30 bg-pink-500/5',
    line: 'bg-pink-500/50',
  },
  calendar: {
    dot: 'bg-orange-500',
    card: 'border-orange-500/30 bg-orange-500/5',
    line: 'bg-orange-500/50',
  },
};

/**
 * Status styling for dots.
 */
const STATUS_STYLES: Record<string, { ring: string; opacity: string }> = {
  pending: { ring: 'ring-2 ring-offset-2 ring-offset-background ring-primary', opacity: '' },
  executed: { ring: '', opacity: '' },
  cancelled: { ring: '', opacity: 'opacity-40' },
  failed: { ring: 'ring-2 ring-red-500', opacity: '' },
};

/**
 * Zoom configuration for proportional timeline spacing.
 */
const ZOOM_CONFIG = {
  min: 0.1,      // Minimum zoom (very compressed)
  max: 5,        // Maximum zoom (very expanded)
  default: 1,    // Default zoom level
  step: 0.2,     // Zoom step for wheel/buttons
  pixelsPerMinute: 2, // Base pixels per minute at zoom 1
  minSpacing: 20,     // Minimum pixels between events
  maxSpacing: 200,    // Maximum pixels for gaps (caps very long gaps)
};

interface EventTimelineProps {
  events: SimulatorEvent[];
  currentTime?: string;
  onEventClick?: (event: SimulatorEvent) => void;
}

/**
 * Generate a brief summary of an event for the timeline card.
 */
function getEventSummary(event: SimulatorEvent): string {
  const data = event.data as Record<string, unknown> | null;
  const modality = event.modality;

  // Handle null/undefined data
  if (!data) {
    return `${modality} event`;
  }

  switch (modality) {
    case 'location': {
      const named = data.named_location as string | undefined;
      const addr = data.address as string | undefined;
      if (named) return named;
      if (addr) return addr.slice(0, 30) + (addr.length > 30 ? '...' : '');
      const lat = data.latitude as number;
      const lon = data.longitude as number;
      return `(${lat?.toFixed(2)}, ${lon?.toFixed(2)})`;
    }
    case 'weather': {
      const temp = data.temp_f as number | undefined;
      const condition = data.condition as string | undefined;
      if (temp !== undefined) return `${temp}°F${condition ? `, ${condition}` : ''}`;
      return 'Weather update';
    }
    case 'time': {
      const tz = data.timezone as string | undefined;
      return tz || 'Time preferences';
    }
    case 'email': {
      const op = data.operation as string | undefined;
      const subject = data.subject as string | undefined;
      if (subject) return subject.slice(0, 25) + (subject.length > 25 ? '...' : '');
      return op || 'Email action';
    }
    case 'sms': {
      const action = data.action as string | undefined;
      const body = data.body as string | undefined;
      if (body) return body.slice(0, 25) + (body.length > 25 ? '...' : '');
      return action?.replace(/_/g, ' ') || 'SMS action';
    }
    case 'chat': {
      const role = data.role as string | undefined;
      const content = data.content as string | undefined;
      if (content) {
        const preview = content.slice(0, 25) + (content.length > 25 ? '...' : '');
        return role ? `${role}: ${preview}` : preview;
      }
      return data.operation as string || 'Chat message';
    }
    case 'calendar': {
      const title = data.title as string | undefined;
      const op = data.operation as string | undefined;
      if (title) return title.slice(0, 25) + (title.length > 25 ? '...' : '');
      return op || 'Calendar event';
    }
    default:
      return 'Event';
  }
}

/**
 * Filter state type.
 */
interface FilterState {
  modalities: Set<Modality>;
  statuses: Set<string>;
}

/**
 * All available modalities for filtering.
 */
const ALL_MODALITIES: Modality[] = ['location', 'weather', 'time', 'email', 'sms', 'chat', 'calendar'];

/**
 * All available statuses for filtering.
 */
const ALL_STATUSES = ['pending', 'executed', 'cancelled', 'failed'];

/**
 * Calculate spacing between two events based on time difference.
 */
function calculateSpacing(
  time1: Date, 
  time2: Date, 
  zoom: number
): number {
  const diffMinutes = Math.abs(differenceInMinutes(time2, time1));
  const rawSpacing = diffMinutes * ZOOM_CONFIG.pixelsPerMinute * zoom;
  
  // Clamp spacing between min and max
  return Math.max(
    ZOOM_CONFIG.minSpacing, 
    Math.min(rawSpacing, ZOOM_CONFIG.maxSpacing * zoom)
  );
}

/**
 * Date header component.
 */
function DateHeader({ date }: { date: Date }) {
  const formattedDate = format(date, 'EEEE, MMMM d, yyyy');
  
  return (
    <div className="relative flex items-center py-2">
      {/* Left line */}
      <div className="flex-1 h-px bg-border" />
      
      {/* Date label */}
      <div className="px-4 py-1 bg-muted rounded-full">
        <span className="text-xs font-medium text-muted-foreground">
          {formattedDate}
        </span>
      </div>
      
      {/* Right line */}
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}

/**
 * Time gap indicator component.
 * Shows a visual break in the timeline with a label indicating the time gap.
 */
function TimeGapIndicator({ minutes }: { minutes: number }) {
  // Format the gap duration
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  const remainingMinutes = minutes % 60;
  
  let label: string;
  if (days > 0) {
    label = remainingHours > 0 ? `${days}d ${remainingHours}h` : `${days}d`;
  } else if (hours > 0) {
    label = remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  } else {
    label = `${minutes}m`;
  }
  
  return (
    <div className="relative flex items-center justify-center py-1">
      {/* Gap indicator with label */}
      <div className="flex items-center gap-2 px-3 py-1 bg-muted/50 rounded-full border border-dashed border-muted-foreground/30">
        <span className="text-[10px] text-muted-foreground font-medium">
          ⋮ {label} gap ⋮
        </span>
      </div>
    </div>
  );
}

/**
 * Filter controls component.
 */
function FilterControls({
  filters,
  onFiltersChange,
  eventCounts,
}: {
  filters: FilterState;
  onFiltersChange: (filters: FilterState) => void;
  eventCounts: { modalities: Record<Modality, number>; statuses: Record<string, number> };
}) {
  const activeFilterCount = 
    (ALL_MODALITIES.length - filters.modalities.size) +
    (ALL_STATUSES.length - filters.statuses.size);

  const toggleModality = (modality: Modality) => {
    const newModalities = new Set(filters.modalities);
    if (newModalities.has(modality)) {
      newModalities.delete(modality);
    } else {
      newModalities.add(modality);
    }
    onFiltersChange({ ...filters, modalities: newModalities });
  };

  const toggleStatus = (status: string) => {
    const newStatuses = new Set(filters.statuses);
    if (newStatuses.has(status)) {
      newStatuses.delete(status);
    } else {
      newStatuses.add(status);
    }
    onFiltersChange({ ...filters, statuses: newStatuses });
  };

  const resetFilters = () => {
    onFiltersChange({
      modalities: new Set(ALL_MODALITIES),
      statuses: new Set(ALL_STATUSES),
    });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Filter className="h-4 w-4" />
          Filter
          {activeFilterCount > 0 && (
            <span className="ml-1 px-1.5 py-0.5 text-xs bg-primary text-primary-foreground rounded-full">
              {activeFilterCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel className="flex items-center justify-between">
          Filters
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={resetFilters}
            >
              Reset
            </Button>
          )}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Modalities
        </DropdownMenuLabel>
        {ALL_MODALITIES.map((modality) => {
          const Icon = MODALITY_ICONS[modality];
          const count = eventCounts.modalities[modality] || 0;
          return (
            <DropdownMenuCheckboxItem
              key={modality}
              checked={filters.modalities.has(modality)}
              onCheckedChange={() => toggleModality(modality)}
            >
              <Icon className="h-4 w-4 mr-2" />
              <span className="capitalize flex-1">{modality}</span>
              <span className="text-xs text-muted-foreground">{count}</span>
            </DropdownMenuCheckboxItem>
          );
        })}
        
        <DropdownMenuSeparator />
        
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Status
        </DropdownMenuLabel>
        {ALL_STATUSES.map((status) => {
          const count = eventCounts.statuses[status] || 0;
          return (
            <DropdownMenuCheckboxItem
              key={status}
              checked={filters.statuses.has(status)}
              onCheckedChange={() => toggleStatus(status)}
            >
              <span className="capitalize flex-1">{status}</span>
              <span className="text-xs text-muted-foreground">{count}</span>
            </DropdownMenuCheckboxItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * Zoom controls component.
 */
function ZoomControls({
  zoom,
  onZoomChange,
}: {
  zoom: number;
  onZoomChange: (zoom: number) => void;
}) {
  const zoomIn = () => {
    onZoomChange(Math.min(zoom + ZOOM_CONFIG.step, ZOOM_CONFIG.max));
  };

  const zoomOut = () => {
    onZoomChange(Math.max(zoom - ZOOM_CONFIG.step, ZOOM_CONFIG.min));
  };

  const resetZoom = () => {
    onZoomChange(ZOOM_CONFIG.default);
  };

  const zoomPercent = Math.round(zoom * 100);

  return (
    <div className="flex items-center gap-1">
      <Button variant="outline" size="icon" className="h-8 w-8" onClick={zoomOut}>
        <ZoomOut className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        className="h-8 px-2 text-xs min-w-[50px]"
        onClick={resetZoom}
      >
        {zoomPercent}%
      </Button>
      <Button variant="outline" size="icon" className="h-8 w-8" onClick={zoomIn}>
        <ZoomIn className="h-4 w-4" />
      </Button>
    </div>
  );
}

/**
 * Single event item on the timeline.
 */
function TimelineEvent({ 
  event, 
  side, 
  onClick,
  isCurrentTime,
}: { 
  event: SimulatorEvent; 
  side: 'left' | 'right';
  onClick?: () => void;
  isCurrentTime?: boolean;
}) {
  const modality = event.modality as Modality;
  const colors = MODALITY_COLORS[modality] || MODALITY_COLORS.location;
  const statusStyle = STATUS_STYLES[event.status] || STATUS_STYLES.pending;
  const Icon = MODALITY_ICONS[modality] || Clock;
  const summary = getEventSummary(event);
  const time = format(new Date(event.scheduled_time), 'HH:mm:ss');
  const date = format(new Date(event.scheduled_time), 'MMM d');

  return (
    <div className={cn(
      'relative flex items-center gap-0',
      side === 'left' ? 'flex-row-reverse' : 'flex-row',
      statusStyle.opacity,
    )}>
      {/* Event Card */}
      <div 
        className={cn(
          'w-[calc(50%-24px)] cursor-pointer transition-all hover:scale-[1.02]',
          side === 'left' ? 'pr-4 text-right' : 'pl-4 text-left',
        )}
        onClick={onClick}
      >
        <div className={cn(
          'inline-block rounded-lg border p-3 shadow-sm transition-shadow hover:shadow-md',
          colors.card,
          side === 'left' ? 'ml-auto' : 'mr-auto',
        )}>
          <div className={cn(
            'flex items-center gap-2 mb-1',
            side === 'left' ? 'flex-row-reverse' : 'flex-row',
          )}>
            <Icon className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground capitalize">
              {modality}
            </span>
            <span className={cn(
              'text-xs px-1.5 py-0.5 rounded',
              event.status === 'pending' && 'bg-primary/10 text-primary',
              event.status === 'executed' && 'bg-green-500/10 text-green-600',
              event.status === 'cancelled' && 'bg-muted text-muted-foreground',
              event.status === 'failed' && 'bg-red-500/10 text-red-600',
            )}>
              {event.status}
            </span>
          </div>
          <p className="text-sm font-medium truncate">{summary}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {date} at {time}
          </p>
        </div>
      </div>

      {/* Connecting Line */}
      <div className={cn(
        'h-0.5 w-4',
        colors.line,
      )} />

      {/* Timeline Dot */}
      <div className={cn(
        'relative z-10 h-4 w-4 rounded-full shrink-0',
        colors.dot,
        statusStyle.ring,
        isCurrentTime && 'animate-pulse',
      )}>
        {/* Inner dot for executed events */}
        {event.status === 'executed' && (
          <div className="absolute inset-1 rounded-full bg-background" />
        )}
      </div>

      {/* Spacer for the other side */}
      <div className="w-[calc(50%-24px)]" />
    </div>
  );
}

/**
 * Current time marker on the timeline.
 */
function CurrentTimeMarker({ 
  time, 
  markerRef 
}: { 
  time: string;
  markerRef?: React.RefObject<HTMLDivElement | null>;
}) {
  const formattedTime = format(new Date(time), 'HH:mm:ss');
  const formattedDate = format(new Date(time), 'MMM d, yyyy');

  return (
    <div ref={markerRef} className="relative flex items-center">
      {/* Left label */}
      <div className="w-[calc(50%-24px)] pr-4 text-right">
        <span className="text-xs font-medium text-primary">
          Current Time
        </span>
      </div>

      {/* Line */}
      <div className="h-0.5 w-4 bg-primary" />

      {/* Diamond marker */}
      <div className="relative z-10 h-4 w-4 rotate-45 bg-primary shrink-0 shadow-lg" />

      {/* Line */}
      <div className="h-0.5 w-4 bg-primary" />

      {/* Right label */}
      <div className="w-[calc(50%-24px)] pl-4 text-left">
        <span className="text-xs text-muted-foreground">
          {formattedDate} {formattedTime}
        </span>
      </div>
    </div>
  );
}

/**
 * Event Timeline component with enhanced features.
 * 
 * Features:
 * - Proportional time-based spacing
 * - Zoom with Ctrl+Mouse wheel
 * - Date headers
 * - Time gap indicators
 * - Filter by modality and status
 * - Jump to current time
 */
export function EventTimeline({ events, currentTime, onEventClick }: EventTimelineProps) {
  // State for zoom and filters
  const [zoom, setZoom] = useState(ZOOM_CONFIG.default);
  const [filters, setFilters] = useState<FilterState>({
    modalities: new Set(ALL_MODALITIES),
    statuses: new Set(ALL_STATUSES),
  });
  
  // Refs for scrolling
  const containerRef = useRef<HTMLDivElement>(null);
  const currentTimeMarkerRef = useRef<HTMLDivElement | null>(null);

  // Filter events
  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const modality = event.modality as Modality;
      return filters.modalities.has(modality) && filters.statuses.has(event.status);
    });
  }, [events, filters]);

  // Sort events by scheduled time
  const sortedEvents = useMemo(() => {
    return [...filteredEvents].sort(
      (a, b) => new Date(a.scheduled_time).getTime() - new Date(b.scheduled_time).getTime()
    );
  }, [filteredEvents]);

  // Calculate event counts for filter display
  const eventCounts = useMemo(() => {
    const modalities: Record<Modality, number> = {} as Record<Modality, number>;
    const statuses: Record<string, number> = {};
    
    for (const event of events) {
      const modality = event.modality as Modality;
      modalities[modality] = (modalities[modality] || 0) + 1;
      statuses[event.status] = (statuses[event.status] || 0) + 1;
    }
    
    return { modalities, statuses };
  }, [events]);

  // Process events with spacing and date headers
  const processedTimeline = useMemo(() => {
    const items: Array<
      | { type: 'event'; event: SimulatorEvent; side: 'left' | 'right'; spacing: number }
      | { type: 'date-header'; date: Date; spacing: number }
      | { type: 'gap'; minutes: number; spacing: number }
      | { type: 'current-time'; time: string; spacing: number }
    > = [];

    if (sortedEvents.length === 0) return items;

    let lastDate: Date | null = null;
    let sideIndex = 0;
    const currentTimeMs = currentTime ? new Date(currentTime).getTime() : null;
    let currentTimeInserted = false;

    for (let i = 0; i < sortedEvents.length; i++) {
      const event = sortedEvents[i];
      const eventDate = new Date(event.scheduled_time);
      const eventMs = eventDate.getTime();

      // Insert current time marker before this event if needed
      if (currentTimeMs && !currentTimeInserted && currentTimeMs < eventMs) {
        // Calculate spacing to current time
        if (lastDate) {
          const gapMinutes = differenceInMinutes(new Date(currentTime!), lastDate);
          // Show gap indicator for gaps of 1 hour or more
          if (gapMinutes >= 60) {
            items.push({ 
              type: 'gap', 
              minutes: gapMinutes, 
              spacing: calculateSpacing(lastDate, new Date(currentTime!), zoom) 
            });
          }
        }
        items.push({ type: 'current-time', time: currentTime!, spacing: 16 });
        currentTimeInserted = true;
        lastDate = new Date(currentTime!);
      }

      // Check if we need a date header
      if (!lastDate || !isSameDay(eventDate, lastDate)) {
        const spacing = lastDate ? 32 : 0;
        items.push({ type: 'date-header', date: eventDate, spacing });
        lastDate = eventDate;
      }

      // Calculate spacing from last item
      let spacing = ZOOM_CONFIG.minSpacing;
      if (i > 0) {
        const prevEvent = sortedEvents[i - 1];
        const prevDate = new Date(prevEvent.scheduled_time);
        const gapMinutes = differenceInMinutes(eventDate, prevDate);
        
        // Add gap indicator for gaps of 1 hour or more (same day only)
        if (gapMinutes >= 60 && isSameDay(eventDate, prevDate)) {
          items.push({ 
            type: 'gap', 
            minutes: gapMinutes, 
            spacing: calculateSpacing(prevDate, eventDate, zoom) 
          });
          spacing = ZOOM_CONFIG.minSpacing;
        } else {
          spacing = calculateSpacing(prevDate, eventDate, zoom);
        }
      }

      // Add the event
      items.push({
        type: 'event',
        event,
        side: (sideIndex % 2 === 0 ? 'left' : 'right') as 'left' | 'right',
        spacing,
      });
      sideIndex++;
      lastDate = eventDate;
    }

    // Insert current time at the end if not yet inserted
    if (currentTimeMs && !currentTimeInserted) {
      if (lastDate) {
        const gapMinutes = differenceInMinutes(new Date(currentTime!), lastDate);
        // Show gap indicator for gaps of 1 hour or more
        if (gapMinutes >= 60) {
          items.push({ 
            type: 'gap', 
            minutes: gapMinutes, 
            spacing: calculateSpacing(lastDate, new Date(currentTime!), zoom) 
          });
        }
      }
      items.push({ type: 'current-time', time: currentTime!, spacing: 16 });
    }

    return items;
  }, [sortedEvents, currentTime, zoom]);

  // Handle Ctrl+Wheel zoom
  const handleWheel = useCallback((e: WheelEvent) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -ZOOM_CONFIG.step : ZOOM_CONFIG.step;
      setZoom((prev) => 
        Math.max(ZOOM_CONFIG.min, Math.min(prev + delta, ZOOM_CONFIG.max))
      );
    }
  }, []);

  // Attach wheel listener
  useEffect(() => {
    const container = containerRef.current;
    if (container) {
      container.addEventListener('wheel', handleWheel, { passive: false });
      return () => container.removeEventListener('wheel', handleWheel);
    }
  }, [handleWheel]);

  // Jump to current time
  const jumpToCurrentTime = useCallback(() => {
    if (currentTimeMarkerRef.current) {
      currentTimeMarkerRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
    }
  }, []);

  // Empty state
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
        <Calendar className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-lg font-medium">No events to display</p>
        <p className="text-sm">Create an event to see it on the timeline</p>
      </div>
    );
  }

  // Filtered empty state
  if (filteredEvents.length === 0) {
    return (
      <div className="flex flex-col">
        {/* Controls */}
        <div className="flex items-center justify-between gap-4 mb-4 px-2">
          <FilterControls
            filters={filters}
            onFiltersChange={setFilters}
            eventCounts={eventCounts}
          />
          <div className="flex items-center gap-2">
            <ZoomControls zoom={zoom} onZoomChange={setZoom} />
          </div>
        </div>
        
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <Filter className="h-12 w-12 mb-4 opacity-50" />
          <p className="text-lg font-medium">No matching events</p>
          <p className="text-sm">Adjust filters to see events</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center justify-between gap-4 mb-4 px-2 shrink-0">
        <FilterControls
          filters={filters}
          onFiltersChange={setFilters}
          eventCounts={eventCounts}
        />
        <div className="flex items-center gap-2">
          {currentTime && (
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={jumpToCurrentTime}
            >
              <Navigation className="h-4 w-4" />
              Jump to Now
            </Button>
          )}
          <ZoomControls zoom={zoom} onZoomChange={setZoom} />
        </div>
      </div>

      {/* Help text */}
      <div className="text-xs text-muted-foreground text-center mb-2">
        Ctrl + Mouse Wheel to zoom
      </div>

      {/* Timeline */}
      <div 
        ref={containerRef}
        className="relative flex-1 overflow-y-auto py-8"
      >
        {/* Timeline items wrapper with central line */}
        <div className="relative">
          {/* Central timeline line - spans full height of content */}
          <div className="absolute left-1/2 top-0 bottom-0 w-0.5 -translate-x-1/2 bg-border" />

          {/* Timeline items */}
          {processedTimeline.map((item, index) => {
            const key = `timeline-item-${index}`;
            
            if (item.type === 'date-header') {
              return (
                <div key={key} style={{ marginTop: `${item.spacing}px` }}>
                  <DateHeader date={item.date} />
                </div>
              );
            }
            
            if (item.type === 'gap') {
              return (
                <div key={key} style={{ marginTop: `${item.spacing}px` }}>
                  <TimeGapIndicator minutes={item.minutes} />
                </div>
              );
            }
            
            if (item.type === 'current-time') {
              return (
                <div key={key} style={{ marginTop: `${item.spacing}px` }}>
                  <CurrentTimeMarker 
                    time={item.time} 
                    markerRef={currentTimeMarkerRef}
                  />
                </div>
              );
            }
            
            // Event type
            if (item.type === 'event') {
              return (
                <div 
                  key={item.event.event_id} 
                  style={{ marginTop: `${item.spacing}px` }}
                >
                  <TimelineEvent
                    event={item.event}
                    side={item.side}
                    onClick={() => onEventClick?.(item.event)}
                  />
                </div>
              );
            }

            // Should never reach here
            return null;
          })}

          {/* Timeline end cap - at the bottom of content */}
          <div className="flex justify-center pt-6">
            <div className="h-3 w-3 rounded-full bg-border" />
          </div>
        </div>
      </div>
    </div>
  );
}
