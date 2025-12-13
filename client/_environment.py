"""Environment state sub-client for the UES API.

This module provides EnvironmentClient and AsyncEnvironmentClient for interacting
with the environment state endpoints (/environment/*).

This is an internal module. Import from `client` instead.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

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


class ModalityListResponse(BaseModel):
    """List of available modalities.
    
    Attributes:
        modalities: List of modality type names.
        count: Total number of modalities.
    """

    modalities: list[str]
    count: int


class ModalityStateResponse(BaseModel):
    """Response model for a single modality's state.
    
    Attributes:
        modality_type: The type/name of the modality.
        current_time: The current simulator time (ISO format string).
        state: The full state of the modality.
    """

    modality_type: str
    current_time: str
    state: dict[str, Any]


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


class ModalityQueryResponse(BaseModel):
    """Response model for modality query results.
    
    Attributes:
        modality_type: The type/name of the modality queried.
        query: The query parameters that were used.
        results: The query results (modality-specific format).
        message: Optional message (e.g., if query not supported).
    """

    modality_type: str
    query: dict[str, Any]
    results: dict[str, Any] | list[Any]
    message: str | None = None


# Synchronous EnvironmentClient


class EnvironmentClient(BaseClient):
    """Synchronous client for environment state endpoints (/environment/*).
    
    This client provides methods for querying the current state of the
    simulated environment, including all modality states.
    
    Example:
        with UESClient() as client:
            # Get complete environment state
            state = client.environment.get_state()
            print(f"Current time: {state.current_time}")
            
            # List available modalities
            modalities = client.environment.list_modalities()
            print(f"Available: {modalities.modalities}")
            
            # Get specific modality state
            email_state = client.environment.get_modality("email")
            print(f"Email state: {email_state.state}")
            
            # Validate environment
            result = client.environment.validate()
            print(f"Valid: {result.valid}")
    """

    _BASE_PATH = "/environment"

    def get_state(self) -> EnvironmentStateResponse:
        """Get a complete snapshot of the current environment state.
        
        Returns the full state of all modalities plus the current simulator time.
        This can return a large response if there's a lot of simulated data.
        
        Returns:
            Complete environment state including all modality states and summaries.
        
        Raises:
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/state")
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

    def get_modality(self, modality: str) -> ModalityStateResponse:
        """Get the current state of a specific modality.
        
        This returns just the state for one modality, which is more efficient
        than fetching the entire environment state.
        
        Args:
            modality: The name of the modality to query (e.g., "email", "sms").
        
        Returns:
            The current state of the requested modality.
        
        Raises:
            NotFoundError: If the modality doesn't exist.
            APIError: If the request fails.
        """
        data = self._get(f"{self._BASE_PATH}/modalities/{modality}")
        return ModalityStateResponse(**data)

    def query_modality(
        self,
        modality: str,
        **query_params: Any,
    ) -> ModalityQueryResponse:
        """Query a modality's state with filters.
        
        This endpoint allows modality-specific queries with custom filter
        parameters. The query format varies by modality type.
        
        Args:
            modality: The name of the modality to query.
            **query_params: Modality-specific query parameters.
        
        Returns:
            Filtered query results from the modality.
        
        Raises:
            NotFoundError: If the modality doesn't exist.
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        
        Query Parameters by Modality:
            See the API documentation for modality-specific query parameters.
            Common parameters include: limit, offset, sort_by, sort_order.
        """
        data = self._post(
            f"{self._BASE_PATH}/modalities/{modality}/query",
            json=query_params,
        )
        return ModalityQueryResponse(**data)

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
    
    Example:
        async with AsyncUESClient() as client:
            # Get complete environment state
            state = await client.environment.get_state()
            print(f"Current time: {state.current_time}")
            
            # List available modalities
            modalities = await client.environment.list_modalities()
            print(f"Available: {modalities.modalities}")
            
            # Get specific modality state
            email_state = await client.environment.get_modality("email")
            print(f"Email state: {email_state.state}")
            
            # Validate environment
            result = await client.environment.validate()
            print(f"Valid: {result.valid}")
    """

    _BASE_PATH = "/environment"

    async def get_state(self) -> EnvironmentStateResponse:
        """Get a complete snapshot of the current environment state.
        
        Returns the full state of all modalities plus the current simulator time.
        This can return a large response if there's a lot of simulated data.
        
        Returns:
            Complete environment state including all modality states and summaries.
        
        Raises:
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/state")
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

    async def get_modality(self, modality: str) -> ModalityStateResponse:
        """Get the current state of a specific modality.
        
        This returns just the state for one modality, which is more efficient
        than fetching the entire environment state.
        
        Args:
            modality: The name of the modality to query (e.g., "email", "sms").
        
        Returns:
            The current state of the requested modality.
        
        Raises:
            NotFoundError: If the modality doesn't exist.
            APIError: If the request fails.
        """
        data = await self._get(f"{self._BASE_PATH}/modalities/{modality}")
        return ModalityStateResponse(**data)

    async def query_modality(
        self,
        modality: str,
        **query_params: Any,
    ) -> ModalityQueryResponse:
        """Query a modality's state with filters.
        
        This endpoint allows modality-specific queries with custom filter
        parameters. The query format varies by modality type.
        
        Args:
            modality: The name of the modality to query.
            **query_params: Modality-specific query parameters.
        
        Returns:
            Filtered query results from the modality.
        
        Raises:
            NotFoundError: If the modality doesn't exist.
            ValidationError: If query parameters are invalid.
            APIError: If the request fails.
        
        Query Parameters by Modality:
            See the API documentation for modality-specific query parameters.
            Common parameters include: limit, offset, sort_by, sort_order.
        """
        data = await self._post(
            f"{self._BASE_PATH}/modalities/{modality}/query",
            json=query_params,
        )
        return ModalityQueryResponse(**data)

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
