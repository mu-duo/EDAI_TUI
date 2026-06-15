"""Tests for the Backend interactive subprocess wrapper."""

from __future__ import annotations

import sys
import time

import pytest
from edai.backend import Backend, BackendError, BackendNotRunningError

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

# A tiny Python script that echoes stdin lines to stdout or stderr.
# Used as the test subprocess so tests are self-contained.
_ECHO_SCRIPT = """\
import sys
for line in sys.stdin:
    line = line.rstrip('\\n')
    if line == '__exit__':
        break
    if line.startswith('err:'):
        print(line[4:], file=sys.stderr, flush=True)
    else:
        print(line, flush=True)
"""


@pytest.fixture
def echo_cmd() -> list[str]:
    """Command that runs the echo script above."""
    return [sys.executable, "-c", _ECHO_SCRIPT]


# ------------------------------------------------------------------
# Basic lifecycle
# ------------------------------------------------------------------


class TestLifecycle:
    def test_start_and_stop(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd) as bk:
            assert bk.is_running
            assert bk.returncode is None

        # After exit, process should be done (returncode is preserved)
        assert bk.returncode == 0
        assert not bk.is_running

    def test_close_twice_is_idempotent(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        bk.start()
        bk.close()
        assert bk.close() is None  # second close returns None

    def test_context_manager(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd):
            pass  # should not raise

    def test_start_twice_raises(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        bk.start()
        try:
            with pytest.raises(BackendError, match="already running"):
                bk.start()
        finally:
            bk.close()


# ------------------------------------------------------------------
# Send / receive
# ------------------------------------------------------------------


class TestIO:
    def test_send_and_read_output(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd) as bk:
            bk.sendline("hello")
            assert bk.read_output(timeout=5.0) == "hello\n"

    def test_multiple_lines(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd) as bk:
            bk.sendline("line1")
            bk.sendline("line2")
            bk.sendline("line3")
            # Drain all output
            out = ""
            deadline = time.monotonic() + 5.0
            while len(out) < len("line1\nline2\nline3\n"):
                out += bk.read_output(timeout=1.0)
                if time.monotonic() > deadline:
                    break
            assert out == "line1\nline2\nline3\n"

    def test_send_without_newline(self, echo_cmd: list[str]) -> None:
        """send() doesn't append newline; the echo script can still echo it."""
        with Backend(echo_cmd) as bk:
            bk.send("hello\n")
            assert bk.read_output(timeout=5.0) == "hello\n"

    def test_flush_output_nonblocking(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd) as bk:
            bk.sendline("hello")
            # Give the reader thread time to pick it up
            deadline = time.monotonic() + 5.0
            out = ""
            while not out:
                out = bk.flush_output()
                if time.monotonic() > deadline:
                    break
                time.sleep(0.05)
            assert out == "hello\n"

    def test_flush_output_empty(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd) as bk:
            assert bk.flush_output() == ""

    def test_read_stderr(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd) as bk:
            bk.sendline("err:warning: something happened")
            err = bk.read_error(timeout=5.0)
            assert err == "warning: something happened\n"

    def test_flush_error(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd) as bk:
            bk.sendline("err:oops")
            deadline = time.monotonic() + 5.0
            out = ""
            while not out:
                out = bk.flush_error()
                if time.monotonic() > deadline:
                    break
                time.sleep(0.05)
            assert out == "oops\n"

    def test_read_output_max_lines(self, echo_cmd: list[str]) -> None:
        """max_lines limits how many buffered lines are returned."""
        with Backend(echo_cmd) as bk:
            bk.sendline("1")
            bk.sendline("2")
            bk.sendline("3")
            # Wait for all lines to arrive first
            all_lines = bk.read_output(timeout=5.0, max_lines=3)
            assert all_lines == "1\n2\n3\n"
            # Buffer should now be empty; send one more and read with max_lines=1
            bk.sendline("a")
            bk.sendline("b")
            one = bk.read_output(timeout=5.0, max_lines=1)
            assert one == "a\n"


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------


class TestErrors:
    def test_command_not_found(self) -> None:
        with pytest.raises(BackendError, match="Command not found"):
            Backend(["./nonexistent_tool_xyz"]).start()

    def test_send_when_not_started(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        with pytest.raises(BackendNotRunningError, match="not been started"):
            bk.send("data")

    def test_read_when_not_started(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        with pytest.raises(BackendNotRunningError, match="not been started"):
            bk.read_output()

    def test_send_after_exit(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        bk.start()
        bk.sendline("__exit__")
        bk.close()
        with pytest.raises(BackendNotRunningError, match="exited with code 0"):
            bk.send("data")

    def test_read_timeout(self, echo_cmd: list[str]) -> None:
        """read_output should timeout if the process produces no output."""
        with Backend(echo_cmd) as bk:
            # Don't send anything; read with a short timeout
            with pytest.raises(TimeoutError, match="No output received"):
                bk.read_output(timeout=0.5)

    def test_start_with_empty_command(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            Backend([])

    def test_terminate(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        bk.start()
        bk.terminate()
        rc = bk.close()
        assert rc is not None

    def test_kill(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        bk.start()
        bk.kill()
        rc = bk.close()
        assert rc is not None

    def test_close_with_timeout(self) -> None:
        """Process that ignores SIGTERM should still be killed by close()."""
        # Use `sleep infinity` or equivalent to create a stubborn process
        if sys.platform == "win32":
            cmd = [sys.executable, "-c", "import time; time.sleep(3600)"]
        else:
            cmd = ["sleep", "infinity"]
        bk = Backend(cmd)
        bk.start()
        # close with aggressive escalation (terminate → kill)
        rc = bk.close(timeout=0.5)
        assert rc is not None  # process was killed


# ------------------------------------------------------------------
# Properties
# ------------------------------------------------------------------


class TestProperties:
    def test_command_property(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        assert bk.command == echo_cmd
        # Should return a copy, not the original list
        assert bk.command is not echo_cmd

    def test_returncode_before_start(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        assert bk.returncode is None

    def test_is_running_before_start(self, echo_cmd: list[str]) -> None:
        bk = Backend(echo_cmd)
        assert not bk.is_running

    def test_max_output_lines(self) -> None:
        """Small buffer should not cause issues."""
        with Backend(
            [sys.executable, "-c", "import sys; [print(l, flush=True) for l in sys.stdin]"],
            max_output_lines=5,
        ) as bk:
            for i in range(10):
                bk.sendline(f"line{i}")
            # Read a few lines back
            out = bk.read_output(timeout=5.0)
            assert out


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


class TestEdgeCases:
    def test_send_empty_string(self, echo_cmd: list[str]) -> None:
        with Backend(echo_cmd) as bk:
            bk.send("")  # should not raise
            bk.send("\n")
            assert bk.read_output(timeout=5.0) == "\n"

    def test_process_that_exits_immediately(self) -> None:
        """Backend should handle a process that exits on its own."""
        bk = Backend([sys.executable, "-c", "print('hello')"])
        bk.start()
        rc = bk.close(timeout=5.0)
        assert rc == 0

    def test_context_manager_on_raise(self, echo_cmd: list[str]) -> None:
        """__exit__ should clean up even if the body raises."""
        with pytest.raises(RuntimeError):
            with Backend(echo_cmd) as bk:
                assert bk.is_running
                raise RuntimeError("boom")
        assert not bk.is_running
