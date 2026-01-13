"""Environment state sub-client for the UES API.

This module provides EnvironmentClient and AsyncEnvironmentClient for interacting
with the environment state endpoints (/environment/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Union, overload

from pydantic import BaseModel, Field

from client._base import AsyncBaseClient, BaseClient

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


# Response models for environment endpoints


class ModalitySummary(BaseModel):
    """Summary information about a single modality.
    
    Attributes:
        modality_type: The type/name of the modality.
        state_summary: Brief summary of the current state.
    """

    modality_type: str
    state_summary: str


class EnvironmentStateResponse(BaseModel):
    """Complete environment state snapshot.
    
    Attributes:
        current_time: The current simulator time (ISO format string).
        modalities: Dictionary mapping modality names to their full state.
        summary: List of brief summaries for each modality.
    """

    current_time: str
    modalities: dict[str, Any] = Field(
        description="Full state for each modality (can be large)"
    )
    summary: list[ModalitySummary]


class CompactSnapshotResponse(BaseModel):
    """Compact, LLM-context-optimized environment snapshot.
    
    Attributes:
        snapshot_time: The simulator time when snapshot was taken (ISO format).
        format: Always "compact" for this response type.
        modalities: Dictionary mapping modality names to their compact snapshots.
        events: Summary of pending events (if available).
    """

    snapshot_time: str
    format: Literal["compact"] = "compact"
    modalities: dict[str, Any] = Field(
        description="Compact state for each modality (LLM-optimized)"
    )
    events: dict[str, Any] | None = Field(
        default=None,
        description="Summary of pending events"
    )


class ModalityListResponse(BaseModel):
    """List of available modalities.
    
    Attributes:
        modalities: List of modality type names.
        count: Total number of modalities.
    """

    modalities: list[str]
    count: int


class ValidationResponse(BaseModel):
    """Response model for environment validation.
    
    Attributes:
        valid: Whether the environment is in a valid state.
        errors: List of validation error messages (empty if valid).
        checked_at: Timestamp when validation was performed.
    """

    valid: bool
    errors: list[str] = Field(default_factory=list)
    checked_at: datetime


# Synchronous EnvironmentClient


class EnvironmentClient(BaseClient):
    """Synchronous client for environment state endpoints (/environment/*).
    
    This client provides methods for querying the current state of the
    simulated environment, including all modality states.
    
    Note:
        To get the state of individual modalities, use the modality-specific
        clients (e.g., client.email.get_state(), client.location.get_state()).
    
    Example:
        with UESClient() as client:
            # Get complete environment state
            state = client.environment.get_state()
            print(f"Current time: {state.current_time}")
            
            # List available modalities
            modalities = client.environment.list_modalities()
            print(f"Available: {modalities.modalities}")
            
            # Validate environment
            result = client.environment.validate()
            print(f"Valid: {result.valid}")
    """

    _BASE_PATH = "/environment"

    @overload
    def get_state(
        self,
        *,
        compact: Literal[False] = False,
        format: Literal["json"] = "json",
    ) -> EnvironmentStateResponse: ...
    
    @overload
    def get_state(
        self,
        *,
        compact: Literal[True],
        format: Literal["json"] = "json",
    ) -> CompactSnapshotResponse: ...
    
    @overload
    def get_state(
        self,
        *,
        compact: Literal[True],
        format: Literal["text"],
    ) -> str: ...

    def get_state(
        self,
        *,
        compact: bool = False,
        format: Literal["json", "text"] = "json",
    ) -> Union[EnvironmentStateResponse, CompactSnapshotResponse, str]:
        """Get a snapshot of the current environment state.
        
        By default, returns the full state of all modalities. Use parameters
        to get a compact, LLM-optimized representation instead.
        
        Args:
            compact: If True, return compact LLM-optimized snapshot instead of full state.
            format: Output format - 'json' for structured data, 'text' for plain text
                (only applicable when compact=True).
        
        Returns:
            Depending on parameters:
            - Default: EnvironmentStateResponse with full modality data
            - compact=True, format="json": CompactSnapshotResponse with LLM-optimized data
            - compact=True, format="text": Plain text string for direct LLM injection
        
        Raises:
            APIError: If the request fails.
        
        Example:
            # Full state (default)
            state = client.environment.get_state()
            
            # Compact JSON snapshot
            snapshot = client.environment.get_state(compact=True)
            
            # Plain text for LLM prompt injection
            text = client.environment.get_state(compact=True, format="text")
        """
        params = {}
        if compact:
            params["compact"] = "true"
            params["format"] = format
        
        if compact and format == "text":
            # For text format, we need to handle the plain text response
            response = self._http_client.get(
                f"{self._BASE_PATH}/state",
                params=params,
            )
            return response.text
        
        data = self._get(f"{self._BASE_PATH}/state", params=params if params else None)
        
        if compact:
            return CompactSnapshotResponse(**data)
        return EnvironmentStateResponse(**data)

    def list_modalities(self) -> ModalityListResponse:
        """Get a list of all available modalities in the environment.
        
        This is a lightweight endpoint that just lists what modalities are present
        without returning their full state.
        
        Returns:
            List of modality names and the total count.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/modalities")
        return ModalityListResponse(**data)

    def validate(self) -> ValidationResponse:
        """Validate the current environment state for consistency.
        
        Checks all modalities for internal consistency and cross-modality
        integrity issues.
        
        Returns:
            Validation results with any errors found.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._post(f"{self._BASE_PATH}/validate")
        return ValidationResponse(**data)


# Asynchronous AsyncEnvironmentClient


class AsyncEnvironmentClient(AsyncBaseClient):
    """Asynchronous client for environment state endpoints (/environment/*).
    
    This client provides async methods for querying the current state of the
    simulated environment, including all modality states.
    
    Note:
        To get the state of individual modalities, use the modality-specific
        clients (e.g., await client.email.get_state(), await client.location.get_state()).
    
    Example:
        async with AsyncUESClient() as client:
            # Get complete environment state
            state = await client.environment.get_state()
            print(f"Current time: {state.current_time}")
            
            # List available modalities
            modalities = await client.environment.list_modalities()
            print(f"Available: {modalities.modalities}")
            
            # Validate environment
            result = await client.environment.validate()
            print(f"Valid: {result.valid}")
    """

    _BASE_PATH = "/environment"

    @overload
    async def get_state(
        self,
        *,
        compact: Literal[False] = False,
        format: Literal["json"] = "json",
    ) -> EnvironmentStateResponse: ...
    
    @overload
    async def get_state(
        self,
        *,
        compact: Literal[True],
        format: Literal["json"] = "json",
    ) -> CompactSnapshotResponse: ...
    
    @overload
    async def get_state(
        self,
        *,
        compact: Literal[True],
        format: Literal["text"],
    ) -> str: ...

    async def get_state(
        self,
        *,
        compact: bool = False,
        format: Literal["json", "text"] = "json",
    ) -> Union[EnvironmentStateResponse, CompactSnapshotResponse, str]:
        """Get a snapshot of the current environment state.
        
        By default, returns the full state of all modalities. Use parameters
        to get a compact, LLM-optimized representation instead.
        
        Args:
            compact: If True, return compact LLM-optimized snapshot instead of full state.
            format: Output format - 'json' for structured data, 'text' for plain text
                (only applicable when compact=True).
        
        Returns:
            Depending on parameters:
            - Default: EnvironmentStateResponse with full modality data
            - compact=True, format="json": CompactSnapshotResponse with LLM-optimized data
            - compact=True, format="text": Plain text string for direct LLM injection
        
        Raises:
            APIError: If the request fails.
        
        Example:
            # Full state (default)
            state = await client.environment.get_state()
            
            # Compact JSON snapshot
            snapshot = await client.environment.get_state(compact=True)
            
            # Plain text for LLM prompt injection
            text = await client.environment.get_state(compact=True, format="text")
        """
        params = {}
        if compact:
            params["compact"] = "true"
            params["format"] = format
        
        if compact and format == "text":
            # For text format, we need to handle the plain text response
            response = await self._http_client.get(
                f"{self._BASE_PATH}/state",
                params=params,
            )
            return response.text
        
        data = await self._get(f"{self._BASE_PATH}/state", params=params if params else None)
        
        if compact:
            return CompactSnapshotResponse(**data)
        return EnvironmentStateResponse(**data)

    async def list_modalities(self) -> ModalityListResponse:
        """Get a list of all available modalities in the environment.
        
        This is a lightweight endpoint that just lists what modalities are present
        without returning their full state.
        
        Returns:
            List of modality names and the total count.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/modalities")
        return ModalityListResponse(**data)

    async def validate(self) -> ValidationResponse:
        """Validate the current environment state for consistency.
        
        Checks all modalities for internal consistency and cross-modality
        integrity issues.
        
        Returns:
            Validation results with any errors found.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._post(f"{self._BASE_PATH}/validate")
        return ValidationResponse(**data)
