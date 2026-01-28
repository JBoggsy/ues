#!/usr/bin/env python3
"""Orchestrated Test Runner for Party Planner.

This script runs the complete party planner integration test, coordinating:
1. Loading the scenario into UES
2. Running the user-side AI agent
3. Running the simulator-side agents (guest/vendor responses)
4. Advancing simulation time
5. Running the test evaluators and generating a score report

Usage:
    python run_test.py [--model MODEL] [--ollama-host HOST] [--ues-host HOST]

Example:
    python run_test.py --model gemma3:12b --duration 8 --verbose
"""

import argparse
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

import httpx

from ues.client import AsyncUESClient
from ues.agent_testing import EvalRunner

# Import our agents
from user_agent import UserAgent
from simulator_agents import (
    GuestResponseAgent,
    SMSResponseAgent,
    VendorResponseAgent,
    load_characters,
)


def load_scenario_into_ues(ues_host: str) -> None:
    """Load the party planner scenario into UES.

    Args:
        ues_host: UES server URL.
    """
    scenario_path = Path(__file__).parent / "scenario.ues-scenario.json"
    scenario_data = json.loads(scenario_path.read_text())
    
    response = httpx.post(
        f"{ues_host}/scenario/import/full",
        json=scenario_data,
        timeout=30.0,
    )
    if not response.is_success:
        print(f"Error loading scenario: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)
    
    result = response.json()
    print(f"✓ Scenario loaded: {result.get('message', 'Success')}")


async def run_orchestrated_test(
    ues_host: str,
    ollama_host: str,
    model: str,
    duration_hours: int = 8,
    time_step_minutes: int = 30,
    verbose: bool = False,
) -> None:
    """Run the complete orchestrated test.

    This coordinates:
    1. User agent executes initial tasks
    2. Simulator agents generate responses
    3. Time advances in steps
    4. User agent handles follow-ups
    5. Final evaluation and scoring

    Args:
        ues_host: UES server URL.
        ollama_host: Ollama server URL.
        model: LLM model to use.
        duration_hours: Total simulation hours to run.
        time_step_minutes: Minutes to advance per step.
        verbose: Whether to print detailed output.
    """
    print("=" * 60)
    print("🎉 PARTY PLANNER INTEGRATION TEST")
    print("=" * 60)
    print()
    
    # Load scenario
    print("📦 Loading scenario...")
    load_scenario_into_ues(ues_host)
    print()
    
    characters = load_characters()
    
    async with AsyncUESClient(base_url=ues_host) as client:
        # Initialize agents
        user_agent = UserAgent(client, model, ollama_host, verbose=verbose)
        guest_agent = GuestResponseAgent(client, characters, model, ollama_host)
        sms_agent = SMSResponseAgent(client, characters, model, ollama_host)
        vendor_agent = VendorResponseAgent(client, characters, model, ollama_host)
        
        # Start simulation
        await client.simulation.start(auto_advance=False)
        
        # Get initial time
        time_state = await client.time.get_state()
        current_time = time_state.current_time
        print(f"⏰ Simulation start time: {current_time}")
        print()
        
        # ================================================================
        # Phase 1: User agent executes initial tasks
        # ================================================================
        print("=" * 60)
        print("📋 PHASE 1: Initial Task Execution")
        print("=" * 60)
        print()
        
        print("🤖 User agent sending invitations and contacting vendors...")
        results = await user_agent.execute_initial_tasks()
        
        print(f"   ✓ Invitations sent: {len(results['invitations_sent'])}")
        print(f"   ✓ SMS to college crew: {'Yes' if results['sms_sent'] else 'No'}")
        print(f"   ✓ Vendors contacted: {len(results['vendors_contacted'])}")
        print(f"   ✓ Calendar event created: {'Yes' if results['calendar_created'] else 'No'}")
        print()
        
        # ================================================================
        # Phase 2: Simulation loop - advance time and process responses
        # ================================================================
        print("=" * 60)
        print("⏳ PHASE 2: Simulation Loop")
        print("=" * 60)
        print()
        
        # Resume time (scenario starts paused)
        await client.time.resume()
        
        total_steps = (duration_hours * 60) // time_step_minutes
        time_step = timedelta(minutes=time_step_minutes)
        
        for step in range(total_steps):
            # Advance time
            advance_result = await client.time.advance(seconds=time_step.total_seconds())
            current_time = advance_result.current_time
            
            if verbose or advance_result.events_executed > 0:
                print(f"⏰ Step {step + 1}/{total_steps}: {current_time.strftime('%Y-%m-%d %H:%M')}")
                if advance_result.events_executed > 0:
                    print(f"   Executed {advance_result.events_executed} events")
            
            # Let simulator agents check for messages and generate responses
            guest_responses = await guest_agent.check_and_respond()
            sms_responses = await sms_agent.check_and_respond()
            vendor_responses = await vendor_agent.check_and_respond()
            
            # Log scheduled responses
            for resp in guest_responses:
                print(f"   📧 Scheduled: {resp['character']} response")
            for resp in sms_responses:
                print(f"   📱 Scheduled: {resp['character']} SMS")
            for resp in vendor_responses:
                print(f"   🏪 Scheduled: {resp['vendor']} response")
            
            # Periodically have user agent check and respond to vendor questions
            if step > 0 and step % 4 == 0:  # Every 2 hours
                responded = await user_agent.respond_to_vendor_questions()
                for vendor in responded:
                    print(f"   📤 User replied to: {vendor}")
            
            # Have user agent process RSVPs
            await user_agent.process_rsvps()
            
            # Brief pause to avoid overwhelming the system
            await asyncio.sleep(0.1)
        
        print()
        
        # ================================================================
        # Phase 3: Final status and evaluation
        # ================================================================
        print("=" * 60)
        print("📊 PHASE 3: Final Evaluation")
        print("=" * 60)
        print()
        
        # Execute any remaining pending events to ensure all responses are processed
        print("Executing remaining pending events...")
        flush_result = await client.time.advance(seconds=3600)  # Advance 1 hour
        if flush_result.events_executed > 0:
            print(f"   Executed {flush_result.events_executed} remaining events")
        
        # Final RSVP processing
        await user_agent.process_rsvps()
        print()
        
        # Save user agent's RSVP tracking for evaluation
        rsvp_tracking_path = Path(__file__).parent / "agent_rsvp_tracking.json"
        rsvp_tracking_path.write_text(json.dumps({
            "tracked_rsvps": user_agent.get_rsvp_tracking(),
            "invitations_sent": list(user_agent.invitations_sent),
            "vendors_contacted": list(user_agent.vendor_contacted),
        }, indent=2))
        print(f"📝 Agent state saved to: {rsvp_tracking_path}")
        print()
        
        # Generate final status report
        status_report = await user_agent.generate_status_report()
        print(status_report)
        print()
        
        # Stop simulation
        await client.simulation.stop()
    
    # ================================================================
    # Phase 4: Run test evaluators
    # ================================================================
    print("=" * 60)
    print("🏆 PHASE 4: Test Scoring")
    print("=" * 60)
    print()
    
    # Use the EvalRunner from the agent_testing framework
    scenario_path = Path(__file__).parent / "scenario.ues-scenario.json"
    criteria_path = Path(__file__).parent / "test_criteria.json"
    
    runner = EvalRunner(
        scenario_path=str(scenario_path),
        criteria_path=str(criteria_path),
        ues_host=ues_host,
    )
    
    # Run post-scenario evaluation
    report = await runner.run()
    
    # Print the report
    runner.print_report()
    
    # Save report to file
    report_path = Path(__file__).parent / "test_results.json"
    runner.save_report(str(report_path))
    print(f"\n📄 Detailed results saved to: {report_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the party planner integration test"
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
        "--duration",
        type=int,
        default=24,
        help="Simulation duration in hours (default: 8)",
    )
    parser.add_argument(
        "--time-step",
        type=int,
        default=30,
        help="Time step in minutes (default: 30)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    asyncio.run(
        run_orchestrated_test(
            ues_host=args.ues_host,
            ollama_host=args.ollama_host,
            model=args.model,
            duration_hours=args.duration,
            time_step_minutes=args.time_step,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
