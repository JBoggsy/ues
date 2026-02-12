/**
 * Type definitions for the SMS Viewer component.
 * These match the backend SMS state models with UI-specific extensions.
 *
 * Contact name resolution is provided via {@link ContactNameResolver} which
 * is backed by the shared useContactsLookup hook from the Contacts modality.
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
 * Phone-number-to-display-name resolver function type.
 * Provided by the useContactsLookup hook from the Contacts modality.
 */
export type ContactNameResolver = (phoneNumber: string) => string | undefined;

/**
 * Resolve a phone number to a display name using an optional contacts resolver.
 *
 * When a resolver is provided (from useContactsLookup), it looks up the phone
 * number in the contacts store. Falls back to the raw phone number if no
 * resolver is available or the number isn't in contacts.
 *
 * @param phoneNumber - The phone number to resolve.
 * @param resolver - Optional contacts-backed resolver function.
 * @returns Display name if found, otherwise the raw phone number.
 */
export function resolveContactName(
  phoneNumber: string,
  resolver?: ContactNameResolver
): string {
  const resolved = resolver?.(phoneNumber);
  if (resolved) return resolved;
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
