"""
edai.tool — Callable tools that an LLM agent can invoke via OpenAI function calling.
"""

from __future__ import annotations

from edai.tool.backend import Backend, BackendError, BackendNotRunningError
from edai.tool.base import Tool
from edai.tool.builtin import BashExec
from edai.tool.interpreter import Interpreter
from edai.tool.manager import ToolsMgr
from edai.tool.repl import ReplExec

__all__ = [
    "Backend",
    "BackendError",
    "BackendNotRunningError",
    "Tool",
    "ToolsMgr",
    "BashExec",
    "Interpreter",
    "ReplExec",
]
