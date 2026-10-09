"""Shared pytest fixtures for crew-engine tests.

The module-level :data:`trace` singleton accumulates events across tests;
reset it before every test so assertions about transcripts see only the
current test's run.
"""

import pytest

from crew_engine.trace import trace


@pytest.fixture(autouse=True)
def clean_trace():
    trace.reset()
    yield
    trace.reset()