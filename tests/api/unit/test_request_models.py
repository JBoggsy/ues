"""Unit tests for API request model validation.

This module tests that request models properly validate input data,
including required fields, type constraints, and value ranges.

Test Organization:
- Common models from api/models.py (PaginationParams, MarkItemsRequest, etc.)
- Simulation request models (StartSimulationRequest)
- Time control request models (AdvanceTimeRequest, SetTimeRequest, SetScaleRequest)
- Event request models (CreateEventRequest, ImmediateEventRequest)
- Chat request models (SendChatMessageRequest, ChatQueryRequest, etc.)
- Email request models (SendEmailRequest, EmailQueryRequest, etc.)
- SMS request models (SendSMSRequest, SMSQueryRequest, etc.)
- Calendar request models (CreateCalendarEventRequest, CalendarQueryRequest, etc.)
- Location request models (UpdateLocationRequest, LocationQueryRequest)
- Weather request models (UpdateWeatherRequest, WeatherQueryRequest)
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

# Common models from api/models.py
from api.models import (
    DateRangeParams,
    DeleteItemsRequest,
    MarkItemsRequest,
    PaginationParams,
    SortParams,
    TextSearchParams,
)

# Simulation request models
from api.routes.simulation import StartSimulationRequest

# Time control request models
from api.routes.time import AdvanceTimeRequest, SetScaleRequest, SetTimeRequest

# Event request models
from api.routes.events import CreateEventRequest, ImmediateEventRequest

# Chat request models
from api.routes.chat import (
    ChatQueryRequest,
    ClearChatRequest,
    DeleteChatMessageRequest,
    SendChatMessageRequest,
)

# Email request models
from api.routes.email import (
    EmailAttachmentRequest,
    EmailLabelRequest,
    EmailMarkRequest,
    EmailMoveRequest,
    EmailQueryRequest,
    ReceiveEmailRequest,
    SendEmailRequest,
)

# SMS request models
from api.routes.sms import (
    MessageAttachmentRequest,
    ReceiveSMSRequest,
    SendSMSRequest,
    SMSDeleteRequest,
    SMSMarkRequest,
    SMSQueryRequest,
    SMSReactRequest,
)

# Calendar request models
from api.routes.calendar import (
    CalendarQueryRequest,
    CreateCalendarEventRequest,
    DeleteCalendarEventRequest,
    UpdateCalendarEventRequest,
)

# Location request models
from api.routes.location import LocationQueryRequest, UpdateLocationRequest

# Weather request models
from api.routes.weather import UpdateWeatherRequest, WeatherQueryRequest


# =============================================================================
# Common Models (api/models.py)
# =============================================================================


class TestPaginationParams:
    """Tests for PaginationParams validation."""

    def test_default_values(self):
        """Test default values when no parameters provided."""
        params = PaginationParams()
        assert params.limit is None
        assert params.offset == 0

    def test_valid_limit(self):
        """Test valid limit values."""
        params = PaginationParams(limit=50)
        assert params.limit == 50

    def test_limit_minimum(self):
        """Test limit minimum constraint (ge=1)."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(limit=0)
        assert "limit" in str(exc_info.value)

    def test_limit_maximum(self):
        """Test limit maximum constraint (le=1000)."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(limit=1001)
        assert "limit" in str(exc_info.value)

    def test_limit_boundary_values(self):
        """Test limit at boundary values."""
        params_min = PaginationParams(limit=1)
        assert params_min.limit == 1
        
        params_max = PaginationParams(limit=1000)
        assert params_max.limit == 1000

    def test_valid_offset(self):
        """Test valid offset values."""
        params = PaginationParams(offset=100)
        assert params.offset == 100

    def test_offset_minimum(self):
        """Test offset minimum constraint (ge=0)."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(offset=-1)
        assert "offset" in str(exc_info.value)


