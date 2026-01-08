/**
 * React hooks for WebSocket event subscription.
 * 
 * These hooks provide easy integration with React Query for automatic
 * cache invalidation when WebSocket events are received.
 * 
 * @example
 * // In your App.tsx or layout component
 * function App() {
 *   useWebSocket(); // Connects and sets up auto-invalidation
 *   return <YourApp />;
 * }
 * 
 * @example
 * // Subscribe to specific events in a component
 * function NotificationBell() {
 *   const [count, setCount] = useState(0);
 *   
 *   useWebSocketEvent('email.received', () => {
 *     setCount(c => c + 1);
 *   });
 *   
 *   return <Badge count={count} />;
 * }
 */

import { useEffect, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { wsClient } from '../websocket';
import type { WSEvent, WSConnectionState } from '../websocket';

/**
 * Hook for managing WebSocket connection and automatic query invalidation.
 * 
 * Call this once at the app root to:
 * - Establish WebSocket connection
 * - Auto-invalidate React Query caches when relevant events occur
 * - Clean up on unmount
 * 
 * @example
 * function App() {
 *   useWebSocket();
 *   return (
 *     <QueryClientProvider client={queryClient}>
 *       <YourRoutes />
 *     </QueryClientProvider>
 *   );
 * }
 */
export function useWebSocket(): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Connect to WebSocket server
    wsClient.connect();

    // Auto-invalidate queries on relevant events
    const unsubTime = wsClient.subscribe('time.', () => {
      queryClient.invalidateQueries({ queryKey: ['time'] });
    });

    const unsubSim = wsClient.subscribe('simulation.', () => {
      queryClient.invalidateQueries({ queryKey: ['simulation'] });
    });

    const unsubEvents = wsClient.subscribe('event.', () => {
      queryClient.invalidateQueries({ queryKey: ['events'] });
    });

    // Modality-specific invalidations
    const unsubEmail = wsClient.subscribe('email.', () => {
      queryClient.invalidateQueries({ queryKey: ['email'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });

    const unsubSms = wsClient.subscribe('sms.', () => {
      queryClient.invalidateQueries({ queryKey: ['sms'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });

    const unsubChat = wsClient.subscribe('chat.', () => {
      queryClient.invalidateQueries({ queryKey: ['chat'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });

    const unsubCalendar = wsClient.subscribe('calendar.', () => {
      queryClient.invalidateQueries({ queryKey: ['calendar'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });

    const unsubLocation = wsClient.subscribe('location.', () => {
      queryClient.invalidateQueries({ queryKey: ['location'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });

    const unsubWeather = wsClient.subscribe('weather.', () => {
      queryClient.invalidateQueries({ queryKey: ['weather'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });

    // Undo/redo events should refresh everything affected
    const unsubUndo = wsClient.subscribe('undo.', () => {
      queryClient.invalidateQueries({ queryKey: ['simulation'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });

    const unsubRedo = wsClient.subscribe('redo.', () => {
      queryClient.invalidateQueries({ queryKey: ['simulation'] });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['environment'] });
    });

    // Cleanup on unmount
    return () => {
      unsubTime();
      unsubSim();
      unsubEvents();
      unsubEmail();
      unsubSms();
      unsubChat();
      unsubCalendar();
      unsubLocation();
      unsubWeather();
      unsubUndo();
      unsubRedo();
      wsClient.disconnect();
    };
  }, [queryClient]);
}

/**
 * Hook for subscribing to a specific WebSocket event type.
 * 
 * Automatically manages subscription lifecycle based on component mount/unmount.
 * The handler is memoized, so changes to the handler function won't cause
 * resubscription (use useCallback if you need stable handler identity).
 * 
 * @param eventType - Event type or prefix to match (e.g., 'time.advanced', 'email.')
 * @param handler - Function to call when matching event received
 * 
 * @example
 * function TimeDisplay() {
 *   const [time, setTime] = useState<string>('');
 *   
 *   useWebSocketEvent('time.advanced', (event) => {
 *     setTime(event.data.current_time as string);
 *   });
 *   
 *   return <div>Current time: {time}</div>;
 * }
 */
export function useWebSocketEvent(
  eventType: string,
  handler: (event: WSEvent) => void
): void {
  // Memoize handler to prevent unnecessary resubscriptions
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const memoizedHandler = useCallback(handler, []);

  useEffect(() => {
    // Ensure we're connected
    wsClient.connect();
    
    // Subscribe to the event type
    return wsClient.subscribe(eventType, memoizedHandler);
  }, [eventType, memoizedHandler]);
}

/**
 * Hook for tracking WebSocket connection state.
 * 
 * Returns the current connection state and updates when it changes.
 * Useful for showing connection status indicators in the UI.
 * 
 * @returns Current connection state: 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
 * 
 * @example
 * function ConnectionIndicator() {
 *   const state = useWebSocketConnectionState();
 *   
 *   const colors: Record<WSConnectionState, string> = {
 *     connected: 'green',
 *     connecting: 'yellow',
 *     reconnecting: 'orange',
 *     disconnected: 'red',
 *   };
 *   
 *   return <StatusDot color={colors[state]} />;
 * }
 */
export function useWebSocketConnectionState(): WSConnectionState {
  const [state, setState] = useState<WSConnectionState>(wsClient.connectionState);

  useEffect(() => {
    return wsClient.onConnectionStateChange(setState);
  }, []);

  return state;
}

/**
 * Hook for collecting recent WebSocket events.
 * 
 * Maintains a buffer of recent events for debugging or display purposes.
 * Automatically limits buffer size to prevent memory issues.
 * 
 * @param maxEvents - Maximum number of events to keep (default: 100)
 * @param eventFilter - Optional event type prefix to filter (e.g., 'time.')
 * @returns Array of recent events, newest first
 * 
 * @example
 * function EventLog() {
 *   const events = useWebSocketEventLog(50);
 *   
 *   return (
 *     <ul>
 *       {events.map((e, i) => (
 *         <li key={i}>{e.type}: {JSON.stringify(e.data)}</li>
 *       ))}
 *     </ul>
 *   );
 * }
 */
export function useWebSocketEventLog(
  maxEvents: number = 100,
  eventFilter?: string
): WSEvent[] {
  const [events, setEvents] = useState<WSEvent[]>([]);

  useEffect(() => {
    wsClient.connect();
    
    const pattern = eventFilter || '*';
    return wsClient.subscribe(pattern, (event) => {
      setEvents((prev) => {
        const updated = [event, ...prev];
        return updated.slice(0, maxEvents);
      });
    });
  }, [maxEvents, eventFilter]);

  return events;
}
