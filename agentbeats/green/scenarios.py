"""Scenario registry for loading and resolving AgentBeats scenarios.

This module provides the ScenarioRegistry class which resolves scenario IDs
to their full definitions, including scenario data, user prompts, character
profiles, and evaluation criteria.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from agentbeats.green.characters import CharacterRegistry


class ScenarioData(BaseModel):
    """Parsed scenario file data.
    
    Contains the raw scenario JSON and any extracted/derived data needed
    for running an assessment.
    
    Attributes:
        scenario_id: The scenario identifier.
        scenario: Raw scenario JSON for import into UES.
        user_prompt: User instructions extracted from scenario or prompt file.
        characters: Character profiles for response generation (if available).
        evaluation_criteria: Evaluation criteria definitions (if available).
        metadata: Scenario metadata (description, author, version).
    """
    
    scenario_id: str = Field(..., description="Scenario identifier")
    scenario: dict[str, Any] = Field(..., description="Raw scenario JSON")
    user_prompt: str | None = Field(
        None, description="User instructions for the assessment"
    )
    characters: CharacterRegistry | None = Field(
        None, description="Character profiles for response generation"
    )
    evaluation_criteria: list[dict[str, Any]] | None = Field(
        None, description="Evaluation criteria definitions"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Scenario metadata"
    )
    
    model_config = {"arbitrary_types_allowed": True}


class ScenarioNotFoundError(Exception):
    """Raised when a scenario cannot be found."""
    pass


class ScenarioRegistry:
    """Resolves scenario_id to scenario data.
    
    Searches for scenarios in predefined locations:
    1. examples/agents/{scenario_id}/scenario.ues-scenario.json
    2. examples/scenarios/{scenario_id}.ues-scenario.json
    
    Also loads associated files if present:
    - characters.json or characters.yaml
    - test_criteria.json
    - system_prompt.txt or user_prompt.txt
    
    Example:
        >>> registry = ScenarioRegistry()
        >>> scenario = await registry.get_scenario("email_reply_generator")
        >>> print(scenario.user_prompt)
        "You are a personal assistant..."
    """
    
    # Default search paths relative to project root
    DEFAULT_SEARCH_PATHS = [
        "examples/agents",
        "examples/scenarios",
    ]
    
    def __init__(
        self,
        search_paths: list[Path] | None = None,
        project_root: Path | None = None,
    ):
        """Initialize the registry.
        
        Args:
            search_paths: Custom search paths for scenarios.
            project_root: Project root directory. If not provided, attempts
                to detect from the current file location.
        """
        if project_root is None:
            # Assume we're in agentbeats/green/scenarios.py
            # Project root is 3 levels up
            project_root = Path(__file__).parent.parent.parent
        
        self._project_root = project_root
        
        if search_paths is not None:
            self._search_paths = search_paths
        else:
            self._search_paths = [
                project_root / path for path in self.DEFAULT_SEARCH_PATHS
            ]
    
    async def get_scenario(self, scenario_id: str) -> ScenarioData:
        """Load scenario by ID.
        
        Search order:
        1. examples/agents/{scenario_id}/scenario.ues-scenario.json
        2. examples/scenarios/{scenario_id}.ues-scenario.json
        
        Args:
            scenario_id: The scenario identifier to load.
            
        Returns:
            ScenarioData containing the parsed scenario and metadata.
            
        Raises:
            ScenarioNotFoundError: If scenario cannot be found.
        """
        # Try to find the scenario file
        scenario_file = self._find_scenario_file(scenario_id)
        if scenario_file is None:
            raise ScenarioNotFoundError(
                f"Scenario '{scenario_id}' not found. Searched paths: "
                f"{[str(p) for p in self._search_paths]}"
            )
        
        # Load the scenario JSON
        scenario_json = self._load_json(scenario_file)
        
        # Extract metadata
        metadata = self._extract_metadata(scenario_json)
        
        # Load associated files
        scenario_dir = scenario_file.parent
        
        # Load user prompt
        user_prompt = self._load_user_prompt(scenario_dir, scenario_json)
        
        # Load characters
        characters = self._load_characters(scenario_dir)
        
        # Load evaluation criteria
        evaluation_criteria = self._load_evaluation_criteria(scenario_dir)
        
        return ScenarioData(
            scenario_id=scenario_id,
            scenario=scenario_json,
            user_prompt=user_prompt,
            characters=characters,
            evaluation_criteria=evaluation_criteria,
            metadata=metadata,
        )
    
    def _find_scenario_file(self, scenario_id: str) -> Path | None:
        """Find the scenario file for a given ID.
        
        Args:
            scenario_id: The scenario identifier.
            
        Returns:
            Path to scenario file if found, None otherwise.
        """
        for search_path in self._search_paths:
            # Try agents/{scenario_id}/scenario.ues-scenario.json
            agent_scenario = search_path / scenario_id / "scenario.ues-scenario.json"
            if agent_scenario.exists():
                return agent_scenario
            
            # Try {scenario_id}.ues-scenario.json directly
            direct_scenario = search_path / f"{scenario_id}.ues-scenario.json"
            if direct_scenario.exists():
                return direct_scenario
        
        return None
    
    def _load_json(self, path: Path) -> dict[str, Any]:
        """Load and parse a JSON file.
        
        Args:
            path: Path to the JSON file.
            
        Returns:
            Parsed JSON as a dict.
        """
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _extract_metadata(self, scenario_json: dict[str, Any]) -> dict[str, Any]:
        """Extract metadata from scenario JSON.
        
        Args:
            scenario_json: The raw scenario JSON.
            
        Returns:
            Metadata dict.
        """
        scenario_block = scenario_json.get("scenario", {})
        return scenario_block.get("metadata", {})
    
    def _load_user_prompt(
        self,
        scenario_dir: Path,
        scenario_json: dict[str, Any],
    ) -> str | None:
        """Load user prompt from various sources.
        
        Priority:
        1. system_prompt.txt or user_prompt.txt in scenario directory
        2. Most recent chat message in scenario (role=user)
        3. Scenario description from metadata
        
        Args:
            scenario_dir: Directory containing the scenario.
            scenario_json: The raw scenario JSON.
            
        Returns:
            User prompt string if found, None otherwise.
        """
        # Try prompt files first
        prompt_files = [
            "system_prompt.txt",
            "user_prompt.txt",
            "prompt.txt",
            "instructions.txt",
        ]
        
        for prompt_file in prompt_files:
            prompt_path = scenario_dir / prompt_file
            if prompt_path.exists():
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read().strip()
        
        # Try to extract from chat messages in scenario
        chat_prompt = self._extract_chat_prompt(scenario_json)
        if chat_prompt:
            return chat_prompt
        
        # Fall back to scenario description
        metadata = self._extract_metadata(scenario_json)
        description = metadata.get("description")
        if description:
            return description
        
        return None
    
    def _extract_chat_prompt(self, scenario_json: dict[str, Any]) -> str | None:
        """Extract user prompt from chat modality messages.
        
        Looks for the most recent message from the user (role=user or
        sender type that indicates user) in the chat state.
        
        Args:
            scenario_json: The raw scenario JSON.
            
        Returns:
            User prompt from chat if found, None otherwise.
        """
        scenario_block = scenario_json.get("scenario", {})
        environment = scenario_block.get("environment", {})
        modality_states = environment.get("modality_states", {})
        chat_state = modality_states.get("chat", {})
        
        # Check for messages list
        messages = chat_state.get("messages", [])
        if messages:
            # Find the most recent user message
            for msg in reversed(messages):
                role = msg.get("role", "").lower()
                if role == "user":
                    content = msg.get("content") or msg.get("text")
                    if content:
                        return content
        
        return None
    
    def _load_characters(self, scenario_dir: Path) -> CharacterRegistry | None:
        """Load character profiles from characters.json.
        
        Args:
            scenario_dir: Directory containing the scenario.
            
        Returns:
            CharacterRegistry if file exists, None otherwise.
        """
        characters_path = scenario_dir / "characters.json"
        if not characters_path.exists():
            return None
        
        characters_data = self._load_json(characters_path)
        
        # Handle different formats
        if "characters" in characters_data:
            # New format: { "characters": { ... } }
            return CharacterRegistry.from_scenario_characters(characters_data)
        else:
            # Simple format: { "email@example.com": { ... } }
            return CharacterRegistry.from_dict(characters_data)
    
    def _load_evaluation_criteria(
        self,
        scenario_dir: Path,
    ) -> list[dict[str, Any]] | None:
        """Load evaluation criteria from test_criteria.json.
        
        Args:
            scenario_dir: Directory containing the scenario.
            
        Returns:
            List of criteria definitions if file exists, None otherwise.
        """
        criteria_path = scenario_dir / "test_criteria.json"
        if not criteria_path.exists():
            return None
        
        criteria_data = self._load_json(criteria_path)
        
        # Handle both list and dict formats
        if isinstance(criteria_data, list):
            return criteria_data
        elif "criteria" in criteria_data:
            return criteria_data["criteria"]
        
        return None
    
    def extract_user_prompt(self, scenario: ScenarioData) -> str:
        """Extract user instructions from scenario.
        
        Helper method that returns the user prompt or a default message.
        
        Args:
            scenario: The loaded scenario data.
            
        Returns:
            User prompt string.
        """
        if scenario.user_prompt:
            return scenario.user_prompt
        
        return (
            f"Complete the scenario: {scenario.scenario_id}. "
            f"Description: {scenario.metadata.get('description', 'No description available.')}"
        )
    
    def list_available_scenarios(self) -> list[str]:
        """List all available scenario IDs.
        
        Returns:
            List of scenario IDs that can be loaded.
        """
        scenarios = set()
        
        for search_path in self._search_paths:
            if not search_path.exists():
                continue
            
            # Look for agent directories with scenario files
            for item in search_path.iterdir():
                if item.is_dir():
                    scenario_file = item / "scenario.ues-scenario.json"
                    if scenario_file.exists():
                        scenarios.add(item.name)
                elif item.is_file() and item.suffix == ".json":
                    # Direct scenario files: {name}.ues-scenario.json
                    if item.name.endswith(".ues-scenario.json"):
                        scenario_id = item.name.replace(".ues-scenario.json", "")
                        scenarios.add(scenario_id)
        
        return sorted(scenarios)
