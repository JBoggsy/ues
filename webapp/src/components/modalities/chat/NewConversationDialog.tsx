/**
 * Dialog for creating a new chat conversation.
 * Auto-generates a conversation ID but allows customization.
 */
import { useState, useCallback } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface NewConversationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateConversation: (conversationId: string) => void;
  existingConversationIds: string[];
}

/**
 * Generate a short, readable conversation ID.
 */
function generateConversationId(): string {
  // Use crypto.randomUUID() and take first 8 characters for a short, unique ID
  return `chat-${crypto.randomUUID().substring(0, 8)}`;
}

export function NewConversationDialog({
  open,
  onOpenChange,
  onCreateConversation,
  existingConversationIds,
}: NewConversationDialogProps) {
  const [conversationId, setConversationId] = useState(() => generateConversationId());
  const [error, setError] = useState<string | null>(null);

  // Regenerate ID when dialog opens
  const handleOpenChange = useCallback((isOpen: boolean) => {
    if (isOpen) {
      setConversationId(generateConversationId());
      setError(null);
    }
    onOpenChange(isOpen);
  }, [onOpenChange]);

  const handleCreate = useCallback(() => {
    const trimmedId = conversationId.trim();
    
    if (!trimmedId) {
      setError('Conversation ID cannot be empty');
      return;
    }

    if (existingConversationIds.includes(trimmedId)) {
      setError('A conversation with this ID already exists');
      return;
    }

    onCreateConversation(trimmedId);
    handleOpenChange(false);
  }, [conversationId, existingConversationIds, onCreateConversation, handleOpenChange]);

  const handleInputChange = useCallback((value: string) => {
    setConversationId(value);
    setError(null);
  }, []);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>New Conversation</DialogTitle>
          <DialogDescription>
            Start a new chat conversation. You can customize the conversation ID
            or use the auto-generated one.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="conversationId">Conversation ID</Label>
            <Input
              id="conversationId"
              value={conversationId}
              onChange={(e) => handleInputChange(e.target.value)}
              placeholder="Enter conversation ID"
            />
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleCreate}>Create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
