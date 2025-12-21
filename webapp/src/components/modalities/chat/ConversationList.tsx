/**
 * Conversation list component for the Chat Viewer.
 * Displays a sidebar list of all conversations with preview info.
 */
import { useMemo } from 'react';
import { MessageCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import type { ChatMessage, ConversationMetadata, MessageContent } from './types';

interface ConversationListProps {
  conversations: Record<string, ConversationMetadata>;
  messages: ChatMessage[];
  selectedConversationId: string | null;
  onSelectConversation: (conversationId: string) => void;
}

/**
 * Format a timestamp to a relative time string.
 */
function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

/**
 * Get preview text from message content.
 */
function getContentPreview(content: MessageContent, maxLength = 40): string {
  if (typeof content === 'string') {
    return content.length > maxLength 
      ? content.substring(0, maxLength) + '...' 
      : content;
  }

  // Multimodal content - find first text block or describe media
  for (const block of content) {
    if (block.type === 'text') {
      const text = block.text;
      return text.length > maxLength 
        ? text.substring(0, maxLength) + '...' 
        : text;
    }
  }

  // No text blocks - describe the media types
  const mediaTypes = content.map(b => b.type).filter(t => t !== 'text');
  if (mediaTypes.length > 0) {
    return `[${mediaTypes.join(', ')}]`;
  }

  return '[Empty message]';
}

/**
 * Capitalize the first letter of a string.
 */
function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function ConversationList({
  conversations,
  messages,
  selectedConversationId,
  onSelectConversation,
}: ConversationListProps) {
  // Sort conversations by last message time (most recent first)
  const sortedConversations = useMemo(() => {
    return Object.values(conversations).sort((a, b) => {
      const aTime = new Date(a.last_message_at).getTime();
      const bTime = new Date(b.last_message_at).getTime();
      return bTime - aTime;
    });
  }, [conversations]);

  // Get the last message for each conversation
  const lastMessageByConversation = useMemo(() => {
    const map: Record<string, ChatMessage | undefined> = {};
    for (const conv of sortedConversations) {
      const convMessages = messages.filter(
        m => m.conversation_id === conv.conversation_id
      );
      if (convMessages.length > 0) {
        // Messages are already sorted by timestamp
        map[conv.conversation_id] = convMessages[convMessages.length - 1];
      }
    }
    return map;
  }, [sortedConversations, messages]);

  if (sortedConversations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-4">
        <MessageCircle className="h-8 w-8 mb-2 opacity-50" />
        <p className="text-sm text-center">No conversations yet</p>
        <p className="text-xs text-center mt-1">Start a new chat to begin</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-2 space-y-1">
        <div className="px-2 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Conversations
        </div>
        {sortedConversations.map((conversation) => {
          const lastMessage = lastMessageByConversation[conversation.conversation_id];
          const isSelected = selectedConversationId === conversation.conversation_id;

          return (
            <button
              key={conversation.conversation_id}
              onClick={() => onSelectConversation(conversation.conversation_id)}
              className={cn(
                'w-full text-left p-3 rounded-lg transition-colors',
                'hover:bg-accent',
                isSelected && 'bg-accent'
              )}
            >
              <div className="flex items-start gap-2">
                {isSelected && (
                  <div className="w-2 h-2 mt-1.5 rounded-full bg-primary flex-shrink-0" />
                )}
                <div className={cn('flex-1 min-w-0', !isSelected && 'ml-4')}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-sm truncate">
                      {conversation.conversation_id}
                    </span>
                    <Badge variant="secondary" className="text-xs flex-shrink-0">
                      {conversation.message_count}
                    </Badge>
                  </div>
                  {lastMessage && (
                    <>
                      <div className="flex items-center gap-1 mt-1">
                        <span className="text-xs text-muted-foreground">
                          {capitalize(lastMessage.role)}
                        </span>
                        <span className="text-xs text-muted-foreground">•</span>
                        <span className="text-xs text-muted-foreground">
                          {formatRelativeTime(lastMessage.timestamp)}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground truncate mt-0.5">
                        "{getContentPreview(lastMessage.content)}"
                      </p>
                    </>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </ScrollArea>
  );
}
