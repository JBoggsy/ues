/**
 * Component displaying weather alerts.
 * Only renders if there are alerts present.
 */
import { AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import type { WeatherAlert } from './types';
import { getAlertSeverity, getAlertColorClasses, formatDate, formatTime } from './types';

interface WeatherAlertsProps {
  /** Weather alerts to display */
  alerts: WeatherAlert[];
  /** Timezone offset in seconds */
  timezoneOffset?: number;
}

export function WeatherAlerts({ alerts, timezoneOffset }: WeatherAlertsProps) {
  // Don't render anything if no alerts
  if (!alerts || alerts.length === 0) {
    return null;
  }

  return (
    <Card className="border-amber-500/50 bg-amber-50/50 dark:bg-amber-950/20">
      <CardHeader className="pb-2">
        <CardTitle className="text-base flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          Weather Alerts ({alerts.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {alerts.map((alert, index) => {
          const severity = getAlertSeverity(alert.event);
          const colorClasses = getAlertColorClasses(severity);
          const startDate = new Date(alert.start * 1000);
          const endDate = new Date(alert.end * 1000);

          return (
            <div
              key={`${alert.event}-${alert.start}-${index}`}
              className={cn(
                'p-3 rounded-lg border-l-4',
                colorClasses
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-semibold uppercase text-sm">
                  {severity === 'extreme' && '🔴 '}
                  {severity === 'high' && '🟠 '}
                  {severity === 'medium' && '🟡 '}
                  {severity === 'low' && '🔵 '}
                  {alert.event}
                </div>
              </div>
              
              <div className="text-xs mt-1 opacity-80">
                {formatDate(alert.start)} {formatTime(alert.start, timezoneOffset)} - {' '}
                {startDate.toDateString() !== endDate.toDateString() 
                  ? `${formatDate(alert.end)} ` 
                  : ''
                }
                {formatTime(alert.end, timezoneOffset)}
              </div>
              
              <div className="text-sm mt-2 line-clamp-3">
                {alert.description}
              </div>
              
              {alert.sender_name && (
                <div className="text-xs mt-2 opacity-70">
                  Source: {alert.sender_name}
                </div>
              )}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
