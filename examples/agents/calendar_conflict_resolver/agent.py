#!/usr/bin/env python3
"""Calendar Conflict Resolver Agent.

A user-side agent that monitors the user's calendar, detects scheduling conflicts,
and generates intelligent recommendations for resolving them using LLM analysis.

This agent demonstrates:
- Calendar API integration for querying events
- Conflict detection (overlaps, insufficient gaps, location conflicts)
- Priority scoring based on attendee importance and meeting context
- LLM-powered recommendation generation
- Day-by-day simulation processing

Usage:
    python agent.py [--model MODEL] [--ollama-host HOST] [--ues-host HOST]

Example:
    python agent.py --model gemma3:12b --ollama-host http://localhost:11434
"""

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from client import UESClient
from client._calendar import CalendarEvent


def load_system_prompt() -> str:
    """Load the system prompt from system_prompt.txt."""
    prompt_path = Path(__file__).parent / "system_prompt.txt"
    return prompt_path.read_text().strip()


def load_priorities() -> dict:
    """Load priority configuration from priorities.json."""
    priorities_path = Path(__file__).parent / "priorities.json"
    return json.loads(priorities_path.read_text())


def load_scenario(scenario_path: Path, ues_host: str) -> None:
    """Load a scenario file into UES via direct HTTP.

    Args:
        scenario_path: Path to the .ues-scenario.json file.
        ues_host: The UES server URL.
    """
    scenario_data = json.loads(scenario_path.read_text())
    response = httpx.post(
        f"{ues_host}/scenario/import/full",
        json=scenario_data,
        timeout=30.0,
    )
    if not response.is_success:
        print(f"Error loading scenario: {response.status_code}")
        print(f"Response: {response.text}")
    response.raise_for_status()


def call_ollama(
    prompt: str,
    system_prompt: str,
    model: str,
    ollama_host: str,
) -> str:
    """Call Ollama API to generate a response.

    Args:
        prompt: The user prompt containing conflict data.
        system_prompt: The system prompt defining agent behavior.
        model: The Ollama model to use.
        ollama_host: The Ollama server URL.

    Returns:
        The generated response text.
    """
    response = httpx.post(
        f"{ollama_host}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
        },
        timeout=180.0,
    )
    response.raise_for_status()
    return response.json()["response"]


