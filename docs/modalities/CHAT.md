# Chat Modality Design

The chat modality represents direct text-based interactions between the user and the assistant,
generally initiated by the user. 

## Data Model Design

### Core Classes

#### `ChatInput` (models/modalities/chat_input.py)

The event payload for a new chat message from either the user or the assistant.

**Attributes:**
- `modality_type`: Always "chat"
- `timestamp`: When this message was sent (simulator time)
- `input_id`: Unique identifier for this message
- `role`: Message sender role - "user" or "assistant"
- `content`: Message content (text, or multimodal content structure)
- `message_id`: Optional explicit message ID (auto-generated if not provided)
- `conversation_id`: Optional conversation/thread identifier for multi-conversation support
- `metadata`: Optional dictionary for extensibility (token count, model info, etc.)

**Content Structure (Multimodal Ready):**
The `content` field uses a flexible structure that supports both simple text and future multimodal content:
- **Simple text**: `content` is a string (e.g., `"Hello, how can I help?"`)
- **Multimodal**: `content` is a list of content blocks, each with a `type` field:
  - `{"type": "text", "text": "Here's an image:"}` 
  - `{"type": "image", "source": "url", "url": "https://..."}` (future)
  - `{"type": "audio", "source": "base64", "data": "..."}` (future)
  - `{"type": "video", "source": "url", "url": "https://..."}` (future)

This design matches common LLM API patterns (Anthropic, OpenAI) for easy integration.

**Methods:**
- `validate_input()`: Validates role, content structure, and conversation_id consistency
- `get_affected_entities()`: Returns conversation_id if set, otherwise "default_conversation"
- `get_summary()`: Human-readable summary (e.g., "User: 'What's the weather?' " or "Assistant: 'It's sunny today'")
- `should_merge_with()`: Returns False (each message is distinct)

**Design Decisions:**
- **Role-based**: Uses "user"/"assistant" roles like standard LLM APIs for familiarity
- **Multimodal ready**: Content structure supports future expansion without breaking changes
- **Flexible IDs**: Auto-generates message_id if not provided, supports explicit IDs for replicability
- **Multi-conversation**: Conversation_id enables multiple simultaneous chat threads (future use case)

#### `ChatState` (models/modalities/chat_state.py)

Tracks the complete conversation history and current state of chat interactions.

**Attributes:**
- `modality_type`: Always "chat"
- `last_updated`: When state was last modified
- `update_count`: Number of messages added
- `messages`: List of `ChatMessage` objects (ordered by timestamp)
- `conversations`: Dict mapping conversation_id to `ConversationMetadata`
- `max_history_size`: Maximum messages to retain per conversation (default: 1000)
- `default_conversation_id`: ID for default conversation (default: "default")

**Helper Class - `ChatMessage`:**
Simple wrapper for storing message data in state:
- `message_id`: Unique message identifier
- `conversation_id`: Which conversation this belongs to
- `role`: "user" or "assistant"
- `content`: Message content (string or multimodal structure)
- `timestamp`: When message was sent (simulator time)
- `metadata`: Optional additional data

**Helper Class - `ConversationMetadata`:**
Tracks metadata for each conversation:
- `conversation_id`: Conversation identifier
- `created_at`: When conversation started
- `last_message_at`: When last message was sent
- `message_count`: Number of messages in this conversation
- `participant_roles`: Set of roles that have participated ("user", "assistant")

**Methods:**
- `apply_input(input_data)`: Adds message to appropriate conversation, manages history limits
- `get_snapshot()`: Returns all conversations and messages for API responses
- `validate_state()`: Checks message ordering, conversation consistency, history limits
- `query(query_params)`: Filters messages by conversation, role, time range, content search
  - Supports: `conversation_id`, `role`, `since`, `until`, `limit`, `search` (text search in content)
- `get_conversation(conversation_id)`: Returns all messages in a specific conversation
- `get_recent_messages(limit, conversation_id)`: Returns most recent N messages
- `get_message_by_id(message_id)`: Retrieves specific message

**Design Decisions:**

1. **Message List vs Conversation Tree**: 
   - Uses flat message list with conversation_id grouping
   - Simple for most use cases, extensible to threads/branches later
   - Efficient chronological ordering and queries

2. **History Management**:
   - Configurable per-conversation history limits
   - Old messages removed when limit exceeded
   - Preserves conversation metadata even when messages pruned

3. **Multi-Conversation Support**:
   - Single state tracks multiple concurrent conversations
   - Useful for testing agents handling multiple users or contexts
   - Default conversation for simple single-thread use case

4. **Multimodal Content Storage**:
   - Content stored as-is (string or structured data)
   - No special handling needed until querying/display
   - Future-proof for images, audio, video without schema changes

5. **Turn Management**:
   - No explicit "turn" tracking (not needed for async chat)
   - Can be derived from message order if needed
   - Agents can send multiple messages without waiting (realistic)

6. **Agent Action Integration**:
   - Assistant messages submitted via `POST /events/immediate` or `POST /modalities/chat/submit`
   - Creates `ChatInput` with `role="assistant"`
   - Applied to `ChatState` via normal event pipeline
   - Complete conversation log captured in event history

## API Usage Patterns

### User Sends Message (Simulated Event)
```
POST /events
{
  "scheduled_time": "2024-03-15T10:30:00Z",
  "modality": "chat",
  "data": {
    "role": "user",
    "content": "What's the weather today?"
  }
}
```

### Agent Responds (Immediate Action)
```
POST /modalities/chat/submit
{
  "role": "assistant",
  "content": "Based on the current weather data, it's sunny and 72°F."
}
```
OR equivalently:
```
POST /events/immediate
{
  "modality": "chat",
  "data": {
    "role": "assistant", 
    "content": "Based on the current weather data, it's sunny and 72°F."
  }
}
```

### Query Conversation History
```
POST /environment/modalities/chat/query
{
  "conversation_id": "default",
  "limit": 10
}
```

### Future Multimodal Message
```
POST /modalities/chat/submit
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What's in this image?"},
    {"type": "image", "source": "url", "url": "https://example.com/image.jpg"}
  ]
}
```

## Implementation Notes

### Content Type Handling
- Accept both string and list formats for `content`
- Validate list format has proper `type` fields
- Store as-is without processing (process at display/query time)

### Message Ordering
- Messages ordered by timestamp within each conversation
- Ties broken by input_id (lexicographic)
- Query methods return chronologically ordered results

### Performance Considerations
- Index messages by conversation_id for fast conversation queries
- Index by message_id for fast lookups
- Consider memory limits with large conversation histories (configurable max_history_size)

### Testing Considerations
- Test simple text messages (most common case)
- Test message ordering with concurrent events
- Test history limit enforcement
- Test multi-conversation isolation
- Test query filtering (role, time range, search)
- Mock multimodal content structure for future compatibility 