/**
 * Email list component with Gmail-style thread grouping.
 * Displays emails/threads for the selected folder with selection support.
 */
import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Star,
  Paperclip,
  ChevronRight,
} from 'lucide-react';
import type { EmailState, EmailMessage, ThreadDisplayItem } from './types';

interface EmailListProps {
  emailState: EmailState | null;
  selectedFolder: string;
  selectedLabel: string | null;
  selectedThreadId: string | null;
  selectedMessageIds: Set<string>;
  onThreadSelect: (threadId: string, messageId: string) => void;
  onMessageToggle: (messageId: string) => void;
  onSelectAll: (selected: boolean) => void;
}

/**
 * Format timestamp for display.
 */
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) {
    return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  } else if (diffDays === 1) {
    return 'Yesterday';
  } else if (diffDays < 7) {
    return date.toLocaleDateString([], { weekday: 'short' });
  } else {
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }
}

/**
 * Extract display name from email address.
 */
function getDisplayName(email: string): string {
  const match = email.match(/^(.+?)\s*<.+>$/);
  if (match) return match[1];
  return email.split('@')[0];
}

/**
 * Get thread display items for the current folder/label.
 */
function getThreadDisplayItems(
  emailState: EmailState | null,
  selectedFolder: string,
  selectedLabel: string | null
): ThreadDisplayItem[] {
  if (!emailState) return [];

  // Get message IDs for the current view
  let messageIds: string[];
  if (selectedLabel) {
    messageIds = emailState.labels[selectedLabel] || [];
  } else {
    messageIds = emailState.folders[selectedFolder] || [];
  }

  // Group messages by thread
  const threadMap = new Map<string, EmailMessage[]>();
  
  for (const msgId of messageIds) {
    const email = emailState.emails[msgId];
    if (!email) continue;
    
    const threadId = email.thread_id;
    if (!threadMap.has(threadId)) {
      threadMap.set(threadId, []);
    }
    threadMap.get(threadId)!.push(email);
  }

  // Convert to display items
  const items: ThreadDisplayItem[] = [];
  
  for (const [threadId, messages] of threadMap) {
    // Sort messages by received_at descending
    messages.sort(
      (a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime()
    );

    const lastMessage = messages[0];
    const allParticipants = new Set<string>();
    let hasAttachments = false;
    let isStarred = false;
    let unreadCount = 0;

    for (const msg of messages) {
      allParticipants.add(msg.from_address);
      msg.to_addresses.forEach((addr) => allParticipants.add(addr));
      if (msg.attachments.length > 0) hasAttachments = true;
      if (msg.is_starred) isStarred = true;
      if (!msg.is_read) unreadCount++;
    }

    items.push({
      thread_id: threadId,
      subject: lastMessage.subject || '(No Subject)',
      participants: Array.from(allParticipants),
      lastMessage,
      messageCount: messages.length,
      unreadCount,
      isStarred,
      hasAttachments,
      folder: selectedFolder,
    });
  }

  // Sort by last message time descending
  items.sort(
    (a, b) =>
      new Date(b.lastMessage.received_at).getTime() -
      new Date(a.lastMessage.received_at).getTime()
  );

  return items;
}

export function EmailList({
  emailState,
  selectedFolder,
  selectedLabel,
  selectedThreadId,
  selectedMessageIds,
  onThreadSelect,
  onMessageToggle,
  onSelectAll,
}: EmailListProps) {
  const threadItems = useMemo(
    () => getThreadDisplayItems(emailState, selectedFolder, selectedLabel),
    [emailState, selectedFolder, selectedLabel]
  );

  const allSelected = threadItems.length > 0 && 
    threadItems.every(item => selectedMessageIds.has(item.lastMessage.message_id));

  if (!emailState) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        Loading emails...
      </div>
    );
  }

  if (threadItems.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground">
        <div className="text-center">
          <p className="text-lg">No emails</p>
          <p className="text-sm">
            {selectedLabel
              ? `No emails with label "${selectedLabel}"`
              : `Your ${selectedFolder} is empty`}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Select All Header */}
      <div className="flex items-center gap-3 px-4 py-2 border-b bg-muted/30">
        <Checkbox
          checked={allSelected}
          onCheckedChange={(checked) => onSelectAll(!!checked)}
          aria-label="Select all emails"
        />
        <span className="text-xs text-muted-foreground">
          {threadItems.length} {threadItems.length === 1 ? 'conversation' : 'conversations'}
        </span>
      </div>

      {/* Email List */}
      <ScrollArea className="flex-1">
        <div className="divide-y">
          {threadItems.map((item) => {
            const isSelected = selectedThreadId === item.thread_id;
            const isChecked = selectedMessageIds.has(item.lastMessage.message_id);
            const isUnread = item.unreadCount > 0;

            // Get sender display - for sent folder, show recipients
            const senderDisplay =
              selectedFolder === 'sent'
                ? `To: ${item.lastMessage.to_addresses.map(getDisplayName).join(', ')}`
                : getDisplayName(item.lastMessage.from_address);

            return (
              <div
                key={item.thread_id}
                className={cn(
                  'flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors',
                  isSelected
                    ? 'bg-primary/10 border-l-2 border-l-primary'
                    : 'hover:bg-muted/50',
                  isUnread && 'bg-blue-50/50 dark:bg-blue-950/20'
                )}
                onClick={() => onThreadSelect(item.thread_id, item.lastMessage.message_id)}
              >
                {/* Checkbox */}
                <div
                  className="pt-1"
                  onClick={(e) => {
                    e.stopPropagation();
                  }}
                >
                  <Checkbox
                    checked={isChecked}
                    onCheckedChange={() => onMessageToggle(item.lastMessage.message_id)}
                    onClick={(e) => e.stopPropagation()}
                    aria-label={`Select ${item.subject}`}
                  />
                </div>

                {/* Star */}
                <button
                  className={cn(
                    'pt-1 transition-colors',
                    item.isStarred
                      ? 'text-yellow-500'
                      : 'text-muted-foreground/30 hover:text-muted-foreground'
                  )}
                  onClick={(e) => {
                    e.stopPropagation();
                    // TODO: Toggle star
                  }}
                  aria-label={item.isStarred ? 'Unstar' : 'Star'}
                >
                  <Star
                    className="h-4 w-4"
                    fill={item.isStarred ? 'currentColor' : 'none'}
                  />
                </button>

                {/* Email Content */}
                <div className="flex-1 min-w-0">
                  {/* Sender and Date Row */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={cn(
                          'truncate',
                          isUnread ? 'font-semibold' : 'font-normal'
                        )}
                      >
                        {senderDisplay}
                      </span>
                      {item.messageCount > 1 && (
                        <span className="text-xs text-muted-foreground shrink-0">
                          ({item.messageCount})
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {item.hasAttachments && (
                        <Paperclip className="h-3.5 w-3.5 text-muted-foreground" />
                      )}
                      <span className="text-xs text-muted-foreground">
                        {formatTimestamp(item.lastMessage.received_at)}
                      </span>
                    </div>
                  </div>

                  {/* Subject */}
                  <div
                    className={cn(
                      'truncate text-sm',
                      isUnread ? 'font-medium' : 'text-foreground'
                    )}
                  >
                    {item.subject}
                  </div>

                  {/* Preview */}
                  <div className="truncate text-sm text-muted-foreground">
                    {item.lastMessage.body_text.slice(0, 100)}
                  </div>

                  {/* Labels */}
                  {item.lastMessage.labels.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {item.lastMessage.labels.slice(0, 3).map((label) => (
                        <span
                          key={label}
                          className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                        >
                          {label}
                        </span>
                      ))}
                      {item.lastMessage.labels.length > 3 && (
                        <span className="text-xs text-muted-foreground">
                          +{item.lastMessage.labels.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Thread Indicator */}
                {item.messageCount > 1 && (
                  <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-1" />
                )}
              </div>
            );
          })}
        </div>
      </ScrollArea>
    </div>
  );
}
