"""Backend — interactive subprocess wrapper for EDA tools.

Manages a long-running child process, providing bidirectional I/O:
send input via stdin, capture stdout/stderr asynchronously.
"""

from __future__ import annotations

import subprocess
import threading
import time as _time
from collections import deque
from typing import IO

from edai.error import BackendError, BackendNotRunningError

__all__ = [
    "Backend",
    "BackendError",
    "BackendNotRunningError",
]


class Backend:
    """Wraps an interactive subprocess with asynchronous I/O capture.

    Typical usage::

        backend = Backend(["irun", "-input", "-"])
        backend.start()
        backend.send("run 100ns\\n")
        print(backend.read_output(timeout=5.0))
        backend.close()

    Output from stdout and stderr is continuously drained in background
    threads so the process never blocks on full pipes.
    """

    def __init__(
        self,
        command: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        max_output_lines: int = 10_000,
    ) -> None:
        """Initialize the backend.

        Args:
            command: The command and arguments to execute (e.g. ["irun"]).
            cwd: Working directory for the child process.
            env: Environment variables for the child process.
                Inherits from the current process by default.
            max_output_lines: Maximum number of output lines retained in
                memory per stream.
        """
        if not command:
            raise ValueError("command must be a non-empty list")

        self._command = list(command)
        self._cwd = cwd
        self._env = env
        self._max_output_lines = max_output_lines

        self._process: subprocess.Popen[str] | None = None
        self._returncode: int | None = None
        self._stdout_lines: deque[str] = deque(maxlen=max_output_lines)
        self._stderr_lines: deque[str] = deque(maxlen=max_output_lines)
        self._lock = threading.Lock()
        self._reader_threads: list[threading.Thread] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def command(self) -> list[str]:
        """The command this backend was configured with (read-only copy)."""
        return list(self._command)

    @property
    def is_running(self) -> bool:
        """True if the child process is still running."""
        proc = self._process
        if proc is None:
            return False
        return proc.poll() is None

    @property
    def returncode(self) -> int | None:
        """Return code of the process, or None if still running or not started."""
        if self._process is not None:
            rc = self._process.poll()
            if rc is not None:
                self._returncode = rc
            return rc
        return self._returncode

    def start(self) -> None:
        """Launch the child process and begin capturing output.

        Raises:
            BackendError: If the process is already running or cannot be started.
        """
        if self._process is not None:
            raise BackendError("Backend is already running — close it first")

        try:
            self._process = subprocess.Popen(
                self._command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._cwd,
                env=self._env,
                text=True,
                bufsize=1,  # line-buffered
            )
        except FileNotFoundError:
            raise BackendError(
                f"Command not found: {self._command[0]}. Is the EDA tool installed and on PATH?"
            ) from None
        except OSError as exc:
            raise BackendError(f"Failed to start '{' '.join(self._command)}': {exc}") from exc

        # Start background reader threads
        assert self._process.stdout is not None
        assert self._process.stderr is not None

        self._reader_threads = [
            threading.Thread(
                target=self._read_stream,
                args=(self._process.stdout, self._stdout_lines),
                daemon=True,
            ),
            threading.Thread(
                target=self._read_stream,
                args=(self._process.stderr, self._stderr_lines),
                daemon=True,
            ),
        ]
        for t in self._reader_threads:
            t.start()

    def send(self, data: str) -> None:
        """Write data to the process's stdin.

        Args:
            data: Text to send (a newline is NOT appended automatically).

        Raises:
            BackendNotRunningError: If the process is not running.
            BackendError: If writing to stdin fails.
        """
        self._check_running()
        assert self._process is not None and self._process.stdin is not None
        try:
            self._process.stdin.write(data)
            self._process.stdin.flush()
        except OSError as exc:
            raise BackendError(f"Failed to write to process stdin: {exc}") from exc

    def sendline(self, line: str) -> None:
        """Write a line (with trailing newline) to the process's stdin.

        Equivalent to ``send(line + '\\n')``.
        """
        self.send(line + "\n")

    def read_output(
        self,
        *,
        timeout: float | None = None,
        max_lines: int | None = None,
    ) -> str:
        """Read captured stdout lines, blocking until at least one line is available.

        Args:
            timeout: Maximum seconds to wait for output (None = wait forever).
            max_lines: Maximum number of lines to return
                (None = return all currently captured lines).

        Returns:
            Joined lines from stdout.

        Raises:
            BackendNotRunningError: If the process is not running.
            TimeoutError: If no output arrives within *timeout* seconds.
        """
        self._check_running()

        with self._lock:
            if self._stdout_lines:
                return self._drain_lines(self._stdout_lines, max_lines)

        # No output yet — wait a bit for reader threads to feed the buffer.
        if timeout is None:
            # Use a finite but generous poll; caller can loop if needed.
            timeout = 30.0

        deadline = _deadline(timeout)
        while True:
            with self._lock:
                if self._stdout_lines:
                    return self._drain_lines(self._stdout_lines, max_lines)
            if _is_expired(deadline):
                raise TimeoutError(f"No output received from backend within {timeout}s")
            _sleep(0.05)

    def read_error(
        self,
        *,
        timeout: float | None = None,
        max_lines: int | None = None,
    ) -> str:
        """Read captured stderr lines (same semantics as *read_output*)."""
        self._check_running()

        with self._lock:
            if self._stderr_lines:
                return self._drain_lines(self._stderr_lines, max_lines)

        deadline = _deadline(timeout if timeout is not None else 30.0)
        while True:
            with self._lock:
                if self._stderr_lines:
                    return self._drain_lines(self._stderr_lines, max_lines)
            if _is_expired(deadline):
                raise TimeoutError(
                    f"No error output received from backend within {timeout or 30.0}s"
                )
            _sleep(0.05)

    def flush_output(self) -> str:
        """Read and return all currently captured stdout without blocking.

        Returns:
            All buffered stdout content (empty string if none).
        """
        with self._lock:
            return self._drain_lines(self._stdout_lines, max_lines=None)

    def flush_error(self) -> str:
        """Read and return all currently captured stderr without blocking."""
        with self._lock:
            return self._drain_lines(self._stderr_lines, max_lines=None)

    def close(self, *, timeout: float = 5.0) -> int | None:
        """Gracefully shut down the backend process.

        1. Send EOF to stdin.
        2. Wait for the process to exit (within *timeout* seconds).
        3. If still alive, terminate → kill.

        Returns:
            The process return code, or None if already stopped.

        Raises:
            BackendError: If closing fails unexpectedly.
        """
        proc = self._process
        if proc is None:
            return None

        returncode = proc.poll()

        # Step 1: close stdin (EOF)
        if returncode is None and proc.stdin is not None:
            try:
                proc.stdin.close()
            except OSError:
                pass

        # Step 2: wait politely
        if returncode is None:
            try:
                proc.wait(timeout=timeout)
                returncode = proc.returncode
            except subprocess.TimeoutExpired:
                pass

        # Step 3: escalate
        if returncode is None:
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
                returncode = proc.returncode
            except (subprocess.TimeoutExpired, OSError):
                try:
                    proc.kill()
                    proc.wait(timeout=2.0)
                    returncode = proc.returncode
                except (subprocess.TimeoutExpired, OSError):
                    pass

        # Join reader threads (best-effort)
        for t in self._reader_threads:
            if t.is_alive():
                t.join(timeout=1.0)

        self._returncode = returncode
        self._process = None
        self._reader_threads.clear()
        return returncode

    def terminate(self) -> None:
        """Send SIGTERM to the child process."""
        self._check_running()
        assert self._process is not None
        self._process.terminate()

    def kill(self) -> None:
        """Send SIGKILL to the child process."""
        self._check_running()
        assert self._process is not None
        self._process.kill()

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
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_running(self) -> None:
        """Raise BackendNotRunningError if the process is not alive."""
        proc = self._process
        if proc is None:
            if self._returncode is not None:
                raise BackendNotRunningError(f"Backend process exited with code {self._returncode}")
            raise BackendNotRunningError("Backend has not been started")
        rc = proc.poll()
        if rc is not None:
            self._returncode = rc
            raise BackendNotRunningError(f"Backend process exited with code {rc}")

    @staticmethod
    def _read_stream(stream: IO[str], buffer: deque[str]) -> None:
        """Drain *stream* line-by-line into *buffer* (runs in a daemon thread)."""
        try:
            for line in stream:
                buffer.append(line)
        except ValueError:
            # Stream closed while reading
            pass
        finally:
            try:
                stream.close()
            except OSError:
                pass

    @staticmethod
    def _drain_lines(buffer: deque[str], max_lines: int | None) -> str:
        """Pop and join lines from *buffer* (caller must hold the lock)."""
        count = max_lines if max_lines is not None else len(buffer)
        lines = [buffer.popleft() for _ in range(min(count, len(buffer)))]
        return "".join(lines)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _deadline(timeout: float) -> float:
    return _time.monotonic() + timeout


def _is_expired(deadline: float) -> bool:
    return _time.monotonic() >= deadline


def _sleep(seconds: float) -> None:
    _time.sleep(seconds)
