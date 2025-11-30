"""Unit tests for API dependency injection.

This module tests the dependency injection providers in api/dependencies.py,
including engine initialization, retrieval, shutdown, and error handling.

Test Organization:
- get_simulation_engine tests - retrieval behavior and error handling
- initialize_simulation_engine tests - engine creation and initial state
- shutdown_simulation_engine tests - cleanup behavior
- Dependency override tests - FastAPI integration
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from api.dependencies import (
    _simulation_engine,
    get_simulation_engine,
    initialize_simulation_engine,
    shutdown_simulation_engine,
    SimulationEngineDep,
)
from models.simulation import SimulationEngine


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_global_engine():
    """Reset the global engine state before and after each test.
    
    This ensures tests are isolated and don't affect each other.
    """
    import api.dependencies as deps
    
    # Store original state
    original_engine = deps._simulation_engine
    
    # Reset before test
    deps._simulation_engine = None
    
    yield
    
    # Reset after test (cleanup)
    if deps._simulation_engine is not None and deps._simulation_engine.is_running:
        deps._simulation_engine.stop()
    deps._simulation_engine = original_engine


# =============================================================================
# get_simulation_engine Tests
# =============================================================================


class TestGetSimulationEngine:
    """Tests for get_simulation_engine dependency function."""

    def test_raises_runtime_error_when_not_initialized(self):
        """Test that RuntimeError is raised when engine is not initialized."""
        with pytest.raises(RuntimeError) as exc_info:
            get_simulation_engine()
        
        assert "SimulationEngine not initialized" in str(exc_info.value)
        assert "initialize_simulation_engine()" in str(exc_info.value)

    def test_returns_engine_after_initialization(self):
        """Test that engine is returned after initialization."""
        initialize_simulation_engine()
        
        engine = get_simulation_engine()
        
        assert engine is not None
        assert isinstance(engine, SimulationEngine)

    def test_returns_same_instance_on_multiple_calls(self):
        """Test that the same engine instance is returned on multiple calls."""
        initialize_simulation_engine()
        
        engine1 = get_simulation_engine()
        engine2 = get_simulation_engine()
        
        assert engine1 is engine2

    def test_returns_initialized_engine_instance(self):
        """Test that returned engine is the one created by initialize."""
        created_engine = initialize_simulation_engine()
        
        retrieved_engine = get_simulation_engine()
        
        assert retrieved_engine is created_engine


# =============================================================================
# initialize_simulation_engine Tests
# =============================================================================


class TestInitializeSimulationEngine:
    """Tests for initialize_simulation_engine function."""

    def test_returns_simulation_engine(self):
        """Test that a SimulationEngine is returned."""
        engine = initialize_simulation_engine()
        
        assert isinstance(engine, SimulationEngine)

    def test_engine_has_environment(self):
        """Test that created engine has an environment."""
        engine = initialize_simulation_engine()
        
        assert engine.environment is not None

    def test_engine_has_event_queue(self):
        """Test that created engine has an event queue."""
        engine = initialize_simulation_engine()
        
        assert engine.event_queue is not None

    def test_environment_has_time_state(self):
        """Test that environment has time state initialized."""
        engine = initialize_simulation_engine()
        
        assert engine.environment.time_state is not None

    def test_time_state_has_current_time(self):
        """Test that time state has a current time set."""
        before = datetime.now(timezone.utc)
        engine = initialize_simulation_engine()
        after = datetime.now(timezone.utc)
        
        current_time = engine.environment.time_state.current_time
        
        # Time should be between before and after
        assert before <= current_time <= after

    def test_time_state_is_timezone_aware(self):
        """Test that time state has timezone-aware datetime."""
        engine = initialize_simulation_engine()
        
        current_time = engine.environment.time_state.current_time
        
        assert current_time.tzinfo is not None
        assert current_time.tzinfo == timezone.utc

    def test_environment_has_weather_modality(self):
        """Test that environment has weather modality registered."""
        engine = initialize_simulation_engine()
        
        assert "weather" in engine.environment.modality_states

    def test_event_queue_is_empty(self):
        """Test that event queue starts empty."""
        engine = initialize_simulation_engine()
        
        assert len(engine.event_queue.events) == 0

    def test_engine_not_running_initially(self):
        """Test that engine is not running after initialization."""
        engine = initialize_simulation_engine()
        
        assert engine.is_running is False

    def test_overwrites_previous_engine(self):
        """Test that calling initialize again creates a new engine."""
        engine1 = initialize_simulation_engine()
        engine2 = initialize_simulation_engine()
        
        # Should be different instances
        assert engine1 is not engine2
        
        # get_simulation_engine should return the new one
        assert get_simulation_engine() is engine2


# =============================================================================
# shutdown_simulation_engine Tests
# =============================================================================


class TestShutdownSimulationEngine:
    """Tests for shutdown_simulation_engine function."""

    def test_does_not_raise_when_not_initialized(self):
        """Test that shutdown doesn't raise when engine is None."""
        # Should not raise any exceptions
        shutdown_simulation_engine()

    def test_sets_engine_to_none(self):
        """Test that shutdown sets global engine to None."""
        initialize_simulation_engine()
        
        shutdown_simulation_engine()
        
        # Should raise RuntimeError now
        with pytest.raises(RuntimeError):
            get_simulation_engine()

    def test_stops_running_engine(self):
        """Test that shutdown stops a running engine."""
        engine = initialize_simulation_engine()
        engine.start()  # Start the engine
        
        assert engine.is_running is True
        
        shutdown_simulation_engine()
        
        # Engine should have been stopped (even though it's now None in global)
        assert engine.is_running is False

    def test_handles_non_running_engine(self):
        """Test that shutdown handles non-running engine gracefully."""
        engine = initialize_simulation_engine()
        
        assert engine.is_running is False
        
        # Should not raise
        shutdown_simulation_engine()

    def test_idempotent_multiple_calls(self):
        """Test that multiple shutdown calls are safe."""
        initialize_simulation_engine()
        
        shutdown_simulation_engine()
        shutdown_simulation_engine()
        shutdown_simulation_engine()
        
        # All calls should succeed without raising


