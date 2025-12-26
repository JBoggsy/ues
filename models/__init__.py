"""UES data models package.

This package contains all data models for the User Environment Simulator,
including base classes for modality inputs and states, core simulation
infrastructure, and specific modality implementations.
"""

from models.base_input import ModalityInput
from models.base_state import ModalityState
from models.event import EventStatus, SimulatorEvent
from models.time import SimulatorTime, TimeMode
from models.queue import EventQueue
from models.environment import Environment
from models.simulation import SimulationEngine, SimulationLoop
from models.undo import UndoEntry, UndoStack
from models.version import UES_VERSION
from models.scenario import (
    Scenario,
    ScenarioMetadata,
    SCENARIO_FORMAT_VERSION,
)
from models.registry import (
    register_modality_state,
    get_modality_state_class,
    is_modality_state_registered,
    list_registered_state_modalities,
    unregister_modality_state,
    clear_state_registry,
    register_modality_input,
    get_modality_input_class,
    is_modality_input_registered,
    list_registered_input_modalities,
    unregister_modality_input,
    clear_input_registry,
    clear_all_registries,
)

__all__ = [
    # Base classes
    "ModalityInput",
    "ModalityState",
    # Event system
    "SimulatorEvent",
    "EventStatus",
    # Time management
    "SimulatorTime",
    "TimeMode",
    # Core infrastructure
    "EventQueue",
    "Environment",
    "SimulationEngine",
    "SimulationLoop",
    # Undo system
    "UndoEntry",
    "UndoStack",
    # Scenario save/load
    "Scenario",
    "ScenarioMetadata",
    "UES_VERSION",
    "SCENARIO_FORMAT_VERSION",
    # Registry functions - State
    "register_modality_state",
    "get_modality_state_class",
    "is_modality_state_registered",
    "list_registered_state_modalities",
    "unregister_modality_state",
    "clear_state_registry",
    # Registry functions - Input
    "register_modality_input",
    "get_modality_input_class",
    "is_modality_input_registered",
    "list_registered_input_modalities",
    "unregister_modality_input",
    "clear_input_registry",
    # Registry functions - Both
    "clear_all_registries",
]
