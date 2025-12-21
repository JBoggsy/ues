/**
 * Map picker component for selecting coordinates by clicking on a map.
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, X, Check, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useReverseGeocoding } from './useGeocoding';

// Fix for default marker icons in Leaflet with bundlers
// @ts-expect-error - Leaflet icon fix
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom icon for selected location (red)
const selectedLocationIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface MapPickerProps {
  /** Initial latitude (for centering the map) */
  initialLat?: number;
  /** Initial longitude (for centering the map) */
  initialLng?: number;
  /** Callback when a location is confirmed */
  onConfirm: (lat: number, lng: number) => void;
  /** Callback when picker is cancelled */
  onCancel: () => void;
}

/**
 * Component that handles map click events.
 */
function MapClickHandler({
  onLocationSelect,
}: {
  onLocationSelect: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click(e) {
      onLocationSelect(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export function MapPicker({
  initialLat,
  initialLng,
  onConfirm,
  onCancel,
}: MapPickerProps) {
  // Selected coordinates
  const [selectedLat, setSelectedLat] = useState<number | null>(null);
  const [selectedLng, setSelectedLng] = useState<number | null>(null);
  
  // Reverse geocoding for selected location
  const { address, isLoading: isGeocodingLoading, lookup: lookupAddress, clear: clearAddress } = useReverseGeocoding();

  // Default center - use initial coords or San Francisco
  const center = useMemo(() => {
    if (initialLat != null && initialLng != null) {
      return { lat: initialLat, lng: initialLng };
    }
    return { lat: 37.7749, lng: -122.4194 };
  }, [initialLat, initialLng]);

  // Handle map click
  const handleLocationSelect = useCallback((lat: number, lng: number) => {
    setSelectedLat(lat);
    setSelectedLng(lng);
    lookupAddress(lat, lng);
  }, [lookupAddress]);
  
  // Clear address when picker is cancelled
  useEffect(() => {
    return () => clearAddress();
  }, [clearAddress]);

  // Confirm selection
  const handleConfirm = useCallback(() => {
    if (selectedLat != null && selectedLng != null) {
      onConfirm(selectedLat, selectedLng);
    }
  }, [selectedLat, selectedLng, onConfirm]);

  const hasSelection = selectedLat != null && selectedLng != null;

  return (
    <Card className="border-2 border-primary">
      <CardHeader className="py-3 px-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            Click on the map to select a location
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={onCancel}
            >
              <X className="h-4 w-4 mr-1" />
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              disabled={!hasSelection}
              onClick={handleConfirm}
            >
              <Check className="h-4 w-4 mr-1" />
              Use Location
            </Button>
          </div>
        </div>
        {hasSelection && (
          <div className="mt-1 space-y-0.5">
            <p className="text-xs text-muted-foreground">
              {selectedLat!.toFixed(6)}, {selectedLng!.toFixed(6)}
            </p>
            {isGeocodingLoading ? (
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Looking up address...
              </p>
            ) : address ? (
              <p className="text-xs font-medium">{address}</p>
            ) : null}
          </div>
        )}
      </CardHeader>
      <CardContent className="p-0">
        <div className="h-64 rounded-b-lg overflow-hidden">
          <MapContainer
            center={[center.lat, center.lng]}
            zoom={initialLat != null ? 13 : 3}
            style={{ height: '100%', width: '100%' }}
            scrollWheelZoom={true}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <MapClickHandler onLocationSelect={handleLocationSelect} />

            {/* Selected location marker */}
            {hasSelection && (
              <Marker
                position={[selectedLat!, selectedLng!]}
                icon={selectedLocationIcon}
              />
            )}
          </MapContainer>
        </div>
      </CardContent>
    </Card>
  );
}
