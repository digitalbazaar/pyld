---
hide: [toc]
---

# :material-arrow-expand: `pyld expand`

!!! warning "Requires `pip install PyLD[cli]`"

Expand a JSON-LD document.

::: mkdocs-typer2
    :module: pyld.cli
    :name: pyld
    :command: expand
    :termynal: true
    :width: 88

## Example

=== "Example"

    {{ terminal('pyld expand docs/examples/data/person.jsonld', indent=4) }}

=== "person.jsonld"

    {{ example_data('data/person.jsonld', indent=4) }}