class TestSortParams:
    """Tests for SortParams validation."""

    def test_default_values(self):
        """Test default values when no parameters provided."""
        params = SortParams()
        assert params.sort_by is None
        assert params.sort_order is None

    def test_valid_sort_by(self):
        """Test setting sort_by field."""
        params = SortParams(sort_by="created_at")
        assert params.sort_by == "created_at"

    def test_valid_sort_order_asc(self):
        """Test valid sort order 'asc'."""
        params = SortParams(sort_order="asc")
        assert params.sort_order == "asc"

    def test_valid_sort_order_desc(self):
        """Test valid sort order 'desc'."""
        params = SortParams(sort_order="desc")
        assert params.sort_order == "desc"

    def test_invalid_sort_order(self):
        """Test invalid sort order value rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SortParams(sort_order="ascending")
        assert "sort_order" in str(exc_info.value)


class TestDateRangeParams:
    """Tests for DateRangeParams validation."""

    def test_default_values(self):
        """Test default values when no parameters provided."""
        params = DateRangeParams()
        assert params.start_date is None
        assert params.end_date is None

    def test_valid_dates(self):
        """Test setting valid date values."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)
        params = DateRangeParams(start_date=start, end_date=end)
        assert params.start_date == start
        assert params.end_date == end


class TestTextSearchParams:
    """Tests for TextSearchParams validation."""

    def test_default_values(self):
        """Test default values when no parameters provided."""
        params = TextSearchParams()
        assert params.search_text is None
        assert params.search_fields is None

    def test_valid_search_text(self):
        """Test setting search text."""
        params = TextSearchParams(search_text="hello world")
        assert params.search_text == "hello world"

    def test_valid_search_fields(self):
        """Test setting search fields list."""
        params = TextSearchParams(search_fields=["title", "body", "subject"])
        assert params.search_fields == ["title", "body", "subject"]


class TestMarkItemsRequest:
    """Tests for MarkItemsRequest validation."""

    def test_valid_request(self):
        """Test valid request with required fields."""
        request = MarkItemsRequest(item_ids=["id1", "id2"], mark_value=True)
        assert request.item_ids == ["id1", "id2"]
        assert request.mark_value is True

    def test_missing_item_ids(self):
        """Test that item_ids is required."""
        with pytest.raises(ValidationError) as exc_info:
            MarkItemsRequest(mark_value=True)
        assert "item_ids" in str(exc_info.value)

    def test_missing_mark_value(self):
        """Test that mark_value is required."""
        with pytest.raises(ValidationError) as exc_info:
            MarkItemsRequest(item_ids=["id1"])
        assert "mark_value" in str(exc_info.value)

    def test_empty_item_ids_rejected(self):
        """Test that empty item_ids list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MarkItemsRequest(item_ids=[], mark_value=True)
        assert "item_ids" in str(exc_info.value)


class TestDeleteItemsRequest:
    """Tests for DeleteItemsRequest validation."""

    def test_valid_request(self):
        """Test valid request with required fields."""
        request = DeleteItemsRequest(item_ids=["id1", "id2"])
        assert request.item_ids == ["id1", "id2"]
        assert request.permanent is False  # Default value

    def test_permanent_flag(self):
        """Test setting permanent flag."""
        request = DeleteItemsRequest(item_ids=["id1"], permanent=True)
        assert request.permanent is True

    def test_missing_item_ids(self):
        """Test that item_ids is required."""
        with pytest.raises(ValidationError) as exc_info:
            DeleteItemsRequest()
        assert "item_ids" in str(exc_info.value)

    def test_empty_item_ids_rejected(self):
        """Test that empty item_ids list is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DeleteItemsRequest(item_ids=[])
        assert "item_ids" in str(exc_info.value)


# =============================================================================
# Simulation Request Models
# =============================================================================


