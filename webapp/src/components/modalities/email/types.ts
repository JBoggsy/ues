/**
 * Type definitions for the Email Viewer component.
 * These extend the base API types with UI-specific properties.
 */

/**
 * Email message as stored in the backend.
 */
export interface EmailMessage {
  message_id: string;
  thread_id: string;
  from_address: string;
  to_addresses: string[];
  cc_addresses: string[];
  bcc_addresses: string[];
  reply_to_address: string | null;
  subject: string;
  body_text: string;
  body_html: string | null;
  attachments: string[];
  in_reply_to: string | null;
  references: string[];
  sent_at: string;
  received_at: string;
  is_read: boolean;
  is_starred: boolean;
  priority: string;
  folder: string;
  labels: string[];
}

/**
 * Email thread grouping multiple messages.
 */
export interface EmailThread {
  thread_id: string;
  subject: string;
  participant_addresses: string[];
  message_ids: string[];
  created_at: string;
  last_message_at: string;
  message_count: number;
  unread_count: number;
}

/**
 * Complete email state from the backend.
 */
export interface EmailState {
  modality_type: string;
  last_updated: string;
  update_count: number;
  emails: Record<string, EmailMessage>;
  threads: Record<string, EmailThread>;
  folders: Record<string, string[]>;
  labels: Record<string, string[]>;
  drafts: Record<string, EmailMessage>;
  user_email_address: string;
}

/**
 * Folder information for display.
 */
export interface FolderInfo {
  name: string;
  icon: string;
  count: number;
  unreadCount: number;
}

/**
 * Thread display item for the email list.
 */
export interface ThreadDisplayItem {
  thread_id: string;
  subject: string;
  participants: string[];
  lastMessage: EmailMessage;
  messageCount: number;
  unreadCount: number;
  isStarred: boolean;
  hasAttachments: boolean;
  folder: string;
}

/**
 * Selection state for email actions.
 */
export interface EmailSelection {
  selectedThreadIds: Set<string>;
  selectedMessageId: string | null;
}

/**
 * Compose email form data.
 */
export interface ComposeEmailData {
  to: string;
  cc: string;
  bcc: string;
  subject: string;
  body: string;
  replyToMessageId?: string;
  forwardMessageId?: string;
}

/**
 * Email action types.
 */
export type EmailAction =
  | 'reply'
  | 'reply_all'
  | 'forward'
  | 'delete'
  | 'archive'
  | 'mark_read'
  | 'mark_unread'
  | 'star'
  | 'unstar'
  | 'move'
  | 'add_label'
  | 'remove_label'
  | 'mark_spam';
