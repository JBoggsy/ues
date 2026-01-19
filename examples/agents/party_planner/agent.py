#!/usr/bin/env python3
"""Party Planner Integration Test Agent.

A simulator-side agent that monitors for party-related emails and SMS messages,
then generates realistic replies from the guest and vendor characters defined
in characters.json.

This agent demonstrates:
- WebSocket-based event monitoring for both email.sent and sms.sent events
- Character personality simulation using LLMs
- Multi-modal response generation (email and SMS)
- Variable response delays for realism
- RSVP tracking based on predefined character responses

Usage:
    python agent.py [--model MODEL] [--ollama-host HOST] [--ues-host HOST]

Example:
    python agent.py --model gemma3:12b --ollama-host http://localhost:11434
"""

import argparse
import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import websockets

from client import AsyncUESClient


def load_system_prompt() -> str:
    """Load the system prompt from system_prompts/guest.txt."""
    prompt_path = Path(__file__).parent / "system_prompts" / "guest.txt"
    return prompt_path.read_text().strip()


def load_characters() -> dict:
    """Load character definitions from characters.json."""
    characters_path = Path(__file__).parent / "characters.json"
    return json.loads(characters_path.read_text())


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
        prompt: The user prompt containing message and character data.
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
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["response"]


def calculate_response_delay(character: dict, current_time: datetime) -> timedelta:
    """Calculate a realistic response delay based on character settings.

    Args:
        character: Character definition with responsiveness settings.
        current_time: Current simulator time.

    Returns:
        Timedelta for when the response should be scheduled.
    """
    responsiveness = character.get("responsiveness", {})
    min_delay = responsiveness.get("min_delay_minutes", 5)
    max_delay = responsiveness.get("max_delay_minutes", 30)

    # Add some randomness within the character's response window
    delay_minutes = random.uniform(min_delay, max_delay)

    return timedelta(minutes=delay_minutes)


def build_email_generation_prompt(
    character: dict,
    user_email: dict,
    user_context: dict,
) -> str:
    """Build the prompt for generating a character's email reply.

    Args:
        character: Character definition.
        user_email: The email from the user that needs a reply.
        user_context: Information about the user (from characters.json).

    Returns:
        Complete prompt for the LLM.
    """
    rsvp_info = ""
    if "rsvp_response" in character:
        rsvp_info = f"""
## RSVP Information (IMPORTANT - Follow This)
Your predefined RSVP response: {character.get('rsvp_response', 'unknown').upper()}
Additional notes to include: {character.get('rsvp_notes', 'None')}
"""

    prompt = f"""## Character Profile

Name: {character['name']}
Role: {character['role']}
Relationship to user: {character['relationship']}
Personality: {character['personality']}
Communication style: {character['communication_style']}
{rsvp_info}
## User Context

The user you are replying to is: {user_context.get('name', 'Unknown')}
User's role: {user_context.get('role', 'Unknown')}
Context: {user_context.get('context', 'No additional context.')}

## Email You Are Replying To

From: {user_email.get('from_address', 'unknown')}
To: {', '.join(user_email.get('to_addresses', []))}
Subject: {user_email.get('subject', 'No subject')}

{user_email.get('body_text', '')}

## Your Task

Write a reply to this email as {character['name']}. Stay in character and respond naturally to what the user has written. If this is a party invitation, follow your predefined RSVP response."""

    return prompt


def build_sms_generation_prompt(
    character: dict,
    sms_message: dict,
    user_context: dict,
    is_group: bool = False,
) -> str:
    """Build the prompt for generating a character's SMS reply.

    Args:
        character: Character definition.
        sms_message: The SMS from the user that needs a reply.
        user_context: Information about the user (from characters.json).
        is_group: Whether this is a group SMS conversation.

    Returns:
        Complete prompt for the LLM.
    """
    rsvp_info = ""
    if "rsvp_response" in character:
        rsvp_info = f"""
## RSVP Information (IMPORTANT - Follow This)
Your predefined RSVP response: {character.get('rsvp_response', 'unknown').upper()}
Additional notes to include: {character.get('rsvp_notes', 'None')}
"""

    group_context = ""
    if is_group:
        group_context = """
Note: This is a GROUP SMS conversation. Keep your response appropriate for a group chat - others can see your message. Feel free to reference or tease other group members if appropriate for your character."""

    prompt = f"""## Character Profile

Name: {character['name']}
Role: {character['role']}
Personality: {character['personality']}
Communication style: {character['communication_style']}
{rsvp_info}
## Context

The user is: {user_context.get('name', 'Unknown')}
{user_context.get('context', '')}
{group_context}

## SMS Message You Are Replying To

From: {sms_message.get('from_number', 'unknown')}
Message: {sms_message.get('body', '')}

## Your Task

Write a SHORT SMS reply as {character['name']}. Keep it casual and brief like a real text message. If this is about a party invitation, follow your predefined RSVP response."""

    return prompt


def find_character_by_recipient(
    characters: dict,
    recipient: str,
) -> dict | None:
    """Find a character by email address or phone number.

    Args:
        characters: Character definitions from characters.json.
        recipient: Email address or phone number to look up.

    Returns:
        Character dict if found, None otherwise.
    """
    return characters.get(recipient)


