"""Typer application assembly for the PyLD CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

try:
    import typer
except ImportError as cause:  # pragma: no cover
    raise ImportError(
        'The pyld command-line interface requires Typer. '
        'Install it with: pip install "PyLD[cli]"'
    ) from cause

from typer import Option

from pyld.cli import state as cli_state
from pyld.cli.commands.cache import cache_clear
from pyld.cli.commands.compact import compact_command
from pyld.cli.commands.expand import expand_command
from pyld.cli.commands.flatten import flatten_command
from pyld.cli.commands.frame import frame_command
from pyld.cli.commands.from_rdf import from_rdf_command
from pyld.cli.commands.get import get_command
from pyld.cli.commands.to_rdf import to_rdf_command
from pyld.cli.errors import print_error
from pyld.cli.state import State

pyld = typer.Typer(
    help='Command-line tool for JSON-LD transformations.',
    no_args_is_help=True,
)


@pyld.callback()
def root(
    ctx: typer.Context,
    traceback: Annotated[
        bool,
        Option('--traceback', help='Show the Python traceback on errors.'),
    ] = False,
    cache_file: Annotated[
        Path | None,
        Option(
            '--cache-file',
            envvar='PYLD_CACHE_FILE',
            help='SQLite file for the CLI HTTP cache.',
        ),
    ] = None,
) -> None:
    state = State(traceback=traceback, cache_file=cache_file)
    ctx.obj = state
    # ``main`` reads this after Click has torn down the context.
    cli_state.current = state


pyld.command('get')(get_command)
pyld.command('expand')(expand_command)
pyld.command('compact')(compact_command)
pyld.command('flatten')(flatten_command)
pyld.command('frame')(frame_command)
pyld.command('to-rdf')(to_rdf_command)
pyld.command('from-rdf')(from_rdf_command)

cache_app = typer.Typer(help='Cache management.', no_args_is_help=True)
cache_app.command('clear')(cache_clear)
pyld.add_typer(cache_app, name='cache')


def main(args: list[str] | None = None) -> None:
    """Entry point for the ``pyld`` console script."""
    try:
        pyld(args=args, prog_name='pyld')
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as err:
        if cli_state.current.traceback:
            raise
        print_error(err, sys.argv[1:] if args is None else args)
        raise SystemExit(1) from None