class ConflictDetector:
    """Detects various types of calendar conflicts."""

    def __init__(self, priorities: dict):
        """Initialize the conflict detector with priority configuration.

        Args:
            priorities: Priority configuration from priorities.json.
        """
        self.priorities = priorities
        self.buffer_settings = priorities.get("buffer_settings", {})
        self.min_gap = timedelta(minutes=self.buffer_settings.get("minimum_gap_minutes", 15))
        self.travel_buffer = timedelta(minutes=self.buffer_settings.get("travel_buffer_minutes", 30))
        self.locations = priorities.get("locations", {})
        self.characters = priorities.get("characters", {})

    def detect_conflicts(self, events: list[CalendarEvent]) -> list[dict[str, Any]]:
        """Detect all conflicts in a list of calendar events.

        Args:
            events: List of CalendarEvent objects for a given day.

        Returns:
            List of conflict dictionaries containing conflict details.
        """
        conflicts = []

        # Sort events by start time
        sorted_events = sorted(events, key=lambda e: e.start)

        # Check for overlaps and insufficient gaps
        for i, event_a in enumerate(sorted_events):
            for event_b in sorted_events[i + 1:]:
                # Check for time overlap
                if self._events_overlap(event_a, event_b):
                    conflict = self._create_conflict(
                        conflict_type="overlap",
                        events=[event_a, event_b],
                        description=f"Time overlap: '{event_a.title}' and '{event_b.title}'",
                    )
                    conflicts.append(conflict)

                # Check for insufficient gap (only if they don't already overlap)
                elif self._insufficient_gap(event_a, event_b):
                    conflict = self._create_conflict(
                        conflict_type="insufficient_gap",
                        events=[event_a, event_b],
                        description=f"Insufficient gap between '{event_a.title}' and '{event_b.title}'",
                    )
                    conflicts.append(conflict)

                # Check for location conflict (different locations without travel time)
                elif self._location_conflict(event_a, event_b):
                    conflict = self._create_conflict(
                        conflict_type="location_conflict",
                        events=[event_a, event_b],
                        description=f"Location conflict: travel time needed between '{event_a.location}' and '{event_b.location}'",
                    )
                    conflicts.append(conflict)

        # Deduplicate conflicts involving the same events
        return self._deduplicate_conflicts(conflicts)

    def _events_overlap(self, event_a: CalendarEvent, event_b: CalendarEvent) -> bool:
        """Check if two events have overlapping times.

        Args:
            event_a: First event.
            event_b: Second event.

        Returns:
            True if events overlap.
        """
        return event_a.start < event_b.end and event_b.start < event_a.end

    def _insufficient_gap(self, event_a: CalendarEvent, event_b: CalendarEvent) -> bool:
        """Check if there's insufficient gap between consecutive events.

        Args:
            event_a: First event (earlier).
            event_b: Second event (later).

        Returns:
            True if gap is insufficient.
        """
        gap = event_b.start - event_a.end
        return timedelta(0) < gap < self.min_gap

    def _location_conflict(self, event_a: CalendarEvent, event_b: CalendarEvent) -> bool:
        """Check if there's a location conflict requiring travel time.

        Args:
            event_a: First event.
            event_b: Second event.

        Returns:
            True if location conflict exists.
        """
        if not event_a.location or not event_b.location:
            return False

        # Skip if same location
        if event_a.location == event_b.location:
            return False

        # Check if both are known locations with travel times
        loc_a = self._get_location_info(event_a.location)
        loc_b = self._get_location_info(event_b.location)

        if loc_a and loc_b:
            # Calculate gap
            gap = event_b.start - event_a.end
            # If different locations and gap is less than travel buffer
            return gap < self.travel_buffer

        return False

    def _get_location_info(self, location_name: str) -> dict | None:
        """Get location info from configuration.

        Args:
            location_name: Location name to look up.

        Returns:
            Location info dict or None if not found.
        """
        for loc_key, loc_info in self.locations.items():
            if loc_key in location_name or location_name in loc_key:
                return loc_info
        return None

    def _create_conflict(
        self,
        conflict_type: str,
        events: list[CalendarEvent],
        description: str,
    ) -> dict[str, Any]:
        """Create a conflict dictionary.

        Args:
            conflict_type: Type of conflict (overlap, insufficient_gap, location_conflict).
            events: List of events involved in the conflict.
            description: Human-readable description of the conflict.

        Returns:
            Conflict dictionary.
        """
        return {
            "type": conflict_type,
            "events": [self._event_to_dict(e) for e in events],
            "description": description,
            "priorities": [self._calculate_priority(e) for e in events],
        }

    def _event_to_dict(self, event: CalendarEvent) -> dict[str, Any]:
        """Convert a CalendarEvent to a simplified dictionary.

        Args:
            event: CalendarEvent to convert.

        Returns:
            Dictionary with event details.
        """
        attendee_names = []
        for att in event.attendees:
            if att.display_name:
                attendee_names.append(att.display_name)
            else:
                attendee_names.append(att.email)

        return {
            "event_id": event.event_id,
            "title": event.title,
            "start": event.start.strftime("%H:%M"),
            "end": event.end.strftime("%H:%M"),
            "location": event.location or "Not specified",
            "organizer": event.organizer,
            "attendees": attendee_names,
            "is_recurring": event.recurrence is not None,
            "description": event.description,
        }

    def _calculate_priority(self, event: CalendarEvent) -> dict[str, Any]:
        """Calculate priority score for an event.

        Args:
            event: CalendarEvent to score.

        Returns:
            Dictionary with priority information.
        """
        # Check attendees for high-priority characters
        highest_priority = "low"
        key_attendee = None

        for att in event.attendees:
            char_info = self.characters.get(att.email)
            if char_info:
                char_priority = char_info.get("priority", "low")
                if self._priority_rank(char_priority) > self._priority_rank(highest_priority):
                    highest_priority = char_priority
                    key_attendee = char_info.get("name", att.email)

        # Check organizer
        if event.organizer:
            char_info = self.characters.get(event.organizer)
            if char_info:
                char_priority = char_info.get("priority", "low")
                if self._priority_rank(char_priority) > self._priority_rank(highest_priority):
                    highest_priority = char_priority
                    key_attendee = char_info.get("name", event.organizer)

        # Check title for priority keywords
        keywords = self.priorities.get("priority_keywords", {})
        title_lower = event.title.lower()

        for keyword in keywords.get("critical", []):
            if keyword.lower() in title_lower:
                highest_priority = "critical"
                break

        return {
            "level": highest_priority,
            "key_attendee": key_attendee,
            "is_recurring": event.recurrence is not None,
        }

    def _priority_rank(self, priority: str) -> int:
        """Convert priority string to numeric rank.

        Args:
            priority: Priority string (low, low-medium, medium, high, critical).

        Returns:
            Numeric rank.
        """
        ranks = {
            "low": 1,
            "low-medium": 2,
            "medium": 3,
            "high": 4,
            "critical": 5,
        }
        return ranks.get(priority, 1)

    def _deduplicate_conflicts(self, conflicts: list[dict]) -> list[dict]:
        """Remove duplicate conflicts involving the same events.

        Args:
            conflicts: List of conflicts to deduplicate.

        Returns:
            Deduplicated list of conflicts.
        """
        seen = set()
        unique_conflicts = []

        for conflict in conflicts:
            # Create a key from sorted event IDs
            event_ids = tuple(sorted(e["event_id"] for e in conflict["events"]))
            if event_ids not in seen:
                seen.add(event_ids)
                unique_conflicts.append(conflict)

        return unique_conflicts


