/**
 * Location modality form component.
 * 
 * Allows users to create location update events with coordinates,
 * address, and optional metadata like altitude and speed.
 */
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { ModalityFormProps } from './types';

/**
 * Default data for a new location event.
 */
export const locationDefaultData = {
  latitude: 0,
  longitude: 0,
  address: '',
  named_location: '',
  altitude: null,
  accuracy: null,
  speed: null,
  bearing: null,
};

/**
 * Validate location form data.
 */
export function validateLocationData(data: Record<string, unknown>): string | null {
  const lat = data.latitude as number;
  const lon = data.longitude as number;

  if (lat === undefined || lat === null) {
    return 'Latitude is required';
  }
  if (lon === undefined || lon === null) {
    return 'Longitude is required';
  }
  if (lat < -90 || lat > 90) {
    return 'Latitude must be between -90 and 90';
  }
  if (lon < -180 || lon > 180) {
    return 'Longitude must be between -180 and 180';
  }

  const accuracy = data.accuracy as number | null;
  if (accuracy !== null && accuracy !== undefined && accuracy < 0) {
    return 'Accuracy must be non-negative';
  }

  const speed = data.speed as number | null;
  if (speed !== null && speed !== undefined && speed < 0) {
    return 'Speed must be non-negative';
  }

  const bearing = data.bearing as number | null;
  if (bearing !== null && bearing !== undefined && (bearing < 0 || bearing > 360)) {
    return 'Bearing must be between 0 and 360';
  }

  return null;
}

/**
 * Form component for creating location events.
 */
export function LocationForm({ data, onChange, disabled }: ModalityFormProps) {
  const handleChange = (field: string, value: string | number | null) => {
    onChange({ ...data, [field]: value });
  };

  const parseNumber = (value: string, allowNull = false): number | null => {
    if (value === '' && allowNull) return null;
    const num = parseFloat(value);
    return isNaN(num) ? (allowNull ? null : 0) : num;
  };

  return (
    <div className="space-y-4">
      {/* Required Fields */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="latitude">
            Latitude <span className="text-destructive">*</span>
          </Label>
          <Input
            id="latitude"
            type="number"
            step="any"
            min="-90"
            max="90"
            placeholder="-90 to 90"
            value={data.latitude as number}
            onChange={(e) => handleChange('latitude', parseNumber(e.target.value))}
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">
            Decimal degrees (-90 to 90)
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="longitude">
            Longitude <span className="text-destructive">*</span>
          </Label>
          <Input
            id="longitude"
            type="number"
            step="any"
            min="-180"
            max="180"
            placeholder="-180 to 180"
            value={data.longitude as number}
            onChange={(e) => handleChange('longitude', parseNumber(e.target.value))}
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">
            Decimal degrees (-180 to 180)
          </p>
        </div>
      </div>

      {/* Address Fields */}
      <div className="space-y-2">
        <Label htmlFor="address">Address</Label>
        <Input
          id="address"
          type="text"
          placeholder="123 Main St, City, State"
          value={(data.address as string) || ''}
          onChange={(e) => handleChange('address', e.target.value || null)}
          disabled={disabled}
        />
        <p className="text-xs text-muted-foreground">
          Human-readable address or location description
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="named_location">Named Location</Label>
        <Input
          id="named_location"
          type="text"
          placeholder="Home, Office, Gym, etc."
          value={(data.named_location as string) || ''}
          onChange={(e) => handleChange('named_location', e.target.value || null)}
          disabled={disabled}
        />
        <p className="text-xs text-muted-foreground">
          Semantic name for the location (e.g., "Home", "Office")
        </p>
      </div>

      {/* Optional Metadata */}
      <div className="border-t pt-4">
        <p className="text-sm font-medium mb-3 text-muted-foreground">
          Optional Metadata
        </p>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="altitude">Altitude (m)</Label>
            <Input
              id="altitude"
              type="number"
              step="any"
              placeholder="Meters above sea level"
              value={data.altitude !== null && data.altitude !== undefined ? (data.altitude as number) : ''}
              onChange={(e) => handleChange('altitude', parseNumber(e.target.value, true))}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="accuracy">Accuracy (m)</Label>
            <Input
              id="accuracy"
              type="number"
              step="any"
              min="0"
              placeholder="Accuracy radius"
              value={data.accuracy !== null && data.accuracy !== undefined ? (data.accuracy as number) : ''}
              onChange={(e) => handleChange('accuracy', parseNumber(e.target.value, true))}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="speed">Speed (m/s)</Label>
            <Input
              id="speed"
              type="number"
              step="any"
              min="0"
              placeholder="Meters per second"
              value={data.speed !== null && data.speed !== undefined ? (data.speed as number) : ''}
              onChange={(e) => handleChange('speed', parseNumber(e.target.value, true))}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="bearing">Bearing (°)</Label>
            <Input
              id="bearing"
              type="number"
              step="any"
              min="0"
              max="360"
              placeholder="0-360 (0 = North)"
              value={data.bearing !== null && data.bearing !== undefined ? (data.bearing as number) : ''}
              onChange={(e) => handleChange('bearing', parseNumber(e.target.value, true))}
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      {/* Quick Presets */}
      <div className="border-t pt-4">
        <p className="text-sm font-medium mb-3 text-muted-foreground">
          Quick Presets
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="px-3 py-1.5 text-xs rounded-md bg-muted hover:bg-muted/80 transition-colors"
            onClick={() => onChange({
              ...data,
              latitude: 40.7128,
              longitude: -74.0060,
              address: 'New York, NY, USA',
              named_location: '',
            })}
            disabled={disabled}
          >
            New York
          </button>
          <button
            type="button"
            className="px-3 py-1.5 text-xs rounded-md bg-muted hover:bg-muted/80 transition-colors"
            onClick={() => onChange({
              ...data,
              latitude: 37.7749,
              longitude: -122.4194,
              address: 'San Francisco, CA, USA',
              named_location: '',
            })}
            disabled={disabled}
          >
            San Francisco
          </button>
          <button
            type="button"
            className="px-3 py-1.5 text-xs rounded-md bg-muted hover:bg-muted/80 transition-colors"
            onClick={() => onChange({
              ...data,
              latitude: 51.5074,
              longitude: -0.1278,
              address: 'London, UK',
              named_location: '',
            })}
            disabled={disabled}
          >
            London
          </button>
          <button
            type="button"
            className="px-3 py-1.5 text-xs rounded-md bg-muted hover:bg-muted/80 transition-colors"
            onClick={() => onChange({
              ...data,
              latitude: 35.6762,
              longitude: 139.6503,
              address: 'Tokyo, Japan',
              named_location: '',
            })}
            disabled={disabled}
          >
            Tokyo
          </button>
        </div>
      </div>
    </div>
  );
}
