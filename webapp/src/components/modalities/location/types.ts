/**
 * Type definitions for the Location modality viewer.
 */

/**
 * A single location entry (current or historical).
 */
export interface LocationEntry {
  timestamp: string;
  latitude: number;
  longitude: number;
  address?: string;
  named_location?: string;
  altitude?: number;
  accuracy?: number;
  speed?: number;
  bearing?: number;
  is_current?: boolean;
}

/**
 * Location state from the API (model_dump() format).
 * Uses flat field names like current_latitude, current_longitude, etc.
 */
export interface LocationState {
  modality_type: 'location';
  last_updated: string;
  update_count: number;
  // Flat current location fields
  current_latitude?: number | null;
  current_longitude?: number | null;
  current_address?: string | null;
  current_named_location?: string | null;
  current_altitude?: number | null;
  current_accuracy?: number | null;
  current_speed?: number | null;
  current_bearing?: number | null;
  // History entries
  location_history: LocationEntry[];
  max_history_size: number;
}

/**
 * A saved/named location stored in cookies.
 */
export interface SavedLocation {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  address?: string;
  altitude?: number;
}

/**
 * Request to update location via API.
 */
export interface UpdateLocationRequest {
  latitude: number;
  longitude: number;
  address?: string;
  named_location?: string;
  altitude?: number;
  accuracy?: number;
  speed?: number;
  bearing?: number;
}

/**
 * History filter options.
 */
export interface HistoryFilter {
  namedOnly: boolean;
  limit: number;
  sortOrder: 'asc' | 'desc';
}

/**
 * Preset city locations for quick testing.
 */
export interface PresetCity {
  name: string;
  latitude: number;
  longitude: number;
  country: string;
}

/**
 * Common preset cities for testing.
 */
export const PRESET_CITIES: PresetCity[] = [
  { name: 'New York', latitude: 40.7128, longitude: -74.0060, country: 'USA' },
  { name: 'San Francisco', latitude: 37.7749, longitude: -122.4194, country: 'USA' },
  { name: 'Los Angeles', latitude: 34.0522, longitude: -118.2437, country: 'USA' },
  { name: 'Chicago', latitude: 41.8781, longitude: -87.6298, country: 'USA' },
  { name: 'London', latitude: 51.5074, longitude: -0.1278, country: 'UK' },
  { name: 'Paris', latitude: 48.8566, longitude: 2.3522, country: 'France' },
  { name: 'Tokyo', latitude: 35.6762, longitude: 139.6503, country: 'Japan' },
  { name: 'Sydney', latitude: -33.8688, longitude: 151.2093, country: 'Australia' },
  { name: 'Berlin', latitude: 52.5200, longitude: 13.4050, country: 'Germany' },
  { name: 'Toronto', latitude: 43.6532, longitude: -79.3832, country: 'Canada' },
];

/**
 * Convert bearing degrees to compass direction.
 */
export function bearingToDirection(bearing: number): string {
  const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const index = Math.round(bearing / 45) % 8;
  return directions[index];
}

/**
 * Format coordinates for display.
 */
export function formatCoordinates(lat: number, lon: number, precision = 4): string {
  return `${lat.toFixed(precision)}, ${lon.toFixed(precision)}`;
}

/**
 * Format speed for display.
 */
export function formatSpeed(speed: number): string {
  if (speed < 1) return '0 m/s';
  if (speed < 10) return `${speed.toFixed(1)} m/s`;
  return `${Math.round(speed)} m/s`;
}
