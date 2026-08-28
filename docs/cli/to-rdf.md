---
hide: [toc]
---

# :material-export: `pyld to-rdf`

!!! warning "Requires `pip install PyLD[cli]`"

Convert JSON-LD to raw N-Quads. `INPUT` accepts a path, URL, or `-`.

::: mkdocs-typer2
    :module: pyld.cli
    :name: pyld
    :command: to-rdf
    :termynal: true
    :width: 88

## Example

=== "Example"

    {{ terminal('pyld to-rdf docs/examples/data/person.jsonld', indent=4) }}

=== "person.jsonld"

    {{ example_data('data/person.jsonld', indent=4) }}
