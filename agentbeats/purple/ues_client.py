"""Tracked UES client wrapper for Purple Agents.

This module provides TrackedAsyncUESClient, a wrapper around AsyncUESClient
that automatically tracks actions in the AssessmentContext. This eliminates
the need to manually call context.record_action() after each UES API call.

Example:
    Using the tracked client::

        from agentbeats.purple import AssessmentContext, TrackedAsyncUESClient

        # Create context (normally from assessment_start)
        context = AssessmentContext(
            assessment_id="test",
            ues_url="http://localhost:8000",
            api_key="key",
            current_time=datetime.now(timezone.utc),
        )

        # Create tracked client
        async with TrackedAsyncUESClient(context) as ues:
            # Actions are automatically tracked
            await ues.email.send(...)  # context.actions_this_turn = 1
            await ues.email.archive([...])  # context.actions_this_turn = 2

            # Read-only operations are NOT tracked
            state = await ues.email.get_state()  # still 2

        # Check action count
        print(context.actions_this_turn)  # 2
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from client import AsyncUESClient

if TYPE_CHECKING:
    from agentbeats.purple.context import AssessmentContext
    from client._calendar import AsyncCalendarClient
    from client._chat import AsyncChatClient
    from client._email import AsyncEmailClient
    from client._location import AsyncLocationClient
    from client._sms import AsyncSMSClient
    from client._weather import AsyncWeatherClient


T = TypeVar("T")


# Methods that count as user actions (write operations)
# Read operations (get_state, query) are NOT tracked
_EMAIL_ACTIONS = frozenset({
    "send",
    "read",
    "unread",
    "star",
    "unstar",
    "archive",
    "delete",
    "move",
    "add_label",
    "remove_label",
})

_SMS_ACTIONS = frozenset({
    "send",
    "read",
    "unread",
    "delete",
    "react",
})

_CHAT_ACTIONS = frozenset({
    "send",
    "delete",
    "clear",
})

_CALENDAR_ACTIONS = frozenset({
    "create",
    "update",
    "delete",
    "rsvp",
})

_LOCATION_ACTIONS = frozenset({
    "update",
})

_WEATHER_ACTIONS = frozenset({
    "update",
})


def _create_tracking_wrapper(
    method: Callable[..., T],
    context: "AssessmentContext",
) -> Callable[..., T]:
    """Create a wrapper that tracks the action after execution.

    Args:
        method: The async method to wrap.
        context: The assessment context to record actions in.

    Returns:
        A wrapped method that calls context.record_action() after success.
    """
    @functools.wraps(method)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        result = await method(*args, **kwargs)
        context.record_action()
        return result

    return wrapper


class TrackedSubClient:
    """Base class for tracked sub-client wrappers.

    Wraps a sub-client (e.g., email, sms) and automatically tracks
    action methods while passing through read-only methods unchanged.
    """

    def __init__(
        self,
        wrapped: Any,
        context: "AssessmentContext",
        action_methods: frozenset[str],
    ) -> None:
        """Initialize the tracked sub-client.

        Args:
            wrapped: The underlying sub-client to wrap.
            context: The assessment context for action tracking.
            action_methods: Set of method names that count as actions.
        """
        self._wrapped = wrapped
        self._context = context
        self._action_methods = action_methods

    def __getattr__(self, name: str) -> Any:
        """Get an attribute from the wrapped client.

        If the attribute is an action method, wrap it with tracking.
        Otherwise, return the attribute unchanged.

        Args:
            name: The attribute name.

        Returns:
            The attribute, possibly wrapped for tracking.
        """
        attr = getattr(self._wrapped, name)
        if name in self._action_methods and callable(attr):
            return _create_tracking_wrapper(attr, self._context)
        return attr


class TrackedEmailClient(TrackedSubClient):
    """Tracked wrapper for AsyncEmailClient.

    Automatically records actions for write operations:
    - send, read, unread, star, unstar
    - archive, delete, move
    - add_label, remove_label

    Read operations (get_state, query) are NOT tracked.
    """

    def __init__(
        self,
        wrapped: "AsyncEmailClient",
        context: "AssessmentContext",
    ) -> None:
        """Initialize the tracked email client.

        Args:
            wrapped: The underlying AsyncEmailClient.
            context: The assessment context for action tracking.
        """
        super().__init__(wrapped, context, _EMAIL_ACTIONS)


class TrackedSMSClient(TrackedSubClient):
    """Tracked wrapper for AsyncSMSClient.

    Automatically records actions for write operations:
    - send, read, unread, delete, react

    Read operations (get_state, query) are NOT tracked.
    """

    def __init__(
        self,
        wrapped: "AsyncSMSClient",
        context: "AssessmentContext",
    ) -> None:
        """Initialize the tracked SMS client.

        Args:
            wrapped: The underlying AsyncSMSClient.
            context: The assessment context for action tracking.
        """
        super().__init__(wrapped, context, _SMS_ACTIONS)


class TrackedChatClient(TrackedSubClient):
    """Tracked wrapper for AsyncChatClient.

    Automatically records actions for write operations:
    - send, delete, clear

    Read operations (get_state, query) are NOT tracked.
    """

    def __init__(
        self,
        wrapped: "AsyncChatClient",
        context: "AssessmentContext",
    ) -> None:
        """Initialize the tracked chat client.

        Args:
            wrapped: The underlying AsyncChatClient.
            context: The assessment context for action tracking.
        """
        super().__init__(wrapped, context, _CHAT_ACTIONS)


class TrackedCalendarClient(TrackedSubClient):
    """Tracked wrapper for AsyncCalendarClient.

    Automatically records actions for write operations:
    - create, update, delete, rsvp

    Read operations (get_state, query) are NOT tracked.
    """

    def __init__(
        self,
        wrapped: "AsyncCalendarClient",
        context: "AssessmentContext",
    ) -> None:
        """Initialize the tracked calendar client.

        Args:
            wrapped: The underlying AsyncCalendarClient.
            context: The assessment context for action tracking.
        """
        super().__init__(wrapped, context, _CALENDAR_ACTIONS)


class TrackedLocationClient(TrackedSubClient):
    """Tracked wrapper for AsyncLocationClient.

    Automatically records actions for write operations:
    - update

    Read operations (get_state, query) are NOT tracked.
    """

    def __init__(
        self,
        wrapped: "AsyncLocationClient",
        context: "AssessmentContext",
    ) -> None:
        """Initialize the tracked location client.

        Args:
            wrapped: The underlying AsyncLocationClient.
            context: The assessment context for action tracking.
        """
        super().__init__(wrapped, context, _LOCATION_ACTIONS)


class TrackedWeatherClient(TrackedSubClient):
    """Tracked wrapper for AsyncWeatherClient.

    Automatically records actions for write operations:
    - update

    Read operations (get_state, query) are NOT tracked.
    """

    def __init__(
        self,
        wrapped: "AsyncWeatherClient",
        context: "AssessmentContext",
    ) -> None:
        """Initialize the tracked weather client.

        Args:
            wrapped: The underlying AsyncWeatherClient.
            context: The assessment context for action tracking.
        """
        super().__init__(wrapped, context, _WEATHER_ACTIONS)


class TrackedAsyncUESClient:
    """Async UES client wrapper with automatic action tracking.

    This class wraps AsyncUESClient and automatically tracks user actions
    in the provided AssessmentContext. Action methods (send, create, etc.)
    are tracked, while read methods (get_state, query) are not.

    This eliminates the need to manually call context.record_action() after
    each UES API call, reducing boilerplate and preventing tracking errors.

    Attributes:
        email: Tracked email client with automatic action counting.
        sms: Tracked SMS client with automatic action counting.
        chat: Tracked chat client with automatic action counting.
        calendar: Tracked calendar client with automatic action counting.
        location: Tracked location client with automatic action counting.
        weather: Tracked weather client with automatic action counting.
        time: Untracked time client (read-only).

    Example:
        Using with assessment context::

            context = AssessmentContext(...)
            async with TrackedAsyncUESClient(context) as ues:
                # This automatically calls context.record_action()
                await ues.email.send(
                    from_address="me@example.com",
                    to_addresses=["you@example.com"],
                    subject="Hello",
                    body_text="Test",
                )

                # This does NOT track (read operation)
                state = await ues.email.get_state()

            print(context.actions_this_turn)  # 1
    """

    def __init__(self, context: "AssessmentContext") -> None:
        """Initialize the tracked UES client.

        Creates an AsyncUESClient configured with the UES URL and API key
        from the assessment context.

        Args:
            context: The assessment context containing UES connection info
                and for tracking actions.
        """
        self._context = context
        self._client = AsyncUESClient(
            base_url=context.ues_url,
            api_key=context.api_key,
        )
        
        # Lazily initialized tracked sub-clients
        self._email: TrackedEmailClient | None = None
        self._sms: TrackedSMSClient | None = None
        self._chat: TrackedChatClient | None = None
        self._calendar: TrackedCalendarClient | None = None
        self._location: TrackedLocationClient | None = None
        self._weather: TrackedWeatherClient | None = None

    async def __aenter__(self) -> "TrackedAsyncUESClient":
        """Enter async context manager.

        Returns:
            Self for use in async with statements.
        """
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context manager and close underlying client."""
        await self._client.__aexit__(*args)

    async def close(self) -> None:
        """Close the underlying client and release resources."""
        await self._client.close()

    @property
    def email(self) -> TrackedEmailClient:
        """Get the tracked email client.

        Returns:
            TrackedEmailClient that auto-tracks action methods.
        """
        if self._email is None:
            self._email = TrackedEmailClient(self._client.email, self._context)
        return self._email

    @property
    def sms(self) -> TrackedSMSClient:
        """Get the tracked SMS client.

        Returns:
            TrackedSMSClient that auto-tracks action methods.
        """
        if self._sms is None:
            self._sms = TrackedSMSClient(self._client.sms, self._context)
        return self._sms

    @property
    def chat(self) -> TrackedChatClient:
        """Get the tracked chat client.

        Returns:
            TrackedChatClient that auto-tracks action methods.
        """
        if self._chat is None:
            self._chat = TrackedChatClient(self._client.chat, self._context)
        return self._chat

    @property
    def calendar(self) -> TrackedCalendarClient:
        """Get the tracked calendar client.

        Returns:
            TrackedCalendarClient that auto-tracks action methods.
        """
        if self._calendar is None:
            self._calendar = TrackedCalendarClient(
                self._client.calendar, self._context
            )
        return self._calendar

    @property
    def location(self) -> TrackedLocationClient:
        """Get the tracked location client.

        Returns:
            TrackedLocationClient that auto-tracks action methods.
        """
        if self._location is None:
            self._location = TrackedLocationClient(
                self._client.location, self._context
            )
        return self._location

    @property
    def weather(self) -> TrackedWeatherClient:
        """Get the tracked weather client.

        Returns:
            TrackedWeatherClient that auto-tracks action methods.
        """
        if self._weather is None:
            self._weather = TrackedWeatherClient(
                self._client.weather, self._context
            )
        return self._weather

    @property
    def time(self) -> Any:
        """Get the time client (untracked, read-only).

        Returns:
            AsyncTimeClient for reading simulator time.
        """
        return self._client.time


def create_tracked_client(context: "AssessmentContext") -> TrackedAsyncUESClient:
    """Create a tracked UES client from an assessment context.

    Convenience function for creating a TrackedAsyncUESClient.

    Args:
        context: The assessment context with UES connection info.

    Returns:
        A new TrackedAsyncUESClient instance.

    Example:
        Creating a tracked client::

            context = AssessmentContext(...)
            ues = create_tracked_client(context)
            async with ues:
                await ues.email.send(...)
    """
    return TrackedAsyncUESClient(context)
