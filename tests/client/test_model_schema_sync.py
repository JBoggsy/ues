"""Tests that verify client models stay in sync with server models.

These tests import both client and server Pydantic models, extract their
field schemas, and compare field names, types, optionality, and defaults.
If a server model field is added, renamed, or retyped, these tests will
fail immediately.

Background:
    The client library defines its own Pydantic models to deserialize API
    responses (in ``src/ues/client/_*.py``). These models were originally
    written independently of the server models and can drift silently. This
    file exists to prevent that drift by comparing field schemas at test time.

    See ``docs/client/CLIENT_SERVER_AUDIT.md`` for the full list of 41
    issues that accumulated before these tests were introduced, and
    ``docs/client/CLIENT_SERVER_REMEDIATION_PLAN.md`` for how they were fixed.

How it works:
    For each pair of (client_model, server_model), the ``compare_models()``
    utility extracts every field name and checks:
      1. Every server field exists on the client model (no missing fields).
      2. Every client field exists on the server model (no phantom fields).
      3. Field optionality matches (required vs. optional).
      4. Field types are compatible (with configurable overrides for known
         acceptable differences like ``set`` → ``list``).

    Known acceptable differences are documented inline with rationale.
"""

from __future__ import annotations

import sys
from typing import Any, get_args, get_origin

import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo

# ---------------------------------------------------------------------------
# Server models
# ---------------------------------------------------------------------------
from ues.models.modalities.calendar_input import (
    Attachment as ServerAttachment,
)
from ues.models.modalities.calendar_input import (
    Attendee as ServerAttendee,
)
from ues.models.modalities.calendar_input import (
    RecurrenceRule as ServerRecurrenceRule,
)
from ues.models.modalities.calendar_input import (
    Reminder as ServerReminder,
)
from ues.models.modalities.calendar_state import (
    Calendar as ServerCalendar,
)
from ues.models.modalities.calendar_state import (
    CalendarEvent as ServerCalendarEvent,
)
from ues.models.modalities.chat_state import (
    ChatMessage as ServerChatMessage,
)
from ues.models.modalities.chat_state import (
    ConversationMetadata as ServerConversationMetadata,
)
from ues.models.modalities.contacts_input import (
    ContactIdentifier as ServerContactIdentifier,
)
from ues.models.modalities.contacts_input import (
    PostalAddress as ServerPostalAddress,
)
from ues.models.modalities.contacts_state import (
    Contact as ServerContact,
)
from ues.models.modalities.email_input import (
    EmailAttachment as ServerEmailAttachment,
)
from ues.models.modalities.email_state import (
    Email as ServerEmail,
)
from ues.models.modalities.email_state import (
    EmailSummary as ServerEmailSummary,
)
from ues.models.modalities.email_state import (
    EmailThread as ServerEmailThread,
)
from ues.models.modalities.sms_state import (
    GroupParticipant as ServerGroupParticipant,
)
from ues.models.modalities.sms_state import (
    MessageAttachment as ServerMessageAttachment,
)
from ues.models.modalities.sms_state import (
    MessageReaction as ServerMessageReaction,
)
from ues.models.modalities.sms_state import (
    SMSConversation as ServerSMSConversation,
)
from ues.models.modalities.sms_state import (
    SMSMessage as ServerSMSMessage,
)
from ues.models.modalities.weather_input import (
    CurrentWeather as ServerCurrentWeather,
)
from ues.models.modalities.weather_input import (
    DailyFeelsLike as ServerDailyFeelsLike,
)
from ues.models.modalities.weather_input import (
    DailyForecast as ServerDailyForecast,
)
from ues.models.modalities.weather_input import (
    DailyTemperature as ServerDailyTemperature,
)
from ues.models.modalities.weather_input import (
    HourlyForecast as ServerHourlyForecast,
)
from ues.models.modalities.weather_input import (
    MinutelyForecast as ServerMinutelyForecast,
)
from ues.models.modalities.weather_input import (
    WeatherAlert as ServerWeatherAlert,
)
from ues.models.modalities.weather_input import (
    WeatherCondition as ServerWeatherCondition,
)
from ues.models.modalities.weather_input import (
    WeatherReport as ServerWeatherReport,
)

