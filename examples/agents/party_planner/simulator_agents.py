#!/usr/bin/env python3
"""Simulator-Side Agents for Party Planner.

These agents monitor for emails/SMS sent by the user-side AI assistant
and generate realistic responses from guests and vendors.

Agents:
- GuestResponseAgent: Generates responses from friends/family
- VendorResponseAgent: Generates responses from bakery/catering
- SMSResponseAgent: Generates responses in the college crew group chat

Usage:
    python simulator_agents.py [--model MODEL] [--ollama-host HOST] [--ues-host HOST]

Example:
    python simulator_agents.py --model gemma3:12b
"""

import argparse
import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from client import AsyncUESClient


# ============================================================================
# Configuration Loading
# ============================================================================


def load_characters() -> dict:
    """Load character definitions from characters.json."""
    characters_path = Path(__file__).parent / "characters.json"
    return json.loads(characters_path.read_text())


def load_system_prompt(prompt_name: str) -> str:
    """Load a system prompt template."""
    prompt_path = Path(__file__).parent / "system_prompts" / f"{prompt_name}.txt"
    return prompt_path.read_text().strip()


# ============================================================================
# LLM Integration
# ============================================================================


def call_ollama(
    prompt: str,
    system_prompt: str,
    model: str,
    ollama_host: str,
) -> str:
    """Call Ollama API to generate a response.

    Args:
        prompt: The user prompt containing context and instructions.
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


def calculate_response_delay(responsiveness: dict, current_time: datetime) -> timedelta:
    """Calculate a realistic response delay based on character settings.

    Args:
        responsiveness: Dict with min_delay_minutes, max_delay_minutes, work_hours_only.
        current_time: Current simulator time.

    Returns:
        Timedelta for when the response should be scheduled.
    """
    min_delay = responsiveness.get("min_delay_minutes", 5)
    max_delay = responsiveness.get("max_delay_minutes", 30)
    
    # Add randomness within the character's response window
    delay_minutes = random.uniform(min_delay, max_delay)
    
    return timedelta(minutes=delay_minutes)


# ============================================================================
# Guest Response Agent
# ============================================================================


class GuestResponseAgent:
    """Agent that generates responses from party guests (email)."""

    def __init__(
        self,
        client: AsyncUESClient,
        characters: dict,
        model: str,
        ollama_host: str,
    ):
        self.client = client
        self.characters = characters.get("characters", {})
        self.model = model
        self.ollama_host = ollama_host
        self.system_prompt = load_system_prompt("guest")
        self.processed_emails: set[str] = set()

    async def check_and_respond(self) -> list[dict]:
        """Check for new emails to guests and generate responses.
        
        Returns:
            List of response events scheduled.
        """
        responses = []
        email_state = await self.client.email.get_state()
        current_time = (await self.client.time.get_state()).current_time
        
        for email in email_state.emails.values():
            # Only process sent emails (to guests)
            if email.folder != "sent":
                continue
            
            # Skip already processed
            if email.message_id in self.processed_emails:
                continue
            
            # Check if any recipient is a known guest
            for recipient in email.to_addresses:
                recipient_lower = recipient.lower()
                if recipient_lower in self.characters:
                    character = self.characters[recipient_lower]
                    response = await self._generate_response(
                        email, character, current_time
                    )
                    if response:
                        responses.append(response)
            
            self.processed_emails.add(email.message_id)
        
        return responses

    async def _generate_response(
        self,
        email: Any,
        character: dict,
        current_time: datetime,
    ) -> dict | None:
        """Generate a response from a guest character."""
        # Check if this looks like a party invitation
        body_lower = (email.body_text or "").lower()
        subject_lower = (email.subject or "").lower()
        
        is_invitation = any(
            kw in body_lower or kw in subject_lower
            for kw in ["party", "invite", "housewarming", "january 31", "gathering"]
        )
        
        if not is_invitation:
            return None
        
        # Build prompt for LLM
        prompt = self._build_prompt(email, character)
        
        # Generate response
        response_text = call_ollama(
            prompt=prompt,
            system_prompt=self.system_prompt,
            model=self.model,
            ollama_host=self.ollama_host,
        )
        
        # Parse response (extract subject and body)
        subject, body = self._parse_email_response(response_text, email.subject)
        
        # Calculate delay
        delay = calculate_response_delay(
            character.get("responsiveness", {}), current_time
        )
        response_time = current_time + delay
        
        # Schedule the response
        await self.client.events.create(
            scheduled_time=response_time,
            modality="email",
            data={
                "operation": "receive",
                "from_address": character["email"],
                "to_addresses": ["sam.rivera@email.com"],
                "subject": subject,
                "body_text": body,
                "thread_id": email.thread_id,
                "in_reply_to": email.message_id,
            },
        )
        
        return {
            "character": character["name"],
            "scheduled_time": response_time.isoformat(),
            "subject": subject,
        }

    def _build_prompt(self, email: Any, character: dict) -> str:
        """Build the prompt for generating a guest response."""
        character_profile = json.dumps(character, indent=2)
        original_message = f"""From: {email.from_address}
