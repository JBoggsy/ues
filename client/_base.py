"""Base class for all sub-clients.

This module provides the base class that all modality-specific sub-clients
inherit from. It provides common functionality for making HTTP requests
and accessing the shared HTTP client.

This is an internal module and should not be imported directly by users.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from client._http import AsyncHTTPClient, HTTPClient


class BaseClient:
    """Base class for synchronous sub-clients.
    
    All modality-specific clients (EmailClient, SMSClient, etc.) inherit
    from this class. It provides access to the shared HTTP client and
    convenience methods for making requests.
    
    Attributes:
        _http: The shared HTTP client for making requests.
    """
    
    def __init__(self, http_client: "HTTPClient") -> None:
        """Initialize the sub-client.
        
        Args:
            http_client: The shared HTTP client instance.
        """
        self._http = http_client
    
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request.
        
        Args:
            path: The URL path.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return self._http.get(path, params=params)
    
    def _post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a POST request.
        
        Args:
            path: The URL path.
            json: JSON body to send.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return self._http.post(path, json=json, params=params)
    
    def _put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a PUT request.
        
        Args:
            path: The URL path.
            json: JSON body to send.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return self._http.put(path, json=json, params=params)
    
    def _delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a DELETE request.
        
        Args:
            path: The URL path.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return self._http.delete(path, params=params)


class AsyncBaseClient:
    """Base class for asynchronous sub-clients.
    
    All async modality-specific clients (AsyncEmailClient, AsyncSMSClient, etc.)
    inherit from this class. It provides access to the shared async HTTP client
    and convenience methods for making requests.
    
    Attributes:
        _http: The shared async HTTP client for making requests.
    """
    
    def __init__(self, http_client: "AsyncHTTPClient") -> None:
        """Initialize the async sub-client.
        
        Args:
            http_client: The shared async HTTP client instance.
        """
        self._http = http_client
    
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make an async GET request.
        
        Args:
            path: The URL path.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return await self._http.get(path, params=params)
    
    async def _post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an async POST request.
        
        Args:
            path: The URL path.
            json: JSON body to send.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return await self._http.post(path, json=json, params=params)
    
    async def _put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make an async PUT request.
        
        Args:
            path: The URL path.
            json: JSON body to send.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return await self._http.put(path, json=json, params=params)
    
    async def _delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make an async DELETE request.
        
        Args:
            path: The URL path.
            params: Query parameters.
        
        Returns:
            The parsed JSON response.
        """
        return await self._http.delete(path, params=params)
