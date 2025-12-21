/**
 * Status bar component for SMS viewer.
 * Displays summary statistics at the bottom.
 */
import type { SMSState } from './types';

interface SMSStatusBarProps {
  smsState: SMSState | null;
}

export function SMSStatusBar({ smsState }: SMSStatusBarProps) {
  if (!smsState) {
    return (
      <div className="px-3 py-1.5 border-t bg-muted/30 text-xs text-muted-foreground">
        Loading...
      </div>
    );
  }

  const conversationCount = Object.keys(smsState.conversations).length;
  const archivedCount = Object.values(smsState.conversations).filter(
    (c) => c.is_archived
  ).length;
  const activeCount = conversationCount - archivedCount;

  return (
    <div className="px-3 py-1.5 border-t bg-muted/30 text-xs text-muted-foreground flex items-center gap-4">
      <span>
        {activeCount} conversation{activeCount !== 1 ? 's' : ''}
      </span>
      <span>•</span>
      <span>
        {smsState.total_message_count} message{smsState.total_message_count !== 1 ? 's' : ''}
      </span>
      <span>•</span>
      <span>
        {smsState.unread_count} unread
      </span>
      {archivedCount > 0 && (
        <>
          <span>•</span>
          <span className="text-muted-foreground/60">
            {archivedCount} archived
          </span>
        </>
      )}
    </div>
  );
}
