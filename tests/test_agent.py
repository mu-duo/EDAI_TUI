"""Tests for the base Agent class — runs against a real LLM API.

Requires ``LLM_API_KEY`` to be set via ``.env`` (loaded automatically by
``python-dotenv`` at import time), **and** ``EDAI_TEST_REAL_API=true``
in the same file.

Without both conditions the real-API fixtures are skipped and only mock-based
or logic-only tests execute.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from edai.agent import Agent, AgentConfig
from edai.error import AgentError, ConfigurationError

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _is_real_api_enabled() -> bool:
    """Check whether ``EDAI_TEST_REAL_API`` is explicitly set to a truthy value.

    Accepts ``true``, ``1``, ``yes`` (case-insensitive).  Anything else
    (including unset) means real-API tests are skipped.
    """
    return os.environ.get("EDAI_TEST_REAL_API", "").strip().lower() in ("true", "1", "yes")


def _load_api_key() -> str | None:
    """Read the LLM API key from the environment.

    ``python-dotenv`` has already loaded ``.env`` by this point via
    ``edai.agent.base``, so ``LLM_API_KEY`` should be available if the
    file exists.
    """
    return os.environ.get("LLM_API_KEY")


@pytest.fixture(scope="session")
def real_config() -> AgentConfig:
    """Build an ``AgentConfig`` from real credentials in ``.env``.

    Skipped unless **both** conditions hold:

    * ``EDAI_TEST_REAL_API=true`` (or ``1`` / ``yes``) is set, **and**
    * ``LLM_API_KEY`` is present (either in ``.env`` or the environment).

    This lets you toggle real-API tests on/off without touching test code.
    """
    if not _is_real_api_enabled():
        pytest.skip("EDAI_TEST_REAL_API not enabled — skipping real API tests")
    api_key = _load_api_key()
    if not api_key:
        pytest.skip("LLM_API_KEY not set — skipping real API tests")
    return AgentConfig(
        api_key=api_key,
        base_url=os.environ.get("LLM_BASE_URL"),
        model=os.environ.get("LLM_MODEL_ID", "deepseek-v4-flash"),
    )


@pytest.fixture(scope="session")
def real_agent(real_config: AgentConfig) -> Agent:
    """Return an ``Agent`` wired to the real API (session-scoped).

    Reuses the same agent across tests to avoid re-creating the HTTP
    client and to accumulate a conversation history where needed.
    """
    return Agent(real_config)


# ------------------------------------------------------------------
# Mock helpers (for edge cases unreachable with a real API)
# ------------------------------------------------------------------


def _make_completion(content: str | None) -> MagicMock:
    """Build a mock ``ChatCompletion`` with a single choice."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    return mock


def _make_stream_chunks(*chunks: str | None) -> list[MagicMock]:
    """Build mock ``ChatCompletionChunk`` objects for testing."""
    items: list[MagicMock] = []
    for text in chunks:
        chunk = MagicMock(spec=[])
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = text
        items.append(chunk)
    return items


# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------


class TestInit:
    """Agent instantiation and configuration."""

    def test_default_config(self, real_config: AgentConfig) -> None:
        """Created with real config, fields are propagated."""
        agent = Agent(real_config)
        assert agent.config.api_key == real_config.api_key
        assert agent.config.base_url == real_config.base_url
        assert agent.config.model == real_config.model
        assert agent.messages == []

    def test_system_prompt_is_first_message(self, real_config: AgentConfig) -> None:
        """System prompt is prepended to the message history."""
        config = AgentConfig(
            api_key=real_config.api_key,
            base_url=real_config.base_url,
            model=real_config.model,
            system_prompt="You are a test bot.",
        )
        agent = Agent(config)
        assert len(agent.messages) == 1
        assert agent.messages[0] == {
            "role": "system",
            "content": "You are a test bot.",
        }

    def test_no_api_key_raises(self) -> None:
        """``ConfigurationError`` when no API key is available."""
        with patch.dict(os.environ, {"LLM_API_KEY": ""}):
            with pytest.raises(ConfigurationError, match="No API key found"):
                Agent()

    def test_repr(self, real_config: AgentConfig) -> None:
        """``repr()`` includes the resolved model name."""
        agent = Agent(real_config)
        assert repr(agent) == f"Agent(model={real_config.model!r})"


# ------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------


class TestProperties:
    """Config and messages property behaviour."""

    def test_config_is_assigned_object(self, real_config: AgentConfig) -> None:
        """``config`` returns the same config object that was passed."""
        agent = Agent(real_config)
        assert agent.config is real_config

    def test_messages_returns_copy(self, real_config: AgentConfig) -> None:
        """``messages`` returns a new list each time (defensive copy)."""
        agent = Agent(real_config)
        msgs1 = agent.messages
        msgs2 = agent.messages
        assert msgs1 is not msgs2
        msgs1.append({"role": "user", "content": "injected"})
        assert len(agent.messages) == 0


# ------------------------------------------------------------------
# Non-streaming chat (real API)
# ------------------------------------------------------------------


