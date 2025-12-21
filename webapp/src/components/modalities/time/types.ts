/**
 * Type definitions for the Time preferences viewer.
 */

/**
 * Time format preference - 12-hour or 24-hour clock.
 */
export type TimeFormatPreference = '12h' | '24h';

/**
 * Week start preference - Sunday or Monday.
 */
export type WeekStart = 'sunday' | 'monday';

/**
 * Valid date format options.
 */
export type DateFormat = 
  | 'MM/DD/YYYY'
  | 'DD/MM/YYYY'
  | 'YYYY-MM-DD'
  | 'YYYY/MM/DD'
  | 'DD.MM.YYYY'
  | 'DD-MM-YYYY';

/**
 * A single entry in the time settings history.
 */
export interface TimeSettingsHistoryEntry {
  timestamp: string;
  timezone: string;
  format_preference: TimeFormatPreference;
  date_format?: string | null;
  locale?: string | null;
  week_start?: WeekStart | null;
}

/**
 * Time modality state from the API.
 */
export interface TimeState {
  modality_type: 'time';
  last_updated: string;
  update_count: number;
  timezone: string;
  format_preference: TimeFormatPreference;
  date_format?: string | null;
  locale?: string | null;
  week_start?: WeekStart | null;
  settings_history: TimeSettingsHistoryEntry[];
  max_history_size: number;
}

/**
 * Form values for editing time preferences.
 */
export interface TimePreferencesFormValues {
  timezone: string;
  format_preference: TimeFormatPreference;
  date_format: DateFormat | null;
  locale: string | null;
  week_start: WeekStart | null;
}

/**
 * TimeInput data structure for submitting to the API.
 */
export interface TimeInputData {
  modality_type: 'time';
  timezone: string;
  format_preference: TimeFormatPreference;
  date_format?: string | null;
  locale?: string | null;
  week_start?: WeekStart | null;
}

/**
 * Common timezone presets for quick selection.
 */
export const TIMEZONE_PRESETS = [
  { value: 'UTC', label: 'UTC (Coordinated Universal Time)', offset: '+00:00' },
  { value: 'America/New_York', label: 'Eastern Time (US)', offset: '-05:00' },
  { value: 'America/Chicago', label: 'Central Time (US)', offset: '-06:00' },
  { value: 'America/Denver', label: 'Mountain Time (US)', offset: '-07:00' },
  { value: 'America/Los_Angeles', label: 'Pacific Time (US)', offset: '-08:00' },
  { value: 'America/Anchorage', label: 'Alaska Time', offset: '-09:00' },
  { value: 'Pacific/Honolulu', label: 'Hawaii Time', offset: '-10:00' },
  { value: 'Europe/London', label: 'London (GMT)', offset: '+00:00' },
  { value: 'Europe/Paris', label: 'Paris (CET)', offset: '+01:00' },
  { value: 'Europe/Berlin', label: 'Berlin (CET)', offset: '+01:00' },
  { value: 'Europe/Moscow', label: 'Moscow', offset: '+03:00' },
  { value: 'Asia/Dubai', label: 'Dubai (GST)', offset: '+04:00' },
  { value: 'Asia/Kolkata', label: 'India (IST)', offset: '+05:30' },
  { value: 'Asia/Bangkok', label: 'Bangkok (ICT)', offset: '+07:00' },
  { value: 'Asia/Singapore', label: 'Singapore (SGT)', offset: '+08:00' },
  { value: 'Asia/Tokyo', label: 'Tokyo (JST)', offset: '+09:00' },
  { value: 'Australia/Sydney', label: 'Sydney (AEDT)', offset: '+11:00' },
  { value: 'Pacific/Auckland', label: 'Auckland (NZDT)', offset: '+13:00' },
] as const;

/**
 * Date format options with display labels.
 */
export const DATE_FORMAT_OPTIONS: { value: DateFormat; label: string; example: string }[] = [
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY', example: '12/21/2025' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY', example: '21/12/2025' },
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD (ISO)', example: '2025-12-21' },
  { value: 'YYYY/MM/DD', label: 'YYYY/MM/DD', example: '2025/12/21' },
  { value: 'DD.MM.YYYY', label: 'DD.MM.YYYY', example: '21.12.2025' },
  { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY', example: '21-12-2025' },
];

/**
 * Common locale presets.
 */
export const LOCALE_PRESETS = [
  { value: 'en_US', label: 'English (US)' },
  { value: 'en_GB', label: 'English (UK)' },
  { value: 'en_AU', label: 'English (Australia)' },
  { value: 'en_CA', label: 'English (Canada)' },
  { value: 'es_ES', label: 'Spanish (Spain)' },
  { value: 'es_MX', label: 'Spanish (Mexico)' },
  { value: 'fr_FR', label: 'French (France)' },
  { value: 'fr_CA', label: 'French (Canada)' },
  { value: 'de_DE', label: 'German (Germany)' },
  { value: 'it_IT', label: 'Italian (Italy)' },
  { value: 'pt_BR', label: 'Portuguese (Brazil)' },
  { value: 'pt_PT', label: 'Portuguese (Portugal)' },
  { value: 'ja_JP', label: 'Japanese (Japan)' },
  { value: 'ko_KR', label: 'Korean (Korea)' },
  { value: 'zh_CN', label: 'Chinese (Simplified)' },
  { value: 'zh_TW', label: 'Chinese (Traditional)' },
] as const;
