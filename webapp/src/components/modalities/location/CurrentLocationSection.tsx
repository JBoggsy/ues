/**
 * Combined component showing map and current location details side-by-side.
 * This matches the original design mockup with map on left, details on right.
 */
import { MapPin, Navigation, Mountain, Target, Gauge, Compass, Loader2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useRef, useMemo } from 'react';
import { useReverseGeocoding } from './useGeocoding';
import type { LocationState, LocationEntry } from './types';
import { formatCoordinates, bearingToDirection, formatSpeed } from './types';

// Fix for default marker icons in Leaflet with bundlers
// @ts-expect-error - Leaflet icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom icon for current location (blue)
const currentLocationIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-blue.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

// Custom icon for history locations (gray)
const historyLocationIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-grey.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface CurrentLocationSectionProps {
  /** Location state from API */
  locationState: LocationState | null | undefined;
  /** Whether data is still loading */
  isLoading?: boolean;
  /** Current location object for map */
  currentLocation?: {
    latitude: number;
    longitude: number;
    address?: string;
    named_location?: string;
  } | null;
  /** Historical locations for map */
  historyLocations?: LocationEntry[];
  /** Whether to show history markers on map */
  showHistory: boolean;
  /** Callback when show history changes */
  onShowHistoryChange: (show: boolean) => void;
  /** Callback when a history location is clicked */
  onLocationClick?: (location: LocationEntry) => void;
}

/**
 * Component to recenter map when location changes.
 */
function MapRecenter({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  const prevLatRef = useRef<number | undefined>(undefined);
  const prevLngRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (prevLatRef.current !== lat || prevLngRef.current !== lng) {
      map.setView([lat, lng], map.getZoom());
      prevLatRef.current = lat;
      prevLngRef.current = lng;
    }
  }, [map, lat, lng]);

  return null;
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
    <div className="flex items-center gap-2 py-0.5">
      <Icon className={`h-3.5 w-3.5 flex-shrink-0 ${muted ? 'text-muted-foreground' : 'text-primary'}`} />
      <span className="text-xs text-muted-foreground">{label}:</span>
      <span className={`text-xs ${muted ? 'text-muted-foreground' : ''}`}>{value}</span>
    </div>
  );
}

/**
 * Format a location entry for popup display.
 */
function formatPopupContent(location: LocationEntry, isCurrent: boolean): string {
  const lines: string[] = [];
  
  if (location.named_location) {
    lines.push(`<strong>${location.named_location}</strong>`);
  }
  
  if (location.address) {
    lines.push(location.address);
  }
  
  lines.push(`<span class="text-muted-foreground">${formatCoordinates(location.latitude, location.longitude)}</span>`);
  
  if (!isCurrent) {
    const time = new Date(location.timestamp).toLocaleString();
    lines.push(`<span class="text-xs text-muted-foreground">${time}</span>`);
  }
  
  return lines.join('<br/>');
}

export function CurrentLocationSection({
  locationState,
  isLoading,
  currentLocation,
  historyLocations = [],
  showHistory,
  onShowHistoryChange,
  onLocationClick,
}: CurrentLocationSectionProps) {
  // Reverse geocoding for current location
  const { address: resolvedAddress, isLoading: isGeocodingLoading, lookup: lookupAddress } = useReverseGeocoding();
  
  // Look up address when location changes (only if no address provided)
  useEffect(() => {
    if (
      locationState?.current_latitude != null &&
      locationState?.current_longitude != null &&
      !locationState?.current_address &&
      !locationState?.current_named_location
    ) {
      lookupAddress(locationState.current_latitude, locationState.current_longitude);
    }
  }, [locationState?.current_latitude, locationState?.current_longitude, locationState?.current_address, locationState?.current_named_location, lookupAddress]);
  
  // Default center if no location set
  const defaultCenter = useMemo(
    () => ({ lat: 37.7749, lng: -122.4194 }), // San Francisco
    []
  );

  const center = useMemo(() => {
    if (currentLocation?.latitude && currentLocation?.longitude) {
      return { lat: currentLocation.latitude, lng: currentLocation.longitude };
    }
    return defaultCenter;
  }, [currentLocation, defaultCenter]);

  const hasLocation = locationState?.current_latitude != null && locationState?.current_longitude != null;

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-6 bg-muted rounded w-1/3" />
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Current Location
          </CardTitle>
          <div className="flex items-center gap-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="show-history-map"
                checked={showHistory}
                onCheckedChange={(checked) => onShowHistoryChange(checked === true)}
              />
              <Label htmlFor="show-history-map" className="text-xs font-normal cursor-pointer">
                Show history ({historyLocations.length})
              </Label>
            </div>
            {hasLocation && (
              <Badge variant="outline" className="text-xs">
                {locationState?.update_count} update{locationState?.update_count !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2">
          {/* Left side: Map */}
          <div className="h-64 md:h-80 rounded-lg overflow-hidden border">
            <MapContainer
              center={[center.lat, center.lng]}
              zoom={13}
              style={{ height: '100%', width: '100%' }}
              scrollWheelZoom={true}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {/* Recenter map when location changes */}
              {hasLocation && (
                <MapRecenter lat={center.lat} lng={center.lng} />
              )}

              {/* Current location marker */}
              {hasLocation && (
                <Marker
                  position={[locationState!.current_latitude!, locationState!.current_longitude!]}
                  icon={currentLocationIcon}
                >
                  <Popup>
                    <div
                      dangerouslySetInnerHTML={{
                        __html: formatPopupContent(
                          {
                            timestamp: new Date().toISOString(),
                            latitude: locationState!.current_latitude!,
                            longitude: locationState!.current_longitude!,
                            address: locationState!.current_address ?? undefined,
                            named_location: locationState!.current_named_location ?? undefined,
                            is_current: true,
                          },
                          true
                        ),
                      }}
                    />
                  </Popup>
                </Marker>
              )}

              {/* History markers */}
              {showHistory &&
                historyLocations.map((location, index) => (
                  <Marker
                    key={`history-${index}-${location.timestamp}`}
                    position={[location.latitude, location.longitude]}
                    icon={historyLocationIcon}
                    eventHandlers={{
                      click: () => onLocationClick?.(location),
                    }}
                  >
                    <Popup>
                      <div
                        dangerouslySetInnerHTML={{
                          __html: formatPopupContent(location, false),
                        }}
                      />
                    </Popup>
                  </Marker>
                ))}
            </MapContainer>
          </div>

          {/* Right side: Details */}
          <div className="flex flex-col">
            {!hasLocation ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <MapPin className="h-8 w-8 mb-2 opacity-50" />
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
                  {locationState?.current_address ? (
                    <p className="text-sm text-muted-foreground">{locationState.current_address}</p>
                  ) : isGeocodingLoading ? (
                    <p className="text-sm text-muted-foreground flex items-center gap-1">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Resolving address...
                    </p>
                  ) : resolvedAddress ? (
                    <p className="text-sm text-muted-foreground">{resolvedAddress}</p>
                  ) : null}
                </div>

                <Separator />

                {/* Coordinates and details */}
                <div className="space-y-0.5">
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
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
