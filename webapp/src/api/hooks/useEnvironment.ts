/**
 * TanStack Query hooks for environment state API endpoints.
 */
import { useQuery } from '@tanstack/react-query';
import apiClient from '../client';
import { usePollingSettings } from './useSettings';
import type { EnvironmentState, ModalitySummary, Modality } from '../types';

const QUERY_KEY = ['environment'];

/**
 * Hook to fetch complete environment state with polling.
 * Uses settings store for default polling interval.
 */
export function useEnvironmentState(pollingInterval?: number) {
  const { environmentPollingInterval } = usePollingSettings();
  const interval = pollingInterval ?? environmentPollingInterval;

  return useQuery<EnvironmentState>({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const response = await apiClient.get('/environment/state');
      return response.data;
    },
    refetchInterval: interval,
  });
}

/**
 * Hook to fetch list of available modalities.
 */
export function useModalityList() {
  return useQuery<ModalitySummary[]>({
    queryKey: [...QUERY_KEY, 'modalities'],
    queryFn: async () => {
      const response = await apiClient.get('/environment/modalities');
      return response.data;
    },
  });
}

/**
 * Hook to fetch state of a specific modality with polling.
 * Uses settings store for default polling interval.
 * 
 * Calls the modality-specific endpoint: /{modality}/state
 */
export function useModalityState<T = unknown>(modality: Modality, pollingInterval?: number) {
  const { environmentPollingInterval } = usePollingSettings();
  const interval = pollingInterval ?? environmentPollingInterval;

  return useQuery<T>({
    queryKey: [...QUERY_KEY, 'modalities', modality],
    queryFn: async () => {
      const response = await apiClient.get(`/${modality}/state`);
      return response.data;
    },
    refetchInterval: interval,
    enabled: !!modality,
  });
}

/**
 * Hook to query a modality with filters.
 * 
 * Calls the modality-specific endpoint: /{modality}/query
 */
export function useModalityQuery<T = unknown>(
  modality: Modality,
  query: Record<string, unknown>,
  enabled = true
) {
  return useQuery<T>({
    queryKey: [...QUERY_KEY, 'modalities', modality, 'query', query],
    queryFn: async () => {
      const response = await apiClient.post(`/${modality}/query`, query);
      return response.data;
    },
    enabled: enabled && !!modality,
  });
}
