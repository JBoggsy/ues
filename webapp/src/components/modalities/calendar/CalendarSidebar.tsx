/**
 * Calendar sidebar component.
 * Shows calendar list with visibility toggles and quick actions.
 * Collapsible to save space.
 */
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Settings,
} from 'lucide-react';
import type { Calendar } from './types';
import { cn } from '@/lib/utils';

interface CalendarSidebarProps {
  /** List of calendars */
  calendars: Calendar[];
  /** IDs of visible calendars */
  visibleCalendarIds: Set<string>;
  /** Callback when calendar visibility is toggled */
  onToggleCalendarVisibility: (calendarId: string) => void;
  /** Callback to add a new calendar */
  onAddCalendar: () => void;
  /** Callback to open calendar settings */
  onOpenSettings: () => void;
  /** Whether sidebar is collapsed */
  isCollapsed: boolean;
  /** Callback to toggle collapsed state */
  onToggleCollapsed: () => void;
}

/**
 * Calendar item in the sidebar list.
 */
function CalendarItem({
  calendar,
  isVisible,
  onToggle,
}: {
  calendar: Calendar;
  isVisible: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center gap-2 py-1 px-2 rounded-md hover:bg-accent/50 group">
      <Checkbox
        checked={isVisible}
        onCheckedChange={onToggle}
        className="h-4 w-4"
        style={{ 
          borderColor: calendar.color,
          backgroundColor: isVisible ? calendar.color : 'transparent',
        }}
      />
      <span className="flex-1 text-sm truncate">{calendar.name}</span>
      <div
        className="w-3 h-3 rounded-sm flex-shrink-0"
        style={{ backgroundColor: calendar.color }}
        title={calendar.color}
      />
    </div>
  );
}

/**
 * Mini calendar for quick date navigation.
 */
function MiniCalendar({
  currentDate,
  onDateSelect,
}: {
  currentDate: Date;
  onDateSelect: (date: Date) => void;
}) {
  const [displayMonth, setDisplayMonth] = useState(
    new Date(currentDate.getFullYear(), currentDate.getMonth(), 1)
  );

  const daysInMonth = new Date(
    displayMonth.getFullYear(),
    displayMonth.getMonth() + 1,
    0
  ).getDate();

  const firstDayOfMonth = new Date(
    displayMonth.getFullYear(),
    displayMonth.getMonth(),
    1
  ).getDay();

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const days: (number | null)[] = [];
  
  // Add empty slots for days before the first of the month
  for (let i = 0; i < firstDayOfMonth; i++) {
    days.push(null);
  }
  
  // Add all days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    days.push(day);
  }

  const handlePrevMonth = () => {
    setDisplayMonth(new Date(displayMonth.getFullYear(), displayMonth.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setDisplayMonth(new Date(displayMonth.getFullYear(), displayMonth.getMonth() + 1, 1));
  };

  const handleDayClick = (day: number) => {
    const selectedDate = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), day);
    onDateSelect(selectedDate);
  };

  const isToday = (day: number) => {
    const date = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), day);
    date.setHours(0, 0, 0, 0);
    return date.getTime() === today.getTime();
  };

  const isSelected = (day: number) => {
    const date = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), day);
    return (
      date.getFullYear() === currentDate.getFullYear() &&
      date.getMonth() === currentDate.getMonth() &&
      date.getDate() === currentDate.getDate()
    );
  };

  return (
    <div className="p-2">
      {/* Month navigation */}
      <div className="flex items-center justify-between mb-2">
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handlePrevMonth}>
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm font-medium">
          {displayMonth.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
        </span>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleNextMonth}>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 gap-0 text-center mb-1">
        {['S', 'M', 'T', 'W', 'T', 'F', 'S'].map((day, i) => (
          <div key={i} className="text-xs text-muted-foreground font-medium py-1">
            {day}
          </div>
        ))}
      </div>

      {/* Days grid */}
      <div className="grid grid-cols-7 gap-0 text-center">
        {days.map((day, i) => (
          <div key={i} className="aspect-square flex items-center justify-center">
            {day !== null ? (
              <button
                className={cn(
                  'w-6 h-6 rounded-full text-xs hover:bg-accent transition-colors',
                  isToday(day) && 'bg-primary text-primary-foreground hover:bg-primary/90',
                  isSelected(day) && !isToday(day) && 'bg-accent ring-1 ring-primary'
                )}
                onClick={() => handleDayClick(day)}
              >
                {day}
              </button>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
}

export function CalendarSidebar({
  calendars,
  visibleCalendarIds,
  onToggleCalendarVisibility,
  onAddCalendar,
  onOpenSettings,
  isCollapsed,
  onToggleCollapsed,
}: CalendarSidebarProps) {
  const [currentDate, setCurrentDate] = useState(new Date());

  if (isCollapsed) {
    return (
      <div className="w-10 border-r flex flex-col items-center py-2 bg-background">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={onToggleCollapsed}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">
              <p>Expand sidebar</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    );
  }

  return (
    <div className="w-56 border-r flex flex-col bg-background">
      {/* Header with collapse button */}
      <div className="flex items-center justify-between p-2 border-b">
        <span className="text-sm font-semibold">Calendars</span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onToggleCollapsed}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
      </div>

      {/* Mini calendar for date navigation */}
      <MiniCalendar 
        currentDate={currentDate} 
        onDateSelect={setCurrentDate} 
      />

      <Separator />

      {/* Calendar list */}
      <div className="flex-1 overflow-auto p-2">
        <div className="space-y-1">
          {calendars.map((calendar) => (
            <CalendarItem
              key={calendar.calendar_id}
              calendar={calendar}
              isVisible={visibleCalendarIds.has(calendar.calendar_id)}
              onToggle={() => onToggleCalendarVisibility(calendar.calendar_id)}
            />
          ))}
        </div>

        {calendars.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No calendars
          </p>
        )}
      </div>

      <Separator />

      {/* Quick actions */}
      <div className="p-2 space-y-1">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start h-8"
          onClick={onAddCalendar}
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Calendar
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start h-8"
          onClick={onOpenSettings}
        >
          <Settings className="h-4 w-4 mr-2" />
          Settings
        </Button>
      </div>
    </div>
  );
}
