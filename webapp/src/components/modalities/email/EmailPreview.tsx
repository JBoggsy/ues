/**
 * Email preview panel component.
 * Displays the full content of the selected email/thread.
 */
import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import {
  Reply,
  ReplyAll,
  Forward,
  Star,
  Paperclip,
  ChevronUp,
  Mail,
} from 'lucide-react';
import type { EmailState, EmailMessage } from './types';

interface EmailPreviewProps {
  emailState: EmailState | null;
  selectedThreadId: string | null;
  selectedMessageId: string | null;
  expandedMessageIds: Set<string>;
  onToggleExpand: (messageId: string) => void;
  onReply: (messageId: string) => void;
  onReplyAll: (messageId: string) => void;
  onForward: (messageId: string) => void;
  onToggleStar: (messageId: string) => void;
}

/**
 * Format full date for email header.
 */
function formatFullDate(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString([], {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/**
 * Format email address for display.
 */
function formatAddress(email: string): string {
  return email;
}

/**
 * Get all messages in a thread, sorted by date ascending.
 */
function getThreadMessages(
  emailState: EmailState | null,
  threadId: string | null
): EmailMessage[] {
  if (!emailState || !threadId) return [];

  const thread = emailState.threads[threadId];
  if (!thread) return [];

  const messages: EmailMessage[] = [];
  for (const msgId of thread.message_ids) {
    const email = emailState.emails[msgId];
    if (email) messages.push(email);
  }

  // Sort by sent_at ascending (oldest first)
  messages.sort(
    (a, b) => new Date(a.sent_at).getTime() - new Date(b.sent_at).getTime()
  );

  return messages;
}

/**
 * Single email message display within the preview.
 */
function MessageItem({
  message,
  isExpanded,
  onToggleExpand,
  onReply,
  onReplyAll,
  onForward,
  onToggleStar,
}: {
  message: EmailMessage;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onReply: () => void;
  onReplyAll: () => void;
  onForward: () => void;
  onToggleStar: () => void;
}) {
  const hasMultipleRecipients =
    message.to_addresses.length > 1 || message.cc_addresses.length > 0;

  return (
    <div
      className={cn(
        'border rounded-lg',
        isExpanded ? 'bg-background' : 'bg-muted/30'
      )}
    >
      {/* Message Header - Always visible */}
      <div
        className={cn(
          'flex items-start gap-3 p-4 cursor-pointer',
          !isExpanded && 'hover:bg-muted/50'
        )}
        onClick={() => !isExpanded && onToggleExpand()}
      >
        {/* Avatar placeholder */}
        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
          <span className="text-sm font-medium text-primary">
            {message.from_address.charAt(0).toUpperCase()}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="font-medium truncate">
                {message.from_address}
              </span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {message.attachments.length > 0 && (
                <Paperclip className="h-4 w-4 text-muted-foreground" />
              )}
              <span className="text-xs text-muted-foreground">
                {formatFullDate(message.sent_at)}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleStar();
                }}
                className={cn(
                  'transition-colors',
                  message.is_starred
                    ? 'text-yellow-500'
                    : 'text-muted-foreground/50 hover:text-muted-foreground'
                )}
              >
                <Star
                  className="h-4 w-4"
                  fill={message.is_starred ? 'currentColor' : 'none'}
                />
              </button>
              {isExpanded && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleExpand();
                  }}
                >
                  <ChevronUp className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>

          {/* Collapsed view - show preview */}
          {!isExpanded && (
            <p className="text-sm text-muted-foreground truncate mt-1">
              {message.body_text.slice(0, 150)}
            </p>
          )}

          {/* Expanded view - show full details */}
          {isExpanded && (
            <div className="text-sm text-muted-foreground mt-1">
              <div>
                To: {message.to_addresses.map(formatAddress).join(', ')}
              </div>
              {message.cc_addresses.length > 0 && (
                <div>
                  Cc: {message.cc_addresses.map(formatAddress).join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Message Body - Only when expanded */}
      {isExpanded && (
        <>
          <Separator />
          <div className="p-4">
            {/* Labels */}
            {message.labels.length > 0 && (
              <div className="flex gap-1 mb-4">
                {message.labels.map((label) => (
                  <Badge key={label} variant="secondary" className="text-xs">
                    {label}
                  </Badge>
                ))}
              </div>
            )}

            {/* Body Content */}
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <pre className="whitespace-pre-wrap font-sans text-sm">
                {message.body_text}
              </pre>
            </div>

            {/* Attachments */}
            {message.attachments.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm font-medium mb-2">
                  Attachments ({message.attachments.length})
                </p>
                <div className="flex flex-wrap gap-2">
                  {message.attachments.map((attachment, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 px-3 py-2 bg-muted rounded-md text-sm"
                    >
                      <Paperclip className="h-4 w-4" />
                      <span>{String(attachment)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="flex gap-2 mt-4 pt-4 border-t">
              <Button variant="outline" size="sm" onClick={onReply}>
                <Reply className="h-4 w-4 mr-2" />
                Reply
              </Button>
              {hasMultipleRecipients && (
                <Button variant="outline" size="sm" onClick={onReplyAll}>
                  <ReplyAll className="h-4 w-4 mr-2" />
                  Reply All
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={onForward}>
                <Forward className="h-4 w-4 mr-2" />
                Forward
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export function EmailPreview({
  emailState,
  selectedThreadId,
  selectedMessageId: _selectedMessageId,
  expandedMessageIds,
  onToggleExpand,
  onReply,
  onReplyAll,
  onForward,
  onToggleStar,
}: EmailPreviewProps) {
  const threadMessages = useMemo(
    () => getThreadMessages(emailState, selectedThreadId),
    [emailState, selectedThreadId]
  );

  // Get the selected thread info
  const thread = selectedThreadId
    ? emailState?.threads[selectedThreadId]
    : null;

  if (!selectedThreadId || !thread) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground border-l">
        <div className="text-center">
          <Mail className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Select an email to read</p>
        </div>
      </div>
    );
  }

  if (threadMessages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground border-l">
        <p>Email not found</p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 border-l">
      {/* Thread Header */}
      <div className="px-4 py-3 border-b">
        <h2 className="text-lg font-semibold truncate">
          {thread.subject || '(No Subject)'}
        </h2>
        <p className="text-sm text-muted-foreground">
          {threadMessages.length} {threadMessages.length === 1 ? 'message' : 'messages'}
          {thread.unread_count > 0 && (
            <span className="ml-2 text-primary">
              ({thread.unread_count} unread)
            </span>
          )}
        </p>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {threadMessages.map((message, idx) => {
            const isLast = idx === threadMessages.length - 1;
            const isExpanded = expandedMessageIds.has(message.message_id) || isLast;

            return (
              <MessageItem
                key={message.message_id}
                message={message}
                isExpanded={isExpanded}
                onToggleExpand={() => onToggleExpand(message.message_id)}
                onReply={() => onReply(message.message_id)}
                onReplyAll={() => onReplyAll(message.message_id)}
                onForward={() => onForward(message.message_id)}
                onToggleStar={() => onToggleStar(message.message_id)}
              />
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
