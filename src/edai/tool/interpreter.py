"""
edai.tool.interpreter — Tool for persistent interaction with named interpreters (python, tcl, …).
"""

from __future__ import annotations

import sys
from typing import Any

from edai.error import BackendError
from edai.tool.backend import Backend
from edai.tool.base import Tool

# Known interpreter configurations: name → (command_path, default_args)
_KNOWN: dict[str, tuple[str, list[str]]] = {
    "python": (sys.executable or "python", ["-i", "-q"]),
    "tcl": ("tclsh", []),
}


class Interpreter(Tool):
    """Persistent interpreter tool backed by :class:`~edai.tool.backend.Backend`.

    Supports named interpreters (``python``, ``tcl``) as well as arbitrary
    custom commands.  Lifecycle: ``start`` → ``input`` (repeat) → ``stop``.
    """

    name = "interpreter"
    description = (
        "Start and interact with a persistent interpreter process "
        "(e.g. python, tcl). Use 'start' to launch, 'input' to send text, "
        "'stop' to shut down."
    )

    def __init__(self) -> None:
        self._backend: Backend | None = None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def parameters_schema(self) -> dict[str, Any]:
        """Return JSON Schema describing the interpreter parameters."""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "input", "stop"],
                    "description": (
                        "Action to perform: start launches the interpreter, "
                        "input sends text, stop shuts down."
                    ),
                },
                "interpreter": {
                    "type": "string",
                    "description": (
                        "For 'start': name of a known interpreter ('python', 'tcl') "
                        "or a path / name of a custom command."
                    ),
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "For 'start': extra arguments appended to the default "
                        "interpreter args (e.g. ['-c', 'import sys'])."
                    ),
                },
                "input_text": {
                    "type": "string",
                    "description": "For 'input': text to send to the interpreter.",
                },
                "timeout": {
                    "type": "number",
                    "description": "Timeout for reading output in seconds (default 10).",
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
        interpreter: str = "",
        args: list[str] | None = None,
        input_text: str = "",
        timeout: float = 10.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute a lifecycle action on the interpreter.

        Parameters
        ----------
        action:
            One of ``"start"``, ``"input"``, ``"stop"``.
        interpreter:
            For ``"start"``: interpreter name or custom command path.
        args:
            For ``"start"``: extra CLI arguments (appended to defaults).
        input_text:
            For ``"input"``: text string to send to the interpreter.
        timeout:
            Read-output timeout in seconds.

        Returns
        -------
        dict[str, Any]
            Action-specific result.
        """
        if action == "start":
            return self._start(interpreter, list(args or []), timeout)
        elif action == "input":
            return self._send(input_text, timeout)
        elif action == "stop":
            return self._stop(timeout)
        else:
            return {"error": f"unknown action: {action}"}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _start(self, interpreter: str, args: list[str], timeout: float) -> dict[str, Any]:
        """Resolve the interpreter name and launch the backend process."""
        if self._backend is not None and self._backend.is_running:
            return {"error": "interpreter already running — stop first"}

        command, default_args = _resolve(interpreter)
        argv = [command, *default_args, *args]

        try:
            backend = Backend(argv)
            backend.start()
        except BackendError as exc:
            return {"error": f"failed to start interpreter: {exc}"}

        # Read initial output (banner, first prompt, …)
        output = ""
        try:
            output = backend.read_output(timeout=timeout)
        except TimeoutError:
            pass

        stderr = backend.flush_error()
        self._backend = backend

        return {"status": "started", "interpreter": command, "output": output, "stderr": stderr}

    def _send(self, input_text: str, timeout: float) -> dict[str, Any]:
        """Send input to the running interpreter and read the response."""
        backend = self._backend
        if backend is None or not backend.is_running:
            return {"error": "interpreter not running — start first"}

        backend.sendline(input_text)

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
        """Stop the interpreter process."""
        backend = self._backend
        if backend is None or not backend.is_running:
            return {"status": "already stopped"}

        returncode = backend.close(timeout=timeout)
        self._backend = None

        return {"status": "stopped", "returncode": returncode}


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _resolve(name: str) -> tuple[str, list[str]]:
    """Resolve an interpreter name to (command, default_args).

    Returns ``(name, [])`` for unknown names so they can be used as
    a custom command path.
    """
    if not name:
        return ("python", list(_KNOWN["python"][1]))
    cfg = _KNOWN.get(name)
    if cfg is not None:
        return cfg[0], list(cfg[1])
    return name, []
