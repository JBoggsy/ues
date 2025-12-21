/**
 * Toolbar component for the Chat Viewer.
 * Displays conversation title and action buttons.
 */
import { RefreshCw, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface ChatToolbarProps {
  selectedConversationId: string | null;
  onRefresh: () => void;
  onNewConversation: () => void;
  onClearConversation: () => void;
  isRefreshing: boolean;
}

export function ChatToolbar({
  selectedConversationId,
  onRefresh,
  onNewConversation,
  onClearConversation,
  isRefreshing,
}: ChatToolbarProps) {
  return (
    <div className="flex items-center justify-between border-b px-4 py-2 bg-background">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold">
          {selectedConversationId 
            ? `Conversation: ${selectedConversationId}` 
            : 'Chat'}
        </h2>
      </div>

      <div className="flex items-center gap-1">
        {/* Clear conversation button */}
        {selectedConversationId && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClearConversation}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">Clear conversation</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Clear conversation</TooltipContent>
          </Tooltip>
        )}

        {/* Refresh button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw 
                className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} 
              />
              <span className="sr-only">Refresh</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>Refresh</TooltipContent>
        </Tooltip>

        {/* New conversation button */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="default"
              size="sm"
              onClick={onNewConversation}
              className="gap-1"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </TooltipTrigger>
          <TooltipContent>Start a new conversation</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}
