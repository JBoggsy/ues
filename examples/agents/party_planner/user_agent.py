#!/usr/bin/env python3
"""User-Side AI Assistant for Party Planner.

This is the AI assistant being tested. It receives instructions from the user
and must coordinate party planning tasks through the UES API.

The agent:
1. Sends personalized email invitations to guests
2. Sends SMS to the college crew group
3. Contacts vendors (bakery, catering)
4. Creates a calendar event
5. Monitors for responses and provides status updates

Usage:
    python user_agent.py [--model MODEL] [--ollama-host HOST] [--ues-host HOST]

Example:
    python user_agent.py --model gemma3:12b
"""

import argparse
import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from client import AsyncUESClient


# ============================================================================
# Configuration
# ============================================================================


def load_system_prompt() -> str:
    """Load the assistant system prompt."""
    prompt_path = Path(__file__).parent / "system_prompts" / "assistant.txt"
    return prompt_path.read_text().strip()


def load_characters() -> dict:
    """Load character definitions."""
    characters_path = Path(__file__).parent / "characters.json"
    return json.loads(characters_path.read_text())


def load_scenario() -> dict:
    """Load the scenario file."""
    scenario_path = Path(__file__).parent / "scenario.ues-scenario.json"
    return json.loads(scenario_path.read_text())


# ============================================================================
# LLM Integration
# ============================================================================


def call_ollama(
    prompt: str,
    system_prompt: str,
    model: str,
    ollama_host: str,
) -> str:
    """Call Ollama API to generate a response."""
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


# ============================================================================
# User Agent Class
# ============================================================================


