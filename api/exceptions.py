"""Exception handlers for the UES FastAPI application.

This module defines custom exception handlers that convert Python exceptions
into consistent, user-friendly JSON responses.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError


# Custom Exception Classes
# These let you raise specific, meaningful errors in your route handlers


class ModalityNotFoundError(Exception):
    """Raised when a requested modality doesn't exist in the environment.
    
    Args:
        modality_name: The name of the modality that wasn't found.
        available_modalities: List of modalities that are available.
    """
    
    def __init__(self, modality_name: str, available_modalities: list[str]):
        self.modality_name = modality_name
        self.available_modalities = available_modalities
        super().__init__(f"Modality '{modality_name}' not found")


class SimulationNotRunningError(Exception):
    """Raised when an operation requires the simulation to be running but it's not.
    
    Args:
        message: Description of the operation that failed.
    """
    
    def __init__(self, message: str = "Simulation is not running"):
        self.message = message
        super().__init__(message)


# Exception Handlers
# These convert exceptions into JSON responses


async def modality_not_found_handler(request: Request, exc: ModalityNotFoundError):
    """Handle ModalityNotFoundError exceptions.
    
    Returns a 404 with details about what modality was requested
    and what modalities are actually available.
    
    Args:
        request: The incoming request that triggered the error.
        exc: The ModalityNotFoundError exception.
    
    Returns:
        JSONResponse with 404 status and helpful details.
    """
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Modality Not Found",
            "detail": f"The modality '{exc.modality_name}' does not exist",
            "requested_modality": exc.modality_name,
            "available_modalities": exc.available_modalities,
        },
    )


async def simulation_not_running_handler(request: Request, exc: SimulationNotRunningError):
    """Handle SimulationNotRunningError exceptions.
    
    Returns a 409 (Conflict) indicating the simulation needs to be started first.
    
    Args:
        request: The incoming request that triggered the error.
        exc: The SimulationNotRunningError exception.
    
    Returns:
        JSONResponse with 409 status.
    """
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "Simulation Not Running",
            "detail": exc.message,
            "suggestion": "Start the simulation with POST /simulation/start",
        },
    )


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors.
    
    These occur when request data doesn't match the expected Pydantic model.
    FastAPI normally handles these automatically, but we can customize the response.
    
    Args:
        request: The incoming request that triggered the error.
        exc: The ValidationError exception.
    
    Returns:
        JSONResponse with validation error details.
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": "The request data failed validation",
            "validation_errors": exc.errors(),
        },
    )


async def value_error_handler(request: Request, exc: ValueError):
    """Handle ValueError exceptions.
    
    ValueErrors typically indicate invalid input values that passed Pydantic
    validation but failed business logic validation.
    
    Args:
        request: The incoming request that triggered the error.
        exc: The ValueError exception.
    
    Returns:
        JSONResponse with error details.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "Invalid Value",
            "detail": str(exc),
            "type": "ValueError",
        },
    )


async def runtime_error_handler(request: Request, exc: RuntimeError):
    """Handle RuntimeError exceptions.
    
    RuntimeErrors typically indicate something went wrong during execution
    that wasn't a validation issue.
    
    Args:
        request: The incoming request that triggered the error.
        exc: The RuntimeError exception.
    
    Returns:
        JSONResponse with error details.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Runtime Error",
            "detail": str(exc),
            "type": "RuntimeError",
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions.
    
    This is a catch-all handler for unexpected errors. It prevents
    stack traces from being exposed to clients.
    
    Args:
        request: The incoming request that triggered the error.
        exc: The exception that was raised.
    
    Returns:
        JSONResponse with generic error message.
    """
    # In production, you'd want to log the full exception here
    import traceback
    print(f"❌ Unhandled exception: {exc}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "type": type(exc).__name__,
        },
    )