# ---------------------------------------------------------------------------
# Client models
# ---------------------------------------------------------------------------
from ues.client._calendar import (
    Attachment as ClientAttachment,
)
from ues.client._calendar import (
    Attendee as ClientAttendee,
)
from ues.client._calendar import (
    CalendarContainer as ClientCalendar,
)
from ues.client._calendar import (
    CalendarEvent as ClientCalendarEvent,
)
from ues.client._calendar import (
    RecurrenceRule as ClientRecurrenceRule,
)
from ues.client._calendar import (
    Reminder as ClientReminder,
)
from ues.client._chat import (
    ChatMessage as ClientChatMessage,
)
from ues.client._chat import (
    ConversationMetadata as ClientConversationMetadata,
)
from ues.client._contacts import (
    Contact as ClientContact,
)
from ues.client._contacts import (
    ContactIdentifier as ClientContactIdentifier,
)
from ues.client._contacts import (
    PostalAddress as ClientPostalAddress,
)
from ues.client._email import (
    Email as ClientEmail,
)
from ues.client._email import (
    EmailAttachment as ClientEmailAttachment,
)
from ues.client._email import (
    EmailSummary as ClientEmailSummary,
)
from ues.client._email import (
    EmailThread as ClientEmailThread,
)
from ues.client._sms import (
    GroupParticipant as ClientGroupParticipant,
)
from ues.client._sms import (
    MessageAttachment as ClientMessageAttachment,
)
from ues.client._sms import (
    MessageReaction as ClientMessageReaction,
)
from ues.client._sms import (
    SMSConversation as ClientSMSConversation,
)
from ues.client._sms import (
    SMSMessage as ClientSMSMessage,
)
from ues.client._weather import (
    CurrentWeather as ClientCurrentWeather,
)
from ues.client._weather import (
    DailyFeelsLike as ClientDailyFeelsLike,
)
from ues.client._weather import (
    DailyForecast as ClientDailyForecast,
)
from ues.client._weather import (
    DailyTemperature as ClientDailyTemperature,
)
from ues.client._weather import (
    HourlyForecast as ClientHourlyForecast,
)
from ues.client._weather import (
    MinutelyForecast as ClientMinutelyForecast,
)
from ues.client._weather import (
    WeatherAlert as ClientWeatherAlert,
)
from ues.client._weather import (
    WeatherCondition as ClientWeatherCondition,
)
from ues.client._weather import (
    WeatherReport as ClientWeatherReport,
)


# ===================================================================
# Comparison Utility
# ===================================================================


def _is_optional(annotation: Any) -> bool:
    """Check whether a type annotation is Optional (i.e. ``X | None``).

    Handles both ``Optional[X]`` and ``X | None`` forms.
    """
    origin = get_origin(annotation)
    if origin is not type(None):
        args = get_args(annotation)
        if args and type(None) in args:
            return True
    return False


def _has_default(field_info: FieldInfo) -> bool:
    """Check whether a Pydantic FieldInfo has a default value."""
    from pydantic_core import PydanticUndefined

    return (
        field_info.default is not PydanticUndefined
        or field_info.default_factory is not None
    )


