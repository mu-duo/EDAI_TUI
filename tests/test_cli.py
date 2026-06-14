"""Tests for the CLI entry point."""

from __future__ import annotations

from edai.__main__ import main


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
    """No arguments should show help and return 0."""
    assert main([]) == 0
