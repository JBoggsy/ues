/**
 * Chat modality components barrel export.
 */
export { ChatViewer } from './ChatViewer';

// Internal components - available for testing but not re-exported from parent
// to avoid naming conflicts with SMS modality
export { ConversationList as ChatConversationList } from './ConversationList';
export { MessageThread as ChatMessageThread } from './MessageThread';
export { ComposeArea as ChatComposeArea } from './ComposeArea';
export { ChatToolbar } from './ChatToolbar';
export { ChatStatusBar } from './ChatStatusBar';
export { NewConversationDialog as ChatNewConversationDialog } from './NewConversationDialog';

export type * from './types';
