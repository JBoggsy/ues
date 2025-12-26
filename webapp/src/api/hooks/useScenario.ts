/**
 * TanStack Query hooks for scenario save/load API endpoints.
 */
import { useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../client';
import type {
  ExportEnvironmentResponse,
  ExportEventsResponse,
  ExportScenarioResponse,
  LoadEnvironmentRequest,
  LoadEnvironmentResponse,
  LoadEventsRequest,
  LoadEventsResponse,
  LoadScenarioRequest,
  LoadScenarioResponse,
  ExportedEnvironmentData,
  ExportedEventQueueData,
  ExportedScenarioData,
  HistoricEventHandling,
} from '../types/scenario';

// ============================================================================
// Export Hooks
// ============================================================================

/**
 * Hook to export the current environment state.
 * Returns environment data that can be saved to a file.
 */
export function useExportEnvironment() {
  return useMutation<ExportEnvironmentResponse>({
    mutationFn: async () => {
      const response = await apiClient.get('/scenario/export/environment');
      return response.data;
    },
  });
}

/**
 * Hook to export the current event queue.
 * Returns event data that can be saved to a file.
 */
export function useExportEvents() {
  return useMutation<ExportEventsResponse>({
    mutationFn: async () => {
      const response = await apiClient.get('/scenario/export/events');
      return response.data;
    },
  });
}

/**
 * Hook to export the complete scenario (environment + events + metadata).
 * Returns a full scenario that can be saved to a file.
 */
export function useExportScenario() {
  return useMutation<ExportScenarioResponse, Error, { author?: string; description?: string }>({
    mutationFn: async ({ author, description }) => {
      const params = new URLSearchParams();
      if (author) params.append('author', author);
      if (description) params.append('description', description);
      const url = params.toString() 
        ? `/scenario/export/full?${params.toString()}`
        : '/scenario/export/full';
      const response = await apiClient.get(url);
      return response.data;
    },
  });
}

// ============================================================================
// Import Hooks
// ============================================================================

/**
 * Hook to import an environment state.
 * Replaces the current environment with the loaded data.
 */
export function useImportEnvironment() {
  const queryClient = useQueryClient();

  return useMutation<
    LoadEnvironmentResponse,
    Error,
    {
      data: ExportedEnvironmentData;
      historicEventHandling?: HistoricEventHandling;
      strictModalities?: boolean;
    }
  >({
    mutationFn: async ({ data, historicEventHandling = 'ignore', strictModalities = false }) => {
      const request: LoadEnvironmentRequest = {
        data,
        historic_event_handling: historicEventHandling,
        strict_modalities: strictModalities,
      };
      const response = await apiClient.post('/scenario/import/environment', request);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate all queries that depend on environment state
      queryClient.invalidateQueries({ queryKey: ['environment'] });
      queryClient.invalidateQueries({ queryKey: ['time'] });
      queryClient.invalidateQueries({ queryKey: ['simulation'] });
    },
  });
}

/**
 * Hook to import event queue data.
 * Can either replace or merge with existing events.
 */
export function useImportEvents() {
  const queryClient = useQueryClient();

  return useMutation<
    LoadEventsResponse,
    Error,
    {
      data: ExportedEventQueueData;
      merge?: boolean;
    }
  >({
    mutationFn: async ({ data, merge = false }) => {
      const request: LoadEventsRequest = {
        data,
        merge,
      };
      const response = await apiClient.post('/scenario/import/events', request);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate event queries
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['simulation'] });
    },
  });
}

/**
 * Hook to import a complete scenario (environment + events).
 * Replaces both the environment and event queue.
 */
export function useImportScenario() {
  const queryClient = useQueryClient();

  return useMutation<
    LoadScenarioResponse,
    Error,
    {
      scenario: ExportedScenarioData;
      strictModalities?: boolean;
    }
  >({
    mutationFn: async ({ scenario, strictModalities = false }) => {
      const request: LoadScenarioRequest = {
        scenario,
        strict_modalities: strictModalities,
      };
      const response = await apiClient.post('/scenario/import/full', request);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate all queries - full scenario affects everything
      queryClient.invalidateQueries({ queryKey: ['environment'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['time'] });
      queryClient.invalidateQueries({ queryKey: ['simulation'] });
    },
  });
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Trigger a file download with the given content.
 * 
 * @param content - JSON string content to download
 * @param filename - Name of the file (with extension)
 */
export function downloadJsonFile(content: string, filename: string): void {
  const blob = new Blob([content], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Read a JSON file from a File input and parse it.
 * 
 * @param file - File object from input element
 * @returns Promise resolving to parsed JSON data
 */
export async function readJsonFile<T = unknown>(file: File): Promise<T> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const text = event.target?.result as string;
        const data = JSON.parse(text) as T;
        resolve(data);
      } catch (error) {
        reject(new Error(`Failed to parse JSON: ${error instanceof Error ? error.message : 'Unknown error'}`));
      }
    };
    reader.onerror = () => reject(new Error('Failed to read file'));
    reader.readAsText(file);
  });
}

/**
 * Detect the type of scenario file based on its content structure.
 * 
 * @param data - Parsed JSON data from a file
 * @returns Detected file type or null if unknown
 */
export function detectFileType(data: unknown): 'environment' | 'events' | 'scenario' | null {
  if (!data || typeof data !== 'object') {
    return null;
  }

  const obj = data as Record<string, unknown>;

  // Full scenario has metadata, environment, and events
  if ('metadata' in obj && 'environment' in obj && 'events' in obj) {
    return 'scenario';
  }

  // Environment has time_state and modality_states
  if ('time_state' in obj && 'modality_states' in obj) {
    return 'environment';
  }

  // Events have an events array
  if ('events' in obj && Array.isArray(obj.events)) {
    return 'events';
  }

  return null;
}

/**
 * Generate a default filename for export based on type and current timestamp.
 * 
 * @param type - Export type
 * @param prefix - Optional prefix for the filename
 * @returns Generated filename with appropriate extension
 */
export function generateExportFilename(
  type: 'environment' | 'events' | 'scenario',
  prefix = 'ues'
): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const extensions: Record<typeof type, string> = {
    environment: '.ues-env.json',
    events: '.ues-events.json',
    scenario: '.ues-scenario.json',
  };
  return `${prefix}-${timestamp}${extensions[type]}`;
}
