/**
 * Toolbar component for SMS viewer.
 * Provides action buttons for conversation management.
 */
import {
  MessageSquarePlus,
  Trash2,
  Archive,
  Pin,
  PinOff,
  BellOff,
  Bell,
  RefreshCw,
  ArchiveRestore,
  MailCheck,
  MailX,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { SMSConversation } from './types';

interface SMSToolbarProps {
  selectedConversation: SMSConversation | null;
  onNewMessage: () => void;
  onDelete: () => void;
  onArchive: () => void;
  onUnarchive: () => void;
  onPin: () => void;
  onUnpin: () => void;
  onMute: () => void;
  onUnmute: () => void;
  onMarkRead: () => void;
  onMarkUnread: () => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

export function SMSToolbar({
  selectedConversation,
  onNewMessage,
  onDelete,
  onArchive,
  onUnarchive,
  onPin,
  onUnpin,
  onMute,
  onUnmute,
  onMarkRead,
  onMarkUnread,
  onRefresh,
  isRefreshing,
}: SMSToolbarProps) {
  const hasSelection = !!selectedConversation;
  const isPinned = selectedConversation?.is_pinned ?? false;
  const isMuted = selectedConversation?.is_muted ?? false;
  const isArchived = selectedConversation?.is_archived ?? false;
  const hasUnread = (selectedConversation?.unread_count ?? 0) > 0;

  return (
    <div className="flex items-center gap-1 px-2 py-1.5 border-b bg-background">
      {/* New Message Button */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="sm" onClick={onNewMessage}>
              <MessageSquarePlus className="h-4 w-4 mr-2" />
              New Message
            </Button>
          </TooltipTrigger>
          <TooltipContent>Start a new conversation</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <Separator orientation="vertical" className="h-6 mx-1" />

      {/* Conversation actions - only enabled with selection */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onDelete}
              disabled={!hasSelection}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Delete conversation</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={isArchived ? onUnarchive : onArchive}
              disabled={!hasSelection}
            >
              {isArchived ? (
                <ArchiveRestore className="h-4 w-4" />
              ) : (
                <Archive className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isArchived ? 'Unarchive' : 'Archive'}</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={isPinned ? onUnpin : onPin}
              disabled={!hasSelection}
            >
              {isPinned ? (
                <PinOff className="h-4 w-4" />
              ) : (
                <Pin className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isPinned ? 'Unpin' : 'Pin to top'}</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={isMuted ? onUnmute : onMute}
              disabled={!hasSelection}
            >
              {isMuted ? (
                <Bell className="h-4 w-4" />
              ) : (
                <BellOff className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{isMuted ? 'Unmute' : 'Mute notifications'}</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={hasUnread ? onMarkRead : onMarkUnread}
              disabled={!hasSelection}
            >
              {hasUnread ? (
                <MailCheck className="h-4 w-4" />
              ) : (
                <MailX className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>{hasUnread ? 'Mark as read' : 'Mark as unread'}</TooltipContent>
        </Tooltip>
      </TooltipProvider>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Refresh */}
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Refresh</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}
