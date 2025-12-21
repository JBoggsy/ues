/**
 * Type definitions for the Chat Viewer component.
 * These match the backend Chat state models.
 */

/**
 * Content block types for multimodal messages.
 */
export type ContentBlockType = 'text' | 'image' | 'audio' | 'video' | 'file';

/**
 * Text content block in a multimodal message.
 */
export interface TextContentBlock {
  type: 'text';
  text: string;
}

/**
 * Media content block in a multimodal message (image, audio, video).
 */
export interface MediaContentBlock {
  type: 'image' | 'audio' | 'video';
  source: 'url' | 'base64';
  url?: string;
  data?: string;
  media_type?: string;
  alt?: string;
}

/**
 * File content block in a multimodal message.
 */
export interface FileContentBlock {
  type: 'file';
  filename: string;
  data?: string;
  url?: string;
  mime_type?: string;
}

/**
 * Union type for all content block types.
 */
export type ContentBlock = TextContentBlock | MediaContentBlock | FileContentBlock;

/**
 * Message content can be a simple string or multimodal content blocks.
 */
export type MessageContent = string | ContentBlock[];

/**
 * Role of the message sender.
 */
export type MessageRole = 'user' | 'assistant';

/**
 * A single chat message as stored in the backend.
 */
export interface ChatMessage {
  message_id: string;
  conversation_id: string;
  role: MessageRole;
  content: MessageContent;
  timestamp: string;
  metadata: Record<string, unknown>;
}

/**
 * Metadata for a conversation.
 */
export interface ConversationMetadata {
  conversation_id: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
  participant_roles: string[];
}

/**
 * Complete chat state from the backend.
 */
export interface ChatState {
  modality_type: 'chat';
  current_time: string;
  conversations: Record<string, ConversationMetadata>;
  messages: ChatMessage[];
  total_message_count: number;
  conversation_count: number;
  max_history_size: number;
}

/**
 * Chat operations supported by the API.
 */
export type ChatOperation = 'send_message' | 'delete_message' | 'clear_conversation';

/**
 * Request to send a chat message.
 */
export interface SendMessageRequest {
  role: MessageRole;
  content: MessageContent;
  conversation_id?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Request to delete a chat message.
 */
export interface DeleteMessageRequest {
  message_id: string;
}

/**
 * Request to clear a conversation.
 */
export interface ClearConversationRequest {
  conversation_id: string;
}
