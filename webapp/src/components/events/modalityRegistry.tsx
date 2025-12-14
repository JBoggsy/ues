/**
 * Modality form registry.
 * 
 * Central registry of all available modality forms and their configurations.
 * Add new modalities here as they are implemented.
 */
import { 
  MapPin, 
  Cloud, 
  Clock, 
  Mail, 
  MessageSquare, 
  MessageCircle, 
  Calendar 
} from 'lucide-react';
import type { Modality } from '@/api/types';
import type { ModalityFormConfig, ModalityFormProps } from './types';
import { LocationForm, locationDefaultData, validateLocationData } from './LocationForm';
import { WeatherForm, weatherDefaultData, validateWeatherData, transformWeatherData } from './WeatherForm';
import { EmailForm, emailDefaultData, validateEmailData, transformEmailData } from './EmailForm';
import { TimeForm, timeDefaultData, validateTimeData } from './TimeForm';
import { SMSForm, smsDefaultData, validateSmsData, transformSmsData } from './SMSForm';
import { ChatForm, chatDefaultData, validateChatData, transformChatData } from './ChatForm';
import { CalendarForm, calendarDefaultData, validateCalendarData, transformCalendarData } from './CalendarForm';

/**
 * Placeholder form for modalities not yet implemented.
 */
function PlaceholderForm(_props: ModalityFormProps) {
  return (
    <div className="py-8 text-center text-muted-foreground">
      <p>Form not yet implemented for this modality.</p>
      <p className="text-sm mt-2">Coming soon!</p>
    </div>
  );
}

/**
 * Registry of all modality form configurations.
 */
export const modalityFormRegistry: Record<Modality, ModalityFormConfig> = {
  location: {
    modality: 'location',
    displayName: 'Location',
    description: 'Update the simulated user\'s geographic location',
    icon: MapPin,
    FormComponent: LocationForm,
    defaultData: locationDefaultData,
    validate: validateLocationData,
  },
  weather: {
    modality: 'weather',
    displayName: 'Weather',
    description: 'Update weather conditions for a location',
    icon: Cloud,
    FormComponent: WeatherForm,
    defaultData: weatherDefaultData,
    validate: validateWeatherData,
    transformData: transformWeatherData,
  },
  time: {
    modality: 'time',
    displayName: 'Time Preferences',
    description: 'Update time display preferences (timezone, format)',
    icon: Clock,
    FormComponent: TimeForm,
    defaultData: timeDefaultData,
    validate: validateTimeData,
  },
  email: {
    modality: 'email',
    displayName: 'Email',
    description: 'Send, receive, or manage email messages',
    icon: Mail,
    FormComponent: EmailForm,
    defaultData: emailDefaultData,
    validate: validateEmailData,
    transformData: transformEmailData,
  },
  sms: {
    modality: 'sms',
    displayName: 'SMS',
    description: 'Send or receive text messages',
    icon: MessageSquare,
    FormComponent: SMSForm,
    defaultData: smsDefaultData,
    validate: validateSmsData,
    transformData: transformSmsData,
  },
  chat: {
    modality: 'chat',
    displayName: 'Chat',
    description: 'Add messages to the chat conversation',
    icon: MessageCircle,
    FormComponent: ChatForm,
    defaultData: chatDefaultData,
    validate: validateChatData,
    transformData: transformChatData,
  },
  calendar: {
    modality: 'calendar',
    displayName: 'Calendar',
    description: 'Create, update, or delete calendar events',
    icon: Calendar,
    FormComponent: CalendarForm,
    defaultData: calendarDefaultData,
    validate: validateCalendarData,
    transformData: transformCalendarData,
  },
};

/**
 * Get the form configuration for a modality.
 */
export function getModalityFormConfig(modality: Modality): ModalityFormConfig {
  return modalityFormRegistry[modality];
}

/**
 * Get all available modalities.
 */
export function getAvailableModalities(): Modality[] {
  return Object.keys(modalityFormRegistry) as Modality[];
}

/**
 * Check if a modality form is implemented (not a placeholder).
 */
export function isModalityFormImplemented(modality: Modality): boolean {
  const config = modalityFormRegistry[modality];
  return config.FormComponent !== PlaceholderForm;
}
