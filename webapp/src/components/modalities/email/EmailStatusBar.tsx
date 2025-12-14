/**
 * Email status bar component.
 * Displays summary statistics about the email state.
 */
import type { EmailState } from './types';

interface EmailStatusBarProps {
  emailState: EmailState | null;
  selectedFolder: string;
}

/**
 * Count emails in a folder.
 */
function getFolderStats(emailState: EmailState | null, folder: string) {
  if (!emailState) {
    return { total: 0, unread: 0, threads: 0 };
  }

  const messageIds = emailState.folders[folder] || [];
  let unread = 0;
  const threadIds = new Set<string>();

  for (const msgId of messageIds) {
    const email = emailState.emails[msgId];
    if (email) {
      if (!email.is_read) unread++;
      threadIds.add(email.thread_id);
    }
  }

  return {
    total: messageIds.length,
    unread,
    threads: threadIds.size,
  };
}

/**
 * Count total emails across all folders.
 */
function getTotalStats(emailState: EmailState | null) {
  if (!emailState) {
    return { total: 0, unread: 0, threads: 0 };
  }

  let unread = 0;
  const total = Object.keys(emailState.emails).length;

  for (const email of Object.values(emailState.emails)) {
    if (!email.is_read) unread++;
  }

  return {
    total,
    unread,
    threads: Object.keys(emailState.threads).length,
  };
}

/**
 * Format relative time.
 */
function formatLastUpdated(timestamp: string | null): string {
  if (!timestamp) return 'Never';
  
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export function EmailStatusBar({ emailState, selectedFolder }: EmailStatusBarProps) {
  const folderStats = getFolderStats(emailState, selectedFolder);
  const totalStats = getTotalStats(emailState);

  return (
    <div className="flex items-center justify-between px-4 py-2 border-t bg-muted/30 text-xs text-muted-foreground">
      <div className="flex items-center gap-4">
        <span>
          {folderStats.total} {folderStats.total === 1 ? 'email' : 'emails'}
          {folderStats.unread > 0 && (
            <span className="text-primary ml-1">
              ({folderStats.unread} unread)
            </span>
          )}
        </span>
        <span>•</span>
        <span>
          {folderStats.threads} {folderStats.threads === 1 ? 'thread' : 'threads'}
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span>
          {totalStats.total} total emails
        </span>
        <span>•</span>
        <span>
          Last sync: {formatLastUpdated(emailState?.last_updated ?? null)}
        </span>
      </div>
    </div>
  );
}
