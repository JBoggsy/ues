/**
 * Weather modality form component.
 * 
 * Allows users to create weather update events with simplified inputs
 * that get converted to the full WeatherReport structure.
 */
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { ModalityFormProps } from './types';

/**
 * Weather condition presets for easy selection.
 */
const WEATHER_CONDITIONS = [
  { id: 800, main: 'Clear', description: 'clear sky', icon: '01d' },
  { id: 801, main: 'Clouds', description: 'few clouds', icon: '02d' },
  { id: 802, main: 'Clouds', description: 'scattered clouds', icon: '03d' },
  { id: 803, main: 'Clouds', description: 'broken clouds', icon: '04d' },
  { id: 804, main: 'Clouds', description: 'overcast clouds', icon: '04d' },
  { id: 500, main: 'Rain', description: 'light rain', icon: '10d' },
  { id: 501, main: 'Rain', description: 'moderate rain', icon: '10d' },
  { id: 502, main: 'Rain', description: 'heavy rain', icon: '10d' },
  { id: 300, main: 'Drizzle', description: 'light drizzle', icon: '09d' },
  { id: 200, main: 'Thunderstorm', description: 'thunderstorm', icon: '11d' },
  { id: 600, main: 'Snow', description: 'light snow', icon: '13d' },
  { id: 601, main: 'Snow', description: 'snow', icon: '13d' },
  { id: 602, main: 'Snow', description: 'heavy snow', icon: '13d' },
  { id: 701, main: 'Mist', description: 'mist', icon: '50d' },
  { id: 741, main: 'Fog', description: 'fog', icon: '50d' },
] as const;

/**
 * Common location presets with coordinates.
 */
const LOCATION_PRESETS = [
  { name: 'New York City', lat: 40.7128, lon: -74.006, tz: 'America/New_York' },
  { name: 'Los Angeles', lat: 34.0522, lon: -118.2437, tz: 'America/Los_Angeles' },
  { name: 'Chicago', lat: 41.8781, lon: -87.6298, tz: 'America/Chicago' },
  { name: 'London', lat: 51.5074, lon: -0.1278, tz: 'Europe/London' },
  { name: 'Tokyo', lat: 35.6762, lon: 139.6503, tz: 'Asia/Tokyo' },
  { name: 'Sydney', lat: -33.8688, lon: 151.2093, tz: 'Australia/Sydney' },
];

/**
 * Convert Fahrenheit to Kelvin.
 */
function fahrenheitToKelvin(f: number): number {
  return (f - 32) * 5 / 9 + 273.15;
}

/**
 * Default data for a new weather event.
 */
export const weatherDefaultData = {
  latitude: 40.7128,
  longitude: -74.006,
  timezone: 'America/New_York',
  condition_id: 800, // Clear sky
  temp_f: 72,
  humidity: 50,
  wind_speed: 5,
  wind_deg: 180,
  clouds: 0,
  pressure: 1013,
  visibility: 10000,
};

/**
 * Validate weather form data.
 */
export function validateWeatherData(data: Record<string, unknown>): string | null {
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

  const temp = data.temp_f as number;
  if (temp === undefined || temp === null) {
    return 'Temperature is required';
  }

  const humidity = data.humidity as number;
  if (humidity !== undefined && humidity !== null && (humidity < 0 || humidity > 100)) {
    return 'Humidity must be between 0 and 100';
  }

  const clouds = data.clouds as number;
  if (clouds !== undefined && clouds !== null && (clouds < 0 || clouds > 100)) {
    return 'Cloud coverage must be between 0 and 100';
  }

  return null;
}

/**
 * Transform form data to WeatherInput format expected by API.
 */
export function transformWeatherData(data: Record<string, unknown>): Record<string, unknown> {
  const lat = data.latitude as number;
  const lon = data.longitude as number;
  const timezone = (data.timezone as string) || 'UTC';
  const conditionId = data.condition_id as number;
  const tempK = fahrenheitToKelvin(data.temp_f as number);
  const humidity = (data.humidity as number) || 50;
  const windSpeed = (data.wind_speed as number) || 0;
  const windDeg = (data.wind_deg as number) || 0;
  const clouds = (data.clouds as number) || 0;
  const pressure = (data.pressure as number) || 1013;
  const visibility = (data.visibility as number) || 10000;

  // Find the weather condition
  const condition = WEATHER_CONDITIONS.find(c => c.id === conditionId) || WEATHER_CONDITIONS[0];

  // Current timestamp
  const now = Math.floor(Date.now() / 1000);
  const sunrise = now - 21600; // ~6 hours ago
  const sunset = now + 21600; // ~6 hours from now

  return {
    latitude: lat,
    longitude: lon,
    report: {
      lat,
      lon,
      timezone,
      timezone_offset: 0,
      current: {
        dt: now,
        sunrise,
        sunset,
        temp: tempK,
        feels_like: tempK,
        pressure,
        humidity,
        dew_point: tempK - 10,
        uvi: 5,
        clouds,
        visibility,
        wind_speed: windSpeed,
        wind_deg: windDeg,
        weather: [{
          id: condition.id,
          main: condition.main,
          description: condition.description,
          icon: condition.icon,
        }],
      },
    },
  };
}

