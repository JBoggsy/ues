/**
 * Message thread component for the Chat Viewer.
 * Displays messages in a chat-bubble style interface with multimodal support.
 */
import { useMemo, useRef, useEffect } from 'react';
import { User, Bot, FileIcon, ImageIcon, Music, Video } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { ChatMessage, MessageContent, ContentBlock } from './types';

interface MessageThreadProps {
  conversationId: string | null;
  messages: ChatMessage[];
}

/**
 * Format a timestamp to a time string.
 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * Format a timestamp to a date string.
 */
function formatDate(timestamp: string): string {
  const date = new Date(timestamp);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.toDateString() === today.toDateString()) {
    return 'Today';
  }
  if (date.toDateString() === yesterday.toDateString()) {
    return 'Yesterday';
  }
  return date.toLocaleDateString([], { 
    weekday: 'short', 
    month: 'short', 
    day: 'numeric' 
  });
}

/**
 * Render a single content block (text, image, audio, video, file).
 */
function ContentBlockRenderer({ block }: { block: ContentBlock }) {
  if (block.type === 'text') {
    return (
      <p className="whitespace-pre-wrap break-words">{block.text}</p>
    );
  }

  if (block.type === 'image') {
    const src = block.source === 'url' ? block.url : `data:${block.media_type || 'image/png'};base64,${block.data}`;
    if (src) {
      return (
        <div className="mt-2">
          <img 
            src={src} 
            alt={block.alt || 'Image'} 
            className="max-w-xs rounded-lg border"
          />
        </div>
      );
    }
    // Fallback placeholder
    return (
      <div className="mt-2 flex items-center gap-2 p-3 bg-muted/50 rounded-lg border">
        <ImageIcon className="h-5 w-5 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          {block.alt || 'Image attachment'}
        </span>
      </div>
    );
  }

  if (block.type === 'audio') {
    const src = block.source === 'url' ? block.url : undefined;
    if (src) {
      return (
        <div className="mt-2">
          <audio controls className="max-w-xs">
            <source src={src} type={block.media_type || 'audio/mpeg'} />
            Your browser does not support audio playback.
          </audio>
        </div>
      );
    }
    // Fallback placeholder
    return (
      <div className="mt-2 flex items-center gap-2 p-3 bg-muted/50 rounded-lg border">
        <Music className="h-5 w-5 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Audio attachment</span>
      </div>
    );
  }

  if (block.type === 'video') {
    const src = block.source === 'url' ? block.url : undefined;
    if (src) {
      return (
        <div className="mt-2">
          <video controls className="max-w-xs rounded-lg border">
            <source src={src} type={block.media_type || 'video/mp4'} />
            Your browser does not support video playback.
          </video>
        </div>
      );
    }
    // Fallback placeholder
    return (
      <div className="mt-2 flex items-center gap-2 p-3 bg-muted/50 rounded-lg border">
        <Video className="h-5 w-5 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Video attachment</span>
      </div>
    );
  }

  if (block.type === 'file') {
    return (
      <div className="mt-2 flex items-center gap-2 p-3 bg-muted/50 rounded-lg border">
        <FileIcon className="h-5 w-5 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          {block.filename || 'File attachment'}
        </span>
      </div>
    );
  }

  // Unknown block type placeholder
  return (
    <div className="mt-2 flex items-center gap-2 p-3 bg-muted/50 rounded-lg border">
      <FileIcon className="h-5 w-5 text-muted-foreground" />
      <span className="text-sm text-muted-foreground">
        Unknown content type
      </span>
    </div>
  );
}

/**
 * Render message content (string or multimodal blocks).
 */
function MessageContentRenderer({ content }: { content: MessageContent }) {
  if (typeof content === 'string') {
    return <p className="whitespace-pre-wrap break-words">{content}</p>;
  }

  return (
    <div className="space-y-1">
      {content.map((block, index) => (
        <ContentBlockRenderer key={index} block={block} />
      ))}
    </div>
  );
}

/**
 * Single message bubble component.
 */
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-3 max-w-[85%]',
        isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
      )}
    >
      {/* Message content */}
      <div className="flex flex-col gap-1">
        <div
          className={cn(
            'px-4 py-3 rounded-2xl',
            isUser
              ? 'bg-primary text-primary-foreground rounded-br-md'
              : 'bg-muted rounded-bl-md'
          )}
        >
          <MessageContentRenderer content={message.content} />
        </div>
        {/* Timestamp and role indicator */}
        <div
          className={cn(
            'flex items-center gap-1.5 text-xs text-muted-foreground',
            isUser ? 'flex-row-reverse' : ''
          )}
        >
          {isUser ? (
            <User className="h-3 w-3" />
          ) : (
            <Bot className="h-3 w-3" />
          )}
          <span>{message.role}</span>
          <span>•</span>
          <span>{formatTime(message.timestamp)}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Date separator between message groups.
 */
function DateSeparator({ date }: { date: string }) {
  return (
    <div className="flex items-center gap-4 my-4">
      <div className="flex-1 h-px bg-border" />
      <span className="text-xs text-muted-foreground px-2">{date}</span>
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}

export function MessageThread({ conversationId, messages }: MessageThreadProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Filter messages for the selected conversation
  const conversationMessages = useMemo(() => {
    if (!conversationId) return [];
    return messages.filter(m => m.conversation_id === conversationId);
  }, [conversationId, messages]);

  // Group messages by date for separators
  const messagesWithDates = useMemo(() => {
    const result: Array<{ type: 'date'; date: string } | { type: 'message'; message: ChatMessage }> = [];
    let currentDate = '';

    for (const message of conversationMessages) {
      const messageDate = formatDate(message.timestamp);
      if (messageDate !== currentDate) {
        result.push({ type: 'date', date: messageDate });
        currentDate = messageDate;
      }
      result.push({ type: 'message', message });
    }

    return result;
  }, [conversationMessages]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversationMessages.length]);

  if (!conversationId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
        <Bot className="h-12 w-12 mb-3 opacity-50" />
        <p className="text-lg font-medium">No conversation selected</p>
        <p className="text-sm">Select a conversation or start a new one</p>
      </div>
    );
  }

  if (conversationMessages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
        <Bot className="h-12 w-12 mb-3 opacity-50" />
        <p className="text-lg font-medium">Start the conversation</p>
        <p className="text-sm">Send a message to begin</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full" ref={scrollRef}>
      <div className="p-4 space-y-4">
        {messagesWithDates.map((item, index) => {
          if (item.type === 'date') {
            return <DateSeparator key={`date-${index}`} date={item.date} />;
          }
          return (
            <MessageBubble key={item.message.message_id} message={item.message} />
          );
        })}
      </div>
    </ScrollArea>
  );
}
