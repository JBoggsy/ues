/**
 * Main email viewer component.
 * Integrates folder panel, email list, preview, and toolbar.
 */
import { useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import apiClient from '@/api/client';
import { useModalityState } from '@/api';
import { useContactsLookup } from '../contacts/useContactsLookup';
import { FolderPanel } from './FolderPanel';
import { EmailList } from './EmailList';
import { EmailPreview } from './EmailPreview';
import { EmailToolbar } from './EmailToolbar';
import { EmailStatusBar } from './EmailStatusBar';
import { ComposeEmailDialog, type ComposeMode } from './ComposeEmailDialog';
import type { EmailState, EmailMessage, ComposeEmailData } from './types';

/**
 * Map of email operations to their API endpoints.
 */
const EMAIL_API_ENDPOINTS: Record<string, string> = {
  send: '/email/send',
  receive: '/email/receive',
  reply: '/email/send', // Replies use /send with in_reply_to
  reply_all: '/email/send', // Reply all uses /send with in_reply_to
  forward: '/email/send', // Forwards use /send
  delete: '/email/delete',
  archive: '/email/archive',
  star: '/email/star',
  unstar: '/email/unstar',
  mark_read: '/email/read',
  mark_unread: '/email/unread',
  move: '/email/move',
  add_label: '/email/label',
  remove_label: '/email/unlabel',
  mark_spam: '/email/move', // Move to spam folder
};

/**
 * Submit an email action to the API.
 */
async function submitEmailAction(
  operation: string,
  data: Record<string, unknown>
): Promise<void> {
  const endpoint = EMAIL_API_ENDPOINTS[operation];
  if (!endpoint) {
    throw new Error(`Unknown email operation: ${operation}`);
  }
  await apiClient.post(endpoint, data);
}

export function EmailViewer() {
  const queryClient = useQueryClient();
  
  // Fetch email state with polling
  const {
    data: emailState,
    isLoading,
    isError,
    refetch,
    isRefetching,
  } = useModalityState<EmailState>('email', 3000);

  // Fetch contacts for email address → display name resolution
  const { resolveEmail } = useContactsLookup();

  // UI State
  const [selectedFolder, setSelectedFolder] = useState('inbox');
  const [selectedLabel, setSelectedLabel] = useState<string | null>(null);
  const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);
  const [selectedMessageIds, setSelectedMessageIds] = useState<Set<string>>(new Set());
  const [expandedMessageIds, setExpandedMessageIds] = useState<Set<string>>(new Set());

  // Compose dialog state
  const [composeOpen, setComposeOpen] = useState(false);
  const [composeMode, setComposeMode] = useState<ComposeMode>('new');
  const [composeOriginalMessage, setComposeOriginalMessage] = useState<EmailMessage | null>(null);

  // Get selected email for toolbar state
  const selectedEmail = selectedMessageId && emailState
    ? emailState.emails[selectedMessageId]
    : null;

  // Refresh the email state
  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Invalidate queries after mutations
  const invalidateEmailState = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['environment', 'modalities', 'email'] });
  }, [queryClient]);

  // Thread selection
  const handleThreadSelect = useCallback((threadId: string, messageId: string) => {
    setSelectedThreadId(threadId);
    setSelectedMessageId(messageId);
    // Auto-expand the selected message
    setExpandedMessageIds(new Set([messageId]));
  }, []);

  // Message toggle for multi-select
  const handleMessageToggle = useCallback((messageId: string) => {
    setSelectedMessageIds((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  }, []);

  // Select all messages in current view
  const handleSelectAll = useCallback(
    (selected: boolean) => {
      if (!emailState) return;

      const messageIds = selectedLabel
        ? emailState.labels[selectedLabel] || []
        : emailState.folders[selectedFolder] || [];

      if (selected) {
        setSelectedMessageIds(new Set(messageIds));
      } else {
        setSelectedMessageIds(new Set());
      }
    },
    [emailState, selectedFolder, selectedLabel]
  );

  // Toggle message expansion in preview
  const handleToggleExpand = useCallback((messageId: string) => {
    setExpandedMessageIds((prev) => {
      const next = new Set(prev);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  }, []);

  // Compose actions
  const openCompose = useCallback((mode: ComposeMode, originalMessage?: EmailMessage | null) => {
    setComposeMode(mode);
    setComposeOriginalMessage(originalMessage || null);
    setComposeOpen(true);
  }, []);

  const handleCompose = useCallback(() => {
    openCompose('new');
  }, [openCompose]);

  const handleReply = useCallback((messageId?: string) => {
    const msgId = messageId || selectedMessageId;
    if (!msgId || !emailState) return;
    const message = emailState.emails[msgId];
    if (message) {
      openCompose('reply', message);
    }
  }, [selectedMessageId, emailState, openCompose]);

  const handleReplyAll = useCallback((messageId?: string) => {
    const msgId = messageId || selectedMessageId;
    if (!msgId || !emailState) return;
    const message = emailState.emails[msgId];
    if (message) {
      openCompose('reply_all', message);
    }
  }, [selectedMessageId, emailState, openCompose]);

  const handleForward = useCallback((messageId?: string) => {
    const msgId = messageId || selectedMessageId;
    if (!msgId || !emailState) return;
    const message = emailState.emails[msgId];
    if (message) {
      openCompose('forward', message);
    }
  }, [selectedMessageId, emailState, openCompose]);

  // Send composed email
  const handleSendEmail = useCallback(
    async (data: ComposeEmailData, mode: ComposeMode) => {
      try {
        const toAddresses = data.to.split(',').map((e) => e.trim()).filter(Boolean);
        const ccAddresses = data.cc ? data.cc.split(',').map((e) => e.trim()).filter(Boolean) : [];
        const bccAddresses = data.bcc ? data.bcc.split(',').map((e) => e.trim()).filter(Boolean) : [];

        let operation: string;
        const payload: Record<string, unknown> = {
          from_address: emailState?.user_email_address || 'user@example.com',
          to_addresses: toAddresses,
          cc_addresses: ccAddresses,
          bcc_addresses: bccAddresses,
          subject: data.subject,
          body_text: data.body,
        };

        switch (mode) {
          case 'reply':
            operation = 'reply';
            payload.in_reply_to = data.replyToMessageId;
            break;
          case 'reply_all':
            operation = 'reply_all';
            payload.in_reply_to = data.replyToMessageId;
            break;
          case 'forward':
            operation = 'forward';
            payload.in_reply_to = data.forwardMessageId;
            break;
          default:
            operation = 'send';
        }

        await submitEmailAction(operation, payload);
        toast.success('Email sent successfully');
        invalidateEmailState();
      } catch (error) {
        console.error('Failed to send email:', error);
        toast.error('Failed to send email');
        throw error;
      }
    },
    [emailState, invalidateEmailState]
  );

  // Email actions
  const handleDelete = useCallback(async () => {
    if (selectedMessageIds.size === 0) return;

    try {
      await submitEmailAction('delete', { message_ids: Array.from(selectedMessageIds) });
      toast.success(`Deleted ${selectedMessageIds.size} email(s)`);
      setSelectedMessageIds(new Set());
      setSelectedThreadId(null);
      setSelectedMessageId(null);
      invalidateEmailState();
    } catch (error) {
      console.error('Failed to delete:', error);
      toast.error('Failed to delete email(s)');
    }
  }, [selectedMessageIds, invalidateEmailState]);

  const handleArchive = useCallback(async () => {
    if (selectedMessageIds.size === 0) return;

    try {
      await submitEmailAction('archive', { message_ids: Array.from(selectedMessageIds) });
      toast.success(`Archived ${selectedMessageIds.size} email(s)`);
      setSelectedMessageIds(new Set());
      invalidateEmailState();
    } catch (error) {
      console.error('Failed to archive:', error);
      toast.error('Failed to archive email(s)');
    }
  }, [selectedMessageIds, invalidateEmailState]);

  const handleToggleStar = useCallback(async (messageId?: string) => {
    const targetIds = messageId ? [messageId] : Array.from(selectedMessageIds);
    if (targetIds.length === 0) return;

    try {
      // Group by star status to batch operations
      const toStar: string[] = [];
      const toUnstar: string[] = [];
      for (const id of targetIds) {
        const email = emailState?.emails[id];
        if (email?.is_starred) {
          toUnstar.push(id);
        } else {
          toStar.push(id);
        }
      }
      if (toStar.length > 0) {
        await submitEmailAction('star', { message_ids: toStar });
      }
      if (toUnstar.length > 0) {
        await submitEmailAction('unstar', { message_ids: toUnstar });
      }
      invalidateEmailState();
    } catch (error) {
      console.error('Failed to toggle star:', error);
      toast.error('Failed to update star status');
    }
  }, [selectedMessageIds, emailState, invalidateEmailState]);

  const handleToggleRead = useCallback(async () => {
    if (selectedMessageIds.size === 0) return;

    try {
      // Group by read status to batch operations
      const toMarkRead: string[] = [];
      const toMarkUnread: string[] = [];
      for (const messageId of selectedMessageIds) {
        const email = emailState?.emails[messageId];
        if (email?.is_read) {
          toMarkUnread.push(messageId);
        } else {
          toMarkRead.push(messageId);
        }
      }
      if (toMarkRead.length > 0) {
        await submitEmailAction('mark_read', { message_ids: toMarkRead });
      }
      if (toMarkUnread.length > 0) {
        await submitEmailAction('mark_unread', { message_ids: toMarkUnread });
      }
      invalidateEmailState();
    } catch (error) {
      console.error('Failed to toggle read status:', error);
      toast.error('Failed to update read status');
    }
  }, [selectedMessageIds, emailState, invalidateEmailState]);

  const handleMarkSpam = useCallback(async () => {
    if (selectedMessageIds.size === 0) return;

    try {
      // Move to spam folder
      await submitEmailAction('move', { 
        message_ids: Array.from(selectedMessageIds), 
        folder: 'spam' 
      });
      toast.success(`Marked ${selectedMessageIds.size} email(s) as spam`);
      setSelectedMessageIds(new Set());
      invalidateEmailState();
    } catch (error) {
      console.error('Failed to mark as spam:', error);
      toast.error('Failed to mark as spam');
    }
  }, [selectedMessageIds, invalidateEmailState]);

  const handleMoveToFolder = useCallback(async (folder: string) => {
    if (selectedMessageIds.size === 0) return;

    try {
      await submitEmailAction('move', { 
        message_ids: Array.from(selectedMessageIds), 
        folder 
      });
      toast.success(`Moved ${selectedMessageIds.size} email(s) to ${folder}`);
      setSelectedMessageIds(new Set());
      invalidateEmailState();
    } catch (error) {
      console.error('Failed to move:', error);
      toast.error('Failed to move email(s)');
    }
  }, [selectedMessageIds, invalidateEmailState]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">Loading emails...</div>
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-destructive mb-2">Failed to load emails</p>
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
      <EmailToolbar
        hasSelection={selectedMessageIds.size > 0}
        hasEmailSelected={!!selectedMessageId}
        isStarred={selectedEmail?.is_starred || false}
        isRead={selectedEmail?.is_read || false}
        onCompose={handleCompose}
        onReply={() => handleReply()}
        onReplyAll={() => handleReplyAll()}
        onForward={() => handleForward()}
        onDelete={handleDelete}
        onArchive={handleArchive}
        onToggleStar={() => handleToggleStar()}
        onToggleRead={handleToggleRead}
        onMarkSpam={handleMarkSpam}
        onMoveToFolder={handleMoveToFolder}
        onRefresh={handleRefresh}
        isRefreshing={isRefetching}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 min-h-0">
        {/* Folder Panel */}
        <FolderPanel
          emailState={emailState || null}
          selectedFolder={selectedFolder}
          onFolderSelect={setSelectedFolder}
          selectedLabel={selectedLabel}
          onLabelSelect={setSelectedLabel}
        />

        {/* Email List */}
        <EmailList
          emailState={emailState || null}
          selectedFolder={selectedFolder}
          selectedLabel={selectedLabel}
          selectedThreadId={selectedThreadId}
          selectedMessageIds={selectedMessageIds}
          onThreadSelect={handleThreadSelect}
          onMessageToggle={handleMessageToggle}
          onSelectAll={handleSelectAll}
          emailNameResolver={resolveEmail}
        />

        {/* Email Preview */}
        <EmailPreview
          emailState={emailState || null}
          selectedThreadId={selectedThreadId}
          selectedMessageId={selectedMessageId}
          expandedMessageIds={expandedMessageIds}
          onToggleExpand={handleToggleExpand}
          onReply={handleReply}
          onReplyAll={handleReplyAll}
          onForward={handleForward}
          onToggleStar={handleToggleStar}
          emailNameResolver={resolveEmail}
        />
      </div>

      {/* Status Bar */}
      <EmailStatusBar
        emailState={emailState || null}
        selectedFolder={selectedFolder}
      />

      {/* Compose Dialog */}
      <ComposeEmailDialog
        open={composeOpen}
        onOpenChange={setComposeOpen}
        mode={composeMode}
        originalMessage={composeOriginalMessage}
        userEmailAddress={emailState?.user_email_address || 'user@example.com'}
        onSend={handleSendEmail}
      />
    </div>
  );
}
