"""
edai.tool.base — Abstract base class for agent-callable tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Abstract base for an agent-callable tool."""

    name: str = ""
    description: str = ""

    @abstractmethod
    def parameters_schema(self) -> dict[str, Any]:
        """Return JSON Schema object describing the tool's parameters.

        Must be a valid JSON Schema ``{"type": "object", "properties": {...}, "required": [...]}``.
        """
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the tool with the given keyword arguments and return a string result."""
        ...

    def to_openai_function(self) -> dict[str, Any]:
        """Return the OpenAI function-calling definition for this tool.

        Format:
        ``{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}``
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters_schema(),
            },
        }
