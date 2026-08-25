---
hide: [toc]
---
# :material-shape-outline: `TypeDirectedDocumentLoader`

::: pyld.TypeDirectedDocumentLoader
    options:
      show_root_heading: false
      show_bases: false
      heading_level: 3
      members: false

`TypeDirectedDocumentLoader` dispatches a value to the loader registered for its Python type. Applications can register any types that represent distinct document locations or loading policies.

## Example use case

One use case for `TypeDirectedDocumentLoader` is an application that accepts local `pathlib.Path` values and remote URL strings in the same JSON-LD workflow. This example routes paths through `FileDocumentLoader`; when a local document references a remote `@context`, its `str` URL is delegated to `SchemeDirectedDocumentLoader`.

=== "Example"

    {{ example('document_loaders/type_directed.py', output_syntax='json', indent=4) }}

=== "person_remote_context.jsonld"

    {{ example_data('data/person_remote_context.jsonld', indent=4) }}
