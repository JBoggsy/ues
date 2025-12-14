/**
 * SMS event creation form.
 *
 * Allows creating SMS/RCS messaging events including send, receive,
 * reactions, delivery status updates, and group operations.
 */

import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import type { ModalityFormProps } from './types';

/**
 * Message types.
 */
const MESSAGE_TYPES = [
  { value: 'sms', label: 'SMS' },
  { value: 'rcs', label: 'RCS (Rich)' },
];

/**
 * Delivery status options.
 */
const DELIVERY_STATUSES = [
  { value: 'delivered', label: 'Delivered' },
  { value: 'read', label: 'Read' },
  { value: 'failed', label: 'Failed' },
];

/**
 * Common emoji reactions.
 */
const REACTION_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🎉', '👎', '🔥'];

/**
 * Default data for a new SMS event.
 */
export const smsDefaultData = {
  action: 'receive_message',
  // Message data
  from_number: '+15551234567',
  to_numbers: '+15559876543',
  body: '',
  message_type: 'sms',
  // Status data
  message_id: '',
  new_status: 'delivered',
  // Reaction data
  phone_number: '+15551234567',
  emoji: '👍',
  reaction_id: '',
  // Edit data
  new_body: '',
  // Group data
  creator_number: '+15551234567',
  participant_numbers: '+15559876543, +15551112222',
  group_name: '',
  group_id: '',
  // Participant data
  participant_number: '+15551112222',
  // Conversation data
  conversation_id: '',
  is_muted: false,
  is_archived: false,
  is_pinned: false,
};

/**
 * Validate SMS data based on action.
 */
export function validateSmsData(data: Record<string, unknown>): string | null {
  const action = data.action as string;

  if (!action) {
    return 'Action is required';
  }

  // Validate message actions
  if (action === 'send_message' || action === 'receive_message') {
    if (!data.from_number || (data.from_number as string).trim() === '') {
      return 'From phone number is required';
    }
    if (!data.to_numbers || (data.to_numbers as string).trim() === '') {
      return 'To phone number(s) required';
    }
    if (!data.body || (data.body as string).trim() === '') {
      return 'Message body is required';
    }
  }

  // Validate status update
  if (action === 'update_delivery_status') {
    if (!data.message_id || (data.message_id as string).trim() === '') {
      return 'Message ID is required';
    }
    if (!data.new_status) {
      return 'New status is required';
    }
  }

  // Validate reaction actions
  if (action === 'add_reaction') {
    if (!data.message_id || (data.message_id as string).trim() === '') {
      return 'Message ID is required';
    }
    if (!data.emoji || (data.emoji as string).trim() === '') {
      return 'Emoji is required';
    }
  }
  if (action === 'remove_reaction') {
    if (!data.message_id || (data.message_id as string).trim() === '') {
      return 'Message ID is required';
    }
    if (!data.reaction_id || (data.reaction_id as string).trim() === '') {
      return 'Reaction ID is required';
    }
  }

  // Validate edit
  if (action === 'edit_message') {
    if (!data.message_id || (data.message_id as string).trim() === '') {
      return 'Message ID is required';
    }
    if (!data.new_body || (data.new_body as string).trim() === '') {
      return 'New message body is required';
    }
  }

  // Validate delete
  if (action === 'delete_message') {
    if (!data.message_id || (data.message_id as string).trim() === '') {
      return 'Message ID is required';
    }
  }

  // Validate group creation
  if (action === 'create_group') {
    if (!data.creator_number || (data.creator_number as string).trim() === '') {
      return 'Creator phone number is required';
    }
    if (!data.participant_numbers || (data.participant_numbers as string).trim() === '') {
      return 'Participant phone numbers are required (at least 2)';
    }
  }

  // Validate group update
  if (action === 'update_group') {
    if (!data.group_id || (data.group_id as string).trim() === '') {
      return 'Group ID is required';
    }
  }

  // Validate participant operations
  if (action === 'add_participant' || action === 'remove_participant') {
    if (!data.group_id || (data.group_id as string).trim() === '') {
      return 'Group ID is required';
    }
    if (!data.participant_number || (data.participant_number as string).trim() === '') {
      return 'Participant phone number is required';
    }
  }

  // Validate leave group
  if (action === 'leave_group') {
    if (!data.group_id || (data.group_id as string).trim() === '') {
      return 'Group ID is required';
    }
    if (!data.phone_number || (data.phone_number as string).trim() === '') {
      return 'Phone number is required';
    }
  }

  // Validate conversation update
  if (action === 'update_conversation') {
    if (!data.conversation_id || (data.conversation_id as string).trim() === '') {
      return 'Conversation ID is required';
    }
  }

  return null;
}

