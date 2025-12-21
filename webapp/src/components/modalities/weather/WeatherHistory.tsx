/**
 * Collapsible component displaying weather history for a location.
 */
import { useState } from 'react';
import { ChevronDown, ChevronRight, History } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { WeatherHistoryEntry, UnitSystem } from './types';
import { formatTemperature, getWeatherEmoji } from './types';

interface WeatherHistoryProps {
  /** History entries */
  history: WeatherHistoryEntry[];
  /** History count from API (may be more than entries returned) */
  historyCount: number;
  /** Current unit system */
  units: UnitSystem;
  /** Whether initially expanded */
  defaultExpanded?: boolean;
}

/**
 * Format ISO timestamp to readable date/time.
 */
function formatHistoryTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function WeatherHistory({ 
  history,
  historyCount,
  units,
  defaultExpanded = false 
}: WeatherHistoryProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  if (historyCount === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <Button
          variant="ghost"
          className="w-full justify-between p-0 h-auto hover:bg-transparent"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <CardTitle className="text-base flex items-center gap-2">
            <History className="h-4 w-4" />
            History ({historyCount} reports)
          </CardTitle>
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </Button>
      </CardHeader>
      
      {isExpanded && (
        <CardContent className="pt-0">
          {history.length === 0 ? (
            <div className="text-sm text-muted-foreground py-2">
              History data not loaded. Query the API with history parameters.
            </div>
          ) : (
            <ScrollArea className="h-48">
              <div className="space-y-1">
                {history.map((entry, index) => {
                  const current = entry.report.current;
                  const weather = current?.weather?.[0];
                  
                  return (
                    <div
                      key={`${entry.timestamp}-${index}`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-accent/50"
                    >
                      {/* Timestamp */}
                      <div className="w-36 text-xs text-muted-foreground">
                        {formatHistoryTime(entry.timestamp)}
                      </div>
                      
                      {/* Temperature and condition */}
                      {current && weather ? (
                        <>
                          <span className="text-lg">
                            {getWeatherEmoji(weather.icon)}
                          </span>
                          <span className="font-medium">
                            {formatTemperature(current.temp, units)}
                          </span>
                          <span className="text-sm text-muted-foreground capitalize flex-1 truncate">
                            {weather.description}
                          </span>
                        </>
                      ) : (
                        <span className="text-sm text-muted-foreground">
                          No current data
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      )}
    </Card>
  );
}
