"""Evaluation context for agent testing.

This module defines the EvalContext class, which is passed to all evaluator
and filter functions to provide API access and state information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from client import AsyncUESClient


@dataclass
class EvalContext:
    """Context object passed to evaluator and filter functions.

    Provides access to the UES client, event history, and scenario configuration.
    Evaluator functions receive this as their first argument.

    Attributes:
        client: Async UES client for API access.
        event_history: List of all events that have occurred in the scenario.
        trigger_event: For on_event evaluators, the event that triggered
            this evaluation. None for post_scenario evaluators.
        scenario_config: The loaded scenario configuration (dict).
        criteria_config: The loaded criteria configuration (dict).

    Example:
        >>> async def check_emails_sent(ctx: EvalContext, params: dict):
        ...     email_state = await ctx.get_state("email")
        ...     sent_count = sum(
        ...         1 for e in email_state.emails.values()
        ...         if e.folder == "sent"
        ...     )
        ...     return EvalResult(
        ...         score=min(sent_count, params["expected"]),
        ...         max_score=params["expected"],
        ...         explanation=f"Sent {sent_count} emails",
        ...     )
    """

    client: "AsyncUESClient"
    event_history: list[dict[str, Any]] = field(default_factory=list)
    trigger_event: dict[str, Any] | None = None
    scenario_config: dict[str, Any] = field(default_factory=dict)
    criteria_config: dict[str, Any] = field(default_factory=dict)

    async def get_state(self, modality: str) -> Any:
        """Get current state for a modality.

        Args:
            modality: The modality name (email, sms, calendar, location, weather).

        Returns:
            The modality state object.

        Raises:
            ValueError: If the modality is not recognized.

        Example:
            >>> email_state = await ctx.get_state("email")
            >>> print(email_state.message_count)
        """
        modality_clients = {
            "email": self.client.email,
            "sms": self.client.sms,
            "calendar": self.client.calendar,
            "location": self.client.location,
            "weather": self.client.weather,
        }

        if modality not in modality_clients:
            raise ValueError(
                f"Unknown modality: {modality}. "
                f"Valid options: {list(modality_clients.keys())}"
            )

        client = modality_clients[modality]
        return await client.get_state()

    async def get_time(self) -> datetime:
        """Get current simulation time.

        Returns:
            The current simulation datetime.

        Example:
            >>> current_time = await ctx.get_time()
            >>> print(f"Simulation time: {current_time}")
        """
        time_state = await self.client.time.get_state()
        return time_state.current_time

    async def get_events(
        self,
        modality: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get events from the event queue.

        Args:
            modality: Filter by modality (optional).
            status: Filter by status: "pending", "executed", or "all" (optional).

        Returns:
            List of event dictionaries.

        Example:
            >>> pending = await ctx.get_events(status="pending")
            >>> email_events = await ctx.get_events(modality="email")
        """
        events = await self.client.events.list()

        result = []
        for event in events:
            event_dict = event.model_dump() if hasattr(event, "model_dump") else event

            if modality and event_dict.get("modality") != modality:
                continue
            if status and status != "all":
                if event_dict.get("status") != status:
                    continue

            result.append(event_dict)

        return result

    def with_trigger_event(self, event: dict[str, Any]) -> "EvalContext":
        """Create a new context with a trigger event set.

        This is used internally by the hook manager to create contexts
        for on_event evaluators.

        Args:
            event: The event that triggered the evaluation.

        Returns:
            A new EvalContext with the trigger_event set.
        """
        return EvalContext(
            client=self.client,
            event_history=self.event_history,
            trigger_event=event,
            scenario_config=self.scenario_config,
            criteria_config=self.criteria_config,
        )

    def add_event(self, event: dict[str, Any]) -> None:
        """Add an event to the history.

        This is used internally by the hook manager to track events.

        Args:
            event: The event to add to history.
        """
        self.event_history.append(event)
