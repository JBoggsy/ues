"""Utility functions for API route handlers.

This module contains helper functions for common operations across
modality route handlers, reducing code duplication.
"""

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from models.event import SimulatorEvent
from models.simulation import SimulationEngine


def create_immediate_event(
    engine: SimulationEngine,
    modality: str,
    data: dict[str, Any],
    priority: int = 100,
) -> SimulatorEvent:
    """Create and add an immediate event to the simulation.
    
    This is a common pattern for all modality action endpoints. Creates
    an event scheduled at the current simulator time with high priority,
    and executes it immediately with undo capture.
    
    Args:
        engine: The SimulationEngine instance.
        modality: The modality type for this event.
        data: The event data (ModalityInput payload).
        priority: Event priority (0-100, higher executes first).
    
    Returns:
        The created SimulatorEvent (after execution).
    
    Raises:
        HTTPException: If event creation or execution fails.
    """
    try:
        current_time = engine.environment.time_state.current_time
        
        event = SimulatorEvent(
            scheduled_time=current_time,
            modality=modality,
            data=data,
            priority=priority,
            created_at=current_time,
        )
        
        engine.add_event(event)
        
        # Execute the event immediately with undo capture
        undo_entry = event.execute(engine.environment, capture_undo=True)
        
        # Push undo entry to undo stack if captured
        if undo_entry is not None:
            engine.undo_stack.push(undo_entry)
        
        return event
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event data: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create event: {str(e)}",
        )


def validate_modality_exists(engine: SimulationEngine, modality: str) -> None:
    """Validate that a modality exists in the environment.
    
    Args:
        engine: The SimulationEngine instance.
        modality: The modality type to check.
    
    Raises:
        HTTPException: If modality is not found (404).
    """
    if modality not in engine.environment.modality_states:
        available = list(engine.environment.modality_states.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Modality '{modality}' not found. Available modalities: {available}",
        )


def get_modality_state(engine: SimulationEngine, modality: str) -> Any:
    """Get the current state for a modality.
    
    Args:
        engine: The SimulationEngine instance.
        modality: The modality type to retrieve.
    
    Returns:
        The modality state object.
    
    Raises:
        HTTPException: If modality is not found (404).
    """
    validate_modality_exists(engine, modality)
    return engine.environment.modality_states[modality]


def get_current_simulator_time(engine: SimulationEngine) -> datetime:
    """Get the current simulator time.
    
    Args:
        engine: The SimulationEngine instance.
    
    Returns:
        Current simulator time as datetime.
    """
    return engine.environment.time_state.current_time


def apply_pagination(
    items: list[Any],
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[Any], int, int]:
    """Apply pagination to a list of items.
    
    Args:
        items: The full list of items to paginate.
        limit: Maximum number of items to return (None = all).
        offset: Number of items to skip.
    
    Returns:
        Tuple of (paginated_items, total_count, returned_count).
    """
    total_count = len(items)
    
    if limit is not None:
        paginated = items[offset : offset + limit]
    else:
        paginated = items[offset:]
    
    returned_count = len(paginated)
    
    return paginated, total_count, returned_count


def apply_sort(
    items: list[dict[str, Any]],
    sort_by: str | None = None,
    sort_order: str = "asc",
) -> list[dict[str, Any]]:
    """Apply sorting to a list of dictionaries.
    
    Args:
        items: The list of items to sort.
        sort_by: Field name to sort by (None = no sorting).
        sort_order: Sort direction ("asc" or "desc").
    
    Returns:
        Sorted list of items.
    """
    if not sort_by:
        return items
    
    reverse = sort_order == "desc"
    
    try:
        return sorted(
            items,
            key=lambda x: x.get(sort_by, ""),
            reverse=reverse,
        )
    except (TypeError, KeyError):
        # If sorting fails, return unsorted
        return items


def filter_by_date_range(
    items: list[dict[str, Any]],
    date_field: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Filter items by date range.
    
    Args:
        items: The list of items to filter.
        date_field: Name of the date field to filter on.
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).
    
    Returns:
        Filtered list of items.
    """
    filtered = items
    
    if start_date:
        filtered = [
            item
            for item in filtered
            if item.get(date_field)
            and item[date_field] >= start_date
        ]
    
    if end_date:
        filtered = [
            item
            for item in filtered
            if item.get(date_field)
            and item[date_field] <= end_date
        ]
    
    return filtered


def filter_by_text_search(
    items: list[dict[str, Any]],
    search_text: str | None = None,
    search_fields: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter items by text search (case-insensitive).
    
    Args:
        items: The list of items to filter.
        search_text: Text to search for.
        search_fields: List of field names to search in (None = search all string fields).
    
    Returns:
        Filtered list of items.
    """
    if not search_text:
        return items
    
    search_lower = search_text.lower()
    filtered = []
    
    for item in items:
        if search_fields:
            # Search only specified fields
            for field in search_fields:
                value = item.get(field)
                if value and isinstance(value, str) and search_lower in value.lower():
                    filtered.append(item)
                    break
        else:
            # Search all string fields
            for value in item.values():
                if isinstance(value, str) and search_lower in value.lower():
                    filtered.append(item)
                    break
    
    return filtered
