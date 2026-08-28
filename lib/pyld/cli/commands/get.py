"""The ``pyld get`` command."""

from __future__ import annotations

from pyld import jsonld
from pyld.cli.input import Input, document_value, is_stdin, parse_location
from pyld.cli.options import loader_options
from pyld.cli.output import print_json


def get_command(input_: Input) -> None:
    """Retrieve and print a JSON-LD document."""
    if is_stdin(input_):
        document = document_value(input_)
    else:
        remote = jsonld.load_document(parse_location(input_), loader_options())
        document = remote['document']
    print_json(document)
