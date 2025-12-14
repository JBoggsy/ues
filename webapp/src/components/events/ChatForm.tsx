/**
 * Chat event creation form.
 *
 * Allows creating chat messages, deleting messages, or clearing conversations.
 * Supports both simple text and multimodal content.
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
 * Default data for a new chat event.
 */
export const chatDefaultData = {
  operation: 'send_message',
  role: 'user',
  content: '',
  message_id: '',
  conversation_id: 'default',
  // Metadata fields (optional)
  model: '',
  token_count: '',
};

/**
 * Validate chat data based on operation.
 */
export function validateChatData(data: Record<string, unknown>): string | null {
  const operation = data.operation as string;

  if (!operation) {
    return 'Operation is required';
  }

  if (operation === 'send_message') {
    if (!data.role) {
      return 'Role is required for send_message';
    }
    if (!data.content || (data.content as string).trim() === '') {
      return 'Message content is required';
    }
  }

  if (operation === 'delete_message') {
    if (!data.message_id || (data.message_id as string).trim() === '') {
      return 'Message ID is required for delete_message';
    }
  }

  if (operation === 'clear_conversation') {
    if (!data.conversation_id || (data.conversation_id as string).trim() === '') {
      return 'Conversation ID is required for clear_conversation';
    }
  }

  return null;
}

/**
 * Transform form data to API format.
 * Constructs metadata from optional fields if provided.
 */
export function transformChatData(data: Record<string, unknown>): Record<string, unknown> {
  const operation = data.operation as string;
  const result: Record<string, unknown> = {
    operation,
    conversation_id: data.conversation_id || 'default',
  };

  if (operation === 'send_message') {
    result.role = data.role;
    result.content = data.content;
    
    // Build metadata from optional fields
    const metadata: Record<string, unknown> = {};
    if (data.model && (data.model as string).trim()) {
      metadata.model = data.model;
    }
    if (data.token_count && (data.token_count as string).trim()) {
      const tokenCount = parseInt(data.token_count as string, 10);
      if (!isNaN(tokenCount)) {
        metadata.token_count = tokenCount;
      }
    }
    if (Object.keys(metadata).length > 0) {
      result.metadata = metadata;
    }
  } else if (operation === 'delete_message') {
    result.message_id = data.message_id;
  }
  // clear_conversation only needs conversation_id which is already set

  return result;
}

/**
 * Chat form component.
 */
export function ChatForm({ data, onChange }: ModalityFormProps) {
  const operation = data.operation as string;

  const handleChange = (field: string, value: string) => {
    onChange({ ...data, [field]: value });
  };

  const isSendMessage = operation === 'send_message';
  const isDeleteMessage = operation === 'delete_message';
  const isClearConversation = operation === 'clear_conversation';

  return (
    <div className="space-y-4">
      {/* Operation Selector */}
      <div className="space-y-2">
        <Label htmlFor="operation">Operation</Label>
        <Select
          value={operation}
          onValueChange={(v) => handleChange('operation', v)}
        >
          <SelectTrigger id="operation">
            <SelectValue placeholder="Select operation" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="send_message">💬 Send Message</SelectItem>
            <SelectItem value="delete_message">🗑️ Delete Message</SelectItem>
            <SelectItem value="clear_conversation">🧹 Clear Conversation</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Conversation ID (always shown) */}
      <div className="space-y-2">
        <Label htmlFor="conversation_id">Conversation ID</Label>
        <Input
          id="conversation_id"
          placeholder="default"
          value={data.conversation_id as string}
          onChange={(e) => handleChange('conversation_id', e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Thread or conversation identifier
        </p>
      </div>

      {/* Send Message Fields */}
      {isSendMessage && (
        <>
          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select
              value={data.role as string}
              onValueChange={(v) => handleChange('role', v)}
            >
              <SelectTrigger id="role">
                <SelectValue placeholder="Select role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user">👤 User</SelectItem>
                <SelectItem value="assistant">🤖 Assistant</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="content">Message Content</Label>
            <Textarea
              id="content"
              placeholder="Type your message..."
              value={data.content as string}
              onChange={(e) => handleChange('content', e.target.value)}
              rows={4}
            />
          </div>

          {/* Optional Metadata Section */}
          <div className="border-t pt-4 mt-4">
            <p className="text-sm font-medium mb-3 text-muted-foreground">
              Optional Metadata
            </p>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="model">Model Name</Label>
                <Input
                  id="model"
                  placeholder="e.g., gpt-4, claude-3-opus"
                  value={data.model as string}
                  onChange={(e) => handleChange('model', e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  AI model that generated this response (for assistant messages)
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="token_count">Token Count</Label>
                <Input
                  id="token_count"
                  type="number"
                  placeholder="e.g., 150"
                  value={data.token_count as string}
                  onChange={(e) => handleChange('token_count', e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Number of tokens in this message
                </p>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Delete Message Fields */}
      {isDeleteMessage && (
        <div className="space-y-2">
          <Label htmlFor="message_id">Message ID</Label>
          <Input
            id="message_id"
            placeholder="msg_abc123..."
            value={data.message_id as string}
            onChange={(e) => handleChange('message_id', e.target.value)}
          />
          <p className="text-xs text-muted-foreground">
            The message will be permanently deleted from the conversation
          </p>
        </div>
      )}

      {/* Clear Conversation Info */}
      {isClearConversation && (
        <div className="rounded-md bg-amber-500/10 border border-amber-500/20 p-4">
          <p className="text-sm text-amber-600 dark:text-amber-400">
            ⚠️ This will delete all messages in the conversation "{data.conversation_id as string}".
            This action cannot be undone within the simulation.
          </p>
        </div>
      )}
    </div>
  );
}
