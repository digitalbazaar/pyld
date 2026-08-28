---
hide: [toc]
---

# :material-format-list-group: `pyld flatten`

!!! warning "Requires `pip install PyLD[cli]`"

Flatten a JSON-LD document. Add `--context` to compact the flattened output.

::: mkdocs-typer2
    :module: pyld.cli
    :name: pyld
    :command: flatten
    :termynal: true
    :width: 88

## Example

=== "Example"

    {{ terminal('pyld flatten docs/examples/data/person.jsonld', indent=4) }}

=== "person.jsonld"

    {{ example_data('data/person.jsonld', indent=4) }}
