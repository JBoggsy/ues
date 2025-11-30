"""
Workflow scenario definitions.

Each scenario is defined as a WorkflowScenario dataclass containing:
- Metadata (name, description, complexity, modalities)
- Setup events (initial state)
- Ordered workflow steps
- Final assertions
"""

from .base import WorkflowScenario, WorkflowStep, StepType
from .scenario_1_basic import SCENARIO_1
from .scenario_2_multimodality import SCENARIO_2
from .scenario_3_interactive import SCENARIO_3

__all__ = [
    "WorkflowScenario",
    "WorkflowStep",
    "StepType",
    "SCENARIO_1",
    "SCENARIO_2",
    "SCENARIO_3",
]