To: {', '.join(email.to_addresses)}
Subject: {email.subject}
Date: {email.sent_at}

{email.body_text}"""
        
        return f"""Character Profile:
{character_profile}

Original Message:
{original_message}

Generate a response email from this character. The character should respond according to their personality and RSVP behavior defined in the profile."""

    def _parse_email_response(self, response: str, original_subject: str) -> tuple[str, str]:
        """Parse LLM response into subject and body."""
        lines = response.strip().split("\n")
        
        subject = f"Re: {original_subject}"
        body_start = 0
        
        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line[8:].strip()
                body_start = i + 1
                # Skip empty line after subject
                if body_start < len(lines) and not lines[body_start].strip():
                    body_start += 1
                break
        
        body = "\n".join(lines[body_start:]).strip()
        return subject, body


# ============================================================================
# SMS Response Agent
# ============================================================================


class SMSResponseAgent:
    """Agent that generates responses in the college crew SMS group."""

    def __init__(
        self,
        client: AsyncUESClient,
        characters: dict,
        model: str,
        ollama_host: str,
    ):
        self.client = client
        self.sms_characters = characters.get("sms_characters", {})
        self.model = model
        self.ollama_host = ollama_host
        self.system_prompt = load_system_prompt("guest")
        self.processed_messages: set[str] = set()
        self.responded_characters: set[str] = set()

    async def check_and_respond(self) -> list[dict]:
        """Check for new SMS to college crew and generate responses.
        
        Returns:
            List of response events scheduled.
        """
        responses = []
        sms_state = await self.client.sms.get_state()
        current_time = (await self.client.time.get_state()).current_time
        
        # Find the college crew thread
        college_thread = sms_state.conversations.get("college-crew")
        if not college_thread:
            return responses
        
        # Check for outgoing messages about the party
        for msg_id in college_thread.message_ids:
            if msg_id in self.processed_messages:
                continue
            
            msg = sms_state.messages.get(msg_id)
            if not msg or msg.direction != "outgoing":
                continue
            
            # Check if this looks like a party invitation
            body_lower = msg.body.lower() if msg.body else ""
            is_invitation = any(
                kw in body_lower
                for kw in ["party", "housewarming", "january 31", "gathering", "invite"]
            )
            
            if is_invitation:
                # Generate responses from each character who hasn't responded
                for phone, character in self.sms_characters.items():
                    if phone in self.responded_characters:
                        continue
                    
                    response = await self._generate_sms_response(
                        msg, character, phone, current_time
                    )
                    if response:
                        responses.append(response)
                        self.responded_characters.add(phone)
            
            self.processed_messages.add(msg_id)
        
        return responses

    async def _generate_sms_response(
        self,
        message: Any,
        character: dict,
        phone: str,
        current_time: datetime,
    ) -> dict | None:
        """Generate an SMS response from a college friend."""
        # Build simple prompt for SMS
        prompt = f"""Character: {character['name']} ({character['nickname']})
Personality: {character['personality']}
RSVP tendency: {character['response_behavior']['rsvp']}
Example response: "{character['example_response']}"

Original group message about party: "{message.body}"

