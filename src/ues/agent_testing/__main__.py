"""CLI entry point for agent testing.

Run with: python -m agent_testing <scenario_path>
"""

import argparse
import asyncio
import sys
from pathlib import Path

from agent_testing import EvalRunner


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run agent tests for a UES scenario",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run tests for a scenario directory
  python -m agent_testing examples/agents/party_planner/

  # Run with explicit criteria file
  python -m agent_testing scenario.json --criteria my_criteria.json

  # Save results to JSON
  python -m agent_testing scenario/ --output results.json
        """,
    )

    parser.add_argument(
        "scenario_path",
        type=Path,
        help="Path to scenario file or directory containing scenario.ues-scenario.json",
    )
    parser.add_argument(
        "--criteria",
        "-c",
        type=Path,
        help="Path to test_criteria.json (default: auto-discover)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Save JSON report to this path",
    )
    parser.add_argument(
        "--host",
        default="http://localhost:8000",
        help="UES server URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only print summary line, not full report",
    )

    args = parser.parse_args()

    # Resolve scenario path
    scenario_path = args.scenario_path
    if scenario_path.is_dir():
        # Look for scenario file in directory
        candidates = [
            scenario_path / "scenario.ues-scenario.json",
            scenario_path / "scenario.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                scenario_path = candidate
                break
        else:
            print(f"Error: No scenario file found in {args.scenario_path}")
            return 1

    if not scenario_path.exists():
        print(f"Error: Scenario file not found: {scenario_path}")
        return 1

    # Run tests
    async def run() -> int:
        runner = EvalRunner(
            scenario_path=scenario_path,
            criteria_path=args.criteria,
            ues_host=args.host,
        )

        try:
            report = await runner.run()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error running tests: {e}")
            return 1

        # Output
        if args.quiet:
            from agent_testing import format_report_summary

            print(format_report_summary(report))
        else:
            runner.print_report()

        if args.output:
            runner.save_report(args.output)
            print(f"\nReport saved to: {args.output}")

        return 0 if report.passed else 1

    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())
