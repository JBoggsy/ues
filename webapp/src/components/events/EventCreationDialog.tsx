/**
 * Event creation dialog component.
 * 
 * A modal dialog for creating new simulation events with modality-specific forms.
 * Supports both scheduled events and immediate execution.
 */
import { useState, useCallback } from 'react';
import { format } from 'date-fns';
import { Plus, Zap, Clock, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCreateEvent, useCreateImmediateEvent, useTimeState } from '@/api';
import type { Modality } from '@/api/types';
import { 
  getModalityFormConfig, 
  getAvailableModalities,
  isModalityFormImplemented,
} from './modalityRegistry';
import type { EventFormState } from './types';

/**
 * Initial form state.
 */
function getInitialFormState(): EventFormState {
  return {
    modality: null,
    scheduledTime: '',
    executeImmediately: false,
    data: {},
  };
}

/**
 * Generate a human-readable summary of an event's data.
 */
function getEventSummary(modality: string, data: Record<string, unknown>): string {
  switch (modality) {
    case 'location': {
      const lat = data.latitude as number;
      const lon = data.longitude as number;
      const named = data.named_location as string | null;
      const addr = data.address as string | null;
      if (named) return `Updated to "${named}" (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
      if (addr) return `Updated to ${addr}`;
      return `Updated to (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
    }
    case 'weather': {
      const lat = data.latitude as number;
      const lon = data.longitude as number;
      const temp = data.temp_f as number;
      return `${temp}°F at (${lat.toFixed(2)}, ${lon.toFixed(2)})`;
    }
    case 'time': {
      const tz = data.timezone as string;
      const fmt = data.format_preference as string;
      const dateFmt = data.date_format as string | undefined;
      const parts = [`${tz}, ${fmt}`];
      if (dateFmt) parts.push(dateFmt);
      return `Preferences: ${parts.join(', ')}`;
    }
    case 'email': {
      const op = data.operation as string;
      const subject = data.subject as string | undefined;
      const from = data.from_address as string | undefined;
      const to = data.to_addresses as string | undefined;
      const msgId = data.message_id as string | undefined;
      
      switch (op) {
        case 'receive':
          return subject ? `Receive: "${subject}" from ${from}` : `Receive email from ${from}`;
        case 'send':
          return subject ? `Send: "${subject}" to ${to}` : `Send email to ${to}`;
        case 'reply':
        case 'reply_all':
          return subject ? `Reply: "${subject}"` : `Reply to message`;
        case 'mark_read':
          return `Mark as read: ${msgId || 'message'}`;
        case 'mark_unread':
          return `Mark as unread: ${msgId || 'message'}`;
        case 'delete':
          return `Delete: ${msgId || 'message'}`;
        case 'archive':
          return `Archive: ${msgId || 'message'}`;
        case 'star':
          return `Star: ${msgId || 'message'}`;
        case 'unstar':
          return `Unstar: ${msgId || 'message'}`;
        case 'move':
          return `Move ${msgId || 'message'} to ${data.target_folder || 'folder'}`;
        default:
          return `Email operation: ${op}`;
      }
    }
    case 'sms': {
      const action = data.action as string;
      const from = data.from_number as string | undefined;
      const to = data.to_numbers as string | undefined;
      const body = data.body as string | undefined;
      const msgId = data.message_id as string | undefined;
      const groupId = data.group_id as string | undefined;

      switch (action) {
        case 'receive_message':
          return body
            ? `Receive SMS from ${from}: "${body.slice(0, 30)}${body.length > 30 ? '...' : ''}"`
            : `Receive SMS from ${from}`;
        case 'send_message':
          return body
            ? `Send SMS to ${to}: "${body.slice(0, 30)}${body.length > 30 ? '...' : ''}"`
            : `Send SMS to ${to}`;
        case 'update_delivery_status':
          return `Update status: ${data.new_status} for ${msgId}`;
        case 'add_reaction':
          return `React ${data.emoji} to ${msgId}`;
        case 'remove_reaction':
          return `Remove reaction from ${msgId}`;
        case 'edit_message':
          return `Edit message ${msgId}`;
        case 'delete_message':
          return `Delete message ${msgId}`;
        case 'create_group':
          return `Create group: ${data.group_name || 'New group'}`;
        case 'update_group':
          return `Update group ${groupId}`;
        case 'add_participant':
          return `Add ${data.participant_number} to group`;
        case 'remove_participant':
          return `Remove ${data.participant_number} from group`;
        case 'leave_group':
          return `Leave group ${groupId}`;
        case 'update_conversation':
          return `Update conversation settings`;
        default:
          return `SMS action: ${action}`;
      }
    }
    case 'chat': {
      const operation = data.operation as string;
      const role = data.role as string | undefined;
      const content = data.content as string | undefined;
      const convId = data.conversation_id as string | undefined;
      const msgId = data.message_id as string | undefined;

      switch (operation) {
        case 'send_message': {
          const roleEmoji = role === 'user' ? '👤' : '🤖';
          const preview = content
            ? `"${content.slice(0, 30)}${content.length > 30 ? '...' : ''}"`
            : '';
          return `${roleEmoji} ${role}: ${preview}`;
        }
        case 'delete_message':
          return `Delete message ${msgId}`;
        case 'clear_conversation':
          return `Clear conversation "${convId}"`;
        default:
          return `Chat operation: ${operation}`;
      }
    }
    case 'calendar': {
      const operation = data.operation as string;
      const title = data.title as string | undefined;
      const eventId = data.event_id as string | undefined;
      const startDate = data.start_date as string | undefined;

      switch (operation) {
        case 'create':
          return title
            ? `Create: "${title}"${startDate ? ` on ${startDate}` : ''}`
            : 'Create calendar event';
        case 'update':
          return title
            ? `Update: "${title}"`
            : `Update event ${eventId}`;
        case 'delete':
          return `Delete event ${eventId}`;
        default:
          return `Calendar operation: ${operation}`;
      }
    }
    default:
      return 'Event data applied';
  }
}

/**
 * Event creation dialog component.
 */
export function EventCreationDialog() {
  const [open, setOpen] = useState(false);
  const [formState, setFormState] = useState<EventFormState>(getInitialFormState);
  const [error, setError] = useState<string | null>(null);

  const { data: timeState } = useTimeState();
  const createEvent = useCreateEvent();
  const createImmediateEvent = useCreateImmediateEvent();

  const modalities = getAvailableModalities();
  const selectedConfig = formState.modality ? getModalityFormConfig(formState.modality) : null;
  const isImplemented = formState.modality ? isModalityFormImplemented(formState.modality) : false;

  // Set default scheduled time to current simulation time
  const defaultScheduledTime = timeState?.current_time
    ? format(new Date(timeState.current_time), "yyyy-MM-dd'T'HH:mm")
    : '';

  const handleModalityChange = useCallback((modality: Modality) => {
    const config = getModalityFormConfig(modality);
    setFormState({
      modality,
      scheduledTime: defaultScheduledTime,
      executeImmediately: true,  // Default to immediate for easier testing
      data: { ...config.defaultData },
    });
    setError(null);
  }, [defaultScheduledTime]);

  const handleDataChange = useCallback((data: Record<string, unknown>) => {
    setFormState(prev => ({ ...prev, data }));
    setError(null);
  }, []);

  const handleSubmit = async () => {
    if (!formState.modality || !selectedConfig) {
      setError('Please select a modality');
      return;
    }

    // Validate form data
    const validationError = selectedConfig.validate(formState.data);
    if (validationError) {
      setError(validationError);
      return;
    }

    // Validate scheduled time for non-immediate events
    if (!formState.executeImmediately && !formState.scheduledTime) {
      setError('Please specify a scheduled time');
      return;
    }

    try {
      const modalityName = selectedConfig?.displayName || formState.modality;
      
      // Transform data if the modality has a transform function
      const apiData = selectedConfig.transformData 
        ? selectedConfig.transformData(formState.data)
        : formState.data;
      
      if (formState.executeImmediately) {
        await createImmediateEvent.mutateAsync({
          modality: formState.modality,
          data: apiData,
        });
        toast.success(`${modalityName} event scheduled`, {
          description: getEventSummary(formState.modality, formState.data),
        });
      } else {
        await createEvent.mutateAsync({
          scheduled_time: new Date(formState.scheduledTime).toISOString(),
          modality: formState.modality,
          data: apiData,
        });
        const scheduledTimeFormatted = format(new Date(formState.scheduledTime), 'MMM d, h:mm a');
        toast.success(`${modalityName} event scheduled`, {
          description: `Scheduled for ${scheduledTimeFormatted}`,
        });
      }

      // Reset and close on success
      setFormState(getInitialFormState());
      setError(null);
      setOpen(false);
    } catch (err: unknown) {
      // Handle specific error cases
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { status?: number; data?: { detail?: string } } };
        if (axiosError.response?.status === 409) {
          const detail = axiosError.response.data?.detail || '';
          if (detail.includes('past')) {
            setError('Cannot schedule event in the past. Try using "Immediate" mode or choose a future time.');
          } else {
            setError(detail || 'Conflict: The request conflicts with current state.');
          }
          return;
        }
      }
      setError(err instanceof Error ? err.message : 'Failed to create event');
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
    if (!newOpen) {
      // Reset form when closing
      setFormState(getInitialFormState());
      setError(null);
    }
  };

  const isSubmitting = createEvent.isPending || createImmediateEvent.isPending;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create Event
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle>Create Simulation Event</DialogTitle>
          <DialogDescription>
            Create a new event to modify the simulation environment.
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-y-auto pr-2">
          <div className="space-y-6 py-4">
            {/* Modality Selection */}
            <div className="space-y-2">
              <Label>Modality</Label>
              <Select
                value={formState.modality || ''}
                onValueChange={(value) => handleModalityChange(value as Modality)}
                disabled={isSubmitting}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a modality..." />
                </SelectTrigger>
                <SelectContent>
                  {modalities.map((modality) => {
                    const config = getModalityFormConfig(modality);
                    const implemented = isModalityFormImplemented(modality);
                    const Icon = config.icon;
                    return (
                      <SelectItem key={modality} value={modality}>
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4" />
                          <span>{config.displayName}</span>
                          {!implemented && (
                            <Badge variant="outline" className="ml-2 text-xs">
                              Coming Soon
                            </Badge>
                          )}
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
              {selectedConfig && (
                <p className="text-sm text-muted-foreground">
                  {selectedConfig.description}
                </p>
              )}
            </div>

            {/* Timing Options */}
            {formState.modality && isImplemented && (
              <div className="space-y-4 border rounded-lg p-4 bg-muted/30">
                <div className="flex items-center gap-4">
                  <button
                    type="button"
                    className={`flex-1 p-3 rounded-md border-2 transition-colors ${
                      !formState.executeImmediately
                        ? 'border-primary bg-primary/10'
                        : 'border-transparent bg-muted hover:bg-muted/80'
                    }`}
                    onClick={() => setFormState(prev => ({ ...prev, executeImmediately: false }))}
                    disabled={isSubmitting}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <Clock className="h-4 w-4" />
                      <span className="font-medium">Schedule</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Execute at a specific time
                    </p>
                  </button>
                  <button
                    type="button"
                    className={`flex-1 p-3 rounded-md border-2 transition-colors ${
                      formState.executeImmediately
                        ? 'border-primary bg-primary/10'
                        : 'border-transparent bg-muted hover:bg-muted/80'
                    }`}
                    onClick={() => setFormState(prev => ({ ...prev, executeImmediately: true }))}
                    disabled={isSubmitting}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <Zap className="h-4 w-4" />
                      <span className="font-medium">Immediate</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Execute right now
                    </p>
                  </button>
                </div>

                {!formState.executeImmediately && (
                  <div className="space-y-2">
                    <Label htmlFor="scheduled_time">Scheduled Time</Label>
                    <Input
                      id="scheduled_time"
                      type="datetime-local"
                      value={formState.scheduledTime}
                      onChange={(e) => setFormState(prev => ({ 
                        ...prev, 
                        scheduledTime: e.target.value 
                      }))}
                      disabled={isSubmitting}
                    />
                    {timeState?.current_time && (
                      <p className="text-xs text-muted-foreground">
                        Current simulation time: {format(new Date(timeState.current_time), 'yyyy-MM-dd HH:mm:ss')}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Modality-Specific Form */}
            {selectedConfig && isImplemented && (
              <div className="border rounded-lg p-4">
                <h3 className="font-medium mb-4 flex items-center gap-2">
                  <selectedConfig.icon className="h-4 w-4" />
                  {selectedConfig.displayName} Details
                </h3>
                <selectedConfig.FormComponent
                  data={formState.data}
                  onChange={handleDataChange}
                  disabled={isSubmitting}
                />
              </div>
            )}

            {/* Not Implemented Message */}
            {selectedConfig && !isImplemented && (
              <div className="border rounded-lg p-8 text-center text-muted-foreground">
                <selectedConfig.icon className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p className="font-medium">{selectedConfig.displayName} Form Coming Soon</p>
                <p className="text-sm mt-2">
                  This modality form is not yet implemented.
                </p>
              </div>
            )}

            {/* Error Display */}
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-md bg-destructive/10 text-destructive text-sm">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </div>
        </div>

        <DialogFooter className="flex-shrink-0 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!formState.modality || !isImplemented || isSubmitting}
          >
            {isSubmitting ? (
              'Creating...'
            ) : formState.executeImmediately ? (
              <>
                <Zap className="mr-2 h-4 w-4" />
                Execute Now
              </>
            ) : (
              <>
                <Plus className="mr-2 h-4 w-4" />
                Schedule Event
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
