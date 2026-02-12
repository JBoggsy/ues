/**
 * Message thread component for SMS viewer.
 * Displays messages in a chat bubble format with compose area.
 */
import { useMemo, useRef, useEffect, useState } from 'react';
import { format, parseISO } from 'date-fns';
import { 
  Send, 
  Paperclip, 
  Smile,
  Users,
  MoreVertical,
  Reply,
  Check,
  CheckCheck,
  AlertCircle,
  MessageSquare
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { 
  SMSState, 
  SMSConversation, 
  SMSMessage,
  MessageReaction,
  ContactNameResolver,
} from './types';
import { resolveContactName } from './types';

interface MessageThreadProps {
  smsState: SMSState | null;
  selectedThreadId: string | null;
  onSendMessage: (body: string) => void;
  isSending?: boolean;
  /** Contacts-backed phone-number-to-name resolver. */
  contactNameResolver?: ContactNameResolver;
}

/**
 * Format timestamp for message display.
 */
function formatMessageTime(timestamp: string): string {
  try {
    return format(parseISO(timestamp), 'h:mm a');
  } catch {
    return '';
  }
}

/**
 * Format date for message grouping header.
 */
function formatMessageDate(timestamp: string): string {
  try {
    const date = parseISO(timestamp);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    }
    if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    }
    return format(date, 'MMMM d, yyyy');
  } catch {
    return '';
  }
}

/**
 * Delivery status indicator component.
 */
function DeliveryStatus({ 
  status, 
  deliveredAt 
}: { 
  status: string; 
  deliveredAt?: string;
}) {
  const getStatusContent = () => {
    switch (status) {
      case 'read':
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <CheckCheck className="h-3 w-3 text-blue-500" />
              </TooltipTrigger>
              <TooltipContent>Read</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      case 'delivered':
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <CheckCheck className="h-3 w-3 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>
                Delivered{deliveredAt && ` at ${formatMessageTime(deliveredAt)}`}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      case 'sent':
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Check className="h-3 w-3 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent>Sent</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      case 'sending':
        return (
          <span className="text-xs text-muted-foreground">Sending...</span>
        );
      case 'failed':
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <AlertCircle className="h-3 w-3 text-destructive" />
              </TooltipTrigger>
              <TooltipContent>Failed to send</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      default:
        return null;
    }
  };

  return <span className="inline-flex items-center ml-1">{getStatusContent()}</span>;
}

/**
 * Reactions display for a message.
 */
function ReactionsDisplay({
  reactions,
  contactNameResolver,
}: {
  reactions: MessageReaction[];
  contactNameResolver?: ContactNameResolver;
}) {
  if (reactions.length === 0) return null;

  // Group reactions by emoji
  const groupedReactions = reactions.reduce((acc, reaction) => {
    if (!acc[reaction.emoji]) {
      acc[reaction.emoji] = [];
    }
    acc[reaction.emoji].push(reaction.phone_number);
    return acc;
  }, {} as Record<string, string[]>);

  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {Object.entries(groupedReactions).map(([emoji, numbers]) => (
        <TooltipProvider key={emoji}>
          <Tooltip>
            <TooltipTrigger>
              <Badge variant="secondary" className="text-xs px-1.5 py-0">
                {emoji} {numbers.length > 1 && numbers.length}
              </Badge>
            </TooltipTrigger>
            <TooltipContent>
              {numbers.map(n => resolveContactName(n, contactNameResolver)).join(', ')}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      ))}
    </div>
  );
}

/**
 * Single message bubble component.
 */
