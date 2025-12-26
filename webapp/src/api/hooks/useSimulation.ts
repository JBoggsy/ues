/**
 * TanStack Query hooks for simulation control API endpoints.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../client';
import { usePollingSettings } from './useSettings';
import type { 
  SimulationStatus, 
  StartSimulationRequest, 
  UndoRedoRequest, 
  ClearRequest 
} from '../types';

const QUERY_KEY = ['simulation'];

/**
 * Hook to fetch simulation status with polling.
 * Uses settings store for default polling interval.
 */
export function useSimulationStatus(pollingInterval?: number) {
  const { timePollingInterval } = usePollingSettings();
  const interval = pollingInterval ?? timePollingInterval;

  return useQuery<SimulationStatus>({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const response = await apiClient.get('/simulation/status');
      return response.data;
    },
    refetchInterval: interval,
  });
}

/**
 * Hook to start the simulation.
 */
export function useStartSimulation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request?: StartSimulationRequest) => {
      const response = await apiClient.post('/simulation/start', request || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['time'] });
    },
  });
}

/**
 * Hook to stop the simulation.
 */
export function useStopSimulation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/simulation/stop');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

/**
 * Hook to reset the simulation.
 */
export function useResetSimulation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/simulation/reset');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['time'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    },
  });
}

/**
 * Hook to clear the simulation.
 */
export function useClearSimulation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request?: ClearRequest) => {
      const response = await apiClient.post('/simulation/clear', request || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['time'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    },
  });
}

/**
 * Hook to undo the last action(s).
 */
export function useUndo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request?: UndoRedoRequest) => {
      const response = await apiClient.post('/simulation/undo', request || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    },
  });
}

/**
 * Hook to redo the last undone action(s).
 */
export function useRedo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request?: UndoRedoRequest) => {
      const response = await apiClient.post('/simulation/redo', request || {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    },
  });
}