/**
 * Form component for creating weather events.
 */
export function WeatherForm({ data, onChange, disabled }: ModalityFormProps) {
  const handleChange = (field: string, value: string | number | null) => {
    onChange({ ...data, [field]: value });
  };

  const parseNumber = (value: string, allowNull = false): number | null => {
    if (value === '' && allowNull) return null;
    const num = parseFloat(value);
    return isNaN(num) ? (allowNull ? null : 0) : num;
  };

  const handleLocationPreset = (presetName: string) => {
    const preset = LOCATION_PRESETS.find(p => p.name === presetName);
    if (preset) {
      onChange({
        ...data,
        latitude: preset.lat,
        longitude: preset.lon,
        timezone: preset.tz,
      });
    }
  };

  return (
    <div className="space-y-4">
      {/* Location Section */}
      <div className="space-y-2">
        <Label>Quick Location</Label>
        <Select onValueChange={handleLocationPreset} disabled={disabled}>
          <SelectTrigger>
            <SelectValue placeholder="Select a city..." />
          </SelectTrigger>
          <SelectContent>
            {LOCATION_PRESETS.map((preset) => (
              <SelectItem key={preset.name} value={preset.name}>
                {preset.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="weather_latitude">
            Latitude <span className="text-destructive">*</span>
          </Label>
          <Input
            id="weather_latitude"
            type="number"
            step="any"
            min="-90"
            max="90"
            placeholder="-90 to 90"
            value={data.latitude as number}
            onChange={(e) => handleChange('latitude', parseNumber(e.target.value))}
            disabled={disabled}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="weather_longitude">
            Longitude <span className="text-destructive">*</span>
          </Label>
          <Input
            id="weather_longitude"
            type="number"
            step="any"
            min="-180"
            max="180"
            placeholder="-180 to 180"
            value={data.longitude as number}
            onChange={(e) => handleChange('longitude', parseNumber(e.target.value))}
            disabled={disabled}
          />
        </div>
      </div>

      {/* Weather Condition */}
      <div className="space-y-2">
        <Label>
          Weather Condition <span className="text-destructive">*</span>
        </Label>
        <Select
          value={String(data.condition_id || 800)}
          onValueChange={(value) => handleChange('condition_id', parseInt(value))}
          disabled={disabled}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select condition..." />
          </SelectTrigger>
          <SelectContent>
            {WEATHER_CONDITIONS.map((condition) => (
              <SelectItem key={condition.id} value={String(condition.id)}>
                {condition.description.charAt(0).toUpperCase() + condition.description.slice(1)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Temperature and Humidity */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="weather_temp">
            Temperature (°F) <span className="text-destructive">*</span>
          </Label>
          <Input
            id="weather_temp"
            type="number"
            step="1"
            placeholder="72"
            value={data.temp_f as number}
            onChange={(e) => handleChange('temp_f', parseNumber(e.target.value))}
            disabled={disabled}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="weather_humidity">Humidity (%)</Label>
          <Input
            id="weather_humidity"
            type="number"
            step="1"
            min="0"
            max="100"
            placeholder="50"
            value={data.humidity as number}
            onChange={(e) => handleChange('humidity', parseNumber(e.target.value))}
            disabled={disabled}
          />
        </div>
      </div>

      {/* Wind */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="weather_wind_speed">Wind Speed (m/s)</Label>
          <Input
            id="weather_wind_speed"
            type="number"
            step="0.1"
            min="0"
            placeholder="5"
            value={data.wind_speed as number}
            onChange={(e) => handleChange('wind_speed', parseNumber(e.target.value))}
            disabled={disabled}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="weather_wind_deg">Wind Direction (°)</Label>
          <Input
            id="weather_wind_deg"
            type="number"
            step="1"
            min="0"
            max="360"
            placeholder="180 (South)"
            value={data.wind_deg as number}
            onChange={(e) => handleChange('wind_deg', parseNumber(e.target.value))}
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">
            0=N, 90=E, 180=S, 270=W
          </p>
        </div>
      </div>

      {/* Additional Details */}
      <div className="border-t pt-4">
        <p className="text-sm font-medium mb-3 text-muted-foreground">
          Additional Details
        </p>
        
        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="weather_clouds">Clouds (%)</Label>
            <Input
              id="weather_clouds"
              type="number"
              step="1"
              min="0"
              max="100"
              placeholder="0"
              value={data.clouds as number}
              onChange={(e) => handleChange('clouds', parseNumber(e.target.value))}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="weather_pressure">Pressure (hPa)</Label>
            <Input
              id="weather_pressure"
              type="number"
              step="1"
              placeholder="1013"
              value={data.pressure as number}
              onChange={(e) => handleChange('pressure', parseNumber(e.target.value))}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="weather_visibility">Visibility (m)</Label>
            <Input
              id="weather_visibility"
              type="number"
              step="100"
              min="0"
              max="10000"
              placeholder="10000"
              value={data.visibility as number}
              onChange={(e) => handleChange('visibility', parseNumber(e.target.value))}
              disabled={disabled}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
