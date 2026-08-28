"""The ``pyld flatten`` command."""

from __future__ import annotations

from typing import Annotated

from typer import Option

from pyld import jsonld
from pyld.cli.input import (
    Input,
    document_value,
    ensure_single_stdin,
)
from pyld.cli.options import (
    Base,
    ExpandContext,
    ExtractAllScripts,
    MaybeStr,
    processing_options,
)
from pyld.cli.output import print_json


def flatten_command(
    input_: Input,
    context: Annotated[
        MaybeStr,
        Option(
            '--context',
            '-c',
            help='Output context path or URL. Pass - to read JSON from standard input.',
        ),
    ] = None,
    expand_context: ExpandContext = None,
    base: Base = None,
    extract_all_scripts: ExtractAllScripts = None,
) -> None:
    """Flatten a JSON-LD document."""
    ensure_single_stdin(input_, context, expand_context)
    options = processing_options(
        base=base,
        extract_all_scripts=extract_all_scripts,
        expand_context=expand_context,
    )
    output_context = document_value(context) if context is not None else None
    result = jsonld.flatten(document_value(input_), output_context, options=options)
    print_json(result)
