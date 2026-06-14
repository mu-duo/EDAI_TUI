"""Tests for edai.tool.repl — ReplExec tool for interactive binary REPLs."""

from __future__ import annotations

import sys
from collections.abc import Generator

import pytest

from edai.tool.repl import ReplExec

# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def repl() -> Generator[ReplExec, None, None]:
    """Start a Python REPL and yield the ReplExec instance (cleans up after).

    Each test gets a fresh REPL. The teardown stops the process if it is
    still running (no-op if the test already stopped it).
    """
    tool = ReplExec()
    result = tool.execute(
        action="start",
        command=sys.executable,
        args=["-i", "-q"],
        timeout=5.0,
    )
    assert result["status"] == "started"
    yield tool
    # Teardown — stop if still running (harmless if already stopped)
    tool.execute(action="stop", timeout=5.0)


# ======================================================================
# TestReplExecLifecycle
# ======================================================================


class TestReplExecLifecycle:
    """Tests the start → eval → stop lifecycle with a real python process."""

    def test_start_python(self) -> None:
        """Starting a Python REPL returns status 'started' with output and stderr strings."""
        tool = ReplExec()
        result = tool.execute(
            action="start",
            command=sys.executable,
            args=["-i", "-q"],
            timeout=5.0,
        )
        assert result["status"] == "started"
        assert isinstance(result["output"], str)
        assert isinstance(result["stderr"], str)
        # Clean up
        tool.execute(action="stop", timeout=5.0)

    def test_eval_simple(self, repl: ReplExec) -> None:
        """Eval'ing print('hello') returns output containing 'hello'."""
        result = repl.execute(action="eval", input='print("hello")', timeout=5.0)
        assert "hello" in result["output"]
        assert result["returncode"] is None

    def test_eval_expression(self, repl: ReplExec) -> None:
        """Eval'ing '1 + 1' returns output containing '2'."""
        result = repl.execute(action="eval", input="1 + 1", timeout=5.0)
        assert "2" in result["output"]
        assert result["returncode"] is None

    def test_eval_stderr(self, repl: ReplExec) -> None:
        """Eval'ing something that writes to stderr captures it in 'stderr' key."""
        result = repl.execute(
            action="eval",
            input='import sys; print("error!", file=sys.stderr)',
            timeout=5.0,
        )
        assert "error!" in result.get("stderr", "")

    def test_stop(self) -> None:
        """Stopping a running REPL returns status 'stopped' with a returncode."""
        tool = ReplExec()
        tool.execute(
            action="start",
            command=sys.executable,
            args=["-i", "-q"],
            timeout=5.0,
        )
        result = tool.execute(action="stop", timeout=5.0)
        assert result["status"] == "stopped"
        assert result["returncode"] is not None

    def test_full_lifecycle(self) -> None:
        """Starting, eval'ing twice, and stopping all succeed in sequence."""
        tool = ReplExec()

        start_result = tool.execute(
            action="start",
            command=sys.executable,
            args=["-i", "-q"],
            timeout=5.0,
        )
        assert start_result["status"] == "started"

        eval1 = tool.execute(action="eval", input='print("first")', timeout=5.0)
        assert "first" in eval1["output"]

        eval2 = tool.execute(action="eval", input='print("second")', timeout=5.0)
        assert "second" in eval2["output"]

        stop_result = tool.execute(action="stop", timeout=5.0)
        assert stop_result["status"] == "stopped"
        assert stop_result["returncode"] is not None


# ======================================================================
# TestReplExecErrors
# ======================================================================


class TestReplExecErrors:
    """Tests error conditions for ReplExec."""

    def test_eval_before_start(self) -> None:
        """Eval without calling start first returns an error."""
        tool = ReplExec()
        result = tool.execute(action="eval", input="hello", timeout=5.0)
        assert result == {"error": "not running — start first"}

    def test_stop_before_start(self) -> None:
        """Stop without calling start first returns status 'already stopped'."""
        tool = ReplExec()
        result = tool.execute(action="stop", timeout=5.0)
        assert result == {"status": "already stopped"}

    def test_double_start(self) -> None:
        """Calling start twice without stopping returns an error."""
        tool = ReplExec()
        tool.execute(
            action="start",
            command=sys.executable,
            args=["-i", "-q"],
            timeout=5.0,
        )
        try:
            result = tool.execute(
                action="start",
                command=sys.executable,
                args=["-i", "-q"],
                timeout=5.0,
            )
            assert result == {"error": "already running — stop first"}
        finally:
            tool.execute(action="stop", timeout=5.0)

    def test_eval_after_stop(self) -> None:
        """Eval after stop returns an error."""
        tool = ReplExec()
        tool.execute(
            action="start",
            command=sys.executable,
            args=["-i", "-q"],
            timeout=5.0,
        )
        tool.execute(action="stop", timeout=5.0)
        result = tool.execute(action="eval", input="hello", timeout=5.0)
        assert result == {"error": "not running — start first"}

    def test_unknown_action(self) -> None:
        """An unknown action returns an appropriate error dict."""
        tool = ReplExec()
        result = tool.execute(action="invalid")
        assert result == {"error": "unknown action: invalid"}

    def test_start_nonexistent_binary(self) -> None:
        """Starting a nonexistent binary returns an error."""
        tool = ReplExec()
        result = tool.execute(action="start", command="nonexistent_cmd_xyz", timeout=5.0)
        assert "error" in result
        # The error message should indicate the command was not found
        assert "not found" in result["error"].lower()


# ======================================================================
# TestReplExecSchema
# ======================================================================


class TestReplExecSchema:
    """Tests the OpenAI function-calling integration for ReplExec."""

    def test_name_and_description(self) -> None:
        """The tool has the expected name and a non-empty description."""
        tool = ReplExec()
        assert tool.name == "repl_exec"
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0
        assert "repl" in tool.description.lower()

    def test_parameters_schema(self) -> None:
        """parameters_schema() returns valid JSON Schema with action as sole required field."""
        tool = ReplExec()
        schema = tool.parameters_schema()
        assert isinstance(schema, dict)
        assert schema["type"] == "object"
        props = schema["properties"]
        assert "action" in props
        assert props["action"]["type"] == "string"
        assert "enum" in props["action"]
        assert props["action"]["enum"] == ["start", "eval", "stop"]
        assert "command" in props
        assert props["command"]["type"] == "string"
        assert "args" in props
        assert props["args"]["type"] == "array"
        assert "input" in props
        assert props["input"]["type"] == "string"
        assert "timeout" in props
        assert props["timeout"]["type"] == "number"
        assert schema["required"] == ["action"]

    def test_to_openai_function(self) -> None:
        """to_openai_function() returns the correct OpenAI function-calling format."""
        tool = ReplExec()
        func = tool.to_openai_function()
        assert func == {
            "type": "function",
            "function": {
                "name": "repl_exec",
                "description": tool.description,
                "parameters": tool.parameters_schema(),
            },
        }
