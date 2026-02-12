"""Main entry point for the User Environment Simulator (UES) FastAPI application.

This module creates and configures the FastAPI app instance that serves the REST API
for simulating user environments and testing AI personal assistants.

To run the development server:
    uv run uvicorn main:app --reload

To run in production:
    uv run uvicorn main:app --host 0.0.0.0 --port 8000
"""

import json
import logging
import os
import stat
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Load environment variables from .env file before any other imports
# that might depend on them (e.g., CORS_ORIGINS, UES_ADMIN_KEY)
load_dotenv()

from ues.api.auth import initialize_api_key_registry, shutdown_api_key_registry
from ues.api.dependencies import initialize_simulation_engine, shutdown_simulation_engine
from ues.api.exceptions import (
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
from ues.api.middleware import (
    AccessLoggingMiddleware,
    initialize_access_log,
    shutdown_access_log,
)
from ues.api.routes import access_logs as access_logs_routes
from ues.api.routes import calendar as calendar_routes
from ues.api.routes import chat as chat_routes
from ues.api.routes import contacts as contacts_routes
from ues.api.routes import email as email_routes
from ues.api.routes import environment as environment_routes
from ues.api.routes import events as events_routes
from ues.api.routes import keys as keys_routes
from ues.api.routes import location as location_routes
from ues.api.routes import scenario as scenario_routes
from ues.api.routes import simulation as simulation_routes
from ues.api.routes import sms as sms_routes
from ues.api.routes import time as time_routes
from ues.api.routes import weather as weather_routes
from ues.api.routes import webhooks as webhooks_routes
from ues.api.routes import websocket as websocket_routes
from ues.api.webhooks import webhook_dispatcher


def _write_admin_key_file(
    file_path: str,
    secret: str,
    key_id: str,
) -> bool:
    """Write admin key credentials to a JSON file with restricted permissions.
    
    The file is written with owner-only read/write permissions (0600) on Unix
    systems. On Windows, standard file permissions apply.
    
    Args:
        file_path: Path where the key file should be written.
        secret: The admin key secret (plaintext).
        key_id: The admin key ID.
    
    Returns:
        True if the file was written successfully, False otherwise.
    """
    key_data = {
        "secret": secret,
        "key_id": key_id,
    }
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(key_data, indent=2) + "\n")
        # Set owner-only read/write permissions on Unix
        if sys.platform != "win32":
            path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        return True
    except OSError as e:
        logger.error(f"Failed to write admin key file to {file_path}: {e}")
        print(
            f"⚠️  WARNING: Failed to write admin key file to {file_path}: {e}",
            file=sys.stderr,
        )
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events.
    
    This context manager runs code at startup (before yield) and shutdown (after yield).
    It's the modern way to handle FastAPI lifecycle events.
    
    Supports the following environment variables for automated key management:
    
    - ``UES_ADMIN_KEY``: Pre-set the admin key secret instead of generating a
      random one. The server will use this exact value as the admin API key.
      Must be at least 32 characters long.
    - ``UES_ADMIN_KEY_FILE``: Path to a file where the admin key credentials
      will be written as JSON (``{"secret": "...", "key_id": "..."}``). The
      file is created with 0600 permissions on Unix systems.
    
    Args:
        app: The FastAPI application instance.
    
    Yields:
        Control back to FastAPI to handle requests.
    """
    # Startup: Initialize the simulation engine
    print("🚀 Starting UES - Initializing SimulationEngine...")
    initialize_simulation_engine()
    print("✅ SimulationEngine initialized")
    
    # Initialize API key registry and create admin key
    # Check for pre-set admin key from environment variable
    preset_admin_key = os.getenv("UES_ADMIN_KEY")
    admin_key_file = os.getenv("UES_ADMIN_KEY_FILE")
    
    print("🔐 Initializing API key registry...")
    admin_secret, admin_key = initialize_api_key_registry(
        admin_secret=preset_admin_key
    )
    print("✅ API key registry initialized")

    # Report admin key source and optionally write to file
    if preset_admin_key:
        print("")
        print("=" * 60)
        print("🔑 Admin key loaded from UES_ADMIN_KEY environment variable")
        print(f"   Key ID: {admin_key.key_id}")
        print("=" * 60)
    elif admin_key_file:
        print("")
        print("=" * 60)
        if _write_admin_key_file(admin_key_file, admin_secret, admin_key.key_id):
            print(f"🔑 Admin key written to: {admin_key_file}")
        else:
            print(f"🔑 ADMIN API KEY (file write failed, showing here):")
            print(f"   Secret: {admin_secret}")
        print(f"   Key ID: {admin_key.key_id}")
        print("=" * 60)
    else:
        print("")
        print("=" * 60)
        print("🔑 ADMIN API KEY (save this - it won't be shown again!):")
        print(f"   Secret: {admin_secret}")
        print(f"   Key ID: {admin_key.key_id}")
        print("=" * 60)
    print("")
    
    # Initialize access logging
    print("📝 Initializing access logging...")
    initialize_access_log(max_entries=10000)
    print("✅ Access logging initialized")
    
    yield  # App runs and handles requests here
    
    # Shutdown: Clean up resources
    print("🛑 Shutting down UES - Cleaning up...")
    await webhook_dispatcher.close()
    shutdown_access_log()
    shutdown_simulation_engine()
    shutdown_api_key_registry()
    print("✅ Shutdown complete")


from ues.models.version import UES_VERSION

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

# Add access logging middleware (after CORS to properly handle preflight requests)
# Note: Middleware is applied in reverse order, so AccessLogging runs first
app.add_middleware(AccessLoggingMiddleware)

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
app.include_router(keys_routes.router)
app.include_router(access_logs_routes.router)
app.include_router(weather_routes.router)
app.include_router(email_routes.router)
app.include_router(sms_routes.router)
app.include_router(chat_routes.router)
app.include_router(calendar_routes.router)
app.include_router(contacts_routes.router)
app.include_router(location_routes.router)
app.include_router(webhooks_routes.router)
app.include_router(websocket_routes.router)


@app.get("/")
async def root():
    """Root endpoint - returns a welcome message.
    
    Returns:
        A dictionary with a welcome message.
    """
    return {
        "message": "Welcome to the User Environment Simulator API",
        "version": "0.3.0",
        "docs_url": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring.
    
    Returns:
        A dictionary indicating the service is healthy.
    """
    return {"status": "healthy"}