async def handle_email_sent(
    event_data: dict,
    characters: dict,
    user_context: dict,
    system_prompt: str,
    model: str,
    ollama_host: str,
    client: AsyncUESClient,
) -> None:
    """Handle an email.sent event and generate responses.

    Args:
        event_data: The email.sent event data.
        characters: Character definitions.
        user_context: User context from characters.json.
        system_prompt: System prompt for LLM.
        model: Ollama model name.
        ollama_host: Ollama server URL.
        client: UES client instance.
    """
    recipients = event_data.get("to", [])
    subject = event_data.get("subject", "")

    print(f"\n📧 Email sent detected!")
    print(f"   To: {', '.join(recipients)}")
    print(f"   Subject: {subject}")

    for recipient in recipients:
        character = find_character_by_recipient(characters, recipient)
        if not character:
            print(f"   ⏭️  Skipping {recipient} (not a known character)")
            continue

        print(f"\n   🎭 Generating reply as {character['name']}...")

        # Get full email state to find the sent email
        email_state = await client.email.get_state()
        email_state_dict = email_state.model_dump()

        # Find the sent email by recipient and subject
        sent_email = None
        for email in email_state_dict.get("emails", {}).values():
            if email.get("folder") == "sent":
                if recipient in email.get("to_addresses", []):
                    if email.get("subject") == subject:
                        sent_email = email
                        break

        if not sent_email:
            print(f"   ⚠️  Could not find sent email in state")
            continue

        # Build prompt and generate response
        prompt = build_email_generation_prompt(
            character=character,
            user_email=sent_email,
            user_context=user_context,
        )

        try:
            reply_body = call_ollama(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                ollama_host=ollama_host,
            )
        except httpx.HTTPError as e:
            print(f"   ❌ LLM generation failed: {e}")
            continue

        # Calculate response delay
        current_time = (await client.time.get_state()).current_time
        delay = calculate_response_delay(character, current_time)
        scheduled_time = current_time + delay

        # Determine reply subject
        reply_subject = subject
        if not reply_subject.startswith("Re: "):
            reply_subject = f"Re: {subject}"

        # Build references list for threading
        references = sent_email.get("references", []) or []
        if isinstance(references, list):
            references = references.copy()
        else:
            references = []
        if sent_email.get("message_id"):
            references.append(sent_email["message_id"])

        # Schedule the reply email
        await client.events.create(
            modality="email",
            scheduled_time=scheduled_time,
            data={
                "operation": "receive",
                "from_address": recipient,
                "to_addresses": [sent_email["from_address"]],
                "subject": reply_subject,
                "body_text": reply_body.strip(),
                "thread_id": sent_email.get("thread_id"),
                "in_reply_to": sent_email.get("message_id"),
                "references": references,
            },
        )

        print(f"   ✓ Reply scheduled for {scheduled_time.strftime('%H:%M:%S')}")
        print(f"   (in {delay.total_seconds() / 60:.1f} minutes)")
        print(f"\n   --- Preview ---")
        preview = reply_body[:200] + "..." if len(reply_body) > 200 else reply_body
        print(f"   {preview}")
        print(f"   ----------------\n")


async def handle_sms_sent(
    event_data: dict,
    characters: dict,
    user_context: dict,
    college_crew_thread: dict,
    system_prompt: str,
    model: str,
    ollama_host: str,
    client: AsyncUESClient,
) -> None:
    """Handle an sms.sent event and generate responses.

    Args:
        event_data: The sms.sent event data.
        characters: Character definitions.
        user_context: User context from characters.json.
        college_crew_thread: College crew group thread info.
        system_prompt: System prompt for LLM.
        model: Ollama model name.
        ollama_host: Ollama server URL.
        client: UES client instance.
    """
    to_numbers = event_data.get("to_numbers", [])
    body = event_data.get("body", "")

    print(f"\n📱 SMS sent detected!")
    print(f"   To: {', '.join(to_numbers)}")
    print(f"   Body: {body[:50]}...")

    # Check if this is a group message to the college crew
    crew_participants = set(college_crew_thread.get("participants", []))
    user_phone = user_context.get("phone", "")
    crew_recipients = crew_participants - {user_phone}

    is_group_sms = len(set(to_numbers) & crew_recipients) > 1

    for recipient in to_numbers:
        character = find_character_by_recipient(characters, recipient)
        if not character:
            print(f"   ⏭️  Skipping {recipient} (not a known character)")
            continue

        print(f"\n   🎭 Generating SMS reply as {character['name']}...")

        # Build the SMS message dict
        sms_message = {
            "from_number": user_phone,
            "to_numbers": to_numbers,
            "body": body,
        }

        # Build prompt and generate response
        prompt = build_sms_generation_prompt(
            character=character,
            sms_message=sms_message,
            user_context=user_context,
            is_group=is_group_sms,
        )

        try:
            reply_body = call_ollama(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                ollama_host=ollama_host,
            )
        except httpx.HTTPError as e:
            print(f"   ❌ LLM generation failed: {e}")
            continue

        # Calculate response delay
        current_time = (await client.time.get_state()).current_time
        delay = calculate_response_delay(character, current_time)
        scheduled_time = current_time + delay

        # Determine recipients for the reply
        if is_group_sms:
            # Reply to whole group
            reply_to = list(crew_participants - {recipient})
        else:
            # Reply just to sender
            reply_to = [user_phone]

        # Schedule the reply SMS
        await client.events.create(
            modality="sms",
            scheduled_time=scheduled_time,
            data={
                "action": "receive_message",
                "message_data": {
                    "from_number": recipient,
                    "to_numbers": reply_to,
                    "body": reply_body.strip(),
                    "message_type": "sms",
                },
            },
        )

        print(f"   ✓ SMS reply scheduled for {scheduled_time.strftime('%H:%M:%S')}")
        print(f"   (in {delay.total_seconds() / 60:.1f} minutes)")
        print(f"\n   --- Preview ---")
        preview = reply_body[:100] + "..." if len(reply_body) > 100 else reply_body
        print(f"   {preview}")
        print(f"   ----------------\n")


