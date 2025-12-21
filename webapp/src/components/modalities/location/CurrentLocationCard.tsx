/**
 * Card component displaying current location details.
 * Shows coordinates, address, named location, and motion data.
 */
import { MapPin, Navigation, Mountain, Target, Gauge, Compass } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import type { LocationState } from './types';
import { formatCoordinates, bearingToDirection, formatSpeed } from './types';

interface CurrentLocationCardProps {
  /** Location state from API */
  locationState: LocationState | null | undefined;
  /** Whether data is still loading */
  isLoading?: boolean;
}

/**
 * Format the last updated timestamp for display.
 */
function formatLastUpdated(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

/**
 * Detail row component for consistent styling.
 */
function DetailRow({
  icon: Icon,
  label,
  value,
  muted = false,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number | undefined | null;
  muted?: boolean;
}) {
  if (value === undefined || value === null) return null;
  
  return (
    <div className="flex items-center gap-2 py-1">
      <Icon className={`h-4 w-4 ${muted ? 'text-muted-foreground' : 'text-primary'}`} />
      <span className="text-sm text-muted-foreground">{label}:</span>
      <span className={`text-sm ${muted ? 'text-muted-foreground' : ''}`}>{value}</span>
    </div>
  );
}

export function CurrentLocationCard({ locationState, isLoading }: CurrentLocationCardProps) {
  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-6 bg-muted rounded w-1/3" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 bg-muted rounded w-2/3" />
            <div className="h-4 bg-muted rounded w-1/2" />
            <div className="h-4 bg-muted rounded w-3/4" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const hasLocation = locationState?.current_latitude != null && locationState?.current_longitude != null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Current Location
          </CardTitle>
          {hasLocation && (
            <Badge variant="outline" className="text-xs">
              {locationState?.update_count} update{locationState?.update_count !== 1 ? 's' : ''}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {!hasLocation ? (
          <div className="text-center py-6 text-muted-foreground">
            <MapPin className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>No location set</p>
            <p className="text-xs mt-1">Update the location to begin tracking</p>
          </div>
        ) : (
          <div className="space-y-3">
            {/* Primary location info */}
            <div>
              {locationState?.current_named_location && (
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="secondary" className="text-sm font-medium">
                    {locationState.current_named_location}
                  </Badge>
                </div>
              )}
              {locationState?.current_address && (
                <p className="text-sm text-muted-foreground">{locationState.current_address}</p>
              )}
            </div>

            <Separator />

            {/* Coordinates and details */}
            <div className="grid grid-cols-1 gap-1">
              <DetailRow
                icon={Navigation}
                label="Coordinates"
                value={formatCoordinates(locationState!.current_latitude!, locationState!.current_longitude!)}
              />
              <DetailRow
                icon={Mountain}
                label="Altitude"
                value={locationState?.current_altitude != null ? `${locationState.current_altitude}m` : undefined}
              />
              <DetailRow
                icon={Target}
                label="Accuracy"
                value={locationState?.current_accuracy != null ? `±${locationState.current_accuracy}m` : undefined}
                muted
              />
              <DetailRow
                icon={Gauge}
                label="Speed"
                value={locationState?.current_speed != null ? formatSpeed(locationState.current_speed) : undefined}
              />
              <DetailRow
                icon={Compass}
                label="Bearing"
                value={
                  locationState?.current_bearing != null
                    ? `${locationState.current_bearing}° ${bearingToDirection(locationState.current_bearing)}`
                    : undefined
                }
              />
            </div>

            <Separator />

            {/* Last updated */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Last updated</span>
              <span>{formatLastUpdated(locationState!.last_updated)}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
