/**
 * Status bar component for the Contacts viewer.
 * Displays summary statistics at the bottom.
 */
import type { ContactsState } from './types';

interface ContactsStatusBarProps {
  contactsState: ContactsState | null;
}

export function ContactsStatusBar({ contactsState }: ContactsStatusBarProps) {
  if (!contactsState) {
    return (
      <div className="px-3 py-1.5 border-t bg-muted/30 text-xs text-muted-foreground">
        Loading...
      </div>
    );
  }

  const groupCount = contactsState.groups.length;

  return (
    <div className="px-3 py-1.5 border-t bg-muted/30 text-xs text-muted-foreground flex items-center gap-4">
      <span>
        {contactsState.total_count} contact{contactsState.total_count !== 1 ? 's' : ''}
      </span>
      <span>•</span>
      <span>
        {contactsState.favorites_count} favorite{contactsState.favorites_count !== 1 ? 's' : ''}
      </span>
      {contactsState.blocked_count > 0 && (
        <>
          <span>•</span>
          <span className="text-muted-foreground/60">
            {contactsState.blocked_count} blocked
          </span>
        </>
      )}
      {groupCount > 0 && (
        <>
          <span>•</span>
          <span>
            {groupCount} group{groupCount !== 1 ? 's' : ''}
          </span>
        </>
      )}
    </div>
  );
}
