/**
 * Main Weather viewer component.
 * Displays tracked weather locations, current conditions, forecasts, and history.
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Plus, CloudSun } from 'lucide-react';
import apiClient from '@/api/client';
import { useModalityState } from '@/api';
import { Button } from '@/components/ui/button';
import { WeatherLocationList } from './WeatherLocationList';
import { WeatherDetail } from './WeatherDetail';
import { WeatherStatusBar } from './WeatherStatusBar';
import { AddLocationDialog } from './AddLocationDialog';
import type { 
  WeatherState, 
  UnitSystem, 
  WeatherReport, 
  CurrentWeather,
} from './types';

// Cookie key for storing unit preference
const UNITS_COOKIE_KEY = 'ues-weather-units';

/**
 * Get stored units preference from cookie.
 */
function getStoredUnits(): UnitSystem {
  if (typeof document === 'undefined') return 'imperial';
  const match = document.cookie.match(new RegExp(`${UNITS_COOKIE_KEY}=([^;]+)`));
  const value = match?.[1];
  if (value === 'imperial' || value === 'metric' || value === 'standard') {
    return value;
  }
  return 'imperial';
}

/**
 * Store units preference in cookie.
 */
function storeUnits(units: UnitSystem): void {
  if (typeof document === 'undefined') return;
  document.cookie = `${UNITS_COOKIE_KEY}=${units}; path=/; max-age=31536000`; // 1 year
}

/**
 * Submit a weather update to the API.
 */
async function addWeatherLocation(
  latitude: number,
  longitude: number
): Promise<void> {
  // Create a minimal weather report to add the location
  const now = Math.floor(Date.now() / 1000);
  const report: WeatherReport = {
    lat: latitude,
    lon: longitude,
    timezone: 'UTC',
    timezone_offset: 0,
    current: {
      dt: now,
      sunrise: now - 3600 * 6,
      sunset: now + 3600 * 6,
      temp: 293.15, // 20°C / 68°F in Kelvin
      feels_like: 293.15,
      pressure: 1013,
      humidity: 50,
      dew_point: 283.15,
      uvi: 3,
      clouds: 25,
      visibility: 10000,
      wind_speed: 5,
      wind_deg: 180,
      weather: [
        {
          id: 800,
          main: 'Clear',
          description: 'clear sky',
          icon: '01d',
        },
      ],
    } as CurrentWeather,
  };

  await apiClient.post('/weather/update', {
    latitude,
    longitude,
    report,
  });
}

export function WeatherViewer() {
  const queryClient = useQueryClient();

  // Fetch weather state with polling
  const {
    data: weatherState,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useModalityState<WeatherState>('weather', 5000);

  // UI State
  const [selectedLocationKey, setSelectedLocationKey] = useState<string | null>(null);
  const [units, setUnits] = useState<UnitSystem>(getStoredUnits);
  const [addDialogOpen, setAddDialogOpen] = useState(false);

  // Update stored units when changed
  useEffect(() => {
    storeUnits(units);
  }, [units]);

  // Auto-select first location when data loads
  useEffect(() => {
    if (weatherState?.locations && !selectedLocationKey) {
      const keys = Object.keys(weatherState.locations);
      if (keys.length > 0) {
        setSelectedLocationKey(keys[0]);
      }
    }
  }, [weatherState?.locations, selectedLocationKey]);

  // Get selected location data
  const selectedLocation = useMemo(() => {
    if (!selectedLocationKey || !weatherState?.locations) return null;
    return weatherState.locations[selectedLocationKey] || null;
  }, [weatherState?.locations, selectedLocationKey]);

  // Invalidate queries after mutations
  const invalidateWeatherState = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['environment', 'modalities', 'weather'] });
  }, [queryClient]);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Handle unit change
  const handleUnitsChange = useCallback((newUnits: UnitSystem) => {
    setUnits(newUnits);
  }, []);

  // Handle adding a new location
  const handleAddLocation = useCallback(
    async (latitude: number, longitude: number, _name?: string) => {
      await addWeatherLocation(latitude, longitude);
      invalidateWeatherState();
      // Select the newly added location
      const key = `${latitude.toFixed(2)},${longitude.toFixed(2)}`;
      setSelectedLocationKey(key);
    },
    [invalidateWeatherState]
  );

  // Handle location selection
  const handleSelectLocation = useCallback((key: string) => {
    setSelectedLocationKey(key);
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <CloudSun className="h-12 w-12 mx-auto mb-4 text-muted-foreground animate-pulse" />
          <p className="text-muted-foreground">Loading weather data...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <CloudSun className="h-12 w-12 mx-auto mb-4 text-destructive" />
          <p className="text-destructive mb-2">Failed to load weather data</p>
          <Button variant="outline" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  const locations = weatherState?.locations || {};
  const locationCount = Object.keys(locations).length;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-background">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <CloudSun className="h-5 w-5" />
          Weather
        </h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefetching}
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${isRefetching ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setAddDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-1" />
            Add Location
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 min-h-0">
        {locationCount === 0 ? (
          // Empty state
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <CloudSun className="h-16 w-16 mx-auto mb-4 text-muted-foreground" />
              <h3 className="text-lg font-semibold mb-2">No Weather Locations</h3>
              <p className="text-muted-foreground mb-4">
                Add a location to start tracking weather data. You can search by city,
                select on a map, or enter coordinates manually.
              </p>
              <Button onClick={() => setAddDialogOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Your First Location
              </Button>
            </div>
          </div>
        ) : (
          // Split view with location list and details
          <div className="flex h-full">
            {/* Left panel - Location list */}
            <div className="w-72 flex-shrink-0 border-r overflow-hidden">
              <WeatherLocationList
                locations={locations}
                selectedLocationKey={selectedLocationKey}
                onSelectLocation={handleSelectLocation}
                units={units}
              />
            </div>
            {/* Right panel - Weather details */}
            <div className="flex-1 min-w-0 overflow-hidden">
              {selectedLocation ? (
                <WeatherDetail
                  location={selectedLocation}
                  history={selectedLocation.history || selectedLocation.report_history || []}
                  units={units}
                  onUpdate={invalidateWeatherState}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground">
                  Select a location to view details
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Status Bar */}
      <WeatherStatusBar
        lastUpdated={weatherState?.last_updated}
        locationCount={locationCount}
        units={units}
        onUnitsChange={handleUnitsChange}
      />

      {/* Add Location Dialog */}
      <AddLocationDialog
        open={addDialogOpen}
        onOpenChange={setAddDialogOpen}
        onSubmit={handleAddLocation}
      />
    </div>
  );
}
