"""Shared fixtures and configuration for edai tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_args() -> list[str]:
    """Return a list of sample CLI arguments."""
    return ["--help"]
