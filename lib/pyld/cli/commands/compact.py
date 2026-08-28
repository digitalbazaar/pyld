"""The ``pyld compact`` command."""

from __future__ import annotations

from typing import Annotated

from typer import Option

from pyld import jsonld
from pyld.cli.input import (
    ContextArgument,
    Input,
    document_value,
    ensure_single_stdin,
)
from pyld.cli.options import (
    Base,
    ExpandContext,
    ExtractAllScripts,
    optional_options,
    processing_options,
)
from pyld.cli.output import print_json


def compact_command(
    input_: Input,
    context: ContextArgument,
    expand_context: ExpandContext = None,
    base: Base = None,
    extract_all_scripts: ExtractAllScripts = None,
    compact_arrays: Annotated[
        bool | None,
        Option(
            '--compact-arrays/--no-compact-arrays',
            help='Compact single-value arrays when appropriate.',
        ),
    ] = None,
    graph: Annotated[
        bool | None,
        Option(
            '--graph/--no-graph',
            help='Always emit a top-level graph.',
        ),
    ] = None,
) -> None:
    """Compact a JSON-LD document using a context."""
    ensure_single_stdin(input_, context, expand_context)
    options = {
        **processing_options(
            base=base,
            extract_all_scripts=extract_all_scripts,
            expand_context=expand_context,
        ),
        **optional_options(compactArrays=compact_arrays, graph=graph),
    }
    result = jsonld.compact(
        document_value(input_),
        document_value(context),
        options=options,
    )
    print_json(result)