Generate a SHORT SMS response (1-2 sentences max) from this character. Match their personality. Use emojis if appropriate for the character."""

        response_text = call_ollama(
            prompt=prompt,
            system_prompt="You are generating a brief SMS response. Keep it short and casual like a real text message.",
            model=self.model,
            ollama_host=self.ollama_host,
        )
        
        # Clean up the response
        response_text = response_text.strip().strip('"')
        
        # Calculate delay
        delay = calculate_response_delay(
            character.get("responsiveness", {}), current_time
        )
        response_time = current_time + delay
        
        # Schedule the response
        await self.client.events.create(
            scheduled_time=response_time,
            modality="sms",
            data={
                "operation": "receive",
                "from_number": phone,
                "to_numbers": ["+15551234567"],  # Sam's number
                "body": response_text,
                "thread_id": "college-crew",
            },
        )
        
        return {
            "character": character["name"],
            "phone": phone,
            "scheduled_time": response_time.isoformat(),
            "message": response_text[:50] + "..." if len(response_text) > 50 else response_text,
        }


# ============================================================================
# Vendor Response Agent
# ============================================================================


class VendorResponseAgent:
    """Agent that generates responses from vendors (bakery, catering)."""

    def __init__(
        self,
        client: AsyncUESClient,
        characters: dict,
        model: str,
        ollama_host: str,
    ):
        self.client = client
        self.vendors = characters.get("vendors", {})
        self.model = model
        self.ollama_host = ollama_host
        self.system_prompt = load_system_prompt("vendor")
        self.processed_emails: set[str] = set()
        self.conversation_state: dict[str, str] = {}  # vendor -> state

    async def check_and_respond(self) -> list[dict]:
        """Check for new emails to vendors and generate responses.
        
        Returns:
            List of response events scheduled.
        """
        responses = []
        email_state = await self.client.email.get_state()
        current_time = (await self.client.time.get_state()).current_time
        
        for email in email_state.emails.values():
            # Only process sent emails
            if email.folder != "sent":
                continue
            
            # Skip already processed
            if email.message_id in self.processed_emails:
                continue
            
            # Check if any recipient is a known vendor
            for recipient in email.to_addresses:
                recipient_lower = recipient.lower()
                if recipient_lower in self.vendors:
                    vendor = self.vendors[recipient_lower]
                    response = await self._generate_response(
                        email, vendor, current_time
                    )
                    if response:
                        responses.append(response)
            
            self.processed_emails.add(email.message_id)
        
        return responses

    async def _generate_response(
        self,
        email: Any,
        vendor: dict,
        current_time: datetime,
    ) -> dict | None:
        """Generate a response from a vendor."""
        vendor_email = vendor["email"]
        
        # Determine conversation state
        if vendor_email not in self.conversation_state:
            self.conversation_state[vendor_email] = "initial"
        
        state = self.conversation_state[vendor_email]
        
        # Get conversation history
        history = await self._get_conversation_history(email.thread_id, vendor_email)
        
        # Build prompt
        prompt = self._build_prompt(email, vendor, history, state)
        
        # Generate response
        response_text = call_ollama(
            prompt=prompt,
            system_prompt=self.system_prompt,
            model=self.model,
            ollama_host=self.ollama_host,
        )
        
        # Parse response
        subject, body = self._parse_email_response(response_text, email.subject)
        
        # Update conversation state
        if state == "initial":
            self.conversation_state[vendor_email] = "quote_sent"
        elif state == "quote_sent":
            self.conversation_state[vendor_email] = "confirmed"
        
        # Calculate delay
        delay = calculate_response_delay(
            vendor.get("responsiveness", {}), current_time
        )
        response_time = current_time + delay
        
        # Schedule the response
        await self.client.events.create(
            scheduled_time=response_time,
            modality="email",
            data={
                "operation": "receive",
                "from_address": vendor_email,
                "to_addresses": ["sam.rivera@email.com"],
                "subject": subject,
                "body_text": body,
                "thread_id": email.thread_id,
                "in_reply_to": email.message_id,
            },
        )
        
        return {
            "vendor": vendor["name"],
            "scheduled_time": response_time.isoformat(),
            "subject": subject,
            "state": self.conversation_state[vendor_email],
        }

    async def _get_conversation_history(
        self, thread_id: str | None, vendor_email: str
    ) -> str:
        """Get conversation history with a vendor."""
        if not thread_id:
            return "No previous conversation."
        
        email_state = await self.client.email.get_state()
        thread = email_state.threads.get(thread_id)
        
        if not thread:
            return "No previous conversation."
        
        history_parts = []
        for msg_id in thread.message_ids:
            if msg_id in email_state.emails:
                email = email_state.emails[msg_id]
                history_parts.append(f"""---
