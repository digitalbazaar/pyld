"""Concise CLI error reporting."""

from __future__ import annotations

import shlex

from rich.console import Console
from rich.errors import NotRenderableError
from rich.panel import Panel

err_console = Console(stderr=True)


def traceback_command(args: list[str]) -> str:
    """Render the failed invocation with ``--traceback`` added."""
    return shlex.join(['pyld', '--traceback', *args])


def print_error(err: Exception, args: list[str]) -> None:
    try:
        err_console.print(Panel(str(err), title=type(err).__name__, style='red'))
    except NotRenderableError:  # pragma: no cover
        err_console.print(Panel(repr(err), title=type(err).__name__, style='red'))
    err_console.print(
        f'To see the Python traceback, run: {traceback_command(args)}',
        style='dim',
        soft_wrap=True,
    )
