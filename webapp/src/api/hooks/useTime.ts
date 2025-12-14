/**
 * TanStack Query hooks for time control API endpoints.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import apiClient from '../client';
import type { 
  TimeState, 
  AdvanceTimeRequest, 
  SetTimeRequest, 
  SetScaleRequest,
  AdvanceTimeResponse,
  SetTimeResponse,
  SkipToNextResponse,
  EventExecutionDetail,
} from '../types';

const QUERY_KEY = ['time'];

/**
 * Format a modality name for display.
 */
function formatModality(modality: string): string {
  const names: Record<string, string> = {
    location: 'Location',
    weather: 'Weather',
    time: 'Time',
    email: 'Email',
    sms: 'SMS',
    chat: 'Chat',
    calendar: 'Calendar',
  };
  return names[modality] || modality;
}

/**
 * Show toast notifications for executed events.
 */
function showExecutionToasts(
  eventsExecuted: number, 
  eventsFailed: number, 
  executionDetails?: EventExecutionDetail[]
) {
  if (eventsExecuted === 0 && eventsFailed === 0) {
    return; // No events to report
  }

  if (eventsExecuted > 0 && eventsFailed === 0) {
    // All succeeded
    if (eventsExecuted === 1 && executionDetails?.length === 1) {
      const detail = executionDetails[0];
      toast.success(`${formatModality(detail.modality)} event executed`);
    } else {
      toast.success(`${eventsExecuted} event${eventsExecuted > 1 ? 's' : ''} executed`);
    }
  } else if (eventsExecuted === 0 && eventsFailed > 0) {
    // All failed
    toast.error(`${eventsFailed} event${eventsFailed > 1 ? 's' : ''} failed`);
  } else {
    // Mixed results
    toast.warning(`${eventsExecuted} executed, ${eventsFailed} failed`);
  }
}

/**
 * Hook to fetch current time state with polling.
 */
export function useTimeState(pollingInterval = 1000) {
  return useQuery<TimeState>({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const response = await apiClient.get('/simulator/time');
      return response.data;
    },
    refetchInterval: pollingInterval,
  });
}

/**
 * Hook to advance simulation time by a duration.
 */
export function useAdvanceTime() {
  const queryClient = useQueryClient();

  return useMutation<AdvanceTimeResponse, Error, AdvanceTimeRequest>({
    mutationFn: async (request: AdvanceTimeRequest) => {
      const response = await apiClient.post('/simulator/time/advance', request);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
      showExecutionToasts(data.events_executed, data.events_failed, data.execution_details);
    },
  });
}

/**
 * Hook to set simulation time to a specific value.
 */
export function useSetTime() {
  const queryClient = useQueryClient();

  return useMutation<SetTimeResponse, Error, SetTimeRequest>({
    mutationFn: async (request: SetTimeRequest) => {
      const response = await apiClient.post('/simulator/time/set', request);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
      showExecutionToasts(data.executed_events, 0);
    },
  });
}

/**
 * Hook to skip to the next scheduled event.
 */
export function useSkipToNext() {
  const queryClient = useQueryClient();

  return useMutation<SkipToNextResponse, Error, void>({
    mutationFn: async () => {
      const response = await apiClient.post('/simulator/time/skip-to-next');
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
      if (data.events_executed > 0) {
        toast.success(`Skipped to next event: ${data.events_executed} executed`);
      } else {
        toast.info('Skipped to next event time');
      }
    },
  });
}

/**
 * Hook to pause the simulation.
 */
export function usePauseTime() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/simulator/time/pause');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

/**
 * Hook to resume the simulation.
 */
export function useResumeTime() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/simulator/time/resume');
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

/**
 * Hook to set the time scale.
 */
export function useSetTimeScale() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: SetScaleRequest) => {
      const response = await apiClient.post('/simulator/time/set-scale', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
