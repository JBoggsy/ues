/**
 * Email modality form component.
 * 
 * Allows users to create email events for various operations like
 * receiving, sending, replying, and managing emails.
 */
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { ModalityFormProps } from './types';

/**
 * Email operations grouped by category.
 */
const EMAIL_OPERATIONS = {
  compose: [
    { value: 'receive', label: 'Receive Email', description: 'Simulate receiving an email' },
    { value: 'send', label: 'Send Email', description: 'Simulate sending an email' },
    { value: 'reply', label: 'Reply', description: 'Reply to an existing email' },
    { value: 'reply_all', label: 'Reply All', description: 'Reply to all recipients' },
    { value: 'forward', label: 'Forward', description: 'Forward an email' },
    { value: 'save_draft', label: 'Save Draft', description: 'Save as draft' },
  ],
  manage: [
    { value: 'mark_read', label: 'Mark Read', description: 'Mark email as read' },
    { value: 'mark_unread', label: 'Mark Unread', description: 'Mark email as unread' },
    { value: 'star', label: 'Star', description: 'Star/flag an email' },
    { value: 'unstar', label: 'Unstar', description: 'Remove star from email' },
    { value: 'delete', label: 'Delete', description: 'Delete an email' },
    { value: 'archive', label: 'Archive', description: 'Archive an email' },
    { value: 'move', label: 'Move to Folder', description: 'Move email to folder' },
  ],
  labels: [
    { value: 'add_label', label: 'Add Label', description: 'Add label to email' },
    { value: 'remove_label', label: 'Remove Label', description: 'Remove label from email' },
    { value: 'mark_spam', label: 'Mark as Spam', description: 'Move to spam' },
    { value: 'mark_not_spam', label: 'Not Spam', description: 'Remove from spam' },
  ],
} as const;

/**
 * All operations flattened.
 */
const ALL_OPERATIONS = [
  ...EMAIL_OPERATIONS.compose,
  ...EMAIL_OPERATIONS.manage,
  ...EMAIL_OPERATIONS.labels,
];

/**
 * Operations that require compose fields (from, to, subject, body).
 */
const COMPOSE_OPERATIONS = ['receive', 'send', 'reply', 'reply_all', 'forward', 'save_draft', 'send_draft'];

/**
 * Operations that require a message_id.
 */
const MESSAGE_ID_OPERATIONS = [
  'reply', 'reply_all', 'forward', 'send_draft',
  'mark_read', 'mark_unread', 'star', 'unstar',
  'delete', 'archive', 'move',
  'add_label', 'remove_label', 'mark_spam', 'mark_not_spam',
];

/**
 * Common folder names.
 */
const FOLDER_PRESETS = ['inbox', 'sent', 'drafts', 'trash', 'spam', 'archive', 'work', 'personal'];

/**
 * Default data for a new email event.
 */
export const emailDefaultData = {
  operation: 'receive',
  from_address: 'sender@example.com',
  to_addresses: 'user@example.com',
  cc_addresses: '',
  subject: '',
  body_text: '',
  priority: 'normal',
  message_id: '',
  folder: 'inbox',
  labels: '',
};

/**
 * Validate email form data.
 */
export function validateEmailData(data: Record<string, unknown>): string | null {
  const operation = data.operation as string;
  
  if (!operation) {
    return 'Operation is required';
  }

  // Validate compose operations
  if (COMPOSE_OPERATIONS.includes(operation)) {
    const from = data.from_address as string;
    const to = data.to_addresses as string;
    const subject = data.subject as string;
    const body = data.body_text as string;

    if (!from || !from.trim()) {
      return 'From address is required';
    }
    if (!isValidEmail(from.trim())) {
      return 'Invalid from email address';
    }
    if (!to || !to.trim()) {
      return 'To address is required';
    }
    // Validate each recipient
    const toList = to.split(',').map(e => e.trim()).filter(e => e);
    for (const email of toList) {
      if (!isValidEmail(email)) {
        return `Invalid to email address: ${email}`;
      }
    }
    if (!subject || !subject.trim()) {
      return 'Subject is required';
    }
    if (!body || !body.trim()) {
      return 'Body is required';
    }
  }

  // Validate message_id operations
  if (MESSAGE_ID_OPERATIONS.includes(operation) && !COMPOSE_OPERATIONS.includes(operation)) {
    const messageId = data.message_id as string;
    if (!messageId || !messageId.trim()) {
      return 'Message ID is required for this operation';
    }
  }

  // Validate move operation
  if (operation === 'move') {
    const folder = data.folder as string;
    if (!folder || !folder.trim()) {
      return 'Target folder is required for move operation';
    }
  }

  // Validate label operations
  if (operation === 'add_label' || operation === 'remove_label') {
    const labels = data.labels as string;
    if (!labels || !labels.trim()) {
      return 'Labels are required for label operations';
    }
  }

  return null;
}

/**
 * Simple email validation.
 */
function isValidEmail(email: string): boolean {
  const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  return pattern.test(email);
}

/**
 * Transform form data to EmailInput format expected by API.
 */