def _strip_optional(annotation: Any) -> Any:
    """Strip ``None`` from a union type to get the inner type."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if args and type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def _normalize_type_name(annotation: Any) -> str:
    """Produce a simplified, human-readable type string for comparison.

    This intentionally collapses:
      - ``set`` → ``list`` (since JSON arrays deserialize as lists)
      - ``typing.Union`` and ``X | Y`` to the same sorted representation
      - ``dict`` (untyped) to ``dict[str, Any]`` (typed with Any values)
      - ``list`` (untyped) to ``list[Any]``

    These normalizations prevent false positives from cosmetic type
    annotation differences that don't affect JSON compatibility.
    """
    import typing
    import types as builtin_types

    origin = get_origin(annotation)
    args = get_args(annotation)

    # Handle None type
    if annotation is type(None):
        return "None"

    # Handle Union types (both typing.Union and Python 3.10+ X | Y)
    is_union = False
    if origin is typing.Union:
        is_union = True
    elif sys.version_info >= (3, 10) and isinstance(
        annotation, builtin_types.UnionType
    ):
        is_union = True
        args = get_args(annotation)

    if is_union and args:
        has_none = type(None) in args
        non_none = [a for a in args if a is not type(None)]

        if has_none and len(non_none) == 1:
            return f"{_normalize_type_name(non_none[0])}?"
        elif has_none:
            parts = sorted(_normalize_type_name(a) for a in non_none)
            return f"({'|'.join(parts)})?"
        else:
            parts = sorted(_normalize_type_name(a) for a in args)
            return "|".join(parts)

    # collections: list, set, dict, frozenset
    if origin in (list, set, frozenset):
        # Normalize set/frozenset to list for comparison (JSON compat)
        inner = (
            ", ".join(_normalize_type_name(a) for a in args)
            if args
            else "Any"
        )
        return f"list[{inner}]"
    if origin is dict:
        if args and len(args) == 2:
            k, v = args
        else:
            k, v = str, Any
        return f"dict[{_normalize_type_name(k)}, {_normalize_type_name(v)}]"

    # Bare ``list`` or ``dict`` without parameters
    if annotation is list:
        return "list[Any]"
    if annotation is dict:
        return "dict[str, Any]"

    # Literal → "str" (all our Literal types are string enums)
    if get_origin(annotation) is typing.Literal:
        return "str"

    # Simple types
    if isinstance(annotation, type):
        return annotation.__name__

    # Fallback
    return str(annotation)


class FieldDifference:
    """A single difference between a client and server field."""

    def __init__(self, field_name: str, kind: str, detail: str) -> None:
        self.field_name = field_name
        self.kind = kind  # "missing_on_client", "extra_on_client", "type_mismatch", "optionality_mismatch"
        self.detail = detail

    def __repr__(self) -> str:
        return f"{self.kind}: {self.field_name} — {self.detail}"


def compare_models(
    client_model: type[BaseModel],
    server_model: type[BaseModel],
    *,
    ignore_fields: set[str] | None = None,
    type_overrides: dict[str, str] | None = None,
    client_extra_fields: set[str] | None = None,
) -> list[FieldDifference]:
    """Compare two Pydantic models field-by-field.

    Args:
        client_model: The client-side Pydantic model class.
        server_model: The server-side Pydantic model class.
        ignore_fields: Fields to skip entirely (e.g., server-internal fields
            that are never serialized to clients).
        type_overrides: Dict mapping field name → expected client type string.
            Use for known acceptable type differences.  If the client's
            normalized type matches this string, it is accepted.
        client_extra_fields: Fields that are expected to exist only on the
            client model (e.g., computed from other data).

    Returns:
        List of FieldDifference objects. Empty means models are in sync.
    """
    ignore = ignore_fields or set()
    overrides = type_overrides or {}
    extra_allowed = client_extra_fields or set()

    server_fields: dict[str, FieldInfo] = server_model.model_fields
    client_fields: dict[str, FieldInfo] = client_model.model_fields

    diffs: list[FieldDifference] = []

    # 1. Check every server field exists on client
    for field_name, server_fi in server_fields.items():
        if field_name in ignore:
            continue

        if field_name not in client_fields:
            diffs.append(
                FieldDifference(
                    field_name,
                    "missing_on_client",
                    f"Server has field '{field_name}' "
                    f"(type={server_fi.annotation}) but client does not",
                )
            )
            continue

        client_fi = client_fields[field_name]

        # Type comparison
        server_type_str = _normalize_type_name(server_fi.annotation)
        client_type_str = _normalize_type_name(client_fi.annotation)

        if field_name in overrides:
            expected = overrides[field_name]
            if client_type_str != expected:
                diffs.append(
                    FieldDifference(
                        field_name,
                        "type_mismatch",
                        f"Client type '{client_type_str}' does not match "
                        f"expected override '{expected}' "
                        f"(server type: '{server_type_str}')",
                    )
                )
        elif server_type_str != client_type_str:
            diffs.append(
                FieldDifference(
                    field_name,
                    "type_mismatch",
                    f"Server type '{server_type_str}' != "
                    f"client type '{client_type_str}'",
                )
            )

        # Optionality: if server field is required (no default),
        # client should also be required
        server_required = not _has_default(server_fi)
        client_required = not _has_default(client_fi)

        if server_required and not client_required:
            diffs.append(
                FieldDifference(
                    field_name,
                    "optionality_mismatch",
                    f"Server field is required but client has default",
                )
            )

    # 2. Check for phantom fields on client
    for field_name in client_fields:
        if field_name in ignore:
            continue
        if field_name in extra_allowed:
            continue
        if field_name not in server_fields:
            diffs.append(
                FieldDifference(
                    field_name,
                    "extra_on_client",
                    f"Client has field '{field_name}' but server does not",
                )
            )

    return diffs


def assert_models_in_sync(
    client_model: type[BaseModel],
    server_model: type[BaseModel],
    *,
    ignore_fields: set[str] | None = None,
    type_overrides: dict[str, str] | None = None,
    client_extra_fields: set[str] | None = None,
    label: str = "",
) -> None:
    """Assert that client and server models have matching schemas.

    Raises ``AssertionError`` with a detailed diff report if they don't match.
    """
    diffs = compare_models(
        client_model,
        server_model,
        ignore_fields=ignore_fields,
        type_overrides=type_overrides,
        client_extra_fields=client_extra_fields,
    )
    if diffs:
        model_label = label or f"{client_model.__name__} vs {server_model.__name__}"
        lines = [f"Schema mismatch in {model_label}:"]
        for d in diffs:
            lines.append(f"  - {d}")
        raise AssertionError("\n".join(lines))


# ===================================================================
# Email Modality
# ===================================================================


class TestEmailSchemaSync:
    """Verify client email models match server email models."""

    def test_email_attachment_sync(self):
        """EmailAttachment client model matches server EmailAttachment."""
        assert_models_in_sync(
            ClientEmailAttachment,
            ServerEmailAttachment,
            label="EmailAttachment",
        )

    def test_email_sync(self):
        """Email client model matches server Email model.

        Known difference: Server uses ``list`` (untyped) for attachments,
        while client uses ``list[EmailAttachment]`` (typed). Both are
        compatible at the JSON level; the client simply provides more type
        safety.
        """
        assert_models_in_sync(
            ClientEmail,
            ServerEmail,
            type_overrides={
                # Server uses bare `list`, client uses `list[EmailAttachment]`
                # Both are compatible; client is stricter
                "attachments": "list[EmailAttachment]",
            },
            label="Email",
        )

    def test_email_thread_sync(self):
        """EmailThread client model matches server EmailThread.

        Known difference: Server uses ``set[str]`` for
        ``participant_addresses`` while client uses ``list[str]``.
        JSON serialization converts sets to arrays, so the client
        uses ``list`` to avoid unnecessary post-processing.
        """
        assert_models_in_sync(
            ClientEmailThread,
            ServerEmailThread,
            label="EmailThread",
            # set[str] → list[str] is normalized by _normalize_type_name
        )

    def test_email_summary_sync(self):
        """EmailSummary client model matches server EmailSummary."""
        assert_models_in_sync(
            ClientEmailSummary,
            ServerEmailSummary,
            label="EmailSummary",
        )


# ===================================================================
# SMS Modality
# ===================================================================


class TestSMSSchemaSync:
    """Verify client SMS models match server SMS models."""

    def test_message_attachment_sync(self):
        """MessageAttachment client model matches server MessageAttachment."""
        assert_models_in_sync(
            ClientMessageAttachment,
            ServerMessageAttachment,
            label="MessageAttachment",
        )

    def test_message_reaction_sync(self):
        """MessageReaction client model matches server MessageReaction."""
        assert_models_in_sync(
            ClientMessageReaction,
            ServerMessageReaction,
            label="MessageReaction",
        )

    def test_group_participant_sync(self):
        """GroupParticipant client model matches server GroupParticipant."""
        assert_models_in_sync(
            ClientGroupParticipant,
            ServerGroupParticipant,
            label="GroupParticipant",
        )

    def test_sms_message_sync(self):
        """SMSMessage client model matches server SMSMessage."""
        assert_models_in_sync(
            ClientSMSMessage,
            ServerSMSMessage,
            label="SMSMessage",
        )

    def test_sms_conversation_sync(self):
        """SMSConversation client model matches server SMSConversation."""
        assert_models_in_sync(
            ClientSMSConversation,
            ServerSMSConversation,
            label="SMSConversation",
        )


# ===================================================================
# Calendar Modality
# ===================================================================


class TestCalendarSchemaSync:
    """Verify client calendar models match server calendar models."""

    def test_attendee_sync(self):
        """Attendee client model matches server Attendee."""
        assert_models_in_sync(
            ClientAttendee,
            ServerAttendee,
            label="Attendee",
        )

    def test_reminder_sync(self):
        """Reminder client model matches server Reminder."""
        assert_models_in_sync(
            ClientReminder,
            ServerReminder,
            label="Reminder",
        )

    def test_attachment_sync(self):
        """Attachment client model matches server Attachment."""
        assert_models_in_sync(
            ClientAttachment,
            ServerAttachment,
            label="Attachment",
        )

    def test_recurrence_rule_sync(self):
        """RecurrenceRule client model matches server RecurrenceRule."""
        assert_models_in_sync(
            ClientRecurrenceRule,
            ServerRecurrenceRule,
            label="RecurrenceRule",
        )

    def test_calendar_event_sync(self):
        """CalendarEvent client model matches server CalendarEvent."""
        assert_models_in_sync(
            ClientCalendarEvent,
            ServerCalendarEvent,
            label="CalendarEvent",
        )

    def test_calendar_container_sync(self):
        """CalendarContainer (client) matches Calendar (server).

        The client names this ``CalendarContainer`` to avoid ambiguity with
        the top-level ``Calendar`` concept; this is acceptable since Pydantic
        does not match on class names.

        Known differences:
          - ``created_at``/``updated_at``: Server uses ``datetime``, client
            uses ``datetime | str`` because the server serializes these to
            ISO-format strings via a field serializer, so the client accepts
            both for flexibility.
        """
        assert_models_in_sync(
            ClientCalendar,
            ServerCalendar,
            type_overrides={
                "created_at": "datetime|str",
                "updated_at": "datetime|str",
            },
            label="CalendarContainer vs Calendar",
        )


# ===================================================================
# Chat Modality
# ===================================================================


class TestChatSchemaSync:
    """Verify client chat models match server chat models."""

    def test_chat_message_sync(self):
        """ChatMessage client model matches server ChatMessage.

        Known differences:
          - ``content``: Server uses ``Union[str, list[dict]]`` (untyped dict),
            client uses ``str | list[dict[str, Any]]`` (typed dict). Both are
            functionally identical; client provides slightly more type info.
          - ``metadata``: Server uses bare ``dict``, client uses
            ``dict[str, Any]``. Functionally identical; client is more explicit.
        """
        assert_models_in_sync(
            ClientChatMessage,
            ServerChatMessage,
            type_overrides={
                "content": "list[dict[str, Any]]|str",
                "metadata": "dict[str, Any]",
            },
            label="ChatMessage",
        )

    def test_conversation_metadata_sync(self):
        """ConversationMetadata client model matches server ConversationMetadata."""
        assert_models_in_sync(
            ClientConversationMetadata,
            ServerConversationMetadata,
            label="ConversationMetadata",
        )


# ===================================================================
# Contacts Modality
# ===================================================================


class TestContactsSchemaSync:
    """Verify client contacts models match server contacts models."""

    def test_contact_identifier_sync(self):
        """ContactIdentifier client model matches server ContactIdentifier."""
        assert_models_in_sync(
            ClientContactIdentifier,
            ServerContactIdentifier,
            label="ContactIdentifier",
        )

    def test_postal_address_sync(self):
        """PostalAddress client model matches server PostalAddress."""
        assert_models_in_sync(
            ClientPostalAddress,
            ServerPostalAddress,
            label="PostalAddress",
        )

    def test_contact_sync(self):
        """Contact client model matches server Contact.

        Known differences:
          - ``groups``: Server uses ``set[str]``, client uses ``list[str]``.
            JSON serialization converts sets to arrays, so the client uses
            ``list`` to match what is received over the wire.
          - ``birthday``: Server uses ``Any | None``, client also uses
            ``Any | None`` for compatibility.
        """
        assert_models_in_sync(
            ClientContact,
            ServerContact,
            label="Contact",
            # set[str] → list[str] is normalized by _normalize_type_name
        )


# ===================================================================
# Weather Modality
# ===================================================================


class TestWeatherSchemaSync:
    """Verify client weather models match server weather models."""

    def test_weather_condition_sync(self):
        """WeatherCondition client model matches server WeatherCondition."""
        assert_models_in_sync(
            ClientWeatherCondition,
            ServerWeatherCondition,
            label="WeatherCondition",
        )

    def test_current_weather_sync(self):
        """CurrentWeather client model matches server CurrentWeather."""
        assert_models_in_sync(
            ClientCurrentWeather,
            ServerCurrentWeather,
            label="CurrentWeather",
        )

    def test_minutely_forecast_sync(self):
        """MinutelyForecast client model matches server MinutelyForecast."""
        assert_models_in_sync(
            ClientMinutelyForecast,
            ServerMinutelyForecast,
            label="MinutelyForecast",
        )

    def test_hourly_forecast_sync(self):
        """HourlyForecast client model matches server HourlyForecast."""
        assert_models_in_sync(
            ClientHourlyForecast,
            ServerHourlyForecast,
            label="HourlyForecast",
        )

    def test_daily_temperature_sync(self):
        """DailyTemperature client model matches server DailyTemperature."""
        assert_models_in_sync(
            ClientDailyTemperature,
            ServerDailyTemperature,
            label="DailyTemperature",
        )

    def test_daily_feels_like_sync(self):
        """DailyFeelsLike client model matches server DailyFeelsLike."""
        assert_models_in_sync(
            ClientDailyFeelsLike,
            ServerDailyFeelsLike,
            label="DailyFeelsLike",
        )

    def test_daily_forecast_sync(self):
        """DailyForecast client model matches server DailyForecast."""
        assert_models_in_sync(
            ClientDailyForecast,
            ServerDailyForecast,
            label="DailyForecast",
        )

    def test_weather_alert_sync(self):
        """WeatherAlert client model matches server WeatherAlert."""
        assert_models_in_sync(
            ClientWeatherAlert,
            ServerWeatherAlert,
            label="WeatherAlert",
        )

    def test_weather_report_sync(self):
        """WeatherReport client model matches server WeatherReport."""
        assert_models_in_sync(
            ClientWeatherReport,
            ServerWeatherReport,
            label="WeatherReport",
        )


# ===================================================================
# Meta-tests: Ensures the comparison utility itself is correct
# ===================================================================


class TestCompareModelsUtility:
    """Tests for the compare_models utility function itself."""

    def test_identical_models_produce_no_diffs(self):
        """When client and server models are identical, no diffs are reported."""

        class ModelA(BaseModel):
            x: int
            y: str = "hello"

        class ModelB(BaseModel):
            x: int
            y: str = "hello"

        diffs = compare_models(ModelA, ModelB)
        assert diffs == []

    def test_missing_field_detected(self):
        """A field present on server but not client is caught."""

        class Client(BaseModel):
            x: int

        class Server(BaseModel):
            x: int
            y: str

        diffs = compare_models(Client, Server)
        assert len(diffs) == 1
        assert diffs[0].kind == "missing_on_client"
        assert diffs[0].field_name == "y"

    def test_extra_field_detected(self):
        """A field present on client but not server is caught."""

        class Client(BaseModel):
            x: int
            phantom: str = "ghost"

        class Server(BaseModel):
            x: int

        diffs = compare_models(Client, Server)
        assert len(diffs) == 1
        assert diffs[0].kind == "extra_on_client"
        assert diffs[0].field_name == "phantom"

    def test_type_mismatch_detected(self):
        """Different field types are caught."""

        class Client(BaseModel):
            x: str

        class Server(BaseModel):
            x: int

        diffs = compare_models(Client, Server)
        assert len(diffs) == 1
        assert diffs[0].kind == "type_mismatch"

    def test_set_list_normalized(self):
        """set[str] and list[str] should NOT produce a diff (JSON compat)."""

        class Client(BaseModel):
            tags: list[str]

        class Server(BaseModel):
            tags: set[str]

        diffs = compare_models(Client, Server)
        assert diffs == []

    def test_ignore_fields(self):
        """Ignored fields are skipped entirely."""

        class Client(BaseModel):
            x: int

        class Server(BaseModel):
            x: int
            internal_only: str

        diffs = compare_models(Client, Server, ignore_fields={"internal_only"})
        assert diffs == []

    def test_type_override(self):
        """Type overrides allow expected differences."""

        class Client(BaseModel):
            data: list[int]

        class Server(BaseModel):
            data: list

        diffs = compare_models(
            Client, Server, type_overrides={"data": "list[int]"}
        )
        assert diffs == []

    def test_client_extra_field_allowed(self):
        """client_extra_fields suppresses extra-on-client warnings."""

        class Client(BaseModel):
            x: int
            computed: str = "derived"

        class Server(BaseModel):
            x: int

        diffs = compare_models(
            Client, Server, client_extra_fields={"computed"}
        )
        assert diffs == []

    def test_optionality_mismatch_detected(self):
        """Server required field with client default is caught."""

        class Client(BaseModel):
            x: int = 0

        class Server(BaseModel):
            x: int

        diffs = compare_models(Client, Server)
        assert any(d.kind == "optionality_mismatch" for d in diffs)