/**
 * Transform form data to API format.
 * The API expects action-specific data in nested objects.
 */
export function transformSmsData(data: Record<string, unknown>): Record<string, unknown> {
  const action = data.action as string;
  const result: Record<string, unknown> = { action };

  // Parse comma-separated phone numbers into array
  const parsePhoneNumbers = (str: string): string[] => {
    return str.split(',').map((n) => n.trim()).filter((n) => n.length > 0);
  };

  if (action === 'send_message' || action === 'receive_message') {
    result.message_data = {
      from_number: data.from_number,
      to_numbers: parsePhoneNumbers(data.to_numbers as string),
      body: data.body,
      message_type: data.message_type || 'sms',
    };
  } else if (action === 'update_delivery_status') {
    result.delivery_update_data = {
      message_id: data.message_id,
      new_status: data.new_status,
    };
  } else if (action === 'add_reaction') {
    result.reaction_data = {
      message_id: data.message_id,
      phone_number: data.phone_number,
      emoji: data.emoji,
    };
  } else if (action === 'remove_reaction') {
    result.reaction_data = {
      message_id: data.message_id,
      phone_number: data.phone_number,
      reaction_id: data.reaction_id,
    };
  } else if (action === 'edit_message') {
    result.edit_data = {
      message_id: data.message_id,
      new_body: data.new_body,
    };
  } else if (action === 'delete_message') {
    result.delete_data = {
      message_id: data.message_id,
    };
  } else if (action === 'create_group') {
    result.group_data = {
      creator_number: data.creator_number,
      participant_numbers: parsePhoneNumbers(data.participant_numbers as string),
      name: data.group_name || undefined,
    };
  } else if (action === 'update_group') {
    result.group_data = {
      group_id: data.group_id,
      name: data.group_name || undefined,
    };
  } else if (action === 'add_participant' || action === 'remove_participant') {
    result.participant_data = {
      group_id: data.group_id,
      phone_number: data.participant_number,
    };
  } else if (action === 'leave_group') {
    result.participant_data = {
      group_id: data.group_id,
      phone_number: data.phone_number,
    };
  } else if (action === 'update_conversation') {
    result.conversation_update_data = {
      conversation_id: data.conversation_id,
      is_muted: data.is_muted,
      is_archived: data.is_archived,
      is_pinned: data.is_pinned,
    };
  }

  return result;
}

/**
 * SMS form component.
 */
