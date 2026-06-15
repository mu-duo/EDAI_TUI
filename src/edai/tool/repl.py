"""
edai.tool.repl — Tool for interacting with a binary tool in a REPL-like manner.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol

from edai.error import BackendError
from edai.tool.base import Tool

if TYPE_CHECKING:
    pass


class ReplExec(Tool):
    name = "repl_exec"
    description = (
        "Interact with a binary tool in a REPL-like manner (e.g. Python interpreter). "
        "Use 'start' to launch the binary, 'eval' to send input and read output, "
        "'stop' to shut down."
    )

    def __init__(
        self,
        backend_factory: Callable[[list[str]], ReplBackendProtocol] | None = None,
        start_command: str | None = None,
        start_args: list[str] | None = None,
    ) -> None:
        """Initialize the REPL tool with no running backend."""
        self._backend: ReplBackendProtocol | None = None
        self._backend_factory = backend_factory or _default_backend_factory
        self._start_command = start_command
        self._start_args = list(start_args or [])

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
                    "description": (
                        "Timeout for reading output in seconds (default 10, 5 for stop)."
                    ),
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
            backend = self._backend_factory([command, *args])
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

    def ensure_started(
        self,
        command: str | None = None,
        args: list[str] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """Start the REPL if needed and return start status/result."""
        backend = self._backend
        if backend is not None and backend.is_running:
            return {"status": "started", "output": "", "stderr": ""}

        start_command = command or self._start_command or ""
        start_args = list(args if args is not None else self._start_args)
        return self._start(start_command, start_args, timeout)

    def eval_input(self, input: str, timeout: float = 10.0) -> dict[str, Any]:
        """Evaluate a line in the current REPL session."""
        return self._eval(input, timeout)

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


class ReplBackendProtocol(Protocol):
    """Minimal backend interface required by ReplExec."""

    @property
    def is_running(self) -> bool: ...

    @property
    def returncode(self) -> int | None: ...

    def start(self) -> None: ...

    def read_output(self, *, timeout: float | None = None, max_lines: int | None = None) -> str: ...

    def flush_error(self) -> str: ...

    def sendline(self, line: str) -> None: ...

    def close(self, *, timeout: float = 5.0) -> int | None: ...


def _default_backend_factory(argv: list[str]) -> ReplBackendProtocol:
    from edai.tool.backend import Backend

    return Backend(argv)


class MockBackend:
    """Simple in-memory backend for REPL-style tool simulation."""

    def __init__(
        self,
        argv: list[str],
        evaluator: Callable[[str], tuple[str, str] | str] | None = None,
        banner: str = "",
    ) -> None:
        self.argv = argv
        self._evaluator = evaluator
        self._banner = banner
        self._stdout_buffer = banner
        self._stderr_buffer = ""
        self._started = False
        self.is_running = False
        self.returncode: int | None = None

    def start(self) -> None:
        self._started = True
        self.is_running = True
        self.returncode = None

    def read_output(self, *, timeout: float | None = None, max_lines: int | None = None) -> str:
        _ = timeout
        _ = max_lines
        output = self._stdout_buffer
        self._stdout_buffer = ""
        if output:
            return output
        raise TimeoutError

    def flush_error(self) -> str:
        stderr = self._stderr_buffer
        self._stderr_buffer = ""
        return stderr

    def sendline(self, line: str) -> None:
        if not self.is_running:
            raise BackendError("backend is not running")

        if self._evaluator is None:
            self._stdout_buffer = f"{line}\n"
            return

        result = self._evaluator(line)
        if isinstance(result, tuple):
            stdout, stderr = result
        else:
            stdout, stderr = result, ""

        self._stdout_buffer = stdout
        self._stderr_buffer = stderr

    def close(self, *, timeout: float = 5.0) -> int | None:
        _ = timeout
        self.is_running = False
        self.returncode = 0
        return self.returncode
