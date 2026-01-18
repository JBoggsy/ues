#!/usr/bin/env python3
"""Email Reply Generator Agent.

A simulator-side agent that monitors for emails sent by the user and generates
realistic replies from the recipient character. Uses WebSocket to receive
real-time email.sent events and schedules response events via the API.

This agent demonstrates:
- WebSocket-based event monitoring
- Character personality simulation using LLMs
- Thread-aware conversation tracking
- Variable response delays for realism

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
    """Load the system prompt from system_prompt.txt."""
    prompt_path = Path(__file__).parent / "system_prompt.txt"
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
        prompt: The user prompt containing email and character data.
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
    
    # Check if character only responds during work hours
    work_hours = character.get("work_hours")
    if work_hours and responsiveness.get("work_hours_only", False):
        # For simplicity, we'll just use the delay as-is
        # A more sophisticated implementation would check actual work hours
        pass
    
    return timedelta(minutes=delay_minutes)


def format_thread_for_prompt(thread_emails: list[dict]) -> str:
    """Format email thread history for the LLM prompt.

    Args:
        thread_emails: List of emails in the thread, ordered chronologically.

    Returns:
        Formatted string representation of the thread.
    """
    if not thread_emails:
        return "No previous emails in this thread."
    
    formatted = []
    for email in thread_emails:
        formatted.append(f"""---
From: {email['from_address']}
To: {', '.join(email['to_addresses'])}
Subject: {email['subject']}
Sent: {email['sent_at']}

{email['body_text']}
---""")
    
    return "\n\n".join(formatted)


def build_generation_prompt(
    character: dict,
    user_email: dict,
    thread_emails: list[dict],
    user_context: dict,
) -> str:
    """Build the prompt for generating a character's email reply.

    Args:
        character: Character definition.
        user_email: The email from the user that needs a reply.
        thread_emails: Previous emails in this thread.
        user_context: Information about the user (from characters.json).

    Returns:
        Complete prompt for the LLM.
    """
    thread_history = format_thread_for_prompt(thread_emails)
    
    prompt = f"""## Character Profile

Name: {character['name']}
Role: {character['role']}
Relationship to user: {character['relationship']}
Personality: {character['personality']}
Communication style: {character['communication_style']}

## User Context

The user you are replying to is: {user_context.get('name', 'Unknown')}
User's role: {user_context.get('role', 'Unknown')}
Context: {user_context.get('context', 'No additional context.')}

## Conversation Thread History

{thread_history}

## Email You Are Replying To

From: {user_email['from_address']}
To: {', '.join(user_email['to_addresses'])}
Subject: {user_email['subject']}
Sent: {user_email['sent_at']}

{user_email['body_text']}

## Your Task

