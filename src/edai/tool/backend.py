"""Backend — interactive subprocess wrapper using pexpect (pseudo-terminal).

Wraps a long-running child process via a pty, handling bidirectional I/O.
stdout and stderr are merged (pty semantics).
"""

from __future__ import annotations

from collections.abc import MutableMapping

import pexpect

from edai.error import BackendError, BackendNotRunningError

__all__ = ["Backend", "BackendError", "BackendNotRunningError"]


class Backend:
    """Wraps an interactive subprocess using pexpect (pseudo-terminal).

    Typical usage::

        backend = Backend(["python", "-i", "-q"])
        backend.start()
        backend.sendline("print(1+1)")
        print(backend.read_output(timeout=5.0))
        backend.close()
    """

    def __init__(
        self,
        command: list[str],
        *,
        cwd: str | None = None,
        env: MutableMapping[str, str] | None = None,
        max_output_lines: int = 1_000_000,
    ) -> None:
        """Initialize the backend.

        Args:
            command: The command and arguments to execute.
            cwd: Working directory for the child process.
            env: Environment variables for the child process.
            max_output_lines: Not used by pexpect (kept for API compat).
        """
        if not command:
            raise ValueError("command must be a non-empty list")
        self._command = list(command)
        self._cwd = cwd
        self._env = env
        self._child: pexpect.spawn[str] | None = None

    @property
    def command(self) -> list[str]:
        return list(self._command)

    @property
    def is_running(self) -> bool:
        if self._child is None:
            return False
        return self._child.isalive()  # type: ignore[no-any-return]

    @property
    def returncode(self) -> int | None:
        if self._child is None:
            return None
        if self._child.isalive():
            return None
        return (  # type: ignore[no-any-return]
            self._child.exitstatus
            if self._child.exitstatus is not None
            else self._child.signalstatus
        )

    def start(self) -> None:
        """Launch the child process."""
        if self._child is not None and self._child.isalive():
            raise BackendError("Backend is already running — close it first")
        try:
            self._child = pexpect.spawn(
                self._command[0],
                args=self._command[1:],
                cwd=self._cwd,
                env=self._env,
                encoding="utf-8",
                timeout=30,
            )
        except pexpect.ExceptionPexpect as exc:
            raise BackendError(f"Failed to start '{' '.join(self._command)}': {exc}") from exc

    def send(self, data: str) -> None:
        """Write data to the process's stdin (no newline appended)."""
        self._check_running()
        try:
            self._child.send(data)  # type: ignore[union-attr]
        except pexpect.ExceptionPexpect as exc:
            raise BackendError(f"Failed to send data: {exc}") from exc

    def sendline(self, line: str) -> None:
        """Write a line (with trailing newline)."""
        self.send(line + "\n")

    def read_output(
        self,
        *,
        timeout: float | None = None,
        max_lines: int | None = None,
    ) -> str:
        """Read output from the process, blocking up to *timeout* seconds.

        Uses ``read_nonblocking`` with a positive timeout to behave like
        a blocking read-with-timeout.  Returns all captured output as a
        single string.
        """
        self._check_running()
        child = self._child
        try:
            data = child.read_nonblocking(  # type: ignore[union-attr]
                size=1_000_000,
                timeout=timeout if timeout is not None else 30,
            )
            return data or ""
        except pexpect.TIMEOUT:
            return ""
        except pexpect.EOF:
            return child.before or ""  # type: ignore[union-attr]

    def read_error(
        self,
        *,
        timeout: float | None = None,
        max_lines: int | None = None,
    ) -> str:
        """Read stderr — always empty (pty merges stdout/stderr).

        Included for API compatibility.  Use ``read_output`` to read all
        process output.
        """
        return ""

    def flush_output(self) -> str:
        """Return all currently buffered output without blocking."""
        if self._child is None or not self._child.isalive():
            return ""
        try:
            return self._child.read_nonblocking(size=1_000_000, timeout=0) or ""
        except (pexpect.TIMEOUT, pexpect.EOF):
            return ""

    def flush_error(self) -> str:
        """Return all currently buffered stderr — always empty (pty semantics)."""
        return ""

    def close(self, *, timeout: float = 5.0) -> int | None:
        """Shut down the child process.

        Closes the pty and waits for the process to exit.  Returns the
        exit code or None.
        """
        if self._child is None:
            return None
        rc = self.returncode
        self._child.close(force=True)
        self._child = None
        return rc

    def terminate(self) -> None:
        """Send SIGTERM to the child process."""
        self._check_running()
        self._child.terminate(force=True)  # type: ignore[union-attr]

    def kill(self) -> None:
        """Send SIGKILL to the child process."""
        self._check_running()
        self._child.kill(sig=9)  # type: ignore[union-attr]  # SIGKILL

    def __enter__(self) -> Backend:
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _check_running(self) -> None:
        if self._child is None:
            raise BackendNotRunningError("Backend has not been started")
        if not self._child.isalive():
            raise BackendNotRunningError(f"Backend process exited with code {self.returncode}")


if __name__ == "__main__":
    # Example usage
    backend = Backend(["python", "-i", "-q"])
    backend.start()
    print("Backend started. Sending command...")
    backend.sendline("print(1+1)")
    print("Reading output...")
    print(backend.read_output(timeout=5.0))
    backend.close()
