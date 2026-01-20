"""Pydantic models for agent testing criteria JSON validation.

This module defines the schema for test criteria configuration files,
which specify how agent performance should be evaluated.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EvalTiming(str, Enum):
    """When a criterion should be evaluated."""

    POST_SCENARIO = "post_scenario"
    """Evaluate once after the scenario completes."""

    ON_EVENT = "on_event"
    """Evaluate each time a matching event occurs."""


class CriterionSchema(BaseModel):
    """Schema for a single test criterion.

    A criterion defines a specific aspect of agent performance to evaluate,
    including the evaluator function, timing, and scoring parameters.

    Attributes:
        id: Unique identifier for this criterion.
        name: Human-readable name for display.
        description: Detailed description of what this criterion tests.
        evaluator: Name of the Python function to call for evaluation.
        max_points: Maximum points possible for this criterion.
        eval_timing: When to evaluate (post_scenario or on_event).
        event_filter: For on_event: name of filter function to determine
            which events trigger evaluation.
        params: Parameters passed to the evaluator function.
    """

    id: str = Field(..., description="Unique identifier for this criterion")
    name: str = Field(..., description="Human-readable name")
    description: str | None = Field(
        None, description="Detailed description of what this tests"
    )
    evaluator: str = Field(..., description="Name of Python evaluator function")
    max_points: float = Field(..., gt=0, description="Maximum points for this criterion")
    eval_timing: EvalTiming = Field(..., description="When to evaluate")
    event_filter: str | None = Field(
        None,
        description="For on_event: name of filter function",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to the evaluator",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure id is a valid identifier."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                f"Criterion id must be alphanumeric with underscores/hyphens: {v}"
            )
        return v

    @field_validator("evaluator", "event_filter")
    @classmethod
    def validate_function_name(cls, v: str | None) -> str | None:
        """Ensure function names are valid Python identifiers."""
        if v is None:
            return v
        if not v.isidentifier():
            raise ValueError(f"Function name must be a valid Python identifier: {v}")
        return v


class CriteriaSchema(BaseModel):
    """Schema for the complete test criteria configuration.

    This is the root schema for test_criteria.json files.

    Attributes:
        name: Human-readable name for this test suite.
        description: Detailed description of what's being tested.
        test_module: Python module name containing evaluator functions.
            Defaults to "scenario_tests".
        criteria: List of criterion definitions.
    """

    name: str = Field(..., description="Name of this test suite")
    description: str | None = Field(
        None, description="Description of what's being tested"
    )
    test_module: str = Field(
        "scenario_tests",
        description="Python module containing evaluator functions",
    )
    criteria: list[CriterionSchema] = Field(
        ..., min_length=1, description="List of criteria to evaluate"
    )

    @field_validator("criteria")
    @classmethod
    def validate_unique_ids(cls, v: list[CriterionSchema]) -> list[CriterionSchema]:
        """Ensure all criterion IDs are unique."""
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            duplicates = [id for id in ids if ids.count(id) > 1]
            raise ValueError(f"Duplicate criterion IDs found: {set(duplicates)}")
        return v

    @field_validator("test_module")
    @classmethod
    def validate_module_name(cls, v: str) -> str:
        """Ensure module name is valid."""
        parts = v.split(".")
        for part in parts:
            if not part.isidentifier():
                raise ValueError(f"Invalid module name: {v}")
        return v


def load_criteria_from_file(path: str) -> CriteriaSchema:
    """Load and validate test criteria from a JSON file.

    Args:
        path: Path to the test_criteria.json file.

    Returns:
        Validated CriteriaSchema instance.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValidationError: If the JSON doesn't match the schema.
        JSONDecodeError: If the file isn't valid JSON.
    """
    import json
    from pathlib import Path

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Criteria file not found: {path}")

    with open(file_path) as f:
        data = json.load(f)

    return CriteriaSchema.model_validate(data)


def load_criteria_from_dict(data: dict[str, Any]) -> CriteriaSchema:
    """Load and validate test criteria from a dictionary.

    Args:
        data: Dictionary containing criteria configuration.

    Returns:
        Validated CriteriaSchema instance.

    Raises:
        ValidationError: If the data doesn't match the schema.
    """
    return CriteriaSchema.model_validate(data)
