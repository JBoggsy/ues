"""Hook manager for on_event evaluation dispatch.

This module provides the EventHookManager class, which handles registration
and dispatch of on_event criteria evaluators.
"""

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable

from ues.agent_testing.context import EvalContext
from ues.agent_testing.results import EvalResult
from ues.agent_testing.schema import CriterionSchema, EvalTiming


@dataclass
class RegisteredHook:
    """A registered event hook with its criterion and functions.

    Attributes:
        criterion: The criterion schema this hook evaluates.
        evaluator: The evaluator function to call.
        event_filter: Optional filter function to determine if an event
            should trigger this hook.
        results: Accumulated results from each evaluation.
    """

    criterion: CriterionSchema
    evaluator: Callable[[EvalContext, dict], EvalResult]
    event_filter: Callable[[dict], bool] | None = None
    results: list[EvalResult] = field(default_factory=list)

    def matches_event(self, event: dict[str, Any]) -> bool:
        """Check if an event should trigger this hook.

        Args:
            event: The event dictionary to check.

        Returns:
            True if the event should trigger evaluation.
        """
        if self.event_filter is None:
            # No filter means match all events
            return True
        return self.event_filter(event)


class EventHookManager:
    """Manages registration and dispatch of on_event evaluators.

    The hook manager tracks which criteria should be evaluated on events,
    dispatches evaluations when matching events occur, and accumulates
    results for later aggregation.

    Example:
        >>> manager = EventHookManager()
        >>> manager.register_hook(criterion, evaluator_fn, filter_fn)
        >>> # When an event occurs:
        >>> await manager.dispatch_event(event, context)
        >>> # Get accumulated results:
        >>> results = manager.get_accumulated_results()
    """

    def __init__(self) -> None:
        """Initialize the hook manager."""
        self._hooks: list[RegisteredHook] = []

    def register_hook(
        self,
        criterion: CriterionSchema,
        evaluator: Callable[[EvalContext, dict], EvalResult],
        event_filter: Callable[[dict], bool] | None = None,
    ) -> None:
        """Register a new event hook.

        Args:
            criterion: The criterion schema being registered.
            evaluator: The evaluator function to call for matching events.
            event_filter: Optional filter to determine which events trigger
                this evaluator. If None, all events will trigger it.

        Raises:
            ValueError: If the criterion is not an on_event criterion.
        """
        if criterion.eval_timing != EvalTiming.ON_EVENT:
            raise ValueError(
                f"Cannot register hook for criterion with timing "
                f"'{criterion.eval_timing}'. Expected 'on_event'."
            )

        hook = RegisteredHook(
            criterion=criterion,
            evaluator=evaluator,
            event_filter=event_filter,
        )
        self._hooks.append(hook)

    async def dispatch_event(
        self,
        event: dict[str, Any],
        context: EvalContext,
    ) -> list[tuple[str, EvalResult]]:
        """Dispatch an event to all matching hooks.

        Calls the evaluator for each hook whose filter matches the event,
        accumulates the results, and returns them.

        Args:
            event: The event dictionary.
            context: The test context (will be cloned with trigger_event set).

        Returns:
            List of (criterion_id, EvalResult) tuples for evaluations that ran.
        """
        results: list[tuple[str, EvalResult]] = []

        for hook in self._hooks:
            if not hook.matches_event(event):
                continue

            # Create context with trigger event
            event_context = context.with_trigger_event(event)

            # Call the evaluator (handle sync and async)
            try:
                result = await self._call_evaluator(
                    hook.evaluator,
                    event_context,
                    hook.criterion.params,
                )
                hook.results.append(result)
                results.append((hook.criterion.id, result))
            except Exception as e:
                # Create an error result
                error_result = EvalResult(
                    score=0,
                    max_score=1,
                    explanation=f"Evaluator error: {e}",
                    details={"error": str(e), "error_type": type(e).__name__},
                )
                hook.results.append(error_result)
                results.append((hook.criterion.id, error_result))

        return results

    async def _call_evaluator(
        self,
        evaluator: Callable[[EvalContext, dict], EvalResult],
        context: EvalContext,
        params: dict[str, Any],
    ) -> EvalResult:
        """Call an evaluator function, handling sync and async.

        Args:
            evaluator: The evaluator function.
            context: The test context.
            params: Parameters to pass to the evaluator.

        Returns:
            The EvalResult from the evaluator.
        """
        if inspect.iscoroutinefunction(evaluator):
            return await evaluator(context, params)
        else:
            # Run sync function in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: evaluator(context, params)
            )

    def get_accumulated_results(self) -> dict[str, list[EvalResult]]:
        """Get accumulated results for all hooks.

        Returns:
            Dictionary mapping criterion_id to list of EvalResults.
        """
        return {hook.criterion.id: list(hook.results) for hook in self._hooks}

    def get_hook_for_criterion(self, criterion_id: str) -> RegisteredHook | None:
        """Get the registered hook for a criterion.

        Args:
            criterion_id: The criterion ID to look up.

        Returns:
            The RegisteredHook, or None if not found.
        """
        for hook in self._hooks:
            if hook.criterion.id == criterion_id:
                return hook
        return None

    def clear_results(self) -> None:
        """Clear accumulated results from all hooks."""
        for hook in self._hooks:
            hook.results.clear()

    @property
    def hook_count(self) -> int:
        """Number of registered hooks."""
        return len(self._hooks)

    @property
    def registered_criterion_ids(self) -> list[str]:
        """List of criterion IDs with registered hooks."""
        return [hook.criterion.id for hook in self._hooks]