# =============================================================================
# SimulationEngineDep Type Alias Tests
# =============================================================================


class TestSimulationEngineDep:
    """Tests for the SimulationEngineDep type alias."""

    def test_type_alias_is_annotated(self):
        """Test that SimulationEngineDep is an Annotated type."""
        # The type should be usable as a type annotation
        # This is more of a compile-time check, but we verify it exists
        from typing import get_origin, get_args
        
        origin = get_origin(SimulationEngineDep)
        
        # Annotated types have origin of Annotated
        assert origin is not None

    def test_type_alias_wraps_simulation_engine(self):
        """Test that the type alias wraps SimulationEngine."""
        from typing import get_args
        
        args = get_args(SimulationEngineDep)
        
        # First arg should be SimulationEngine
        assert len(args) >= 1
        assert args[0] is SimulationEngine


# =============================================================================
# Integration with FastAPI Dependency Injection
# =============================================================================


class TestFastAPIDependencyIntegration:
    """Tests for FastAPI dependency injection integration."""

    def test_dependency_can_be_overridden(self):
        """Test that dependency can be overridden for testing."""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        
        @app.get("/test")
        def test_endpoint(engine: SimulationEngineDep):
            return {"has_engine": engine is not None}
        
        # Create a mock engine
        mock_engine = initialize_simulation_engine()
        
        # Override the dependency
        app.dependency_overrides[get_simulation_engine] = lambda: mock_engine
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json()["has_engine"] is True
        
        # Clean up
        app.dependency_overrides.clear()

    def test_dependency_raises_500_when_not_initialized(self):
        """Test that endpoints return 500 when engine not initialized."""
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        
        @app.get("/test")
        def test_endpoint(engine: SimulationEngineDep):
            return {"status": "ok"}
        
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test")
        
        # FastAPI converts RuntimeError to 500
        assert response.status_code == 500

    def test_dependency_injection_with_running_engine(self):
        """Test dependency injection with a properly running engine."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        
        app = FastAPI()
        
        @app.get("/status")
        def get_status(engine: SimulationEngineDep):
            return {
                "is_running": engine.is_running,
                "has_environment": engine.environment is not None,
            }
        
        # Initialize and start engine
        engine = initialize_simulation_engine()
        engine.start()
        
        app.dependency_overrides[get_simulation_engine] = lambda: engine
        
        client = TestClient(app)
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_running"] is True
        assert data["has_environment"] is True
        
        # Clean up
        engine.stop()
        app.dependency_overrides.clear()


# =============================================================================
# Thread Safety and Concurrency Tests
# =============================================================================


class TestConcurrencyBehavior:
    """Tests for concurrent access patterns (basic checks)."""

    def test_multiple_get_calls_return_same_instance(self):
        """Test that multiple rapid calls return the same instance."""
        initialize_simulation_engine()
        
        # Simulate multiple rapid accesses
        engines = [get_simulation_engine() for _ in range(100)]
        
        # All should be the same instance
        first = engines[0]
        for engine in engines[1:]:
            assert engine is first

    def test_initialization_is_idempotent_for_functionality(self):
        """Test that multiple initializations don't break functionality."""
        # Initialize multiple times
        for _ in range(5):
            initialize_simulation_engine()
        
        # Should still be able to get engine
        engine = get_simulation_engine()
        assert engine is not None
        assert isinstance(engine, SimulationEngine)


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_get_engine_after_shutdown_raises(self):
        """Test that getting engine after shutdown raises RuntimeError."""
        initialize_simulation_engine()
        shutdown_simulation_engine()
        
        with pytest.raises(RuntimeError):
            get_simulation_engine()

    def test_reinitialize_after_shutdown(self):
        """Test that engine can be reinitialized after shutdown."""
        initialize_simulation_engine()
        shutdown_simulation_engine()
        
        # Should be able to reinitialize
        new_engine = initialize_simulation_engine()
        
        assert new_engine is not None
        assert get_simulation_engine() is new_engine

    def test_initialize_creates_fresh_state(self):
        """Test that each initialization creates fresh state."""
        engine1 = initialize_simulation_engine()
        time1 = engine1.environment.time_state.current_time
        
        # Modify the engine state
        engine1.start()
        
        # Reinitialize
        engine2 = initialize_simulation_engine()
        time2 = engine2.environment.time_state.current_time
        
        # New engine should not be running
        assert engine2.is_running is False
        
        # Times might be slightly different (created at different moments)
        assert time2 >= time1

    def test_shutdown_cleans_up_loop(self):
        """Test that shutdown properly cleans up simulation loop."""
        engine = initialize_simulation_engine()
        engine.start(auto_advance=True, time_scale=10.0)
        
        # Engine should have a loop
        assert engine.is_running is True
        
        shutdown_simulation_engine()
        
        # Engine should be stopped
        assert engine.is_running is False
