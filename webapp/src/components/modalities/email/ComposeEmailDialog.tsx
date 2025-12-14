/**
 * Compose email dialog component.
 * Modal for creating, replying to, or forwarding emails.
 */
import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import {
  ChevronDown,
  ChevronUp,
  Paperclip,
  Send,
} from 'lucide-react';
import type { EmailMessage, ComposeEmailData } from './types';

export type ComposeMode = 'new' | 'reply' | 'reply_all' | 'forward';

interface ComposeEmailDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: ComposeMode;
  originalMessage?: EmailMessage | null;
  userEmailAddress: string;
  onSend: (data: ComposeEmailData, mode: ComposeMode) => void;
}

/**
 * Build initial form data based on compose mode.
 */
function buildInitialData(
  mode: ComposeMode,
  originalMessage: EmailMessage | null | undefined,
  userEmailAddress: string
): ComposeEmailData {
  if (!originalMessage) {
    return { to: '', cc: '', bcc: '', subject: '', body: '' };
  }

  switch (mode) {
    case 'reply':
      return {
        to: originalMessage.from_address,
        cc: '',
        bcc: '',
        subject: originalMessage.subject.startsWith('Re: ')
          ? originalMessage.subject
          : `Re: ${originalMessage.subject}`,
        body: buildReplyBody(originalMessage),
        replyToMessageId: originalMessage.message_id,
      };

    case 'reply_all': {
      // Include original sender and all recipients except self
      const allRecipients = new Set([
        originalMessage.from_address,
        ...originalMessage.to_addresses,
      ]);
      allRecipients.delete(userEmailAddress);
      
      const ccRecipients = new Set([...originalMessage.cc_addresses]);
      ccRecipients.delete(userEmailAddress);

      return {
        to: Array.from(allRecipients).join(', '),
        cc: Array.from(ccRecipients).join(', '),
        bcc: '',
        subject: originalMessage.subject.startsWith('Re: ')
          ? originalMessage.subject
          : `Re: ${originalMessage.subject}`,
        body: buildReplyBody(originalMessage),
        replyToMessageId: originalMessage.message_id,
      };
    }

    case 'forward':
      return {
        to: '',
        cc: '',
        bcc: '',
        subject: originalMessage.subject.startsWith('Fwd: ')
          ? originalMessage.subject
          : `Fwd: ${originalMessage.subject}`,
        body: buildForwardBody(originalMessage),
        forwardMessageId: originalMessage.message_id,
      };

    default:
      return { to: '', cc: '', bcc: '', subject: '', body: '' };
  }
}

/**
 * Build reply body with quoted original message.
 */
function buildReplyBody(original: EmailMessage): string {
  const date = new Date(original.sent_at);
  const dateStr = date.toLocaleDateString([], {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  return `\n\n---\nOn ${dateStr}, ${original.from_address} wrote:\n\n${original.body_text
    .split('\n')
    .map((line) => `> ${line}`)
    .join('\n')}`;
}

/**
 * Build forward body with original message details.
 */
function buildForwardBody(original: EmailMessage): string {
  const date = new Date(original.sent_at);
  const dateStr = date.toLocaleDateString([], {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });

  return `\n\n---------- Forwarded message ---------
From: ${original.from_address}
Date: ${dateStr}
Subject: ${original.subject}
To: ${original.to_addresses.join(', ')}
${original.cc_addresses.length > 0 ? `Cc: ${original.cc_addresses.join(', ')}\n` : ''}
${original.body_text}`;
}

/**
 * Get dialog title based on mode.
 */
function getTitle(mode: ComposeMode): string {
  switch (mode) {
    case 'reply':
      return 'Reply';
    case 'reply_all':
      return 'Reply All';
    case 'forward':
      return 'Forward';
    default:
      return 'Compose Email';
  }
}

export function ComposeEmailDialog({
  open,
  onOpenChange,
  mode,
  originalMessage,
  userEmailAddress,
  onSend,
}: ComposeEmailDialogProps) {
  const [formData, setFormData] = useState<ComposeEmailData>(() =>
    buildInitialData(mode, originalMessage, userEmailAddress)
  );
  const [showCcBcc, setShowCcBcc] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // Reset form when dialog opens or mode changes
  useEffect(() => {
    if (open) {
      setFormData(buildInitialData(mode, originalMessage, userEmailAddress));
      setShowCcBcc(mode === 'reply_all' && (originalMessage?.cc_addresses?.length ?? 0) > 0);
      setIsSending(false);
    }
  }, [open, mode, originalMessage, userEmailAddress]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.to.trim()) {
      return; // TODO: Show validation error
    }

    setIsSending(true);
    try {
      await onSend(formData, mode);
      onOpenChange(false);
    } catch (error) {
      console.error('Failed to send email:', error);
    } finally {
      setIsSending(false);
    }
  };

  const updateField = (field: keyof ComposeEmailData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{getTitle(mode)}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="space-y-4 flex-1 overflow-y-auto">
            {/* To Field */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="to">To</Label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => setShowCcBcc(!showCcBcc)}
                >
                  {showCcBcc ? (
                    <>
                      <ChevronUp className="h-3 w-3 mr-1" />
                      Hide Cc/Bcc
                    </>
                  ) : (
                    <>
                      <ChevronDown className="h-3 w-3 mr-1" />
                      Show Cc/Bcc
                    </>
                  )}
                </Button>
              </div>
              <Input
                id="to"
                type="text"
                placeholder="recipient@example.com"
                value={formData.to}
                onChange={(e) => updateField('to', e.target.value)}
                required
              />
            </div>

            {/* Cc/Bcc Fields */}
            {showCcBcc && (
              <>
                <div className="space-y-2">
                  <Label htmlFor="cc">Cc</Label>
                  <Input
                    id="cc"
                    type="text"
                    placeholder="cc@example.com"
                    value={formData.cc}
                    onChange={(e) => updateField('cc', e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="bcc">Bcc</Label>
                  <Input
                    id="bcc"
                    type="text"
                    placeholder="bcc@example.com"
                    value={formData.bcc}
                    onChange={(e) => updateField('bcc', e.target.value)}
                  />
                </div>
              </>
            )}

            {/* Subject Field */}
            <div className="space-y-2">
              <Label htmlFor="subject">Subject</Label>
              <Input
                id="subject"
                type="text"
                placeholder="Email subject"
                value={formData.subject}
                onChange={(e) => updateField('subject', e.target.value)}
              />
            </div>

            <Separator />

            {/* Body Field */}
            <div className="space-y-2 flex-1">
              <Label htmlFor="body">Message</Label>
              <Textarea
                id="body"
                placeholder="Write your message..."
                value={formData.body}
                onChange={(e) => updateField('body', e.target.value)}
                className="min-h-[200px] resize-none"
              />
            </div>
          </div>

          <DialogFooter className="mt-4 pt-4 border-t">
            <div className="flex items-center justify-between w-full">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                disabled
                title="Attachments coming soon"
              >
                <Paperclip className="h-4 w-4 mr-2" />
                Attach
              </Button>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isSending || !formData.to.trim()}>
                  <Send className="h-4 w-4 mr-2" />
                  {isSending ? 'Sending...' : 'Send'}
                </Button>
              </div>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
