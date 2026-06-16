"""Base agent — LLM interaction primitive.

Wraps the OpenAI Python client for chat completions with support for
synchronous and streaming responses, message history management, and
environment-based configuration via ``python-dotenv``.

Environment variables consulted (in order of precedence — explicit config
wins over env var, env var wins over hard-coded default):

* ``LLM_API_KEY`` — API key (required)
* ``LLM_BASE_URL`` — API base URL (optional; defaults to OpenAI)
* ``LLM_MODEL_ID`` — Model identifier (default: ``deepseek-v4-flash``)
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from edai.agent.context import Context
from edai.error import AgentError, ConfigurationError  # noqa: F401 — re-exported

# Load .env file once at import time so all consumers inherit the env.
load_dotenv()


def _default_model() -> str:
    return os.environ.get("LLM_MODEL_ID", "deepseek-v4-flash")


@dataclass
class AgentConfig:
    """Configuration for an :class:`Agent` instance."""

    api_key: str | None = None
    """LLM API key (fallback: ``LLM_API_KEY``)."""

    base_url: str | None = None
    """API base URL (fallback: ``LLM_BASE_URL``)."""

    model: str = field(default_factory=_default_model)
    """Model identifier (fallback: ``LLM_MODEL_ID`` or ``"deepseek-v4-flash"``)."""

    system_prompt: str | None = None
    """Optional system-level instruction prepended to every conversation."""

    max_tokens: int | None = None
    """Maximum tokens in the response (``None`` = model default)."""

    temperature: float | None = None
    """Sampling temperature (``None`` = model default)."""


class Agent:
    """Base agent for LLM interaction via the OpenAI-compatible API.

    Can be used directly as a simple stateless chatbot, or subclassed to
    build higher-level agents with specialised behaviour.

    Usage::

        agent = Agent(model="gpt-4o")
        reply = agent.chat("Hello!")
        print(reply)

        # Streaming
        for chunk in agent.chat_stream("Tell me a story"):
            print(chunk, end="", flush=True)

    Message history is preserved between calls so the model sees the full
    conversation context.  Call :meth:`reset` to clear the history.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        context: Context | None = None,
    ) -> None:
        self._config = config or AgentConfig()
        self._context = context if context is not None else Context()
        self._client = self._build_client()
        self._init_system_prompt()

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> AgentConfig:
        """Read-only config that this agent was created with."""
        return self._config

    @property
    def context(self) -> Context:
        """The conversation message history.

        Returns the :class:`Context` instance directly.  Use
        ``list(agent.context)`` if a plain list is needed.
        """
        return self._context

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, message: str, **kwargs: Any) -> str:
        """Send a user message and return the full assistant response.

        Args:
            message: The user's input text.
            **kwargs: Additional parameters forwarded to the OpenAI
                chat completion call (e.g. ``max_tokens``, ``temperature``).

        Returns:
            The assistant's response content.
        """
        self._context.append({"role": "user", "content": message})

        completion = self._client.chat.completions.create(
            model=self._resolve_model(),
            messages=list(self._context),
            **kwargs,
        )
        content = completion.choices[0].message.content or ""
        self._context.append({"role": "assistant", "content": content})
        return content

    def chat_stream(self, message: str, **kwargs: Any) -> Iterator[str]:
        """Send a user message and yield response chunks as they arrive.

        The full response is still stored in the message history after
        iteration completes.

        Args:
            message: The user's input text.
            **kwargs: Additional parameters forwarded to the OpenAI
                chat completion call.

        Yields:
            Content delta strings as they arrive from the API.
        """
        self._context.append({"role": "user", "content": message})

        stream = self._client.chat.completions.create(
            model=self._resolve_model(),
            messages=list(self._context),
            stream=True,
            **kwargs,
        )

        collected: list[str] = []
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                collected.append(delta)
                yield delta

        self._context.append({"role": "assistant", "content": "".join(collected)})

    def reset(self) -> None:
        """Clear all message history.

        The system prompt (if any) is re-inserted so the next conversation
        starts fresh with the same instructions.
        """
        self._context.clear()
        self._init_system_prompt()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_client(self) -> OpenAI:
        api_key = self._config.api_key or os.environ.get("LLM_API_KEY")
        if not api_key:
            raise ConfigurationError(
                "No API key found. Set LLM_API_KEY (or pass api_key to AgentConfig)."
            )
        return OpenAI(
            api_key=api_key,
            base_url=self._config.base_url or os.environ.get("LLM_BASE_URL"),
        )

    def _resolve_model(self) -> str:
        return self._config.model

    def _init_system_prompt(self) -> None:
        if self._config.system_prompt:
            self._context.append({"role": "system", "content": self._config.system_prompt})

    def __repr__(self) -> str:
        return f"Agent(model={self._resolve_model()!r}, messages={len(self._context)})"
