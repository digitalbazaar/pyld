---
hide: [toc]
---

# :material-download: `pyld get`

!!! warning "Requires `pip install PyLD[cli]`"

Retrieve and print a JSON-LD document.

::: mkdocs-typer2
    :module: pyld.cli
    :name: pyld
    :command: get
    :termynal: true
    :width: 88

## Example

=== "Example"

    {{ terminal('pyld get docs/examples/data/person.jsonld', indent=4) }}

=== "person.jsonld"

    {{ example_data('data/person.jsonld', indent=4) }}