function MessageBubble({
  message,
  isOutgoing,
  showSender,
  senderName,
  contactNameResolver,
}: {
  message: SMSMessage;
  isOutgoing: boolean;
  showSender: boolean;
  senderName: string;
  contactNameResolver?: ContactNameResolver;
}) {
  return (
    <div className={cn(
      'flex flex-col max-w-[75%] mb-1',
      isOutgoing ? 'items-end ml-auto' : 'items-start'
    )}>
      {/* Sender name for group chats */}
      {showSender && !isOutgoing && (
        <span className="text-xs text-muted-foreground ml-2 mb-0.5">
          {senderName}
        </span>
      )}

      {/* Message bubble */}
      <div className={cn(
        'px-3 py-1.5 rounded-2xl',
        isOutgoing 
          ? 'bg-primary text-primary-foreground rounded-br-sm' 
          : 'bg-muted rounded-bl-sm',
        message.is_deleted && 'italic opacity-60'
      )}>
        {/* Reply indicator */}
        {message.replied_to_message_id && (
          <div className={cn(
            'text-xs mb-1 pb-1 border-b flex items-center gap-1',
            isOutgoing ? 'border-primary-foreground/30' : 'border-border'
          )}>
            <Reply className="h-3 w-3" />
            <span className="opacity-70">Reply</span>
          </div>
        )}

        {/* Message body */}
        <p className="text-sm whitespace-pre-wrap break-words">
          {message.is_deleted ? 'This message was deleted' : message.body}
        </p>

        {/* Attachments indicator */}
        {message.attachments.length > 0 && (
          <div className="flex items-center gap-1 mt-1 text-xs opacity-70">
            <Paperclip className="h-3 w-3" />
            {message.attachments.length} attachment{message.attachments.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Time and status row */}
      <div className="flex items-center gap-1 px-2 mt-0.5">
        <span className="text-xs text-muted-foreground">
          {formatMessageTime(message.sent_at)}
        </span>
        {isOutgoing && (
          <DeliveryStatus 
            status={message.delivery_status} 
            deliveredAt={message.delivered_at}
          />
        )}
        {message.edited_at && (
          <span className="text-xs text-muted-foreground">(edited)</span>
        )}
      </div>

      {/* Reactions */}
      <ReactionsDisplay
        reactions={message.reactions}
        contactNameResolver={contactNameResolver}
      />
    </div>
  );
}

/**
 * Thread header with conversation info.
 */
function ThreadHeader({
  conversation,
  userPhoneNumber,
  contactNameResolver,
}: {
  conversation: SMSConversation;
  userPhoneNumber: string;
  contactNameResolver?: ContactNameResolver;
}) {
  const displayInfo = useMemo(() => {
    if (conversation.conversation_type === 'group') {
      const activeCount = conversation.participants.filter(p => !p.left_at).length;
      return {
        name: conversation.group_name || 'Group Chat',
        subtitle: `${activeCount} participants`,
        isGroup: true,
      };
    } else {
      const other = conversation.participants.find(
        p => p.phone_number !== userPhoneNumber && !p.left_at
      );
      const phoneNumber = other?.phone_number || 'Unknown';
      return {
        name: resolveContactName(phoneNumber, contactNameResolver),
        subtitle: phoneNumber,
        isGroup: false,
      };
    }
  }, [conversation, userPhoneNumber, contactNameResolver]);

  return (
    <div className="flex items-center justify-between px-4 py-2 border-b bg-background">
      <div className="flex items-center gap-3">
        <div className={cn(
          'w-10 h-10 rounded-full flex items-center justify-center',
          displayInfo.isGroup ? 'bg-blue-100' : 'bg-muted'
        )}>
          {displayInfo.isGroup ? (
            <Users className="h-5 w-5 text-blue-600" />
          ) : (
            <span className="text-lg font-medium text-muted-foreground">
              {displayInfo.name.charAt(0).toUpperCase()}
            </span>
          )}
        </div>
        <div>
          <div className="font-medium">{displayInfo.name}</div>
          <div className="text-xs text-muted-foreground">{displayInfo.subtitle}</div>
        </div>
      </div>
      <Button variant="ghost" size="icon">
        <MoreVertical className="h-4 w-4" />
      </Button>
    </div>
  );
}

/**
 * Compose area for sending messages.
 */
function ComposeArea({
  onSend,
  isSending,
  disabled,
}: {
  onSend: (body: string) => void;
  isSending?: boolean;
  disabled?: boolean;
}) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isSending && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="border-t p-2 bg-background">
      <form onSubmit={handleSubmit} className="flex items-center gap-2">
        <Button 
          type="button" 
          variant="ghost" 
          size="icon"
          disabled={disabled}
          className="flex-shrink-0"
        >
          <Paperclip className="h-4 w-4" />
        </Button>
        <Input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={disabled || isSending}
          className="flex-1"
        />
        <Button 
          type="button" 
          variant="ghost" 
          size="icon"
          disabled={disabled}
          className="flex-shrink-0"
        >
          <Smile className="h-4 w-4" />
        </Button>
        <Button 
          type="submit" 
          size="icon"
          disabled={!message.trim() || isSending || disabled}
          className="flex-shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  );
}

export function MessageThread({
  smsState,
  selectedThreadId,
  onSendMessage,
  isSending,
  contactNameResolver,
}: MessageThreadProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get selected conversation and its messages
  const { conversation, messages, isGroup } = useMemo(() => {
    if (!smsState || !selectedThreadId) {
      return { conversation: null, messages: [], isGroup: false };
    }

    const conv = smsState.conversations[selectedThreadId];
    if (!conv) {
      return { conversation: null, messages: [], isGroup: false };
    }

    const msgs = Object.values(smsState.messages)
      .filter(m => m.thread_id === selectedThreadId && !m.is_deleted)
      .sort((a, b) => new Date(a.sent_at).getTime() - new Date(b.sent_at).getTime());

    return {
      conversation: conv,
      messages: msgs,
      isGroup: conv.conversation_type === 'group',
    };
  }, [smsState, selectedThreadId]);

  // Group messages by date
  const groupedMessages = useMemo(() => {
    const groups: { date: string; messages: SMSMessage[] }[] = [];
    let currentDate = '';

    for (const message of messages) {
      const msgDate = formatMessageDate(message.sent_at);
      if (msgDate !== currentDate) {
        currentDate = msgDate;
        groups.push({ date: msgDate, messages: [] });
      }
      groups[groups.length - 1].messages.push(message);
    }

    return groups;
  }, [messages]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  // Empty state
  if (!smsState || !selectedThreadId || !conversation) {
    return (
      <div className="flex-1 flex items-center justify-center bg-muted/20">
        <div className="text-center text-muted-foreground">
          <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Select a conversation to view messages</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <ThreadHeader 
        conversation={conversation} 
        userPhoneNumber={smsState.user_phone_number}
        contactNameResolver={contactNameResolver}
      />

      {/* Messages */}
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        {groupedMessages.map((group) => (
          <div key={group.date}>
            {/* Date separator */}
            <div className="flex items-center justify-center my-4">
              <span className="text-xs text-muted-foreground bg-background px-2 py-0.5 rounded-full border">
                {group.date}
              </span>
            </div>

            {/* Messages */}
            {group.messages.map((message, idx) => {
              const isOutgoing = message.direction === 'outgoing';
              // Show sender name in groups for consecutive messages from different senders
              const prevMessage = idx > 0 ? group.messages[idx - 1] : null;
              const showSender = isGroup && 
                !isOutgoing && 
                (!prevMessage || prevMessage.from_number !== message.from_number);

              return (
                <MessageBubble
                  key={message.message_id}
                  message={message}
                  isOutgoing={isOutgoing}
                  showSender={showSender}
                  senderName={resolveContactName(message.from_number, contactNameResolver)}
                  contactNameResolver={contactNameResolver}
                />
              );
            })}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </ScrollArea>

      {/* Compose area */}
      <ComposeArea 
        onSend={onSendMessage}
        isSending={isSending}
        disabled={conversation.is_archived}
      />
    </div>
  );
}
