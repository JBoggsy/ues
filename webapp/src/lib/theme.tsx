/**
 * Theme provider that syncs the app theme with settings store.
 * Applies 'dark' class to document root based on theme preference.
 */
import { useEffect } from 'react';
import { useSettingsStore, type Theme } from './store';

/**
 * Resolves the effective theme based on user preference and system settings.
 */
function resolveTheme(theme: Theme): 'light' | 'dark' {
  if (theme === 'system') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return theme;
}

/**
 * Hook that syncs theme from settings store to document root.
 * Should be called once at the app root level.
 */
export function useTheme() {
  const theme = useSettingsStore((state) => state.theme);

  useEffect(() => {
    const root = document.documentElement;
    const effectiveTheme = resolveTheme(theme);

    if (effectiveTheme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    // Listen for system theme changes when in 'system' mode
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = (e: MediaQueryListEvent) => {
        if (e.matches) {
          root.classList.add('dark');
        } else {
          root.classList.remove('dark');
        }
      };
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme]);
}

/**
 * ThemeProvider component that initializes theme syncing.
 * Wrap your app with this component to enable theme support.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useTheme();
  return <>{children}</>;
}