def format_conflicts_for_prompt(
    day_name: str,
    date_str: str,
    conflicts: list[dict],
    all_events: list[CalendarEvent],
) -> str:
    """Format conflicts and events for the LLM prompt.

    Args:
        day_name: Name of the day (e.g., "Monday").
        date_str: Date string (e.g., "January 19, 2026").
        conflicts: List of detected conflicts.
        all_events: All events for the day.

    Returns:
        Formatted prompt string.
    """
    prompt_parts = [
        f"## Calendar for {day_name}, {date_str}",
        "",
        "### All Scheduled Events",
    ]

    # Sort events by start time
    sorted_events = sorted(all_events, key=lambda e: e.start)

    for event in sorted_events:
        attendee_str = ""
        if event.attendees:
            names = [a.display_name or a.email for a in event.attendees]
            attendee_str = f" (with: {', '.join(names)})"

        location_str = f" @ {event.location}" if event.location else ""

        prompt_parts.append(
            f"- {event.start.strftime('%H:%M')}-{event.end.strftime('%H:%M')}: "
            f"**{event.title}**{location_str}{attendee_str}"
        )

    prompt_parts.extend(["", "### Detected Conflicts", ""])

    if not conflicts:
        prompt_parts.append("✅ No conflicts detected for this day.")
    else:
        for i, conflict in enumerate(conflicts, 1):
            prompt_parts.append(f"**Conflict #{i}: {conflict['type'].replace('_', ' ').title()}**")
            prompt_parts.append(f"Description: {conflict['description']}")
            prompt_parts.append("Involved meetings:")

            for j, event in enumerate(conflict["events"]):
                priority = conflict["priorities"][j]
                prompt_parts.append(
                    f"  - {event['start']}-{event['end']}: {event['title']} "
                    f"(Priority: {priority['level']}, Key: {priority['key_attendee'] or 'N/A'})"
                )

            prompt_parts.append("")

    prompt_parts.extend([
        "",
        "### Your Task",
        "Analyze each conflict and provide specific recommendations for how Jordan should handle them.",
        "Consider attendee priorities, meeting importance, and business implications.",
    ])

    return "\n".join(prompt_parts)


def print_briefing_header(day_name: str, date_str: str) -> None:
    """Print the daily briefing header.

    Args:
        day_name: Name of the day.
        date_str: Date string.
    """
    print("\n" + "═" * 65)
    print(f"📅 CALENDAR BRIEFING - {day_name}, {date_str}")
    print("═" * 65)


def print_conflict_summary(conflicts: list[dict], events: list[CalendarEvent]) -> None:
    """Print a summary of conflicts for the day.

    Args:
        conflicts: List of detected conflicts.
        events: List of events for the day.
    """
    print(f"\n📊 Day Summary:")
    print(f"   • Total meetings: {len(events)}")
    print(f"   • Conflicts detected: {len(conflicts)}")

    if conflicts:
        conflict_types = {}
        for c in conflicts:
            ctype = c["type"]
            conflict_types[ctype] = conflict_types.get(ctype, 0) + 1

        for ctype, count in conflict_types.items():
            print(f"   • {ctype.replace('_', ' ').title()}: {count}")