class TestStartSimulationRequest:
    """Tests for StartSimulationRequest validation."""

    def test_default_values(self):
        """Test default values when no parameters provided."""
        request = StartSimulationRequest()
        assert request.auto_advance is False
        assert request.time_scale == 1.0

    def test_auto_advance_enabled(self):
        """Test enabling auto advance."""
        request = StartSimulationRequest(auto_advance=True)
        assert request.auto_advance is True

    def test_custom_time_scale(self):
        """Test setting custom time scale."""
        request = StartSimulationRequest(time_scale=2.5)
        assert request.time_scale == 2.5

    def test_time_scale_must_be_positive(self):
        """Test that time scale must be greater than 0."""
        with pytest.raises(ValidationError) as exc_info:
            StartSimulationRequest(time_scale=0)
        assert "time_scale" in str(exc_info.value)

    def test_negative_time_scale_rejected(self):
        """Test that negative time scale is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            StartSimulationRequest(time_scale=-1.0)
        assert "time_scale" in str(exc_info.value)

    def test_very_small_time_scale(self):
        """Test very small positive time scale accepted."""
        request = StartSimulationRequest(time_scale=0.001)
        assert request.time_scale == 0.001

    def test_very_large_time_scale(self):
        """Test very large time scale accepted."""
        request = StartSimulationRequest(time_scale=10000.0)
        assert request.time_scale == 10000.0


# =============================================================================
# Time Control Request Models
# =============================================================================


class TestAdvanceTimeRequest:
    """Tests for AdvanceTimeRequest validation."""

    def test_valid_seconds(self):
        """Test valid seconds value."""
        request = AdvanceTimeRequest(seconds=60.0)
        assert request.seconds == 60.0

    def test_missing_seconds(self):
        """Test that seconds is required."""
        with pytest.raises(ValidationError) as exc_info:
            AdvanceTimeRequest()
        assert "seconds" in str(exc_info.value)

    def test_zero_seconds_rejected(self):
        """Test that zero seconds is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AdvanceTimeRequest(seconds=0)
        assert "seconds" in str(exc_info.value)

    def test_negative_seconds_rejected(self):
        """Test that negative seconds is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            AdvanceTimeRequest(seconds=-10.0)
        assert "seconds" in str(exc_info.value)

    def test_fractional_seconds(self):
        """Test fractional seconds accepted."""
        request = AdvanceTimeRequest(seconds=0.5)
        assert request.seconds == 0.5


class TestSetTimeRequest:
    """Tests for SetTimeRequest validation."""

    def test_valid_target_time(self):
        """Test valid target time."""
        target = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        request = SetTimeRequest(target_time=target)
        assert request.target_time == target

    def test_missing_target_time(self):
        """Test that target_time is required."""
        with pytest.raises(ValidationError) as exc_info:
            SetTimeRequest()
        assert "target_time" in str(exc_info.value)

    def test_iso_string_parsing(self):
        """Test that ISO format string is parsed correctly."""
        request = SetTimeRequest(target_time="2024-06-15T12:00:00+00:00")
        assert request.target_time.year == 2024
        assert request.target_time.month == 6
        assert request.target_time.day == 15


class TestSetScaleRequest:
    """Tests for SetScaleRequest validation."""

    def test_valid_scale(self):
        """Test valid scale value."""
        request = SetScaleRequest(scale=2.0)
        assert request.scale == 2.0

    def test_missing_scale(self):
        """Test that scale is required."""
        with pytest.raises(ValidationError) as exc_info:
            SetScaleRequest()
        assert "scale" in str(exc_info.value)

    def test_zero_scale_rejected(self):
        """Test that zero scale is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SetScaleRequest(scale=0)
        assert "scale" in str(exc_info.value)

    def test_negative_scale_rejected(self):
        """Test that negative scale is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SetScaleRequest(scale=-1.0)
        assert "scale" in str(exc_info.value)

    def test_fractional_scale(self):
        """Test fractional scale accepted (slow-motion)."""
        request = SetScaleRequest(scale=0.5)
        assert request.scale == 0.5


# =============================================================================
# Event Request Models
# =============================================================================


class TestCreateEventRequest:
    """Tests for CreateEventRequest validation."""

    def test_valid_request(self):
        """Test valid request with required fields."""
        scheduled = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        request = CreateEventRequest(
            scheduled_time=scheduled,
            modality="email",
            data={"subject": "Test"},
        )
        assert request.scheduled_time == scheduled
        assert request.modality == "email"
        assert request.data == {"subject": "Test"}

    def test_default_values(self):
        """Test default values for optional fields."""
        request = CreateEventRequest(
            scheduled_time=datetime.now(timezone.utc),
            modality="email",
            data={},
        )
        assert request.priority == 50
        assert request.metadata == {}
        assert request.agent_id is None

    def test_custom_priority(self):
        """Test setting custom priority."""
        request = CreateEventRequest(
            scheduled_time=datetime.now(timezone.utc),
            modality="email",
            data={},
            priority=75,
        )
        assert request.priority == 75

    def test_priority_minimum(self):
        """Test priority minimum constraint (ge=0)."""
        request = CreateEventRequest(
            scheduled_time=datetime.now(timezone.utc),
            modality="email",
            data={},
            priority=0,
        )
        assert request.priority == 0

    def test_priority_maximum(self):
        """Test priority maximum constraint (le=100)."""
        request = CreateEventRequest(
            scheduled_time=datetime.now(timezone.utc),
            modality="email",
            data={},
            priority=100,
        )
        assert request.priority == 100

    def test_priority_below_minimum_rejected(self):
        """Test that priority below 0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CreateEventRequest(
                scheduled_time=datetime.now(timezone.utc),
                modality="email",
                data={},
                priority=-1,
            )
        assert "priority" in str(exc_info.value)

    def test_priority_above_maximum_rejected(self):
        """Test that priority above 100 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            CreateEventRequest(
                scheduled_time=datetime.now(timezone.utc),
                modality="email",
                data={},
                priority=101,
            )
        assert "priority" in str(exc_info.value)

    def test_missing_scheduled_time(self):
        """Test that scheduled_time is required."""
        with pytest.raises(ValidationError) as exc_info:
            CreateEventRequest(modality="email", data={})
        assert "scheduled_time" in str(exc_info.value)

    def test_missing_modality(self):
        """Test that modality is required."""
        with pytest.raises(ValidationError) as exc_info:
            CreateEventRequest(
                scheduled_time=datetime.now(timezone.utc),
                data={},
            )
        assert "modality" in str(exc_info.value)

    def test_missing_data(self):
        """Test that data is required."""
        with pytest.raises(ValidationError) as exc_info:
            CreateEventRequest(
                scheduled_time=datetime.now(timezone.utc),
                modality="email",
            )
        assert "data" in str(exc_info.value)


class TestImmediateEventRequest:
    """Tests for ImmediateEventRequest validation."""

    def test_valid_request(self):
        """Test valid request with required fields."""
        request = ImmediateEventRequest(
            modality="chat",
            data={"content": "Hello"},
        )
        assert request.modality == "chat"
        assert request.data == {"content": "Hello"}

    def test_missing_modality(self):
        """Test that modality is required."""
        with pytest.raises(ValidationError) as exc_info:
            ImmediateEventRequest(data={})
        assert "modality" in str(exc_info.value)

    def test_missing_data(self):
        """Test that data is required."""
        with pytest.raises(ValidationError) as exc_info:
            ImmediateEventRequest(modality="chat")
        assert "data" in str(exc_info.value)


# =============================================================================
# Chat Request Models
# =============================================================================


class TestSendChatMessageRequest:
    """Tests for SendChatMessageRequest validation."""

    def test_valid_user_message(self):
        """Test valid user message."""
        request = SendChatMessageRequest(role="user", content="Hello")
        assert request.role == "user"
        assert request.content == "Hello"
        assert request.conversation_id == "default"
        assert request.metadata == {}

    def test_valid_assistant_message(self):
        """Test valid assistant message."""
        request = SendChatMessageRequest(role="assistant", content="Hi there!")
        assert request.role == "assistant"

    def test_invalid_role_rejected(self):
        """Test that invalid role is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SendChatMessageRequest(role="system", content="Test")
        assert "role" in str(exc_info.value)

    def test_multimodal_content(self):
        """Test multimodal content (list of content blocks)."""
        content = [
            {"type": "text", "text": "Check this image"},
            {"type": "image", "url": "http://example.com/img.jpg"},
        ]
        request = SendChatMessageRequest(role="user", content=content)
        assert request.content == content

    def test_custom_conversation_id(self):
        """Test custom conversation ID."""
        request = SendChatMessageRequest(
            role="user",
            content="Hello",
            conversation_id="my-conversation",
        )
        assert request.conversation_id == "my-conversation"

    def test_missing_role(self):
        """Test that role is required."""
        with pytest.raises(ValidationError) as exc_info:
            SendChatMessageRequest(content="Hello")
        assert "role" in str(exc_info.value)

    def test_missing_content(self):
        """Test that content is required."""
        with pytest.raises(ValidationError) as exc_info:
            SendChatMessageRequest(role="user")
        assert "content" in str(exc_info.value)


