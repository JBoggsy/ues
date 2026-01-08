/**
 * WebSocket client for real-time event notifications.
 * 
 * Provides automatic reconnection with exponential backoff,
 * event type filtering via subscription, and React-friendly API.
 * 
 * @example
 * // Subscribe to all time events
 * const unsubscribe = wsClient.subscribe('time.', (event) => {
 *   console.log('Time event:', event);
 * });
 * 
 * // Clean up
 * unsubscribe();
 */

import { useSettingsStore } from '@/lib/store';

/**
 * A WebSocket event received from the server.
 */
export interface WSEvent {
  /** Event type identifier (e.g., "time.advanced", "email.received") */
  type: string;
  /** Event-specific payload data */
  data: Record<string, unknown>;
  /** ISO 8601 timestamp when the event was created on the server */
  timestamp: string;
}

/**
 * Handler function for WebSocket events.
 */
export type WSEventHandler = (event: WSEvent) => void;

/**
 * Connection state for the WebSocket.
 */
export type WSConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

/**
 * Listener for connection state changes.
 */
export type WSConnectionStateListener = (state: WSConnectionState) => void;

/**
 * WebSocket client with automatic reconnection and event filtering.
 */
class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<WSEventHandler>> = new Map();
  private connectionStateListeners: Set<WSConnectionStateListener> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private _connectionState: WSConnectionState = 'disconnected';
  private intentionalClose = false;
  private serverSubscriptions: string[] | null = null;

  /**
   * Get the current connection state.
   */
  get connectionState(): WSConnectionState {
    return this._connectionState;
  }

  /**
   * Set the connection state and notify listeners.
   */
  private setConnectionState(state: WSConnectionState): void {
    if (this._connectionState !== state) {
      this._connectionState = state;
      this.connectionStateListeners.forEach((listener) => listener(state));
    }
  }

  /**
   * Get the WebSocket URL from current settings.
   */
  private getWebSocketUrl(): string {
    const settings = useSettingsStore.getState();
    // Convert HTTP URL to WebSocket URL
    return settings.apiUrl.replace(/^http/, 'ws') + '/ws';
  }

  /**
   * Connect to the WebSocket server.
   * 
   * If already connected, this is a no-op.
   * Uses settings from the Zustand store for the server URL.
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
      return;
    }

    this.intentionalClose = false;
    this.setConnectionState('connecting');

    const url = this.getWebSocketUrl();
    console.debug('[WebSocket] Connecting to', url);

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.debug('[WebSocket] Connected');
      this.reconnectAttempts = 0;
      this.setConnectionState('connected');
      
      // Re-apply server-side subscription filter if any
      if (this.serverSubscriptions !== null) {
        this.sendServerSubscription(this.serverSubscriptions);
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const parsed: WSEvent = JSON.parse(event.data);
        this.emit(parsed);
      } catch (err) {
        console.error('[WebSocket] Failed to parse message:', err);
      }
    };

    this.ws.onclose = (event) => {
      console.debug('[WebSocket] Connection closed', event.code, event.reason);
      this.ws = null;
      
      if (this.intentionalClose) {
        this.setConnectionState('disconnected');
        return;
      }

      // Attempt to reconnect with exponential backoff
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.setConnectionState('reconnecting');
        const delay = 1000 * Math.pow(2, this.reconnectAttempts);
        console.debug(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
        
        this.reconnectTimeout = setTimeout(() => {
          this.reconnectAttempts++;
          this.connect();
        }, delay);
      } else {
        console.error('[WebSocket] Max reconnection attempts reached');
        this.setConnectionState('disconnected');
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
    };
  }

  /**
   * Disconnect from the WebSocket server.
   * 
   * Stops any pending reconnection attempts.
   */
  disconnect(): void {
    this.intentionalClose = true;
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.setConnectionState('disconnected');
    console.debug('[WebSocket] Disconnected');
  }

  /**
   * Send a subscription message to the server.
   * 
   * This tells the server to filter which events are sent to this client.
   */
  private sendServerSubscription(eventTypes: string[]): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        events: eventTypes,
      }));
    }
  }

  /**
   * Set server-side event filter.
   * 
   * Unlike client-side subscribe(), this tells the server to only send
   * matching events, reducing network traffic.
   * 
   * @param eventTypes - Event type prefixes to receive (null = all events)
   */
  setServerFilter(eventTypes: string[] | null): void {
    this.serverSubscriptions = eventTypes;
    if (eventTypes !== null) {
      this.sendServerSubscription(eventTypes);
    }
  }

  /**
   * Subscribe to events matching a pattern.
   * 
   * The handler will be called for:
   * - Exact matches: 'time.advanced' matches 'time.advanced'
   * - Prefix matches: 'time.' matches 'time.advanced', 'time.set', etc.
   * - Wildcard: '*' matches all events
   * 
   * @param eventType - Event type or prefix to match
   * @param handler - Function to call when matching event received
   * @returns Unsubscribe function
   * 
   * @example
   * const unsubscribe = wsClient.subscribe('time.', (event) => {
   *   console.log('Time changed:', event.data);
   * });
   * 
   * // Later, to stop receiving events:
   * unsubscribe();
   */
  subscribe(eventType: string, handler: WSEventHandler): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get(eventType)?.delete(handler);
      // Clean up empty sets
      if (this.handlers.get(eventType)?.size === 0) {
        this.handlers.delete(eventType);
      }
    };
  }

  /**
   * Subscribe to connection state changes.
   * 
   * @param listener - Function to call when connection state changes
   * @returns Unsubscribe function
   */
  onConnectionStateChange(listener: WSConnectionStateListener): () => void {
    this.connectionStateListeners.add(listener);
    // Immediately call with current state
    listener(this._connectionState);
    
    return () => {
      this.connectionStateListeners.delete(listener);
    };
  }

  /**
   * Emit an event to all matching handlers.
   */
  private emit(event: WSEvent): void {
    // Exact match handlers
    this.handlers.get(event.type)?.forEach((h) => h(event));

    // Prefix match handlers (e.g., "time." matches "time.advanced")
    this.handlers.forEach((handlers, pattern) => {
      if (pattern.endsWith('.') && event.type.startsWith(pattern)) {
        handlers.forEach((h) => h(event));
      }
    });

    // Wildcard handlers
    this.handlers.get('*')?.forEach((h) => h(event));
  }
}

/**
 * Global WebSocket client instance.
 * 
 * Use this singleton throughout the application for consistent
 * connection management and event handling.
 */
export const wsClient = new WebSocketClient();
