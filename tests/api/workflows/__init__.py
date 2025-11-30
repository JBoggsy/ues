"""
Workflow Tests for UES REST API.

This package contains multi-step workflow tests that validate realistic
API usage scenarios. Each scenario is defined declaratively and executed
by the WorkflowRunner.

Structure:
- scenarios/: Scenario definitions (data-driven)
- builders.py: Fluent event builders for each modality
- validators.py: State validation helpers
- runner.py: WorkflowRunner class that executes scenarios
- test_scenario_*.py: Thin test files that run scenarios
"""

from .runner import WorkflowRunner
from .scenarios.base import WorkflowScenario, WorkflowStep, StepType

__all__ = [
    "WorkflowRunner",
    "WorkflowScenario",
    "WorkflowStep",
    "StepType",
]