def run_agent(
    model: str,
    ollama_host: str,
    ues_host: str,
    skip_llm: bool = False,
) -> None:
    """Run the calendar conflict resolver agent.

    Args:
        model: The Ollama model to use for analysis.
        ollama_host: The Ollama server URL.
        ues_host: The UES server URL.
        skip_llm: If True, skip LLM calls and show conflicts only.
    """
    system_prompt = load_system_prompt()
    priorities = load_priorities()
    scenario_path = Path(__file__).parent / "scenario.ues-scenario.json"

    print("=" * 65)
    print("Calendar Conflict Resolver Agent")
    print("=" * 65)
    print(f"Model: {model}")
    print(f"Ollama: {ollama_host}")
    print(f"UES: {ues_host}")
    print("=" * 65)

    # Load the scenario
    print("\nLoading scenario...")
    load_scenario(scenario_path, ues_host)
    print("Scenario loaded successfully.")

    # Initialize conflict detector
    detector = ConflictDetector(priorities)

    with UESClient(base_url=ues_host) as client:
        # Start the simulation
        client.simulation.start(auto_advance=False)
        print("Simulation started.\n")

        # Get initial time
        time_state = client.time.get_state()
        current_time = time_state.current_time
        print(f"Simulator start time: {current_time.strftime('%Y-%m-%d %H:%M %Z')}")

        # Resume simulation
        client.time.resume()

        # Define the days we'll process (Mon-Fri, Jan 19-23, 2026)
        days = [
            ("Monday", datetime(2026, 1, 19, 8, 0, tzinfo=timezone.utc)),
            ("Tuesday", datetime(2026, 1, 20, 8, 0, tzinfo=timezone.utc)),
            ("Wednesday", datetime(2026, 1, 21, 8, 0, tzinfo=timezone.utc)),
            ("Thursday", datetime(2026, 1, 22, 8, 0, tzinfo=timezone.utc)),
            ("Friday", datetime(2026, 1, 23, 8, 0, tzinfo=timezone.utc)),
        ]

        for day_name, day_start in days:
            day_end = day_start + timedelta(days=1)
            date_str = day_start.strftime("%B %d, %Y")

            # Advance time to ensure events are executed for this day
            # We need to advance past the start time to execute pending events
            current = client.time.get_state().current_time
            if current <= day_start:
                # Advance to 1 second past day start to execute any events scheduled at day_start
                target_seconds = (day_start - current).total_seconds() + 1
                result = client.time.advance(seconds=int(target_seconds))
                if result.events_executed > 0:
                    print(f"   (Executed {result.events_executed} calendar events)")

            # Query calendar events for this day
            query_result = client.calendar.query(
                start=day_start,
                end=day_end,
                sort_by="start",
                sort_order="asc",
            )

            events = query_result.events

            # Print header
            print_briefing_header(day_name, date_str)

            if not events:
                print("\n✅ No meetings scheduled for today.")
                print("-" * 65)
                continue

            # Detect conflicts
            conflicts = detector.detect_conflicts(events)

            # Print summary
            print_conflict_summary(conflicts, events)

            if not conflicts:
                print("\n✅ No scheduling conflicts detected.")
                print("-" * 65)
                continue

            # Build prompt and get LLM analysis
            prompt = format_conflicts_for_prompt(day_name, date_str, conflicts, events)

            if skip_llm:
                print("\n📋 CONFLICT DETAILS (LLM analysis skipped):")
                print("-" * 65)
                for conflict in conflicts:
                    print(f"\n  🔴 {conflict['description']}")
                    for j, event in enumerate(conflict["events"]):
                        priority = conflict["priorities"][j]
                        print(f"     - {event['start']}-{event['end']}: {event['title']}")
                        print(f"       Priority: {priority['level']}, Key: {priority.get('key_attendee', 'N/A')}")
            else:
                print("\n🤔 Analyzing conflicts with LLM...")

                try:
                    recommendations = call_ollama(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        model=model,
                        ollama_host=ollama_host,
                    )

                    print("\n📝 RECOMMENDATIONS:")
                    print("-" * 65)
                    print(recommendations.strip())

                except httpx.HTTPError as e:
                    print(f"\n❌ LLM analysis failed: {e}")
                    print("Showing conflict details only:")
                    for conflict in conflicts:
                        print(f"\n  🔴 {conflict['description']}")
                        for event in conflict["events"]:
                            print(f"     - {event['start']}-{event['end']}: {event['title']}")

            print("\n" + "-" * 65)

        # Final summary
        print("\n" + "═" * 65)
        print("📊 WEEKLY SUMMARY")
        print("═" * 65)
        print("Calendar conflict analysis complete for the week.")
        print("Review the recommendations above and take action as needed.")
        print("=" * 65)

        # Stop simulation
        client.simulation.stop()


def main() -> None:
    """Parse arguments and run the agent."""
    parser = argparse.ArgumentParser(
        description="Calendar Conflict Resolver Agent for UES",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent.py
  python agent.py --model llama3.2:3b
  python agent.py --ues-host http://localhost:8000 --ollama-host http://localhost:11434
  python agent.py --skip-llm  # Skip LLM calls, show conflicts only
        """,
    )
    parser.add_argument(
        "--model",
        default="gemma3:12b",
        help="Ollama model to use for conflict analysis (default: gemma3:12b)",
    )
    parser.add_argument(
        "--ollama-host",
        default="http://localhost:11434",
        help="Ollama server URL (default: http://localhost:11434)",
    )
    parser.add_argument(
        "--ues-host",
        default="http://localhost:8000",
        help="UES server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM calls and show conflict details only",
    )

    args = parser.parse_args()

    print(f"Using model: {args.model}")
    print(f"Ollama host: {args.ollama_host}")
    print(f"UES host: {args.ues_host}")
    if args.skip_llm:
        print("LLM analysis: SKIPPED")
    print()

    run_agent(
        model=args.model,
        ollama_host=args.ollama_host,
        ues_host=args.ues_host,
        skip_llm=args.skip_llm,
    )


if __name__ == "__main__":
    main()
