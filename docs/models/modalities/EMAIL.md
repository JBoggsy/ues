# Email Modality Design

The Email modality simulates a simplified email system for testing AI personal assistants. It includes the core features of modern email clients without complex infrastructure details like encryption, routing, or server protocols.

## Email Content

- **Text body**: Plain text and HTML-formatted content
- **Subject line**: Email subject
- **Attachments**: Files with metadata (filename, size, MIME type)
- **Inline images**: Images embedded in HTML body
- **Recipients**: To, CC, and BCC address lists

## Email Metadata

- **Message ID**: Unique identifier for each email
- **From address**: Sender email address
- **Reply-to address**: Optional different reply address
- **Timestamps**:
  - Sent timestamp (when originally sent)
  - Received timestamp (when arrived in inbox)
- **Threading headers**:
  - Thread ID for grouping related emails
  - In-Reply-To header (references parent message)
  - References header (full thread chain)

## Folders and Organization

- **Standard folders**: Inbox, Sent, Drafts, Trash, Spam, Archive
- **Custom labels**: Gmail-style tags/labels
- **Folder operations**: Move, copy between folders
- **Bulk operations**: Move/delete multiple emails

## Email Status and Flags

- **Read/unread status**: Track which emails have been read
- **Starred/flagged**: Mark important emails
- **Priority levels**: High, normal, low priority indicators
- **Importance markers**: Urgent flags
- **Unread counts**: Per-folder unread email counts

## Email Actions

- **Compose**: Create new email
- **Reply**: Respond to sender
- **Reply All**: Respond to all recipients
- **Forward**: Send email to new recipients
- **Save draft**: Store partially composed emails
- **Send**: Deliver email to recipients
- **Delete**: Move to trash
- **Archive**: Remove from inbox while preserving
- **Mark as spam/not spam**: Flag/unflag spam emails
- **Star/unstar**: Toggle important flag

## Threading

- **Conversation grouping**: Group related emails by thread
- **Reply context**: Include original message in replies
- **Forward markers**: Indicate forwarded content
- **Thread chronology**: Maintain message order within threads

## Search and Filtering

- **Search by**:
  - Sender address
  - Recipient address
  - Subject keywords
  - Body content
  - Date range
- **Filter by**:
  - Read/unread status
  - Has attachments
  - Folder/label
  - Starred status
  - Priority level

## Drafts

- **Save drafts**: Store incomplete emails
- **Auto-save**: Periodic draft saving
- **Edit drafts**: Modify saved drafts
- **Send drafts**: Complete and send saved drafts
- **Discard drafts**: Delete draft emails

## Features Explicitly Excluded

The following email features are **not** simulated to maintain simplicity:
- PGP/GPG encryption and signing
- S/MIME signing
- Email routing headers (Received, X-headers)
- DKIM/SPF/DMARC authentication
- IMAP/POP3/SMTP protocol details
- Email server configuration
- Bounce handling and NDRs
- Mailing list management headers
- Complex email rules/filters
- Custom headers beyond standard ones

---

## Implementation Design

### Helper Classes

#### `EmailAttachment`
Represents a file attachment with metadata.

**Attributes:**
- `filename: str` - Name of the attached file
- `size: int` - File size in bytes
- `mime_type: str` - MIME type (e.g., "application/pdf", "image/jpeg")
- `content_id: Optional[str]` - Content ID for inline images (e.g., "cid:image001")
- `attachment_id: str` - Unique identifier (auto-generated UUID)

**Methods:**
- `to_dict() -> dict[str, Any]` - Serialize to dictionary for API responses
- `is_inline() -> bool` - Check if attachment is inline (has content_id)

#### `Email`
Represents a complete email message with all metadata.

**Attributes:**
- `message_id: str` - Unique message identifier (UUID)
- `thread_id: str` - Thread identifier for conversation grouping
- `from_address: str` - Sender email address
- `to_addresses: list[str]` - Primary recipient addresses
- `cc_addresses: list[str]` - CC recipient addresses (default: empty list)
- `bcc_addresses: list[str]` - BCC recipient addresses (default: empty list)
- `reply_to_address: Optional[str]` - Reply-to address if different from sender
- `subject: str` - Email subject line
- `body_text: str` - Plain text body content
- `body_html: Optional[str]` - HTML body content (optional)
- `attachments: list[EmailAttachment]` - List of attachments (default: empty list)
- `in_reply_to: Optional[str]` - Message ID this email replies to
- `references: list[str]` - List of message IDs in thread chain
- `sent_at: datetime` - When email was originally sent (simulator time)
- `received_at: datetime` - When email arrived in inbox (simulator time)
- `is_read: bool` - Read/unread status (default: False)
- `is_starred: bool` - Starred/flagged status (default: False)
- `priority: str` - Priority level: "high", "normal", "low" (default: "normal")
- `folder: str` - Current folder location (default: "inbox")
- `labels: list[str]` - List of applied labels/tags (default: empty list)

