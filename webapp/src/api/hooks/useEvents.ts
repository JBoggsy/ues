/**
 * TanStack Query hooks for event management API endpoints.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '../client';
import type { 
  SimulatorEvent, 
  EventListResponse, 
  EventSummaryResponse,
  CreateEventRequest,
  ImmediateEventRequest,
  EventStatus,
  Modality
} from '../types';

const QUERY_KEY = ['events'];

interface EventFilters {
  status?: EventStatus;
  modality?: Modality;
  limit?: number;
  offset?: number;
}

/**
 * Hook to fetch events list with polling.
 */
export function useEvents(filters?: EventFilters, pollingInterval = 3000) {
  return useQuery<EventListResponse>({
    queryKey: [...QUERY_KEY, filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.modality) params.append('modality', filters.modality);
      if (filters?.limit) params.append('limit', String(filters.limit));
      if (filters?.offset) params.append('offset', String(filters.offset));
      
      const response = await apiClient.get(`/events?${params.toString()}`);
      return response.data;
    },
    refetchInterval: pollingInterval,
  });
}

/**
 * Hook to fetch a single event by ID.
 */
export function useEvent(eventId: string) {
  return useQuery<SimulatorEvent>({
    queryKey: [...QUERY_KEY, eventId],
    queryFn: async () => {
      const response = await apiClient.get(`/events/${eventId}`);
      return response.data;
    },
    enabled: !!eventId,
  });
}

/**
 * Hook to fetch the next pending event.
 */
export function useNextEvent() {
  return useQuery<SimulatorEvent | null>({
    queryKey: [...QUERY_KEY, 'next'],
    queryFn: async () => {
      const response = await apiClient.get('/events/next');
      return response.data;
    },
  });
}

/**
 * Hook to fetch event summary statistics.
 */
export function useEventSummary(pollingInterval = 5000) {
  return useQuery<EventSummaryResponse>({
    queryKey: [...QUERY_KEY, 'summary'],
    queryFn: async () => {
      const response = await apiClient.get('/events/summary');
      return response.data;
    },
    refetchInterval: pollingInterval,
  });
}

/**
 * Hook to create a new scheduled event.
 */
export function useCreateEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: CreateEventRequest) => {
      const response = await apiClient.post('/events', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}

/**
 * Hook to create and immediately execute an event.
 */
export function useCreateImmediateEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ImmediateEventRequest) => {
      const response = await apiClient.post('/events/immediate', request);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    },
  });
}

/**
 * Hook to cancel a pending event.
 */
export function useCancelEvent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (eventId: string) => {
      const response = await apiClient.delete(`/events/${eventId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });
}
