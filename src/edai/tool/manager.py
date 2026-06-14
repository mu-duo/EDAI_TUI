"""
edai.tool.manager — Registry for agent-callable tools.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from edai.error import ToolExecutionError, ToolInvalidParamError, ToolNotFoundError
from edai.tool.base import Tool


class ToolsMgr:
    """Registry for agent-callable tools.

    Manages registration, schema generation (for OpenAI function calling),
    and dispatching of tool calls.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Raises ValueError if a tool with the same name already exists.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool by name. Does nothing if the tool doesn't exist."""
        self._tools.pop(name, None)

    def lookup(self, name: str) -> Tool:
        """Return the tool with the given name.

        Raises ToolNotFoundError if the tool is not registered.
        """
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(f"Tool '{name}' not found")

    def list_tools(self) -> list[str]:
        """Return a sorted list of registered tool names."""
        return sorted(self._tools)

    def get_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI function-calling schemas for all registered tools."""
        return [tool.to_openai_function() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a registered tool by name with the given arguments.

        Raises ToolNotFoundError if the tool is not registered.
        Raises ToolInvalidParamError if validate=True and parameters fail validation.
        Raises ToolExecutionError if the tool's execute() raises an exception.
        """
        tool = self.lookup(name)

        try:
            return tool.execute(**arguments)
        except ToolInvalidParamError:
            raise
        except ToolNotFoundError:
            raise
        except Exception as exc:
            raise ToolExecutionError(f"Execution of tool '{name}' failed: {exc}") from exc

    def __len__(self) -> int:
        """Number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools

    def __iter__(self) -> Iterator[str]:
        """Iterate over registered tool names."""
        return iter(self._tools)

    def __repr__(self) -> str:
        """Return a string representation of the registry."""
        return f"ToolsMgr(tools={len(self._tools)})"