class TestDeleteChatMessageRequest:
    """Tests for DeleteChatMessageRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = DeleteChatMessageRequest(message_id="msg-123")
        assert request.message_id == "msg-123"

    def test_missing_message_id(self):
        """Test that message_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            DeleteChatMessageRequest()
        assert "message_id" in str(exc_info.value)


class TestClearChatRequest:
    """Tests for ClearChatRequest validation."""

    def test_default_conversation_id(self):
        """Test default conversation ID."""
        request = ClearChatRequest()
        assert request.conversation_id == "default"

    def test_custom_conversation_id(self):
        """Test custom conversation ID."""
        request = ClearChatRequest(conversation_id="my-conv")
        assert request.conversation_id == "my-conv"


class TestChatQueryRequest:
    """Tests for ChatQueryRequest validation."""

    def test_default_values(self):
        """Test default values."""
        request = ChatQueryRequest()
        assert request.conversation_id is None
        assert request.role is None
        assert request.since is None
        assert request.until is None
        assert request.search is None
        assert request.limit is None
        assert request.offset == 0
        assert request.sort_by == "timestamp"
        assert request.sort_order == "asc"

    def test_valid_role_filter_user(self):
        """Test filtering by user role."""
        request = ChatQueryRequest(role="user")
        assert request.role == "user"

    def test_valid_role_filter_assistant(self):
        """Test filtering by assistant role."""
        request = ChatQueryRequest(role="assistant")
        assert request.role == "assistant"

    def test_invalid_role_filter_rejected(self):
        """Test that invalid role filter is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatQueryRequest(role="system")
        assert "role" in str(exc_info.value)

    def test_limit_minimum(self):
        """Test limit minimum constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ChatQueryRequest(limit=0)
        assert "limit" in str(exc_info.value)

    def test_limit_maximum(self):
        """Test limit maximum constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ChatQueryRequest(limit=1001)
        assert "limit" in str(exc_info.value)

    def test_offset_minimum(self):
        """Test offset minimum constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ChatQueryRequest(offset=-1)
        assert "offset" in str(exc_info.value)


