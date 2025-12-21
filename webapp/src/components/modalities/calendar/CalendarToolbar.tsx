/**
 * Calendar toolbar component.
 * Provides navigation, view switching, and action buttons.
 */
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  ToggleGroup,
  ToggleGroupItem,
} from '@/components/ui/toggle-group';
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Settings,
  RefreshCw,
  CalendarDays,
  CalendarRange,
  Calendar as CalendarIcon,
  LayoutGrid,
} from 'lucide-react';
import type { CalendarViewMode } from './types';

interface CalendarToolbarProps {
  /** Current view mode */
  viewMode: CalendarViewMode;
  /** Callback when view mode changes */
  onViewModeChange: (mode: CalendarViewMode) => void;
  /** Currently displayed date (for title) */
  currentDate: Date;
  /** Callback to go to previous period */
  onPrevious: () => void;
  /** Callback to go to next period */
  onNext: () => void;
  /** Callback to go to today */
  onToday: () => void;
  /** Callback to create a new event */
  onCreateEvent: () => void;
  /** Callback to open settings */
  onOpenSettings: () => void;
  /** Callback to refresh calendar data */
  onRefresh: () => void;
  /** Whether data is currently refreshing */
  isRefreshing?: boolean;
  /** Event count summary */
  eventCount?: number;
}

/**
 * Format the date range title based on view mode.
 */
function formatDateTitle(date: Date, viewMode: CalendarViewMode): string {
  switch (viewMode) {
    case 'month':
      return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
    case 'week': {
      // Get the start and end of the week
      const weekStart = new Date(date);
      weekStart.setDate(date.getDate() - date.getDay());
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      
      const startMonth = weekStart.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const endMonth = weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      return `${startMonth} - ${endMonth}`;
    }
    case '3-day': {
      const endDate = new Date(date);
      endDate.setDate(date.getDate() + 2);
      const start = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const end = endDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
      return `${start} - ${end}`;
    }
    case 'day':
      return date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        month: 'long', 
        day: 'numeric', 
        year: 'numeric' 
      });
  }
}

/**
 * Icon button with tooltip.
 */
function ToolbarButton({
  icon: Icon,
  label,
  onClick,
  disabled,
  variant = 'ghost',
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  variant?: 'ghost' | 'default' | 'outline';
}) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={variant}
            size="sm"
            onClick={onClick}
            disabled={disabled}
            className="h-8"
          >
            <Icon className="h-4 w-4" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export function CalendarToolbar({
  viewMode,
  onViewModeChange,
  currentDate,
  onPrevious,
  onNext,
  onToday,
  onCreateEvent,
  onOpenSettings,
  onRefresh,
  isRefreshing,
  eventCount,
}: CalendarToolbarProps) {
  return (
    <div className="flex flex-col gap-2 p-2 border-b bg-background">
      {/* Top row: Navigation and view switcher */}
      <div className="flex items-center justify-between">
        {/* Left side: Navigation */}
        <div className="flex items-center gap-2">
          <ToolbarButton
            icon={ChevronLeft}
            label="Previous"
            onClick={onPrevious}
          />
          <Button 
            variant="outline" 
            size="sm" 
            onClick={onToday}
            className="h-8"
          >
            Today
          </Button>
          <ToolbarButton
            icon={ChevronRight}
            label="Next"
            onClick={onNext}
          />
          
          <Separator orientation="vertical" className="h-6 mx-2" />
          
          {/* Date title */}
          <h2 className="text-lg font-semibold min-w-[200px]">
            {formatDateTitle(currentDate, viewMode)}
          </h2>
        </div>

        {/* Right side: View mode toggle */}
        <div className="flex items-center gap-2">
          <ToggleGroup 
            type="single" 
            value={viewMode} 
            onValueChange={(value) => value && onViewModeChange(value as CalendarViewMode)}
            className="border rounded-md"
          >
            <ToggleGroupItem value="month" aria-label="Month view" className="h-8 px-3">
              <LayoutGrid className="h-4 w-4 mr-1" />
              Month
            </ToggleGroupItem>
            <ToggleGroupItem value="week" aria-label="Week view" className="h-8 px-3">
              <CalendarRange className="h-4 w-4 mr-1" />
              Week
            </ToggleGroupItem>
            <ToggleGroupItem value="3-day" aria-label="3-Day view" className="h-8 px-3">
              <CalendarDays className="h-4 w-4 mr-1" />
              3-Day
            </ToggleGroupItem>
            <ToggleGroupItem value="day" aria-label="Day view" className="h-8 px-3">
              <CalendarIcon className="h-4 w-4 mr-1" />
              Day
            </ToggleGroupItem>
          </ToggleGroup>
          
          <ToolbarButton
            icon={RefreshCw}
            label="Refresh"
            onClick={onRefresh}
            disabled={isRefreshing}
          />
        </div>
      </div>

      {/* Bottom row: Actions and status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button 
            onClick={onCreateEvent}
            size="sm"
            className="h-8"
          >
            <Plus className="h-4 w-4 mr-1" />
            Create Event
          </Button>
          
          <ToolbarButton
            icon={Settings}
            label="Calendar Settings"
            onClick={onOpenSettings}
            variant="outline"
          />
        </div>

        {/* Status */}
        {eventCount !== undefined && (
          <span className="text-sm text-muted-foreground">
            {eventCount} event{eventCount !== 1 ? 's' : ''} in view
          </span>
        )}
      </div>
    </div>
  );
}
