"""Shared JSON-LD API option construction for CLI commands."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from typer import Option

from pyld.cli.input import document_loader, document_value
from pyld.options import DocumentLoaderOptions, ExpandContextOptions

MaybeStr = str | None
FrameEmbed = Literal['@once', '@always', '@never', '@last', '@link']
RdfDirection = Literal['i18n-datatype', 'compound-literal']
NQUADS_FORMAT = 'application/n-quads'

Base = Annotated[MaybeStr, Option(help='The base IRI to use.')]

ExtractAllScripts = Annotated[
    bool | None,
    Option(
        '--extract-all-scripts/--no-extract-all-scripts',
        help='Extract all JSON-LD script elements from HTML, or just the first.',
    ),
]

ExpandContext = Annotated[
    MaybeStr,
    Option(help='Context path or URL. Pass - to read JSON from standard input.'),
]


def loader_options() -> DocumentLoaderOptions:
    return {'documentLoader': document_loader()}


def optional_options(**values: Any) -> dict[str, Any]:
    """Return only API options explicitly supplied by the user."""
    return {name: value for name, value in values.items() if value is not None}


def processing_options(
    *,
    base: MaybeStr,
    extract_all_scripts: bool | None,
    expand_context: MaybeStr = None,
) -> ExpandContextOptions:
    """Build processing options without overriding API defaults."""
    expand_context_options = (
        {}
        if expand_context is None
        else {'expandContext': document_value(expand_context)}
    )
    return {
        **loader_options(),
        'processingMode': 'json-ld-1.1',
        **optional_options(
            base=base,
            extractAllScripts=extract_all_scripts,
        ),
        **expand_context_options,
    }