# =============================================================================
# Email Request Models
# =============================================================================


class TestEmailAttachmentRequest:
    """Tests for EmailAttachmentRequest validation."""

    def test_valid_attachment(self):
        """Test valid attachment."""
        attachment = EmailAttachmentRequest(
            filename="doc.pdf",
            size=1024,
            mime_type="application/pdf",
        )
        assert attachment.filename == "doc.pdf"
        assert attachment.size == 1024
        assert attachment.mime_type == "application/pdf"

    def test_size_must_be_positive(self):
        """Test that size must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            EmailAttachmentRequest(
                filename="doc.pdf",
                size=0,
                mime_type="application/pdf",
            )
        assert "size" in str(exc_info.value)


class TestSendEmailRequest:
    """Tests for SendEmailRequest validation."""

    def test_valid_request(self):
        """Test valid request with required fields."""
        request = SendEmailRequest(
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test Subject",
            body_text="Hello, World!",
        )
        assert request.from_address == "sender@example.com"
        assert request.to_addresses == ["recipient@example.com"]
        assert request.subject == "Test Subject"
        assert request.body_text == "Hello, World!"

    def test_default_values(self):
        """Test default values for optional fields."""
        request = SendEmailRequest(
            from_address="sender@example.com",
            to_addresses=["recipient@example.com"],
            subject="Test",
            body_text="Hello",
        )
        assert request.cc_addresses == []
        assert request.bcc_addresses == []
        assert request.reply_to_address is None
        assert request.body_html is None
        assert request.attachments == []
        assert request.priority == "normal"

    def test_empty_to_addresses_rejected(self):
        """Test that empty to_addresses is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SendEmailRequest(
                from_address="sender@example.com",
                to_addresses=[],
                subject="Test",
                body_text="Hello",
            )
        assert "to_addresses" in str(exc_info.value)

    def test_valid_priority_levels(self):
        """Test valid priority levels."""
        for priority in ["high", "normal", "low"]:
            request = SendEmailRequest(
                from_address="sender@example.com",
                to_addresses=["recipient@example.com"],
                subject="Test",
                body_text="Hello",
                priority=priority,
            )
            assert request.priority == priority

    def test_invalid_priority_rejected(self):
        """Test that invalid priority is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SendEmailRequest(
                from_address="sender@example.com",
                to_addresses=["recipient@example.com"],
                subject="Test",
                body_text="Hello",
                priority="urgent",
            )
        assert "priority" in str(exc_info.value)


class TestEmailMarkRequest:
    """Tests for EmailMarkRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = EmailMarkRequest(message_ids=["msg-1", "msg-2"])
        assert request.message_ids == ["msg-1", "msg-2"]

    def test_empty_message_ids_rejected(self):
        """Test that empty message_ids is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmailMarkRequest(message_ids=[])
        assert "message_ids" in str(exc_info.value)


class TestEmailLabelRequest:
    """Tests for EmailLabelRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = EmailLabelRequest(
            message_ids=["msg-1"],
            labels=["important", "work"],
        )
        assert request.message_ids == ["msg-1"]
        assert request.labels == ["important", "work"]

    def test_empty_message_ids_rejected(self):
        """Test that empty message_ids is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmailLabelRequest(message_ids=[], labels=["important"])
        assert "message_ids" in str(exc_info.value)

    def test_empty_labels_rejected(self):
        """Test that empty labels is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmailLabelRequest(message_ids=["msg-1"], labels=[])
        assert "labels" in str(exc_info.value)


