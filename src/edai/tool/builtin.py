"""
edai.tool.builtin — Built-in tools shipped with the edai package.
"""

from __future__ import annotations

import subprocess
from typing import Any

from edai.tool.base import Tool


class BashExec(Tool):
    name = "bash_exec"
    description = "Execute a bash shell command and return its output."

    def parameters_schema(self) -> dict[str, Any]:
        """Return JSON Schema describing the bash_exec parameters."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute.",
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory for the command (optional).",
                },
                "timeout": {
                    "type": "number",
                    "description": (
                        "Maximum execution time in seconds (default 30, -1 for no timeout)."
                    ),
                },
            },
            "required": ["command"],
        }

    def execute(  # type: ignore[override]
        self,
        command: str,
        workdir: str | None = None,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a bash command and return its output.

        Parameters
        ----------
        command:
            The bash command to execute.
        workdir:
            Optional working directory for the command.
        timeout:
            Maximum execution time in seconds (default 30, and -1 for no timeout).

        Returns
        -------
        dict[str, Any]
            Formatted output containing stdout, stderr, and return code.
        """
        if not command or not command.strip():
            return {"error": "no command provided"}

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workdir,
            )
        except subprocess.TimeoutExpired:
            return {"error": f"command timed out after {timeout}s"}

        stdout = result.stdout
        stderr = result.stderr if result.stderr else ""
        return {
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
