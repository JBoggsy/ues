/**
 * Status bar component for the Chat Viewer.
 * Displays summary statistics at the bottom of the conversation list.
 */

interface ChatStatusBarProps {
  conversationCount: number;
  messageCount: number;
}

export function ChatStatusBar({
  conversationCount,
  messageCount,
}: ChatStatusBarProps) {
  return (
    <div className="border-t px-3 py-2 text-xs text-muted-foreground bg-muted/30">
      <div className="space-y-0.5">
        <div>{conversationCount} conversation{conversationCount !== 1 ? 's' : ''}</div>
        <div>{messageCount} message{messageCount !== 1 ? 's' : ''} total</div>
      </div>
    </div>
  );
}
