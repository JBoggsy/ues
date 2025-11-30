"""
Pytest fixtures for workflow tests.

This module provides fixtures specific to workflow testing,
building on the existing API test fixtures.
"""

import pytest

from .runner import WorkflowRunner


@pytest.fixture
def workflow_runner(client_with_engine):
    """Create a WorkflowRunner instance for the test.

    This fixture provides a configured WorkflowRunner that uses
    the test client and fresh engine from the standard API test fixtures.

    Usage:
        def test_my_workflow(workflow_runner):
            runner = workflow_runner
            runner.run(MY_SCENARIO)
    """
    client, engine = client_with_engine
    return WorkflowRunner(client, engine, verbose=True)


@pytest.fixture
def quiet_workflow_runner(client_with_engine):
    """Create a quiet WorkflowRunner instance (no output).

    Useful for tests where you don't want verbose output.
    """
    client, engine = client_with_engine
    return WorkflowRunner(client, engine, verbose=False)
