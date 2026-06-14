"""
edai.tool — Callable tools that an LLM agent can invoke via OpenAI function calling.
"""

from __future__ import annotations

from edai.tool.base import Tool
from edai.tool.builtin import BashExec
from edai.tool.manager import ToolsMgr
from edai.tool.repl import ReplExec

__all__ = ["Tool", "ToolsMgr", "BashExec", "ReplExec"]
