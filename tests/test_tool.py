"""Tests for edai.tool — Tool ABC, ToolsMgr, and built-in BashExec tool."""

from __future__ import annotations

from typing import Any

import pytest

from edai.error import ToolExecutionError, ToolNotFoundError
from edai.tool import BashExec, Tool, ToolsMgr

# ======================================================================
# TestToolABC
# ======================================================================


class TestToolABC:
    """Abstract base class behaviours, verified via a concrete BashExec instance."""

    def test_name_and_description(self) -> None:
        """BashExec has the expected name and description class-level attributes."""
        tool = BashExec()
        assert tool.name == "bash_exec"
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0
        assert "bash" in tool.description.lower()

    def test_parameters_schema(self) -> None:
        """parameters_schema() returns a valid JSON Schema dict."""
        tool = BashExec()
        schema = tool.parameters_schema()
        assert isinstance(schema, dict)
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "command" in schema["properties"]
        assert "command" in schema["required"]
        assert schema["required"] == ["command"]

    def test_to_openai_function(self) -> None:
        """to_openai_function() returns the correct OpenAI function-calling format."""
        tool = BashExec()
        func = tool.to_openai_function()
        assert func == {
            "type": "function",
            "function": {
                "name": "bash_exec",
                "description": tool.description,
                "parameters": tool.parameters_schema(),
            },
        }

    def test_cannot_instantiate(self) -> None:
        """Tool() cannot be instantiated directly (abstract methods)."""
        with pytest.raises(TypeError):
            Tool()  # type: ignore[abstract]


# ======================================================================
# TestToolsMgr
# ======================================================================


class TestToolsMgr:
    """ToolsMgr registry — registration, lookup, dispatch, and dunder methods."""

    # ------------------------------------------------------------------
    # Registration & lookup
    # ------------------------------------------------------------------

    def test_register_and_lookup(self) -> None:
        """Register a tool and look it up, asserting it is the same instance."""
        mgr = ToolsMgr()
        tool = BashExec()
        mgr.register(tool)
        retrieved = mgr.lookup("bash_exec")
        assert retrieved is tool

    def test_register_duplicate_raises(self) -> None:
        """Registering the same tool name twice raises ValueError."""
        mgr = ToolsMgr()
        mgr.register(BashExec())
        with pytest.raises(ValueError, match="already registered"):
            mgr.register(BashExec())

    def test_unregister(self) -> None:
        """Unregister removes a tool; subsequent lookup raises ToolNotFoundError."""
        mgr = ToolsMgr()
        mgr.register(BashExec())
        mgr.unregister("bash_exec")
        with pytest.raises(ToolNotFoundError):
            mgr.lookup("bash_exec")

    def test_unregister_nonexistent_noop(self) -> None:
        """Unregistering a nonexistent tool is a silent no-op."""
        mgr = ToolsMgr()
        mgr.unregister("i_do_not_exist")  # should not raise

    def test_lookup_nonexistent_raises(self) -> None:
        """Lookup of an unknown tool raises ToolNotFoundError with an informative message."""
        mgr = ToolsMgr()
        with pytest.raises(ToolNotFoundError, match="not found"):
            mgr.lookup("nonexistent_tool")

    # ------------------------------------------------------------------
    # Listing and schemas
    # ------------------------------------------------------------------

    def test_list_tools(self) -> None:
        """list_tools() returns a sorted list of registered tool names."""
        mgr = ToolsMgr()
        assert mgr.list_tools() == []

        mgr.register(BashExec())
        assert mgr.list_tools() == ["bash_exec"]

    def test_list_tools_sorted(self) -> None:
        """list_tools() returns names in alphabetical order."""
        mgr = ToolsMgr()

        # Create two minimal tools with out-of-order names
        class ATool(Tool):
            name = "alpha"
            description = ""

            def parameters_schema(self) -> dict[str, Any]:
                return {"type": "object", "properties": {}, "required": []}

            def execute(self, **kwargs: Any) -> dict[str, Any]:
                return {}

        class ZTool(Tool):
            name = "zeta"
            description = ""

            def parameters_schema(self) -> dict[str, Any]:
                return {"type": "object", "properties": {}, "required": []}

            def execute(self, **kwargs: Any) -> dict[str, Any]:
                return {}

        mgr.register(ZTool())
        mgr.register(ATool())
        assert mgr.list_tools() == ["alpha", "zeta"]

    def test_get_schemas(self) -> None:
        """get_schemas() returns OpenAI function-calling schemas for all registered tools."""
        mgr = ToolsMgr()
        assert mgr.get_schemas() == []

        mgr.register(BashExec())
        schemas = mgr.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "bash_exec"

    # ------------------------------------------------------------------
    # Dispatch (execute)
    # ------------------------------------------------------------------

    def test_execute_dispatches(self) -> None:
        """mgr.execute() dispatches to the correct tool and returns its output."""
        mgr = ToolsMgr()
        mgr.register(BashExec())
        result = mgr.execute("bash_exec", {"command": "echo hello"})
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]

    def test_execute_nonexistent_raises(self) -> None:
        """mgr.execute() with an unknown tool name raises ToolNotFoundError."""
        mgr = ToolsMgr()
        with pytest.raises(ToolNotFoundError, match="not found"):
            mgr.execute("nonexistent", {})

    def test_execute_raises_execution_error(self) -> None:
        """mgr.execute() wraps tool execution exceptions in ToolExecutionError with chain."""
        mgr = ToolsMgr()

        class FailingTool(Tool):
            name = "failing"
            description = "A tool that always fails"

            def parameters_schema(self) -> dict[str, Any]:
                return {"type": "object", "properties": {}, "required": []}

            def execute(self, **kwargs: Any) -> dict[str, Any]:
                raise RuntimeError("boom")

        mgr.register(FailingTool())

        with pytest.raises(ToolExecutionError) as exc_info:
            mgr.execute("failing", {})

        assert "failing" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert str(exc_info.value.__cause__) == "boom"

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def test_len(self) -> None:
        """len(mgr) returns the number of registered tools."""
        mgr = ToolsMgr()
        assert len(mgr) == 0
        mgr.register(BashExec())
        assert len(mgr) == 1

    def test_contains(self) -> None:
        """'name in mgr' reflects whether a tool is registered."""
        mgr = ToolsMgr()
        assert "bash_exec" not in mgr
        mgr.register(BashExec())
        assert "bash_exec" in mgr
        assert "nonexistent" not in mgr

    def test_iter(self) -> None:
        """Iterating over mgr yields registered tool names."""
        mgr = ToolsMgr()
        mgr.register(BashExec())
        names = list(mgr)
        assert names == ["bash_exec"]

    def test_iter_empty(self) -> None:
        """Iterating over an empty mgr yields nothing."""
        mgr = ToolsMgr()
        assert list(mgr) == []

    def test_repr(self) -> None:
        """repr(mgr) includes the tool count."""
        mgr = ToolsMgr()
        assert repr(mgr) == "ToolsMgr(tools=0)"
        mgr.register(BashExec())
        assert repr(mgr) == "ToolsMgr(tools=1)"


