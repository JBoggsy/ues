/**
 * Main Time preferences viewer component.
 * Two-column layout: settings form on left, preview + history on right.
 */
import { useState, useCallback, useMemo, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Clock, Save, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/api/client';
import { useModalityState } from '@/api';
import { Button } from '@/components/ui/button';
import { CurrentSettings } from './CurrentSettings';
import { LivePreview } from './LivePreview';
import { SettingsHistory } from './SettingsHistory';
import type {
  TimeState,
  TimePreferencesFormValues,
  TimeInputData,
  DateFormat,
} from './types';

/**
 * Submit time preferences update via immediate event.
 */
async function updateTimePreferences(data: TimeInputData): Promise<void> {
  await apiClient.post('/events/immediate', {
    modality: 'time',
    data,
  });
}

/**
 * Check if form values differ from saved state.
 */
function hasChanges(
  formValues: TimePreferencesFormValues,
  savedState: TimeState
): boolean {
  return (
    formValues.timezone !== savedState.timezone ||
    formValues.format_preference !== savedState.format_preference ||
    formValues.date_format !== (savedState.date_format ?? null) ||
    formValues.locale !== (savedState.locale ?? null) ||
    formValues.week_start !== (savedState.week_start ?? null)
  );
}

export function TimeViewer() {
  const queryClient = useQueryClient();

  // Fetch time state with polling
  const {
    data: timeState,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useModalityState<TimeState>('time', 3000);

  // Form state - initialized from API data
  const [formValues, setFormValues] = useState<TimePreferencesFormValues>({
    timezone: 'UTC',
    format_preference: '12h',
    date_format: null,
    locale: null,
    week_start: null,
  });

  // Track if we're submitting
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize form values from API state when it loads
  useEffect(() => {
    if (timeState) {
      setFormValues({
        timezone: timeState.timezone,
        format_preference: timeState.format_preference,
        date_format: (timeState.date_format as DateFormat) ?? null,
        locale: timeState.locale ?? null,
        week_start: timeState.week_start ?? null,
      });
    }
  }, [timeState]);

  // Check if form has unsaved changes
  const formHasChanges = useMemo(() => {
    if (!timeState) return false;
    return hasChanges(formValues, timeState);
  }, [formValues, timeState]);

  // Invalidate queries after mutations
  const invalidateTimeState = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: ['environment', 'modalities', 'time'],
    });
  }, [queryClient]);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Reset form to saved state
  const handleReset = useCallback(() => {
    if (timeState) {
      setFormValues({
        timezone: timeState.timezone,
        format_preference: timeState.format_preference,
        date_format: (timeState.date_format as DateFormat) ?? null,
        locale: timeState.locale ?? null,
        week_start: timeState.week_start ?? null,
      });
    }
  }, [timeState]);

  // Submit form changes
  const handleSubmit = useCallback(async () => {
    if (!formHasChanges) return;

    setIsSubmitting(true);
    try {
      const inputData: TimeInputData = {
        modality_type: 'time',
        timezone: formValues.timezone,
        format_preference: formValues.format_preference,
        date_format: formValues.date_format,
        locale: formValues.locale,
        week_start: formValues.week_start,
      };

      await updateTimePreferences(inputData);
      toast.success('Time preferences updated');
      invalidateTimeState();
    } catch (error) {
      console.error('Failed to update time preferences:', error);
      toast.error('Failed to update time preferences');
    } finally {
      setIsSubmitting(false);
    }
  }, [formValues, formHasChanges, invalidateTimeState]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Clock className="h-12 w-12 mx-auto mb-4 text-muted-foreground animate-pulse" />
          <p className="text-muted-foreground">Loading time preferences...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Clock className="h-12 w-12 mx-auto mb-4 text-destructive" />
          <p className="text-destructive mb-2">Failed to load time preferences</p>
          <Button variant="outline" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-background">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Time Preferences
        </h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefetching}
          >
            <RefreshCw
              className={`h-4 w-4 mr-1 ${isRefetching ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Main content - two column layout */}
      <div className="flex-1 overflow-auto p-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {/* Left column: Settings form */}
          <div className="space-y-4">
            <CurrentSettings values={formValues} onChange={setFormValues} />

            {/* Action buttons */}
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={handleReset}
                disabled={!formHasChanges || isSubmitting}
              >
                <RotateCcw className="h-4 w-4 mr-1" />
                Reset
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!formHasChanges || isSubmitting}
              >
                <Save className="h-4 w-4 mr-1" />
                {isSubmitting ? 'Saving...' : 'Apply Changes'}
              </Button>
            </div>
          </div>

          {/* Right column: Preview + History */}
          <div className="space-y-4">
            <LivePreview
              values={formValues}
              simulatorTime={timeState?.last_updated}
            />
            <SettingsHistory
              history={timeState?.settings_history ?? []}
              currentSettings={{
                timezone: timeState?.timezone ?? 'UTC',
                format_preference: timeState?.format_preference ?? '12h',
                date_format: timeState?.date_format ?? null,
                locale: timeState?.locale ?? null,
                week_start: timeState?.week_start ?? null,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