class TestEmailMoveRequest:
    """Tests for EmailMoveRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = EmailMoveRequest(message_ids=["msg-1"], folder="archive")
        assert request.message_ids == ["msg-1"]
        assert request.folder == "archive"

    def test_empty_message_ids_rejected(self):
        """Test that empty message_ids is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EmailMoveRequest(message_ids=[], folder="archive")
        assert "message_ids" in str(exc_info.value)


class TestEmailQueryRequest:
    """Tests for EmailQueryRequest validation."""

    def test_default_values(self):
        """Test default values."""
        request = EmailQueryRequest()
        assert request.folder is None
        assert request.is_read is None
        assert request.is_starred is None
        assert request.limit is None
        assert request.offset == 0
        assert request.sort_order == "desc"

    def test_limit_constraints(self):
        """Test limit constraints."""
        # Valid limit
        request = EmailQueryRequest(limit=50)
        assert request.limit == 50
        
        # Below minimum
        with pytest.raises(ValidationError):
            EmailQueryRequest(limit=0)
        
        # Above maximum
        with pytest.raises(ValidationError):
            EmailQueryRequest(limit=1001)


# =============================================================================
# SMS Request Models
# =============================================================================


class TestMessageAttachmentRequest:
    """Tests for MessageAttachmentRequest (SMS) validation."""

    def test_valid_attachment(self):
        """Test valid attachment."""
        attachment = MessageAttachmentRequest(
            filename="photo.jpg",
            size=2048,
            mime_type="image/jpeg",
        )
        assert attachment.filename == "photo.jpg"
        assert attachment.size == 2048
        assert attachment.mime_type == "image/jpeg"

    def test_size_must_be_positive(self):
        """Test that size must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            MessageAttachmentRequest(
                filename="photo.jpg",
                size=0,
                mime_type="image/jpeg",
            )
        assert "size" in str(exc_info.value)


class TestSendSMSRequest:
    """Tests for SendSMSRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = SendSMSRequest(
            from_number="+1234567890",
            to_numbers=["+0987654321"],
            body="Hello!",
        )
        assert request.from_number == "+1234567890"
        assert request.to_numbers == ["+0987654321"]
        assert request.body == "Hello!"
        assert request.message_type == "sms"  # Default

    def test_empty_to_numbers_rejected(self):
        """Test that empty to_numbers is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SendSMSRequest(
                from_number="+1234567890",
                to_numbers=[],
                body="Hello!",
            )
        assert "to_numbers" in str(exc_info.value)

    def test_valid_message_types(self):
        """Test valid message types."""
        for msg_type in ["sms", "rcs"]:
            request = SendSMSRequest(
                from_number="+1234567890",
                to_numbers=["+0987654321"],
                body="Hello!",
                message_type=msg_type,
            )
            assert request.message_type == msg_type


class TestSMSMarkRequest:
    """Tests for SMSMarkRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = SMSMarkRequest(message_ids=["msg-1", "msg-2"])
        assert request.message_ids == ["msg-1", "msg-2"]

    def test_empty_message_ids_rejected(self):
        """Test that empty message_ids is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SMSMarkRequest(message_ids=[])
        assert "message_ids" in str(exc_info.value)


class TestSMSDeleteRequest:
    """Tests for SMSDeleteRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = SMSDeleteRequest(message_ids=["msg-1"])
        assert request.message_ids == ["msg-1"]

    def test_empty_message_ids_rejected(self):
        """Test that empty message_ids is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SMSDeleteRequest(message_ids=[])
        assert "message_ids" in str(exc_info.value)


class TestSMSReactRequest:
    """Tests for SMSReactRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = SMSReactRequest(
            message_id="msg-1",
            phone_number="+1234567890",
            emoji="👍",
        )
        assert request.message_id == "msg-1"
        assert request.phone_number == "+1234567890"
        assert request.emoji == "👍"


