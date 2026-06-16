"""
edai.agent — Agent abstraction layer for LLM interaction.

Provides the base :class:`Agent` class that wraps the OpenAI-compatible chat
completion API.  Higher-level agents inherit from this primitive.
"""

from edai.agent.base import Agent, AgentConfig
from edai.agent.context import Context
from edai.error import AgentError, ConfigurationError

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentError",
    "ConfigurationError",
    "Context",
]
