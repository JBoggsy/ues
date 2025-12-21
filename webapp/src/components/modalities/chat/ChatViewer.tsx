/**
 * Main Chat viewer component.
 * Integrates conversation list, message thread, toolbar, and dialogs.
 */
import { useState, useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import apiClient from '@/api/client';
import { useModalityState } from '@/api';
import { ConversationList } from './ConversationList';
import { MessageThread } from './MessageThread';
import { ChatToolbar } from './ChatToolbar';
import { ChatStatusBar } from './ChatStatusBar';
import { ComposeArea } from './ComposeArea';
import { NewConversationDialog } from './NewConversationDialog';
import type { ChatState, MessageRole } from './types';

/**
 * Map of chat operations to their API endpoints.
 */
const CHAT_API_ENDPOINTS: Record<string, string> = {
  send: '/chat/send',
  delete: '/chat/delete',
  clear: '/chat/clear',
};

/**
 * Submit a chat action to the API.
 */
async function submitChatAction(
  endpoint: string,
  data: Record<string, unknown>
): Promise<void> {
  await apiClient.post(endpoint, data);
}

export function ChatViewer() {
  const queryClient = useQueryClient();

  // Fetch chat state with polling
  const {
    data: chatState,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useModalityState<ChatState>('chat', 3000);

  // UI State
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  // Dialog state
  const [newConversationOpen, setNewConversationOpen] = useState(false);

  // Get list of existing conversation IDs for the new conversation dialog
  const existingConversationIds = useMemo(() => {
    if (!chatState) return [];
    return Object.keys(chatState.conversations);
  }, [chatState]);

  // Invalidate queries after mutations
  const invalidateChatState = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['environment', 'modalities', 'chat'] });
  }, [queryClient]);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Conversation selection
  const handleConversationSelect = useCallback((conversationId: string) => {
    setSelectedConversationId(conversationId);
  }, []);

  // Send message in current conversation
  const handleSendMessage = useCallback(async (role: MessageRole, content: string) => {
    if (!selectedConversationId) return;

    setIsSending(true);
    try {
      await submitChatAction(CHAT_API_ENDPOINTS.send, {
        role,
        content,
        conversation_id: selectedConversationId,
      });

      toast.success('Message sent');
      invalidateChatState();
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
    } finally {
      setIsSending(false);
    }
  }, [selectedConversationId, invalidateChatState]);

  // Create a new conversation (creates it by sending the first message)
  const handleCreateConversation = useCallback((conversationId: string) => {
    // Just select the new conversation ID - it will be created when first message is sent
    setSelectedConversationId(conversationId);
    toast.info(`Conversation "${conversationId}" ready. Send a message to start.`);
  }, []);

  // Clear conversation
  const handleClearConversation = useCallback(async () => {
    if (!selectedConversationId) return;

    try {
      await submitChatAction(CHAT_API_ENDPOINTS.clear, {
        conversation_id: selectedConversationId,
      });

      toast.success('Conversation cleared');
      invalidateChatState();
    } catch (error) {
      console.error('Failed to clear conversation:', error);
      toast.error('Failed to clear conversation');
    }
  }, [selectedConversationId, invalidateChatState]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">Loading chat...</div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-destructive mb-2">Failed to load chat</p>
          <button
            onClick={() => refetch()}
            className="text-sm text-primary hover:underline"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] border rounded-lg overflow-hidden">
      {/* Toolbar */}
      <ChatToolbar
        selectedConversationId={selectedConversationId}
        onRefresh={handleRefresh}
        onNewConversation={() => setNewConversationOpen(true)}
        onClearConversation={handleClearConversation}
        isRefreshing={isRefetching}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 min-h-0">
        {/* Conversation List (Left Panel) */}
        <div className="w-72 border-r flex flex-col flex-shrink-0">
          <div className="flex-1 min-h-0">
            <ConversationList
              conversations={chatState?.conversations || {}}
              messages={chatState?.messages || []}
              selectedConversationId={selectedConversationId}
              onSelectConversation={handleConversationSelect}
            />
          </div>
          <ChatStatusBar
            conversationCount={chatState?.conversation_count || 0}
            messageCount={chatState?.total_message_count || 0}
          />
        </div>

        {/* Message Thread (Right Panel) */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 min-h-0">
            <MessageThread
              conversationId={selectedConversationId}
              messages={chatState?.messages || []}
            />
          </div>
          <ComposeArea
            conversationId={selectedConversationId}
            onSendMessage={handleSendMessage}
            isSending={isSending}
          />
        </div>
      </div>

      {/* New Conversation Dialog */}
      <NewConversationDialog
        open={newConversationOpen}
        onOpenChange={setNewConversationOpen}
        onCreateConversation={handleCreateConversation}
        existingConversationIds={existingConversationIds}
      />
    </div>
  );
}
