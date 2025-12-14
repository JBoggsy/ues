/**
 * Types and interfaces for event creation forms.
 */
import type { Modality } from '@/api/types';

/**
 * Props for modality-specific form components.
 */
export interface ModalityFormProps {
  /** Current form data */
  data: Record<string, unknown>;
  /** Callback to update form data */
  onChange: (data: Record<string, unknown>) => void;
  /** Whether the form is disabled (e.g., during submission) */
  disabled?: boolean;
}

/**
 * Configuration for a modality form.
 */
export interface ModalityFormConfig {
  /** Modality identifier */
  modality: Modality;
  /** Human-readable name */
  displayName: string;
  /** Description of what this modality does */
  description: string;
  /** Icon component to display */
  icon: React.ComponentType<{ className?: string }>;
  /** Form component for this modality */
  FormComponent: React.ComponentType<ModalityFormProps>;
  /** Default form data for this modality */
  defaultData: Record<string, unknown>;
  /** Validation function - returns error message or null if valid */
  validate: (data: Record<string, unknown>) => string | null;
  /** Optional transform function to convert form data to API format */
  transformData?: (data: Record<string, unknown>) => Record<string, unknown>;
}

/**
 * Form state for event creation.
 */
export interface EventFormState {
  modality: Modality | null;
  scheduledTime: string;
  executeImmediately: boolean;
  data: Record<string, unknown>;
}
