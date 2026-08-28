"""The ``pyld from-rdf`` command."""

from __future__ import annotations

from typing import Annotated

from typer import Option

from pyld import jsonld
from pyld.cli.input import LocalInput, read_nquads
from pyld.cli.options import NQUADS_FORMAT, RdfDirection, optional_options
from pyld.cli.output import print_json


def from_rdf_command(
    input_: LocalInput,
    use_rdf_type: Annotated[
        bool | None,
        Option(
            '--use-rdf-type/--no-use-rdf-type',
            help='Use rdf:type instead of @type.',
        ),
    ] = None,
    use_native_types: Annotated[
        bool | None,
        Option(
            '--use-native-types/--no-use-native-types',
            help='Convert XSD values to native JSON types.',
        ),
    ] = None,
    rdf_direction: Annotated[
        RdfDirection | None,
        Option(help='How to decode base direction from RDF.'),
    ] = None,
) -> None:
    """Convert N-Quads to JSON-LD."""
    options = {
        'format': NQUADS_FORMAT,
        **optional_options(
            useRdfType=use_rdf_type,
            useNativeTypes=use_native_types,
            rdfDirection=rdf_direction,
        ),
    }
    result = jsonld.from_rdf(read_nquads(input_), options=options)
    print_json(result)