export function transformEmailData(data: Record<string, unknown>): Record<string, unknown> {
  const operation = data.operation as string;
  const result: Record<string, unknown> = {
    operation,
  };

  // Add compose fields
  if (COMPOSE_OPERATIONS.includes(operation)) {
    result.from_address = (data.from_address as string).trim();
    result.to_addresses = (data.to_addresses as string)
      .split(',')
      .map(e => e.trim())
      .filter(e => e);
    
    const cc = data.cc_addresses as string;
    if (cc && cc.trim()) {
      result.cc_addresses = cc.split(',').map(e => e.trim()).filter(e => e);
    }
    
    result.subject = (data.subject as string).trim();
    result.body_text = (data.body_text as string).trim();
    result.priority = data.priority || 'normal';
  }

  // Add message_id for operations that need it
  if (MESSAGE_ID_OPERATIONS.includes(operation)) {
    const messageId = data.message_id as string;
    if (messageId && messageId.trim()) {
      result.message_id = messageId.trim();
    }
  }

  // Add folder for move operation
  if (operation === 'move') {
    result.folder = (data.folder as string).trim();
  }

  // Add labels for label operations
  if (operation === 'add_label' || operation === 'remove_label') {
    const labels = data.labels as string;
    if (labels && labels.trim()) {
      result.labels = labels.split(',').map(l => l.trim()).filter(l => l);
    }
  }

  return result;
}

/**
 * Form component for creating email events.
 */
export function EmailForm({ data, onChange, disabled }: ModalityFormProps) {
  const operation = data.operation as string;
  const showComposeFields = COMPOSE_OPERATIONS.includes(operation);
  const showMessageId = MESSAGE_ID_OPERATIONS.includes(operation) && !showComposeFields;
  const showFolder = operation === 'move';
  const showLabels = operation === 'add_label' || operation === 'remove_label';

  const handleChange = (field: string, value: string) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <div className="space-y-4">
      {/* Operation Selection */}
      <div className="space-y-2">
        <Label>
          Operation <span className="text-destructive">*</span>
        </Label>
        <Select
          value={operation}
          onValueChange={(value) => handleChange('operation', value)}
          disabled={disabled}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select operation..." />
          </SelectTrigger>
          <SelectContent>
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
              Compose
            </div>
            {EMAIL_OPERATIONS.compose.map((op) => (
              <SelectItem key={op.value} value={op.value}>
                {op.label}
              </SelectItem>
            ))}
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 pt-2">
              Manage
            </div>
            {EMAIL_OPERATIONS.manage.map((op) => (
              <SelectItem key={op.value} value={op.value}>
                {op.label}
              </SelectItem>
            ))}
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground border-t mt-1 pt-2">
              Labels & Spam
            </div>
            {EMAIL_OPERATIONS.labels.map((op) => (
              <SelectItem key={op.value} value={op.value}>
                {op.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          {ALL_OPERATIONS.find(op => op.value === operation)?.description}
        </p>
      </div>

      {/* Compose Fields */}
      {showComposeFields && (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="email_from">
                From <span className="text-destructive">*</span>
              </Label>
              <Input
                id="email_from"
                type="email"
                placeholder="sender@example.com"
                value={(data.from_address as string) || ''}
                onChange={(e) => handleChange('from_address', e.target.value)}
                disabled={disabled}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="email_priority">Priority</Label>
              <Select
                value={(data.priority as string) || 'normal'}
                onValueChange={(value) => handleChange('priority', value)}
                disabled={disabled}
              >
                <SelectTrigger id="email_priority">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email_to">
              To <span className="text-destructive">*</span>
            </Label>
            <Input
              id="email_to"
              type="text"
              placeholder="recipient@example.com (comma-separated for multiple)"
              value={(data.to_addresses as string) || ''}
              onChange={(e) => handleChange('to_addresses', e.target.value)}
              disabled={disabled}
            />
            <p className="text-xs text-muted-foreground">
              Separate multiple addresses with commas
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email_cc">CC</Label>
            <Input
              id="email_cc"
              type="text"
              placeholder="cc@example.com (optional)"
              value={(data.cc_addresses as string) || ''}
              onChange={(e) => handleChange('cc_addresses', e.target.value)}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email_subject">
              Subject <span className="text-destructive">*</span>
            </Label>
            <Input
              id="email_subject"
              type="text"
              placeholder="Email subject line"
              value={(data.subject as string) || ''}
              onChange={(e) => handleChange('subject', e.target.value)}
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email_body">
              Body <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="email_body"
              placeholder="Email body content..."
              rows={5}
              value={(data.body_text as string) || ''}
              onChange={(e) => handleChange('body_text', e.target.value)}
              disabled={disabled}
            />
          </div>
        </>
      )}

      {/* Message ID for management operations */}
      {showMessageId && (
        <div className="space-y-2">
          <Label htmlFor="email_message_id">
            Message ID <span className="text-destructive">*</span>
          </Label>
          <Input
            id="email_message_id"
            type="text"
            placeholder="existing-message-id"
            value={(data.message_id as string) || ''}
            onChange={(e) => handleChange('message_id', e.target.value)}
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">
            The ID of the email to perform this action on
          </p>
        </div>
      )}

      {/* Folder for move operation */}
      {showFolder && (
        <div className="space-y-2">
          <Label htmlFor="email_folder">
            Target Folder <span className="text-destructive">*</span>
          </Label>
          <Select
            value={(data.folder as string) || ''}
            onValueChange={(value) => handleChange('folder', value)}
            disabled={disabled}
          >
            <SelectTrigger id="email_folder">
              <SelectValue placeholder="Select folder..." />
            </SelectTrigger>
            <SelectContent>
              {FOLDER_PRESETS.map((folder) => (
                <SelectItem key={folder} value={folder}>
                  {folder.charAt(0).toUpperCase() + folder.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Labels for label operations */}
      {showLabels && (
        <div className="space-y-2">
          <Label htmlFor="email_labels">
            Labels <span className="text-destructive">*</span>
          </Label>
          <Input
            id="email_labels"
            type="text"
            placeholder="work, important (comma-separated)"
            value={(data.labels as string) || ''}
            onChange={(e) => handleChange('labels', e.target.value)}
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">
            Separate multiple labels with commas
          </p>
        </div>
      )}
    </div>
  );
}
