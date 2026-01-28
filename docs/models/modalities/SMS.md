# SMS/RCS Modality Design

The SMS/RCS modality simulates text messaging (SMS) and Rich Communication Services (RCS) for testing AI personal assistants. This modality focuses on native phone-based texting, not third-party chat apps like WhatsApp, Telegram, or iMessage. It includes the core features of modern messaging apps without protocol-level details like carrier routing, delivery receipts, or telecom infrastructure.

## Message Content

- **Text body**: Plain text message content
- **Media attachments**: Images, videos, audio, GIFs, and other file types
  - Filename, size, MIME type, thumbnail (for images/videos)
- **Rich content (RCS)**: 
  - Formatted text (bold, italic, links)
  - Read receipts
  - Typing indicators
  - High-resolution media
- **Emoji and reactions**: Unicode emoji in messages and message reactions
- **Links**: URLs with optional preview metadata (title, description, thumbnail)

## Message Metadata

- **Message ID**: Unique identifier for each message
- **Phone numbers**: 
  - From number (sender)
  - To number(s) (recipient(s))
- **Timestamps**:
  - Sent timestamp (when message was sent)
  - Delivered timestamp (when message reached recipient's device)
  - Read timestamp (when recipient opened/read message)
- **Message type**: SMS (basic text) vs RCS (rich messaging)
- **Direction**: Incoming (received) or outgoing (sent)
- **Thread ID**: Groups messages into conversations

## Conversations (Threads)

- **One-on-one conversations**: Direct messaging between two people
- **Group conversations**: Multi-participant text threads
  - Group name (optional, user-defined)
  - Participant list with phone numbers
  - Group created timestamp
  - Group creator
- **Conversation metadata**:
  - Last message timestamp
  - Unread message count
  - Total message count
  - Pinned status
  - Muted status (notifications disabled)
  - Archived status

## Contact Integration

**Note**: The SMS modality stores and operates on **phone numbers only**. Display names, contact photos, blocked status, and other contact metadata are managed by a separate Contacts modality (to be implemented). The SMS state references phone numbers as immutable identifiers; display names are resolved via cross-modality queries when rendering messages.

- **Phone numbers**: All participants identified by phone number (E.164 format recommended)
- **Display name resolution**: Query Contacts modality to get display names for phone numbers
- **Contact photos**: Retrieved from Contacts modality when rendering UI
- **Unknown numbers**: Display raw phone number when not found in Contacts
- **Blocked numbers**: Managed by Contacts modality; SMS checks blocked status during message processing
- **Spam detection**: Flag individual messages as spam (message-level flag, not contact-level)

## Message Status and State

- **Delivery status**: Sending, sent, delivered, failed
- **Read status**: Read/unread for received messages
- **Seen by indicators**: In group chats, who has read each message
- **Failed message**: Retry or delete failed sends
- **Draft messages**: Partially composed messages saved per conversation

## Message Actions

- **Send message**: Create and send new text message
- **Send media**: Attach and send images, videos, audio, files
- **Reply**: Respond to message (can quote/reference original)
- **Forward**: Send message to different conversation
- **Delete**: Remove message (for yourself or for everyone if supported)
- **Edit**: Modify sent message (RCS feature, limited time window)
- **React**: Add emoji reaction to a message
- **Copy text**: Copy message content to clipboard
- **Share**: Share message content to other apps

## Group Conversation Features

- **Create group**: Start new multi-participant conversation
- **Add participants**: Add new members to existing group
- **Remove participants**: Remove members from group
- **Leave group**: Exit group conversation
- **Group name**: Set/change group name
- **Group photo**: Set/change group icon/photo
- **Group admin**: Designate group administrators with special permissions
- **Participant list**: View all current group members
- **Participant count**: Track number of members

## Conversation Management

- **Pin conversations**: Keep important conversations at top of list
- **Mute notifications**: Disable alerts for specific conversation
- **Archive conversations**: Hide conversation from main list (still accessible)
- **Unarchive**: Restore archived conversation to main list
- **Delete conversation**: Remove entire conversation history
- **Mark as read/unread**: Change read status for all messages in conversation
- **Block contact**: Prevent messages from specific number
- **Unblock contact**: Allow messages from previously blocked number

## Search and Filtering

- **Search by**:
  - Message content (text search)
  - Sender/recipient phone number or contact name
  - Date range
  - Media type (messages with photos, videos, etc.)
  - Conversation/thread
- **Filter by**:
  - Read/unread status
  - Conversation type (one-on-one vs group)
  - Has attachments
  - Pinned conversations
  - Archived conversations
  - Muted conversations

## Notifications

- **Message notifications**: Alert when new message arrives
- **Notification content**:
  - Sender name/number
  - Message preview (first N characters)
  - Conversation context
- **Notification actions**: Reply, mark as read, mute directly from notification
- **Do Not Disturb**: Global notification muting
- **Per-conversation muting**: Disable notifications for specific conversations

## RCS-Specific Features

RCS (Rich Communication Services) is the modern SMS successor supported by Android Messages and some carriers:

- **Typing indicators**: "User is typing..." status
- **Read receipts**: Confirmation when message is read
- **Delivery receipts**: Confirmation when message is delivered
- **High-resolution media**: Full-quality photos/videos (not compressed like MMS)
- **Group chat features**: Enhanced group messaging with member management
- **Message editing**: Edit sent messages within time window
- **Message reactions**: Emoji reactions to messages
- **Rich cards**: Interactive message cards (buttons, carousels)
- **File sharing**: Send any file type, not just media
- **Location sharing**: Share map location

**RCS Fallback**: If recipient doesn't support RCS, messages automatically fall back to SMS/MMS.

## Features Explicitly Excluded

The following SMS/RCS features are **not** simulated to maintain simplicity:
- Third-party messaging apps (WhatsApp, Telegram, Signal, Facebook Messenger, iMessage)
- SMS protocol details (PDU encoding, GSM 7-bit alphabet)
- Carrier routing and delivery infrastructure
- SIM card management
- Dual SIM handling
- SMS over IP (VoIP) protocols
- Short codes and premium SMS
- SMS authentication/2FA message generation
- SMS backup and restore protocols
- SMS to email forwarding
- International SMS country codes and costs
- MMS APN configuration
- RCS configuration and provisioning
- End-to-end encryption protocols (Signal Protocol)
- Self-destructing messages
- Message scheduling (send later)
- Auto-reply and vacation responders

---

## Implementation Design

### Helper Classes

#### `MessageAttachment`
Represents media or file attachments in messages.

**Attributes:**
- `filename: str` - Original filename
- `size: int` - File size in bytes
- `mime_type: str` - MIME type (e.g., "image/jpeg", "video/mp4", "audio/mpeg")
- `attachment_id: str` - Unique identifier (auto-generated UUID)
- `thumbnail_url: Optional[str]` - Thumbnail for images/videos (if available)
- `duration: Optional[int]` - Duration in seconds for audio/video

**Methods:**
- `to_dict() -> dict[str, Any]` - Serialize to dictionary for API responses
- `is_image() -> bool` - Check if attachment is an image
- `is_video() -> bool` - Check if attachment is a video
- `is_audio() -> bool` - Check if attachment is audio

#### `MessageReaction`
Represents an emoji reaction to a message.

**Attributes:**
- `reaction_id: str` - Unique reaction identifier (UUID)
- `message_id: str` - ID of message being reacted to
- `phone_number: str` - Phone number of person who reacted
- `emoji: str` - Emoji character(s) used for reaction
- `timestamp: datetime` - When reaction was added (simulator time)

**Methods:**
- `to_dict() -> dict[str, Any]` - Serialize to dictionary

#### `GroupParticipant`
Represents a participant in a group conversation.

**Attributes:**
- `phone_number: str` - Participant's phone number (immutable identifier)
- `is_admin: bool` - Whether participant has admin privileges (default: False)
- `joined_at: datetime` - When participant joined group (simulator time)
- `left_at: Optional[datetime]` - When participant left group, if applicable

**Note**: Display names are resolved by querying the Contacts modality with the phone number.

**Methods:**
- `to_dict() -> dict[str, Any]` - Serialize to dictionary
- `is_active() -> bool` - Check if participant is currently in group (left_at is None)

#### `SMSMessage`
Represents a complete SMS/RCS message with all metadata.

**Attributes:**
- `message_id: str` - Unique message identifier (UUID)
- `thread_id: str` - Conversation/thread identifier
- `from_number: str` - Sender phone number (E.164 format recommended)
- `to_numbers: list[str]` - Recipient phone number(s)
- `body: str` - Message text content
- `attachments: list[MessageAttachment]` - Media/file attachments (default: empty list)
- `reactions: list[MessageReaction]` - Emoji reactions to this message (default: empty list)
- `message_type: str` - "sms" or "rcs" (default: "sms")
- `direction: str` - "incoming" or "outgoing"
- `sent_at: datetime` - When message was sent (simulator time)
- `delivered_at: Optional[datetime]` - When message was delivered (outgoing messages)
- `read_at: Optional[datetime]` - When message was read (outgoing) or when user read it (incoming)
- `is_read: bool` - Read status (default: False for incoming, True for outgoing)
- `delivery_status: str` - "sending", "sent", "delivered", "failed", "read" (default: "sent")
- `edited_at: Optional[datetime]` - When message was edited (RCS only)
- `is_deleted: bool` - Whether message has been deleted (default: False)
- `replied_to_message_id: Optional[str]` - ID of message this is replying to
- `is_spam: bool` - Whether flagged as spam (default: False)

**Methods:**
- `to_dict() -> dict[str, Any]` - Serialize to dictionary for API responses
- `mark_read()` - Set is_read to True and read_at to current time
- `mark_unread()` - Set is_read to False and clear read_at
- `mark_delivered()` - Update delivery_status to "delivered" and set delivered_at
- `mark_failed()` - Update delivery_status to "failed"
- `add_reaction(phone_number: str, emoji: str)` - Add emoji reaction
- `remove_reaction(reaction_id: str)` - Remove specific reaction
- `edit_body(new_body: str)` - Edit message text (RCS only, updates edited_at)
- `soft_delete()` - Mark as deleted without removing from state

#### `SMSConversation`
Represents a conversation thread (one-on-one or group).

**Attributes:**
- `thread_id: str` - Unique conversation identifier (UUID)
- `conversation_type: str` - "one_on_one" or "group"
- `participants: list[GroupParticipant]` - All participants in conversation
- `group_name: Optional[str]` - User-defined group name (group conversations only)
- `group_photo_url: Optional[str]` - URL to group icon/photo
- `created_at: datetime` - When conversation was created (simulator time)
- `created_by: Optional[str]` - Phone number of conversation creator (groups)
- `last_message_at: datetime` - Timestamp of most recent message
- `message_count: int` - Total number of messages in conversation
- `unread_count: int` - Number of unread messages
- `is_pinned: bool` - Whether conversation is pinned to top (default: False)
- `is_muted: bool` - Whether notifications are disabled (default: False)
- `is_archived: bool` - Whether conversation is archived (default: False)
- `draft_message: Optional[str]` - Partially composed message text

**Methods:**
- `to_dict() -> dict[str, Any]` - Serialize to dictionary for API responses
- `is_group() -> bool` - Check if conversation is group chat
- `get_participant_numbers() -> list[str]` - Get list of all participant phone numbers
- `get_active_participants() -> list[GroupParticipant]` - Get currently active participants
- `add_participant(phone_number: str, display_name: Optional[str], is_admin: bool)` - Add new participant
- `remove_participant(phone_number: str)` - Remove participant (set left_at)
- `get_other_participant() -> Optional[str]` - For one-on-one, get the other phone number
- `update_last_message(timestamp: datetime)` - Update last_message_at
- `increment_unread()` - Increase unread count
- `mark_all_read()` - Reset unread_count to 0
- `pin()` - Set is_pinned to True
- `unpin()` - Set is_pinned to False
- `mute()` - Set is_muted to True
- `unmute()` - Set is_muted to False
- `archive()` - Set is_archived to True
- `unarchive()` - Set is_archived to False
- `save_draft(text: str)` - Save draft message text
- `clear_draft()` - Clear draft message

---

## SMS Input/State Models

### `SMSInput` (models/modalities/sms_input.py)

The event payload for SMS/RCS operations (send message, update conversation, etc.).

**Attributes:**
- `modality_type: str` - Always "sms"
- `timestamp: datetime` - When this input event occurs (simulator time)
- `input_id: str` - Unique identifier for this input (auto-generated UUID)
- `action: str` - Type of action:
  - `send_message`
  - `receive_message`
  - `update_delivery_status`
  - `add_reaction`
  - `remove_reaction`
  - `edit_message`
  - `delete_message`
  - `create_group`
  - `update_group`
  - `add_participant`
  - `remove_participant`
  - `leave_group`
  - `update_conversation`
- `message_data: Optional[dict[str, Any]]` - For message actions (send, receive, edit)
  - `from_number: str` - Sender phone number
  - `to_numbers: list[str]` - Recipient phone number(s)
  - `body: str` - Message text
  - `attachments: list[dict]` - Attachment metadata
  - `message_type: str` - "sms" or "rcs"
  - `thread_id: Optional[str]` - Existing conversation ID (auto-created if not provided)
  - `replied_to_message_id: Optional[str]` - Message being replied to
- `delivery_update_data: Optional[dict[str, Any]]` - For delivery status updates
  - `message_id: str` - Message to update
  - `new_status: str` - "delivered", "read", "failed"
  - `timestamp: datetime` - When status change occurred
- `reaction_data: Optional[dict[str, Any]]` - For add/remove reaction
  - `message_id: str` - Message to react to
  - `phone_number: str` - Who is reacting
  - `emoji: str` - Emoji character (add_reaction only)
  - `reaction_id: str` - Reaction to remove (remove_reaction only)
- `edit_data: Optional[dict[str, Any]]` - For message editing
  - `message_id: str` - Message to edit
  - `new_body: str` - Updated message text
- `delete_data: Optional[dict[str, Any]]` - For message deletion
  - `message_id: str` - Message to delete
  - `delete_for_everyone: bool` - Whether to delete for all participants
- `group_data: Optional[dict[str, Any]]` - For group operations
  - `thread_id: Optional[str]` - Existing group (for updates)
  - `group_name: Optional[str]` - Group name
  - `creator_number: str` - Group creator phone number
  - `participant_numbers: list[str]` - Initial or updated participants
- `participant_data: Optional[dict[str, Any]]` - For add/remove participant
  - `thread_id: str` - Group conversation ID
  - `phone_number: str` - Participant to add/remove
  - `is_admin: bool` - Admin status (add only, default: False)
- `conversation_update_data: Optional[dict[str, Any]]` - For conversation state changes
  - `thread_id: str` - Conversation to update
  - `pin: Optional[bool]` - Pin/unpin conversation
  - `mute: Optional[bool]` - Mute/unmute notifications
  - `archive: Optional[bool]` - Archive/unarchive conversation
  - `mark_all_read: Optional[bool]` - Mark all messages as read
  - `draft_message: Optional[str]` - Save draft text (None to clear)

**Methods:**
- `validate_input()` - Validates that required data for the specified action is present and well-formed
- `get_affected_entities() -> list[str]` - Returns thread_id(s) or message_id(s) affected by this input
- `get_summary() -> str` - Human-readable summary (e.g., "Send SMS from +1234567890 to +9876543210: 'Hello!'")
- `should_merge_with(other: SMSInput) -> bool` - Returns False (SMS events are discrete)

**Design Decisions:**
- **Action-based**: Single input type handles all SMS operations via action discriminator
- **Flexible phone numbers**: Supports any phone number format, but E.164 recommended
- **Thread auto-creation**: If thread_id not provided for message, creates/finds appropriate conversation
- **RCS feature detection**: Validates RCS-only features (edit, reactions) only apply to RCS messages
- **Group vs one-on-one**: Automatically determined by number of participants

### `SMSState` (models/modalities/sms_state.py)

Tracks all SMS/RCS conversations, messages, and related state.

**Attributes:**
- `modality_type: str` - Always "sms"
- `last_updated: datetime` - When state was last modified
- `update_count: int` - Number of inputs applied
- `messages: dict[str, SMSMessage]` - All messages keyed by message_id
- `conversations: dict[str, SMSConversation]` - All conversations keyed by thread_id
- `max_messages_per_conversation: int` - Message history limit per conversation (default: 10000)
- `user_phone_number: str` - The simulated user's phone number (for determining direction)

**Note**: Blocked numbers and contact-level spam flagging are managed by the Contacts modality. The SMS modality queries Contacts to check if a number is blocked before processing incoming messages. Individual messages can be flagged as spam via the `is_spam` field on `SMSMessage`.

**Methods:**
- `apply_input(input_data: SMSInput)` - Processes SMS action and updates state accordingly
  - Handles all action types: send_message, receive_message, update_delivery_status, etc.
  - Creates conversations automatically when needed
  - Enforces message history limits
  - Updates conversation metadata (last_message_at, unread_count)
- `get_snapshot() -> dict[str, Any]` - Returns complete state for API responses
  - Includes all conversations, messages, blocked numbers
  - Optionally filtered by conversation, time range, etc.
- `validate_state()` - Checks state consistency
  - Verifies all message thread_ids reference valid conversations
  - Checks participant consistency in group conversations
  - Validates message ordering within conversations
- `query(query_params: dict[str, Any]) -> dict[str, Any]` - Searches messages
  - Returns dictionary with `messages` (list of message dicts), `count`, and `query_params`
  - Supports: `thread_id`, `phone_number`, `direction`, `message_type`, `since`, `until`, `has_attachments`, `is_read`, `search_text`, `limit`
- `get_conversation(thread_id: str) -> Optional[SMSConversation]` - Retrieve specific conversation
- `get_conversation_messages(thread_id: str, limit: Optional[int]) -> list[SMSMessage]` - Get messages in conversation, ordered by timestamp
- `get_message(message_id: str) -> Optional[SMSMessage]` - Retrieve specific message
- `get_recent_conversations(limit: int, include_archived: bool) -> list[SMSConversation]` - Get most recent conversations, sorted by last_message_at
- `get_unread_count(thread_id: Optional[str]) -> int` - Get unread message count (global or per-conversation)
- `find_or_create_conversation(participants: list[str], group_name: Optional[str]) -> str` - Find existing or create new conversation, returns thread_id
- `mark_message_spam(message_id: str)` - Flag individual message as spam
- `unmark_message_spam(message_id: str)` - Remove spam flag from message

**Design Decisions:**

1. **Message Storage**:
   - Messages stored in flat dictionary keyed by message_id for fast lookup
   - Conversations maintain message_count but not message lists (queries fetch from messages dict)
   - Efficient for large message volumes and diverse query patterns

2. **Conversation Discovery**:
   - One-on-one conversations identified by sorted participant tuple
   - Group conversations require explicit thread_id or group_name
   - Prevents duplicate conversations for same participants

3. **Direction Detection**:
   - Uses `user_phone_number` to determine incoming vs outgoing
   - Message from user_phone_number = outgoing
   - Message to user_phone_number = incoming

4. **Group Management**:
   - Participants never fully removed, just marked with left_at timestamp
   - Preserves conversation history even after participants leave
   - Active participants query filters by left_at is None

5. **Read Status**:
   - Incoming messages default to unread
   - Outgoing messages default to read
   - Read status tracked per-message and aggregated per-conversation

6. **Delivery Tracking**:
   - Only outgoing messages track delivery/read receipts
   - Incoming messages don't have delivery status
   - Realistic simulation of actual SMS/RCS behavior

7. **Message History Limits**:
   - Configurable max_messages_per_conversation prevents unbounded growth
   - Oldest messages deleted when limit exceeded
   - Conversation metadata preserved even when messages pruned

8. **Blocked and Spam Handling**:
   - Blocked numbers: Managed by Contacts modality; SMS queries Contacts during apply_input to check blocked status
   - Message-level spam flags: Individual messages can be marked as spam (stored in SMSMessage.is_spam)
   - Contact-level spam: Managed by Contacts modality (future feature)
   - Blocked messages are rejected before creating SMSMessage instances
   - Spam messages are delivered but flagged for filtering in UI

## Cross-Modality Interactions

The SMS modality interacts with the future **Contacts modality** for contact-related functionality:

### Display Name Resolution
When rendering messages or conversations, display names are resolved by querying Contacts:
```python
# Pseudocode example
for message in sms_state.messages.values():
    from_name = contacts_state.get_display_name(message.from_number)
    # Fall back to phone number if not in contacts
    display_from = from_name or message.from_number
```

### Blocked Number Checking
When processing incoming messages, SMS checks if sender is blocked:
```python
# In SMSState.apply_input() for receive_message action
if contacts_state.is_blocked(from_number):
    # Reject message, don't create SMSMessage
    return
```

### Implementation Pattern
- SMS modality operates independently (can work without Contacts)
- When Contacts modality exists, SMS queries it during:
  - Message processing (blocked number check)
  - API responses (display name enrichment)
  - Contact lookup (phone number → contact info)
- This loose coupling allows modalities to evolve independently

**Future**: SimulationEngine or API layer will handle cross-modality queries transparently.

---

## API Usage Patterns

### User Receives Text Message (Simulated Event)
```json
POST /events
{
  "scheduled_time": "2024-03-15T10:30:00Z",
  "modality": "sms",
  "data": {
    "action": "receive_message",
    "message_data": {
      "from_number": "+11234567890",
      "to_numbers": ["+19876543210"],
      "body": "Hey, are we still meeting at 3pm?",
      "message_type": "sms"
    }
  }
}
```

### User Sends Reply (Agent Action)
```json
POST /events/immediate
{
  "modality": "sms",
  "data": {
    "action": "send_message",
    "message_data": {
      "from_number": "+19876543210",
      "to_numbers": ["+11234567890"],
      "body": "Yes, see you then!",
      "message_type": "sms",
      "thread_id": "existing-thread-id",
      "replied_to_message_id": "message-id-of-question"
    }
  }
}
```

### Group Message Arrives
```json
POST /events
{
  "scheduled_time": "2024-03-15T14:00:00Z",
  "modality": "sms",
  "data": {
    "action": "receive_message",
    "message_data": {
      "from_number": "+15551234567",
      "to_numbers": ["+19876543210", "+15559876543", "+15551112222"],
      "body": "Don't forget to bring snacks!",
      "message_type": "rcs",
      "thread_id": "group-thread-id"
    }
  }
}
```

### Create New Group Conversation
```json
POST /events/immediate
{
  "modality": "sms",
  "data": {
    "action": "create_group",
    "group_data": {
      "group_name": "Weekend Plans",
      "creator_number": "+19876543210",
      "participant_numbers": ["+19876543210", "+15551234567", "+15559876543"]
    }
  }
}
```

### Add Emoji Reaction (RCS)
```json
POST /events/immediate
{
  "modality": "sms",
  "data": {
    "action": "add_reaction",
    "reaction_data": {
      "message_id": "message-to-react-to",
      "phone_number": "+19876543210",
      "emoji": "👍"
    }
  }
}
```

### Mark Message as Read
```json
POST /events/immediate
{
  "modality": "sms",
  "data": {
    "action": "update_delivery_status",
    "delivery_update_data": {
      "message_id": "message-id",
      "new_status": "read",
      "timestamp": "2024-03-15T10:35:00Z"
    }
  }
}
```

### Query API Examples

**Get SMS state (all conversations and messages):**
```
GET /sms/state
```

**Query specific conversation:**
```
POST /sms/query
{
  "phone_number": "+1234567890",
  "limit": 50
}
```

**Search messages:**
```
POST /sms/query
{
  "search_text": "meeting",
  "is_read": false
}
```

**Get unread messages:**
```
POST /sms/query
{
  "is_read": false
}
```

---

## Testing Scenarios

The SMS modality enables testing various realistic scenarios:

1. **Basic Messaging**: Simple back-and-forth text conversations
2. **Group Coordination**: Multi-participant group chats with varying participation
3. **Media Sharing**: Sending/receiving photos, videos, voice messages
4. **Urgent Messages**: Testing assistant's ability to recognize and prioritize urgent texts
5. **Spam Handling**: Filtering and responding to spam/scam messages
6. **Context Switching**: Managing multiple simultaneous conversations
7. **Read Receipt Pressure**: Balancing response expectations with message priority
8. **Group Management**: Adding/removing participants, leaving groups
9. **Message Correction**: Editing mistakes (RCS) or sending corrections
10. **Missed Messages**: Handling messages received while assistant was busy
