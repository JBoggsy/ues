"""Main UES client classes.

This module provides the main entry points for interacting with the UES API:
- UESClient: Synchronous client for the UES REST API
- AsyncUESClient: Asynchronous client for the UES REST API

Both clients provide namespaced access to all API functionality through
sub-client properties (e.g., client.email, client.simulation, etc.).

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
"""

from typing import Any

from client._calendar import AsyncCalendarClient, CalendarClient
from client._chat import AsyncChatClient, ChatClient
from client._email import AsyncEmailClient, EmailClient
from client._environment import AsyncEnvironmentClient, EnvironmentClient
from client._events import AsyncEventsClient, EventsClient
from client._http import AsyncHTTPClient, HTTPClient
from client._location import AsyncLocationClient, LocationClient
from client._simulation import AsyncSimulationClient, SimulationClient
from client._sms import AsyncSMSClient, SMSClient
from client._time import AsyncTimeClient, TimeClient
from client._weather import AsyncWeatherClient, WeatherClient


class UESClient:
    """Synchronous client for the UES REST API.
    
    Provides a unified interface to all UES API endpoints through namespaced
    sub-clients. Supports context manager protocol for automatic resource cleanup.
    
    Attributes:
        base_url: The base URL of the UES server.
        timeout: Request timeout in seconds.
        retry_enabled: Whether automatic retry is enabled.
        max_retries: Maximum number of retry attempts.
    
    Example:
        Basic usage with context manager::
        
            with UESClient(base_url="http://localhost:8000") as client:
                # Start simulation
                client.simulation.start(auto_advance=False)
                
                # Send an email
                client.email.send(
                    from_address="sender@example.com",
                    to_addresses=["recipient@example.com"],
                    subject="Hello from UES",
                    body_text="This is a test email.",
                )
                
                # Advance time by 1 hour
                result = client.time.advance(seconds=3600)
                print(f"Executed {result.events_executed} events")
                
                # Query email state
                state = client.email.get_state()
                print(f"Total emails: {state.message_count}")
        
        Manual lifecycle management::
        
            client = UESClient()
            try:
                client.simulation.start()
                # ... do work ...
            finally:
                client.close()
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        retry_enabled: bool = False,
        max_retries: int = 3,
        transport: Any = None,
    ) -> None:
        """Initialize the UES client.
        
        Args:
            base_url: The base URL of the UES server (default: http://localhost:8000).
            timeout: Request timeout in seconds (default: 30.0).
            retry_enabled: Whether to automatically retry on transient failures.
                Retries on connection errors, timeouts, and HTTP 502/503/504.
                Uses exponential backoff (default: False).
            max_retries: Maximum number of retry attempts when retry is enabled
                (default: 3).
            transport: Custom HTTP transport (e.g., ASGITransport for testing).
        """
        self._base_url = base_url
        self._timeout = timeout
        self._retry_enabled = retry_enabled
        self._max_retries = max_retries
        
        # Create the shared HTTP client
        self._http = HTTPClient(
            base_url=base_url,
            timeout=timeout,
            retry_enabled=retry_enabled,
            max_retries=max_retries,
            transport=transport,
        )
        
        # Initialize sub-clients (lazy initialization via properties)
        self._time: TimeClient | None = None
        self._simulation: SimulationClient | None = None
        self._events: EventsClient | None = None
        self._environment: EnvironmentClient | None = None
        self._email: EmailClient | None = None
        self._sms: SMSClient | None = None
        self._chat: ChatClient | None = None
        self._calendar: CalendarClient | None = None
        self._location: LocationClient | None = None
        self._weather: WeatherClient | None = None
    
    def __enter__(self) -> "UESClient":
        """Enter context manager.
        
        Returns:
            The client instance.
        """
        return self
    
    def __exit__(self, *args: Any) -> None:
        """Exit context manager and close the client."""
        self.close()
    
    def close(self) -> None:
        """Close the client and release resources.
        
        This method should be called when you're done using the client
        if not using the context manager protocol.
        """
        self._http.close()
    
    # Sub-client properties (lazy initialization)
    
    @property
    def time(self) -> TimeClient:
        """Access time control endpoints (/simulator/time/*).
        
        Provides methods for:
        - Getting current simulator time state
        - Advancing time by a duration
        - Setting time to a specific datetime
        - Skipping to the next scheduled event
        - Pausing/resuming time progression
        - Setting the time scale factor
        
        Returns:
            TimeClient instance for time operations.
        """
        if self._time is None:
            self._time = TimeClient(self._http)
        return self._time
    
    @property
    def simulation(self) -> SimulationClient:
        """Access simulation control endpoints (/simulation/*).
        
        Provides methods for:
        - Starting/stopping the simulation
        - Getting simulation status
        - Resetting to initial state
        - Clearing all events and state
        - Undo/redo operations
        
        Returns:
            SimulationClient instance for simulation control.
        """
        if self._simulation is None:
            self._simulation = SimulationClient(self._http)
        return self._simulation
    
    @property
    def events(self) -> EventsClient:
        """Access event management endpoints (/events/*).
        
        Provides methods for:
        - Listing scheduled events
        - Creating new events (scheduled or immediate)
        - Getting event details
        - Cancelling events
        - Getting next pending event
        - Getting event queue summary
        
        Returns:
            EventsClient instance for event management.
        """
        if self._events is None:
            self._events = EventsClient(self._http)
        return self._events
    
    @property
    def environment(self) -> EnvironmentClient:
        """Access environment state endpoints (/environment/*).
        
        Provides methods for:
        - Getting complete environment state
        - Listing available modalities
        - Getting specific modality state
        - Querying modality data
        - Validating environment configuration
        
        Returns:
            EnvironmentClient instance for environment operations.
        """
        if self._environment is None:
            self._environment = EnvironmentClient(self._http)
        return self._environment
    
    @property
    def email(self) -> EmailClient:
        """Access email modality endpoints (/email/*).
        
        Provides methods for:
        - Getting email state (inbox, sent, etc.)
        - Querying emails with filters
        - Sending/receiving emails
        - Marking as read/unread, starred/unstarred
        - Moving, archiving, deleting emails
        - Managing labels
        
        Returns:
            EmailClient instance for email operations.
        """
        if self._email is None:
            self._email = EmailClient(self._http)
        return self._email
    
    @property
    def sms(self) -> SMSClient:
        """Access SMS/RCS modality endpoints (/sms/*).
        
        Provides methods for:
        - Getting SMS conversation state
        - Querying messages with filters
        - Sending/receiving SMS and RCS messages
        - Marking as read/unread
        - Deleting messages
        - Adding reactions (RCS)
        
        Returns:
            SMSClient instance for SMS operations.
        """
        if self._sms is None:
            self._sms = SMSClient(self._http)
        return self._sms
    
    @property
    def chat(self) -> ChatClient:
        """Access chat modality endpoints (/chat/*).
        
        Provides methods for:
        - Getting chat conversation state
        - Querying messages with filters
        - Sending messages (user or assistant)
        - Deleting messages
        - Clearing conversations
        
        Returns:
            ChatClient instance for chat operations.
        """
        if self._chat is None:
            self._chat = ChatClient(self._http)
        return self._chat
    
    @property
    def calendar(self) -> CalendarClient:
        """Access calendar modality endpoints (/calendar/*).
        
        Provides methods for:
        - Getting calendar state
        - Querying events with filters
        - Creating new events (one-time or recurring)
        - Updating events
        - Deleting events
        
        Returns:
            CalendarClient instance for calendar operations.
        """
        if self._calendar is None:
            self._calendar = CalendarClient(self._http)
        return self._calendar
    
    @property
    def location(self) -> LocationClient:
        """Access location modality endpoints (/location/*).
        
        Provides methods for:
        - Getting current location state
        - Querying location history
        - Updating user location
        
        Returns:
            LocationClient instance for location operations.
        """
        if self._location is None:
            self._location = LocationClient(self._http)
        return self._location
    
    @property
    def weather(self) -> WeatherClient:
        """Access weather modality endpoints (/weather/*).
        
        Provides methods for:
        - Getting weather state for all locations
        - Querying weather data for specific locations
        - Updating weather conditions
        
        Returns:
            WeatherClient instance for weather operations.
        """
        if self._weather is None:
            self._weather = WeatherClient(self._http)
        return self._weather


class AsyncUESClient:
    """Asynchronous client for the UES REST API.
    
    Provides a unified interface to all UES API endpoints through namespaced
    sub-clients. All methods are asynchronous. Supports async context manager
    protocol for automatic resource cleanup.
    
    Attributes:
        base_url: The base URL of the UES server.
        timeout: Request timeout in seconds.
        retry_enabled: Whether automatic retry is enabled.
        max_retries: Maximum number of retry attempts.
    
    Example:
        Basic usage with async context manager::
        
            async with AsyncUESClient(base_url="http://localhost:8000") as client:
                # Start simulation
                await client.simulation.start(auto_advance=False)
                
                # Send multiple emails concurrently
                import asyncio
                await asyncio.gather(
                    client.email.send(
                        from_address="sender@example.com",
                        to_addresses=["a@example.com"],
                        subject="Email 1",
                        body_text="...",
                    ),
                    client.email.send(
                        from_address="sender@example.com",
                        to_addresses=["b@example.com"],
                        subject="Email 2",
                        body_text="...",
                    ),
                )
                
                # Get simulation status
                status = await client.simulation.status()
                print(f"Pending events: {status.pending_events}")
        
        Manual lifecycle management::
        
            client = AsyncUESClient()
            try:
                await client.simulation.start()
                # ... do work ...
            finally:
                await client.close()
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
        retry_enabled: bool = False,
        max_retries: int = 3,
        transport: Any = None,
    ) -> None:
        """Initialize the async UES client.
        
        Args:
            base_url: The base URL of the UES server (default: http://localhost:8000).
            timeout: Request timeout in seconds (default: 30.0).
            retry_enabled: Whether to automatically retry on transient failures.
                Retries on connection errors, timeouts, and HTTP 502/503/504.
                Uses exponential backoff (default: False).
            max_retries: Maximum number of retry attempts when retry is enabled
                (default: 3).
            transport: Custom HTTP transport (e.g., ASGITransport for testing).
        """
        self._base_url = base_url
        self._timeout = timeout
        self._retry_enabled = retry_enabled
        self._max_retries = max_retries
        
        # Create the shared async HTTP client
        self._http = AsyncHTTPClient(
            base_url=base_url,
            timeout=timeout,
            retry_enabled=retry_enabled,
            max_retries=max_retries,
            transport=transport,
        )
        
        # Initialize sub-clients (lazy initialization via properties)
        self._time: AsyncTimeClient | None = None
        self._simulation: AsyncSimulationClient | None = None
        self._events: AsyncEventsClient | None = None
        self._environment: AsyncEnvironmentClient | None = None
        self._email: AsyncEmailClient | None = None
        self._sms: AsyncSMSClient | None = None
        self._chat: AsyncChatClient | None = None
        self._calendar: AsyncCalendarClient | None = None
        self._location: AsyncLocationClient | None = None
        self._weather: AsyncWeatherClient | None = None
    
    async def __aenter__(self) -> "AsyncUESClient":
        """Enter async context manager.
        
        Returns:
            The client instance.
        """
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager and close the client."""
        await self.close()
    
    async def close(self) -> None:
        """Close the client and release resources.
        
        This method should be called when you're done using the client
        if not using the async context manager protocol.
        """
        await self._http.close()
    
    # Sub-client properties (lazy initialization)
    
    @property
    def time(self) -> AsyncTimeClient:
        """Access time control endpoints (/simulator/time/*).
        
        Provides async methods for:
        - Getting current simulator time state
        - Advancing time by a duration
        - Setting time to a specific datetime
        - Skipping to the next scheduled event
        - Pausing/resuming time progression
        - Setting the time scale factor
        
        Returns:
            AsyncTimeClient instance for time operations.
        """
        if self._time is None:
            self._time = AsyncTimeClient(self._http)
        return self._time
    
    @property
    def simulation(self) -> AsyncSimulationClient:
        """Access simulation control endpoints (/simulation/*).
        
        Provides async methods for:
        - Starting/stopping the simulation
        - Getting simulation status
        - Resetting to initial state
        - Clearing all events and state
        - Undo/redo operations
        
        Returns:
            AsyncSimulationClient instance for simulation control.
        """
        if self._simulation is None:
            self._simulation = AsyncSimulationClient(self._http)
        return self._simulation
    
    @property
    def events(self) -> AsyncEventsClient:
        """Access event management endpoints (/events/*).
        
        Provides async methods for:
        - Listing scheduled events
        - Creating new events (scheduled or immediate)
        - Getting event details
        - Cancelling events
        - Getting next pending event
        - Getting event queue summary
        
        Returns:
            AsyncEventsClient instance for event management.
        """
        if self._events is None:
            self._events = AsyncEventsClient(self._http)
        return self._events
    
    @property
    def environment(self) -> AsyncEnvironmentClient:
        """Access environment state endpoints (/environment/*).
        
        Provides async methods for:
        - Getting complete environment state
        - Listing available modalities
        - Getting specific modality state
        - Querying modality data
        - Validating environment configuration
        
        Returns:
            AsyncEnvironmentClient instance for environment operations.
        """
        if self._environment is None:
            self._environment = AsyncEnvironmentClient(self._http)
        return self._environment
    
    @property
    def email(self) -> AsyncEmailClient:
        """Access email modality endpoints (/email/*).
        
        Provides async methods for:
        - Getting email state (inbox, sent, etc.)
        - Querying emails with filters
        - Sending/receiving emails
        - Marking as read/unread, starred/unstarred
        - Moving, archiving, deleting emails
        - Managing labels
        
        Returns:
            AsyncEmailClient instance for email operations.
        """
        if self._email is None:
            self._email = AsyncEmailClient(self._http)
        return self._email
    
    @property
    def sms(self) -> AsyncSMSClient:
        """Access SMS/RCS modality endpoints (/sms/*).
        
        Provides async methods for:
        - Getting SMS conversation state
        - Querying messages with filters
        - Sending/receiving SMS and RCS messages
        - Marking as read/unread
        - Deleting messages
        - Adding reactions (RCS)
        
        Returns:
            AsyncSMSClient instance for SMS operations.
        """
        if self._sms is None:
            self._sms = AsyncSMSClient(self._http)
        return self._sms
    
    @property
    def chat(self) -> AsyncChatClient:
        """Access chat modality endpoints (/chat/*).
        
        Provides async methods for:
        - Getting chat conversation state
        - Querying messages with filters
        - Sending messages (user or assistant)
        - Deleting messages
        - Clearing conversations
        
        Returns:
            AsyncChatClient instance for chat operations.
        """
        if self._chat is None:
            self._chat = AsyncChatClient(self._http)
        return self._chat
    
    @property
    def calendar(self) -> AsyncCalendarClient:
        """Access calendar modality endpoints (/calendar/*).
        
        Provides async methods for:
        - Getting calendar state
        - Querying events with filters
        - Creating new events (one-time or recurring)
        - Updating events
        - Deleting events
        
        Returns:
            AsyncCalendarClient instance for calendar operations.
        """
        if self._calendar is None:
            self._calendar = AsyncCalendarClient(self._http)
        return self._calendar
    
    @property
    def location(self) -> AsyncLocationClient:
        """Access location modality endpoints (/location/*).
        
        Provides async methods for:
        - Getting current location state
        - Querying location history
        - Updating user location
        
        Returns:
            AsyncLocationClient instance for location operations.
        """
        if self._location is None:
            self._location = AsyncLocationClient(self._http)
        return self._location
    
    @property
    def weather(self) -> AsyncWeatherClient:
        """Access weather modality endpoints (/weather/*).
        
        Provides async methods for:
        - Getting weather state for all locations
        - Querying weather data for specific locations
        - Updating weather conditions
        
        Returns:
            AsyncWeatherClient instance for weather operations.
        """
        if self._weather is None:
            self._weather = AsyncWeatherClient(self._http)
        return self._weather