From: {email.from_address}
Subject: {email.subject}
Date: {email.sent_at}

{email.body_text}
---""")
        
        return "\n\n".join(history_parts) if history_parts else "No previous conversation."

    def _build_prompt(
        self, email: Any, vendor: dict, history: str, state: str
    ) -> str:
        """Build the prompt for generating a vendor response."""
        vendor_profile = json.dumps(vendor, indent=2)
        customer_message = f"""From: {email.from_address}
Subject: {email.subject}
Date: {email.sent_at}

{email.body_text}"""
        
        return f"""Vendor Profile:
{vendor_profile}

Conversation History:
{history}

Latest Customer Message:
{customer_message}

Current Response Stage: {state}

Generate a professional email response from this vendor. Follow the response flow appropriate for the current stage."""

    def _parse_email_response(self, response: str, original_subject: str) -> tuple[str, str]:
        """Parse LLM response into subject and body."""
        lines = response.strip().split("\n")
        
        subject = f"Re: {original_subject}"
        body_start = 0
        
        for i, line in enumerate(lines):
            if line.lower().startswith("subject:"):
                subject = line[8:].strip()
                body_start = i + 1
                if body_start < len(lines) and not lines[body_start].strip():
                    body_start += 1
                break
        
        body = "\n".join(lines[body_start:]).strip()
        return subject, body


# ============================================================================
# Main Agent Loop
# ============================================================================


async def run_agents(
    ues_host: str,
    ollama_host: str,
    model: str,
    check_interval: float = 5.0,
    verbose: bool = False,
) -> None:
    """Run all simulator-side agents in a loop.

    Args:
        ues_host: UES server URL.
        ollama_host: Ollama server URL.
        model: LLM model to use.
        check_interval: Seconds between checks for new messages.
        verbose: Whether to print detailed status.
    """
    characters = load_characters()
    
    async with AsyncUESClient(base_url=ues_host) as client:
        guest_agent = GuestResponseAgent(client, characters, model, ollama_host)
        sms_agent = SMSResponseAgent(client, characters, model, ollama_host)
        vendor_agent = VendorResponseAgent(client, characters, model, ollama_host)
        
        print("🎉 Simulator agents started")
        print(f"   Model: {model}")
        print(f"   UES: {ues_host}")
        print(f"   Ollama: {ollama_host}")
        print("   Monitoring for emails and SMS...")
        print()
        
        try:
            while True:
                # Check for messages and generate responses
                guest_responses = await guest_agent.check_and_respond()
                sms_responses = await sms_agent.check_and_respond()
                vendor_responses = await vendor_agent.check_and_respond()
                
                # Log any scheduled responses
                if verbose or guest_responses or sms_responses or vendor_responses:
                    for resp in guest_responses:
                        print(f"📧 Guest response scheduled: {resp['character']} - {resp['subject']}")
                    for resp in sms_responses:
                        print(f"📱 SMS response scheduled: {resp['character']} - {resp['message']}")
                    for resp in vendor_responses:
                        print(f"🏪 Vendor response scheduled: {resp['vendor']} - {resp['subject']}")
                
                await asyncio.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n👋 Simulator agents stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run simulator-side agents for party planner scenario"
    )
    parser.add_argument(
        "--model",
        default="gemma3:12b",
        help="Ollama model to use (default: gemma3:12b)",
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
        "--interval",
        type=float,
        default=5.0,
        help="Check interval in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    asyncio.run(
        run_agents(
            ues_host=args.ues_host,
            ollama_host=args.ollama_host,
            model=args.model,
            check_interval=args.interval,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