class TestSMSQueryRequest:
    """Tests for SMSQueryRequest validation."""

    def test_default_values(self):
        """Test default values."""
        request = SMSQueryRequest()
        assert request.thread_id is None
        assert request.from_number is None
        assert request.to_number is None
        assert request.direction is None
        assert request.limit is None
        assert request.offset == 0

    def test_valid_direction_filters(self):
        """Test valid direction filters."""
        for direction in ["incoming", "outgoing"]:
            request = SMSQueryRequest(direction=direction)
            assert request.direction == direction


# =============================================================================
# Calendar Request Models
# =============================================================================


class TestCreateCalendarEventRequest:
    """Tests for CreateCalendarEventRequest validation."""

    def test_valid_request(self):
        """Test valid request with required fields."""
        start = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        request = CreateCalendarEventRequest(
            title="Meeting",
            start=start,
            end=end,
        )
        assert request.title == "Meeting"
        assert request.start == start
        assert request.end == end
        assert request.calendar_id == "primary"  # Default

    def test_default_values(self):
        """Test default values for optional fields."""
        start = datetime(2024, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
        request = CreateCalendarEventRequest(
            title="Meeting",
            start=start,
            end=end,
        )
        assert request.all_day is False
        assert request.timezone == "UTC"
        assert request.status == "confirmed"
        assert request.visibility == "default"


class TestUpdateCalendarEventRequest:
    """Tests for UpdateCalendarEventRequest validation."""

    def test_valid_request(self):
        """Test valid request with event_id."""
        request = UpdateCalendarEventRequest(
            event_id="evt-123",
            title="Updated Title",
        )
        assert request.event_id == "evt-123"
        assert request.title == "Updated Title"

    def test_missing_event_id(self):
        """Test that event_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateCalendarEventRequest(title="New Title")
        assert "event_id" in str(exc_info.value)


class TestDeleteCalendarEventRequest:
    """Tests for DeleteCalendarEventRequest validation."""

    def test_valid_request(self):
        """Test valid request."""
        request = DeleteCalendarEventRequest(event_id="evt-123")
        assert request.event_id == "evt-123"
        assert request.calendar_id == "primary"  # Default

    def test_missing_event_id(self):
        """Test that event_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            DeleteCalendarEventRequest()
        assert "event_id" in str(exc_info.value)


class TestCalendarQueryRequest:
    """Tests for CalendarQueryRequest validation."""

    def test_default_values(self):
        """Test default values."""
        request = CalendarQueryRequest()
        assert request.calendar_ids is None
        assert request.start is None
        assert request.end is None
        assert request.search is None
        assert request.status is None
        assert request.expand_recurring is False
        assert request.offset == 0
        assert request.sort_by == "start"
        assert request.sort_order == "asc"


# =============================================================================
# Location Request Models
# =============================================================================


class TestUpdateLocationRequest:
    """Tests for UpdateLocationRequest validation."""

    def test_valid_request(self):
        """Test valid request with coordinates."""
        request = UpdateLocationRequest(latitude=37.7749, longitude=-122.4194)
        assert request.latitude == 37.7749
        assert request.longitude == -122.4194

    def test_optional_fields(self):
        """Test optional fields."""
        request = UpdateLocationRequest(
            latitude=37.7749,
            longitude=-122.4194,
            address="San Francisco, CA",
            named_location="Office",
            altitude=100.0,
            accuracy=10.0,
            speed=0.0,
            bearing=90.0,
        )
        assert request.address == "San Francisco, CA"
        assert request.named_location == "Office"
        assert request.altitude == 100.0
        assert request.accuracy == 10.0
        assert request.speed == 0.0
        assert request.bearing == 90.0

    def test_missing_latitude(self):
        """Test that latitude is required."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateLocationRequest(longitude=-122.4194)
        assert "latitude" in str(exc_info.value)

    def test_missing_longitude(self):
        """Test that longitude is required."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateLocationRequest(latitude=37.7749)
        assert "longitude" in str(exc_info.value)


class TestLocationQueryRequest:
    """Tests for LocationQueryRequest validation."""

    def test_default_values(self):
        """Test default values."""
        request = LocationQueryRequest()
        assert request.since is None
        assert request.until is None
        assert request.named_location is None
        assert request.limit is None
        assert request.offset == 0
        assert request.include_current is True
        assert request.sort_by == "timestamp"
        assert request.sort_order == "desc"

    def test_limit_minimum(self):
        """Test limit minimum constraint."""
        with pytest.raises(ValidationError) as exc_info:
            LocationQueryRequest(limit=0)
        assert "limit" in str(exc_info.value)

    def test_offset_minimum(self):
        """Test offset minimum constraint."""
        with pytest.raises(ValidationError) as exc_info:
            LocationQueryRequest(offset=-1)
        assert "offset" in str(exc_info.value)


# =============================================================================
# Weather Request Models
# =============================================================================


class TestUpdateWeatherRequest:
    """Tests for UpdateWeatherRequest validation."""

    def test_valid_request(self):
        """Test valid request with coordinates and report."""
        # Note: WeatherReport requires complex structure, testing just coordinates
        # A more complete test would include a valid WeatherReport
        with pytest.raises(ValidationError):
            # Missing report - should fail
            UpdateWeatherRequest(latitude=37.7749, longitude=-122.4194)

    def test_missing_latitude(self):
        """Test that latitude is required."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateWeatherRequest(longitude=-122.4194, report={})
        assert "latitude" in str(exc_info.value)

    def test_missing_longitude(self):
        """Test that longitude is required."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateWeatherRequest(latitude=37.7749, report={})
        assert "longitude" in str(exc_info.value)


class TestWeatherQueryRequest:
    """Tests for WeatherQueryRequest validation."""

    def test_valid_request(self):
        """Test valid request with coordinates."""
        request = WeatherQueryRequest(lat=37.7749, lon=-122.4194)
        assert request.lat == 37.7749
        assert request.lon == -122.4194
        assert request.units == "standard"  # Default
        assert request.real is False  # Default

    def test_default_values(self):
        """Test default values for optional fields."""
        request = WeatherQueryRequest(lat=0.0, lon=0.0)
        assert request.exclude is None
        assert request.units == "standard"
        assert request.from_time is None
        assert request.to_time is None
        assert request.real is False
        assert request.limit is None
        assert request.offset == 0

    def test_valid_units(self):
        """Test valid units values."""
        for units in ["standard", "metric", "imperial"]:
            request = WeatherQueryRequest(lat=0.0, lon=0.0, units=units)
            assert request.units == units

    def test_invalid_units_rejected(self):
        """Test that invalid units is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherQueryRequest(lat=0.0, lon=0.0, units="celsius")
        assert "units" in str(exc_info.value)

    def test_missing_lat(self):
        """Test that lat is required."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherQueryRequest(lon=-122.4194)
        assert "lat" in str(exc_info.value)

    def test_missing_lon(self):
        """Test that lon is required."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherQueryRequest(lat=37.7749)
        assert "lon" in str(exc_info.value)

    def test_limit_minimum(self):
        """Test limit minimum constraint."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherQueryRequest(lat=0.0, lon=0.0, limit=0)
        assert "limit" in str(exc_info.value)

    def test_offset_minimum(self):
        """Test offset minimum constraint."""
        with pytest.raises(ValidationError) as exc_info:
            WeatherQueryRequest(lat=0.0, lon=0.0, offset=-1)
        assert "offset" in str(exc_info.value)
