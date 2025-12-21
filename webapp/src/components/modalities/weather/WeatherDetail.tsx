/**
 * Detail panel showing full weather information for a selected location.
 */
import { useState, useCallback } from 'react';
import { MapPin, Plus } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { WeatherAlerts } from './WeatherAlerts';
import { CurrentConditions } from './CurrentConditions';
import { HourlyForecast } from './HourlyForecast';
import { DailyForecast } from './DailyForecast';
import { WeatherHistory } from './WeatherHistory';
import { NewWeatherReportDialog } from './NewWeatherReportDialog';
import apiClient from '@/api/client';
import type { WeatherLocationData, WeatherHistoryEntry, UnitSystem, WeatherReport } from './types';
import { getLocationDisplayName } from './types';

interface WeatherDetailProps {
  /** Selected location data */
  location: WeatherLocationData;
  /** History entries (loaded separately) */
  history: WeatherHistoryEntry[];
  /** Current unit system */
  units: UnitSystem;
  /** Callback when data is updated */
  onUpdate?: () => void;
}

export function WeatherDetail({ location, history, units, onUpdate }: WeatherDetailProps) {
  const { current_report: report } = location;
  const displayName = getLocationDisplayName(
    location.latitude,
    location.longitude,
    report
  );

  const [newReportDialogOpen, setNewReportDialogOpen] = useState(false);

  const handleSubmitReport = useCallback(async (weatherReport: WeatherReport) => {
    const response = await apiClient.post('/weather/update', {
      latitude: location.latitude,
      longitude: location.longitude,
      report: weatherReport,
    });

    if (response.data.error) {
      throw new Error(response.data.error);
    }

    // Trigger a refresh of the weather data
    onUpdate?.();
  }, [location.latitude, location.longitude, onUpdate]);

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        {/* Location header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <MapPin className="h-5 w-5 mt-0.5 text-primary" />
            <div>
              <h2 className="text-xl font-semibold">{displayName}</h2>
              <p className="text-sm text-muted-foreground">
                Lat: {location.latitude.toFixed(4)}, Lon: {location.longitude.toFixed(4)}
              </p>
              {report.timezone && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  Timezone: {report.timezone}
                </p>
              )}
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setNewReportDialogOpen(true)}
          >
            <Plus className="h-4 w-4 mr-1" />
            New Report
          </Button>
        </div>

        <Separator />

        {/* Weather Alerts (only shows if alerts exist) */}
        <WeatherAlerts 
          alerts={report.alerts || []} 
          timezoneOffset={report.timezone_offset}
        />

        {/* Current Conditions */}
        {report.current && (
          <CurrentConditions
            current={report.current}
            timezoneOffset={report.timezone_offset}
            units={units}
          />
        )}

        {/* Hourly Forecast (collapsible) */}
        {report.hourly && report.hourly.length > 0 && (
          <HourlyForecast
            hourly={report.hourly}
            timezoneOffset={report.timezone_offset}
            units={units}
            defaultExpanded={false}
          />
        )}

        {/* Daily Forecast (collapsible) */}
        {report.daily && report.daily.length > 0 && (
          <DailyForecast
            daily={report.daily}
            units={units}
            defaultExpanded={false}
          />
        )}

        {/* Weather History (collapsible) */}
        <WeatherHistory
          history={history}
          historyCount={location.history_count}
          units={units}
          defaultExpanded={false}
        />
      </div>

      {/* New Weather Report Dialog */}
      <NewWeatherReportDialog
        open={newReportDialogOpen}
        onOpenChange={setNewReportDialogOpen}
        latitude={location.latitude}
        longitude={location.longitude}
        locationName={displayName}
        units={units}
        onSubmit={handleSubmitReport}
      />
    </ScrollArea>
  );
}
