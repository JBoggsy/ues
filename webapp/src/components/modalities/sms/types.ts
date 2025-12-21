/**
 * Type definitions for the SMS Viewer component.
 * These match the backend SMS state models with UI-specific extensions.
 * 
 * NOTE: Contact name resolution is a placeholder pending Contacts modality.
 * When Contacts is implemented, integrate lookups for display names.
 */

/**
 * Attachment on an SMS/RCS message.
 */
export interface MessageAttachment {
  filename: string;
  size: number;
  mime_type: string;
  attachment_id: string;
  thumbnail_url?: string;
  duration?: number;
}

/**
 * Emoji reaction on a message.
 */
export interface MessageReaction {
  reaction_id: string;
  message_id: string;
  phone_number: string;
  emoji: string;
  timestamp: string;
}

/**
 * Participant in a group conversation.
 */
export interface GroupParticipant {
  phone_number: string;
  is_admin: boolean;
  joined_at: string;
  left_at?: string;
}

/**
 * SMS/RCS message as stored in the backend.
 */
export interface SMSMessage {
  message_id: string;
  thread_id: string;
  from_number: string;
  to_numbers: string[];
  body: string;
  attachments: MessageAttachment[];
  reactions: MessageReaction[];
  message_type: 'sms' | 'rcs';
  direction: 'incoming' | 'outgoing';
  sent_at: string;
  delivered_at?: string;
  read_at?: string;
  is_read: boolean;
  delivery_status: 'sending' | 'sent' | 'delivered' | 'failed' | 'read';
  edited_at?: string;
  is_deleted: boolean;
  replied_to_message_id?: string;
  is_spam: boolean;
}

/**
 * Conversation thread containing messages.
 */
export interface SMSConversation {
  thread_id: string;
  conversation_type: 'one_on_one' | 'group';
  participants: GroupParticipant[];
  group_name?: string;
  group_photo_url?: string;
  created_at: string;
  created_by?: string;
  last_message_at: string;
  message_count: number;
  unread_count: number;
  is_pinned: boolean;
  is_muted: boolean;
  is_archived: boolean;
  draft_message?: string;
}

/**
 * Complete SMS state from the backend.
 */
export interface SMSState {
  modality_type: 'sms';
  current_time: string;
  user_phone_number: string;
  messages: Record<string, SMSMessage>;
  conversations: Record<string, SMSConversation>;
  total_message_count: number;
  unread_count: number;
  total_conversation_count: number;
}

/**
 * Filter options for conversation list.
 */
export type ConversationFilter = 'all' | 'unread' | 'groups' | 'archived';

/**
 * Compose message form data.
 */
export interface ComposeMessageData {
  to_numbers: string[];
  body: string;
  message_type: 'sms' | 'rcs';
  attachments: MessageAttachment[];
  replied_to_message_id?: string;
}

/**
 * Display item for conversation list.
 * Extends conversation data with computed display properties.
 */
export interface ConversationDisplayItem {
  conversation: SMSConversation;
  lastMessage?: SMSMessage;
  displayName: string;
  displayNumber: string;
  lastMessagePreview: string;
  lastMessageTime: string;
  isGroup: boolean;
  participantCount: number;
}

/**
 * Contact info placeholder.
 * TODO: Replace with actual Contact type when Contacts modality is implemented.
 */
export interface ContactInfo {
  phone_number: string;
  display_name?: string;
  // Future fields from Contacts modality:
  // avatar_url?: string;
  // is_blocked?: boolean;
}

/**
 * Resolve a phone number to a display name.
 * Placeholder for Contacts modality integration.
 * 
 * @param phoneNumber - The phone number to resolve
 * @param contacts - Map of phone numbers to contact info (placeholder)
 * @returns Display name if found, otherwise formatted phone number
 */
export function resolveContactName(
  phoneNumber: string,
  contacts?: Map<string, ContactInfo>
): string {
  // TODO: When Contacts modality is available, use it to look up names
  const contact = contacts?.get(phoneNumber);
  if (contact?.display_name) {
    return contact.display_name;
  }
  // Return the phone number as-is for now
  return phoneNumber;
}

/**
 * Format a phone number for display.
 * Placeholder for more sophisticated formatting.
 */
export function formatPhoneNumber(phoneNumber: string): string {
  // Basic US phone number formatting
  const cleaned = phoneNumber.replace(/\D/g, '');
  if (cleaned.length === 10) {
    return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
  }
  if (cleaned.length === 11 && cleaned.startsWith('1')) {
    return `+1 (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
  }
  // Return as-is if we can't parse it
  return phoneNumber;
}

/**
 * SMS action types for API operations.
 */
export type SMSAction =
  | 'send'
  | 'receive'
  | 'delete'
  | 'mark_read'
  | 'mark_unread'
  | 'react'
  | 'archive'
  | 'unarchive'
  | 'pin'
  | 'unpin'
  | 'mute'
  | 'unmute';