class TestChat:
    """``chat()`` — synchronous full-response via the real API."""

    def test_appends_user_and_assistant(self, real_agent: Agent) -> None:
        """Two messages are added per call: user then assistant."""
        real_agent.reset()
        real_agent.chat("Say hello in one word.")
        assert len(real_agent.messages) == 2
        assert real_agent.messages[0] == {
            "role": "user",
            "content": "Say hello in one word.",
        }
        assert real_agent.messages[1]["role"] == "assistant"
        content = real_agent.messages[1].get("content")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_returns_content(self, real_agent: Agent) -> None:
        """``chat()`` returns the assistant message content as a string."""
        real_agent.reset()
        reply = real_agent.chat("Reply with just the word: hello")
        assert isinstance(reply, str)
        assert len(reply) > 0

    def test_preserves_history_across_calls(self, real_agent: Agent) -> None:
        """Multiple ``chat()`` calls accumulate in message history."""
        real_agent.reset()
        real_agent.chat("First message")
        real_agent.chat("Second message")
        assert len(real_agent.messages) == 4
        content = real_agent.messages[0].get("content")
        assert isinstance(content, str)
        assert content == "First message"
        assert real_agent.messages[1]["role"] == "assistant"
        content = real_agent.messages[2].get("content")
        assert isinstance(content, str)
        assert content == "Second message"
        assert real_agent.messages[3]["role"] == "assistant"

    def test_none_content_becomes_empty_string(self) -> None:
        """When the API returns ``None`` content, chat returns ``""``.

        (This edge case is tested with a mock since real APIs always
        return a string.)
        """
        with patch("edai.agent.base.OpenAI") as cls:
            client = MagicMock()
            cls.return_value = client
            client.chat.completions.create.return_value = _make_completion(None)
            agent = Agent(AgentConfig(api_key="sk-dummy"))
            reply = agent.chat("Say nothing")
        assert reply == ""


# ------------------------------------------------------------------
# Streaming chat (real API)
# ------------------------------------------------------------------


class TestChatStream:
    """``chat_stream()`` — streaming response via the real API."""

    def test_yields_real_chunks(self, real_agent: Agent) -> None:
        """Chunks are yielded as non-empty strings from the real API."""
        real_agent.reset()
        chunks = list(real_agent.chat_stream("Count to three."))
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, str)

    def test_stores_full_response(self, real_agent: Agent) -> None:
        """After iteration, the full concatenated response is stored."""
        real_agent.reset()
        chunks = list(real_agent.chat_stream("Say hello."))
        full = "".join(chunks)
        assert len(real_agent.messages) == 2
        assert real_agent.messages[1]["role"] == "assistant"
        content = real_agent.messages[1].get("content")
        assert isinstance(content, str)
        assert content == full

    def test_none_delta_skipped(self) -> None:
        """Chunks with ``None`` delta content are silently skipped.

        (Edge case tested with a mock.)
        """
        with patch("edai.agent.base.OpenAI") as cls:
            client = MagicMock()
            cls.return_value = client
            client.chat.completions.create.return_value = _make_stream_chunks("A", None, "B")
            agent = Agent(AgentConfig(api_key="sk-dummy"))
            result = list(agent.chat_stream("X"))
        assert result == ["A", "B"]

    def test_empty_stream(self) -> None:
        """An empty stream produces no chunks and stores an empty string."""
        with patch("edai.agent.base.OpenAI") as cls:
            client = MagicMock()
            cls.return_value = client
            client.chat.completions.create.return_value = []
            agent = Agent(AgentConfig(api_key="sk-dummy"))
            result = list(agent.chat_stream("Hi"))
        assert result == []
        assert agent.messages[-1] == {"role": "assistant", "content": ""}


# ------------------------------------------------------------------
# Reset
# ------------------------------------------------------------------


class TestReset:
    """``reset()`` — clearing message history."""

    def test_clears_messages(self, real_agent: Agent) -> None:
        """History is empty after reset when there is no system prompt."""
        real_agent.reset()
        # Manually push a stale message
        real_agent._messages.append({"role": "user", "content": "stale"})
        real_agent.reset()
        assert real_agent.messages == []

    def test_preserves_system_prompt(self, real_config: AgentConfig) -> None:
        """System prompt survives a reset."""
        config = AgentConfig(
            api_key=real_config.api_key,
            base_url=real_config.base_url,
            model=real_config.model,
            system_prompt="You are a bot.",
        )
        agent = Agent(config)
        agent._messages.append({"role": "user", "content": "stale"})
        agent.reset()
        assert len(agent.messages) == 1
        assert agent.messages[0] == {"role": "system", "content": "You are a bot."}

    def test_reset_twice_is_idempotent(self, real_agent: Agent) -> None:
        """Calling reset() multiple times is safe."""
        real_agent.reset()
        real_agent.reset()
        assert real_agent.messages == []


# ------------------------------------------------------------------
# Re-exported error types
# ------------------------------------------------------------------


class TestErrors:
    """Agent module re-exports the relevant error classes."""

    def test_agent_error_is_exported(self) -> None:
        """``AgentError`` is accessible from ``edai.agent``."""
        from edai.agent import AgentError as AgentErrorReexport

        assert AgentErrorReexport is AgentError

    def test_configuration_error_is_exported(self) -> None:
        """``ConfigurationError`` is accessible from ``edai.agent``."""
        from edai.agent import ConfigurationError as ConfigurationErrorReexport

        assert ConfigurationErrorReexport is ConfigurationError
