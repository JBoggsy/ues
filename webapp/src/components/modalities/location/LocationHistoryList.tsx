/**
 * Component displaying location history grouped by date.
 * Includes filtering and pagination options.
 */
import { useMemo, useState } from 'react';
import { format, isToday, isYesterday, isSameDay } from 'date-fns';
import { History, MapPin, Navigation, Gauge, Filter, ChevronDown, ChevronRight, Eye } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { LocationEntry, HistoryFilter } from './types';
import { formatCoordinates, bearingToDirection, formatSpeed } from './types';

interface LocationHistoryListProps {
  /** List of historical locations (not including current) */
  history: LocationEntry[];
  /** Current location for comparison */
  currentLocation?: LocationEntry | null;
  /** Callback when a history item is clicked (e.g., to center map) */
  onLocationSelect?: (location: LocationEntry) => void;
  /** Max height for the scroll area */
  maxHeight?: string;
}

/**
 * Format a date for group headers.
 */
function formatDateHeader(date: Date): string {
  if (isToday(date)) return 'Today';
  if (isYesterday(date)) return 'Yesterday';
  return format(date, 'EEEE, MMMM d, yyyy');
}

/**
 * Format time for individual entries.
 */
function formatTime(isoString: string): string {
  return format(new Date(isoString), 'h:mm a');
}

/**
 * Group locations by date.
 */
function groupByDate(locations: LocationEntry[]): Map<string, LocationEntry[]> {
  const groups = new Map<string, LocationEntry[]>();
  
  for (const location of locations) {
    const date = new Date(location.timestamp);
    const dateKey = format(date, 'yyyy-MM-dd');
    
    if (!groups.has(dateKey)) {
      groups.set(dateKey, []);
    }
    groups.get(dateKey)!.push(location);
  }
  
  return groups;
}

/**
 * Individual location history entry component.
 */
