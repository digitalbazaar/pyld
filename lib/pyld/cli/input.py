"""CLI document locations and standard-input readers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlparse

import typer
from platformdirs import user_cache_dir
from typer import Argument

from pyld import (
    FileDocumentLoader,
    SchemeDirectedDocumentLoader,
    SqliteCacheRequestsDocumentLoader,
    TypeDirectedDocumentLoader,
)
from pyld.cli import state as cli_state

Input = Annotated[
    str,
    Argument(
        metavar='INPUT',
        help='Path or HTTP(S) URL. Pass - to read from standard input.',
    ),
]

LocalInput = Annotated[
    str,
    Argument(
        metavar='INPUT',
        help='Local path. Pass - to read from standard input.',
    ),
]

ContextArgument = Annotated[
    str,
    Argument(
        metavar='CONTEXT',
        help='Context path or URL. Pass - to read JSON from standard input.',
    ),
]

FrameArgument = Annotated[
    str,
    Argument(
        metavar='FRAME',
        help='Frame path or URL. Pass - to read JSON from standard input.',
    ),
]


def default_cache_file() -> Path:
    return Path(user_cache_dir('pyld')) / 'cli' / 'http_cache.sqlite'


def configured_cache_file() -> Path:
    override = cli_state.current.cache_file
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
    windows_drive = sys.platform == 'win32' and len(scheme) == 1
    if scheme and not windows_drive:
        return value
    return Path(value).expanduser().resolve()


def document_url(value: str) -> str:
    """Convert a CLI location to the URL form accepted by the JSON-LD API."""
    location = parse_location(value)
    if isinstance(location, Path):
        # Processing APIs dereference string inputs, so local documents enter
        # the loader pipeline as file URLs rather than Path objects.
        return location.as_uri()
    return location


def is_stdin(value: str) -> bool:
    return value == '-'


def document_value(value: str) -> Any:
    """Return JSON from stdin, or a URL for a document operand."""
    if is_stdin(value):
        return json.load(sys.stdin)
    return document_url(value)


def ensure_single_stdin(*values: str | None) -> None:
    """Reject invocations where more than one operand would consume stdin."""
    if sum(value == '-' for value in values) > 1:
        raise typer.BadParameter(
            'Only one operand may read from standard input.',
            param_hint='INPUT',
        )


def read_nquads(value: str) -> str:
    """Read raw N-Quads from standard input or a local file."""
    if is_stdin(value):
        return sys.stdin.read()
    location = parse_location(value)
    if isinstance(location, str):
        raise typer.BadParameter(
            'N-Quads input must be a local path or -.',
            param_hint='INPUT',
        )
    return location.read_text(encoding='utf-8')
