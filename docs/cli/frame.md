---
hide: [toc]
---

# :material-image-frame: `pyld frame`

!!! warning "Requires `pip install PyLD[cli]`"

Frame a JSON-LD document using a required frame. `INPUT` accepts a path, URL,
or `-`; `FRAME` accepts a path, URL, or `-`. Only one operand may read from
standard input.

::: mkdocs-typer2
    :module: pyld.cli
    :name: pyld
    :command: frame
    :termynal: true
    :width: 88

## Example

=== "Example"

    {{ terminal('pyld frame docs/examples/data/person.jsonld docs/examples/data/frame.jsonld', indent=4) }}

=== "person.jsonld"

    {{ example_data('data/person.jsonld', indent=4) }}

=== "frame.jsonld"

    {{ example_data('data/frame.jsonld', indent=4) }}
