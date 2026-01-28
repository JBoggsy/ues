"""Result classes for agent testing.

This module defines the data structures used to represent test results,
from individual evaluator returns to complete test reports.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class EvalResult:
    """Result returned by an evaluator function.

    Evaluator functions must return an EvalResult indicating the score
    achieved and an explanation.

    Attributes:
        score: Points earned (should be between 0 and max_score).
        max_score: Maximum possible points for this evaluation.
        explanation: Human-readable explanation of the score.
        details: Optional structured data for debugging or analysis.

    Example:
        >>> def check_emails_sent(ctx, params):
        ...     sent_count = len(ctx.get_state("email").sent_emails)
        ...     expected = params["expected_count"]
        ...     return EvalResult(
        ...         score=min(sent_count, expected),
        ...         max_score=expected,
        ...         explanation=f"Sent {sent_count}/{expected} emails",
        ...     )
    """

    score: float
    max_score: float
    explanation: str
    details: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate score is within bounds."""
        if self.score < 0:
            raise ValueError(f"Score cannot be negative: {self.score}")
        if self.max_score <= 0:
            raise ValueError(f"Max score must be positive: {self.max_score}")
        if self.score > self.max_score:
            raise ValueError(
                f"Score ({self.score}) cannot exceed max_score ({self.max_score})"
            )

    @property
    def percentage(self) -> float:
        """Calculate score as a percentage."""
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "score": self.score,
            "max_score": self.max_score,
            "percentage": round(self.percentage, 2),
            "explanation": self.explanation,
            "details": self.details,
        }


@dataclass
class CriterionResult:
    """Aggregated result for a single criterion.

    For post_scenario criteria, this contains a single evaluation result.
    For on_event criteria, this aggregates multiple evaluation results.

    Attributes:
        id: Criterion identifier from the schema.
        name: Human-readable criterion name.
        score: Total points earned.
        max_score: Maximum possible points (from criterion schema).
        explanation: Summary explanation.
        eval_count: Number of times the evaluator was called.
        individual_results: For on_event: list of each evaluation result.
        raw_score: For on_event: sum of raw evaluator scores before scaling.
        raw_max_score: For on_event: sum of raw evaluator max_scores.
    """

    id: str
    name: str
    score: float
    max_score: float
    explanation: str
    eval_count: int = 1
    individual_results: list[EvalResult] | None = None
    raw_score: float | None = None
    raw_max_score: float | None = None

    @property
    def percentage(self) -> float:
        """Calculate score as a percentage."""
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "id": self.id,
            "name": self.name,
            "score": round(self.score, 2),
            "max_score": round(self.max_score, 2),
            "percentage": round(self.percentage, 2),
            "explanation": self.explanation,
            "eval_count": self.eval_count,
        }
        if self.individual_results:
            result["individual_results"] = [r.to_dict() for r in self.individual_results]
        if self.raw_score is not None:
            result["raw_score"] = round(self.raw_score, 2)
        if self.raw_max_score is not None:
            result["raw_max_score"] = round(self.raw_max_score, 2)
        return result


@dataclass
class EvalReport:
    """Complete test report for a scenario evaluation.

    Attributes:
        name: Name of the test suite.
        timestamp: When the test was run.
        duration_seconds: How long the test took.
        total_score: Sum of all criterion scores.
        max_score: Sum of all criterion max_scores.
        criteria_results: Results for each criterion.
        scenario_path: Path to the scenario file.
        criteria_path: Path to the criteria file.
        metadata: Optional additional metadata.
    """

    name: str
    timestamp: datetime
    duration_seconds: float
    total_score: float
    max_score: float
    criteria_results: list[CriterionResult]
    scenario_path: str | None = None
    criteria_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def percentage(self) -> float:
        """Calculate total score as a percentage."""
        return (self.total_score / self.max_score) * 100 if self.max_score > 0 else 0

    @property
    def grade(self) -> str:
        """Get letter grade based on percentage."""
        pct = self.percentage
        if pct >= 90:
            return "Excellent"
        elif pct >= 70:
            return "Good"
        elif pct >= 50:
            return "Needs Improvement"
        else:
            return "Failing"

    @property
    def grade_description(self) -> str:
        """Get grade with description."""
        pct = self.percentage
        if pct >= 90:
            return "Excellent - Agent handles the scenario flawlessly"
        elif pct >= 70:
            return "Good - Minor gaps but core functionality works"
        elif pct >= 50:
            return "Needs Improvement - Significant issues with some tasks"
        else:
            return "Failing - Major functionality broken"

    @property
    def passed(self) -> bool:
        """Whether the test passed (score >= 50%)."""
        return self.percentage >= 50

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": round(self.duration_seconds, 2),
            "total_score": round(self.total_score, 2),
            "max_score": round(self.max_score, 2),
            "percentage": round(self.percentage, 2),
            "grade": self.grade,
            "passed": self.passed,
            "criteria_results": [r.to_dict() for r in self.criteria_results],
            "scenario_path": self.scenario_path,
            "criteria_path": self.criteria_path,
            "metadata": self.metadata,
        }

    @classmethod
    def create(
        cls,
        name: str,
        criteria_results: list[CriterionResult],
        duration_seconds: float,
        scenario_path: str | None = None,
        criteria_path: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "EvalReport":
        """Create an EvalReport from criterion results.

        Args:
            name: Name of the test suite.
            criteria_results: Results for each criterion.
            duration_seconds: How long the test took.
            scenario_path: Path to the scenario file.
            criteria_path: Path to the criteria file.
            metadata: Optional additional metadata.

        Returns:
            A new EvalReport instance.
        """
        total_score = sum(r.score for r in criteria_results)
        max_score = sum(r.max_score for r in criteria_results)

        return cls(
            name=name,
            timestamp=datetime.now(timezone.utc),
            duration_seconds=duration_seconds,
            total_score=total_score,
            max_score=max_score,
            criteria_results=criteria_results,
            scenario_path=scenario_path,
            criteria_path=criteria_path,
            metadata=metadata or {},
        )
