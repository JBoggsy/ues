/**
 * Main SMS viewer component.
 * Integrates conversation list, message thread, toolbar, and dialogs.
 */
import { useState, useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import apiClient from '@/api/client';
import { useModalityState } from '@/api';
import { useContactsLookup } from '../contacts/useContactsLookup';
import { ConversationList } from './ConversationList';
import { MessageThread } from './MessageThread';
import { SMSToolbar } from './SMSToolbar';
import { SMSStatusBar } from './SMSStatusBar';
import { NewConversationDialog } from './NewConversationDialog';
import type { SMSState, ConversationFilter } from './types';

/**
 * Map of SMS operations to their API endpoints.
 */
const SMS_API_ENDPOINTS: Record<string, string> = {
  send: '/sms/send',
  receive: '/sms/receive',
  delete: '/sms/delete',
  read: '/sms/read',
  unread: '/sms/unread',
  react: '/sms/react',
  conversation: '/sms/conversation',
};

/**
 * Submit an SMS action to the API.
 */
async function submitSMSAction(
  endpoint: string,
  data: Record<string, unknown>
): Promise<void> {
  await apiClient.post(endpoint, data);
}

export function SMSViewer() {
  const queryClient = useQueryClient();

  // Fetch SMS state with polling
  const {
    data: smsState,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useModalityState<SMSState>('sms', 3000);

  // Fetch contacts for phone number → display name resolution
  const { resolvePhone } = useContactsLookup();

  // UI State
  const [filter, setFilter] = useState<ConversationFilter>('all');
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  // Dialog state
  const [newConversationOpen, setNewConversationOpen] = useState(false);

  // Get selected conversation
  const selectedConversation = useMemo(() => {
    if (!smsState || !selectedThreadId) return null;
    return smsState.conversations[selectedThreadId] || null;
  }, [smsState, selectedThreadId]);

  // Invalidate queries after mutations
  const invalidateSMSState = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['environment', 'modalities', 'sms'] });
  }, [queryClient]);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Conversation selection
  const handleConversationSelect = useCallback((threadId: string) => {
    setSelectedThreadId(threadId);
  }, []);

  // Send message in current conversation
  const handleSendMessage = useCallback(async (body: string) => {
    if (!smsState || !selectedThreadId || !selectedConversation) return;

    setIsSending(true);
    try {
      // Get recipient numbers (all participants except user)
      const toNumbers = selectedConversation.participants
        .filter(p => p.phone_number !== smsState.user_phone_number && !p.left_at)
        .map(p => p.phone_number);

      if (toNumbers.length === 0) {
        toast.error('No recipients in this conversation');
        return;
      }

      await submitSMSAction(SMS_API_ENDPOINTS.send, {
        from_number: smsState.user_phone_number,
        to_numbers: toNumbers,
        body,
        message_type: 'sms',
      });

      toast.success('Message sent');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
    } finally {
      setIsSending(false);
    }
  }, [smsState, selectedThreadId, selectedConversation, invalidateSMSState]);

  // New conversation send handler
  const handleNewConversationSend = useCallback(async (
    toNumbers: string[],
    body: string
  ) => {
    if (!smsState) return;

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.send, {
        from_number: smsState.user_phone_number,
        to_numbers: toNumbers,
        body,
        message_type: 'sms',
      });

      toast.success('Message sent');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error('Failed to send message');
      throw error;
    }
  }, [smsState, invalidateSMSState]);

  // Delete conversation (delete all messages)
  const handleDelete = useCallback(async () => {
    if (!smsState || !selectedThreadId) return;

    // Get all message IDs in this conversation
    const messageIds = Object.values(smsState.messages)
      .filter(m => m.thread_id === selectedThreadId)
      .map(m => m.message_id);

    if (messageIds.length === 0) {
      toast.info('No messages to delete');
      return;
    }

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.delete, {
        message_ids: messageIds,
      });

      toast.success('Conversation deleted');
      setSelectedThreadId(null);
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      toast.error('Failed to delete conversation');
    }
  }, [smsState, selectedThreadId, invalidateSMSState]);

  // Archive conversation
  const handleArchive = useCallback(async () => {
    if (!selectedThreadId) return;

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.conversation, {
        thread_id: selectedThreadId,
        archive: true,
      });
      toast.success('Conversation archived');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to archive conversation:', error);
      toast.error('Failed to archive conversation');
    }
  }, [selectedThreadId, invalidateSMSState]);

  // Unarchive conversation
  const handleUnarchive = useCallback(async () => {
    if (!selectedThreadId) return;

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.conversation, {
        thread_id: selectedThreadId,
        archive: false,
      });
      toast.success('Conversation unarchived');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to unarchive conversation:', error);
      toast.error('Failed to unarchive conversation');
    }
  }, [selectedThreadId, invalidateSMSState]);

  // Pin conversation
  const handlePin = useCallback(async () => {
    if (!selectedThreadId) return;

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.conversation, {
        thread_id: selectedThreadId,
        pin: true,
      });
      toast.success('Conversation pinned');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to pin conversation:', error);
      toast.error('Failed to pin conversation');
    }
  }, [selectedThreadId, invalidateSMSState]);

  // Unpin conversation
  const handleUnpin = useCallback(async () => {
    if (!selectedThreadId) return;

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.conversation, {
        thread_id: selectedThreadId,
        pin: false,
      });
      toast.success('Conversation unpinned');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to unpin conversation:', error);
      toast.error('Failed to unpin conversation');
    }
  }, [selectedThreadId, invalidateSMSState]);

  // Mute conversation
  const handleMute = useCallback(async () => {
    if (!selectedThreadId) return;

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.conversation, {
        thread_id: selectedThreadId,
        mute: true,
      });
      toast.success('Conversation muted');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to mute conversation:', error);
      toast.error('Failed to mute conversation');
    }
  }, [selectedThreadId, invalidateSMSState]);

  // Unmute conversation
  const handleUnmute = useCallback(async () => {
    if (!selectedThreadId) return;

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.conversation, {
        thread_id: selectedThreadId,
        mute: false,
      });
      toast.success('Conversation unmuted');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to unmute conversation:', error);
      toast.error('Failed to unmute conversation');
    }
  }, [selectedThreadId, invalidateSMSState]);

  // Mark conversation as read
  const handleMarkRead = useCallback(async () => {
    if (!selectedThreadId) return;

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.conversation, {
        thread_id: selectedThreadId,
        mark_all_read: true,
      });
      toast.success('Conversation marked as read');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to mark conversation as read:', error);
      toast.error('Failed to mark conversation as read');
    }
  }, [selectedThreadId, invalidateSMSState]);

  // Mark conversation as unread (marks the most recent message as unread)
  const handleMarkUnread = useCallback(async () => {
    if (!smsState || !selectedThreadId) return;

    // Get the most recent message in the conversation to mark as unread
    const conversationMessages = Object.values(smsState.messages)
      .filter(msg => msg.thread_id === selectedThreadId && !msg.is_deleted)
      .sort((a, b) => new Date(b.sent_at).getTime() - new Date(a.sent_at).getTime());

    if (conversationMessages.length === 0) {
      toast.info('No messages to mark as unread');
      return;
    }

    const latestMessage = conversationMessages[0];

    try {
      await submitSMSAction(SMS_API_ENDPOINTS.unread, {
        message_ids: [latestMessage.message_id],
      });
      toast.success('Conversation marked as unread');
      invalidateSMSState();
    } catch (error) {
      console.error('Failed to mark conversation as unread:', error);
      toast.error('Failed to mark conversation as unread');
    }
  }, [smsState, selectedThreadId, invalidateSMSState]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">Loading messages...</div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-destructive mb-2">Failed to load messages</p>
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
      <SMSToolbar
        selectedConversation={selectedConversation}
        onNewMessage={() => setNewConversationOpen(true)}
        onDelete={handleDelete}
        onArchive={handleArchive}
        onUnarchive={handleUnarchive}
        onPin={handlePin}
        onUnpin={handleUnpin}
        onMute={handleMute}
        onUnmute={handleUnmute}
        onMarkRead={handleMarkRead}
        onMarkUnread={handleMarkUnread}
        onRefresh={handleRefresh}
        isRefreshing={isRefetching}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 min-h-0">
        {/* Conversation List */}
        <ConversationList
          smsState={smsState || null}
          selectedThreadId={selectedThreadId}
          filter={filter}
          onFilterChange={setFilter}
          onConversationSelect={handleConversationSelect}
          contactNameResolver={resolvePhone}
        />

        {/* Message Thread */}
        <MessageThread
          smsState={smsState || null}
          selectedThreadId={selectedThreadId}
          onSendMessage={handleSendMessage}
          isSending={isSending}
          contactNameResolver={resolvePhone}
        />
      </div>

      {/* Status Bar */}
      <SMSStatusBar smsState={smsState || null} />

      {/* New Conversation Dialog */}
      <NewConversationDialog
        open={newConversationOpen}
        onOpenChange={setNewConversationOpen}
        onSend={handleNewConversationSend}
        userPhoneNumber={smsState?.user_phone_number || '+1-555-0000'}
      />
    </div>
  );
}
