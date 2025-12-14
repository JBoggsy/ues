/**
 * TanStack Query hooks for environment state API endpoints.
 */
import { useQuery } from '@tanstack/react-query';
import apiClient from '../client';
import type { EnvironmentState, ModalitySummary, Modality } from '../types';

const QUERY_KEY = ['environment'];

/**
 * Hook to fetch complete environment state with polling.
 */
export function useEnvironmentState(pollingInterval = 5000) {
  return useQuery<EnvironmentState>({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const response = await apiClient.get('/environment/state');
      return response.data;
    },
    refetchInterval: pollingInterval,
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
 */
export function useModalityState<T = unknown>(modality: Modality, pollingInterval = 5000) {
  return useQuery<T>({
    queryKey: [...QUERY_KEY, 'modalities', modality],
    queryFn: async () => {
      const response = await apiClient.get(`/environment/modalities/${modality}`);
      return response.data;
    },
    refetchInterval: pollingInterval,
    enabled: !!modality,
  });
}

/**
 * Hook to query a modality with filters.
 */
export function useModalityQuery<T = unknown>(
  modality: Modality,
  query: Record<string, unknown>,
  enabled = true
) {
  return useQuery<T>({
    queryKey: [...QUERY_KEY, 'modalities', modality, 'query', query],
    queryFn: async () => {
      const response = await apiClient.post(`/environment/modalities/${modality}/query`, query);
      return response.data;
    },
    enabled: enabled && !!modality,
  });
}
