"""UES API Client Library.

This module provides a type-safe Python client for interacting with the
UES (User Environment Simulator) REST API. It supports both synchronous
and asynchronous usage patterns.

Example:
    Synchronous usage::
    
        from ues.client import UESClient
        
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
    
        from ues.client import AsyncUESClient
        
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

from ues.client._events import (
    AsyncEventsClient,
    BatchCreateEventResponse,
    BatchEventRequest,
    BatchEventResult,
    BatchValidationResponse,
    BatchValidationResult,
    CancelEventResponse,
    EventListResponse,
    EventResponse,
    EventsClient,
    EventSummaryResponse,
)
from ues.client._email import (
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
from ues.client._scenario import (
    AsyncScenarioClient,
    ExportedEnvironmentData,
    ExportedEventQueueData,
    ExportedScenarioData,
    ExportedTimeState,
    ExportEnvironmentResponse,
    ExportEventsResponse,
    ExportScenarioResponse,
    LoadedScenarioMetadata,
    LoadEnvironmentResponse,
    LoadEventsResponse,
    LoadScenarioResponse,
    ScenarioClient,
    ScenarioMetadata,
)
from ues.client._sms import (
    AsyncSMSClient,
    GroupParticipant,
    MessageAttachment,
    MessageReaction,
    SMSClient,
    SMSCompactStateResponse,
    SMSConversation,
    SMSMessage,
    SMSQueryResponse,
    SMSStateResponse,
)
from ues.client._chat import (
    AsyncChatClient,
    ChatClient,
    ChatCompactStateResponse,
    ChatMessage,
    ChatQueryResponse,
    ChatStateResponse,
    ConversationMetadata,
)
from ues.client._contacts import (
    AsyncContactsClient,
    Contact,
    ContactIdentifier,
    ContactsClient,
    ContactsCompactStateResponse,
    ContactsQueryResponse,
    ContactsStateResponse,
    PostalAddress,
)
from ues.client._calendar import (
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
from ues.client._location import (
    AsyncLocationClient,
    LocationClient,
    LocationCompactStateResponse,
    LocationQueryResponse,
    LocationStateResponse,
)
from ues.client._weather import (
    AsyncWeatherClient,
    CurrentWeather,
    DailyFeelsLike,
    DailyForecast,
    DailyTemperature,
    HourlyForecast,
    MinutelyForecast,
    WeatherAlert,
    WeatherClient,
    WeatherCompactStateResponse,
    WeatherCondition,
    WeatherQueryResponse,
    WeatherReport,
    WeatherStateResponse,
)
from ues.client._environment import (
    AsyncEnvironmentClient,
    CompactSnapshotResponse,
    EnvironmentClient,
    EnvironmentStateResponse,
    ModalityListResponse,
    ModalitySummary,
)
from ues.client._webhooks import (
    AsyncWebhooksClient,
    WebhooksClient,
)
from ues.client._websocket import (
    WebSocketSubscription,
    WSEvent,
)
from ues.client.exceptions import (
    APIError,
    ConflictError,
    ConnectionError,
    NotFoundError,
    ServerError,
    TimeoutError,
    UESClientError,
    ValidationError,
)
from ues.client.models import (
    HealthResponse,
    ModalityActionResponse,
    ModalityQueryResponse,
    ModalityStateResponse,
    SimulationStatusResponse,
)
from ues.client.client import AsyncUESClient, UESClient

__all__ = [
    # Main clients
    "UESClient",
    "AsyncUESClient",
    # WebSocket support
    "WebSocketSubscription",
    "WSEvent",
    # Sub-clients (for direct use or Phase 4 integration)
    "EventsClient",
    "AsyncEventsClient",
    "EmailClient",
    "AsyncEmailClient",
    "SMSClient",
    "AsyncSMSClient",
    "ChatClient",
    "AsyncChatClient",
    "ContactsClient",
    "AsyncContactsClient",
    "CalendarClient",
    "AsyncCalendarClient",
    "LocationClient",
    "AsyncLocationClient",
    "WeatherClient",
    "AsyncWeatherClient",
    "WebhooksClient",
    "AsyncWebhooksClient",
    "ScenarioClient",
    "AsyncScenarioClient",
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
    "HealthResponse",
    "SimulationStatusResponse",
    # Response models - Events
    "EventResponse",
    "EventListResponse",
    "EventSummaryResponse",
    "CancelEventResponse",
    "BatchEventRequest",
    "BatchEventResult",
    "BatchCreateEventResponse",
    "BatchValidationResult",
    "BatchValidationResponse",
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
    "SMSCompactStateResponse",
    "SMSQueryResponse",
    "MessageAttachment",
    "MessageReaction",
    "GroupParticipant",
    # Response models - Chat
    "ChatMessage",
    "ChatStateResponse",
    "ChatCompactStateResponse",
    "ChatQueryResponse",
    "ConversationMetadata",
    # Response models - Contacts
    "Contact",
    "ContactIdentifier",
    "PostalAddress",
    "ContactsStateResponse",
    "ContactsCompactStateResponse",
    "ContactsQueryResponse",
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
    "LocationCompactStateResponse",
    "LocationQueryResponse",
    # Response models - Weather
    "WeatherStateResponse",
    "WeatherCompactStateResponse",
    "WeatherQueryResponse",
    "WeatherCondition",
    "CurrentWeather",
    "MinutelyForecast",
    "HourlyForecast",
    "DailyTemperature",
    "DailyFeelsLike",
    "DailyForecast",
    "WeatherAlert",
    "WeatherReport",
    # Response models - Environment
    "EnvironmentStateResponse",
    "EnvironmentClient",
    "AsyncEnvironmentClient",
    "CompactSnapshotResponse",
    "ModalityListResponse",
    "ModalitySummary",
    # Response models - Scenario
    "ExportedTimeState",
    "ExportedEnvironmentData",
    "ExportedEventQueueData",
    "ScenarioMetadata",
    "ExportedScenarioData",
    "ExportEnvironmentResponse",
    "ExportEventsResponse",
    "ExportScenarioResponse",
    "LoadEnvironmentResponse",
    "LoadEventsResponse",
    "LoadedScenarioMetadata",
    "LoadScenarioResponse",
]