# ======================================================================
# TestBashExec
# ======================================================================


class TestBashExec:
    """Built-in BashExec tool — command execution, formatting, and edge cases."""

    # ------------------------------------------------------------------
    # Basic execution
    # ------------------------------------------------------------------

    def test_echo_hello(self) -> None:
        """A simple echo command returns stdout with the expected text and returncode 0."""
        tool = BashExec()
        result = tool.execute(command="echo hello")
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]

    def test_returncode_nonzero(self) -> None:
        """A command that exits with code 1 reports returncode 1 and has empty stderr."""
        tool = BashExec()
        result = tool.execute(command="exit 1")
        print("Result:", result)
        assert result["returncode"] == 1
        assert result["stderr"] == ""

    def test_command_not_found(self) -> None:
        """A nonexistent command returns returncode 127 with an error in stderr."""
        tool = BashExec()
        result = tool.execute(command="nonexistent_command_xyz")
        assert result["returncode"] == 127
        # The shell writes an error message to stderr
        assert "not found" in result["stderr"].lower() or "error" in result["stderr"].lower()

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_empty_command(self) -> None:
        """An empty command returns the no-command-provided error string."""
        tool = BashExec()
        result = tool.execute(command="")
        assert result == {"error": "no command provided"}

    def test_whitespace_only_command(self) -> None:
        """A whitespace-only command also returns the no-command-provided error."""
        tool = BashExec()
        result = tool.execute(command="   ")
        assert result == {"error": "no command provided"}

    def test_stdout_and_stderr_both(self) -> None:
        """Both stdout and stderr are captured when a command writes to both."""
        tool = BashExec()
        result = tool.execute(command="echo out && echo err >&2")
        assert result["returncode"] == 0
        assert "out" in result["stdout"]
        assert "err" in result["stderr"]

    # ------------------------------------------------------------------
    # Timeout
    # ------------------------------------------------------------------

    def test_timeout(self) -> None:
        """A command that exceeds the timeout returns the timeout error string."""
        tool = BashExec()
        result = tool.execute(command="sleep 10", timeout=0.5)
        assert result == {"error": "command timed out after 0.5s"}

    def test_timeout_with_long_duration(self) -> None:
        """Timeout parameter controls how long to wait before killing the subprocess."""
        tool = BashExec()
        # A very short timeout on a command that would take much longer
        result = tool.execute(command="sleep 5", timeout=0.3)
        assert "timed out" in result["error"]
        assert "0.3" in result["error"]

    # ------------------------------------------------------------------
    # Working directory
    # ------------------------------------------------------------------

    def test_workdir(self) -> None:
        """When workdir is provided, the command runs in that directory."""
        tool = BashExec()
        result = tool.execute(command="pwd", workdir="/tmp")
        assert result["returncode"] == 0
        assert "/tmp" in result["stdout"]

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def test_parameters_schema_structure(self) -> None:
        """The BashExec parameters schema has the expected structure."""
        tool = BashExec()
        schema = tool.parameters_schema()

        assert schema["type"] == "object"
        props = schema["properties"]
        assert "command" in props
        assert props["command"]["type"] == "string"
        assert "workdir" in props
        assert props["workdir"]["type"] == "string"
        assert "timeout" in props
        assert props["timeout"]["type"] == "number"
        assert schema["required"] == ["command"]

    # ------------------------------------------------------------------
    # Extra kwargs
    # ------------------------------------------------------------------

    def test_execute_accepts_extra_kwargs(self) -> None:
        """Extra keyword arguments are silently accepted via **kwargs."""
        tool = BashExec()
        result = tool.execute(
            command="echo hello",
            workdir=None,
            timeout=5.0,
            extra_arg1="value1",
            extra_arg2=42,
        )
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]
