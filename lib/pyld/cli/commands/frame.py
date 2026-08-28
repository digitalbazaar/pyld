"""The ``pyld frame`` command."""

from __future__ import annotations

from typing import Annotated

from typer import Option

from pyld import jsonld
from pyld.cli.input import (
    FrameArgument,
    Input,
    document_value,
    ensure_single_stdin,
)
from pyld.cli.options import (
    Base,
    ExpandContext,
    ExtractAllScripts,
    FrameEmbed,
    optional_options,
    processing_options,
)
from pyld.cli.output import print_json


def frame_command(
    input_: Input,
    frame: FrameArgument,
    expand_context: ExpandContext = None,
    base: Base = None,
    extract_all_scripts: ExtractAllScripts = None,
    embed: Annotated[
        FrameEmbed | None,
        Option(help='Default @embed behavior.'),
    ] = None,
    explicit: Annotated[
        bool | None,
        Option('--explicit/--no-explicit', help='Default @explicit behavior.'),
    ] = None,
    omit_default: Annotated[
        bool | None,
        Option(
            '--omit-default/--no-omit-default',
            help='Default @omitDefault behavior.',
        ),
    ] = None,
    prune_blank_node_identifiers: Annotated[
        bool | None,
        Option(
            '--prune-blank-node-identifiers/--no-prune-blank-node-identifiers',
            help='Remove unnecessary blank node identifiers.',
        ),
    ] = None,
    require_all: Annotated[
        bool | None,
        Option(
            '--require-all/--no-require-all',
            help='Default @requireAll behavior.',
        ),
    ] = None,
) -> None:
    """Frame a JSON-LD document."""
    ensure_single_stdin(input_, frame, expand_context)
    options = {
        **processing_options(
            base=base,
            extract_all_scripts=extract_all_scripts,
            expand_context=expand_context,
        ),
        **optional_options(
            embed=embed,
            explicit=explicit,
            omitDefault=omit_default,
            pruneBlankNodeIdentifiers=prune_blank_node_identifiers,
            requireAll=require_all,
        ),
    }
    result = jsonld.frame(
        document_value(input_),
        document_value(frame),
        options=options,
    )
    print_json(result)
