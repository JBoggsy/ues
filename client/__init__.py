"""UES API Client Library.

This module provides a type-safe Python client for interacting with the
UES (User Environment Simulator) REST API. It supports both synchronous
and asynchronous usage patterns.

Example:
    Synchronous usage::
    
        from client import UESClient
        
        with UESClient(base_url="http://localhost:8000") as client:
            client.simulation.start()
            client.email.send(
                from_address="user@example.com",
                to_addresses=["recipient@example.com"],
                subject="Hello",
                body_text="Test message",
            )
            state = client.email.get_state()
    
    Asynchronous usage::
    
        from client import AsyncUESClient
        
        async with AsyncUESClient() as client:
            await client.simulation.start()
            await client.email.send(...)

Exports:
    UESClient: Synchronous client for the UES REST API.
    AsyncUESClient: Asynchronous client for the UES REST API.
    
    Exceptions:
        UESClientError: Base exception for all client errors.
        ConnectionError: Failed to connect to the server.
        TimeoutError: Request timed out.
        APIError: Server returned an error response.
        ValidationError: Request validation failed (HTTP 422).
        NotFoundError: Resource not found (HTTP 404).
        ConflictError: State conflict (HTTP 409).
        ServerError: Server-side error (HTTP 5xx).
"""

from client._email import (
    AsyncEmailClient,
    Email,
    EmailAttachment,
    EmailClient,
    EmailQueryResponse,
    EmailStateResponse,
    EmailSummary,
    EmailSummaryStateResponse,
    EmailThread,
)
from client._sms import (
    AsyncSMSClient,
    GroupParticipant,
    MessageAttachment,
    MessageReaction,
    SMSClient,
    SMSConversation,
    SMSMessage,
    SMSQueryResponse,
    SMSStateResponse,
)
from client._chat import (
    AsyncChatClient,
    ChatClient,
    ChatMessage,
    ChatQueryResponse,
    ChatStateResponse,
    ConversationMetadata,
)
from client._calendar import (
    AsyncCalendarClient,
    Attachment,
    Attendee,
    CalendarClient,
    CalendarEvent,
    CalendarQueryResponse,
    CalendarStateResponse,
    RecurrenceRule,
    Reminder,
)
from client._location import (
    AsyncLocationClient,
    LocationClient,
    LocationQueryResponse,
    LocationStateResponse,
)
from client._weather import (
    AsyncWeatherClient,
    WeatherClient,
    WeatherQueryResponse,
    WeatherStateResponse,
)
from client.exceptions import (
    APIError,
    ConflictError,
    ConnectionError,
    NotFoundError,
    ServerError,
    TimeoutError,
    UESClientError,
    ValidationError,
)
from client.models import (
    CancelEventResponse,
    EventSummaryResponse,
    HealthResponse,
    ModalityActionResponse,
    ModalityQueryResponse,
    ModalityStateResponse,
    SimulationStatusResponse,
)
from client.client import AsyncUESClient, UESClient

__all__ = [
    # Main clients
    "UESClient",
    "AsyncUESClient",
    # Sub-clients (for direct use or Phase 4 integration)
    "EmailClient",
    "AsyncEmailClient",
    "SMSClient",
    "AsyncSMSClient",
    "ChatClient",
    "AsyncChatClient",
    "CalendarClient",
    "AsyncCalendarClient",
    "LocationClient",
    "AsyncLocationClient",
    "WeatherClient",
    "AsyncWeatherClient",
    # Exceptions
    "UESClientError",
    "ConnectionError",
    "TimeoutError",
    "APIError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "ServerError",
    # Response models - General
    "ModalityStateResponse",
    "ModalityActionResponse",
    "ModalityQueryResponse",
    "CancelEventResponse",
    "EventSummaryResponse",
    "HealthResponse",
    "SimulationStatusResponse",
    # Response models - Email
    "Email",
    "EmailAttachment",
    "EmailThread",
    "EmailSummary",
    "EmailStateResponse",
    "EmailSummaryStateResponse",
    "EmailQueryResponse",
    # Response models - SMS
    "SMSMessage",
    "SMSConversation",
    "SMSStateResponse",
    "SMSQueryResponse",
    "MessageAttachment",
    "MessageReaction",
    "GroupParticipant",
    # Response models - Chat
    "ChatMessage",
    "ChatStateResponse",
    "ChatQueryResponse",
    "ConversationMetadata",
    # Response models - Calendar
    "CalendarClient",
    "AsyncCalendarClient",
    "CalendarEvent",
    "CalendarStateResponse",
    "CalendarQueryResponse",
    "Attendee",
    "Reminder",
    "Attachment",
    "RecurrenceRule",
    # Response models - Location
    "LocationStateResponse",
    "LocationQueryResponse",
    # Response models - Weather
    "WeatherStateResponse",
    "WeatherQueryResponse",
]
