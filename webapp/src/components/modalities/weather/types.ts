/**
 * Type definitions for the Weather modality viewer.
 */

/**
 * Weather condition from OpenWeather API format.
 */
export interface WeatherCondition {
  id: number;
  main: string;
  description: string;
  icon: string;
}

/**
 * Current weather conditions.
 */
export interface CurrentWeather {
  dt: number;
  sunrise: number;
  sunset: number;
  temp: number;
  feels_like: number;
  pressure: number;
  humidity: number;
  dew_point: number;
  uvi: number;
  clouds: number;
  visibility: number;
  wind_speed: number;
  wind_deg: number;
  wind_gust?: number;
  weather: WeatherCondition[];
}

/**
 * Minutely precipitation forecast.
 */
export interface MinutelyForecast {
  dt: number;
  precipitation: number;
}

/**
 * Hourly weather forecast.
 */
export interface HourlyForecast {
  dt: number;
  temp: number;
  feels_like: number;
  pressure: number;
  humidity: number;
  dew_point: number;
  uvi: number;
  clouds: number;
  visibility?: number;
  wind_speed: number;
  wind_deg: number;
  wind_gust?: number;
  weather: WeatherCondition[];
  pop: number;
  rain?: { '1h': number };
  snow?: { '1h': number };
}

/**
 * Daily temperature breakdown.
 */
export interface DailyTemperature {
  day: number;
  min: number;
  max: number;
  night: number;
  eve: number;
  morn: number;
}

/**
 * Daily feels like temperature breakdown.
 */
export interface DailyFeelsLike {
  day: number;
  night: number;
  eve: number;
  morn: number;
}

/**
 * Daily weather forecast.
 */
export interface DailyForecast {
  dt: number;
  sunrise: number;
  sunset: number;
  moonrise: number;
  moonset: number;
  moon_phase: number;
  summary?: string;
  temp: DailyTemperature;
  feels_like: DailyFeelsLike;
  pressure: number;
  humidity: number;
  dew_point: number;
  wind_speed: number;
  wind_deg: number;
  wind_gust?: number;
  weather: WeatherCondition[];
  clouds: number;
  pop: number;
  rain?: number;
  snow?: number;
  uvi: number;
}

/**
 * Weather alert.
 */
export interface WeatherAlert {
  sender_name: string;
  event: string;
  start: number;
  end: number;
  description: string;
  tags: string[];
}

/**
 * Complete weather report for a location.
 */
export interface WeatherReport {
  lat: number;
  lon: number;
  timezone: string;
  timezone_offset: number;
  current?: CurrentWeather;
  minutely?: MinutelyForecast[];
  hourly?: HourlyForecast[];
  daily?: DailyForecast[];
  alerts?: WeatherAlert[];
}

/**
 * Historical weather report entry.
 */
export interface WeatherHistoryEntry {
  timestamp: string;
  report: WeatherReport;
}

/**
 * Weather data for a single location.
 */
export interface WeatherLocationData {
  latitude: number;
  longitude: number;
  current_report: WeatherReport;
  first_seen: string;
  last_updated: string;
  update_count: number;
  history_count: number;
  /** History from /weather/state endpoint */
  history?: WeatherHistoryEntry[];
  /** History from /environment/modalities/weather endpoint */
  report_history?: WeatherHistoryEntry[];
}

/**
 * Weather state from the API.
 */
export interface WeatherState {
  modality_type: 'weather';
  last_updated: string;
  update_count: number;
  locations: Record<string, WeatherLocationData>;
  location_count: number;
}

/**
 * Request to update weather via API.
 */
export interface UpdateWeatherRequest {
  latitude: number;
  longitude: number;
  report: WeatherReport;
}

/**
 * Unit system for displaying weather data.
 */
export type UnitSystem = 'imperial' | 'metric' | 'standard';

/**
 * Preset city for quick weather location selection.
 */
export interface WeatherPresetCity {
  name: string;
  latitude: number;
  longitude: number;
  region: string;
}

