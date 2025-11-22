"""Pytest configuration and shared fixtures."""

import pytest

# Import all fixtures from modality fixture modules
pytest_plugins = [
    "tests.fixtures.modalities.location",
    "tests.fixtures.modalities.time",
    "tests.fixtures.modalities.chat",
    "tests.fixtures.modalities.weather",
    "tests.fixtures.modalities.email",
    "tests.fixtures.modalities.calendar",
    "tests.fixtures.modalities.sms",
    "tests.fixtures.core.events",
    "tests.fixtures.core.queues",
    "tests.fixtures.core.environments",
]
