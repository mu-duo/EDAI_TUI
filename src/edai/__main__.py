"""CLI entry point for the edai package.

Invoke with::

    python -m edai

or after installation::

    edai
"""

import sys


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = argv if argv is not None else sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print("Usage: edai [OPTIONS]")
        print()
        print("A LLM-driven TUI for EDA tools")
        return 0

    if args[0] in ("-V", "--version"):
        from edai import __version__

        print(f"edai v{__version__}")
        return 0

    print(f"edai: unknown argument '{args[0]}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
