#!/usr/bin/env python3
"""SMS Group Chat Simulator Agent.

A simulator-side agent that manages multiple distinct personalities in a group
SMS chat, creating realistic group dynamics with agreements, disagreements,
and natural conversation flow.

This agent demonstrates:
- Multi-character simulation with distinct personalities
- WebSocket-based event monitoring for sms.sent events
- Variable response delays per character
- Inter-character dynamics and reactions
- Conversation state tracking

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
from typing import Any

import httpx
import websockets

from ues.client import AsyncUESClient


# Configuration constants
GROUP_THREAD_ID = "weekend-warriors-camping"


def load_system_prompt() -> str:
    """Load the system prompt template from system_prompt.txt."""
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


def calculate_response_delay(character: dict) -> timedelta:
    """Calculate response delay based on character settings.

    Args:
        character: Character definition with response_delay settings.

    Returns:
        Timedelta for when the response should be scheduled.
    """
    delay_config = character.get("response_delay", {})
    min_seconds = delay_config.get("min_seconds", 30)
    max_seconds = delay_config.get("max_seconds", 300)
    delay_seconds = random.uniform(min_seconds, max_seconds)
    return timedelta(seconds=delay_seconds)


def should_character_respond(character: dict, message_content: str, sender: str) -> bool:
    """Determine if a character should respond to a message.

    Args:
        character: Character definition.
        message_content: The content of the message.
        sender: Phone number of the message sender.

    Returns:
        True if the character should respond.
    """
    # Characters don't respond to their own messages
    if character.get("phone_number") == sender:
        return False
    
    # Check response probability
    probability = character.get("response_probability", 0.7)
    
    # Increase probability if character is directly mentioned
    if character.get("name", "").lower() in message_content.lower():
        probability = min(1.0, probability + 0.3)
    
    # Questions typically warrant more responses
    if "?" in message_content:
        probability = min(1.0, probability + 0.2)
    
    return random.random() < probability


def format_recent_messages(messages: list[dict], limit: int = 10) -> str:
    """Format recent messages for the LLM prompt.

    Args:
        messages: List of message dictionaries.
        limit: Maximum number of messages to include.

    Returns:
        Formatted string of recent messages.
    """
    recent = messages[-limit:] if len(messages) > limit else messages
    formatted = []
    for msg in recent:
        sender = msg.get("from_number", "Unknown")
        body = msg.get("body", "")
        formatted.append(f"{sender}: {body}")
    return "\n".join(formatted) if formatted else "No recent messages."


def format_decisions(conversation_state: dict) -> str:
    """Format decisions already made.

    Args:
        conversation_state: Current conversation state tracking.

    Returns:
        Formatted string of decisions made.
    """
    decisions = conversation_state.get("decisions_made", {})
    if not decisions:
        return "No decisions have been made yet."
    
    formatted = []
    for topic, decision in decisions.items():
        if decision:
            formatted.append(f"- {topic}: {decision}")
    return "\n".join(formatted) if formatted else "No decisions have been made yet."


def build_generation_prompt(
    character: dict,
    latest_message: dict,
    recent_messages: list[dict],
    conversation_state: dict,
    characters_data: dict,
) -> str:
    """Build the prompt for generating a character's response.

    Args:
        character: Character definition.
        latest_message: The message to respond to.
        recent_messages: Recent messages in the conversation.
        conversation_state: Current conversation state.
        characters_data: Full characters data.

    Returns:
        Complete prompt for the LLM.
    """
    # Get character opinions as formatted string
    opinions = character.get("opinions", {})
    opinions_str = "\n".join([f"- {k}: {v}" for k, v in opinions.items()])
    
    # Get conversation summary
    summary_parts = []
    if conversation_state.get("current_topic"):
        summary_parts.append(f"Current topic: {conversation_state['current_topic']}")
    if conversation_state.get("pending_questions"):
        summary_parts.append(f"Open questions: {', '.join(conversation_state['pending_questions'])}")
    conversation_summary = "\n".join(summary_parts) if summary_parts else "General camping trip planning discussion."
    
    prompt = f"""## Message You Are Responding To

From: {latest_message.get('from_number', 'Unknown')}
Message: {latest_message.get('body', '')}

## Recent Conversation History

{format_recent_messages(recent_messages)}

## Your Response

