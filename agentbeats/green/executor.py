"""A2A AgentExecutor for UES benchmark assessments.

This module handles incoming A2A requests and orchestrates the assessment
lifecycle: loading scenarios, coordinating with purple agents, advancing
simulation time, and evaluating results.
"""

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    Task,
    TaskState,
    UnsupportedOperationError,
    InvalidRequestError,
)
from a2a.utils.errors import ServerError
from a2a.utils import new_agent_text_message, new_task

from agent import Agent


TERMINAL_STATES = {
    TaskState.completed,
    TaskState.canceled,
    TaskState.failed,
    TaskState.rejected,
}


class Executor(AgentExecutor):
    """A2A executor that manages UES benchmark assessment sessions.

    Each assessment runs in its own context, with a dedicated Agent instance
    managing the scenario lifecycle and purple agent coordination.
    """

    def __init__(self):
        """Initialize the executor with empty agent registry."""
        self.agents: dict[str, Agent] = {}  # context_id -> Agent instance

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Handle an incoming A2A request.

        Args:
            context: The request context containing the message and current task.
            event_queue: Queue for emitting task events and updates.

        Raises:
            ServerError: If the request is invalid or task already processed.
        """
        msg = context.message
        if not msg:
            raise ServerError(error=InvalidRequestError(message="Missing message in request"))

        task = context.current_task
        if task and task.status.state in TERMINAL_STATES:
            raise ServerError(
                error=InvalidRequestError(
                    message=f"Task {task.id} already processed (state: {task.status.state})"
                )
            )

        # Create task if this is a new request
        if not task:
            task = new_task(msg)
            await event_queue.enqueue_event(task)

        context_id = task.context_id

        # Get or create agent instance for this assessment context
        agent = self.agents.get(context_id)
        if not agent:
            agent = Agent()
            self.agents[context_id] = agent

        # Create updater for progress reporting
        updater = TaskUpdater(event_queue, task.id, context_id)

        await updater.start_work()
        try:
            await agent.run(msg, updater)
            if not updater._terminal_state_reached:
                await updater.complete()
        except Exception as e:
            print(f"Assessment failed with error: {e}")
            await updater.failed(
                new_agent_text_message(
                    f"Assessment error: {e}",
                    context_id=context_id,
                    task_id=task.id,
                )
            )
        finally:
            # Clean up agent instance after assessment completes
            if context_id in self.agents:
                del self.agents[context_id]

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """Handle a cancellation request.

        Args:
            context: The request context.
            event_queue: Queue for emitting events.

        Raises:
            ServerError: Cancellation is not currently supported.
        """
        # TODO: Implement graceful cancellation of ongoing assessments
        raise ServerError(error=UnsupportedOperationError())
