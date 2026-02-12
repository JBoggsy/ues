/**
 * Zustand store for application settings with localStorage persistence.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Theme = 'light' | 'dark' | 'system';

export interface SettingsState {
  // Connection Settings
  apiUrl: string;
  apiKey: string;
  connectionTimeout: number; // in milliseconds

  // Polling Intervals (in milliseconds)
  timePollingInterval: number;
  environmentPollingInterval: number;
  eventsPollingInterval: number;

  // Display Settings
  theme: Theme;
  toastDuration: number; // in milliseconds
  confirmDestructiveActions: boolean;

  // Time Display (placeholders for future implementation)
  displayTimezone: 'simulator' | 'browser';
  use24HourFormat: boolean;

  // Actions
  setApiUrl: (url: string) => void;
  setApiKey: (key: string) => void;
  setConnectionTimeout: (timeout: number) => void;
  setTimePollingInterval: (interval: number) => void;
  setEnvironmentPollingInterval: (interval: number) => void;
  setEventsPollingInterval: (interval: number) => void;
  setTheme: (theme: Theme) => void;
  setToastDuration: (duration: number) => void;
  setConfirmDestructiveActions: (confirm: boolean) => void;
  setDisplayTimezone: (timezone: 'simulator' | 'browser') => void;
  setUse24HourFormat: (use24Hour: boolean) => void;
  resetToDefaults: () => void;
}

/**
 * Derive the default API URL from the current browser location.
 *
 * When VITE_API_BASE_URL is set, that value is used as-is (build-time override).
 * Otherwise, we assume the API server runs on the same host as the web UI on
 * port 8000, so we build the URL from `window.location.hostname`. This lets
 * both LAN and remote clients reach the correct backend automatically.
 */
function getDefaultApiUrl(): string {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  const hostname = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  return `http://${hostname}:8000`;
}

const DEFAULT_SETTINGS = {
  apiUrl: getDefaultApiUrl(),
  apiKey: '',
  connectionTimeout: 10000,
  timePollingInterval: 1000,
  environmentPollingInterval: 5000,
  eventsPollingInterval: 3000,
  theme: 'system' as Theme,
  toastDuration: 4000,
  confirmDestructiveActions: true,
  displayTimezone: 'simulator' as const,
  use24HourFormat: false,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...DEFAULT_SETTINGS,

      setApiUrl: (url) => set({ apiUrl: url }),
      setApiKey: (key) => set({ apiKey: key }),
      setConnectionTimeout: (timeout) => set({ connectionTimeout: timeout }),
      setTimePollingInterval: (interval) => set({ timePollingInterval: interval }),
      setEnvironmentPollingInterval: (interval) => set({ environmentPollingInterval: interval }),
      setEventsPollingInterval: (interval) => set({ eventsPollingInterval: interval }),
      setTheme: (theme) => set({ theme }),
      setToastDuration: (duration) => set({ toastDuration: duration }),
      setConfirmDestructiveActions: (confirm) => set({ confirmDestructiveActions: confirm }),
      setDisplayTimezone: (timezone) => set({ displayTimezone: timezone }),
      setUse24HourFormat: (use24Hour) => set({ use24HourFormat: use24Hour }),
      resetToDefaults: () => set(DEFAULT_SETTINGS),
    }),
    {
      name: 'ues-settings',
    }
  )
);
