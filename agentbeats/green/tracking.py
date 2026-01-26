"""Action tracking for Purple agent assessments.

This module provides the ActionTracker class which monitors and logs all
actions taken by the Purple agent during an assessment by querying events
created with the Purple agent's API key.
"""

from datetime import datetime

from client import AsyncUESClient
from agentbeats.green.session import ActionLogEntry


class ActionTracker:
    """Tracks Purple agent actions for logging and evaluation.
    
    Uses the UES event attribution feature to query events created by the
    Purple agent (filtered by agent_id). This provides a reliable way to
    identify Purple's actions regardless of event execution timing.
    
    Example:
        >>> tracker = ActionTracker(ues_client, "purple-agent-12345")
        >>> actions = await tracker.get_actions_since(turn_start_time)
        >>> for action in actions:
        ...     print(f"Turn {action.turn}: {action.summary}")
    """
    
    def __init__(self, ues_client: AsyncUESClient, purple_agent_id: str):
        """Initialize the action tracker.
        
        Args:
            ues_client: AsyncUESClient for querying UES events.
            purple_agent_id: Agent ID used for Purple's API key.
        """
        self._client = ues_client
        self._purple_agent_id = purple_agent_id
        self._last_query_time: datetime | None = None
        self._seen_event_ids: set[str] = set()
    
    async def get_actions_since(
        self,
        since_time: datetime,
        turn: int = 1,
    ) -> list[ActionLogEntry]:
        """Query events created by Purple since the given time.
        
        Returns events that were created after the specified time and
        haven't been seen before (to avoid duplicates across calls).
        
        Args:
            since_time: Only include events created after this time.
            turn: Turn number to assign to action log entries.
            
        Returns:
            List of ActionLogEntry instances for new actions.
        """
        # Query events created by Purple agent
        response = await self._client.events.list_events(
            agent_id=self._purple_agent_id,
        )
        
        # Filter to new events created after since_time
        new_entries = []
        for event in response.events:
            # Skip if we've already seen this event
            if event.event_id in self._seen_event_ids:
                continue
            
            # Skip if created before since_time
            if event.created_at and event.created_at < since_time:
                continue
            
            # Record as seen
            self._seen_event_ids.add(event.event_id)
            
            # Convert to ActionLogEntry
            entry = self._event_to_action_entry(event, turn)
            new_entries.append(entry)
        
        # Update last query time
        self._last_query_time = datetime.now()
        
        return new_entries
    
    async def get_all_actions(self, turn: int = 1) -> list[ActionLogEntry]:
        """Get all actions taken by Purple agent.
        
        Unlike get_actions_since, this returns all events regardless of
        whether they've been seen before.
        
        Args:
            turn: Turn number to assign to action log entries.
            
        Returns:
            List of all ActionLogEntry instances.
        """
        response = await self._client.events.list_events(
            agent_id=self._purple_agent_id,
        )
        
        entries = []
        for event in response.events:
            entry = self._event_to_action_entry(event, turn)
            entries.append(entry)
            # Also mark as seen
            self._seen_event_ids.add(event.event_id)
        
        return entries
    
    def _event_to_action_entry(
        self,
        event,
        turn: int,
    ) -> ActionLogEntry:
        """Convert an EventResponse to an ActionLogEntry.
        
        Args:
            event: EventResponse from UES client.
            turn: Turn number to assign.
            
        Returns:
            ActionLogEntry instance.
        """
        # Determine action type from event data
        action_type = self._determine_action_type(event.modality, event.data)
        
        # Generate summary
        summary = self._generate_summary(event.modality, action_type, event.data)
        
        return ActionLogEntry(
            turn=turn,
            event_id=event.event_id,
            modality=event.modality,
            action_type=action_type,
            timestamp=event.scheduled_time,
            summary=summary,
            details=event.data,
        )
    
    def _determine_action_type(
        self,
        modality: str,
        data: dict | None,
    ) -> str:
        """Determine the action type from event data.
        
        Args:
            modality: The modality of the event.
            data: The event data payload.
            
        Returns:
            Action type string (e.g., "send", "create", "update").
        """
        if data is None:
            return "unknown"
        
        # Check for explicit operation field
        if "operation" in data:
            return data["operation"]
        
        # Check for action field
        if "action" in data:
            return data["action"]
        
        # Infer from modality-specific patterns
        if modality == "email":
            if data.get("is_draft"):
                return "draft"
            if "to_addresses" in data:
                return "send"
            return "read"
        
        if modality == "sms":
            if "to" in data or "to_number" in data:
                return "send"
            return "receive"
        
        if modality == "calendar":
            if data.get("event_id") and "title" in data:
                return "create"
            return "update"
        
        if modality == "chat":
            return "send"
        
        return "action"
    
    def _generate_summary(
        self,
        modality: str,
        action_type: str,
        data: dict | None,
    ) -> str:
        """Generate a human-readable summary of the action.
        
        Args:
            modality: The modality of the event.
            action_type: The type of action taken.
            data: The event data payload.
            
        Returns:
            Human-readable summary string.
        """
        if data is None:
            return f"{modality.capitalize()} action: {action_type}"
        
        # Modality-specific summaries
        if modality == "email":
            subject = data.get("subject", "No subject")
            to = data.get("to_addresses", ["unknown"])
            to_str = to[0] if isinstance(to, list) and to else str(to)
            if action_type == "send":
                return f"Sent email to {to_str}: '{subject}'"
            elif action_type == "draft":
                return f"Drafted email to {to_str}: '{subject}'"
            elif action_type == "reply":
                return f"Replied to email: '{subject}'"
            return f"Email action ({action_type}): '{subject}'"
        
        if modality == "sms":
            to = data.get("to") or data.get("to_number", "unknown")
            text = data.get("text", data.get("content", ""))
            preview = text[:50] + "..." if len(text) > 50 else text
            return f"Sent SMS to {to}: '{preview}'"
        
        if modality == "calendar":
            title = data.get("title", "Untitled event")
            if action_type == "create":
                return f"Created calendar event: '{title}'"
            elif action_type == "update":
                return f"Updated calendar event: '{title}'"
            elif action_type == "delete":
                return f"Deleted calendar event: '{title}'"
            return f"Calendar action ({action_type}): '{title}'"
        
        if modality == "chat":
            content = data.get("content", data.get("text", ""))
            preview = content[:50] + "..." if len(content) > 50 else content
            return f"Sent chat message: '{preview}'"
        
        # Generic summary
        return f"{modality.capitalize()} {action_type}"
    
    def reset(self) -> None:
        """Reset the tracker state.
        
        Clears seen event IDs so all events will be treated as new.
        """
        self._seen_event_ids.clear()
        self._last_query_time = None
    
    @property
    def seen_count(self) -> int:
        """Number of events that have been seen."""
        return len(self._seen_event_ids)
