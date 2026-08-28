"""The ``pyld to-rdf`` command."""

from __future__ import annotations

from typing import Annotated

from typer import Option

from pyld import jsonld
from pyld.cli.input import Input, document_value
from pyld.cli.options import (
    NQUADS_FORMAT,
    Base,
    ExtractAllScripts,
    RdfDirection,
    optional_options,
    processing_options,
)
from pyld.cli.output import print_nquads


def to_rdf_command(
    input_: Input,
    base: Base = None,
    extract_all_scripts: ExtractAllScripts = None,
    produce_generalized_rdf: Annotated[
        bool | None,
        Option(
            '--produce-generalized-rdf/--no-produce-generalized-rdf',
            help='Permit generalized RDF output.',
        ),
    ] = None,
    rdf_direction: Annotated[
        RdfDirection | None,
        Option(help='How to encode base direction in RDF.'),
    ] = None,
) -> None:
    """Convert a JSON-LD document to N-Quads."""
    options = {
        **processing_options(
            base=base,
            extract_all_scripts=extract_all_scripts,
        ),
        'format': NQUADS_FORMAT,
        **optional_options(
            produceGeneralizedRdf=produce_generalized_rdf,
            rdfDirection=rdf_direction,
        ),
    }
    result = jsonld.to_rdf(document_value(input_), options=options)
    print_nquads(result)
