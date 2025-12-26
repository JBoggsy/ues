/**
 * TypeScript types for the Scenario Save/Load API.
 * These types mirror the Pydantic models from the backend (api/models.py).
 */

// ============================================================================
// Exported Data Structure Types
// ============================================================================

/**
 * Serialized simulator time state.
 * Represents the time_state portion of an exported environment.
 */
export interface ExportedTimeState {
  current_time: string;  // ISO datetime
  time_scale: number;
  is_paused: boolean;
  auto_advance: boolean;
  last_wall_time_update: string;  // ISO datetime
}

/**
 * Structure of exported environment data.
 * Matches the output of Environment.to_scenario_dict().
 */
export interface ExportedEnvironmentData {
  time_state: ExportedTimeState;
  modality_states: Record<string, Record<string, unknown>>;
}

/**
 * Structure of exported event queue data.
 * Matches the output of EventQueue.to_scenario_dict().
 */
export interface ExportedEventQueueData {
  events: Array<Record<string, unknown>>;
}

/**
 * Metadata for a saved scenario.
 */
export interface ScenarioMetadata {
  ues_version: string;
  scenario_version: string;
  created_at: string;  // ISO datetime
  author?: string | null;
  description?: string | null;
}

/**
 * Complete scenario structure for export/import.
 */
export interface ExportedScenarioData {
  metadata: ScenarioMetadata;
  environment: ExportedEnvironmentData;
  events: ExportedEventQueueData;
}

// ============================================================================
// Export Response Types
// ============================================================================

/**
 * Response for environment export endpoint.
 */
export interface ExportEnvironmentResponse {
  environment: ExportedEnvironmentData;
  modalities_exported: string[];
}

/**
 * Response for event queue export endpoint.
 */
export interface ExportEventsResponse {
  events: ExportedEventQueueData;
  total_events: number;
  pending_events: number;
  executed_events: number;
}

/**
 * Response for full scenario export endpoint.
 */
export interface ExportScenarioResponse {
  scenario: ExportedScenarioData;
}

// ============================================================================
// Import Request Types
// ============================================================================

/**
 * Valid options for handling historic events during environment load.
 */
export type HistoricEventHandling = 'ignore' | 'delete' | 'apply';

/**
 * Request body for importing an environment.
 */
export interface LoadEnvironmentRequest {
  data: ExportedEnvironmentData;
  historic_event_handling?: HistoricEventHandling;
  strict_modalities?: boolean;
}

/**
 * Request body for importing events.
 */
export interface LoadEventsRequest {
  data: ExportedEventQueueData;
  merge?: boolean;
}

/**
 * Request body for importing a full scenario.
 */
export interface LoadScenarioRequest {
  scenario: ExportedScenarioData;
  strict_modalities?: boolean;
}

// ============================================================================
// Import Response Types
// ============================================================================

/**
 * Response for environment import endpoint.
 */
export interface LoadEnvironmentResponse {
  success: boolean;
  modalities_loaded: string[];
  modalities_skipped: string[];
  warnings: string[];
  historic_events_count: number;
  historic_events_action: string;
}

/**
 * Response for event queue import endpoint.
 */
export interface LoadEventsResponse {
  success: boolean;
  events_loaded: number;
  events_merged: number;
  previous_events: number;
  historic_events_warning: boolean;
  historic_event_count: number;
}

/**
 * Summary of loaded scenario metadata in response.
 */
export interface LoadedScenarioMetadata {
  ues_version: string;
  scenario_version: string;
  created_at: string;  // ISO datetime
  author?: string | null;
  description?: string | null;
}

/**
 * Response for full scenario import endpoint.
 */
export interface LoadScenarioResponse {
  success: boolean;
  environment_loaded: boolean;
  events_loaded: number;
  modalities_loaded: string[];
  modalities_skipped: string[];
  warnings: string[];
  scenario_metadata: LoadedScenarioMetadata;
}

// ============================================================================
// Export Type Selection
// ============================================================================

/**
 * Types of exports available.
 */
export type ExportType = 'environment' | 'events' | 'scenario';

/**
 * File extensions for each export type.
 */
export const EXPORT_FILE_EXTENSIONS: Record<ExportType, string> = {
  environment: '.ues-env.json',
  events: '.ues-events.json',
  scenario: '.ues-scenario.json',
};

/**
 * Human-readable labels for export types.
 */
export const EXPORT_TYPE_LABELS: Record<ExportType, string> = {
  environment: 'Environment Only',
  events: 'Events Only',
  scenario: 'Full Scenario',
};