function LocationHistoryEntry({
  location,
  isCurrent,
  onSelect,
}: {
  location: LocationEntry;
  isCurrent: boolean;
  onSelect?: () => void;
}) {
  return (
    <div
      className={`
        flex items-start gap-3 p-3 rounded-lg border
        ${isCurrent ? 'bg-primary/5 border-primary/20' : 'hover:bg-muted/50 cursor-pointer'}
      `}
      onClick={onSelect}
    >
      {/* Time column */}
      <div className="w-16 flex-shrink-0 text-sm font-medium">
        {formatTime(location.timestamp)}
      </div>

      {/* Icon */}
      <div className="flex-shrink-0">
        <MapPin className={`h-4 w-4 ${isCurrent ? 'text-primary' : 'text-muted-foreground'}`} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          {location.named_location && (
            <span className="font-medium">{location.named_location}</span>
          )}
          {isCurrent && (
            <Badge variant="outline" className="text-xs">Current</Badge>
          )}
        </div>
        
        {location.address && (
          <p className="text-sm text-muted-foreground truncate">{location.address}</p>
        )}
        
        <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Navigation className="h-3 w-3" />
            {formatCoordinates(location.latitude, location.longitude)}
          </span>
          
          {location.speed !== undefined && location.speed > 0 && (
            <span className="flex items-center gap-1">
              <Gauge className="h-3 w-3" />
              {formatSpeed(location.speed)}
              {location.bearing !== undefined && ` ${bearingToDirection(location.bearing)}`}
            </span>
          )}
        </div>
      </div>

      {/* View on map button */}
      {!isCurrent && onSelect && (
        <Button
          variant="ghost"
          size="sm"
          className="flex-shrink-0"
          onClick={(e) => {
            e.stopPropagation();
            onSelect();
          }}
        >
          <Eye className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}

/**
 * Collapsible date group component.
 */
function DateGroup({
  dateKey,
  locations,
  currentLocation,
  onLocationSelect,
  defaultExpanded = true,
}: {
  dateKey: string;
  locations: LocationEntry[];
  currentLocation?: LocationEntry | null;
  onLocationSelect?: (location: LocationEntry) => void;
  defaultExpanded?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const date = new Date(dateKey);
  
  return (
    <div className="mb-4">
      <button
        className="flex items-center gap-2 w-full text-left py-2 px-1 hover:bg-muted/50 rounded"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        <span className="text-sm font-semibold">{formatDateHeader(date)}</span>
        <Badge variant="secondary" className="text-xs ml-auto">
          {locations.length}
        </Badge>
      </button>
      
      {isExpanded && (
        <div className="space-y-2 mt-2 pl-6">
          {locations.map((location, index) => {
            const isCurrent = currentLocation
              ? location.latitude === currentLocation.latitude &&
                location.longitude === currentLocation.longitude &&
                isSameDay(new Date(location.timestamp), new Date(currentLocation.timestamp))
              : false;
            
            return (
              <LocationHistoryEntry
                key={`${location.timestamp}-${index}`}
                location={location}
                isCurrent={isCurrent}
                onSelect={() => onLocationSelect?.(location)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

export function LocationHistoryList({
  history,
  currentLocation,
  onLocationSelect,
  maxHeight = '400px',
}: LocationHistoryListProps) {
  // Filter state
  const [filter, setFilter] = useState<HistoryFilter>({
    namedOnly: false,
    limit: 20,
    sortOrder: 'desc',
  });
  const [showFilters, setShowFilters] = useState(false);

  // Apply filters and sorting
  const filteredHistory = useMemo(() => {
    let result = [...history];
    
    // Filter by named locations only
    if (filter.namedOnly) {
      result = result.filter((loc) => loc.named_location);
    }
    
    // Sort
    result.sort((a, b) => {
      const diff = new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      return filter.sortOrder === 'desc' ? diff : -diff;
    });
    
    // Limit
    result = result.slice(0, filter.limit);
    
    return result;
  }, [history, filter]);

  // Group by date
  const groupedHistory = useMemo(() => {
    return groupByDate(filteredHistory);
  }, [filteredHistory]);

  // Convert to array for rendering (already sorted)
  const sortedGroups = useMemo(() => {
    return Array.from(groupedHistory.entries()).sort((a, b) => {
      const diff = new Date(b[0]).getTime() - new Date(a[0]).getTime();
      return filter.sortOrder === 'desc' ? diff : -diff;
    });
  }, [groupedHistory, filter.sortOrder]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <History className="h-4 w-4" />
            Location History
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter className="h-4 w-4 mr-1" />
            Filter
          </Button>
        </div>

        {/* Filter controls */}
        {showFilters && (
          <div className="flex items-center gap-4 pt-3 flex-wrap">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="named-only"
                checked={filter.namedOnly}
                onCheckedChange={(checked) =>
                  setFilter((f) => ({ ...f, namedOnly: checked === true }))
                }
              />
              <Label htmlFor="named-only" className="text-sm font-normal cursor-pointer">
                Named only
              </Label>
            </div>

            <div className="flex items-center gap-2">
              <Label className="text-sm font-normal">Show:</Label>
              <Select
                value={String(filter.limit)}
                onValueChange={(value) =>
                  setFilter((f) => ({ ...f, limit: parseInt(value, 10) }))
                }
              >
                <SelectTrigger className="w-20 h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="10">10</SelectItem>
                  <SelectItem value="20">20</SelectItem>
                  <SelectItem value="50">50</SelectItem>
                  <SelectItem value="100">100</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Label className="text-sm font-normal">Sort:</Label>
              <Select
                value={filter.sortOrder}
                onValueChange={(value: 'asc' | 'desc') =>
                  setFilter((f) => ({ ...f, sortOrder: value }))
                }
              >
                <SelectTrigger className="w-28 h-8">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="desc">Newest first</SelectItem>
                  <SelectItem value="asc">Oldest first</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent>
        {history.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <History className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No location history</p>
            <p className="text-xs mt-1">History will appear as locations are updated</p>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No locations match filters</p>
            <p className="text-xs mt-1">Try adjusting the filter settings</p>
          </div>
        ) : (
          <>
            <ScrollArea style={{ maxHeight }}>
              <div className="pr-4">
                {sortedGroups.map(([dateKey, locations], index) => (
                  <DateGroup
                    key={dateKey}
                    dateKey={dateKey}
                    locations={locations}
                    currentLocation={currentLocation}
                    onLocationSelect={onLocationSelect}
                    defaultExpanded={index === 0} // Only expand first group by default
                  />
                ))}
              </div>
            </ScrollArea>

            {/* Summary */}
            <div className="flex items-center justify-between text-xs text-muted-foreground pt-3 mt-3 border-t">
              <span>
                Showing {filteredHistory.length} of {history.length} locations
              </span>
              {filteredHistory.length < history.length && (
                <Button
                  variant="link"
                  size="sm"
                  className="h-auto p-0 text-xs"
                  onClick={() =>
                    setFilter((f) => ({ ...f, limit: Math.min(f.limit + 20, history.length) }))
                  }
                >
                  Load more
                </Button>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
