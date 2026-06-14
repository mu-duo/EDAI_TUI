"""Tests for package metadata and version consistency."""

from edai import __version__


def test_version_exists() -> None:
    """The package must expose a valid version string."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_parsable() -> None:
    """The version string must be a valid PEP 440 version."""
    parts = __version__.split(".")
    assert len(parts) == 3, f"Expected MAJOR.MINOR.PATCH, got {__version__}"
    for i, part in enumerate(parts):
        assert part.isdigit(), f"Version part {i} ('{part}') is not numeric"
