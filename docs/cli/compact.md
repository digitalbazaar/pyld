---
hide: [toc]
---

# :material-arrow-collapse: `pyld compact`

!!! warning "Requires `pip install PyLD[cli]`"

Compact a JSON-LD document using a required context. `INPUT` accepts a path,
URL, or `-`; `CONTEXT` accepts a path, URL, or `-`. Only one operand may read
from standard input.

::: mkdocs-typer2
    :module: pyld.cli
    :name: pyld
    :command: compact
    :termynal: true
    :width: 88

## Example

=== "Example"

    {{ terminal('pyld compact docs/examples/data/person.jsonld docs/examples/data/context.jsonld', indent=4) }}

=== "person.jsonld"

    {{ example_data('data/person.jsonld', indent=4) }}

=== "context.jsonld"

    {{ example_data('data/context.jsonld', indent=4) }}
