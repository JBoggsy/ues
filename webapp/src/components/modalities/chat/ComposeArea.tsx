/**
 * Compose area component for the Chat Viewer.
 * Text input with role selector and send button.
 */
import { useState, useCallback } from 'react';
import type { KeyboardEvent } from 'react';
import { Send, Paperclip } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { MessageRole } from './types';

interface ComposeAreaProps {
  conversationId: string | null;
  onSendMessage: (role: MessageRole, content: string) => void;
  isSending: boolean;
  disabled?: boolean;
}

export function ComposeArea({
  conversationId,
  onSendMessage,
  isSending,
  disabled = false,
}: ComposeAreaProps) {
  const [message, setMessage] = useState('');
  const [role, setRole] = useState<MessageRole>('user');

  const handleSend = useCallback(() => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || !conversationId) return;

    onSendMessage(role, trimmedMessage);
    setMessage('');
  }, [message, role, conversationId, onSendMessage]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Send on Enter (without Shift)
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleAttachment = useCallback(() => {
    toast.info('Attachment upload coming soon!', {
      description: 'Multimodal message attachments are not yet implemented.',
    });
  }, []);

  const isDisabled = disabled || !conversationId || isSending;

  return (
    <div className="border-t bg-background p-4">
      <div className="flex items-end gap-2">
        {/* Role selector */}
        <Select
          value={role}
          onValueChange={(value) => setRole(value as MessageRole)}
          disabled={isDisabled}
        >
          <SelectTrigger className="w-28 flex-shrink-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="user">User</SelectItem>
            <SelectItem value="assistant">Assistant</SelectItem>
          </SelectContent>
        </Select>

        {/* Message input */}
        <div className="flex-1 relative">
          <Textarea
            placeholder={
              conversationId
                ? 'Type your message... (Enter to send, Shift+Enter for new line)'
                : 'Select or create a conversation first'
            }
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isDisabled}
            className="min-h-[44px] max-h-32 resize-none pr-12"
            rows={1}
          />
        </div>

        {/* Attachment button (placeholder) */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleAttachment}
              disabled={isDisabled}
              className="flex-shrink-0"
            >
              <Paperclip className="h-4 w-4" />
              <span className="sr-only">Attach file</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>Attach file (coming soon)</TooltipContent>
        </Tooltip>

        {/* Send button */}
        <Button
          onClick={handleSend}
          disabled={isDisabled || !message.trim()}
          size="icon"
          className="flex-shrink-0"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send message</span>
        </Button>
      </div>
    </div>
  );
}
