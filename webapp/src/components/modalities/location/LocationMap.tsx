/**
 * Interactive map component using Leaflet with OpenStreetMap tiles.
 * Displays current location and optional history pins.
 */
import { useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import type { LocationEntry } from './types';
import { formatCoordinates, bearingToDirection } from './types';

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

interface LocationMapProps {
  /** Current location (highlighted with blue marker) */
  currentLocation?: {
    latitude: number;
    longitude: number;
    address?: string;
    named_location?: string;
  } | null;
  /** Historical locations (shown with gray markers when enabled) */
  historyLocations?: LocationEntry[];
  /** Whether to show history markers on the map */
  showHistory: boolean;
  /** Callback when show history toggle changes */
  onShowHistoryChange: (show: boolean) => void;
  /** Optional callback when a location is clicked */
  onLocationClick?: (location: LocationEntry) => void;
  /** Height of the map container */
  height?: string;
}

/**
 * Component to recenter map when location changes.
 */
function MapRecenter({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  const prevLatRef = useRef<number | undefined>(undefined);
  const prevLngRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    // Only recenter if location actually changed
    if (prevLatRef.current !== lat || prevLngRef.current !== lng) {
      map.setView([lat, lng], map.getZoom());
      prevLatRef.current = lat;
      prevLngRef.current = lng;
    }
  }, [map, lat, lng]);

  return null;
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
  
  if (location.altitude !== undefined) {
    lines.push(`Altitude: ${location.altitude}m`);
  }
  
  if (location.speed !== undefined && location.speed > 0) {
    const speedInfo = location.bearing !== undefined
      ? `${location.speed.toFixed(1)} m/s ${bearingToDirection(location.bearing)}`
      : `${location.speed.toFixed(1)} m/s`;
    lines.push(`Speed: ${speedInfo}`);
  }
  
  if (!isCurrent) {
    const time = new Date(location.timestamp).toLocaleString();
    lines.push(`<span class="text-xs text-muted-foreground">${time}</span>`);
  }
  
  return lines.join('<br/>');
}

export function LocationMap({
  currentLocation,
  historyLocations = [],
  showHistory,
  onShowHistoryChange,
  onLocationClick,
  height = '300px',
}: LocationMapProps) {
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

  const hasLocation = currentLocation?.latitude !== undefined;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Map</CardTitle>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="show-history"
              checked={showHistory}
              onCheckedChange={(checked) => onShowHistoryChange(checked === true)}
            />
            <Label htmlFor="show-history" className="text-sm font-normal cursor-pointer">
              Show history ({historyLocations.length})
            </Label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div style={{ height }} className="rounded-b-lg overflow-hidden">
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
                position={[currentLocation!.latitude, currentLocation!.longitude]}
                icon={currentLocationIcon}
              >
                <Popup>
                  <div
                    dangerouslySetInnerHTML={{
                      __html: formatPopupContent(
                        {
                          timestamp: new Date().toISOString(),
                          latitude: currentLocation!.latitude,
                          longitude: currentLocation!.longitude,
                          address: currentLocation!.address,
                          named_location: currentLocation!.named_location,
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

            {/* No location message */}
            {!hasLocation && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-[1000]">
                <p className="text-muted-foreground">No location set</p>
              </div>
            )}
          </MapContainer>
        </div>
      </CardContent>
    </Card>
  );
}
