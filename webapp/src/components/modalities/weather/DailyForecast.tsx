/**
 * Collapsible component displaying daily weather forecast.
 */
import { useState } from 'react';
import { ChevronDown, ChevronRight, Droplets } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { DailyForecast as DailyForecastType, UnitSystem } from './types';
import { formatTemperature, getWeatherEmoji, formatDayName } from './types';

interface DailyForecastProps {
  /** Daily forecast data */
  daily: DailyForecastType[];
  /** Current unit system */
  units: UnitSystem;
  /** Whether initially expanded */
  defaultExpanded?: boolean;
}

export function DailyForecast({ 
  daily, 
  units,
  defaultExpanded = false 
}: DailyForecastProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (!daily || daily.length === 0) {
    return null;
  }

  // Show up to 7 days
  const displayDays = daily.slice(0, 7);

  return (
    <Card>
      <CardHeader className="pb-2">
        <Button
          variant="ghost"
          className="w-full justify-between p-0 h-auto hover:bg-transparent"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <CardTitle className="text-base">Daily Forecast</CardTitle>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </CardHeader>
      
      {isExpanded && (
        <CardContent className="pt-0">
          <div className="space-y-2">
            {displayDays.map((day, index) => {
              const weather = day.weather?.[0];
              const isToday = index === 0;
              
              return (
                <div
                  key={day.dt}
                  className={cn(
                    'flex items-center gap-3 p-2 rounded-lg',
                    isToday && 'bg-accent'
                  )}
                >
                  {/* Day name */}
                  <div className="w-24 text-sm font-medium">
                    {formatDayName(day.dt)}
                  </div>
                  
                  {/* Weather icon */}
                  <span className="text-xl">
                    {weather ? getWeatherEmoji(weather.icon) : '🌡️'}
                  </span>
                  
                  {/* Precipitation chance */}
                  <div className="w-12 flex items-center gap-0.5 text-xs text-blue-500">
                    {day.pop > 0 && (
                      <>
                        <Droplets className="h-3 w-3" />
                        {Math.round(day.pop * 100)}%
                      </>
                    )}
                  </div>
                  
                  {/* Temperature range */}
                  <div className="flex-1 flex items-center justify-end gap-2 text-sm">
                    <span className="font-semibold">
                      {formatTemperature(day.temp.max, units)}
                    </span>
                    <span className="text-muted-foreground">/</span>
                    <span className="text-muted-foreground">
                      {formatTemperature(day.temp.min, units)}
                    </span>
                  </div>
                  
                  {/* Description */}
                  <div className="w-32 text-xs text-muted-foreground capitalize truncate text-right">
                    {weather?.description || day.summary}
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      )}
    </Card>
  );
}
