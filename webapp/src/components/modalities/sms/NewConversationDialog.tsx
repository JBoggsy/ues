/**
 * New conversation dialog for SMS viewer.
 * Allows starting a new conversation with a phone number.
 * 
 * NOTE: Contact selection is a placeholder pending Contacts modality.
 * When implemented, add a contact picker alongside direct phone entry.
 */
import { useState } from 'react';
import { Users, Phone, UserPlus } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface NewConversationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSend: (to_numbers: string[], body: string) => void;
  userPhoneNumber: string;
}

/**
 * Placeholder component for contact picker.
 * TODO: Replace with actual contact integration when Contacts modality is available.
 */
function ContactPickerPlaceholder() {
  return (
    <div className="text-center py-8 text-muted-foreground">
      <Users className="h-12 w-12 mx-auto mb-3 opacity-50" />
      <p className="text-sm font-medium mb-1">Contacts Coming Soon</p>
      <p className="text-xs">
        Contact selection will be available when the Contacts modality is implemented.
        <br />
        For now, please enter phone numbers directly.
      </p>
    </div>
  );
}

/**
 * Phone number input with recipient management.
 */
function PhoneNumberInput({
  recipients,
  onAddRecipient,
  onRemoveRecipient,
}: {
  recipients: string[];
  onAddRecipient: (phoneNumber: string) => void;
  onRemoveRecipient: (phoneNumber: string) => void;
}) {
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  const validatePhoneNumber = (value: string): boolean => {
    // Basic phone number validation - at least 7 digits
    const cleaned = value.replace(/\D/g, '');
    return cleaned.length >= 7;
  };

  const handleAdd = () => {
    const trimmed = inputValue.trim();
    if (!trimmed) return;

    if (!validatePhoneNumber(trimmed)) {
      setError('Please enter a valid phone number (at least 7 digits)');
      return;
    }

    if (recipients.includes(trimmed)) {
      setError('This number is already added');
      return;
    }

    onAddRecipient(trimmed);
    setInputValue('');
    setError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
    // Clear error on typing
    if (error) setError(null);
  };

  return (
    <div className="space-y-2">
      <Label>Recipient(s)</Label>
      
      {/* Recipient badges */}
      {recipients.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {recipients.map((number) => (
            <Badge
              key={number}
              variant="secondary"
              className="pr-1"
            >
              <Phone className="h-3 w-3 mr-1" />
              {number}
              <button
                type="button"
                onClick={() => onRemoveRecipient(number)}
                className="ml-1 hover:bg-muted rounded-full p-0.5"
              >
                ×
              </button>
            </Badge>
          ))}
        </div>
      )}

      {/* Phone number input */}
      <div className="flex gap-2">
        <Input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter phone number..."
          className="flex-1"
        />
        <Button type="button" variant="outline" onClick={handleAdd}>
          <UserPlus className="h-4 w-4" />
        </Button>
      </div>

      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}

      <p className="text-xs text-muted-foreground">
        Enter a phone number and press Enter or click + to add.
        {recipients.length > 1 && ' Multiple recipients will create a group conversation.'}
      </p>
    </div>
  );
}

export function NewConversationDialog({
  open,
  onOpenChange,
  onSend,
  userPhoneNumber,
}: NewConversationDialogProps) {
  const [recipients, setRecipients] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [activeTab, setActiveTab] = useState<'phone' | 'contacts'>('phone');

  const handleAddRecipient = (phoneNumber: string) => {
    setRecipients([...recipients, phoneNumber]);
  };

  const handleRemoveRecipient = (phoneNumber: string) => {
    setRecipients(recipients.filter((r) => r !== phoneNumber));
  };

  const handleSend = async () => {
    if (recipients.length === 0 || !message.trim()) return;

    setIsSending(true);
    try {
      await onSend(recipients, message.trim());
      // Reset form
      setRecipients([]);
      setMessage('');
      onOpenChange(false);
    } finally {
      setIsSending(false);
    }
  };

  const handleClose = () => {
    if (!isSending) {
      setRecipients([]);
      setMessage('');
      onOpenChange(false);
    }
  };

  const canSend = recipients.length > 0 && message.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>New Message</DialogTitle>
          <DialogDescription>
            Start a new conversation by entering a phone number and message.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Recipient selection tabs */}
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="phone">
                <Phone className="h-4 w-4 mr-2" />
                Phone Number
              </TabsTrigger>
              <TabsTrigger value="contacts">
                <Users className="h-4 w-4 mr-2" />
                Contacts
              </TabsTrigger>
            </TabsList>

            <TabsContent value="phone" className="mt-4">
              <PhoneNumberInput
                recipients={recipients}
                onAddRecipient={handleAddRecipient}
                onRemoveRecipient={handleRemoveRecipient}
              />
            </TabsContent>

            <TabsContent value="contacts" className="mt-4">
              <ContactPickerPlaceholder />
            </TabsContent>
          </Tabs>

          <Separator />

          {/* Message input */}
          <div className="space-y-2">
            <Label htmlFor="message">Message</Label>
            <Textarea
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message..."
              rows={4}
              disabled={isSending}
            />
          </div>

          {/* Info about sender */}
          <p className="text-xs text-muted-foreground">
            Sending as: {userPhoneNumber}
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isSending}>
            Cancel
          </Button>
          <Button onClick={handleSend} disabled={!canSend || isSending}>
            {isSending ? 'Sending...' : 'Send Message'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
