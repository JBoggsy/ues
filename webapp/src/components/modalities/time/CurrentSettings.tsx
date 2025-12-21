/**
 * Current time settings editing form component.
 * Allows users to configure timezone, time format, date format, locale, and week start.
 */
import { useCallback, useMemo } from 'react';
import { Clock, Globe, Calendar, Languages, CalendarDays } from 'lucide-react';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type {
  TimePreferencesFormValues,
  TimeFormatPreference,
  DateFormat,
  WeekStart,
} from './types';
import {
  TIMEZONE_PRESETS,
  DATE_FORMAT_OPTIONS,
  LOCALE_PRESETS,
} from './types';

interface CurrentSettingsProps {
  values: TimePreferencesFormValues;
  onChange: (values: TimePreferencesFormValues) => void;
}

export function CurrentSettings({ values, onChange }: CurrentSettingsProps) {
  // Helper to update a single field
  const updateField = useCallback(
    <K extends keyof TimePreferencesFormValues>(
      field: K,
      value: TimePreferencesFormValues[K]
    ) => {
      onChange({ ...values, [field]: value });
    },
    [values, onChange]
  );

  // Get display label for current timezone
  const currentTimezoneLabel = useMemo(() => {
    const preset = TIMEZONE_PRESETS.find((tz) => tz.value === values.timezone);
    return preset ? preset.label : values.timezone;
  }, [values.timezone]);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium">Current Settings</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Timezone */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2 text-sm font-medium">
            <Globe className="h-4 w-4 text-muted-foreground" />
            Timezone
          </Label>
          <Select
            value={values.timezone}
            onValueChange={(value) => updateField('timezone', value)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select timezone">
                {currentTimezoneLabel}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {TIMEZONE_PRESETS.map((tz) => (
                <SelectItem key={tz.value} value={tz.value}>
                  <span className="flex justify-between gap-4">
                    <span>{tz.label}</span>
                    <span className="text-muted-foreground text-xs">
                      {tz.offset}
                    </span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Time Format */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2 text-sm font-medium">
            <Clock className="h-4 w-4 text-muted-foreground" />
            Time Format
          </Label>
          <RadioGroup
            value={values.format_preference}
            onValueChange={(value) =>
              updateField('format_preference', value as TimeFormatPreference)
            }
            className="flex gap-4"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="12h" id="format-12h" />
              <Label htmlFor="format-12h" className="font-normal cursor-pointer">
                12-hour <span className="text-muted-foreground text-xs">(2:30 PM)</span>
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="24h" id="format-24h" />
              <Label htmlFor="format-24h" className="font-normal cursor-pointer">
                24-hour <span className="text-muted-foreground text-xs">(14:30)</span>
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Date Format */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2 text-sm font-medium">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            Date Format
          </Label>
          <Select
            value={values.date_format ?? 'none'}
            onValueChange={(value) =>
              updateField('date_format', value === 'none' ? null : (value as DateFormat))
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select date format" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">
                <span className="text-muted-foreground">Not set</span>
              </SelectItem>
              {DATE_FORMAT_OPTIONS.map((fmt) => (
                <SelectItem key={fmt.value} value={fmt.value}>
                  <span className="flex justify-between gap-4">
                    <span>{fmt.label}</span>
                    <span className="text-muted-foreground text-xs">
                      {fmt.example}
                    </span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Locale */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2 text-sm font-medium">
            <Languages className="h-4 w-4 text-muted-foreground" />
            Locale
          </Label>
          <Select
            value={values.locale ?? 'none'}
            onValueChange={(value) =>
              updateField('locale', value === 'none' ? null : value)
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select locale" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">
                <span className="text-muted-foreground">Not set</span>
              </SelectItem>
              {LOCALE_PRESETS.map((loc) => (
                <SelectItem key={loc.value} value={loc.value}>
                  {loc.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Week Start */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2 text-sm font-medium">
            <CalendarDays className="h-4 w-4 text-muted-foreground" />
            Week Starts On
          </Label>
          <ToggleGroup
            type="single"
            value={values.week_start ?? 'none'}
            onValueChange={(value) =>
              updateField('week_start', value === 'none' ? null : (value as WeekStart))
            }
            className="justify-start"
          >
            <ToggleGroupItem
              value="none"
              aria-label="Not set"
              className="px-4"
            >
              Not set
            </ToggleGroupItem>
            <ToggleGroupItem
              value="sunday"
              aria-label="Sunday"
              className="px-4"
            >
              Sunday
            </ToggleGroupItem>
            <ToggleGroupItem
              value="monday"
              aria-label="Monday"
              className="px-4"
            >
              Monday
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
      </CardContent>
    </Card>
  );
}
