"""Hold models for multi-agent coordination.

This module provides the Hold class and HoldManager for coordinating
concurrent agent access to the simulation. When multiple agents need
to interact with the simulation (e.g., one advancing time while another
generates LLM responses), holds prevent race conditions by blocking
time advancement while holds are active.

See docs/SIMULATION_ENGINE.md for design documentation.

Example usage:
    # Agent 1 receives an event and needs time to generate a response
    hold_id = engine.hold_manager.acquire(
        reason="Generating LLM response to email",
        timeout_seconds=60.0
    )
    
    # ... Agent 1 generates response and schedules events ...
    
    # Agent 1 releases the hold
    engine.hold_manager.release(hold_id)
    
    # Time advancement (by Agent 2) was blocked until release
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class Hold(BaseModel):
    """A hold on simulation time advancement.
    
    When a hold is active, time advancement operations (advance_time,
    set_time, skip_to_next_event) will raise an error until all holds
    are released or expire.
    
    Attributes:
        hold_id: Unique identifier for this hold.
        reason: Optional human-readable description of why the hold was acquired.
        acquired_at: UTC timestamp when the hold was acquired.
        timeout_seconds: Optional timeout after which the hold auto-expires.
            None means no timeout (hold must be explicitly released).
        agent_id: Optional identifier for the agent that acquired the hold.
    """
    
    hold_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reason: Optional[str] = None
    acquired_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    timeout_seconds: Optional[float] = None
    agent_id: Optional[str] = None
    
    model_config = ConfigDict(frozen=False)
    
    @property
    def expires_at(self) -> Optional[datetime]:
        """Calculate when this hold expires, if it has a timeout.
        
        Returns:
            UTC datetime when hold expires, or None if no timeout.
        """
        if self.timeout_seconds is None:
            return None
        return self.acquired_at + __import__('datetime').timedelta(
            seconds=self.timeout_seconds
        )
    
    def is_expired(self, current_time: Optional[datetime] = None) -> bool:
        """Check if this hold has expired.
        
        Args:
            current_time: Time to check against (defaults to now UTC).
        
        Returns:
            True if hold has a timeout and that timeout has passed.
        """
        if self.timeout_seconds is None:
            return False
        
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        return current_time >= self.expires_at


class HoldManager(BaseModel):
    """Manages active holds on simulation time advancement.
    
    Thread-safe manager for acquiring, releasing, and checking holds.
    Time advancement should check has_active_holds() before proceeding.
    
    Attributes:
        active_holds: Dictionary mapping hold_id to Hold instances.
        default_timeout_seconds: Default timeout for new holds if none specified.
            None means holds have no timeout by default.
    """
    
    active_holds: dict[str, Hold] = Field(default_factory=dict)
    default_timeout_seconds: Optional[float] = 300.0  # 5 minutes default
    
    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)
    
    def acquire(
        self,
        reason: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        agent_id: Optional[str] = None,
        use_default_timeout: bool = True,
    ) -> str:
        """Acquire a new hold on time advancement.
        
        Creates and registers a new hold. While any holds are active,
        time advancement operations will be blocked.
        
        Args:
            reason: Human-readable description of why the hold is needed.
            timeout_seconds: Optional timeout in seconds. If None and
                use_default_timeout is True, uses default_timeout_seconds.
            agent_id: Optional identifier for the acquiring agent.
            use_default_timeout: Whether to use default timeout if none specified.
        
        Returns:
            The hold_id for the newly acquired hold.
        """
        # Clean up expired holds first
        self._cleanup_expired()
        
        # Determine timeout
        effective_timeout = timeout_seconds
        if effective_timeout is None and use_default_timeout:
            effective_timeout = self.default_timeout_seconds
        
        # Create the hold
        hold = Hold(
            reason=reason,
            timeout_seconds=effective_timeout,
            agent_id=agent_id,
        )
        
        self.active_holds[hold.hold_id] = hold
        
        logger.info(
            f"Hold acquired: {hold.hold_id}"
            + (f" (reason: {reason})" if reason else "")
            + (f" (timeout: {effective_timeout}s)" if effective_timeout else " (no timeout)")
        )
        
        return hold.hold_id
    
    def release(self, hold_id: str) -> bool:
        """Release an active hold.
        
        Args:
            hold_id: The ID of the hold to release.
        
        Returns:
            True if the hold was found and released, False if not found.
        """
        if hold_id in self.active_holds:
            del self.active_holds[hold_id]
            logger.info(f"Hold released: {hold_id}")
            return True
        
        # Check if it was already expired and cleaned up
        logger.warning(f"Hold not found for release: {hold_id}")
        return False
    
    def get_hold(self, hold_id: str) -> Optional[Hold]:
        """Get a specific hold by ID.
        
        Args:
            hold_id: The ID of the hold to retrieve.
        
        Returns:
            The Hold instance if found and not expired, None otherwise.
        """
        self._cleanup_expired()
        return self.active_holds.get(hold_id)
    
    def list_holds(self) -> list[Hold]:
        """Get all active (non-expired) holds.
        
        Returns:
            List of active Hold instances.
        """
        self._cleanup_expired()
        return list(self.active_holds.values())
    
    def has_active_holds(self) -> bool:
        """Check if any holds are currently active.
        
        This method should be called before time advancement operations.
        
        Returns:
            True if at least one non-expired hold is active.
        """
        self._cleanup_expired()
        return len(self.active_holds) > 0
    
    def active_hold_count(self) -> int:
        """Get the number of active holds.
        
        Returns:
            Number of non-expired active holds.
        """
        self._cleanup_expired()
        return len(self.active_holds)
    
    def clear_all(self) -> int:
        """Clear all active holds.
        
        Use with caution - this force-releases all holds regardless
        of timeout or reason.
        
        Returns:
            Number of holds that were cleared.
        """
        count = len(self.active_holds)
        self.active_holds.clear()
        logger.info(f"All holds cleared: {count} holds removed")
        return count
    
    def _cleanup_expired(self) -> int:
        """Remove any expired holds.
        
        Called internally before checking holds.
        
        Returns:
            Number of holds that were expired and removed.
        """
        now = datetime.now(timezone.utc)
        expired_ids = [
            hold_id
            for hold_id, hold in self.active_holds.items()
            if hold.is_expired(now)
        ]
        
        for hold_id in expired_ids:
            del self.active_holds[hold_id]
            logger.info(f"Hold expired and removed: {hold_id}")
        
        return len(expired_ids)


class HoldError(Exception):
    """Raised when a time operation is blocked by active holds.
    
    Attributes:
        active_holds: List of holds that are blocking the operation.
        message: Human-readable error message.
    """
    
    def __init__(self, active_holds: list[Hold], message: Optional[str] = None):
        """Initialize HoldError with blocking holds.
        
        Args:
            active_holds: List of holds blocking the operation.
            message: Optional custom message.
        """
        self.active_holds = active_holds
        
        if message is None:
            hold_count = len(active_holds)
            hold_reasons = [h.reason for h in active_holds if h.reason]
            if hold_reasons:
                reasons_str = ", ".join(hold_reasons[:3])
                if len(hold_reasons) > 3:
                    reasons_str += f" (and {len(hold_reasons) - 3} more)"
                message = (
                    f"Time advancement blocked by {hold_count} active hold(s): "
                    f"{reasons_str}"
                )
            else:
                message = f"Time advancement blocked by {hold_count} active hold(s)"
        
        super().__init__(message)
