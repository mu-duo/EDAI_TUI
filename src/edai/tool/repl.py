"""
edai.tool.repl — Tool for interacting with a binary tool in a REPL-like manner.
"""

from __future__ import annotations

from typing import Any

from edai.backend import Backend
from edai.error import BackendError
from edai.tool.base import Tool


class ReplExec(Tool):
    name = "repl_exec"
    description = (
        "Interact with a binary tool in a REPL-like manner (e.g. Python interpreter). "
        "Use 'start' to launch the binary, 'eval' to send input and read output, "
        "'stop' to shut down."
    )

    def __init__(self) -> None:
        """Initialize the REPL tool with no running backend."""
        self._backend: Backend | None = None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def parameters_schema(self) -> dict[str, Any]:
        """Return JSON Schema describing the repl_exec parameters."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "eval", "stop"],
                    "description": (
                        "Action to perform: start launches the binary, "
                        "eval sends input and reads output, stop shuts down."
                    ),
                },
                "command": {
                    "type": "string",
                    "description": "For 'start': the binary to run (e.g., 'python').",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Extra arguments for 'start' (e.g., ['-i', '-q']).",
                },
                "input": {
                    "type": "string",
                    "description": "For 'eval': input to send to the process.",
                },
                "timeout": {
                    "type": "number",
                    "description": ("Timeout for reading output in seconds (default 10, 5 for stop)."),
                },
            },
            "required": ["action"],
        }

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(  # type: ignore[override]
        self,
        action: str,
        command: str = "",
        args: list[str] | None = None,
        input: str = "",
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a REPL action.

        Parameters
        ----------
        action:
            One of "start", "eval", or "stop".
        command:
            For 'start': the binary to run.
        args:
            For 'start': extra arguments for the binary.
        input:
            For 'eval': input to send to the process.
        timeout:
            Timeout for reading output in seconds.

        Returns
        -------
        dict[str, Any]
            Action-specific result dictionary.
        """
        if action == "start":
            return self._start(command, args or [], timeout)
        elif action == "eval":
            return self._eval(input, timeout)
        elif action == "stop":
            return self._stop(timeout)
        else:
            return {"error": f"unknown action: {action}"}

    # ------------------------------------------------------------------
    # Internal action handlers
    # ------------------------------------------------------------------

    def _start(self, command: str, args: list[str], timeout: float) -> dict[str, Any]:
        """Launch the binary REPL process."""
        if self._backend is not None and self._backend.is_running:
            return {"error": "already running — stop first"}

        try:
            backend = Backend([command, *args])
            backend.start()
        except BackendError as exc:
            return {"error": str(exc)}

        # Read initial output (e.g. banner, prompt)
        output = ""
        try:
            output = backend.read_output(timeout=timeout)
        except TimeoutError:
            pass

        stderr = backend.flush_error()
        self._backend = backend

        return {"status": "started", "output": output, "stderr": stderr}

    def _eval(self, input: str, timeout: float) -> dict[str, Any]:
        """Send input to the REPL and read the response."""
        backend = self._backend
        if backend is None or not backend.is_running:
            return {"error": "not running — start first"}

        backend.sendline(input)

        output = ""
        try:
            output = backend.read_output(timeout=timeout)
        except TimeoutError:
            pass

        stderr = backend.flush_error()

        result: dict[str, Any] = {
            "output": output,
            "stderr": stderr,
            "returncode": None,
        }

        if not backend.is_running:
            result["returncode"] = backend.returncode

        return result

    def _stop(self, timeout: float) -> dict[str, Any]:
        """Stop the REPL process."""
        backend = self._backend
        if backend is None or not backend.is_running:
            return {"status": "already stopped"}

        returncode = backend.close(timeout=timeout)
        self._backend = None

        return {"status": "stopped", "returncode": returncode}
