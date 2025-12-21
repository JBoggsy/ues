/**
 * Collapsible component displaying hourly weather forecast.
 */
import { useState } from 'react';
import { ChevronDown, ChevronRight, Droplets } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import type { HourlyForecast as HourlyForecastType, UnitSystem } from './types';
import { formatTemperature, getWeatherEmoji, formatTime } from './types';

interface HourlyForecastProps {
  /** Hourly forecast data */
  hourly: HourlyForecastType[];
  /** Timezone offset in seconds */
  timezoneOffset?: number;
  /** Current unit system */
  units: UnitSystem;
  /** Whether initially expanded */
  defaultExpanded?: boolean;
}

export function HourlyForecast({ 
  hourly, 
  timezoneOffset, 
  units,
  defaultExpanded = false 
}: HourlyForecastProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!hourly || hourly.length === 0) {
    return null;
  }

  // Show next 24 hours
  const displayHours = hourly.slice(0, 24);

  return (
    <Card>
      <CardHeader className="pb-2">
        <Button
          variant="ghost"
          className="w-full justify-between p-0 h-auto hover:bg-transparent"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <CardTitle className="text-base">Hourly Forecast</CardTitle>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </CardHeader>
      
      {isExpanded && (
        <CardContent className="pt-0">
          <ScrollArea className="w-full whitespace-nowrap">
            <div className="flex gap-4 pb-2">
              {displayHours.map((hour, index) => {
                const weather = hour.weather?.[0];
                const isNow = index === 0;
                
                return (
                  <div
                    key={hour.dt}
                    className={cn(
                      'flex flex-col items-center gap-1 min-w-[60px] p-2 rounded-lg',
                      isNow && 'bg-accent'
                    )}
                  >
                    <div className="text-xs text-muted-foreground">
                      {isNow ? 'Now' : formatTime(hour.dt, timezoneOffset)}
                    </div>
                    <span className="text-2xl">
                      {weather ? getWeatherEmoji(weather.icon) : '🌡️'}
                    </span>
                    <div className="text-sm font-semibold">
                      {formatTemperature(hour.temp, units)}
                    </div>
                    {hour.pop > 0 && (
                      <div className="flex items-center gap-0.5 text-xs text-blue-500">
                        <Droplets className="h-3 w-3" />
                        {Math.round(hour.pop * 100)}%
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <ScrollBar orientation="horizontal" />
          </ScrollArea>
        </CardContent>
      )}
    </Card>
  );
}
