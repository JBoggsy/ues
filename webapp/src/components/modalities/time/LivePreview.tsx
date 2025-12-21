/**
 * Live preview component showing how dates/times appear with current settings.
 */
import { useMemo } from 'react';
import { Eye } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { TimePreferencesFormValues, DateFormat } from './types';

interface LivePreviewProps {
  values: TimePreferencesFormValues;
  simulatorTime?: string;
}

/**
 * Format a date according to the specified date format.
 */
function formatDate(date: Date, format: DateFormat | null): string {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();

  switch (format) {
    case 'MM/DD/YYYY':
      return `${month}/${day}/${year}`;
    case 'DD/MM/YYYY':
      return `${day}/${month}/${year}`;
    case 'YYYY-MM-DD':
      return `${year}-${month}-${day}`;
    case 'YYYY/MM/DD':
      return `${year}/${month}/${day}`;
    case 'DD.MM.YYYY':
      return `${day}.${month}.${year}`;
    case 'DD-MM-YYYY':
      return `${day}-${month}-${year}`;
    default:
      // Default to locale format
      return date.toLocaleDateString();
  }
}

/**
 * Format a time according to 12h or 24h preference.
 */
function formatTime(date: Date, format: '12h' | '24h'): string {
  const hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');

  if (format === '24h') {
    return `${String(hours).padStart(2, '0')}:${minutes}:${seconds}`;
  } else {
    const period = hours >= 12 ? 'PM' : 'AM';
    const displayHours = hours % 12 || 12;
    return `${displayHours}:${minutes}:${seconds} ${period}`;
  }
}

/**
 * Get day of week name.
 */
function getDayName(date: Date): string {
  return date.toLocaleDateString('en-US', { weekday: 'long' });
}

/**
 * Calculate ISO week number.
 */
function getWeekNumber(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

export function LivePreview({ values, simulatorTime }: LivePreviewProps) {
  // Use simulator time if provided, otherwise use current wall time for preview
  const previewDate = useMemo(() => {
    if (simulatorTime) {
      return new Date(simulatorTime);
    }
    return new Date();
  }, [simulatorTime]);

  // Format date/time based on current settings
  const formattedTime = useMemo(
    () => formatTime(previewDate, values.format_preference),
    [previewDate, values.format_preference]
  );

  const formattedDate = useMemo(
    () => formatDate(previewDate, values.date_format),
    [previewDate, values.date_format]
  );

  const dayName = useMemo(() => getDayName(previewDate), [previewDate]);
  const weekNumber = useMemo(() => getWeekNumber(previewDate), [previewDate]);

  // Display locale info
  const localeDisplay = values.locale || 'System default';

  // Display week start info
  const weekStartDisplay = values.week_start
    ? values.week_start === 'sunday'
      ? 'Sunday'
      : 'Monday'
    : 'System default';

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Eye className="h-4 w-4" />
          Live Preview
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-center py-4 bg-muted/30 rounded-lg">
          <div className="text-3xl font-mono font-semibold tracking-wide">
            {formattedTime}
          </div>
          <div className="text-lg mt-1 text-muted-foreground">
            {formattedDate}
          </div>
          <div className="text-sm text-muted-foreground mt-1">
            {dayName}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-muted-foreground">Timezone:</div>
          <div className="font-medium truncate" title={values.timezone}>
            {values.timezone}
          </div>

          <div className="text-muted-foreground">Week Number:</div>
          <div className="font-medium">{weekNumber}</div>

          <div className="text-muted-foreground">Locale:</div>
          <div className="font-medium">{localeDisplay}</div>

          <div className="text-muted-foreground">Week Starts:</div>
          <div className="font-medium">{weekStartDisplay}</div>
        </div>
      </CardContent>
    </Card>
  );
}
