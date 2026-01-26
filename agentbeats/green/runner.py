"""Assessment lifecycle management for the Green Agent.

This module provides AssessmentRunner, which orchestrates the full assessment
lifecycle: setup, turn loop, and cleanup. It is used by the Agent class.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from client import AsyncUESClient

from agentbeats.green.key_manager import KeyManager, AssessmentKeys
from agentbeats.green.messenger import Messenger
from agentbeats.green.scenarios import ScenarioRegistry, ScenarioData
from agentbeats.green.session import AssessmentSession
from agentbeats.green.tracking import ActionTracker
from agentbeats.green.schemas import (
    AssessmentStartMessage,
    AssessmentResult,
    CriterionResult,
    InitialStateSummary,
    ModalityCounts,
    TurnStartMessage,
    TurnCompleteMessage,
    EarlyCompletionMessage,
    AssessmentCompleteMessage,
    AssessmentCompleteReason,
)
from agentbeats.green.a2a_integration import (
    MessageParseError,
    TurnResult,
    parse_purple_response,
    produce_result_artifact,
    serialize_message,
)


class AssessmentRunner:
    """Orchestrates the full assessment lifecycle.
    
    This class handles:
    - Setup: Reset UES, load scenario, provision API keys, send assessment_start
    - Turn loop: Wait for turn_complete, advance time, track actions, send turn_start
    - Cleanup: Invalidate API keys, compile results
    
    Example:
        >>> runner = AssessmentRunner(
        ...     ues_url="http://localhost:8000",
        ...     ues_client=ues_client,
        ... )
        >>> session, actions = await runner.run_assessment(
        ...     scenario_id="email_reply_generator",
        ...     participant_url="http://localhost:9000",
        ... )
    """
    
    def __init__(
        self,
        ues_url: str,
        ues_client: AsyncUESClient,
        key_manager: KeyManager | None = None,
        scenario_registry: ScenarioRegistry | None = None,
        messenger: Messenger | None = None,
    ) -> None:
        """Initialize the assessment runner.
        
        Args:
            ues_url: Base URL of the UES API (sent to Purple).
            ues_client: AsyncUESClient for UES operations.
            key_manager: KeyManager for API key management.
            scenario_registry: ScenarioRegistry for loading scenarios.
            messenger: Messenger for A2A communication.
        """
        self._ues_url = ues_url
        self._ues_client = ues_client
        self._key_manager = key_manager or KeyManager()
        self._scenario_registry = scenario_registry or ScenarioRegistry()
        self._messenger = messenger or Messenger()
        
        # Set during assessment
        self._session: AssessmentSession | None = None
        self._action_tracker: ActionTracker | None = None
        self._scenario_data: ScenarioData | None = None
    
    async def setup_assessment(
        self,
        scenario_id: str,
        participant_url: str,
        verbose_updates: bool = True,
        seed: int | None = None,
        default_time_step: timedelta | None = None,
        turn_timeout_seconds: float = 300.0,
    ) -> AssessmentSession:
        """Initialize the assessment: reset UES, load scenario, provision keys.
        
        Args:
            scenario_id: ID of the scenario to load.
            participant_url: A2A URL of the Purple agent.
            verbose_updates: Whether to emit detailed progress updates.
            seed: Random seed for reproducibility.
            default_time_step: Default time advance per turn.
            turn_timeout_seconds: Timeout for Purple agent's turn.
            
        Returns:
            AssessmentSession with all state initialized.
        """
        # 1. Generate assessment ID
        assessment_id = str(uuid4())
        
        # 2. Reset UES to clean state
        await self._ues_client.simulation.reset()
        
        # 3. Provision API keys
        purple_agent_id = f"purple-{assessment_id[:8]}"
        green_agent_id = f"green-{assessment_id[:8]}"
        keys = self._key_manager.provision_assessment_keys(
            assessment_id=assessment_id,
            proctor_agent_id=green_agent_id,
            user_agent_id=purple_agent_id,
        )
        
        # 4. Load and import scenario
        scenario = self._scenario_registry.get_scenario(scenario_id)
        await self._ues_client.scenario.import_scenario(scenario.scenario)
        
        # Store scenario data
        self._scenario_data = scenario
        
        # 5. Create session
        session = AssessmentSession(
            assessment_id=assessment_id,
            scenario_id=scenario_id,
            participant_url=participant_url,
            proctor_key=keys.proctor_key,
            user_key=keys.user_key,
            purple_agent_id=purple_agent_id,
            verbose_updates=verbose_updates,
            seed=seed,
            default_time_step=default_time_step or timedelta(hours=1),
            turn_timeout_seconds=turn_timeout_seconds,
        )
        
        # 6. Initialize action tracker
        self._action_tracker = ActionTracker(self._ues_client, purple_agent_id)
        self._session = session
        
        return session
    
    async def send_assessment_start(self, session: AssessmentSession) -> str:
        """Send AssessmentStartMessage to Purple agent.
        
        Args:
            session: The assessment session.
            
        Returns:
            Response from Purple agent.
        """
        # Build initial state summary
        summary = await self._build_initial_state_summary()
        
        # Get current simulator time
        time_state = await self._ues_client.time.get_state()
        
        # Create message
        message = AssessmentStartMessage(
            ues_url=self._ues_url,
            api_key=session.user_key,
            current_time=time_state.current_time,
            initial_state_summary=summary,
        )
        
        # Record turn start time
        session.update_turn_end_time(time_state.current_time)
        
        # Send via A2A
        response = await self._messenger.talk_to_agent(
            message=message.model_dump_json(),
            url=session.participant_url,
            new_conversation=True,
        )
        
        return response
    
    async def _build_initial_state_summary(self) -> InitialStateSummary:
        """Build a summary of the initial environment state.
        
        Returns:
            InitialStateSummary with counts for each modality.
        """
        summary_data: dict[str, Any] = {}
        
        # Email summary
        try:
            email_state = await self._ues_client.email.get_state()
            unread_count = sum(
                1 for email in email_state.emails
                if email.read_status == "unread"
            )
            summary_data["email"] = ModalityCounts(
                total=len(email_state.emails),
                unread=unread_count,
            )
        except Exception:
            pass  # Email modality not active
        
        # SMS summary
        try:
            sms_state = await self._ues_client.sms.get_state()
            unread_count = sum(
                1 for msg in sms_state.messages
                if not msg.read
            )
            summary_data["sms"] = ModalityCounts(
                total=len(sms_state.messages),
                unread=unread_count,
            )
        except Exception:
            pass  # SMS modality not active
        
        # Chat summary
        try:
            chat_state = await self._ues_client.chat.get_state()
            # Count unread as user messages without assistant response
            # (simplified - actual logic may differ)
            summary_data["chat"] = ModalityCounts(
                total=chat_state.total_message_count,
                unread=0,  # Chat doesn't have unread concept
            )
        except Exception:
            pass  # Chat modality not active
        
        # Calendar summary
        try:
            calendar_state = await self._ues_client.calendar.get_state()
            time_state = await self._ues_client.time.get_state()
            today = time_state.current_time.date()
            events_today = sum(
                1 for event in calendar_state.events
                if event.start_time.date() == today
            )
            summary_data["calendar"] = ModalityCounts(
                total=len(calendar_state.events),
                events_today=events_today,
            )
        except Exception:
            pass  # Calendar modality not active
        
        return InitialStateSummary(**summary_data)
    
    async def run_turn_loop(
        self,
        session: AssessmentSession,
        max_turns: int = 100,
    ) -> AssessmentCompleteReason:
        """Execute the main turn-based assessment loop.
        
        Args:
            session: The assessment session.
            max_turns: Maximum number of turns before stopping.
            
        Returns:
            Reason for assessment completion.
        """
        while session.current_turn < max_turns:
            session.increment_turn()
            
            # Wait for Purple's turn_complete message
            try:
                turn_result = await asyncio.wait_for(
                    self._wait_for_purple_response(session),
                    timeout=session.turn_timeout_seconds,
                )
            except asyncio.TimeoutError:
                return AssessmentCompleteReason.TIMEOUT
            
            # Check for early completion
            if turn_result.is_early_completion:
                return AssessmentCompleteReason.EARLY_COMPLETION
            
            # Track Purple's actions
            if self._action_tracker:
                actions = await self._action_tracker.get_actions_since(
                    session.last_turn_end_time,
                    turn=session.current_turn,
                )
                session.record_actions(actions)
            
            # Advance simulation time
            time_step = turn_result.time_step or session.default_time_step
            advance_result = await self._ues_client.time.advance(
                seconds=int(time_step.total_seconds())
            )
            
            # Update turn end time with new simulator time
            time_state = await self._ues_client.time.get_state()
            session.update_turn_end_time(time_state.current_time)
            
            # Check termination conditions
            if self._should_terminate(session, advance_result):
                return AssessmentCompleteReason.SCENARIO_COMPLETE
            
            # Send turn_start to Purple
            await self._send_turn_start(session, advance_result.events_executed)
        
        return AssessmentCompleteReason.SCENARIO_COMPLETE
    
    async def _wait_for_purple_response(
        self,
        session: AssessmentSession,
    ) -> TurnResult:
        """Wait for Purple agent's response and parse it.
        
        Waits for Purple agent to send either a TurnCompleteMessage or
        EarlyCompletionMessage via A2A protocol. The response is parsed
        into a TurnResult for uniform handling.
        
        Note: In the current implementation, this returns a default
        TurnResult. In production with full A2A bidirectional messaging,
        this would wait for an actual response from the Purple agent.
        
        Args:
            session: The assessment session.
            
        Returns:
            TurnResult with parsed response data.
        """
        # In full A2A implementation, this would wait for a response
        # from the Purple agent. For now, return default turn result.
        # The actual response parsing happens when we receive the
        # response from talk_to_agent calls.
        return TurnResult(
            is_early_completion=False,
            actions_taken=0,
            time_step=session.default_time_step,
        )
    
    async def _send_turn_start(
        self,
        session: AssessmentSession,
        events_processed: int,
    ) -> str:
        """Send TurnStartMessage to Purple agent.
        
        Args:
            session: The assessment session.
            events_processed: Number of events executed during time advance.
            
        Returns:
            Response from Purple agent.
        """
        time_state = await self._ues_client.time.get_state()
        
        message = TurnStartMessage(
            current_time=time_state.current_time,
            events_processed=events_processed,
        )
        
        response = await self._messenger.talk_to_agent(
            message=message.model_dump_json(),
            url=session.participant_url,
            new_conversation=False,  # Continue existing conversation
        )
        
        return response
    
    def _should_terminate(
        self,
        session: AssessmentSession,
        advance_result: Any,
    ) -> bool:
        """Check if the assessment should terminate.
        
        Args:
            session: The assessment session.
            advance_result: Result from time advance.
            
        Returns:
            True if assessment should end, False otherwise.
        """
        # For now, always continue. Scenario-specific termination conditions
        # will be implemented later.
        return False
    
    def parse_a2a_response(self, response: str) -> TurnResult:
        """Parse a raw A2A response into a TurnResult.
        
        This method can be used to parse responses received from
        talk_to_agent calls into structured TurnResult objects.
        
        Args:
            response: Raw JSON response from Purple agent.
            
        Returns:
            TurnResult with parsed data.
            
        Raises:
            MessageParseError: If the response cannot be parsed.
        """
        return TurnResult.from_response(response)
    
    async def produce_result(
        self,
        session: AssessmentSession,
        reason: AssessmentCompleteReason,
        criteria_results: list[CriterionResult],
    ) -> AssessmentResult:
        """Produce the final assessment result artifact.
        
        Args:
            session: The completed assessment session.
            reason: Why the assessment ended.
            criteria_results: Results from evaluation.
            
        Returns:
            Complete AssessmentResult artifact.
        """
        return produce_result_artifact(session, reason, criteria_results)
    
    async def send_assessment_complete(
        self,
        session: AssessmentSession,
        reason: AssessmentCompleteReason,
        message: str | None = None,
    ) -> str:
        """Send AssessmentCompleteMessage to Purple agent.
        
        Args:
            session: The assessment session.
            reason: Why the assessment ended.
            message: Optional explanation.
            
        Returns:
            Response from Purple agent.
        """
        complete_message = AssessmentCompleteMessage(
            reason=reason,
            message=message,
        )
        
        response = await self._messenger.talk_to_agent(
            message=complete_message.model_dump_json(),
            url=session.participant_url,
            new_conversation=False,
        )
        
        return response
    
    def cleanup_assessment(self, session: AssessmentSession) -> None:
        """Clean up assessment resources.
        
        Args:
            session: The assessment session.
        """
        # Invalidate API keys
        self._key_manager.cleanup_assessment(session.assessment_id)
        
        # Reset messenger state
        self._messenger.reset()
        
        # Clear local state
        self._session = None
        self._action_tracker = None
        self._scenario_data = None
    
    async def run_assessment(
        self,
        scenario_id: str,
        participant_url: str,
        verbose_updates: bool = True,
        seed: int | None = None,
        max_turns: int = 100,
    ) -> tuple[AssessmentSession, AssessmentCompleteReason]:
        """Run a complete assessment from start to finish.
        
        This is a convenience method that runs the full lifecycle.
        
        Args:
            scenario_id: ID of the scenario to load.
            participant_url: A2A URL of the Purple agent.
            verbose_updates: Whether to emit detailed progress updates.
            seed: Random seed for reproducibility.
            max_turns: Maximum number of turns.
            
        Returns:
            Tuple of (session, completion_reason).
        """
        try:
            # Setup
            session = await self.setup_assessment(
                scenario_id=scenario_id,
                participant_url=participant_url,
                verbose_updates=verbose_updates,
                seed=seed,
            )
            
            # Send assessment start
            await self.send_assessment_start(session)
            
            # Run turn loop
            reason = await self.run_turn_loop(session, max_turns=max_turns)
            
            # Send completion message
            await self.send_assessment_complete(session, reason)
            
            return session, reason
            
        finally:
            # Always cleanup
            if self._session:
                self.cleanup_assessment(self._session)
