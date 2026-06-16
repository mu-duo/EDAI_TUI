"""CLI entry point for the edai package.

Invoke with::

    python -m edai

or after installation::

    edai
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Callable
from typing import Any


def _print_help() -> None:
    print("Usage: edai [OPTIONS]")
    print()
    print("A LLM-driven TUI for EDA tools")
    print()
    print("Options:")
    print("  -h, --help       Show this help message")
    print("  -V, --version    Show package version")


def _extract_tcl_command(reply: str, valid_commands: set[str]) -> str | None:
    """Try to extract a Tcl command line from an agent reply."""
    text = reply.strip()
    if not text:
        return None

    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()

    if text.startswith("%tcl"):
        text = text[4:].strip()

    for line in text.splitlines():
        candidate = line.strip()
        if not candidate:
            continue
        first = candidate.split()[0]
        if first in valid_commands:
            return candidate

    return None


def _run_python_input(text: str, namespace: dict[str, Any]) -> tuple[bool, Any]:
    """Try to execute shell input as Python.

    Returns ``(True, result)`` on success, where ``result`` is the final expression
    value when available. Returns ``(False, exc)`` when execution fails.
    """
    try:
        tree = ast.parse(text, mode="exec")
    except SyntaxError:
        return False, None

    try:
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            prefix = tree.body[:-1]
            if prefix:
                prefix_module = ast.Module(body=prefix, type_ignores=[])
                ast.fix_missing_locations(prefix_module)
                exec(compile(prefix_module, "<edai-shell>", "exec"), namespace, namespace)

            expr = ast.Expression(tree.body[-1].value)
            ast.fix_missing_locations(expr)
            result = eval(compile(expr, "<edai-shell>", "eval"), namespace, namespace)
            return True, result

        exec(compile(tree, "<edai-shell>", "exec"), namespace, namespace)
        return True, None
    except Exception as exc:
        return False, exc


def _make_shell_dispatch_transformer(
    valid_commands: set[str],
) -> Callable[[str | list[str]], str | list[str]]:
    """Route all regular shell input through the unified dispatcher."""

    def _transform(line: str | list[str]) -> str | list[str]:
        if isinstance(line, list):
            raw = line[0]
        else:
            raw = line
        stripped = raw.strip()

        if not stripped or stripped[0] in ("%", "!", "?", "#", ";"):
            return line

        if raw.startswith('get_ipython().run_line_magic("tcl",'):
            return line

        first = stripped.split()[0] if stripped.split() else ""
        if first in valid_commands:
            return line

        rewritten = f"_handle_shell_input({stripped!r})"
        if isinstance(line, list):
            return [rewritten] + line[1:]
        return rewritten

    return _transform


def _build_commands_text(commands: dict[str, Any]) -> str:
    """Build a compact command reference string for the agent."""
    parts = ["Available Tcl commands and their options:"]
    for name, info in sorted(commands.items()):
        opts = info.get("options", [])
        switches = set(info.get("switch_options", []))
        tokens: list[str] = []
        for o in opts:
            if o == "-help":
                continue
            if o in switches:
                tokens.append(o)
            else:
                tokens.append(f"{o} <value>")
        opt_str = " ".join(tokens)
        if opt_str:
            parts.append(f"  {name} {opt_str}")
        else:
            parts.append(f"  {name}")
    parts.append("")
    parts.append("Tcl builtins: set, puts, expr, list_vars")
    parts.append("")
    parts.append(
        "When the user types a Tcl command directly it executes immediately "
        "and the result is logged to this context. "
        "When you respond with a Tcl command line, it will be extracted and executed."
    )
    return "\n".join(parts)


def _display_shell_value(value: Any) -> None:
    """Display shell output without relying on repr echo."""
    if value is None or value == "":
        return

    try:
        from IPython.display import Pretty, display

        display(Pretty(str(value)))  # type: ignore[no-untyped-call]
    except ImportError:
        print(value)


def _launch_ipython_shell() -> int:
    from IPython.terminal.interactiveshell import TerminalInteractiveShell

    from edai.agent import Agent, AgentConfig
    from edai.error import ConfigurationError
    from edai.tool.tcl_interpreter import (
        ALL_COMMANDS,
        TCL_BUILTINS,
        TCL_COMMANDS,
        _interp,
        load_ipython_extension,
    )

    shell = TerminalInteractiveShell.instance()
    load_ipython_extension(shell)

    tcl = _interp
    valid_commands = set(ALL_COMMANDS) | set(TCL_BUILTINS)

    agent: Agent | None
    agent_error: str | None = None
    try:
        agent = Agent(
            AgentConfig(
                system_prompt=(
                    "You are an EDA Tcl assistant. "
                    "The shell already executes direct Tcl commands on its own. "
                    "You only receive non-Tcl user input. "
                    "If the user intent can be satisfied with one Tcl command, reply with exactly "
                    "one Tcl command line and nothing else. "
                    "If the user likely mistyped a Tcl command or the request is ambiguous, "
                    "reply with one short sentence explaining the issue and suggest the closest "
                    "valid Tcl command when possible. "
                    "Do not use markdown fences. Do not return multiple commands."
                )
            )
        )
        # Give the agent the full command reference
        agent.context.append({"role": "system", "content": _build_commands_text(TCL_COMMANDS)})
    except ConfigurationError as exc:
        agent = None
        agent_error = str(exc)

    def run_tcl(command: str) -> Any:
        """Execute a Tcl command directly through TclInterpreter."""
        result = tcl.execute(command)
        if agent is not None:
            agent.context.append({"role": "user", "content": f"[Tcl] {command}"})
            agent.context.append({"role": "system", "content": f"[Output] {result}"})
        return result

    def ask_agent(message: str) -> dict[str, Any]:
        """Ask the agent to execute intent or diagnose likely command mistakes."""
        if agent is None:
            return {
                "error": agent_error or "agent is not available",
                "executed": False,
            }

        reply = agent.chat(message)
        command = _extract_tcl_command(reply, valid_commands)
        if command is None:
            return {
                "input": message,
                "agent_reply": reply,
                "executed": False,
            }

        result = tcl.execute(command)
        # Log the Tcl execution result back to context so the agent
        # can see what happened with the command it chose.
        agent.context.append(
            {
                "role": "system",
                "content": f"[Tcl] {command}\n[Output] {result}",
            }
        )
        return {
            "input": message,
            "agent_reply": reply,
            "command": command,
            "executed": True,
            "result": result,
        }

    def _handle_shell_input(text: str) -> None:
        """Handle regular shell input with Python/Tcl/agent fallback."""
        stripped = text.strip()
        if not stripped:
            return

        first = stripped.split()[0] if stripped.split() else ""
        if first in valid_commands:
            _display_shell_value(run_tcl(stripped))
            return

        python_ok, python_result = _run_python_input(stripped, shell.user_ns)
        if python_ok:
            _display_shell_value(python_result)
            if agent is not None and python_result is not None:
                agent.context.append({"role": "user", "content": f"[Python] {stripped}"})
                agent.context.append(
                    {
                        "role": "system",
                        "content": f"[Output] {python_result}",
                    }
                )
            return

        result = ask_agent(stripped)

        error = result.get("error")
        if error:
            print(f"Agent unavailable: {error}")
            return

        if result.get("executed"):
            command = result.get("command", "")
            if command:
                print(f"[agent->tcl] {command}")
            _display_shell_value(result.get("result"))
            return

        reply = result.get("agent_reply")
        if reply:
            print(f"[agent] {reply}")

    banner = [
        "EDAI IPython shell",
        "Direct input behavior:",
        "  - Tcl command      -> execute in Tcl interpreter",
        "  - Other text       -> send to agent for intent execution / typo check",
        "Available objects:",
        "  - tcl_interpreter: TclInterpreter instance",
        "  - run_tcl(cmd): execute a Tcl command directly",
        "  - ask_agent(msg): ask the LLM to choose and execute a Tcl command",
        "Examples:",
        "  read_liberty -path ./demo.lib",
        "  please read liberty file ./demo.lib",
    ]
    if agent_error:
        banner.append(f"Agent unavailable: {agent_error}")

    print("\n".join(banner))

    shell.input_transformers_post.append(_make_shell_dispatch_transformer(valid_commands))
    shell.user_ns["tcl_interpreter"] = tcl
    shell.user_ns["run_tcl"] = run_tcl
    shell.user_ns["ask_agent"] = ask_agent
    shell.user_ns["_handle_shell_input"] = _handle_shell_input
    shell.user_ns["agent"] = agent
    shell.mainloop()  # type: ignore[no-untyped-call]
    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point."""
    args = argv if argv is not None else sys.argv[1:]

    if args and args[0] in ("-h", "--help"):
        _print_help()
        return 0

    if args and args[0] in ("-V", "--version"):
        from edai import __version__

        print(f"edai v{__version__}")
        return 0

    if not args:
        return _launch_ipython_shell()

    print(f"edai: unknown argument '{args[0]}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