async def run_agent(
    model: str,
    ollama_host: str,
    ues_host: str,
) -> None:
    """Run the party planner simulator agent.

    Args:
        model: The Ollama model to use for generation.
        ollama_host: The Ollama server URL.
        ues_host: The UES server URL.
    """
    system_prompt = load_system_prompt()
    characters_data = load_characters()
    characters = characters_data["characters"]
    user_context = characters_data.get("user", {})
    college_crew_thread = characters_data.get("college_crew_thread", {})
    scenario_path = Path(__file__).parent / "scenario.ues-scenario.json"

    print("=" * 60)
    print("Party Planner Simulator Agent")
    print("=" * 60)
    print(f"Model: {model}")
    print(f"Ollama: {ollama_host}")
    print(f"UES: {ues_host}")
    print(f"Characters: {len(characters)}")
    print("=" * 60)

    # Load the scenario
    print("\nLoading scenario...")
    load_scenario(scenario_path, ues_host)
    print("Scenario loaded successfully.")

    async with AsyncUESClient(base_url=ues_host) as client:
        # Start the simulation
        await client.simulation.start(auto_advance=False)
        print("Simulation started.\n")

        # Get initial time
        time_state = await client.time.get_state()
        print(f"Simulator time: {time_state.current_time.strftime('%Y-%m-%d %H:%M %Z')}\n")

        # Resume simulation so events can execute
        await client.time.resume()

        # Connect to WebSocket and subscribe to email.sent and sms.sent events
        ws_url = ues_host.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws"

        print("Connecting to WebSocket...")
        print("Waiting for Sam to send party invitations...")
        print("(Advance time or send emails/SMS via API to trigger the agent)\n")

        async with websockets.connect(ws_url) as ws:
            # Subscribe to email.sent and sms.sent events
            subscribe_msg = {
                "type": "subscribe",
                "events": ["email.sent", "sms.sent"],
            }
            await ws.send(json.dumps(subscribe_msg))

            # Wait for subscription confirmation
            response = await ws.recv()
            response_data = json.loads(response)
            if response_data.get("type") == "subscription.updated":
                print("✓ Subscribed to email.sent and sms.sent events\n")

            # Main event loop
            while True:
                try:
                    message = await ws.recv()
                    event = json.loads(message)
                    event_type = event.get("type")

                    if event_type == "email.sent":
                        await handle_email_sent(
                            event_data=event.get("data", {}),
                            characters=characters,
                            user_context=user_context,
                            system_prompt=system_prompt,
                            model=model,
                            ollama_host=ollama_host,
                            client=client,
                        )
                    elif event_type == "sms.sent":
                        await handle_sms_sent(
                            event_data=event.get("data", {}),
                            characters=characters,
                            user_context=user_context,
                            college_crew_thread=college_crew_thread,
                            system_prompt=system_prompt,
                            model=model,
                            ollama_host=ollama_host,
                            client=client,
                        )

                except websockets.ConnectionClosed:
                    print("\nWebSocket connection closed.")
                    break
                except KeyboardInterrupt:
                    print("\nShutting down...")
                    break


def main():
    """Parse arguments and run the agent."""
    parser = argparse.ArgumentParser(
        description="Party Planner Simulator Agent for UES",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent.py
  python agent.py --model llama3.2:3b
  python agent.py --ues-host http://localhost:8000 --ollama-host http://localhost:11434

This agent simulates guests and vendors responding to party invitations.
It monitors for emails and SMS sent by the user (Sam Rivera) and generates
realistic replies based on character definitions in characters.json.
        """,
    )
    parser.add_argument(
        "--model",
        default="gemma3:12b",
        help="Ollama model to use for response generation (default: gemma3:12b)",
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

    args = parser.parse_args()

    asyncio.run(run_agent(
        model=args.model,
        ollama_host=args.ollama_host,
        ues_host=args.ues_host,
    ))


if __name__ == "__main__":
    main()