Generate a single SMS response as {character['name']}. Keep it short and in character."""

    return prompt


def build_system_prompt(
    template: str,
    character: dict,
    conversation_state: dict,
    recent_messages: list[dict],
) -> str:
    """Build the system prompt with character-specific details.

    Args:
        template: System prompt template.
        character: Character definition.
        conversation_state: Current conversation state.
        recent_messages: Recent messages for context.

    Returns:
        Populated system prompt.
    """
    opinions = character.get("opinions", {})
    opinions_str = "\n".join([f"- {k}: {v}" for k, v in opinions.items()])
    
    summary_parts = []
    if conversation_state.get("current_topic"):
        summary_parts.append(f"Current topic: {conversation_state['current_topic']}")
    conversation_summary = "\n".join(summary_parts) if summary_parts else "Planning a weekend camping trip"
    
    return template.format(
        character_name=character["name"],
        character_personality=character.get("personality", ""),
        character_style=character.get("communication_style", ""),
        character_opinions=opinions_str or "No specific opinions",
        conversation_summary=conversation_summary,
        decisions_made=format_decisions(conversation_state),
        recent_messages=format_recent_messages(recent_messages),
    )


class ConversationStateTracker:
    """Tracks conversation state including decisions and pending questions."""
    
    def __init__(self):
        self.decisions_made: dict[str, str | None] = {
            "destination": None,
            "departure_time": None,
            "transportation": None,
        }
        self.pending_questions: list[str] = []
        self.current_topic: str | None = None
        self.character_opinions: dict[str, dict] = {}
    
    def to_dict(self) -> dict:
        """Convert state to dictionary."""
        return {
            "decisions_made": self.decisions_made,
            "pending_questions": self.pending_questions,
            "current_topic": self.current_topic,
            "character_opinions": self.character_opinions,
        }
    
    def update_from_message(self, message: dict) -> None:
        """Update state based on a new message.

        Args:
            message: The new message dictionary.
        """
        body = message.get("body", "").lower()
        
        # Detect topics being discussed
        if "where" in body or "pine ridge" in body or "lake haven" in body or "mountain view" in body:
            self.current_topic = "destination"
        elif "when" in body or "time" in body or "leave" in body or "friday" in body or "saturday" in body:
            self.current_topic = "departure_time"
        elif "drive" in body or "car" in body or "ride" in body:
            self.current_topic = "transportation"
        
        # Detect questions
        if "?" in body:
            # Extract the question (simple approach - get sentence with ?)
            sentences = body.split("?")
            for s in sentences[:-1]:  # All but last (which is after the ?)
                q = s.strip().split(".")[-1].strip() + "?"
                if q and len(q) > 5 and q not in self.pending_questions:
                    self.pending_questions.append(q)
                    # Keep only recent questions
                    self.pending_questions = self.pending_questions[-5:]


async def run_agent(
    model: str,
    ollama_host: str,
    ues_host: str,
) -> None:
    """Run the SMS group chat simulator agent.

    Args:
        model: The Ollama model to use for generation.
        ollama_host: The Ollama server URL.
        ues_host: The UES server URL.
    """
    system_prompt_template = load_system_prompt()
    characters_data = load_characters()
    characters = characters_data["characters"]
    user_data = characters_data.get("user", {})
    user_phone = user_data.get("phone_number", "+15550000001")
    scenario_path = Path(__file__).parent / "scenario.ues-scenario.json"
    
    # Initialize conversation state tracker
    conversation_state = ConversationStateTracker()

    print("=" * 60)
    print("SMS Group Chat Simulator Agent")
    print("=" * 60)
    print(f"Model: {model}")
    print(f"Ollama: {ollama_host}")
    print(f"UES: {ues_host}")
    print(f"Characters: {len(characters)}")
    for phone, char in characters.items():
        print(f"  - {char['name']} ({char['emoji']}) {phone}")
    print(f"User: {user_data.get('name', 'Unknown')} ({user_phone})")
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

        # Get initial message history
        sms_state = await client.sms.get_state()
        recent_messages = []
        for msg in sms_state.messages.values():
            if msg.thread_id == GROUP_THREAD_ID:
                recent_messages.append({
                    "message_id": msg.message_id,
                    "from_number": msg.from_number,
                    "body": msg.body,
                    "sent_at": msg.sent_at.isoformat(),
                })
        # Sort by sent_at
        recent_messages.sort(key=lambda m: m["sent_at"])
        
        print(f"Loaded {len(recent_messages)} existing messages in thread.\n")

        # Connect to WebSocket and subscribe to sms.sent events
        ws_url = ues_host.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws"
        
        print("Connecting to WebSocket...")
        print("Waiting for user to send messages to the group chat...")
        print("(Send SMS messages via the API or Web UI to trigger responses)\n")

        async with websockets.connect(ws_url) as ws:
            # Subscribe to sms.sent events (when user sends a message)
            subscribe_msg = {
                "action": "subscribe",
                "events": ["sms.sent"],
            }
            await ws.send(json.dumps(subscribe_msg))
            
            # Wait for subscription confirmation
            response = await ws.recv()
            response_data = json.loads(response)
            if response_data.get("type") == "subscription.updated":
                print("✓ Subscribed to sms.sent events\n")
            else:
                print(f"⚠️  Unexpected response: {response_data}\n")

            # Track scheduled responses to avoid duplicates
            pending_responses: dict[str, asyncio.Task] = {}

            # Main event loop
            while True:
                try:
                    message = await ws.recv()
                    event = json.loads(message)
                    
                    if event.get("type") != "sms.sent":
                        continue
                    
                    event_data = event.get("data", {})
                    body_preview = event_data.get("preview", "")
                    
                    print(f"\n📱 SMS sent event detected!")
                    print(f"   Preview: {body_preview[:50]}...")
                    
                    # Get the full message from SMS state to find sender
                    sms_state = await client.sms.get_state()
                    
                    # Find messages from the user in the group thread
                    sent_messages = [
                        msg for msg in sms_state.messages.values()
                        if msg.from_number == user_phone and msg.thread_id == GROUP_THREAD_ID
                    ]
                    if not sent_messages:
                        print("   ⏭️  Message not from user in group thread, skipping")
                        continue
                    
                    # Get the most recent user message
                    sent_messages.sort(key=lambda m: m.sent_at, reverse=True)
                    user_message = sent_messages[0]
                    
                    # Skip if this message was already processed (check if body matches preview)
                    msg_preview = user_message.body[:50] + "..." if len(user_message.body) > 50 else user_message.body
                    if msg_preview != body_preview:
                        print("   ⏭️  Message preview doesn't match latest user message")
                        continue
                    
                    print(f"   From: {user_message.from_number}")
                    print(f"   Full message: {user_message.body}")
                    
                    # Update recent messages list
                    recent_messages.append({
                        "message_id": user_message.message_id,
                        "from_number": user_message.from_number,
                        "body": user_message.body,
                        "sent_at": user_message.sent_at.isoformat(),
                    })
                    
                    # Update conversation state
                    conversation_state.update_from_message({
                        "body": user_message.body,
                        "from_number": user_message.from_number,
                    })
                    
                    print(f"   Full message: {user_message.body}")
                    
                    # Determine which characters should respond
                    responding_characters = []
                    for phone, character in characters.items():
                        if should_character_respond(character, user_message.body, user_message.from_number):
                            responding_characters.append((phone, character))
                    
                    if not responding_characters:
                        print("   📭 No characters chose to respond this time.\n")
                        continue
                    
                    print(f"\n   🎭 {len(responding_characters)} character(s) will respond:")
                    
                    # Generate and schedule responses for each character
                    for phone, character in responding_characters:
                        char_name = character["name"]
                        print(f"\n   [{char_name}] Generating response...")
                        
                        # Build prompts
                        system_prompt = build_system_prompt(
                            template=system_prompt_template,
                            character=character,
                            conversation_state=conversation_state.to_dict(),
                            recent_messages=recent_messages,
                        )
                        
                        generation_prompt = build_generation_prompt(
                            character=character,
                            latest_message={
                                "from_number": user_message.from_number,
                                "body": user_message.body,
                            },
                            recent_messages=recent_messages,
                            conversation_state=conversation_state.to_dict(),
                            characters_data=characters_data,
                        )
                        
                        try:
                            response_body = call_ollama(
                                prompt=generation_prompt,
                                system_prompt=system_prompt,
                                model=model,
                                ollama_host=ollama_host,
                            )
                            response_body = response_body.strip()
                            
                            # Remove any accidental quoting or prefixes
                            if response_body.startswith('"') and response_body.endswith('"'):
                                response_body = response_body[1:-1]
                            if response_body.startswith(f"{char_name}:"):
                                response_body = response_body[len(f"{char_name}:"):].strip()
                            
                        except httpx.HTTPError as e:
                            print(f"   [{char_name}] ❌ LLM generation failed: {e}")
                            continue
                        
                        # Calculate response delay
                        delay = calculate_response_delay(character)
                        current_time = (await client.time.get_state()).current_time
                        scheduled_time = current_time + delay
                        
                        # Get all participant numbers for the group
                        conversation = sms_state.conversations.get(GROUP_THREAD_ID)
                        if conversation:
                            to_numbers = [
                                p.phone_number for p in conversation.participants
                                if p.phone_number != phone
                            ]
                        else:
                            to_numbers = [user_phone]
                        
                        # Schedule the SMS response
                        await client.events.create(
                            modality="sms",
                            scheduled_time=scheduled_time,
                            data={
                                "modality_type": "sms",
                                "action": "receive_message",
                                "timestamp": scheduled_time.isoformat(),
                                "message_data": {
                                    "from_number": phone,
                                    "to_numbers": to_numbers,
                                    "body": response_body,
                                    "thread_id": GROUP_THREAD_ID,
                                    "message_type": "sms",
                                },
                            },
                        )
                        
                        print(f"   [{char_name}] ✓ Response scheduled for {scheduled_time.strftime('%H:%M:%S')}")
                        print(f"   [{char_name}] (in {delay.total_seconds():.0f} seconds)")
                        print(f"   [{char_name}] Message: {response_body[:80]}{'...' if len(response_body) > 80 else ''}")
                        
                        # Add to recent messages for subsequent characters
                        recent_messages.append({
                            "message_id": f"pending-{phone}",
                            "from_number": phone,
                            "body": response_body,
                            "sent_at": scheduled_time.isoformat(),
                        })
                    
                    print("\n" + "-" * 40)

                except websockets.ConnectionClosed:
                    print("\nWebSocket connection closed.")
                    break
                except KeyboardInterrupt:
                    print("\nShutting down...")
                    break


def main():
    """Parse arguments and run the agent."""
    parser = argparse.ArgumentParser(
        description="SMS Group Chat Simulator Agent for UES",
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
