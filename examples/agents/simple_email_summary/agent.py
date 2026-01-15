#!/usr/bin/env python3
"""Simple Email Summary Agent.

An hourly email summary agent that uses Ollama to summarize emails received
in the past hour. The agent is orchestrated programmatically, advancing the
UES simulator time hour by hour from 6am to 8pm.

Usage:
    python agent.py [--model MODEL] [--ollama-host HOST] [--ues-host HOST]

Example:
    python agent.py --model gemma3:12b --ollama-host http://localhost:11434
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from client import UESClient


def load_system_prompt() -> str:
    """Load the system prompt from system_prompt.txt."""
    prompt_path = Path(__file__).parent / "system_prompt.txt"
    return prompt_path.read_text().strip()


def call_ollama(
    prompt: str,
    system_prompt: str,
    model: str,
    ollama_host: str,
) -> str:
    """Call Ollama API to generate a response.

    Args:
        prompt: The user prompt containing email data.
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


def format_emails_for_prompt(emails: list[dict]) -> str:
    """Format email data as JSON for the agent prompt.

    Args:
        emails: List of email dictionaries from UES query.

    Returns:
        JSON string of simplified email data.
    """
    simplified = [
        {
            "from": email["from_address"],
            "to": email["to_addresses"],
            "subject": email["subject"],
            "body": email["body_text"],
            "received_at": email["received_at"],
            "is_read": email["is_read"],
        }
        for email in emails
    ]
    return json.dumps(simplified, indent=2)


def load_scenario(scenario_path: Path, ues_host: str) -> None:
    """Load a scenario file into UES via direct HTTP.

    The UES Python client does not have a scenario sub-client, so we use
    httpx to call the scenario import endpoint directly.

    Args:
        scenario_path: Path to the .ues-scenario.json file.
        ues_host: The UES server URL.
    """
    scenario_data = json.loads(scenario_path.read_text())
    response = httpx.post(
        f"{ues_host}/scenario/import/full",
        json={"scenario": scenario_data},
        timeout=30.0,
    )
    if not response.is_success:
        print(f"Error loading scenario: {response.status_code}")
        print(f"Response: {response.text}")
    response.raise_for_status()


def run_agent(
    model: str,
    ollama_host: str,
    ues_host: str,
) -> None:
    """Run the hourly email summary agent.

    Args:
        model: The Ollama model to use for summarization.
        ollama_host: The Ollama server URL.
        ues_host: The UES server URL.
    """
    system_prompt = load_system_prompt()
    scenario_path = Path(__file__).parent / "scenario.ues-scenario.json"

    # Load the scenario via direct HTTP (no client.scenario sub-client)
    load_scenario(scenario_path, ues_host)
    print("Scenario loaded successfully.")

    with UESClient(base_url=ues_host) as client:
        # Start the simulation
        client.simulation.start(auto_advance=False)
        print("Simulation started.\n")

        # Get initial time (should be 6am)
        initial_state = client.time.get_state()
        current_time = initial_state.current_time
        print(f"Starting at: {current_time.strftime('%I:%M %p')}\n")
        print("=" * 60)

        # Resume the simulation so we can advance time
        client.time.resume()

        # Loop from 6am to 8pm (hours 6-20, so we advance 14 times to reach 8pm)
        # After each advance, we query emails from the previous hour
        for hour_num in range(14):
            # Advance time by 1 hour (executes any scheduled events)
            advance_result = client.time.advance(seconds=3600)
            current_time = advance_result.current_time
            one_hour_ago = current_time - timedelta(hours=1)

            print(f"\n📧 Hour ending at {current_time.strftime('%I:%M %p')}")
            print(f"   Events executed: {advance_result.events_executed}")

            # Query emails received in the last hour
            query_result = client.email.query(
                received_after=one_hour_ago,
                received_before=current_time,
                sort_by="received_at",
                sort_order="asc",
            )

            if query_result.total_count == 0:
                print("   No new emails this hour.\n")
                print("-" * 60)
                continue

            print(f"   Emails received: {query_result.total_count}")

            # Convert to dict for JSON serialization
            emails_data = [email.model_dump(mode="json") for email in query_result.emails]

            # Format emails for the agent
            email_json = format_emails_for_prompt(emails_data)

            # Call the agent
            prompt = f"Emails received in the past hour:\n\n{email_json}"
            summary = call_ollama(prompt, system_prompt, model, ollama_host)

            print(f"\n   📝 Summary:\n   {summary.strip()}\n")
            print("-" * 60)

        print("\n" + "=" * 60)
        print("Simulation complete. End of workday reached.")


def main() -> None:
    """Parse arguments and run the agent."""
    parser = argparse.ArgumentParser(
        description="Hourly email summary agent using Ollama and UES.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemma3:12b",
        help="Ollama model to use for summarization.",
    )
    parser.add_argument(
        "--ollama-host",
        type=str,
        default="http://localhost:11434",
        help="Ollama server URL.",
    )
    parser.add_argument(
        "--ues-host",
        type=str,
        default="http://localhost:8000",
        help="UES server URL.",
    )

    args = parser.parse_args()

    print(f"Using model: {args.model}")
    print(f"Ollama host: {args.ollama_host}")
    print(f"UES host: {args.ues_host}\n")

    run_agent(
        model=args.model,
        ollama_host=args.ollama_host,
        ues_host=args.ues_host,
    )


if __name__ == "__main__":
    main()
