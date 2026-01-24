"""Main entry point for the User Environment Simulator (UES) FastAPI application.

This module creates and configures the FastAPI app instance that serves the REST API
for simulating user environments and testing AI personal assistants.

To run the development server:
    uv run uvicorn main:app --reload

To run in production:
    uv run uvicorn main:app --host 0.0.0.0 --port 8000

To run with access control enabled (for AgentBeats assessments):
    UES_ACCESS_CONTROL=true uv run uvicorn main:app --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

# Load environment variables from .env file before any other imports
# that might depend on them (e.g., WeatherState reads OPENWEATHER_API_KEY)
load_dotenv()

from api.dependencies import initialize_simulation_engine, shutdown_simulation_engine
from api.exceptions import (
    ModalityNotFoundError,
    SimulationNotRunningError,
    generic_exception_handler,
    modality_not_found_handler,
    request_validation_exception_handler,
    runtime_error_handler,
    simulation_not_running_handler,
    validation_exception_handler,
    value_error_handler,
)
from api.routes import admin as admin_routes
from api.routes import calendar as calendar_routes
from api.routes import chat as chat_routes
from api.routes import email as email_routes
from api.routes import environment as environment_routes
from api.routes import events as events_routes
from api.routes import location as location_routes
from api.routes import scenario as scenario_routes
from api.routes import simulation as simulation_routes
from api.routes import sms as sms_routes
from api.routes import time as time_routes
from api.routes import weather as weather_routes
from api.routes import webhooks as webhooks_routes
from api.routes import websocket as websocket_routes
from api.webhooks import webhook_dispatcher

# Configure logging
logger = logging.getLogger(__name__)

# Access control configuration
# When enabled, all non-public endpoints require X-API-Key header
ACCESS_CONTROL_ENABLED = os.getenv("UES_ACCESS_CONTROL", "false").lower() == "true"


class AccessControlMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing API key-based access control.
    
    When enabled via UES_ACCESS_CONTROL=true, this middleware:
    1. Allows public routes (/, /health, /docs, etc.) without authentication
    2. Requires X-API-Key header for all other routes
    3. Validates the key and checks permissions for the endpoint
    4. Returns 401 for missing/invalid keys, 403 for insufficient permissions
    5. Logs request attribution for tracing
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request through access control checks."""
        from api.access_control import (
            get_route_permission,
            is_access_allowed,
            key_registry,
        )
        
        method = request.method
        path = request.url.path
        
        # Get required permission level for this route
        required_level = get_route_permission(method, path)
        
        # Public routes - allow without authentication
        if required_level is None:
            return await call_next(request)
        
        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning(f"Access denied: missing API key for {method} {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing X-API-Key header"},
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # Validate the key
        context = key_registry.validate_key(api_key)
        
        if context is None:
            logger.warning(f"Access denied: invalid API key for {method} {path}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or expired API key"},
                headers={"WWW-Authenticate": "ApiKey"},
            )
        
        # Check permission level
        if not is_access_allowed(required_level, context.level):
            logger.warning(
                f"Access denied: {context.level.value} cannot access {method} {path} "
                f"(requires {required_level.value}) - agent_id={context.agent_id}"
            )
            return JSONResponse(
                status_code=403,
                content={
                    "detail": f"This endpoint requires {required_level.value}-level access"
                },
            )
        
        # Log successful access for tracing
        logger.debug(
            f"Access granted: {method} {path} - "
            f"level={context.level.value}, agent_id={context.agent_id}, "
            f"assessment_id={context.assessment_id}"
        )
        
        # Store context in request state for route handlers if needed
        request.state.access_context = context
        
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events.
    
    This context manager runs code at startup (before yield) and shutdown (after yield).
    It's the modern way to handle FastAPI lifecycle events.
    
    Args:
        app: The FastAPI application instance.
    
    Yields:
        Control back to FastAPI to handle requests.
    """
    # Startup: Initialize the simulation engine
    print("🚀 Starting UES - Initializing SimulationEngine...")
    initialize_simulation_engine()
    print("✅ SimulationEngine initialized")
    if ACCESS_CONTROL_ENABLED:
        print("🔐 Access control ENABLED - API keys required")
    else:
        print("🔓 Access control DISABLED - open access")
    
    yield  # App runs and handles requests here
    
    # Shutdown: Clean up resources
    print("🛑 Shutting down UES - Cleaning up...")
    await webhook_dispatcher.close()
    shutdown_simulation_engine()
    print("✅ Shutdown complete")


from models.version import UES_VERSION

# Create the FastAPI application instance
app = FastAPI(
    title="User Environment Simulator (UES)",
    description="API for simulating user environments to test AI personal assistants",
    version=UES_VERSION,
    lifespan=lifespan,  # Register the lifespan handler
)

# Configure CORS for web UI access
# Read allowed origins from environment variable (comma-separated)
# Example: CORS_ORIGINS=http://localhost:5173,http://192.168.1.42:5173
cors_origins_env = os.getenv("CORS_ORIGINS", "")
cors_origins = [origin.strip() for origin in cors_origins_env.split(",") if len(origin.strip()) > 0]

# If no origins specified, allow common development origins
if not cors_origins:
    cors_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add access control middleware (only when enabled)
if ACCESS_CONTROL_ENABLED:
    app.add_middleware(AccessControlMiddleware)
    logger.info("🔐 Access control ENABLED - API keys required for non-public endpoints")
else:
    logger.info("🔓 Access control DISABLED - all endpoints accessible without authentication")

# Register exception handlers
# These convert Python exceptions into clean JSON responses
# Order matters: specific exceptions before general ones
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(ModalityNotFoundError, modality_not_found_handler)
app.add_exception_handler(SimulationNotRunningError, simulation_not_running_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(RuntimeError, runtime_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Register route modules
# Each router groups related endpoints together
app.include_router(time_routes.router)
app.include_router(environment_routes.router)
app.include_router(events_routes.router)
app.include_router(simulation_routes.router)
app.include_router(scenario_routes.router)
app.include_router(weather_routes.router)
app.include_router(email_routes.router)
app.include_router(sms_routes.router)
app.include_router(chat_routes.router)
app.include_router(calendar_routes.router)
app.include_router(location_routes.router)
app.include_router(webhooks_routes.router)
app.include_router(websocket_routes.router)

# Register admin routes (only when access control is enabled)
if ACCESS_CONTROL_ENABLED:
    app.include_router(admin_routes.router)


@app.get("/")
async def root():
    """Root endpoint - returns a welcome message.
    
    Returns:
        A dictionary with a welcome message.
    """
    return {
        "message": "Welcome to the User Environment Simulator API",
        "version": "0.1.0",
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring.
    
    Returns:
        A dictionary indicating the service is healthy.
    """
    return {"status": "healthy"}