class UserAgent:
    """AI assistant that coordinates party planning tasks."""

    def __init__(
        self,
        client: AsyncUESClient,
        model: str,
        ollama_host: str,
        verbose: bool = False,
    ):
        self.client = client
        self.model = model
        self.ollama_host = ollama_host
        self.verbose = verbose
        self.system_prompt = load_system_prompt()
        self.characters = load_characters()
        self.scenario = load_scenario()
        
        # State tracking
        self.invitations_sent: set[str] = set()
        self.vendor_contacted: set[str] = set()
        self.vendor_replied: set[str] = set()
        self.calendar_created = False
        self.sms_sent = False
        
        # RSVP tracking: maps email/phone to "yes"/"no"/"tentative"
        self.rsvp_tracking: dict[str, str] = {}

    async def execute_initial_tasks(self) -> dict:
        """Execute the initial party planning tasks.
        
        This includes:
        1. Sending email invitations
        2. Sending SMS to college crew
        3. Contacting vendors
        4. Creating calendar event
        
        Returns:
            Summary of actions taken.
        """
        results = {
            "invitations_sent": [],
            "sms_sent": False,
            "vendors_contacted": [],
            "calendar_created": False,
        }
        
        # Get current time
        time_state = await self.client.time.get_state()
        current_time = time_state.current_time
        
        if self.verbose:
            print(f"\n📅 Current simulation time: {current_time}")
            print("\n🎯 Starting party planning tasks...\n")
        
        # 1. Send email invitations
        guests = [
            ("linda.rivera@email.com", "Mom"),
            ("jamie.walsh@email.com", "Jamie"),
            ("pat.chen@email.com", "Pat"),
            ("chris.miller@email.com", "Chris"),
        ]
        
        for email, name in guests:
            if email not in self.invitations_sent:
                await self._send_invitation_email(email, name)
                results["invitations_sent"].append(email)
                self.invitations_sent.add(email)
                if self.verbose:
                    print(f"  ✉️  Sent invitation to {name} ({email})")
        
        # 2. Send SMS to college crew
        if not self.sms_sent:
            await self._send_college_crew_sms()
            results["sms_sent"] = True
            self.sms_sent = True
            if self.verbose:
                print("  📱 Sent SMS to College Crew group")
        
        # 3. Contact vendors
        vendors = [
            ("orders@sweetdelightsbakery.com", "Sweet Delights Bakery", "cake"),
            ("catering@coastalcatering.com", "Coastal Catering", "appetizers"),
        ]
        
        for email, name, service in vendors:
            if email not in self.vendor_contacted:
                await self._contact_vendor(email, name, service)
                results["vendors_contacted"].append(email)
                self.vendor_contacted.add(email)
                if self.verbose:
                    print(f"  🏪 Contacted {name} for {service}")
        
        # 4. Create calendar event
        if not self.calendar_created:
            await self._create_party_event()
            results["calendar_created"] = True
            self.calendar_created = True
            if self.verbose:
                print("  📅 Created calendar event for party")
        
        return results

    async def _send_invitation_email(self, to_email: str, name: str) -> None:
        """Send a personalized party invitation email."""
        # Get character info for personalization
        character = self.characters.get("characters", {}).get(to_email, {})
        relationship = character.get("relationship", "friend")
        
        # Generate personalized invitation using LLM
        prompt = f"""Generate a party invitation email for the following recipient:

Name: {name}
Email: {to_email}
Relationship: {relationship}

Party Details:
- Event: Housewarming Party
- Host: Sam Rivera
- Date: Saturday, January 31, 2026
- Time: 6:00 PM
- Address: 456 Oak Street, Atlanta, GA 30308
- Expected guests: 10-15 people

Write a warm, personalized invitation that:
1. Mentions this is a housewarming for Sam's new house
2. Includes all party details (date, time, address)
3. Requests an RSVP
4. Matches the relationship (more personal for Mom, casual for friends)

Format your response as:
Subject: [subject line]

[email body]"""

        response = call_ollama(
            prompt=prompt,
            system_prompt="You are writing invitation emails. Be warm and personalized based on the relationship.",
            model=self.model,
            ollama_host=self.ollama_host,
        )
        
        # Parse subject and body
        subject, body = self._parse_email(response)
        
        # Send via API
        await self.client.email.send(
            from_address="sam.rivera@email.com",
            to_addresses=[to_email],
            subject=subject,
            body_text=body,
        )

    async def _send_college_crew_sms(self) -> None:
        """Send SMS to the college crew group about the party."""
        message = (
            "Hey everyone! 🏠🎉 I'm having a housewarming party at my new place! "
            "Saturday Jan 31st at 6pm. 456 Oak Street, Atlanta. "
            "Hope you all can make it! RSVP!"
        )
        
        await self.client.sms.send(
            from_number="+15551234567",  # Sam's number
            to_numbers=["+15552345001", "+15552345002", "+15552345003"],
            body=message,
        )

    async def _contact_vendor(self, email: str, name: str, service: str) -> None:
        """Send an inquiry email to a vendor."""
        if service == "cake":
            subject = "Cake Order Inquiry - Housewarming Party January 31"
            body = f"""Hi,

I'm hosting a housewarming party on Saturday, January 31, 2026, and I'd like to order a cake for approximately 15 guests.

Could you please let me know:
- What sizes/flavors you recommend for this group size?
- Pricing options?
- Whether you offer delivery to Atlanta (30308)?

The party starts at 6 PM, so I'd need the cake ready before then.

Thank you!

Sam Rivera
sam.rivera@email.com
(555) 123-4567"""
        else:  # catering
            subject = "Appetizer Quote Request - Housewarming Party January 31"
            body = f"""Hello,

I'm planning a housewarming party on Saturday, January 31, 2026, and I'm looking for appetizer catering for approximately 15 guests.

Could you please send me a quote for appetizer options? The party will run from 6 PM to approximately 9 PM.

My address is 456 Oak Street, Atlanta, GA 30308.

Please let me know what packages you offer and the pricing.

Thank you!

Sam Rivera
sam.rivera@email.com
(555) 123-4567"""

        await self.client.email.send(
            from_address="sam.rivera@email.com",
            to_addresses=[email],
            subject=subject,
            body_text=body,
        )

    async def _create_party_event(self) -> None:
        """Create a calendar event for the party."""
        # Party is January 31, 2026 at 6 PM Eastern
        party_start = datetime(2026, 1, 31, 18, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        party_end = datetime(2026, 1, 31, 22, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        
        await self.client.calendar.create(
            title="🏠 Housewarming Party",
            start=party_start,
            end=party_end,
            calendar_id="personal",
            timezone="America/New_York",
            description="Housewarming party at the new house! Guests include family, friends, and the college crew.",
            location="456 Oak Street, Atlanta, GA 30308",
        )

    async def check_for_responses(self) -> dict:
        """Check for responses from guests and vendors.
        
        Returns:
            Summary of responses received.
        """
        email_state = await self.client.email.get_state()
        sms_state = await self.client.sms.get_state()
        
        responses = {
            "email_responses": [],
            "sms_responses": [],
        }
        
        # Check inbox for guest/vendor responses
        for email in email_state.emails.values():
            if email.folder == "inbox":
                responses["email_responses"].append({
                    "from": email.from_address,
                    "subject": email.subject,
                    "preview": (email.body_text or "")[:100],
                })
        
        # Check SMS responses
        college_thread = sms_state.conversations.get("college-crew")
        if college_thread:
            for msg_id in college_thread.message_ids:
                msg = sms_state.messages.get(msg_id)
                if msg and msg.direction == "incoming":
                    # This is an incoming message
                    responses["sms_responses"].append({
                        "from": msg.from_number,
                        "message": msg.body,
                    })
        
        return responses

    async def process_rsvps(self) -> dict[str, str]:
        """Process incoming messages to track RSVPs.
        
        Analyzes email and SMS responses to determine who has RSVPd
        and what their response was (yes/no/tentative).
        
        Returns:
            Dictionary mapping contact (email/phone) to RSVP status.
        """
        email_state = await self.client.email.get_state()
        sms_state = await self.client.sms.get_state()
        
        # Process email RSVPs
        guest_emails = [
            "linda.rivera@email.com",
            "jamie.walsh@email.com",
            "pat.chen@email.com",
            "chris.miller@email.com",
        ]
        
        for email in email_state.emails.values():
            if email.folder != "inbox":
                continue
            
            sender = email.from_address.lower()
            if sender not in guest_emails:
                continue
            
            body_lower = (email.body_text or "").lower()
            
            # Determine RSVP status from content
            if any(word in body_lower for word in ["yes", "count me in", "i'll be there", "we'll be there", "of course", "absolutely", "definitely"]):
                if any(word in body_lower for word in ["maybe", "might", "tentative", "let me check", "not sure if"]):
                    self.rsvp_tracking[sender] = "tentative"
                else:
                    self.rsvp_tracking[sender] = "yes"
            elif any(word in body_lower for word in ["no", "can't make", "cannot", "won't be able", "unfortunately", "regret"]):
                self.rsvp_tracking[sender] = "no"
            elif any(word in body_lower for word in ["maybe", "might", "not sure", "tentative", "possibly"]):
                self.rsvp_tracking[sender] = "tentative"
        
        # Process SMS RSVPs from college crew
        college_thread = sms_state.conversations.get("college-crew")
        if college_thread:
            for msg_id in college_thread.message_ids:
                msg = sms_state.messages.get(msg_id)
                if msg and msg.direction == "incoming":
                    sender = msg.from_number
                    body_lower = msg.body.lower()
                    
                    if any(word in body_lower for word in ["yes", "i'm in", "count me in", "i'll be there", "definitely"]):
                        self.rsvp_tracking[sender] = "yes"
                    elif any(word in body_lower for word in ["no", "can't", "out", "busy"]):
                        self.rsvp_tracking[sender] = "no"
                    elif any(word in body_lower for word in ["maybe", "might", "not sure"]):
                        self.rsvp_tracking[sender] = "tentative"
        
        return self.rsvp_tracking

    def get_rsvp_tracking(self) -> dict[str, str]:
        """Get the current RSVP tracking state.
        
        Returns:
            Dictionary mapping contact (email/phone) to RSVP status.
        """
        return self.rsvp_tracking.copy()

    async def respond_to_vendor_questions(self) -> list[str]:
        """Check for vendor questions and respond appropriately.
        
        Returns:
            List of vendors responded to.
        """
        email_state = await self.client.email.get_state()
        responded = []
        
        vendor_emails = [
            "orders@sweetdelightsbakery.com",
            "catering@coastalcatering.com",
        ]
        
        for email in email_state.emails.values():
            if email.folder != "inbox":
                continue
            
            sender = email.from_address.lower()
            if sender not in vendor_emails:
                continue
            
            # Check if this is a question that needs response
            body_lower = (email.body_text or "").lower()
            needs_response = any(
                kw in body_lower 
                for kw in ["?", "please let us know", "preference", "which option"]
            )
            
            if needs_response:
                if sender not in self.vendor_replied:
                    # Generate and send response
                    await self._respond_to_vendor(email, sender)
                    responded.append(sender)
                    self.vendor_replied.add(sender)
        
        return responded

    async def _respond_to_vendor(self, email: Any, vendor_email: str) -> None:
        """Generate and send a response to a vendor question."""
        if "sweetdelights" in vendor_email:
            # Bakery - respond with cake preferences
            subject = f"Re: {email.subject}"
            body = """Hi,

Thank you for getting back to me so quickly!

Here are my preferences:
- Flavor: Chocolate would be great
- No dietary restrictions to worry about
- Message on cake: "Welcome Home Sam!" 
- Delivery would be preferred

Please let me know the total and how to confirm the order.

Thanks!
Sam"""
        else:
            # Catering - select an option
            subject = f"Re: {email.subject}"
            body = """Hi,

Thank you for the detailed quote!

I'd like to go with Option A - "The Crowd Pleaser" at $180. That sounds perfect for our group.

Please confirm the booking for:
- Date: January 31, 2026
- Time: Ready by 5:30 PM (party starts at 6 PM)
- Address: 456 Oak Street, Atlanta, GA 30308
- Guest count: 15 people

Let me know if you need anything else!

Thanks!
Sam"""

        await self.client.email.send(
            from_address="sam.rivera@email.com",
            to_addresses=[vendor_email],
            subject=subject,
            body_text=body,
            thread_id=email.thread_id,
            in_reply_to=email.message_id,
        )

    async def generate_status_report(self) -> str:
        """Generate a status report of party planning progress.
        
        Returns:
            Formatted status report string.
        """
        email_state = await self.client.email.get_state()
        sms_state = await self.client.sms.get_state()
        calendar_state = await self.client.calendar.get_state()
        
        report_lines = ["📋 PARTY PLANNING STATUS REPORT", "=" * 40, ""]
        
        # Invitations
        report_lines.append("📨 INVITATIONS:")
        sent_to = list(self.invitations_sent)
        if sent_to:
            for email in sent_to:
                report_lines.append(f"  ✓ {email}")
        else:
            report_lines.append("  (none sent)")
        
        if self.sms_sent:
            report_lines.append("  ✓ College Crew (SMS group)")
        report_lines.append("")
        
        # RSVPs
        report_lines.append("📬 RSVPs RECEIVED:")
        if self.rsvp_tracking:
            for contact, status in sorted(self.rsvp_tracking.items()):
                status_display = status.upper()
                report_lines.append(f"  • {contact}: {status_display}")
        else:
            report_lines.append("  (waiting for responses)")
        report_lines.append("")
        
        # Vendors
        report_lines.append("🏪 VENDORS:")
        for vendor in self.vendor_contacted:
            name = "Sweet Delights Bakery" if "sweetdelights" in vendor else "Coastal Catering"
            report_lines.append(f"  ✓ {name} - contacted")
        report_lines.append("")
        
        # Calendar
        report_lines.append("📅 CALENDAR:")
        if calendar_state.events:
            for event in calendar_state.events.values():
                report_lines.append(f"  ✓ {event.title} - {event.start}")
        else:
            report_lines.append("  (no events)")
        
        return "\n".join(report_lines)

    def _parse_email(self, response: str) -> tuple[str, str]:
        """Parse LLM response into subject and body."""
        lines = response.strip().split("\n")
        
        subject = "You're Invited - Housewarming Party!"
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
# Main Entry Point
# ============================================================================


async def run_user_agent(
    ues_host: str,
    ollama_host: str,
    model: str,
    verbose: bool = False,
) -> None:
    """Run the user-side AI agent.

    Args:
        ues_host: UES server URL.
        ollama_host: Ollama server URL.
        model: LLM model to use.
        verbose: Whether to print detailed output.
    """
    async with AsyncUESClient(base_url=ues_host) as client:
        agent = UserAgent(client, model, ollama_host, verbose=verbose)
        
        print("🤖 Party Planning Assistant Started")
        print(f"   Model: {model}")
        print(f"   UES: {ues_host}")
        print()
        
        # Execute initial tasks
        print("📋 Executing initial party planning tasks...")
        results = await agent.execute_initial_tasks()
        
        print("\n✅ Initial tasks completed:")
        print(f"   • Invitations sent: {len(results['invitations_sent'])}")
        print(f"   • College crew SMS: {'Yes' if results['sms_sent'] else 'No'}")
        print(f"   • Vendors contacted: {len(results['vendors_contacted'])}")
        print(f"   • Calendar event: {'Created' if results['calendar_created'] else 'No'}")
        
        # Generate initial status report
        print("\n" + await agent.generate_status_report())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the user-side AI assistant for party planning"
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
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    asyncio.run(
        run_user_agent(
            ues_host=args.ues_host,
            ollama_host=args.ollama_host,
            model=args.model,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
