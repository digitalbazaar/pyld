---
hide: [toc]
---

# :material-import: `pyld from-rdf`

!!! warning "Requires `pip install PyLD[cli]`"

Convert raw N-Quads from a local path or `-` into JSON-LD. Remote RDF input is
not supported.

::: mkdocs-typer2
    :module: pyld.cli
    :name: pyld
    :command: from-rdf
    :termynal: true
    :width: 88

## Example

=== "Example"

    {{ terminal('pyld from-rdf docs/examples/data/person.nq', indent=4) }}

=== "person.nq"

    {{ example_data('data/person.nq', indent=4) }}
