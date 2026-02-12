/**
 * Conversation list component for SMS viewer.
 * Displays all conversations with filters and selection.
 */
import { useMemo } from 'react';
import { formatDistanceToNow, parseISO } from 'date-fns';
import { 
  MessageSquare, 
  Users, 
  Pin, 
  BellOff, 
  Archive
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { 
  SMSState, 
  SMSMessage,
  ConversationFilter,
  ConversationDisplayItem,
  ContactNameResolver,
} from './types';
import { resolveContactName } from './types';

interface ConversationListProps {
  smsState: SMSState | null;
  selectedThreadId: string | null;
  filter: ConversationFilter;
  onFilterChange: (filter: ConversationFilter) => void;
  onConversationSelect: (threadId: string) => void;
  /** Contacts-backed phone-number-to-name resolver. */
  contactNameResolver?: ContactNameResolver;
}

/**
 * Build display items for conversations with computed properties.
 */
function buildConversationDisplayItems(
  smsState: SMSState,
  contactNameResolver?: ContactNameResolver,
): ConversationDisplayItem[] {
  const items: ConversationDisplayItem[] = [];

  for (const conversation of Object.values(smsState.conversations)) {
    // Get messages for this conversation
    const conversationMessages = Object.values(smsState.messages)
      .filter(msg => msg.thread_id === conversation.thread_id && !msg.is_deleted)
      .sort((a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime());

    const lastMessage = conversationMessages[0];

    // Build display name
    let displayName: string;
    let displayNumber: string;

    if (conversation.conversation_type === 'group') {
      displayName = conversation.group_name || 'Group Chat';
      displayNumber = `${conversation.participants.filter(p => !p.left_at).length} participants`;
    } else {
      // One-on-one: find the other participant (not the user)
      const otherParticipant = conversation.participants.find(
        p => p.phone_number !== smsState.user_phone_number && !p.left_at
      );
      displayNumber = otherParticipant?.phone_number || 'Unknown';
      displayName = resolveContactName(displayNumber, contactNameResolver);
    }

    // Build message preview
    let lastMessagePreview = '';
    if (lastMessage) {
      const prefix = lastMessage.direction === 'outgoing' ? 'You: ' : '';
      lastMessagePreview = prefix + (lastMessage.body.length > 40 
        ? lastMessage.body.slice(0, 40) + '...' 
        : lastMessage.body);
    }

    // Format time
    let lastMessageTime = '';
    if (lastMessage) {
      try {
        lastMessageTime = formatDistanceToNow(parseISO(lastMessage.sent_at), { 
          addSuffix: false 
        });
      } catch {
        lastMessageTime = '';
      }
    }

    items.push({
      conversation,
      lastMessage,
      displayName,
      displayNumber,
      lastMessagePreview,
      lastMessageTime,
      isGroup: conversation.conversation_type === 'group',
      participantCount: conversation.participants.filter(p => !p.left_at).length,
    });
  }

  // Sort: pinned first, then by last message time
  return items.sort((a, b) => {
    if (a.conversation.is_pinned && !b.conversation.is_pinned) return -1;
    if (!a.conversation.is_pinned && b.conversation.is_pinned) return 1;
    
    const aTime = a.lastMessage?.sent_at || a.conversation.created_at;
    const bTime = b.lastMessage?.sent_at || b.conversation.created_at;
    return new Date(bTime).getTime() - new Date(aTime).getTime();
  });
}

/**
 * Filter conversations based on selected filter.
 */
function filterConversations(
  items: ConversationDisplayItem[],
  filter: ConversationFilter
): ConversationDisplayItem[] {
  switch (filter) {
    case 'unread':
      return items.filter(item => 
        item.conversation.unread_count > 0 && !item.conversation.is_archived
      );
    case 'groups':
      return items.filter(item => 
        item.isGroup && !item.conversation.is_archived
      );
    case 'archived':
      return items.filter(item => item.conversation.is_archived);
    case 'all':
    default:
      return items.filter(item => !item.conversation.is_archived);
  }
}

/**
 * Get delivery status indicator for outgoing messages.
 */
function DeliveryStatusIndicator({ message }: { message?: SMSMessage }) {
  if (!message || message.direction !== 'outgoing') return null;

  switch (message.delivery_status) {
    case 'read':
      return <span className="text-blue-500 text-xs">✓✓</span>;
    case 'delivered':
      return <span className="text-muted-foreground text-xs">✓✓</span>;
    case 'sent':
      return <span className="text-muted-foreground text-xs">✓</span>;
    case 'sending':
      return <span className="text-muted-foreground text-xs">○</span>;
    case 'failed':
      return <span className="text-destructive text-xs">!</span>;
    default:
      return null;
  }
}

/**
 * Single conversation list item.
 */
function ConversationItem({
  item,
  isSelected,
  onClick,
}: {
  item: ConversationDisplayItem;
  isSelected: boolean;
  onClick: () => void;
}) {
  const { conversation, lastMessage } = item;

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left p-3 border-b transition-colors',
        'hover:bg-muted/50',
        isSelected && 'bg-muted',
        conversation.is_muted && 'opacity-60'
      )}
    >
      <div className="flex items-start gap-2">
        {/* Icon */}
        <div className="flex-shrink-0 mt-0.5">
          {item.isGroup ? (
            <Users className="h-5 w-5 text-muted-foreground" />
          ) : (
            <MessageSquare className="h-5 w-5 text-muted-foreground" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Header row */}
          <div className="flex items-center gap-1">
            {conversation.is_pinned && (
              <Pin className="h-3 w-3 text-muted-foreground flex-shrink-0" />
            )}
            {conversation.is_muted && (
              <BellOff className="h-3 w-3 text-muted-foreground flex-shrink-0" />
            )}
            {conversation.is_archived && (
              <Archive className="h-3 w-3 text-muted-foreground flex-shrink-0" />
            )}
            <span className={cn(
              'font-medium truncate',
              conversation.unread_count > 0 && 'font-semibold'
            )}>
              {item.displayName}
            </span>
          </div>

          {/* Phone number or participant count */}
          <div className="text-xs text-muted-foreground truncate">
            {item.displayNumber}
          </div>

          {/* Last message preview */}
          {item.lastMessagePreview && (
            <div className="flex items-center gap-1 mt-0.5">
              <span className={cn(
                'text-sm truncate',
                conversation.unread_count > 0 
                  ? 'text-foreground' 
                  : 'text-muted-foreground'
              )}>
                {item.lastMessagePreview}
              </span>
            </div>
          )}
        </div>

        {/* Right side - time and unread */}
        <div className="flex-shrink-0 text-right">
          {item.lastMessageTime && (
            <div className="text-xs text-muted-foreground">
              {item.lastMessageTime}
            </div>
          )}
          <div className="flex items-center gap-1 justify-end mt-1">
            <DeliveryStatusIndicator message={lastMessage} />
            {conversation.unread_count > 0 && (
              <Badge 
                variant="default" 
                className="h-5 min-w-[20px] px-1.5 text-xs"
              >
                {conversation.unread_count}
              </Badge>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}

export function ConversationList({
  smsState,
  selectedThreadId,
  filter,
  onFilterChange,
  onConversationSelect,
  contactNameResolver,
}: ConversationListProps) {
  // Build and filter conversation items
  const filteredItems = useMemo(() => {
    if (!smsState) return [];
    const allItems = buildConversationDisplayItems(smsState, contactNameResolver);
    return filterConversations(allItems, filter);
  }, [smsState, filter, contactNameResolver]);

  // Count unread for filter badge
  const unreadCount = useMemo(() => {
    if (!smsState) return 0;
    return Object.values(smsState.conversations)
      .filter(c => !c.is_archived)
      .reduce((sum, c) => sum + c.unread_count, 0);
  }, [smsState]);

  if (!smsState) {
    return (
      <div className="w-72 border-r bg-background flex items-center justify-center">
        <span className="text-muted-foreground">Loading...</span>
      </div>
    );
  }

  return (
    <div className="w-72 border-r bg-background flex flex-col">
      {/* Filter selector */}
      <div className="p-2 border-b">
        <Select value={filter} onValueChange={(v) => onFilterChange(v as ConversationFilter)}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Filter conversations" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Conversations</SelectItem>
            <SelectItem value="unread">
              Unread Only {unreadCount > 0 && `(${unreadCount})`}
            </SelectItem>
            <SelectItem value="groups">Groups Only</SelectItem>
            <SelectItem value="archived">Archived</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Conversation list */}
      <ScrollArea className="flex-1">
        {filteredItems.length === 0 ? (
          <div className="p-4 text-center text-muted-foreground text-sm">
            {filter === 'all' && 'No conversations yet'}
            {filter === 'unread' && 'No unread messages'}
            {filter === 'groups' && 'No group conversations'}
            {filter === 'archived' && 'No archived conversations'}
          </div>
        ) : (
          filteredItems.map((item) => (
            <ConversationItem
              key={item.conversation.thread_id}
              item={item}
              isSelected={item.conversation.thread_id === selectedThreadId}
              onClick={() => onConversationSelect(item.conversation.thread_id)}
            />
          ))
        )}
      </ScrollArea>
    </div>
  );
}
