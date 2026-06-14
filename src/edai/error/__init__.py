"""
edai.error — Centralised error hierarchy for the entire project.

All public exceptions in edai inherit from :class:`EdaiError`, making it
possible to catch any library-specific error with a single ``except EdaiError``.

Hierarchy::

    EdaiError
    ├── AgentError
    │   ├── ConfigurationError
    │   ├── ModelError
    │   │   ├── ModelTimeoutError
    │   │   ├── ModelRateLimitError
    │   │   └── ModelContentFilterError
    │   └── ToolError
    │       ├── ToolNotFoundError
    │       ├── ToolExecutionError
    │       └── ToolInvalidParamError
    ├── BackendError
    │   ├── BackendNotRunningError
    │   └── BackendTimeoutError
    └── ConfigError
        ├── ConfigNotFoundError
        └── ConfigParseError
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


class EdaiError(Exception):
    """Base exception for all edai errors.

    Catch ``EdaiError`` to handle any library-specific exception without
    worrying about the concrete type.
    """


# ---------------------------------------------------------------------------
# Agent / LLM interaction
# ---------------------------------------------------------------------------


class AgentError(EdaiError):
    """Errors raised during LLM agent interaction."""


class ConfigurationError(AgentError):
    """Invalid or missing agent / client configuration.

    For example: no API key provided, unrecognised model name.
    """


class ModelError(AgentError):
    """Errors originating from the LLM model or API provider."""


class ModelTimeoutError(ModelError):
    """The model did not respond within the allotted time."""


class ModelRateLimitError(ModelError):
    """The API rate limit was exceeded."""


class ModelContentFilterError(ModelError):
    """The model response was blocked by a content safety filter."""


class ToolError(AgentError):
    """Errors related to tool / function calls made by the agent."""


class ToolNotFoundError(ToolError):
    """The agent requested a tool that has not been registered."""


class ToolExecutionError(ToolError):
    """A tool call completed with an execution error."""


class ToolInvalidParamError(ToolError):
    """The parameters supplied to a tool call are invalid."""


# ---------------------------------------------------------------------------
# Backend (subprocess)
# ---------------------------------------------------------------------------


class BackendError(EdaiError):
    """Errors from the interactive subprocess (:class:`~edai.backend.Backend`)."""


class BackendNotRunningError(BackendError):
    """An operation was attempted on a backend process that is not running."""


class BackendTimeoutError(BackendError):
    """A backend I/O operation timed out."""


# ---------------------------------------------------------------------------
# General configuration / file loading
# ---------------------------------------------------------------------------


class ConfigError(EdaiError):
    """Errors related to project or user configuration."""


class ConfigNotFoundError(ConfigError):
    """A required configuration file or directory was not found."""


class ConfigParseError(ConfigError):
    """A configuration file could not be parsed correctly."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "EdaiError",
    # Agent
    "AgentError",
    "ConfigurationError",
    "ModelError",
    "ModelTimeoutError",
    "ModelRateLimitError",
    "ModelContentFilterError",
    "ToolError",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolInvalidParamError",
    # Backend
    "BackendError",
    "BackendNotRunningError",
    "BackendTimeoutError",
    # Config
    "ConfigError",
    "ConfigNotFoundError",
    "ConfigParseError",
]