Write a reply to this email as {character['name']}. Stay in character and respond naturally to what the user has written."""

    return prompt


def get_thread_emails(
    email_state: dict,
    thread_id: str,
    exclude_message_id: str | None = None,
) -> list[dict]:
    """Get all emails in a thread, ordered chronologically.

    Args:
        email_state: Full email state from API.
        thread_id: Thread ID to look up.
        exclude_message_id: Optional message ID to exclude (e.g., the current email).

    Returns:
        List of emails in the thread, ordered by sent_at.
    """
    thread = email_state.get("threads", {}).get(thread_id)
    if not thread:
        return []
    
    emails = []
    for message_id in thread.get("message_ids", []):
        if message_id == exclude_message_id:
            continue
        email = email_state.get("emails", {}).get(message_id)
        if email:
            emails.append(email)
    
    # Sort by sent_at
    emails.sort(key=lambda e: e.get("sent_at", ""))
    return emails


def find_sent_email_by_recipient(
    email_state: dict,
    recipient_email: str,
    subject: str,
) -> dict | None:
    """Find a sent email by recipient and subject.

    Since email.sent event only provides email_id (which is the event ID, not
    message ID), we need to search for the email by other attributes.

    Args:
        email_state: Full email state from API.
        recipient_email: Email address of the recipient.
        subject: Subject line of the email.

    Returns:
        The matching email dict, or None if not found.
    """
    for email in email_state.get("emails", {}).values():
        if email.get("folder") == "sent":
            if recipient_email in email.get("to_addresses", []):
                if email.get("subject") == subject:
                    return email
    return None


async def run_agent(
    model: str,
    ollama_host: str,
    ues_host: str,
) -> None:
    """Run the email reply generator agent.

    Args:
        model: The Ollama model to use for generation.
        ollama_host: The Ollama server URL.
        ues_host: The UES server URL.
    """
    system_prompt = load_system_prompt()
    characters_data = load_characters()
    characters = characters_data["characters"]
    user_context = characters_data.get("user", {})
    scenario_path = Path(__file__).parent / "scenario.ues-scenario.json"

    print("=" * 60)
    print("Email Reply Generator Agent")
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

        # Connect to WebSocket and subscribe to email.sent events
        ws_url = ues_host.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws"
        
        print("Connecting to WebSocket...")
        print("Waiting for user to send emails...")
        print("(Advance time or send emails via API to trigger the agent)\n")

        async with websockets.connect(ws_url) as ws:
            # Subscribe to email.sent events
            subscribe_msg = {
                "type": "subscribe",
                "events": ["email.sent"],
            }
            await ws.send(json.dumps(subscribe_msg))
            
            # Wait for subscription confirmation
            response = await ws.recv()
            response_data = json.loads(response)
            if response_data.get("type") == "subscription.updated":
                print("✓ Subscribed to email.sent events\n")

            # Main event loop
            while True:
                try:
                    message = await ws.recv()
                    event = json.loads(message)
                    
                    if event.get("type") != "email.sent":
                        continue
                    
                    event_data = event.get("data", {})
                    recipients = event_data.get("to", [])
                    subject = event_data.get("subject", "")
                    
                    print(f"\n📧 Email sent detected!")
                    print(f"   To: {', '.join(recipients)}")
                    print(f"   Subject: {subject}")
                    
                    # Check if any recipient is a known character
                    for recipient in recipients:
                        if recipient not in characters:
                            print(f"   ⏭️  Skipping {recipient} (not a known character)")
                            continue
                        
                        character = characters[recipient]
                        print(f"\n   🎭 Generating reply as {character['name']}...")
                        
                        # Get full email state to find the sent email and thread
                        email_state = await client.email.get_state()
                        email_state_dict = email_state.model_dump()
                        
                        # Find the sent email
                        sent_email = find_sent_email_by_recipient(
                            email_state_dict,
                            recipient,
                            subject,
                        )
                        
                        if not sent_email:
                            print(f"   ⚠️  Could not find sent email in state")
                            continue
                        
                        # Get thread history
                        thread_id = sent_email.get("thread_id")
                        thread_emails = get_thread_emails(
                            email_state_dict,
                            thread_id,
                            exclude_message_id=sent_email.get("message_id"),
                        )
                        
                        if thread_emails:
                            print(f"   📜 Thread has {len(thread_emails)} previous email(s)")
                        
                        # Build prompt and generate response
                        prompt = build_generation_prompt(
                            character=character,
                            user_email=sent_email,
                            thread_emails=thread_emails,
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
                        references = sent_email.get("references", []).copy()
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
                                "thread_id": thread_id,
                                "in_reply_to": sent_email.get("message_id"),
                                "references": references,
                            },
                        )
                        
                        print(f"   ✓ Reply scheduled for {scheduled_time.strftime('%H:%M:%S')}")
                        print(f"   (in {delay.total_seconds() / 60:.1f} minutes)")
                        print(f"\n   --- Preview ---")
                        # Show first 200 chars of reply
                        preview = reply_body[:200] + "..." if len(reply_body) > 200 else reply_body
                        print(f"   {preview}")
                        print(f"   ----------------\n")

                except websockets.ConnectionClosed:
                    print("\nWebSocket connection closed.")
                    break
                except KeyboardInterrupt:
                    print("\nShutting down...")
                    break


def main():
    """Parse arguments and run the agent."""
    parser = argparse.ArgumentParser(
        description="Email Reply Generator Agent for UES",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent.py
  python agent.py --model llama3.2:3b
  python agent.py --ues-host http://localhost:8000 --ollama-host http://localhost:11434
        """,
    )
    parser.add_argument(
        "--model",
        default="gemma3:12b",
        help="Ollama model to use for email generation (default: gemma3:12b)",
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
