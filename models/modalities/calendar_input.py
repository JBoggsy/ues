"""Calendar input model."""

from models.base_input import ModalityInput


class CalendarEventInput(ModalityInput):
    """Input for new or modified calendar events.

    Args:
        title: Event title.
        start_time: Event start time (simulator time).
        end_time: Event end time (simulator time).
        location: Event location.
        attendees: List of attendee email addresses.
        recurrence: Optional recurrence rule (daily, weekly, etc.).
        description: Optional event description.
    """

    pass
