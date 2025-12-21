/**
 * Component displaying a list of tracked weather locations.
 */
import { MapPin, Check } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type { WeatherLocationData, UnitSystem } from './types';
import { formatTemperature, getWeatherEmoji, getLocationDisplayName } from './types';

interface WeatherLocationListProps {
  /** Map of location keys to weather data */
  locations: Record<string, WeatherLocationData>;
  /** Currently selected location key */
  selectedLocationKey: string | null;
  /** Callback when a location is selected */
  onSelectLocation: (key: string) => void;
  /** Current unit system */
  units: UnitSystem;
}

/**
 * Format relative time for last updated.
 */
function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
}

export function WeatherLocationList({
  locations,
  selectedLocationKey,
  onSelectLocation,
  units,
}: WeatherLocationListProps) {
  const locationKeys = Object.keys(locations);

  if (locationKeys.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No weather locations tracked</p>
        <p className="text-xs mt-1">Click "Add Location" to get started</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2 border-b">
        <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wide">
          Tracked Locations ({locationKeys.length})
        </h3>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-2 space-y-2">
          {locationKeys.map((key) => {
            const location = locations[key];
            const isSelected = key === selectedLocationKey;
            const current = location.current_report.current;
            const weather = current?.weather?.[0];
            const displayName = getLocationDisplayName(
              location.latitude,
              location.longitude,
              location.current_report
            );

            return (
              <Card
                key={key}
                className={cn(
                  'cursor-pointer transition-colors hover:bg-accent/50',
                  isSelected && 'border-primary bg-accent'
                )}
                onClick={() => onSelectLocation(key)}
              >
                <CardContent className="p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <MapPin className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                      <span className="font-medium truncate">{displayName}</span>
                    </div>
                    {isSelected && (
                      <Check className="h-4 w-4 flex-shrink-0 text-primary" />
                    )}
                  </div>
                  
                  {current && weather && (
                    <div className="mt-2 flex items-center gap-2 text-sm">
                      <span className="text-lg">{getWeatherEmoji(weather.icon)}</span>
                      <span className="font-semibold">
                        {formatTemperature(current.temp, units)}
                      </span>
                      <span className="text-muted-foreground capitalize">
                        {weather.description}
                      </span>
                    </div>
                  )}
                  
                  <div className="mt-1 text-xs text-muted-foreground">
                    Updated: {formatRelativeTime(location.last_updated)}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
