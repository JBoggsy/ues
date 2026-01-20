"""Display utilities for agent testing.

This module provides functions for formatting test reports as terminal
output and saving them as JSON files.
"""

import json
from pathlib import Path
from typing import Any

from agent_testing.results import CriterionResult, EvalReport


def format_report_terminal(report: EvalReport) -> str:
    """Format a test report for terminal display.

    Creates a nicely formatted, human-readable report with progress bars
    and color-coded grades.

    Args:
        report: The EvalReport to format.

    Returns:
        Formatted string for terminal output.
    """
    lines: list[str] = []
    width = 65

    # Header
    lines.append("=" * width)
    lines.append(f"📊 TEST RESULTS: {report.name}")
    lines.append("=" * width)
    lines.append("")

    # Criterion scores
    lines.append("Criterion Scores:")
    lines.append("-" * width)

    for result in report.criteria_results:
        lines.extend(_format_criterion_result(result, width))
        lines.append("")

    # Total
    lines.append("-" * width)
    total_bar = _create_progress_bar(report.percentage, 20)
    lines.append(
        f"{'TOTAL SCORE':<25} [{total_bar}] "
        f"{report.total_score:.1f}/{report.max_score:.1f}  "
        f"{report.percentage:.1f}%"
    )
    lines.append("")

    # Grade
    grade_emoji = _get_grade_emoji(report.grade)
    lines.append(f"{grade_emoji} Grade: {report.grade_description}")

    # Footer
    lines.append("=" * width)

    # Metadata
    if report.duration_seconds:
        lines.append(f"Duration: {report.duration_seconds:.1f}s")
    lines.append(f"Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    return "\n".join(lines)


def _format_criterion_result(result: CriterionResult, width: int) -> list[str]:
    """Format a single criterion result."""
    lines: list[str] = []

    # Main score line with progress bar
    bar = _create_progress_bar(result.percentage, 20)
    name_truncated = result.name[:25]
    lines.append(
        f"{name_truncated:<25} [{bar}] "
        f"{result.score:.1f}/{result.max_score:.0f}  "
        f"{result.percentage:.0f}%"
    )

    # Explanation (indented)
    explanation = result.explanation
    if len(explanation) > width - 4:
        explanation = explanation[: width - 7] + "..."
    lines.append(f"  {explanation}")

    # Show eval count for on_event criteria
    if result.eval_count > 1:
        lines.append(f"  ({result.eval_count} evaluations)")

    return lines


def _create_progress_bar(percentage: float, width: int = 20) -> str:
    """Create a text-based progress bar.

    Args:
        percentage: Percentage (0-100).
        width: Width of the bar in characters.

    Returns:
        Progress bar string like "████████░░░░░░░░░░░░".
    """
    filled = int((percentage / 100) * width)
    filled = max(0, min(filled, width))  # Clamp to valid range
    empty = width - filled
    return "█" * filled + "░" * empty


def _get_grade_emoji(grade: str) -> str:
    """Get emoji for a grade."""
    grade_emojis = {
        "Excellent": "🏆",
        "Good": "✅",
        "Needs Improvement": "⚠️",
        "Failing": "❌",
    }
    return grade_emojis.get(grade, "📋")


def format_report_summary(report: EvalReport) -> str:
    """Format a brief one-line summary of the report.

    Args:
        report: The EvalReport to summarize.

    Returns:
        One-line summary string.
    """
    emoji = _get_grade_emoji(report.grade)
    return (
        f"{emoji} {report.name}: "
        f"{report.total_score:.1f}/{report.max_score:.1f} "
        f"({report.percentage:.1f}%) - {report.grade}"
    )


def save_report_json(report: EvalReport, path: str | Path) -> None:
    """Save a test report to a JSON file.

    Args:
        report: The EvalReport to save.
        path: Path to save the JSON file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(report.to_dict(), f, indent=2, default=_json_serializer)


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for types not natively supported."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def load_report_json(path: str | Path) -> dict[str, Any]:
    """Load a test report from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Dictionary containing the report data.
    """
    with open(path) as f:
        return json.load(f)
