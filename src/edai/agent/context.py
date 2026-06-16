"""
edai.agent.context — Message history container with pretty-printing and file export.

The :class:`Context` class holds the list of chat messages for an :class:`~edai.agent.Agent`.
It provides human-readable formatting for debugging and can write its contents
to a file.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, overload

from openai.types.chat import ChatCompletionMessageParam

# ── style constants ──────────────────────────────────────────────────────

_SEP: str = "━"
_SEP_LEN: int = 60
_INDENT: str = "  "


def _separator(label: str) -> str:
    """Build a section separator line like ``━━━ label ━━━``."""
    inner = f" {label} "
    pad = _SEP * max(0, (_SEP_LEN - len(inner)) // 2)
    return f"{pad}{inner}{pad}"


def _format_message(index: int, msg: dict[str, Any]) -> str:
    """Format a single message dict into readable text."""
    role = msg.get("role", "?")  # type: ignore[union-attr]
    content = msg.get("content", "") or ""

    lines: list[str] = []
    lines.append(_separator(f"Message #{index} [{role}]"))

    # Format content — multi-line gets indented body
    if isinstance(content, str):
        if "\n" in content:
            for line in content.splitlines():
                lines.append(f"{_INDENT}{line}")
        else:
            lines.append(f"{_INDENT}{content}")
    else:
        # content is a list of parts (vision / tool-call messages)
        lines.append(f"{_INDENT}[complex content: {type(content).__name__}]")
        lines.append(f"{_INDENT}{content!r}")

    lines.append("")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
# Context
# ══════════════════════════════════════════════════════════════════════════


class Context:
    """Container for an LLM conversation message history.

    Provides pretty-printing for debugging (via :meth:`__str__`) and
    file export (via :meth:`to_file`).

    The class implements a list-like interface so it can serve as a
    drop-in replacement for a plain ``list[ChatCompletionMessageParam]``
    in most contexts (iteration, indexing, ``len()``, ``bool()``).
    """

    def __init__(
        self,
        messages: list[ChatCompletionMessageParam] | None = None,
    ) -> None:
        self._messages: list[ChatCompletionMessageParam] = (
            list(messages) if messages is not None else []
        )

    # ------------------------------------------------------------------
    # Read / write — list-like interface
    # ------------------------------------------------------------------

    def append(self, message: ChatCompletionMessageParam) -> None:
        """Append a message to the history."""
        self._messages.append(message)

    def clear(self) -> None:
        """Remove all messages."""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)

    @overload
    def __getitem__(self, index: int) -> ChatCompletionMessageParam: ...

    @overload
    def __getitem__(self, index: slice) -> list[ChatCompletionMessageParam]: ...

    def __getitem__(
        self, index: int | slice
    ) -> ChatCompletionMessageParam | list[ChatCompletionMessageParam]:
        return self._messages[index]

    def __setitem__(self, index: int, message: ChatCompletionMessageParam) -> None:
        self._messages[index] = message

    def __delitem__(self, index: int | slice) -> None:
        del self._messages[index]

    def __iter__(self) -> Iterator[ChatCompletionMessageParam]:
        return iter(self._messages)

    def __bool__(self) -> bool:
        return len(self._messages) > 0

    def __contains__(self, item: object) -> bool:
        return item in self._messages

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Context):
            return self._messages == other._messages
        if isinstance(other, list):
            return self._messages == other
        return NotImplemented

    def __reversed__(self) -> Iterator[ChatCompletionMessageParam]:
        return reversed(self._messages)

    def copy(self) -> Context:
        """Return a new :class:`Context` with the same messages."""
        return Context(list(self._messages))

    # ------------------------------------------------------------------
    # Pretty output
    # ------------------------------------------------------------------

    def to_text(self) -> str:
        """Return the entire message history as a human-readable string.

        Each message is prefixed with a separator header showing its
        index and role.
        """
        parts: list[str] = []
        for i, msg in enumerate(self._messages):
            parts.append(_format_message(i + 1, dict(msg)))  # type: ignore[arg-type]
        parts.append(_separator(f"Total: {len(self._messages)} messages"))
        parts.append("")
        return "\n".join(parts)

    def __str__(self) -> str:
        return self.to_text()

    def __repr__(self) -> str:
        return f"Context({len(self._messages)} messages)"

    # ------------------------------------------------------------------
    # File export
    # ------------------------------------------------------------------

    def to_file(self, path: str, mode: str = "w") -> None:
        """Write the pretty-printed message history to *path*.

        Args:
            path: Destination file path.
            mode: File open mode (default ``"w"``).
        """
        text = self.to_text()
        with open(path, mode, encoding="utf-8") as f:
            f.write(text)