**Methods:**
- `to_dict() -> dict[str, Any]` - Serialize to dictionary for API responses
- `mark_read()` - Set is_read to True
- `mark_unread()` - Set is_read to False
- `toggle_star()` - Toggle is_starred status
- `add_label(label: str)` - Add a label if not already present
- `remove_label(label: str)` - Remove a label if present
- `move_to_folder(folder: str)` - Change folder location

#### `EmailThread`
Represents a conversation thread grouping related emails.

**Attributes:**
- `thread_id: str` - Unique thread identifier
- `subject: str` - Thread subject (from first email)
- `participant_addresses: set[str]` - All email addresses involved
- `message_ids: list[str]` - Ordered list of message IDs in thread
- `created_at: datetime` - When thread started (first email timestamp)
- `last_message_at: datetime` - When last email was added
- `message_count: int` - Number of emails in thread
- `unread_count: int` - Number of unread emails in thread

**Methods:**
- `to_dict() -> dict[str, Any]` - Serialize to dictionary for API responses
- `add_message(message_id: str, timestamp: datetime)` - Add message to thread
- `update_unread_count(delta: int)` - Adjust unread count

### EmailInput

`EmailInput` represents different types of email-related events that modify the email state.

**Operation Types (via discriminated union or action field):**
- `receive` - New email arrives in inbox
- `send` - Send a new email (appears in Sent folder)
- `reply` - Reply to an existing email
- `reply_all` - Reply to all recipients of an email
- `forward` - Forward an email to new recipients
- `save_draft` - Save email as draft
- `send_draft` - Send a previously saved draft
- `mark_read` - Mark email(s) as read
- `mark_unread` - Mark email(s) as unread
- `star` - Star/flag email(s)
- `unstar` - Remove star from email(s)
- `move` - Move email(s) to different folder
- `delete` - Move email(s) to Trash
- `archive` - Move email(s) to Archive
- `add_label` - Add label(s) to email(s)
- `remove_label` - Remove label(s) from email(s)
- `mark_spam` - Move email(s) to Spam
- `mark_not_spam` - Move email(s) from Spam to Inbox

**Attributes (context-dependent on operation):**
- `modality_type: str` - Always "email"
- `timestamp: datetime` - When operation occurred (simulator time)
- `input_id: str` - Unique input identifier (auto-generated)
- `operation: str` - One of the operation types listed above
- `message_id: Optional[str]` - For operations on existing emails
- `message_ids: Optional[list[str]]` - For bulk operations
- `from_address: Optional[str]` - For send/receive operations
- `to_addresses: Optional[list[str]]` - For send/receive operations
- `cc_addresses: Optional[list[str]]` - For send operations (default: empty)
- `bcc_addresses: Optional[list[str]]` - For send operations (default: empty)
- `reply_to_address: Optional[str]` - For send operations
- `subject: Optional[str]` - For send/receive operations
- `body_text: Optional[str]` - For send/receive operations
- `body_html: Optional[str]` - For send/receive operations
- `attachments: Optional[list[EmailAttachment]]` - For send/receive operations
- `thread_id: Optional[str]` - For threading (auto-generated if new thread)
- `in_reply_to: Optional[str]` - For reply/forward operations
- `references: Optional[list[str]]` - For threading
- `priority: Optional[str]` - For send/receive operations (default: "normal")
- `folder: Optional[str]` - For move operations
- `labels: Optional[list[str]]` - For label operations
- `is_draft: Optional[bool]` - Whether this is a draft (default: False)

**Methods:**
- `validate_input()` - Validate email addresses, check required fields per operation
- `get_affected_entities()` - Return `[f"email:{message_id}"]` or thread ID
- `get_summary()` - Return operation description (e.g., "Received email from john@example.com: 'Meeting Tomorrow'")
- `should_merge_with()` - Return False (emails should not be merged)

### EmailState

`EmailState` tracks the complete current state of the email system.

**Attributes:**
- `modality_type: str` - Always "email"
- `last_updated: datetime` - When state was last modified
- `update_count: int` - Number of operations applied
- `emails: dict[str, Email]` - All emails indexed by message_id
- `threads: dict[str, EmailThread]` - All threads indexed by thread_id
- `folders: dict[str, list[str]]` - Folder name to list of message_ids
- `labels: dict[str, list[str]]` - Label name to list of message_ids
- `drafts: dict[str, Email]` - Draft emails indexed by message_id
- `user_email_address: str` - The simulated user's email address