/**
 * Grouped preset cities by region.
 */
export const WEATHER_PRESET_CITIES: Record<string, WeatherPresetCity[]> = {
  'North America': [
    { name: 'New York', latitude: 40.7128, longitude: -74.0060, region: 'North America' },
    { name: 'Los Angeles', latitude: 34.0522, longitude: -118.2437, region: 'North America' },
    { name: 'Chicago', latitude: 41.8781, longitude: -87.6298, region: 'North America' },
    { name: 'Toronto', latitude: 43.6532, longitude: -79.3832, region: 'North America' },
    { name: 'San Francisco', latitude: 37.7749, longitude: -122.4194, region: 'North America' },
    { name: 'Miami', latitude: 25.7617, longitude: -80.1918, region: 'North America' },
  ],
  'Europe': [
    { name: 'London', latitude: 51.5074, longitude: -0.1278, region: 'Europe' },
    { name: 'Paris', latitude: 48.8566, longitude: 2.3522, region: 'Europe' },
    { name: 'Berlin', latitude: 52.5200, longitude: 13.4050, region: 'Europe' },
    { name: 'Madrid', latitude: 40.4168, longitude: -3.7038, region: 'Europe' },
    { name: 'Rome', latitude: 41.9028, longitude: 12.4964, region: 'Europe' },
    { name: 'Amsterdam', latitude: 52.3676, longitude: 4.9041, region: 'Europe' },
  ],
  'Asia-Pacific': [
    { name: 'Tokyo', latitude: 35.6762, longitude: 139.6503, region: 'Asia-Pacific' },
    { name: 'Sydney', latitude: -33.8688, longitude: 151.2093, region: 'Asia-Pacific' },
    { name: 'Singapore', latitude: 1.3521, longitude: 103.8198, region: 'Asia-Pacific' },
    { name: 'Hong Kong', latitude: 22.3193, longitude: 114.1694, region: 'Asia-Pacific' },
    { name: 'Seoul', latitude: 37.5665, longitude: 126.9780, region: 'Asia-Pacific' },
    { name: 'Mumbai', latitude: 19.0760, longitude: 72.8777, region: 'Asia-Pacific' },
  ],
  'South America': [
    { name: 'São Paulo', latitude: -23.5505, longitude: -46.6333, region: 'South America' },
    { name: 'Buenos Aires', latitude: -34.6037, longitude: -58.3816, region: 'South America' },
    { name: 'Rio de Janeiro', latitude: -22.9068, longitude: -43.1729, region: 'South America' },
    { name: 'Lima', latitude: -12.0464, longitude: -77.0428, region: 'South America' },
  ],
};

/**
 * Weather icon mapping from OpenWeather icon codes.
 */
export const WEATHER_ICONS: Record<string, string> = {
  '01d': '☀️',  // clear sky day
  '01n': '🌙',  // clear sky night
  '02d': '⛅',  // few clouds day
  '02n': '☁️',  // few clouds night
  '03d': '☁️',  // scattered clouds
  '03n': '☁️',
  '04d': '☁️',  // broken clouds
  '04n': '☁️',
  '09d': '🌧️',  // shower rain
  '09n': '🌧️',
  '10d': '🌦️',  // rain day
  '10n': '🌧️',  // rain night
  '11d': '⛈️',  // thunderstorm
  '11n': '⛈️',
  '13d': '❄️',  // snow
  '13n': '❄️',
  '50d': '🌫️',  // mist
  '50n': '🌫️',
};

/**
 * Get weather emoji from icon code.
 */
export function getWeatherEmoji(iconCode: string): string {
  return WEATHER_ICONS[iconCode] || '🌡️';
}

/**
 * Convert temperature based on unit system.
 * API stores in Kelvin by default.
 */
export function convertTemperature(kelvin: number, units: UnitSystem): number {
  switch (units) {
    case 'metric':
      return kelvin - 273.15;
    case 'imperial':
      return (kelvin - 273.15) * 9 / 5 + 32;
    case 'standard':
    default:
      return kelvin;
  }
}

