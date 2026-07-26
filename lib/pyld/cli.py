"""Command-line interface for PyLD."""

from __future__ import annotations

import json
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

try:
    import typer
except ImportError as cause:  # pragma: no cover
    raise ImportError(
        'The pyld command-line interface requires Typer. '
        'Install it with: pip install "PyLD[cli]"'
    ) from cause

from rich.console import Console
from rich.errors import NotRenderableError
from rich.panel import Panel
from rich.syntax import Syntax
from typer import Argument, Option

from pyld import (
    FileDocumentLoader,
    SchemeDirectedDocumentLoader,
    SqliteCacheRequestsDocumentLoader,
    TypeDirectedDocumentLoader,
    jsonld,
)


@dataclass
class State:
    """Per-invocation CLI state carried on ``typer.Context.obj``."""

    traceback: bool = False
    cache_file: Path | None = None


pyld = typer.Typer(
    help='Command-line tool for JSON-LD transformations.',
    no_args_is_help=True,
)
cache_app = typer.Typer(help='Cache management.', no_args_is_help=True)
pyld.add_typer(cache_app, name='cache')
pyld.state = State()  # type: ignore[attr-defined]

console = Console()
err_console = Console(stderr=True)

MaybeStr = str | None

InputArgument = Annotated[
    MaybeStr,
    Argument(
        metavar='INPUT',
        help='Path or URL. Omit or pass - to read from standard input.',
    ),
]


def default_cache_file() -> Path:
    from platformdirs import user_cache_dir

    return Path(user_cache_dir('pyld')) / 'cli' / 'http_cache.sqlite'


def configured_cache_file() -> Path:
    override = pyld.state.cache_file  # type: ignore[attr-defined]
    path = override if override is not None else default_cache_file()
    return path.expanduser().resolve()


def document_loader():
    file_loader = FileDocumentLoader()
    remote = SqliteCacheRequestsDocumentLoader(
        sqlite_file_path=configured_cache_file(),
    )
    return TypeDirectedDocumentLoader(
        {
            Path: file_loader,
            str: SchemeDirectedDocumentLoader(
                file=file_loader,
                http=remote,
                https=remote,
            ),
        }
    )


def parse_location(value: str) -> str | Path:
    """Interpret a CLI argument as a URL string or a local filesystem Path."""
    scheme = urlparse(value).scheme
    # Single-letter schemes are Windows drive letters (C:\…), not URLs.
    if scheme and len(scheme) != 1:
        return value
    return Path(value).expanduser().resolve()


def is_stdin(value: MaybeStr) -> bool:
    return value is None or value == '-'


def as_document_url(location: str | Path) -> str:
    """Convert a parsed location to a URL string for the JSON-LD API."""
    if isinstance(location, Path):
        return location.as_uri()
    return location


def read_input(value: MaybeStr) -> Any:
    """Return a document from stdin, or a URL string for PyLD to dereference."""
    if is_stdin(value):
        return json.load(sys.stdin)
    return as_document_url(parse_location(value))


def context_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return as_document_url(parse_location(value))


def print_json(document: Any) -> None:
    text = json.dumps(document, indent=2, ensure_ascii=False)
    console.print(
        Syntax(text, 'json', background_color='default'),
        soft_wrap=True,
    )


def loader_options() -> dict:
    return {'documentLoader': document_loader()}


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
    # Entry-point wrapper reads this after Click has torn down the context.
    pyld.state = state  # type: ignore[attr-defined]


@pyld.command('get')
def get_command(input_: InputArgument = None) -> None:
    """Retrieve and print a JSON-LD document."""
    if is_stdin(input_):
        document = json.load(sys.stdin)
    else:
        remote = jsonld.load_document(parse_location(input_), loader_options())
        document = remote['document']
    print_json(document)


@pyld.command('expand')
def expand_command(
    input_: InputArgument = None,
    context: Annotated[
        MaybeStr,
        Option('--context', '-c', help='Context to expand with.'),
    ] = None,
    base: Annotated[MaybeStr, Option(help='The base IRI to use.')] = None,
    extract_all_scripts: Annotated[
        bool | None,
        Option(
            '--extract-all-scripts/--no-extract-all-scripts',
            help=('Extract all JSON-LD script elements from HTML, or just the first.'),
        ),
    ] = None,
) -> None:
    """Expand a JSON-LD document."""
    options = loader_options()
    if context is not None:
        options['expandContext'] = context_value(context)
    if base is not None:
        options['base'] = base
    if extract_all_scripts is not None:
        options['extractAllScripts'] = extract_all_scripts

    result = jsonld.expand(read_input(input_), options=options)
    print_json(result)


@cache_app.command('clear')
def cache_clear() -> None:
    """Clear the CLI HTTP cache."""
    path = configured_cache_file()
    if path.exists():
        path.unlink()
    console.print('Cache cleared.', style='green')


def main(args: list[str] | None = None) -> None:
    """Entry point for the ``pyld`` console script."""
    try:
        pyld(args=args, prog_name='pyld')
    except (SystemExit, KeyboardInterrupt):
        raise
    except Exception as err:
        if pyld.state.traceback:  # type: ignore[attr-defined]
            raise
        print_error(err, sys.argv[1:] if args is None else args)
        raise SystemExit(1) from None