**Standard Folders (initialized in state):**
- `inbox` - Incoming emails
- `sent` - Sent emails
- `drafts` - Draft emails (also tracked separately)
- `trash` - Deleted emails
- `spam` - Spam/junk emails
- `archive` - Archived emails

**Methods:**

- `apply_input(input_data: ModalityInput)` - Apply an EmailInput to modify state
  - Dispatches to operation-specific handlers based on `operation` field
  - Updates appropriate folders, labels, threads, and email objects
  - Manages threading relationships
  - Updates timestamps and counts

- `get_snapshot() -> dict[str, Any]` - Return complete state
  - Returns structure: `{folders: {...}, threads: {...}, unread_counts: {...}, total_count: N}`

- `validate_state() -> list[str]` - Check consistency
  - Verify all message_ids in folders/labels exist in emails dict
  - Verify all message_ids in threads reference valid emails
  - Check thread chronology and participant consistency
  - Validate folder assignments (each email in exactly one folder)

- `query(query_params: dict[str, Any]) -> dict[str, Any]` - Execute queries
  - **Supported query parameters:**
    - `folder: str` - Filter by folder
    - `label: str` - Filter by label
    - `is_read: bool` - Filter by read status
    - `is_starred: bool` - Filter by starred status
    - `has_attachments: bool` - Filter by attachment presence
    - `from_address: str` - Filter by sender
    - `to_address: str` - Filter by recipient
    - `subject_contains: str` - Search subject
    - `body_contains: str` - Search body
    - `date_from: datetime` - Start of date range
    - `date_to: datetime` - End of date range
    - `thread_id: str` - Get specific thread
    - `limit: int` - Max results to return
    - `offset: int` - Pagination offset
    - `sort_by: str` - Sort field ("date", "from", "subject")
    - `sort_order: str` - "asc" or "desc"
  - Returns: `{emails: [...], total_count: N, query: {...}}`

**Helper Methods:**
- `_create_thread(email: Email) -> EmailThread` - Create new thread from email
- `_add_to_thread(email: Email, thread_id: str)` - Add email to existing thread
- `_move_email(message_id: str, from_folder: str, to_folder: str)` - Internal move
- `_get_unread_count(folder: str) -> int` - Count unread in folder
- `_build_thread_references(in_reply_to: str) -> list[str]` - Build references list

### Interaction with Simulator

1. **Event Creation**: Developer or AI agent creates `SimulatorEvent` with `EmailInput` payload
2. **Event Scheduling**: Event added to `EventQueue` with `scheduled_time`
3. **Event Execution**: When simulator time reaches event time:
   - `SimulatorEvent.execute()` is called with `Environment`
   - Gets `EmailState` from environment via `environment.get_state("email")`
   - Calls `EmailState.apply_input(email_input)`
   - Email state is modified in-place
4. **API Queries**: AI assistant queries email via REST API:
   - Endpoint: `GET /email/state`
   - Returns: `EmailState.get_snapshot()`
   - Search: `POST /email/query` with query parameters
   - Returns: `EmailState.query(params)`
5. **State Persistence**: Environment snapshots save complete email state for reproducibility

### Design Decisions

**Threading Strategy**: Emails are grouped by `thread_id`. When replying/forwarding, the `in_reply_to` field links to parent message, and `references` contains full chain. Thread ID generated from first email's message ID.

**Folder Model**: Each email exists in exactly one folder at a time. Moving changes the `folder` attribute. Labels are separate from folders and emails can have multiple labels.

**Draft Handling**: Drafts stored both in `drafts` dict and in `emails` dict with `folder="drafts"`. This allows querying drafts like regular emails while maintaining separate access path.

**BCC Privacy**: BCC addresses stored on sent emails but not exposed in API responses to simulated recipients. Only the sender sees BCC list.

**Search Performance**: For small datasets (typical testing scenarios), linear search is acceptable. The `query()` method filters in Python. For larger datasets, could add indexing.

**Attachment Storage**: Attachments store only metadata (filename, size, MIME type). Actual file content not stored unless needed for specific test scenarios.

**Email Validation**: Basic email address format validation using regex. Validates @ symbol and domain structure, but not exhaustive RFC 5322 compliance.

**Thread Subject Handling**: Subject changes (Re:, Fwd: prefixes) don't break threading as thread_id is independent of subject. 
