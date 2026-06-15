"""Tests for the CLI entry point."""

from __future__ import annotations

from unittest.mock import patch

from edai.__main__ import _run_python_input, main


def test_help() -> None:
    """--help should return exit code 0."""
    assert main(["--help"]) == 0


def test_version() -> None:
    """--version should return exit code 0 and print version."""
    assert main(["--version"]) == 0


def test_unknown_arg() -> None:
    """An unknown argument should return exit code 1."""
    assert main(["--bogus"]) == 1


def test_no_args() -> None:
    """No arguments should launch the interactive shell."""
    with patch("edai.__main__._launch_ipython_shell", return_value=0) as launcher:
        assert main([]) == 0
    launcher.assert_called_once_with()


def test_run_python_input_reports_failures_for_agent_fallback() -> None:
    """Non-executable input should be available for agent fallback."""
    namespace: dict[str, object] = {}

    ok, result = _run_python_input("你好", namespace)
    assert ok is False
    assert isinstance(result, Exception) or result is None

    ok, result = _run_python_input('print("1")', namespace)
    assert ok is True
    assert result is None
