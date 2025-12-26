/**
 * Hook to access settings store values for polling intervals.
 * This provides a convenient way for API hooks to access settings
 * without needing to pass them as parameters every time.
 */
import { useSettingsStore } from '@/lib/store';

export interface PollingSettings {
  timePollingInterval: number;
  environmentPollingInterval: number;
  eventsPollingInterval: number;
}

/**
 * Hook to get current polling settings from the store.
 */
export function usePollingSettings(): PollingSettings {
  const timePollingInterval = useSettingsStore((state) => state.timePollingInterval);
  const environmentPollingInterval = useSettingsStore((state) => state.environmentPollingInterval);
  const eventsPollingInterval = useSettingsStore((state) => state.eventsPollingInterval);

  return {
    timePollingInterval,
    environmentPollingInterval,
    eventsPollingInterval,
  };
}