export function SMSForm({ data, onChange }: ModalityFormProps) {
  const action = data.action as string;

  const handleChange = (field: string, value: string | boolean) => {
    onChange({ ...data, [field]: value });
  };

  const isMessageAction = action === 'send_message' || action === 'receive_message';
  const isStatusAction = action === 'update_delivery_status';
  const isAddReaction = action === 'add_reaction';
  const isRemoveReaction = action === 'remove_reaction';
  const isEditAction = action === 'edit_message';
  const isDeleteAction = action === 'delete_message';
  const isCreateGroup = action === 'create_group';
  const isUpdateGroup = action === 'update_group';
  const isParticipantAction = action === 'add_participant' || action === 'remove_participant';
  const isLeaveGroup = action === 'leave_group';
  const isConversationUpdate = action === 'update_conversation';

  return (
    <div className="space-y-4">
      {/* Action Selector */}
      <div className="space-y-2">
        <Label htmlFor="action">Action</Label>
        <Select
          value={action}
          onValueChange={(v) => handleChange('action', v)}
        >
          <SelectTrigger id="action">
            <SelectValue placeholder="Select action" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="receive_message" className="font-medium">
              📥 Receive Message
            </SelectItem>
            <SelectItem value="send_message">📤 Send Message</SelectItem>
            <SelectItem value="edit_message">✏️ Edit Message</SelectItem>
            <SelectItem value="delete_message">🗑️ Delete Message</SelectItem>
            <SelectItem value="update_delivery_status">📬 Update Delivery Status</SelectItem>
            <SelectItem value="add_reaction">👍 Add Reaction</SelectItem>
            <SelectItem value="remove_reaction">👎 Remove Reaction</SelectItem>
            <SelectItem value="create_group">👥 Create Group</SelectItem>
            <SelectItem value="update_group">✏️ Update Group</SelectItem>
            <SelectItem value="add_participant">➕ Add Participant</SelectItem>
            <SelectItem value="remove_participant">➖ Remove Participant</SelectItem>
            <SelectItem value="leave_group">🚪 Leave Group</SelectItem>
            <SelectItem value="update_conversation">⚙️ Update Conversation</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Message Fields (send/receive) */}
      {isMessageAction && (
        <>
          <div className="space-y-2">
            <Label htmlFor="from_number">From Phone Number</Label>
            <Input
              id="from_number"
              placeholder="+15551234567"
              value={data.from_number as string}
              onChange={(e) => handleChange('from_number', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="to_numbers">To Phone Number(s)</Label>
            <Input
              id="to_numbers"
              placeholder="+15559876543, +15551112222"
              value={data.to_numbers as string}
              onChange={(e) => handleChange('to_numbers', e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated for multiple recipients
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="body">Message Body</Label>
            <Textarea
              id="body"
              placeholder="Type your message..."
              value={data.body as string}
              onChange={(e) => handleChange('body', e.target.value)}
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="message_type">Message Type</Label>
            <Select
              value={data.message_type as string}
              onValueChange={(v) => handleChange('message_type', v)}
            >
              <SelectTrigger id="message_type">
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                {MESSAGE_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      )}

      {/* Delivery Status Fields */}
      {isStatusAction && (
        <>
          <div className="space-y-2">
            <Label htmlFor="message_id">Message ID</Label>
            <Input
              id="message_id"
              placeholder="msg_abc123..."
              value={data.message_id as string}
              onChange={(e) => handleChange('message_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new_status">New Status</Label>
            <Select
              value={data.new_status as string}
              onValueChange={(v) => handleChange('new_status', v)}
            >
              <SelectTrigger id="new_status">
                <SelectValue placeholder="Select status" />
              </SelectTrigger>
              <SelectContent>
                {DELIVERY_STATUSES.map((status) => (
                  <SelectItem key={status.value} value={status.value}>
                    {status.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </>
      )}

      {/* Add Reaction Fields */}
      {isAddReaction && (
        <>
          <div className="space-y-2">
            <Label htmlFor="message_id">Message ID</Label>
            <Input
              id="message_id"
              placeholder="msg_abc123..."
              value={data.message_id as string}
              onChange={(e) => handleChange('message_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone_number">Reacting Phone Number</Label>
            <Input
              id="phone_number"
              placeholder="+15551234567"
              value={data.phone_number as string}
              onChange={(e) => handleChange('phone_number', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label>Emoji</Label>
            <div className="flex flex-wrap gap-2">
              {REACTION_EMOJIS.map((emoji) => (
                <button
                  key={emoji}
                  type="button"
                  onClick={() => handleChange('emoji', emoji)}
                  className={`p-2 text-xl rounded border transition-colors ${
                    data.emoji === emoji
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  {emoji}
                </button>
              ))}
            </div>
            <Input
              placeholder="Or type custom emoji"
              value={data.emoji as string}
              onChange={(e) => handleChange('emoji', e.target.value)}
              className="mt-2"
            />
          </div>
        </>
      )}

      {/* Remove Reaction Fields */}
      {isRemoveReaction && (
        <>
          <div className="space-y-2">
            <Label htmlFor="message_id">Message ID</Label>
            <Input
              id="message_id"
              placeholder="msg_abc123..."
              value={data.message_id as string}
              onChange={(e) => handleChange('message_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone_number">Phone Number</Label>
            <Input
              id="phone_number"
              placeholder="+15551234567"
              value={data.phone_number as string}
              onChange={(e) => handleChange('phone_number', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="reaction_id">Reaction ID</Label>
            <Input
              id="reaction_id"
              placeholder="reaction_xyz789..."
              value={data.reaction_id as string}
              onChange={(e) => handleChange('reaction_id', e.target.value)}
            />
          </div>
        </>
      )}

      {/* Edit Message Fields */}
      {isEditAction && (
        <>
          <div className="space-y-2">
            <Label htmlFor="message_id">Message ID</Label>
            <Input
              id="message_id"
              placeholder="msg_abc123..."
              value={data.message_id as string}
              onChange={(e) => handleChange('message_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new_body">New Message Body</Label>
            <Textarea
              id="new_body"
              placeholder="Type new message content..."
              value={data.new_body as string}
              onChange={(e) => handleChange('new_body', e.target.value)}
              rows={3}
            />
          </div>
        </>
      )}

      {/* Delete Message Fields */}
      {isDeleteAction && (
        <div className="space-y-2">
          <Label htmlFor="message_id">Message ID</Label>
          <Input
            id="message_id"
            placeholder="msg_abc123..."
            value={data.message_id as string}
            onChange={(e) => handleChange('message_id', e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            The message will be permanently deleted
          </p>
        </div>
      )}

      {/* Create Group Fields */}
      {isCreateGroup && (
        <>
          <div className="space-y-2">
            <Label htmlFor="creator_number">Creator Phone Number</Label>
            <Input
              id="creator_number"
              placeholder="+15551234567"
              value={data.creator_number as string}
              onChange={(e) => handleChange('creator_number', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="participant_numbers">Participant Phone Numbers</Label>
            <Input
              id="participant_numbers"
              placeholder="+15559876543, +15551112222"
              value={data.participant_numbers as string}
              onChange={(e) => handleChange('participant_numbers', e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated, minimum 2 participants required
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="group_name">Group Name (Optional)</Label>
            <Input
              id="group_name"
              placeholder="Family Chat"
              value={data.group_name as string}
              onChange={(e) => handleChange('group_name', e.target.value)}
            />
          </div>
        </>
      )}

      {/* Update Group Fields */}
      {isUpdateGroup && (
        <>
          <div className="space-y-2">
            <Label htmlFor="group_id">Group ID</Label>
            <Input
              id="group_id"
              placeholder="group_abc123..."
              value={data.group_id as string}
              onChange={(e) => handleChange('group_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="group_name">New Group Name</Label>
            <Input
              id="group_name"
              placeholder="Updated Group Name"
              value={data.group_name as string}
              onChange={(e) => handleChange('group_name', e.target.value)}
            />
          </div>
        </>
      )}

      {/* Add/Remove Participant Fields */}
      {isParticipantAction && (
        <>
          <div className="space-y-2">
            <Label htmlFor="group_id">Group ID</Label>
            <Input
              id="group_id"
              placeholder="group_abc123..."
              value={data.group_id as string}
              onChange={(e) => handleChange('group_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="participant_number">Participant Phone Number</Label>
            <Input
              id="participant_number"
              placeholder="+15551112222"
              value={data.participant_number as string}
              onChange={(e) => handleChange('participant_number', e.target.value)}
            />
          </div>
        </>
      )}

      {/* Leave Group Fields */}
      {isLeaveGroup && (
        <>
          <div className="space-y-2">
            <Label htmlFor="group_id">Group ID</Label>
            <Input
              id="group_id"
              placeholder="group_abc123..."
              value={data.group_id as string}
              onChange={(e) => handleChange('group_id', e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone_number">Your Phone Number</Label>
            <Input
              id="phone_number"
              placeholder="+15551234567"
              value={data.phone_number as string}
              onChange={(e) => handleChange('phone_number', e.target.value)}
            />
          </div>
        </>
      )}

      {/* Update Conversation Fields */}
      {isConversationUpdate && (
        <>
          <div className="space-y-2">
            <Label htmlFor="conversation_id">Conversation ID</Label>
            <Input
              id="conversation_id"
              placeholder="conv_abc123..."
              value={data.conversation_id as string}
              onChange={(e) => handleChange('conversation_id', e.target.value)}
            />
          </div>

          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="is_muted">Muted</Label>
              <input
                type="checkbox"
                id="is_muted"
                checked={data.is_muted as boolean}
                onChange={(e) => handleChange('is_muted', e.target.checked)}
                className="h-4 w-4"
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="is_archived">Archived</Label>
              <input
                type="checkbox"
                id="is_archived"
                checked={data.is_archived as boolean}
                onChange={(e) => handleChange('is_archived', e.target.checked)}
                className="h-4 w-4"
              />
            </div>

            <div className="flex items-center justify-between">
              <Label htmlFor="is_pinned">Pinned</Label>
              <input
                type="checkbox"
                id="is_pinned"
                checked={data.is_pinned as boolean}
                onChange={(e) => handleChange('is_pinned', e.target.checked)}
                className="h-4 w-4"
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
