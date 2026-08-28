"""The ``pyld expand`` command."""

from __future__ import annotations

from typing import Annotated

from typer import Option

from pyld import jsonld
from pyld.cli.input import (
    Input,
    document_value,
    ensure_single_stdin,
)
from pyld.cli.options import Base, ExtractAllScripts, MaybeStr, processing_options
from pyld.cli.output import print_json


def expand_command(
    input_: Input,
    context: Annotated[
        MaybeStr,
        Option(
            '--context',
            '-c',
            help='Context path or URL. Pass - to read JSON from standard input.',
        ),
    ] = None,
    base: Base = None,
    extract_all_scripts: ExtractAllScripts = None,
) -> None:
    """Expand a JSON-LD document."""
    ensure_single_stdin(input_, context)
    options = processing_options(
        base=base,
        extract_all_scripts=extract_all_scripts,
    )
    if context is not None:
        options = {**options, 'expandContext': document_value(context)}

    result = jsonld.expand(document_value(input_), options=options)
    print_json(result)