/**
 * Format temperature with unit symbol.
 */
export function formatTemperature(kelvin: number, units: UnitSystem): string {
  const temp = convertTemperature(kelvin, units);
  const symbol = units === 'imperial' ? '°F' : units === 'metric' ? '°C' : 'K';
  return `${Math.round(temp)}${symbol}`;
}

/**
 * Convert wind speed based on unit system.
 * API stores in m/s by default.
 */
export function convertWindSpeed(mps: number, units: UnitSystem): number {
  if (units === 'imperial') {
    return mps * 2.23694; // m/s to mph
  }
  return mps; // metric and standard use m/s
}

/**
 * Format wind speed with unit.
 */
export function formatWindSpeed(mps: number, units: UnitSystem): string {
  const speed = convertWindSpeed(mps, units);
  const unit = units === 'imperial' ? 'mph' : 'm/s';
  return `${Math.round(speed)} ${unit}`;
}

/**
 * Convert wind degrees to compass direction.
 */
export function windDegToDirection(deg: number): string {
  const directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const index = Math.round(deg / 22.5) % 16;
  return directions[index];
}

/**
 * Format Unix timestamp to time string.
 */
export function formatTime(timestamp: number, timezoneOffset?: number): string {
  const date = new Date((timestamp + (timezoneOffset || 0)) * 1000);
  return date.toLocaleTimeString('en-US', { 
    hour: 'numeric', 
    minute: '2-digit',
    hour12: true 
  });
}

/**
 * Format Unix timestamp to date string.
 */
export function formatDate(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  return date.toLocaleDateString('en-US', { 
    weekday: 'short',
    month: 'short', 
    day: 'numeric' 
  });
}

/**
 * Format Unix timestamp to day name.
 */
export function formatDayName(timestamp: number): string {
  const date = new Date(timestamp * 1000);
  const today = new Date();
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  
  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  }
  if (date.toDateString() === tomorrow.toDateString()) {
    return 'Tomorrow';
  }
  return date.toLocaleDateString('en-US', { weekday: 'long' });
}

/**
 * Get alert severity level from event type.
 */
export function getAlertSeverity(event: string): 'low' | 'medium' | 'high' | 'extreme' {
  const lowKeywords = ['advisory', 'statement', 'outlook'];
  const highKeywords = ['warning', 'emergency', 'extreme'];
  const extremeKeywords = ['tornado', 'hurricane', 'tsunami', 'evacuation'];
  
  const eventLower = event.toLowerCase();
  
  if (extremeKeywords.some(k => eventLower.includes(k))) return 'extreme';
  if (highKeywords.some(k => eventLower.includes(k))) return 'high';
  if (lowKeywords.some(k => eventLower.includes(k))) return 'low';
  return 'medium';
}

/**
 * Get alert color classes based on severity.
 */
export function getAlertColorClasses(severity: 'low' | 'medium' | 'high' | 'extreme'): string {
  switch (severity) {
    case 'extreme':
      return 'bg-purple-100 border-purple-500 text-purple-900 dark:bg-purple-950 dark:text-purple-100';
    case 'high':
      return 'bg-red-100 border-red-500 text-red-900 dark:bg-red-950 dark:text-red-100';
    case 'medium':
      return 'bg-yellow-100 border-yellow-500 text-yellow-900 dark:bg-yellow-950 dark:text-yellow-100';
    case 'low':
    default:
      return 'bg-blue-100 border-blue-500 text-blue-900 dark:bg-blue-950 dark:text-blue-100';
  }
}

/**
 * Get a display name for a location from coordinates.
 */
export function getLocationDisplayName(
  lat: number, 
  lon: number, 
  report?: WeatherReport
): string {
  // Try to use timezone as a rough location indicator
  if (report?.timezone) {
    const parts = report.timezone.split('/');
    if (parts.length >= 2) {
      return parts[parts.length - 1].replace(/_/g, ' ');
    }
  }
  return `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
}
