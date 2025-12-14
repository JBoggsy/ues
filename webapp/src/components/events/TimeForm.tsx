/**
 * Time preferences event creation form.
 *
 * Allows creating events that update user time display preferences
 * including timezone, format preferences, and locale settings.
 */

import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { ModalityFormProps } from './types';

/**
 * Common timezone presets organized by region.
 */
const TIMEZONE_PRESETS = [
  { label: 'UTC', value: 'UTC' },
  { label: 'US/Eastern', value: 'America/New_York' },
  { label: 'US/Central', value: 'America/Chicago' },
  { label: 'US/Mountain', value: 'America/Denver' },
  { label: 'US/Pacific', value: 'America/Los_Angeles' },
  { label: 'US/Alaska', value: 'America/Anchorage' },
  { label: 'US/Hawaii', value: 'Pacific/Honolulu' },
  { label: 'UK/London', value: 'Europe/London' },
  { label: 'Europe/Paris', value: 'Europe/Paris' },
  { label: 'Europe/Berlin', value: 'Europe/Berlin' },
  { label: 'Europe/Moscow', value: 'Europe/Moscow' },
  { label: 'Asia/Tokyo', value: 'Asia/Tokyo' },
  { label: 'Asia/Shanghai', value: 'Asia/Shanghai' },
  { label: 'Asia/Singapore', value: 'Asia/Singapore' },
  { label: 'Asia/Dubai', value: 'Asia/Dubai' },
  { label: 'Asia/Kolkata', value: 'Asia/Kolkata' },
  { label: 'Australia/Sydney', value: 'Australia/Sydney' },
  { label: 'Australia/Perth', value: 'Australia/Perth' },
  { label: 'Pacific/Auckland', value: 'Pacific/Auckland' },
];

/**
 * Date format options.
 */
const DATE_FORMATS = [
  { label: 'MM/DD/YYYY (US)', value: 'MM/DD/YYYY' },
  { label: 'DD/MM/YYYY (EU)', value: 'DD/MM/YYYY' },
  { label: 'YYYY-MM-DD (ISO)', value: 'YYYY-MM-DD' },
  { label: 'YYYY/MM/DD', value: 'YYYY/MM/DD' },
  { label: 'DD.MM.YYYY', value: 'DD.MM.YYYY' },
  { label: 'DD-MM-YYYY', value: 'DD-MM-YYYY' },
];

/**
 * Common locale presets.
 */
const LOCALE_PRESETS = [
  { label: 'English (US)', value: 'en_US' },
  { label: 'English (UK)', value: 'en_GB' },
  { label: 'English (Australia)', value: 'en_AU' },
  { label: 'Spanish', value: 'es_ES' },
  { label: 'French', value: 'fr_FR' },
  { label: 'German', value: 'de_DE' },
  { label: 'Italian', value: 'it_IT' },
  { label: 'Portuguese (Brazil)', value: 'pt_BR' },
  { label: 'Japanese', value: 'ja_JP' },
  { label: 'Chinese (Simplified)', value: 'zh_CN' },
  { label: 'Korean', value: 'ko_KR' },
  { label: 'Russian', value: 'ru_RU' },
  { label: 'Arabic', value: 'ar_SA' },
  { label: 'Hindi', value: 'hi_IN' },
];

/**
 * Default data for a new time preferences event.
 */
export const timeDefaultData = {
  timezone: 'America/New_York',
  format_preference: '12h',
  date_format: 'MM/DD/YYYY',
  locale: 'en_US',
  week_start: 'sunday',
};

/**
 * Validate time preferences data.
 */
export function validateTimeData(data: Record<string, unknown>): string | null {
  const timezone = data.timezone as string;
  const formatPref = data.format_preference as string;

  if (!timezone || timezone.trim() === '') {
    return 'Timezone is required';
  }

  if (!formatPref || !['12h', '24h'].includes(formatPref)) {
    return 'Format preference must be 12h or 24h';
  }

  return null;
}

/**
 * Time preferences form component.
 */
export function TimeForm({ data, onChange }: ModalityFormProps) {
  const handleChange = (field: string, value: string) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <div className="space-y-4">
      {/* Timezone */}
      <div className="space-y-2">
        <Label htmlFor="timezone">Timezone</Label>
        <Select
          value={data.timezone as string}
          onValueChange={(v) => handleChange('timezone', v)}
        >
          <SelectTrigger id="timezone">
            <SelectValue placeholder="Select timezone" />
          </SelectTrigger>
          <SelectContent>
            {TIMEZONE_PRESETS.map((tz) => (
              <SelectItem key={tz.value} value={tz.value}>
                {tz.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          User's preferred timezone for time display
        </p>
      </div>

      {/* Custom Timezone */}
      <div className="space-y-2">
        <Label htmlFor="custom_timezone">Or Enter Custom Timezone</Label>
        <Input
          id="custom_timezone"
          placeholder="e.g., America/Detroit, Europe/Rome"
          value={
            TIMEZONE_PRESETS.some((tz) => tz.value === data.timezone)
              ? ''
              : (data.timezone as string)
          }
          onChange={(e) => {
            if (e.target.value.trim()) {
              handleChange('timezone', e.target.value.trim());
            }
          }}
        />
        <p className="text-xs text-muted-foreground">
          IANA timezone identifier (overrides dropdown selection)
        </p>
      </div>

      {/* Time Format */}
      <div className="space-y-2">
        <Label htmlFor="format_preference">Time Format</Label>
        <Select
          value={data.format_preference as string}
          onValueChange={(v) => handleChange('format_preference', v)}
        >
          <SelectTrigger id="format_preference">
            <SelectValue placeholder="Select format" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="12h">12-hour (1:30 PM)</SelectItem>
            <SelectItem value="24h">24-hour (13:30)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Date Format */}
      <div className="space-y-2">
        <Label htmlFor="date_format">Date Format</Label>
        <Select
          value={(data.date_format as string) || ''}
          onValueChange={(v) => handleChange('date_format', v)}
        >
          <SelectTrigger id="date_format">
            <SelectValue placeholder="Select date format" />
          </SelectTrigger>
          <SelectContent>
            {DATE_FORMATS.map((fmt) => (
              <SelectItem key={fmt.value} value={fmt.value}>
                {fmt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Locale */}
      <div className="space-y-2">
        <Label htmlFor="locale">Locale</Label>
        <Select
          value={(data.locale as string) || ''}
          onValueChange={(v) => handleChange('locale', v)}
        >
          <SelectTrigger id="locale">
            <SelectValue placeholder="Select locale" />
          </SelectTrigger>
          <SelectContent>
            {LOCALE_PRESETS.map((loc) => (
              <SelectItem key={loc.value} value={loc.value}>
                {loc.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Affects number formatting, month/day names
        </p>
      </div>

      {/* Week Start */}
      <div className="space-y-2">
        <Label htmlFor="week_start">Week Starts On</Label>
        <Select
          value={(data.week_start as string) || ''}
          onValueChange={(v) => handleChange('week_start', v)}
        >
          <SelectTrigger id="week_start">
            <SelectValue placeholder="Select start day" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="sunday">Sunday</SelectItem>
            <SelectItem value="monday">Monday</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          First day of week for calendar views
        </p>
      </div>
    </div>
  );
}
